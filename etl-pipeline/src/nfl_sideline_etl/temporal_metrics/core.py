"""Deterministic revision selection, frozen-calendar expectation and exact rollups."""
from decimal import Decimal
from fractions import Fraction

from ..offline_metrics.artifact import identity, json_bytes
from ..offline_metrics.statistics import COUNTS, FOUNDATIONS, exact_sum
from ..offline_metrics.validation import decimal_text
from . import ALGORITHM_VERSION, RESULT_VERSION
from .evidence import Policy
from .times import cutoff, instant, eastern_kickoff
from .validation import validate, fields, integer, string, json_values

WINDOWS = {'SEASON_TO_CUTOFF', 'LAST_3_CALENDAR_WEEKS', 'WEEK_OBSERVATION', 'HISTORICAL_REFERENCE'}
VERSIONS = {'population': 'classified-scrimmage-v1', 'definition': '1.0.0', 'adapter': '1.0.0'}


def ratio(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'exact': str(Fraction(numerator) / denominator) if denominator else None}


def validate_request(request):
    json_values(request)
    fields(request, ('season', 'phase', 'team', 'targetGameId', 'targetWeek', 'mode', 'windows', 'derivedAt'),
           ('asOfInstant', 'asOfDate', 'week', 'historicalSeason', 'historicalPhase', 'retrospective'))
    integer(request['season'], 1999)
    integer(request['targetWeek'], 1)
    string(request['team'])
    string(request['targetGameId'])
    if request['mode'] not in ('POINT_IN_TIME', 'EVENT_RECONSTRUCTION') or request['phase'] not in ('REG', 'POST'):
        raise ValueError('Invalid mode/phase')
    if not isinstance(request['windows'], list) or not request['windows'] or set(request['windows']) - WINDOWS or len(set(request['windows'])) != len(request['windows']):
        raise ValueError('Explicit supported windows required')
    if 'WEEK_OBSERVATION' in request['windows']:
        integer(request.get('week'), 1)
    if 'HISTORICAL_REFERENCE' in request['windows']:
        integer(request.get('historicalSeason'), 1999)
        if request['historicalSeason'] >= request['season'] or request.get('historicalPhase') not in ('REG', 'POST'):
            raise ValueError('Explicit earlier historical season/phase required')
    if request['mode'] == 'EVENT_RECONSTRUCTION':
        fields(request.get('retrospective'), ('calendars', 'states', 'calculations'))
        for mapping in request['retrospective'].values():
            if not isinstance(mapping, dict):
                raise ValueError('Explicit retrospective map required')
    elif 'retrospective' in request:
        raise ValueError('Retrospective choice is not a PIT selection')
    instant(request['derivedAt'])
    return cutoff(request)


