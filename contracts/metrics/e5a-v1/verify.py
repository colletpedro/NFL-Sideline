"""E5a example model only. Stdlib; no ETL, network, database or environment reads."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / 'contract.json').read_text())
FLAGS = CONTRACT['population']['requiredZeroFlags']
FOUNDATIONS = CONTRACT['statistics']['foundations']
FIELDS = CONTRACT['statistics']['fields']


def instant(value):
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('UTC Z instant required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.microsecond or result.utcoffset().total_seconds() != 0:
        raise ValueError('UTC second precision required')
    return result


def ratio(numerator, denominator):
    if numerator is None or not denominator:
        return None
    return str(Fraction(numerator) / denominator)


def unique(records, key):
    result = {}
    ignored = 0
    for record in records:
        identity = key(record)
        if identity in result:
            if result[identity] != record:
                raise ValueError(f'Conflicting identity: {identity}')
            ignored += 1
        else:
            result[identity] = record
    return [result[k] for k in sorted(result)], ignored


def normalized_plays(rows):
    """Validate the contractual projection; differences in drive are conflicts."""
    projected = []
    for row in rows:
        required = CONTRACT['population']['requiredPlayFields']
        if any(field not in row for field in required):
            raise ValueError('Missing play field')
        r = {field: row[field] for field in required}
        if not r['game_id'] or r['play_id'] is None:
            raise ValueError('Missing play identity')
        try:
            play_id = Decimal(str(r['play_id']))
        except InvalidOperation as exc:
            raise ValueError('Invalid play identity') from exc
        if not play_id.is_finite():
            raise ValueError('Nonfinite play identity')
        r['play_id'] = str(Fraction(play_id))
        if not r['posteam'] or not r['defteam'] or r['posteam'] == r['defteam']:
            raise ValueError('Invalid play teams')
        if r['season_type'] not in ['REG', 'POST']:
            raise ValueError('Unsupported phase')
        for field in FLAGS:
            if r[field] is not None and r[field] not in (0, 1):
                raise ValueError('Invalid filter flag')
        if r['epa'] is not None:
            try:
                r['epa'] = str(Decimal(str(r['epa'])))
            except InvalidOperation as exc:
                raise ValueError('Invalid EPA') from exc
        projected.append(r)
    return unique(projected, lambda r: (r['game_id'], r['play_id']))


def aggregate(rows, team, role):
    """Exact sufficient statistics of one explicit season/phase; complete subset only."""
    if role not in ['off', 'def']:
        raise ValueError('Invalid role')
    rows, duplicates = normalized_plays(rows)
    if len({(r['season'], r['season_type']) for r in rows}) > 1:
        raise ValueError('Mixed season/phase')
    team_field = 'posteam' if role == 'off' else 'defteam'
    stats = {f: dict(eligible_n=0, epa_n=0, epa_sum=None, success_n=0,
                     epa_missing_n=0, epa_nonfinite_n=0) for f in FOUNDATIONS}
    # Fractions sum decimal inputs exactly, including a positive value below Decimal128 precision.
    sums = {f: Fraction(0) for f in FOUNDATIONS}
    excluded = Counter()
    for r in rows:
        if r[team_field] != team:
            continue
        if r['play_type'] not in ['pass', 'run']:
            excluded['OUTSIDE_PLAY_TYPE'] += 1
            continue
        flagged = next((field for field in FLAGS if r[field] == 1), None)
        if flagged:
            excluded[flagged] += 1
            continue
        if any(r[field] is None for field in FLAGS):
            excluded['UNKNOWN_FILTER_FLAGS'] += 1
            continue
        f = 'classified_pass' if r['play_type'] == 'pass' else 'classified_rush'
        epa = None if r['epa'] is None else Decimal(r['epa'])
        for name in ['general', f]:
            s = stats[name]
            s['eligible_n'] += 1
            if epa is None:
                s['epa_missing_n'] += 1
            elif not epa.is_finite():
                s['epa_nonfinite_n'] += 1
            else:
                s['epa_n'] += 1
                sums[name] += Fraction(epa)
                s['success_n'] += int(epa > 0)
    for f, s in stats.items():
        s['epa_sum'] = str(sums[f]) if s['epa_n'] else None
        s['epa_mean'] = ratio(sums[f], s['epa_n'])
        s['success_rate'] = ratio(s['success_n'], s['epa_n'])
        s['frequency'] = ratio(s['eligible_n'], stats['general']['eligible_n'])
    return {'stats': stats, 'excluded_plays': dict(sorted(excluded.items())),
            'duplicate_rows_ignored': duplicates}


def event_reason(g, q):
    if g['game_id'] == q['target_game_id']:
        return 'TARGET_GAME'
    if g['status'] != 'FINAL':
        return 'NOT_FINAL'
    bound = g['event_upper_bound']
    if (not bound or not g['event_bound_evidence']
            or g.get('event_time_basis') not in CONTRACT['temporal']['eventBoundAllowedBases']):
        return 'EVENT_TIME_UNKNOWN'
    if instant(bound) >= instant(q['as_of_instant']):
        return 'EVENT_NOT_BEFORE_CUT'
    if q['temporal_mode'] == 'POINT_IN_TIME':
        if not g['available_at'] or not g['availability_evidence']:
            return 'AVAILABILITY_UNKNOWN'
        if instant(g['available_at']) >= instant(q['as_of_instant']):
            return 'NOT_AVAILABLE_BEFORE_CUT'
        if not g['ingested_at'] or instant(g['ingested_at']) >= instant(q['as_of_instant']):
            return 'NOT_INGESTED_BEFORE_CUT'
    return None


def evaluate(case):
    q = case['query']
    instant(q['as_of_instant'])
    if q['temporal_mode'] not in ['POINT_IN_TIME', 'EVENT_RECONSTRUCTION']:
        raise ValueError('Invalid temporal mode')
    if q['phase'] not in ['REG', 'POST'] or q['role'] not in ['off', 'def']:
        raise ValueError('Invalid scope')
    window = q['window']
    if window not in CONTRACT['windows'] or window == 'recommended':
        raise ValueError('Invalid window')
    if window == 'HISTORICAL_REFERENCE' and (q['season'] >= q['target_season']):
        raise ValueError('Historical season must be explicit and prior')
    calendar = case['calendar']
    if q['temporal_mode'] == 'POINT_IN_TIME':
        if (not calendar['receipt_evidence'] or not calendar['available_at']
                or instant(calendar['available_at']) >= instant(q['as_of_instant'])):
            raise ValueError('Calendar not proven available before cut')
    games, game_duplicates = unique(case['games'], lambda g: g['game_id'])
    all_ids = {g['game_id'] for g in games}
    if any(r['game_id'] not in all_ids for r in case['plays']):
        raise ValueError('Play missing calendar game')
    weeks = None
    if window == 'LAST_3_CALENDAR_WEEKS':
        weeks = list(range(max(1, q['target_week'] - 3), q['target_week']))
    elif window == 'WEEK_OBSERVATION':
        weeks = [q['observation_week']]
    scoped = [g for g in games if g['season'] == q['season'] and g['phase'] == q['phase']
              and q['team'] in g['teams'] and (weeks is None or g['week'] in weeks)]
    excluded = {}
    event_eligible = []
    event_query = {**q, 'temporal_mode': 'EVENT_RECONSTRUCTION'}
    for g in scoped:
        reason = event_reason(g, event_query)
        if reason:
            excluded[g['game_id']] = reason
        else:
            event_eligible.append(g)
    if window == 'LAST_3_GAMES':
        event_eligible = sorted(event_eligible, key=lambda g: (instant(g['event_upper_bound']), g['game_id']))[-3:]
    eligible = []
    for g in event_eligible:
        reason = event_reason(g, q)
        if reason:
            excluded[g['game_id']] = reason
        else:
            eligible.append(g)
    observed, rows, states, metric_games = [], [], {}, set()
    metric_games_by_foundation = {f: set() for f in FOUNDATIONS}
    eligible_play_games = set()
    for g in eligible:
        gp = [r for r in case['plays'] if r['game_id'] == g['game_id']]
        clean, _ = normalized_plays(gp)
        for r in clean:
            if ((r['season'], r['week'], r['season_type']) != (g['season'], g['week'], g['phase'])
                    or set([r['posteam'], r['defteam']]) != set(g['teams'])):
                raise ValueError('Play/calendar mismatch')
        state = g['pbp_status']
        if state not in CONTRACT['coverage']['sourceStates']:
            raise ValueError('Invalid PBP state')
        if state in ['PBP_ABSENT', 'SOURCE_DELAY', 'INGESTION_FAILED'] and not g.get('source_state_evidence'):
            raise ValueError('Missing source state evidence')
        if state == 'COMPLETE':
            if len(clean) > g['expected_unique_rows']:
                raise ValueError('Source row count exceeds manifest')
            if len(clean) < g['expected_unique_rows']:
                state = 'PARTIAL'
        states[g['game_id']] = state
        if state != 'COMPLETE':
            continue
        observed.append(g['game_id'])
        rows.extend(gp)
        game_stats = aggregate(gp, q['team'], q['role'])['stats']
        if game_stats['general']['eligible_n'] > 0:
            eligible_play_games.add(g['game_id'])
        for foundation in FOUNDATIONS:
            if game_stats[foundation]['epa_n'] > 0:
                metric_games_by_foundation[foundation].add(g['game_id'])
        metric_games = metric_games_by_foundation['general']
    output = aggregate(rows, q['team'], q['role'])
    if not observed:
        output['stats'] = {f: {key: None for key in output['stats'][f]} for f in FOUNDATIONS}
    temporal_expectation_known = 'EVENT_TIME_UNKNOWN' not in excluded.values()
    expected = len(event_eligible) if calendar['complete'] and temporal_expectation_known else None
    weekly_states = {}
    for week in weeks or sorted({g['week'] for g in scoped}):
        programmed = [g for g in scoped if g['week'] == week and g['game_id'] != q['target_game_id']]
        closed = week in calendar['closed_weeks']
        if not calendar['complete']:
            weekly_states[str(week)] = 'CALENDAR_UNKNOWN'
        elif not closed:
            weekly_states[str(week)] = 'NOT_YET_CLOSED'
        elif not programmed:
            weekly_states[str(week)] = 'BYE'
        elif any(g['game_id'] not in states for g in programmed):
            weekly_states[str(week)] = 'EVENT_EXCLUDED'
        elif any(states[g['game_id']] == 'PARTIAL' for g in programmed):
            weekly_states[str(week)] = 'PARTIAL'
        elif any(states[g['game_id']] != 'COMPLETE' for g in programmed):
            weekly_states[str(week)] = 'SOURCE_UNKNOWN'
        elif not any(g['game_id'] in metric_games for g in programmed):
            weekly_states[str(week)] = ('NO_EPA_OBSERVATIONS' if any(
                g['game_id'] in eligible_play_games for g in programmed) else 'NO_ELIGIBLE_PLAYS')
        else:
            weekly_states[str(week)] = 'OBSERVED'
    output.update(game_ids=sorted(g['game_id'] for g in eligible),
                  event_eligible_game_ids=sorted(g['game_id'] for g in event_eligible),
                  observed_game_ids=sorted(observed),
                  metric_game_ids_by_foundation={f: sorted(ids) for f, ids in metric_games_by_foundation.items()}, excluded_events=dict(sorted(excluded.items())),
                  game_states=dict(sorted(states.items())), weekly_states=weekly_states,
                  coverage={'expected_games': expected, 'observed_complete_games': len(observed),
                            'metric_observed_games': len(metric_games),
                            'source_ratio': ratio(len(observed), expected),
                            'metric_ratio': ratio(len(metric_games), expected),
                            'metric_by_foundation': {f: {'observed_games': len(ids),
                                'ratio': ratio(len(ids), expected)} for f, ids in metric_games_by_foundation.items()}},
                  origin='HISTORICAL_REFERENCE' if window == 'HISTORICAL_REFERENCE' else 'CURRENT',
                  historical_availability='PROVEN' if q['temporal_mode'] == 'POINT_IN_TIME' else 'UNKNOWN_OR_NOT_PROVEN',
                  duplicate_games_ignored=game_duplicates)
    s = output['stats']['general']
    output['general_integrity_eligible'] = bool(
        expected and len(observed) == expected and s['epa_n'] and not s['epa_missing_n']
        and not s['epa_nonfinite_n'] and not output['excluded_plays'].get('UNKNOWN_FILTER_FLAGS'))
    output['metrics'] = {}
    for m in CONTRACT['metrics']:
        if m['role'] != q['role']:
            continue
        f = output['stats'][m['foundation']]
        if '.epa.' in m['id']:
            value = f['epa_mean']
        elif '.success_rate.' in m['id']:
            value = f['success_rate']
        elif '.volume.' in m['id']:
            value = f['eligible_n']
        else:
            value = f['frequency']
        output['metrics'][m['id']] = value
    return output



def comparison_eligible(left_case, right_case, foundation='general'):
    """Descriptive pair eligibility, independent of legacy editorial rules."""
    a, b = evaluate(left_case), evaluate(right_case)
    qa, qb = left_case['query'], right_case['query']
    scope = ['season', 'phase', 'target_game_id', 'target_season', 'target_week',
             'as_of_instant', 'temporal_mode', 'window', 'observation_week']
    if any(qa.get(key) != qb.get(key) for key in scope) or a['origin'] != b['origin']:
        return False
    if left_case['calendar'] != right_case['calendar']:
        return False
    for output in [a, b]:
        c, s = output['coverage'], output['stats'][foundation]
        if (not c['expected_games'] or c['observed_complete_games'] != c['expected_games']
                or not s['epa_n'] or s['epa_missing_n'] or s['epa_nonfinite_n']
                or output['excluded_plays'].get('UNKNOWN_FILTER_FLAGS')):
            return False
    return True


def check_expected(actual, expected, path='result'):
    """Golden expectations are hand-authored subsets, never generated from the model."""
    if isinstance(expected, dict):
        for key, value in expected.items():
            if key not in actual:
                raise ValueError(f'{path}.{key}: missing')
            check_expected(actual[key], value, f'{path}.{key}')
    elif actual != expected:
        raise ValueError(f'{path}: expected {expected!r}, got {actual!r}')


def verify_cases():
    cases = json.loads((ROOT / 'fixtures/cases.json').read_text())['cases']
    for case in cases:
        if 'expected_error' in case:
            try:
                evaluate(case)
            except ValueError as exc:
                if case['expected_error'] not in str(exc):
                    raise
            else:
                raise ValueError(f"{case['id']}: expected rejection")
        else:
            check_expected(evaluate(case), case['expected'], case['id'])
    return len(cases)


if __name__ == '__main__':
    print(json.dumps({'package': CONTRACT['packageId'], 'version': CONTRACT['version'],
                      'golden_cases_passed': verify_cases(), 'production_implemented': False}))
