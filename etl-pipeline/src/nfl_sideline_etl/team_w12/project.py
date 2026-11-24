"""Explicit two-week team observations; never an average of weekly rates."""
from collections import Counter
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import json
from . import VERSION, PROJECTION, SOURCE_PIN
from ..situational import digest

GUARANTEES = {k: 'UNKNOWN' for k in ('completeness', 'expectedCoverage', 'epaModel', 'historicalAvailability')}
VALID = ('AVAILABLE', 'NO_OPPORTUNITIES')
FOUNDATIONS = ('general', 'classified_pass', 'classified_rush')


def permission(operation, descriptors, reasons=()):
    reasons = list(reasons)
    for d in descriptors:
        if d['status'] not in VALID: reasons.append(d['status'])
        if d.get('ambiguousIds'): reasons.append('AMBIGUOUS_UNITS')
        if d['weeks'] != [1, 2] or not d['integrityVerified'] or not d['provenanceVerified']: reasons.append('UNVERIFIED_SCOPE_OR_SOURCE')
    if operation == 'sideBySide':
        if any(not d['denominator'] for d in descriptors): reasons.append('RATE_UNDEFINED')
        for k in ('metric', 'definition', 'population', 'unit', 'sourceHash', 'sourceColumn', 'weeks'):
            if any(d[k] != descriptors[0][k] for d in descriptors): reasons.append('INCOMPATIBLE_'+k.upper())
    return dict(operation=operation, allowed=not reasons, policyVersion='broadcast-team-policy-1.0.0',
                observationIds=[d['id'] for d in descriptors], reasonCodes=sorted(set(reasons)),
                interpretation='OBSERVED_SAMPLE_DESCRIPTIVE', independence='NOT_ASSERTED')


def aggregate_descriptor(parts, team, perspective, name, games):
    """Zero opportunities is valid. Missing/insufficient components never silently disappear."""
    first = deepcopy(parts[0])
    first.update(id=f'{team}/{perspective}/1-2/{name}', team=team, perspective=perspective, weeks=[1, 2], gameIds=games)
    reasons = []
    if len(parts) != 2 or sorted(w for p in parts for w in p['weeks']) != [1, 2] or sorted(g for p in parts for g in p['gameIds']) != sorted(games): reasons.append('MISSING_OR_WRONG_COMPONENT')
    for key in ('metric', 'definition', 'population', 'unit', 'sourceHash', 'sourceColumn', 'season', 'phase'):
        if any(p[key] != parts[0][key] for p in parts): reasons.append('INCOMPATIBLE_'+key.upper())
    ids = [u for p in parts for u in p['unitIds']]
    if len(ids) != len(set(ids)): reasons.append('DUPLICATE_UNITS')
    if any(not p['integrityVerified'] or not p['provenanceVerified'] for p in parts): reasons.append('UNVERIFIED_COMPONENT')
    if any(p['ambiguousIds'] for p in parts): reasons.append('AMBIGUOUS_UNITS')
    for p in parts:
        if p['status'] in VALID:
            n, den = p['numerator'], p['denominator']
            try:
                v = Fraction(str(n))
                if isinstance(den, bool) or not isinstance(den, int) or den < 0 or len(p['unitIds']) != den or (p['status'] == 'AVAILABLE' and den == 0) or (p['status'] == 'NO_OPPORTUNITIES' and (den != 0 or v != 0)) or (p['metric'] != 'epa' and (v.denominator != 1 or not 0 <= v <= den)):
                    reasons.append('INVALID_NUMERATOR_DENOMINATOR')
            except (ValueError, TypeError, ZeroDivisionError): reasons.append('INVALID_NUMERATOR_DENOMINATOR')
    if any(p['status'] == 'SOURCE_ABSENT' for p in parts): status = 'SOURCE_ABSENT'
    elif any(p['status'] not in VALID for p in parts) or reasons: status = 'INSUFFICIENT'
    else: status = 'AVAILABLE' if sum(p['denominator'] for p in parts) else 'NO_OPPORTUNITIES'
    first.update(status=status, unitIds=ids, ambiguousIds=[x for p in parts for x in p['ambiguousIds']], guarantees=GUARANTEES,
                 numerator=None, denominator=None, componentReasonCodes=sorted(set(reasons)))
    if status in VALID:
        first['denominator'] = sum(p['denominator'] for p in parts)
        with localcontext() as ctx:
            ctx.prec = 100
            n = sum((Decimal(str(p['numerator'])) for p in parts), Decimal(0))
        first['numerator'] = format(n, 'f') if name in FOUNDATIONS else int(n)
    return first