def select(document, request):
    """No clocks, filesystem, DB, environment or network; does not mutate inputs."""
    normalized_cut, date_mapping = validate_request(request)
    resources, proofs, calculations = validate(document)
    policy = Policy(resources, proofs, document['policy'], request['mode'], instant(normalized_cut))
    decisions, used_resources, used_proofs = [], set(), set()

    def use_proof(envelope, subject, kinds):
        status, proof = policy.proof(envelope, subject, kinds)
        if proof is not None and status == 'ACCEPTED_BY_POLICY':
            used_proofs.add(proof['evidence_id'])
            used_resources.update(policy.closure(proof['dependencies']))
        return status

    def pick(candidates, category, key, eligibility):
        eligible = []
        explicit = None
        if request['mode'] == 'EVENT_RECONSTRUCTION':
            explicit = request['retrospective'][category].get(key)
        for candidate in sorted(candidates, key=lambda r: r['revision_id']):
            reasons, available = eligibility(candidate)
            if request['mode'] == 'EVENT_RECONSTRUCTION' and candidate['revision_id'] != explicit:
                reasons.append({'reason': 'RETROSPECTIVE_NOT_CHOSEN', 'subjectId': candidate['revision_id']})
            if not reasons:
                eligible.append((available or Fraction(0), candidate['revision_id'], candidate))
            decisions.append({'category': category, 'key': key, 'revision_id': candidate['revision_id'],
                              'selected': False, 'reasons': reasons, 'selectionOrderAvailableAtEpochSeconds': str(available) if available is not None else None})
        if request['mode'] == 'EVENT_RECONSTRUCTION' and explicit is None:
            raise ValueError('Explicit retrospective selection required: ' + category + '/' + key)
        if explicit is not None and explicit not in {c['revision_id'] for c in candidates}:
            raise ValueError('Retrospective revision does not match scope: ' + explicit)
        chosen = max(eligible, key=lambda row: row[:2])[2] if eligible else None
        for decision in decisions:
            if decision['category'] != category or decision['key'] != key:
                continue
            if chosen is not None and decision['revision_id'] == chosen['revision_id']:
                decision['selected'] = True
            elif not decision['reasons']:
                decision['reasons'] = [{'reason': 'SUPERSEDED_ELIGIBLE_REVISION', 'subjectId': decision['revision_id']}]
        return chosen

    scopes = {(request['season'], request['phase'])}
    if 'HISTORICAL_REFERENCE' in request['windows']:
        scopes.add((request['historicalSeason'], request['historicalPhase']))
    calendars, states = {}, {}
    for season, phase in sorted(scopes):
        candidates = [r for r in resources.values() if r['kind'] == 'CALENDAR' and (r['payload']['season'], r['payload']['phase']) == (season, phase)]
        cal = pick(candidates, 'calendars', f'{season}/{phase}', lambda r: policy.resource(r['revision_id']))
        calendars[season, phase] = cal
        if cal is None:
            continue
        used_resources.update(policy.closure([cal['revision_id']]))
        for g in sorted(cal['payload']['games'], key=lambda g: g['game_id']):
            gid = g['game_id']
            candidates = [r for r in resources.values() if r['kind'] == 'STATE' and r['payload']['game_id'] == gid and r['payload']['calendar_revision_id'] == cal['revision_id']]
            # Target may have no state: uncertainty is reported rather than inventing kickoff.
            if not candidates and gid == request['targetGameId']:
                states[cal['revision_id'], gid] = None
                continue
            state = pick(candidates, 'states', cal['revision_id'] + '/' + gid, lambda r: policy.resource(r['revision_id']))
            states[cal['revision_id'], gid] = state
            if state:
                used_resources.update(policy.closure([state['revision_id']]))
    # Pregame time is an independent guarantee from identity exclusion.
    current = calendars[request['season'], request['phase']]
    target_state = states.get((current['revision_id'], request['targetGameId'])) if current else None
    pregame = {'targetGameExcluded': True, 'timeStatus': 'PREGAME_TIME_UNVERIFIED', 'kickoff': None}
    if target_state and target_state['payload']['kickoff']:
        k = target_state['payload']['kickoff']
        converted = k['value'] if 'value' in k else eastern_kickoff(k['gameday'], k['gametime'])
        if converted:
            env = {'value': converted, 'evidence_id': k['evidence_id']}
            if use_proof(env, target_state['revision_id'], {'METADATA'}) == 'ACCEPTED_BY_POLICY':
                if policy.cut > instant(converted):
                    raise ValueError('PREGAME_CUTOFF_AFTER_KICKOFF')
                pregame.update(timeStatus='PREGAME_TIME_VERIFIED_BY_POLICY', kickoff={'utc': converted, 'original': k, 'zone': 'America/New_York' if 'gameday' in k else None})

    blocks = []
    for window in sorted(request['windows']):
        historical = window == 'HISTORICAL_REFERENCE'
        season = request['historicalSeason'] if historical else request['season']
        phase = request['historicalPhase'] if historical else request['phase']
        cal = calendars[season, phase]
        if window == 'LAST_3_CALENDAR_WEEKS':
            weeks = list(range(max(1, request['targetWeek'] - 3), request['targetWeek']))
        elif window == 'WEEK_OBSERVATION':
            weeks = [request['week']]
        else:
            weeks = sorted({g['week'] for g in cal['payload']['games']}) if cal else []
        events, selected_calculations = [], []
        calendar_complete = False
        closed = set()
        if cal:
            calendar_complete = use_proof(cal['payload']['complete'], cal['revision_id'], {'CALENDAR_COMPLETE'}) == 'ACCEPTED_BY_POLICY' and cal['payload']['complete']['value'] is True
            for c in cal['payload']['closed_weeks']:
                if use_proof({'value': c['week'], 'evidence_id': c['evidence_id']}, cal['revision_id'], {'PERIOD_CLOSED'}) == 'ACCEPTED_BY_POLICY':
                    closed.add(c['week'])
        scheduled = [g for g in cal['payload']['games'] if request['team'] in (g['home_team'], g['away_team']) and g['week'] in weeks] if cal else []
        for g in sorted(scheduled, key=lambda g: g['game_id']):
            gid = g['game_id']
            event = {'game': g, 'eventEligible': False, 'eventUncertain': False, 'reasons': [],
                     'stateRevisionId': None, 'calculationRevisionId': None, 'calculationId': None,
                     'coverageRevisionId': None, 'sourceSetId': None, 'completeness': 'UNKNOWN',
                     'sourceState': 'SOURCE_UNKNOWN'}
            events.append(event)
            if gid == request['targetGameId']:
                event['reasons'].append('TARGET_GAME_EXCLUDED')
                continue
            state = states.get((cal['revision_id'], gid))
            if state is None:
                event['eventUncertain'] = True
                event['reasons'].append('STATE_UNKNOWN_OR_INELIGIBLE')
                continue
            event['stateRevisionId'] = state['revision_id']
            p = state['payload']
            source_cause = p.get('source_cause')
            event['sourceCause'] = source_cause['value'] if use_proof(source_cause, state['revision_id'], {'METADATA'}) == 'ACCEPTED_BY_POLICY' else 'SOURCE_UNKNOWN'
            event['eventUpperBound'] = p['event_upper_bound']
            bound_status = use_proof(p['event_upper_bound'], state['revision_id'], {'FINAL_OBSERVATION', 'EVENT_END_BOUND'})
            if p['status'] != 'FINAL' or bound_status != 'ACCEPTED_BY_POLICY':
                event['eventUncertain'] = True
                event['reasons'].append('EVENT_TIME_UNKNOWN' if p['status'] == 'FINAL' else 'EVENT_NOT_FINAL')
                event['boundQualification'] = bound_status
                continue
            if instant(p['event_upper_bound']['value']) >= policy.cut:
                event['reasons'].append('EVENT_NOT_BEFORE_CUTOFF')
                continue
            event['eventEligible'] = True
            candidates = [c for c in calculations.values() if c['calendar_revision_id'] == cal['revision_id'] and c['game']['game_id'] == gid]
            def calculation_eligibility(c):
                reasons, available_times = [], []
                for rid in [c['calendar_revision_id'], c['pbp_revision_id'], *c['metadata_revision_ids']]:
                    rejected, available = policy.resource(rid)
                    reasons.extend(rejected)
                    if available is not None:
                        available_times.append(available)
                if c['versions'] != VERSIONS:
                    reasons.append({'reason': 'INCOMPATIBLE_DEFINITION_OR_POPULATION', 'subjectId': c['revision_id']})
                for source_id, env in c['source_models'].items():
                    status, source_proof = policy.proof(env, source_id, {'METADATA'})
                    if status == 'ACCEPTED_BY_POLICY':
                        available_times.append(instant(source_proof['recorded_at']))
                    if status in ('EVIDENCE_NOT_KNOWN_AT_CUTOFF', 'EVIDENCE_DEPENDENCY_INELIGIBLE'):
                        reasons.append({'reason': status, 'subjectId': env['evidence_id']})
                model_values = source_model_values(c, policy)
                known_models = set(model_values.values()) - {'UNKNOWN'}
                if len(known_models) > 1:
                    reasons.append({'reason': 'INCOMPATIBLE_EPA_MODELS_IN_SOURCE_SET', 'subjectId': c['revision_id']})
                model_status, _ = policy.proof(c['model'], c['calculation_id'], {'METADATA'})
                if model_status == 'ACCEPTED_BY_POLICY' and c['model']['value'] != 'UNKNOWN' and known_models - {c['model']['value']}:
                    reasons.append({'reason': 'CALCULATION_SOURCE_MODEL_CONFLICT', 'subjectId': c['revision_id']})
                for env, subject, kinds in ((c['completeness'], c['coverage_revision_id'], {'PBP_COMPLETE'}), (c['model'], c['calculation_id'], {'METADATA'}), (c.get('source_cause'), c['coverage_revision_id'], {'METADATA'})):
                    status, metadata_proof = policy.proof(env, subject, kinds)
                    if status == 'ACCEPTED_BY_POLICY':
                        available_times.append(instant(metadata_proof['recorded_at']))
                    if status in ('EVIDENCE_NOT_KNOWN_AT_CUTOFF', 'EVIDENCE_DEPENDENCY_INELIGIBLE'):
                        reasons.append({'reason': status, 'subjectId': env['evidence_id']})
                return reasons, max(available_times) if available_times else None
            # Explicit reconstruction may choose null only to acknowledge a source gap.
            key = cal['revision_id'] + '/' + gid
            if request['mode'] == 'EVENT_RECONSTRUCTION' and request['retrospective']['calculations'].get(key, 'MISSING') is None:
                for c in candidates:
                    decisions.append({'category': 'calculations', 'key': key, 'revision_id': c['revision_id'], 'selected': False,
                                      'reasons': [{'reason': 'RETROSPECTIVE_NOT_CHOSEN', 'subjectId': c['revision_id']}]})
                chosen = None
            else:
                chosen = pick(candidates, 'calculations', key, calculation_eligibility)
            if chosen is None:
                event['sourceState'] = event['sourceCause']
                event['reasons'].append('PBP_REVISION_UNAVAILABLE_AT_CUTOFF' if candidates else event['sourceCause'])
                continue
            c = chosen
            selected_calculations.append(c)
            used_resources.update(policy.closure([c['calendar_revision_id'], c['pbp_revision_id'], *c['metadata_revision_ids']]))
            event.update(calculationRevisionId=c['revision_id'], calculationId=c['calculation_id'], coverageRevisionId=c['coverage_revision_id'], sourceSetId=c['pbp_revision_id'])
            complete_status = use_proof(c['completeness'], c['coverage_revision_id'], {'PBP_COMPLETE'})
            completeness = c['completeness']['value'] if complete_status == 'ACCEPTED_BY_POLICY' else 'UNKNOWN'
            event.update(completeness=completeness, completenessQualification=complete_status,
                         sourceState='OBSERVED' if completeness == 'COMPLETE' else 'PARTIAL')
            if c.get('source_cause') and use_proof(c['source_cause'], c['coverage_revision_id'], {'METADATA'}) == 'ACCEPTED_BY_POLICY':
                event['sourceCause'] = c['source_cause']['value']
            model_status = use_proof(c['model'], c['calculation_id'], {'METADATA'})
            source_models = source_model_values(c, policy)
            for source_id, env in c['source_models'].items():
                use_proof(env, source_id, {'METADATA'})
            event['epaModel'] = next(iter(set(source_models.values()))) if len(set(source_models.values())) == 1 else 'UNKNOWN'
            event['sourceModels'] = source_models
            event['modelQualification'] = model_status
            if 'UNKNOWN' in source_models.values():
                event['epaModel'] = 'UNKNOWN'
            event['unknownFilterFlagsN'] = c['unknown_filter_flags_n']
        eligible = [e for e in events if e['eventEligible']]
        uncertain = [e['game']['game_id'] for e in events if e['eventUncertain']]
        complete = [e['game']['game_id'] for e in eligible if e['completeness'] == 'COMPLETE']
        observed = [e['game']['game_id'] for e in eligible if e['calculationId'] is not None]
        # Open periods disallow percentage expectations even if known events passed.
        expectation_known = cal is not None and calendar_complete and not uncertain and set(weeks) <= closed
        expected = len(eligible) if expectation_known else None
        weekly = []
        for week in weeks:
            games = [e for e in events if e['game']['week'] == week and e['game']['game_id'] != request['targetGameId']]
            if not calendar_complete:
                status = 'CALENDAR_UNKNOWN'
            elif week not in closed:
                status = 'NOT_YET_CLOSED'
            elif not games:
                status = 'TARGET_GAME_EXCLUDED' if any(e['game']['week'] == week and e['game']['game_id'] == request['targetGameId'] for e in events) else 'BYE'
            elif any(e['eventUncertain'] for e in games):
                status = 'EVENT_TIME_UNKNOWN'
            elif not all(e['eventEligible'] for e in games):
                status = 'NOT_YET_CLOSED'
            elif not all(e['calculationId'] for e in games):
                status = 'SOURCE_UNKNOWN'
            elif not all(e['completeness'] == 'COMPLETE' for e in games):
                status = 'PARTIAL'
            else:
                rows = [r for c in selected_calculations if c['game']['week'] == week for r in c['statistics'] if r['team'] == request['team']]
                status = 'NO_ELIGIBLE_PLAYS' if not any(r['eligible_n'] for r in rows) else 'NO_EPA_OBSERVATIONS' if not any(r['epa_n'] for r in rows) else 'OBSERVED'
            weekly.append({'week': week, 'status': status, 'gameIds': [e['game']['game_id'] for e in games]})
        strict_policy = Policy(resources, proofs, document['policy'], 'POINT_IN_TIME', policy.cut)
        knowledge_known = [c['game']['game_id'] for c in selected_calculations if not any(strict_policy.resource(r)[0] for r in [c['calendar_revision_id'], c['pbp_revision_id'], *c['metadata_revision_ids']])]
        metric_observed = sorted(c['game']['game_id'] for c in selected_calculations if any(r['epa_n'] for r in c['statistics'] if r['team'] == request['team'] and r['foundation'] == 'general'))
        expectation_failures = []
        if cal is None:
            expectation_failures.append({'reason': 'CALENDAR_INELIGIBLE_OR_UNKNOWN'})
        elif not calendar_complete:
            expectation_failures.append({'reason': 'CALENDAR_COMPLETENESS_UNPROVEN'})
        if set(weeks) - closed:
            expectation_failures.append({'reason': 'PERIOD_NOT_CLOSED', 'weeks': sorted(set(weeks) - closed)})
        if uncertain:
            expectation_failures.append({'reason': 'EVENT_EXPECTATION_UNCERTAIN', 'gameIds': sorted(uncertain)})
        coverage = {'expectedGames': expected, 'expectationFailures': expectation_failures, 'availabilityKnownGameIds': sorted(knowledge_known), 'metricObservedGameIds': metric_observed, 'knownEligibleGameIds': [e['game']['game_id'] for e in eligible],
                    'uncertainGameIds': uncertain, 'observedGameIds': observed, 'observedCompleteGameIds': complete,
                    'sourceRatio': ratio(len(complete), expected) if expected is not None else None,
                    'calendarComplete': calendar_complete, 'closedWeeks': sorted(closed & set(weeks)),
                    'gaps': [{'gameId': e['game']['game_id'], 'reason': e.get('sourceCause', 'SOURCE_UNKNOWN'), 'details': e['reasons']} for e in eligible if not e['calculationId']]}
        aggregates = aggregate(selected_calculations, events, request['team'], coverage)
        blocks.append({'window': window, 'origin': 'HISTORICAL_REFERENCE' if historical else 'CURRENT',
                       'season': season, 'phase': phase, 'calendarRevisionId': cal['revision_id'] if cal else None,
                       'requestedWeeks': weeks, 'actualWeeks': sorted({e['game']['week'] for e in events if e['calculationId']}),
                       'scheduledGameIds': [e['game']['game_id'] for e in events], 'events': events,
                       'coverage': coverage, 'weeklyStates': weekly, 'aggregates': aggregates})
    # Availability/ingestion proofs are part of the selected lineage too.
    pending = list(used_resources)
    while pending:
        rid = pending.pop()
        for key in ('available_at', 'ingested_at'):
            env = resources[rid][key]
            if env:
                status, proof = policy.proof(env, rid, {'ARCHIVE_OBSERVATION', 'SYSTEM_INGESTION'} if key == 'available_at' else {'SYSTEM_INGESTION'})
                if status != 'ACCEPTED_BY_POLICY':
                    continue
                used_proofs.add(proof['evidence_id'])
                for dep in policy.closure(proof['dependencies']):
                    if dep not in used_resources:
                        used_resources.add(dep)
                        pending.append(dep)
    normalized_request = {k: v for k, v in request.items() if k not in ('derivedAt', 'asOfDate', 'asOfInstant', 'retrospective')}
    normalized_request['windows'] = sorted(request['windows'])
    normalized_request['asOfInstant'] = normalized_cut
    semantic = {'resultVersion': RESULT_VERSION, 'algorithmVersion': ALGORITHM_VERSION,
                'policy': document['policy'], 'request': normalized_request, 'asOfDateMapping': date_mapping,
                'pregame': pregame, 'blocks': blocks,
                'resourcesUsed': [resources[r] for r in sorted(used_resources)],
                'evidenceUsed': [proofs[e] for e in sorted(used_proofs)]}
    # Canonicalize unordered input collections within the semantic projection.
    semantic = canonical(semantic)
    result = {**semantic, 'result_id': identity(semantic), 'derivedAt': request['derivedAt'],
              'structuralValidation': 'PASSED', 'revisionDecisions': canonical(decisions),
              'temporalEligibility': [{'window': b['window'], 'calendarEligible': b['calendarRevisionId'] is not None,
                                       'eligibleGameIds': b['coverage']['knownEligibleGameIds'],
                                       'uncertainGameIds': b['coverage']['uncertainGameIds']} for b in blocks],
              'input_id': identity(canonical(document)),
              'resourceDecisions': [{'revision_id': rid, 'used': rid in used_resources,
                                     'reasons': policy.resource(rid)[0] if rid not in used_resources else [],
                                     'usage': 'USED_IN_SELECTED_LINEAGE' if rid in used_resources else 'NOT_REQUIRED_OR_INELIGIBLE'} for rid in resources],
              'evidenceQualifications': [qualify_evidence(e, policy, used_proofs) for e in proofs.values()],
              'guarantees': {'temporalMode': request['mode'], 'knowledgeAtCutoff': 'CONDITIONAL_ON_MATERIALIZED_POLICY_EVIDENCE' if request['mode'] == 'POINT_IN_TIME' else 'NOT_DEMONSTRATED',
                             'historicalAvailability': 'UNKNOWN_OR_NOT_PROVEN' if request['mode'] == 'EVENT_RECONSTRUCTION' else 'ONLY_SELECTED_SOURCES_PROVEN_BY_POLICY',
                             'laterKnowledgePermitted': request['mode'] == 'EVENT_RECONSTRUCTION',
                             'postCutoffEvidenceIds': sorted(e for e in used_proofs if instant(proofs[e]['recorded_at']) >= policy.cut),
                             'postCutoffResourceIds': sorted(r for r in used_resources if any(resources[r][k] and instant(resources[r][k]['value']) >= policy.cut for k in ('available_at', 'ingested_at'))),
                             'unknownKnowledgeResourceIds': sorted(r for r in used_resources if resources[r]['kind'] != 'SET' and any(policy.proof(resources[r][k], r, {'ARCHIVE_OBSERVATION', 'SYSTEM_INGESTION'} if k == 'available_at' else {'SYSTEM_INGESTION'})[0] != 'ACCEPTED_BY_POLICY' for k in ('available_at', 'ingested_at'))),
                             'statisticalUncertainty': 'NOT_ESTIMATED',
                             'limits': ['Trust origins and materialized timestamps are premises, not external authentication.',
                                        'Hashes prove byte integrity only; receipts do not prove earlier availability, event closure or completeness.',
                                        'Coverage is not statistical confidence; partial/unknown content is not full-game volume.',
                                        'No historical local dataset certified by synthetic fixtures.']}}
    result['audit_id'] = identity(result)
    return result


