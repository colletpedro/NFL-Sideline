"""Pure projection of a fully verified materialization, with nominal choices only.

Public file entry points in publication always verify/recover the accepted chain
first. This module has no filesystem/clock/DB access and never calls select().
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import re

from ..offline_metrics.artifact import identity, json_bytes
from ..offline_metrics.statistics import FOUNDATIONS, exact_sum
from ..offline_metrics.validation import decimal_text
from ..temporal_metrics.evidence import Policy
from ..temporal_metrics.times import instant
from ..temporal_metrics.validation import fields, integer, json_values, string, validate
from . import REQUEST_VERSION, BUNDLE_VERSION, IMPLEMENTATION_VERSION, OBSERVATION_VERSION

FAMILIES = ('epa', 'successRate', 'volume', 'frequency')
COUNT_MAP = {'eligibleN': 'eligible_n', 'epaN': 'epa_n', 'successN': 'success_n',
             'epaMissingN': 'epa_missing_n', 'epaNonfiniteN': 'epa_nonfinite_n'}
ASSOCIATION = ('gameId', 'calculationId', 'coverageRevisionId', 'artifactId', 'archiveId', 'temporalRevisionId')
FIELD_SCOPES = {
    'unknownFilterFlagsN': 'GAME_CONTEXT: original.coverage.unknown_filter_flags_n; '
    'not measured by team/role/foundation; sum once per distinct game within one observation; '
    'never sum across observations/groups',
    'generalEligibleN': 'same game/team/role/revisions: statistics foundation=general',
    'eligibleN,epaN,successN,epaMissingN,epaNonfiniteN,epaSum': 'original selected game/team/role/foundation statistics'}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def semantic_id(document):
    value = {k: v for k, v in document.items() if k not in ('observationId', 'derivedAt', 'presentation')}
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def unique(values):
    require(isinstance(values, list), 'Expected explicit list')
    return sorted({json_bytes(v): v for v in values}.values(), key=json_bytes)


def normalize_request(request):
    q = deepcopy(request)
    json_values(q)
    fields(q, ('requestVersion', 'source', 'derivedAt', 'presentation', 'requests'))
    require(q['requestVersion'] == REQUEST_VERSION, 'Unsupported observation request version')
    fields(q['source'], ('materializationId', 'temporalInputId'))
    for value in q['source'].values():
        require(isinstance(value, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', value), 'Invalid source identity')
    instant(q['derivedAt'])
    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', q['derivedAt']), 'derivedAt requires UTC whole seconds')
    fields(q['presentation'], ('epaDecimals', 'ratePercentDecimals', 'rounding'))
    integer(q['presentation']['epaDecimals']); integer(q['presentation']['ratePercentDecimals'])
    require(q['presentation']['rounding'] == 'HALF_UP', 'Unsupported presentation rounding')
    require(isinstance(q['requests'], list) and q['requests'], 'Explicit requests required')
    for r in q['requests']:
        fields(r, ('season', 'phase', 'weeks', 'origin', 'teams', 'roles', 'foundations',
                   'calendarSourceSetId', 'calendarRevisionId', 'associations'))
        integer(r['season'], 1999)
        require(r['phase'] in ('REG', 'POST') and r['origin'] in ('CURRENT', 'HISTORICAL_REFERENCE'), 'Invalid phase/origin')
        for key in ('weeks', 'teams', 'roles', 'foundations'):
            require(isinstance(r[key], list) and r[key], 'Explicit nonempty ' + key)
            for value in r[key]:
                integer(value, 1) if key == 'weeks' else string(value)
            r[key] = sorted(set(r[key]))
        require(not set(r['roles']) - {'off', 'def'} and not set(r['foundations']) - set(FOUNDATIONS), 'Unsupported group')
        for key in ('calendarSourceSetId', 'calendarRevisionId'):
            string(r[key])
        choices = {}
        require(isinstance(r['associations'], list), 'Explicit association list required')
        for a in r['associations']:
            fields(a, ASSOCIATION)
            for key, value in a.items():
                if key != 'temporalRevisionId' or value is not None:
                    string(value)
            require(a['gameId'] not in choices or choices[a['gameId']] == a, 'Ambiguous nominal game selection: ' + a['gameId'])
            choices[a['gameId']] = a
        r['associations'] = [choices[k] for k in sorted(choices)]
    q['requests'] = unique(q['requests'])
    return q


def request_semantic(q):
    return {k: v for k, v in q.items() if k not in ('derivedAt', 'presentation')}


def guarantee(state, reasons=(), evidence=(), **extra):
    return {'state': state, 'reasonCodes': sorted(set(reasons)), 'evidenceIds': sorted(set(evidence)), **extra}


def sufficient_values(totals, foundation):
    """E5a exact numerator/denominator projection, independent of presentation."""
    numbers = dict.fromkeys(FAMILIES)
    if totals is not None:
        numbers['volume'] = {'numerator': str(totals['eligibleN']), 'denominator': 1}
        if totals['epaN']:
            numbers['epa'] = {'numerator': totals['epaSum'], 'denominator': totals['epaN']}
            numbers['successRate'] = {'numerator': str(totals['successN']), 'denominator': totals['epaN']}
        if foundation != 'general' and totals['generalEligibleN']:
            numbers['frequency'] = {'numerator': str(totals['eligibleN']), 'denominator': totals['generalEligibleN']}
    return numbers


def project_verified(temporal, lineage, request):
    """Pure; caller must first reverify originals via lineage.verify_source()."""
    q = normalize_request(request)
    require(q['source'] == {'materializationId': lineage['materialization_id'],
                             'temporalInputId': lineage['temporalInputId']}, 'Nominal source package identity mismatch')
    resources, proofs, calculations = validate(temporal)
    # Only envelope qualification is reused. No event/revision/window selection.
    policy = Policy(resources, proofs, temporal['policy'], 'EVENT_RECONSTRUCTION', None)
    relations = lineage['relations']['relations']
    audits = {r['coverage_revision_id']: r['audit_json'] for r in relations['game_metric_coverage_revision']}
    choices = {r['calculation_id']: r for r in lineage['relations']['selection']}
    associations = {(r['calculation_id'], r['game_id']): r['coverage_revision_id']
                    for r in relations['metric_calculation_coverage']}
    outputs, mapping, evidence_index = {}, {}, {}
    def qualified(env, subject, kinds):
        status, proof = policy.proof(env, subject, kinds)
        if status != 'ACCEPTED_BY_POLICY':
            return None, []
        ref = identity(proof)
        evidence_index[ref] = {'originalEvidenceId': proof['evidence_id'], 'subjectId': subject}
        return env['value'], [ref]
    for r in q['requests']:
        cal = resources.get(r['calendarRevisionId'])
        require(cal and cal['kind'] == 'CALENDAR' and r['calendarSourceSetId'] in cal['dependencies'], 'Nominal calendar binding mismatch')
        require((cal['payload']['season'], cal['payload']['phase']) == (r['season'], r['phase']), 'Calendar scope mismatch')
        require(all(any(team in (g['home_team'], g['away_team']) for g in cal['payload']['games']) for team in r['teams']), 'Team absent from selected calendar')
        games = {g['game_id']: g for g in cal['payload']['games'] if g['week'] in r['weeks'] and
                 set(r['teams']) & {g['home_team'], g['away_team']}}
        require({a['gameId'] for a in r['associations']} == set(games), 'Nominal choices must include all declared calendar games, including gaps')
        selected = []
        for a in r['associations']:
            cid, cov = a['calculationId'], a['coverageRevisionId']
            require(cid in choices and choices[cid]['artifact_id'] == a['artifactId'] and
                    choices[cid]['archive_id'] == a['archiveId'], 'Artifact/archive/calculation association mismatch')
            require(associations.get((cid, a['gameId'])) == cov and cov in audits, 'Coverage association mismatch')
            audit = audits[cov]
            require({k: audit[k] for k in games[a['gameId']]} == games[a['gameId']] and
                    audit['calendar_revision_id'] == r['calendarSourceSetId'], 'Participants/period/calendar originals mismatch')
            candidates = [c for c in calculations.values() if c['calculation_id'] == cid and c['coverage_revision_id'] == cov]
            c = None
            if a['temporalRevisionId'] is not None:
                require(a['temporalRevisionId'] in calculations, 'Missing selected temporal association')
                c = calculations[a['temporalRevisionId']]
                require(c in candidates and c['calendar_revision_id'] == r['calendarRevisionId'], 'Nominal temporal association mismatch')
            else:
                require(not candidates and audit['statistics_status'] == 'SOURCE_UNKNOWN', 'Observed association requires explicit temporalRevisionId')
            selected.append((a, audit, c))
        selection_id = identity(r)
        for team in r['teams']:
            team_rows = [(a, audit, c) for a, audit, c in selected if team in (audit['home_team'], audit['away_team'])]
            model_map, model_declared = {}, {}
            for a, audit, c in team_rows:
                if c is None:
                    continue
                for sid, env in c['source_models'].items():
                    value, evidence = qualified(env, sid, {'METADATA'})
                    state = 'KNOWN' if value not in (None, 'UNKNOWN') else 'UNKNOWN'
                    m = {'sourceRevisionId': sid, 'state': state, 'modelId': value if state == 'KNOWN' else None,
                         'evidenceIds': evidence}
                    require(sid not in model_map or model_map[sid] == m, 'Conflicting source model qualifications: ' + sid)
                    model_map[sid] = m
                    declared = c['original']['manifest']['source_model_versions'][sid[7:]]['value']
                    require(sid not in model_declared or model_declared[sid] == declared, 'Conflicting original source models: ' + sid)
                    model_declared[sid] = declared
            values = {m['modelId'] or 'UNKNOWN' for m in model_map.values()}
            declared = set(model_declared.values())
            require(len(values) <= 1 and len(declared) <= 1,
                    'INCOMPATIBLE_EPA_MODELS_SEPARATED: split nominal requests; sources=' + ','.join(sorted(model_map)))
            model = next(iter(values), 'UNKNOWN')
            for role in r['roles']:
                for foundation in r['foundations']:
                    members, member_map, comp_proofs, limitations = [], [], [], []
                    def limit(code, subject):
                        limitations.append({'code': code, 'subjectId': subject})
                    for a, audit, c in team_rows:
                        complete, evidence = qualified(c['completeness'], a['coverageRevisionId'], {'PBP_COMPLETE'}) if c else (None, [])
                        complete = complete if complete in ('COMPLETE', 'PARTIAL') else 'UNKNOWN'
                        comp_proofs.extend(evidence)
                        st = None
                        sources, receipts = [], []
                        if c:
                            row = next(s for s in c['statistics'] if (s['team'], s['role'], s['foundation']) == (team, role, foundation))
                            general = next(s for s in c['statistics'] if (s['team'], s['role'], s['foundation']) == (team, role, 'general'))
                            st = {k: row[v] for k, v in COUNT_MAP.items()}
                            st.update(epaSum=decimal_text(Decimal(row['epa_sum'])) if row['epa_sum'] is not None else None,
                                      generalEligibleN=general['eligible_n'], unknownFilterFlagsN=audit['unknown_filter_flags_n'])
                            sources = sorted(c['source_models'])
                            archive = lineage['recoveredArchives'][a['archiveId']]
                            original = c['original']['manifest']
                            source_hashes = {i['sha256'] for i in original['inputs']}
                            art = next(x for x in relations['metric_artifact'] if x['artifact_id'] == a['artifactId'])
                            receipts = sorted(archive['receipts'][sha]['receipt_id'] for sha in source_hashes | set(art['files_json'].values()))
                            limit('UNKNOWN_FILTER_FLAGS_GAME_SCOPE', a['gameId'])
                            if audit['unknown_filter_flags_n']:
                                limit('UNKNOWN_FILTER_FLAGS', a['gameId'])
                        else:
                            limit('NO_SOURCE_OBSERVATION', a['gameId'])
                            manifests = [row['manifest_json'] for row in relations['metric_calculation'] if row['calculation_id'] == a['calculationId']]
                            if manifests and all(i['raw_rows'] == 0 for i in manifests[0]['inputs'] if i['kind'] == 'pbp'):
                                limit('EMPTY_SOURCE_SET_WITHOUT_GAME_OBSERVATION', a['gameId'])
                        if complete != 'COMPLETE':
                            limit('SOURCE_SUBSET' if complete == 'PARTIAL' else 'COMPLETENESS_UNKNOWN', a['gameId'])
                        members.append({'gameId': a['gameId'], 'week': audit['week'], 'round': audit['round'],
                            'sourceState': 'PRESENT' if c else 'ABSENT', 'sourceRevisionIds': sources,
                            'calculationId': a['calculationId'] if c else None, 'coverageRevisionId': a['coverageRevisionId'],
                            'artifactId': a['artifactId'] if c else None, 'archiveReceiptIds': receipts,
                            'completeness': complete, 'statistics': st})
                        member_map.append(a)
                    members.sort(key=lambda m: m['gameId'])
                    stats = [m['statistics'] for m in members if m['statistics'] is not None]
                    totals = None
                    if stats:
                        totals = {k: sum(s[k] for s in stats) for k in stats[0] if k != 'epaSum'}
                        totals['epaSum'] = decimal_text(exact_sum(Decimal(s['epaSum']) for s in stats if s['epaSum'] is not None)) if totals['epaN'] else None
                    numbers = sufficient_values(totals, foundation)
                    if totals is not None and not totals['epaN']:
                        limit('NO_EPA_OBSERVATIONS', team)
                    if totals is not None and foundation != 'general' and not totals['generalEligibleN']:
                        limit('ZERO_FREQUENCY_DENOMINATOR', team)
                    observed = [m for m in members if m['statistics'] is not None]
                    used = {fam: sorted(m['gameId'] for m in observed if fam == 'volume' or
                        (fam in ('epa', 'successRate') and m['statistics']['epaN']) or
                        (fam == 'frequency' and foundation != 'general' and m['statistics']['generalEligibleN'])) for fam in FAMILIES}
                    cal_complete, cal_evidence = qualified(cal['payload']['complete'], cal['revision_id'], {'CALENDAR_COMPLETE'})
                    closed = set()
                    for entry in cal['payload']['closed_weeks']:
                        value, proof = qualified({'value': entry['week'], 'evidence_id': entry['evidence_id']}, cal['revision_id'], {'PERIOD_CLOSED'})
                        if value is not None:
                            closed.add(value); cal_evidence.extend(proof)
                    known_expected = cal_complete is True and set(r['weeks']) <= closed
                    expected = sorted(m['gameId'] for m in members) if known_expected else None
                    count = len(expected) if expected is not None else None
                    cov_state = ('KNOWN' if len(observed) == count else 'PARTIAL') if known_expected else 'UNKNOWN'
                    cov_reasons = [] if cov_state == 'KNOWN' else ['INCOMPLETE_SOURCE_COVERAGE' if cov_state == 'PARTIAL' else 'EXPECTATION_UNKNOWN']
                    completeness = 'PARTIAL' if any(m['completeness'] == 'PARTIAL' for m in members) else ('UNKNOWN' if not members or any(m['completeness'] == 'UNKNOWN' for m in members) else 'COMPLETE')
                    comp_reasons = [] if completeness == 'COMPLETE' else ['SOURCE_SUBSET' if completeness == 'PARTIAL' else 'COMPLETENESS_UNKNOWN']
                    if cov_reasons:
                        limit(cov_reasons[0], team)
                    if model == 'UNKNOWN':
                        limit('EPA_MODEL_UNKNOWN', team)
                    limit('ARCHIVED_OBSERVATION_NOT_POINT_IN_TIME', team)
                    for reason in ('AVAILABLE_AT_UNKNOWN', 'INGESTED_AT_UNKNOWN', 'EVENT_TIME_UNKNOWN'):
                        limit(reason, team)
                    d = {'observationVersion': OBSERVATION_VERSION, 'policyVersion': 'metrics-consumption-policy-v1',
                         'derivationVersion': 'metrics-observation-projection-candidate-1', 'derivedAt': q['derivedAt'],
                         'originPath': 'OFFLINE_PERSISTED_ACCEPTED',
                         'definition': {'definitionVersion': '1.0.0', 'populationVersion': 'classified-scrimmage-v1', 'adapterVersion': '1.0.0'},
                         'subject': {'team': team, 'role': role, 'foundation': foundation},
                         'request': {'season': r['season'], 'phase': r['phase'], 'origin': r['origin'],
                            'period': {'kind': 'DECLARED_WEEKS', 'weeks': r['weeks']}, 'calendarSourceSetId': r['calendarSourceSetId'], 'selectionManifestId': selection_id},
                         'observed': {'actualWeeks': sorted({m['week'] for m in observed}), 'includedGameIds': sorted(m['gameId'] for m in observed), 'metricUsedGameIds': used},
                         'members': members, 'totals': totals, 'values': numbers,
                         'guarantees': {'integrity': guarantee('RECONCILED', evidence=[lineage['materialization_id']]),
                            'coverage': guarantee(cov_state, cov_reasons, cal_evidence, expectedGameIds=expected, expectedCount=count,
                                coverageRatio={'numerator': str(len(observed)), 'denominator': count} if count else None),
                            'completeness': guarantee(completeness, comp_reasons, comp_proofs),
                            'compatibility': guarantee('KNOWN', evidence=[lineage['temporalInputId']],
                                epaModel={'state': 'UNKNOWN' if model == 'UNKNOWN' else 'KNOWN', 'id': None if model == 'UNKNOWN' else model},
                                sourceModels=[model_map[sid] for sid in sorted(model_map)]),
                            'temporal': guarantee('UNKNOWN', ['AVAILABLE_AT_UNKNOWN', 'INGESTED_AT_UNKNOWN', 'EVENT_TIME_UNKNOWN'], cutoff=None, targetGameId=None, targetKickoff=None)},
                         'limitations': unique(limitations), 'presentation': q['presentation']}
                    d['observationId'] = semantic_id(d)
                    outputs[d['observationId']] = d
                    mapping[d['observationId']] = {'selectionManifestId': selection_id, 'associations': member_map}
    manifest = {'bundleVersion': BUNDLE_VERSION, 'implementationVersion': IMPLEMENTATION_VERSION,
        'source': q['source'], 'requestSemanticId': identity(request_semantic(q)), 'selfContained': True,
        'externalDependencies': [], 'fieldScopes': FIELD_SCOPES, 'observationIds': sorted(outputs),
        'lineageByObservation': mapping, 'evidenceIndex': evidence_index,
        'temporalGuarantee': 'NOT_DEMONSTRATED', 'comparison': 'NOT_IMPLEMENTED'}
    manifest['bundleId'] = identity(manifest)
    return q, [outputs[key] for key in sorted(outputs)], manifest