def metric(parts, units, team, role, family, games, original):
    d = aggregate_descriptor([p['descriptor'] for p in parts], team, role, family, games)
    observation = dict(status=d['status'], numerator=d['numerator'], denominator=d['denominator'], unitIds=d['unitIds'],
                       ratio=None if not d['denominator'] else dict(numerator=d['numerator'], denominator=d['denominator']),
                       exclusions=dict(sum_counters([p['observation']['exclusions'] for p in parts])))
    if family == 'third':
        observation.update(byDistance={}, byType={})
        for key, values in [('byDistance', ('short', 'medium', 'long', 'unknown')), ('byType', ('pass', 'run'))]:
            for value in values:
                group = [u for u in units if u['distance' if key == 'byDistance' else 'kind'] == value]
                observation[key][value] = dict(numerator=sum(u['converted'] for u in group), denominator=len(group))
    else: observation['outcomes'] = dict(Counter(u['outcome'] for u in units))
    matched = d['status'] not in VALID or (d['numerator'] == original[family]['numerator'] and d['denominator'] == original[family]['denominator'] and
                  d['status'] == original[family]['status'] and set(d['unitIds']) == set(original[family]['unitIds']))
    if not matched: raise ValueError('Original situational aggregate mismatch: '+d['id'])
    if d['status'] in VALID:
        for key in ('byDistance', 'byType') if family == 'third' else ('outcomes',):
            if observation[key] != original[family][key]: raise ValueError('Original aggregate partition mismatch')
    return dict(descriptor=d, display=permission('display', [d]), aggregation=permission('aggregate', [d], d['componentReasonCodes']),
                components=parts, observation=observation, originalAggregate=deepcopy(original[family]), originalAggregateId=original['id']+'/'+family,
                originalReconciliation='MATCHED' if d['status'] in VALID else 'UNAVAILABLE_COMPONENT')


def sum_counters(counters):
    out = Counter()
    for counter in counters: out.update(counter)
    return out