def canonical(value):
    """These arrays are sets/bags, never meaningful event order. Keep duplicates."""
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return sorted((canonical(v) for v in value), key=lambda v: (type(v).__name__, v if isinstance(v, (str, int)) else json_bytes(v)))
    return value


def aggregate(calculations, events, team, coverage):
    by_game = {e['game']['game_id']: e for e in events}
    groups = {}
    for c in calculations:
        e = by_game[c['game']['game_id']]
        content_scope = 'COMPLETE' if e['completeness'] == 'COMPLETE' else 'AUDITABLE_SUBSET_' + e['completeness']
        model = e['epaModel']
        for row in c['statistics']:
            if row['team'] != team:
                continue
            key = (content_scope, model, row['role'], row['foundation'])
            groups.setdefault(key, []).append((row, c))
    known_models = {key[1] for key in groups if key[1] != 'UNKNOWN'}
    result = []
    for (scope, model, role, foundation), rows in sorted(groups.items()):
        sums = {count: sum(r[count] for r, _ in rows) for count in COUNTS}
        sums['epa_sum'] = decimal_text(exact_sum(Decimal(r['epa_sum']) for r, _ in rows if r['epa_n'])) if sums['epa_n'] else None
        general_rows = groups[scope, model, role, 'general']
        general_n = sum(r['eligible_n'] for r, _ in general_rows)
        game_ids = sorted(c['game']['game_id'] for _, c in rows)
        failures = []
        if scope != 'COMPLETE':
            failures.append('SOURCE_SUBSET')
        if coverage['expectedGames'] is None:
            failures.append('EXPECTATION_UNKNOWN')
        elif len(game_ids) != coverage['expectedGames'] or set(game_ids) != set(coverage['knownEligibleGameIds']):
            failures.append('INCOMPLETE_SOURCE_COVERAGE')
        if sums['epa_missing_n'] or sums['epa_nonfinite_n']:
            failures.append('EPA_INCOMPLETE')
        if any(c['unknown_filter_flags_n'] for _, c in rows):
            failures.append('UNKNOWN_FILTER_FLAGS')
        if not sums['epa_n']:
            failures.append('NO_EPA_OBSERVATIONS')
        if model == 'UNKNOWN':
            failures.append('EPA_MODEL_UNKNOWN')
        if len(known_models) > 1:
            failures.append('INCOMPATIBLE_EPA_MODELS_SEPARATED')
        result.append({'scope': scope, 'model': model, 'role': role, 'foundation': foundation,
                       'populationVersion': VERSIONS['population'], 'definitionVersion': VERSIONS['definition'],
                       'gameIds': game_ids, 'sums': sums, 'volume': sums['eligible_n'],
                       'epa': ratio(sums['epa_sum'], sums['epa_n']),
                       'successRate': ratio(sums['success_n'], sums['epa_n']),
                       'frequency': ratio(sums['eligible_n'], general_n) if foundation != 'general' else None,
                       'foundationCoverage': {'observedSourceGames': len(game_ids), 'expectedGames': coverage['expectedGames'],
                                              'eligibleN': sums['eligible_n'], 'epaN': sums['epa_n'],
                                              'epaObservedGameIds': sorted(c['game']['game_id'] for r, c in rows if r['epa_n']),
                                              'noEligiblePlaysGameIds': sorted(c['game']['game_id'] for r, c in rows if not r['eligible_n']),
                                              'noEpaObservationsGameIds': sorted(c['game']['game_id'] for r, c in rows if r['eligible_n'] and not r['epa_n']),
                                              'sourceRatio': ratio(len(game_ids), coverage['expectedGames']) if scope == 'COMPLETE' and coverage['expectedGames'] is not None else None},
                       'comparisonEligible': not failures, 'comparisonFailures': failures,
                       'statisticalUncertainty': 'NOT_ESTIMATED'})
    return result