def project(index, documents, source_root, policy):
    situational = json.loads((source_root/'sources/situational/situational.json').read_bytes())
    observations = json.loads((source_root/'sources/observations/observations.json').read_bytes())
    original_s = {d['id']: d for d in situational['documents']}
    original_e = {(o['subject']['team'], o['subject']['role'], o['subject']['foundation']): o for o in observations
                  if o['request']['season'] == 2026 and o['request']['phase'] == 'REG' and o['request']['period']['weeks'] == [1, 2]}
    result = {}
    teams = sorted({t for g in index['games'] for t in (g['away'], g['home'])})
    if len(teams) != 32: raise ValueError('Expected 32 teams')
    for team in teams:
        games = sorted([g for g in index['games'] if team in (g['away'], g['home'])], key=lambda g: g['week'])
        if [g['week'] for g in games] != [1, 2]: raise ValueError('Two exact games required')
        game_ids = [g['gameId'] for g in games]
        productions = []
        for role in ('off', 'def'):
            components = []
            for game in games:
                doc = documents[game['gameId']]
                p = next(p for p in doc['productions'] if (p['offense'] == team if role == 'off' else p['defense'] == team))
                components.append(dict(gameId=game['gameId'], week=game['week'], offense=p['offense'], defense=p['defense'], sourceDocumentHash=game['documentHash'], production=p))
            attempts = [deepcopy(u) for c in components for u in c['production']['thirdAttempts']]
            campaigns = [deepcopy(u) for c in components for u in c['production']['redZoneCampaigns']]
            if any(len([u['id'] for u in us]) != len({u['id'] for u in us}) for us in (attempts, campaigns)): raise ValueError('Duplicate evidence')
            original = original_s[f'{team}/{role}/1-2']
            if {g['gameId'] for g in original['games']} != set(game_ids): raise ValueError('Legacy game scope differs')
            metrics = {f: metric([c['production']['metrics'][f] for c in components], attempts if f == 'third' else campaigns,
                                team, role, f, game_ids, original) for f in ('third', 'redZone')}
            epas = []
            for foundation in FOUNDATIONS:
                parts = [next(e for e in c['production']['epa'] if e['foundation'] == foundation) for c in components]
                d = aggregate_descriptor([e['descriptor'] for e in parts], team, role, foundation, game_ids)
                orig = original_e[team, role, foundation]
                totals = {key: sum(e['originalObservation']['totals'][key] for e in parts) for key in orig['totals'] if key != 'epaSum'}
                if d['status'] in VALID:
                    totals['epaSum'] = d['numerator']
                    if any(totals[k] != orig['totals'][k] for k in totals if k != 'epaSum') or Decimal(totals['epaSum']) != Decimal(orig['totals']['epaSum']): raise ValueError('Legacy EPA totals differ')
                    if set(orig['observed']['includedGameIds']) != set(game_ids) or any(e['originalObservation']['definition'] != orig['definition'] for e in parts): raise ValueError('Legacy EPA definition/scope differs')
                    d['numerator'] = orig['totals']['epaSum']
                eligible = [u for e in parts for u in e['eligibleUnitIds']]
                if len(eligible) != len(set(eligible)): raise ValueError('Repeated EPA eligible units')
                epas.append(dict(foundation=foundation, descriptor=d, display=permission('display', [d]), aggregation=permission('aggregate', [d], d['componentReasonCodes']),
                                 originalObservation=deepcopy(orig), calculatedTotals=totals, eligibleUnitIds=eligible, finiteEpaUnitIds=d['unitIds'], components=parts,
                                 originalReconciliation='MATCHED' if d['status'] in VALID else 'UNAVAILABLE_COMPONENT'))
            joint = [dict(distance=b, kind=k, numerator=sum(u['converted'] for u in attempts if u['distance']==b and u['kind']==k),
                          denominator=sum(u['distance']==b and u['kind']==k for u in attempts), unitIds=[u['id'] for u in attempts if u['distance']==b and u['kind']==k])
                     for b in ('short', 'medium', 'long', 'unknown') for k in ('pass', 'run')]
            productions.append(dict(team=team, perspective=role, label=team+' com a bola' if role=='off' else 'Adversários contra '+team,
                                     opponents=[c['defense'] if role=='off' else c['offense'] for c in components], gameIds=game_ids,
                                     components=components, epa=epas, metrics=metrics, thirdAttempts=attempts, redZoneCampaigns=campaigns, thirdDistanceByType=joint))
        comparisons = {}
        for family in (*FOUNDATIONS, 'third', 'redZone'):
            ds = [next(e['descriptor'] for e in p['epa'] if e['foundation']==family) if family in FOUNDATIONS else p['metrics'][family]['descriptor'] for p in productions]
            comparisons[family] = dict(sideBySide=permission('sideBySide', ds), difference=permission('difference', ds, ['NOT_REQUESTED']), leagueReference=permission('leagueReference', ds, ['TEAM_LEAGUE_REFERENCE_OUT_OF_SCOPE']))
        facts = []
        for family, phrase in [('third', 'conversões em terceiras elegíveis'), ('redZone', 'TDs ofensivos em campanhas de red zone')]:
            m = productions[0]['metrics'][family];d = m['descriptor']
            if m['display']['allowed']:
                text = f"{team}: {d['numerator']}/{d['denominator']} {phrase} nos dois jogos de W1–2." if d['denominator'] else f"{team} não teve campanhas elegíveis de red zone nos dois jogos de W1–2; sem taxa." if family=='redZone' else f"{team} não teve terceiras elegíveis nos dois jogos de W1–2; sem taxa."
                facts.append(dict(text=text, observationId=d['id'], numerator=d['numerator'], denominator=d['denominator'], unitIds=d['unitIds'], permission=m['display']))
        result[team] = dict(contractVersion=VERSION, projectionVersion=PROJECTION, scope=dict(team=team, season=2026, phase='REG', weeks=[1,2], mode='RETROSPECTIVE'),
                            games=games, productions=productions, comparisons=comparisons, facts=facts, definitions=dict(document=(source_root/'definitions.md').read_text()),
                            policy=dict(version='broadcast-team-policy-1.0.0', document=policy), guarantees=GUARANTEES,
                            sources=dict(matchupCollection=SOURCE_PIN, **index['sources'], originalEpaHash=digest((source_root/'sources/observations/observations.json').read_bytes()), originalSituationalHash=digest((source_root/'sources/situational/situational.json').read_bytes())),
                            limitations=['Two observed games, not complete season', 'Opponent production is not independent confirmation', 'No aggregated league reference', 'EPA model and historical availability UNKNOWN'])
    return result