def comparison(left, right, left_block, right_block, left_request, right_request):
    """Descriptive compatibility only; retains original values on failure."""
    failures = set(left['comparisonFailures'] + right['comparisonFailures'])
    for key in ('populationVersion', 'definitionVersion', 'role', 'foundation', 'model', 'scope'):
        if left[key] != right[key]:
            failures.add('MISMATCH_' + key)
    for key in ('season', 'phase', 'origin', 'window'):
        if left_block[key] != right_block[key]:
            failures.add('MISMATCH_' + key)
    for key in ('mode', 'asOfInstant'):
        if left_request[key] != right_request[key]:
            failures.add('MISMATCH_' + key)
    return {'comparisonEligible': not failures, 'failures': sorted(failures), 'left': left, 'right': right,
            'statisticalUncertainty': 'NOT_ESTIMATED'}


def qualify_evidence(e, policy, used):
    capabilities = {
        'HASH_CHECK': ['BYTE_INTEGRITY_ONLY'],
        'ARCHIVE_OBSERVATION': ['LOCAL_BYTE_OBSERVATION', 'CONSERVATIVE_AVAILABILITY_AT_OBSERVATION'],
        'SYSTEM_INGESTION': ['SYSTEM_INGESTION', 'CONSERVATIVE_AVAILABILITY_AT_INGESTION'],
        'FINAL_OBSERVATION': ['FINAL_STATE_OBSERVED', 'CONSERVATIVE_EVENT_UPPER_BOUND'],
        'EVENT_END_BOUND': ['DOCUMENTED_EVENT_UPPER_BOUND'],
        'CALENDAR_COMPLETE': ['CALENDAR_COMPLETENESS'],
        'PERIOD_CLOSED': ['CALENDAR_PERIOD_CLOSURE'],
        'PBP_COMPLETE': ['SOURCE_COMPLETENESS_DECLARATION_ACCEPTED'],
        'METADATA': ['MATERIALIZED_METADATA_VALUE'],
    }
    if e['evidence_id'] in used:
        status = 'ACCEPTED_BY_POLICY'
    elif e['origin'] not in policy.origins:
        status = 'DECLARATION_UNPROVEN'
    elif policy.mode == 'POINT_IN_TIME' and instant(e['recorded_at']) >= policy.cut:
        status = 'EVIDENCE_NOT_KNOWN_AT_CUTOFF'
    else:
        status = 'NOT_USED_OR_BINDING_UNPROVEN'
    return {'evidence_id': e['evidence_id'], 'kind': e['kind'], 'status': status,
            'subjectId': e['subject_id'], 'originalRecordedAt': e['recorded_at'],
            'knownBeforeCutoff': instant(e['recorded_at']) < policy.cut,
            'conditionalCapabilities': capabilities[e['kind']],
            'externallyAuthenticated': False}


def source_model_values(calculation, policy):
    return {source_id: env['value'] if policy.proof(env, source_id, {'METADATA'})[0] == 'ACCEPTED_BY_POLICY' else 'UNKNOWN'
            for source_id, env in calculation['source_models'].items()}
