"""Review regressions and manual expectations; no acquisition or external calls."""
from copy import deepcopy
import random

import pytest

from nfl_sideline_etl.temporal_metrics.core import select, comparison, requested_period
from test_temporal_metrics import (package, query, revision, calc, proof, block,
                                  append_evidence, reconstruction, clone_state,
                                  CUTOFF, EARLY, LATE)


def season(result):
    return block(result, 'SEASON_TO_CUTOFF')


def aggregate_pair(p, lq, rq, foundation='general'):
    l, r = select(p, lq), select(p, rq)
    lb, rb = l['blocks'][0], r['blocks'][0]
    la, ra = [next(a for a in b['aggregates'] if a['role'] == 'off' and a['foundation'] == foundation)
              for b in (lb, rb)]
    assert la['comparisonEligible'] and ra['comparisonEligible']
    return la, ra, lb, rb, l['request'], r['request']


def clean_beta(p):
    # Synthetic sufficient sums stay unchanged; remove only EPA-missing plays
    # from eligible counts symmetrically, preserving all 12 reconciled groups.
    cal = revision(p, 'calendar-v1')
    cal['payload']['games'] = [g for g in cal['payload']['games'] if g['game_id'] != 'gap']
    p['resources'] = [r for r in p['resources'] if r['revision_id'] != 'state:gap']
    for c in p['calculations']:
        if c['game']['game_id'] == 'beta':
            for row in c['statistics']:
                row['eligible_n'] -= row['epa_missing_n']
                row['epa_missing_n'] = 0


@pytest.mark.parametrize('target_week', [1, 4, 8, 18, 30])
def test_excluded_target_open_week_does_not_change_prior_coverage(package, query, target_week):
    q = {**query, 'windows': ['SEASON_TO_CUTOFF']}
    before = season(select(package, q))
    next(g for g in revision(package, 'calendar-v1')['payload']['games'] if g['game_id'] == 'target')['week'] = target_week
    after = season(select(package, q))
    assert before['coverage']['expectedGames'] == after['coverage']['expectedGames'] == 3
    assert after['coverage']['knownEligibleGameIds'] == ['alpha', 'beta', 'gap']
    assert after['coverage']['uncertainGameIds'] == []
    assert after['coverage']['expectationFailures'] == []
    assert after['coverage']['sourceRatio']['exact'] == '2/3'
    assert after['aggregates'] == before['aggregates']
    assert after['requestedPeriod'] == before['requestedPeriod']


def add_future(p, week, lower=None):
    p['inputVersion'] = 'metrics-temporal-input-v2'
    cal = revision(p, 'calendar-v1')
    gid = 'future-' + str(week)
    g = {**cal['payload']['games'][0], 'game_id': gid, 'week': week}
    cal['payload']['games'].append(g)
    state = clone_state(p, 'alpha', 'state:' + gid, EARLY)
    state['payload'].update(game_id=gid, status='SCHEDULED', event_upper_bound=None, kickoff=None)
    if lower:
        state['payload']['event_lower_bound'] = append_evidence(p, 'EVENT_START_LOWER_BOUND', state['revision_id'], lower, LATE)
    return gid, state


def retro_with(p, q):
    q = reconstruction(q)
    for r in p['resources']:
        if r['kind'] == 'STATE' and r['payload']['game_id'].startswith('future-'):
            key = 'calendar-v1/' + r['payload']['game_id']
            q['retrospective']['states'][key] = r['revision_id']
            q['retrospective']['calculations'][key] = None
    return q


@pytest.mark.parametrize('count', [1, 3, 14])
def test_complete_future_calendar_with_proven_outside_events(package, query, count):
    ids = [add_future(package, w, CUTOFF)[0] for w in range(4, 4 + count)]
    q = retro_with(package, {**query, 'windows': ['SEASON_TO_CUTOFF']})
    b = season(select(package, q))
    assert b['coverage']['expectedGames'] == 3
    assert b['coverage']['outsideCutoffGameIds'] == sorted(ids)
    assert b['coverage']['uncertainGameIds'] == []
    assert b['coverage']['sourceRatio']['exact'] == '2/3'
    assert b['coverage']['expectationFailures'] == []
    assert all(w['status'] == 'NOT_YET_CLOSED' for w in b['weeklyStates'] if w['week'] >= 4)


@pytest.mark.parametrize('status', ['SCHEDULED', 'POSTPONED', 'UNKNOWN'])
def test_future_week_or_scheduled_status_alone_is_uncertain(package, query, status):
    gid, s = add_future(package, 18)
    s['payload']['status'] = status
    s['payload']['kickoff'] = append_evidence(package, 'METADATA', s['revision_id'], LATE)
    b = season(select(package, query))
    assert b['coverage']['expectedGames'] is None
    assert b['coverage']['uncertainGameIds'] == [gid]
    assert b['coverage']['outsideCutoffGameIds'] == []
    assert b['coverage']['expectationFailures'] == [{'reason': 'EVENT_EXPECTATION_UNCERTAIN', 'gameIds': [gid]}]


@pytest.mark.parametrize('bound', [CUTOFF, '2026-09-28T12:00:00.000000001Z', LATE])
def test_upper_bound_at_or_after_cut_does_not_prove_future(package, query, bound):
    state = revision(package, 'state:alpha')
    state['payload']['event_upper_bound'] = append_evidence(package, 'EVENT_END_BOUND', state['revision_id'], bound, LATE)
    b = season(select(package, reconstruction(query)))
    assert b['coverage']['expectedGames'] is None
    assert b['coverage']['uncertainGameIds'] == ['alpha']
    assert b['coverage']['outsideCutoffGameIds'] == []
    assert b['coverage']['knownEligibleGameIds'] == ['beta', 'gap']


@pytest.mark.parametrize('bound,outside', [('2026-09-28T11:59:59.999999999Z', False),
                                         (CUTOFF, True), ('2026-09-28T09:00:00-03:00', True),
                                         ('2026-09-28T12:00:00.000000001Z', True)])
def test_lower_bound_exact_precision_and_mode_separation(package, query, bound, outside):
    gid, _ = add_future(package, 8, bound)
    pit = season(select(package, query))
    assert pit['coverage']['expectedGames'] is None
    assert pit['coverage']['uncertainGameIds'] == [gid]
    r = select(package, retro_with(package, query))
    b = season(r)
    assert b['coverage']['expectedGames'] == (3 if outside else None)
    assert b['coverage']['outsideCutoffGameIds'] == ([gid] if outside else [])
    assert r['guarantees']['knowledgeAtCutoff'] == 'NOT_DEMONSTRATED'
    assert r['guarantees']['postCutoffEvidenceIds']


def test_future_reconstruction_requires_explicit_state(package, query):
    add_future(package, 8, CUTOFF)
    with pytest.raises(ValueError, match='Explicit retrospective selection required'):
        select(package, reconstruction(query))


def test_eligible_missing_pbp_remains_in_denominator(package, query):
    package['calculations'] = [c for c in package['calculations'] if c['game']['game_id'] != 'alpha']
    b = season(select(package, query))
    assert b['coverage']['expectedGames'] == 3
    assert b['coverage']['sourceRatio']['exact'] == '1/3'
    assert b['coverage']['gaps'] == [
        {'gameId': 'alpha', 'reason': 'SOURCE_UNKNOWN', 'details': ['SOURCE_UNKNOWN']},
        {'gameId': 'gap', 'reason': 'SOURCE_UNKNOWN', 'details': ['SOURCE_UNKNOWN']}]


@pytest.mark.parametrize('complete', [None, False])
def test_incomplete_calendar_cannot_certify_expectation(package, query, complete):
    cal = revision(package, 'calendar-v1')
    cal['payload']['complete'] = None if complete is None else append_evidence(package, 'CALENDAR_COMPLETE', cal['revision_id'], False)
    b = season(select(package, query))
    assert b['coverage']['expectedGames'] is None
    assert b['coverage']['knownEligibleGameIds'] == ['alpha', 'beta', 'gap']
    assert b['coverage']['expectationFailures'] == [{'reason': 'CALENDAR_COMPLETENESS_UNPROVEN'}]


def test_open_periods_preserved_for_weekly_but_not_event_windows(package, query):
    revision(package, 'calendar-v1')['payload']['closed_weeks'] = []
    result = select(package, query)
    assert season(result)['coverage']['expectedGames'] == 3
    for w in ('WEEK_OBSERVATION', 'LAST_3_CALENDAR_WEEKS'):
        b = block(result, w)
        assert b['coverage']['expectedGames'] is None
        assert b['coverage']['expectationFailures'] == [{'reason': 'PERIOD_NOT_CLOSED', 'weeks': b['requestedWeeks']}]


def test_rejected_reschedule_preserves_frozen_selected_events(package, query):
    before = select(package, query)
    cal = deepcopy(revision(package, 'calendar-v1'))
    cal['revision_id'] = 'calendar-rescheduled'
    next(g for g in cal['payload']['games'] if g['game_id'] == 'alpha')['week'] = 18
    cal['payload']['complete'] = append_evidence(package, 'CALENDAR_COMPLETE', cal['revision_id'], True, LATE)
    cal['payload']['closed_weeks'] = []
    for key in ('available_at', 'ingested_at'):
        cal[key] = append_evidence(package, 'SYSTEM_INGESTION', cal['revision_id'], LATE, LATE)
    package['resources'].append(cal)
    after = select(package, query)
    assert season(after)['coverage']['expectedGames'] == 3
    assert after['result_id'] == before['result_id']
    assert after['audit_id'] != before['audit_id']


def test_historical_event_expectation_does_not_require_all_periods_closed(package, query):
    # Explicit historic phase/calendar/state with no metrics (not fallback).
    cal = deepcopy(revision(package, 'calendar-v1'))
    cal['revision_id'] = 'history'
    game = {**cal['payload']['games'][0], 'game_id': 'old', 'season': 2025, 'phase': 'POST', 'round': 'WC'}
    cal['payload'].update(season=2025, phase='POST', games=[game], closed_weeks=[])
    for key in ('available_at', 'ingested_at'):
        cal[key] = append_evidence(package, 'SYSTEM_INGESTION', 'history', EARLY)
    cal['payload']['complete'] = append_evidence(package, 'CALENDAR_COMPLETE', 'history', True)
    package['resources'].append(cal)
    state = clone_state(package, 'alpha', 'state:old', EARLY)
    state['dependencies'] = ['history']
    state['payload'].update(game_id='old', calendar_revision_id='history')
    q = {**query, 'windows': ['HISTORICAL_REFERENCE'], 'historicalSeason': 2025, 'historicalPhase': 'POST'}
    b = block(select(package, q), 'HISTORICAL_REFERENCE')
    assert b['coverage']['expectedGames'] == 1
    assert b['coverage']['sourceRatio']['exact'] == '0'
    assert b['aggregates'] == []
    assert b['requestedPeriod'] == {'window': 'HISTORICAL_REFERENCE', 'season': 2025, 'phase': 'POST',
                                    'origin': 'HISTORICAL_REFERENCE', 'mode': 'POINT_IN_TIME',
                                    'cutoff': CUTOFF, 'selection': {'eventEndBefore': CUTOFF}}
    state['payload']['event_upper_bound'] = None
    b = block(select(package, q), 'HISTORICAL_REFERENCE')
    assert b['coverage']['expectedGames'] is None
    assert b['coverage']['uncertainGameIds'] == ['old']


def test_review_different_recent_windows(package, query):
    q = {**query, 'windows': ['LAST_3_CALENDAR_WEEKS'], 'targetWeek': 2}
    args = aggregate_pair(package, q, {**q, 'targetWeek': 3})
    assert args[0]['epa']['exact'] == args[1]['epa']['exact'] == '1/2'
    assert args[2]['requestedWeeks'] == [1] and args[3]['requestedWeeks'] == [1, 2]
    result = comparison(*args)
    assert result['failures'] == ['MISMATCH_REQUESTED_PERIOD']
    assert not result['comparisonEligible']
    assert result['left'] == args[0] and result['right'] == args[1]


def test_review_different_week_observations(package, query):
    clean_beta(package)
    q = {**query, 'windows': ['WEEK_OBSERVATION'], 'week': 1}
    args = aggregate_pair(package, q, {**q, 'week': 3}, 'classified_pass')
    assert args[0]['epa']['exact'] == '1/2'
    assert args[1]['epa']['exact'] == '-1/3'
    result = comparison(*args)
    assert result['failures'] == ['MISMATCH_REQUESTED_PERIOD']
    assert not result['comparisonEligible']
    assert result['left']['epa']['exact'] == '1/2' and result['right']['epa']['exact'] == '-1/3'


def test_same_requested_period_distinct_teams_and_games(package, query):
    # Team A plays alpha W1; construct team C game with distinct frozen ID.
    cal = revision(package, 'calendar-v1')
    g = {**cal['payload']['games'][0], 'game_id': 'other', 'home_team': 'C', 'away_team': 'D', 'week': 1}
    cal['payload']['games'].append(g)
    state = clone_state(package, 'alpha', 'state:other', EARLY)
    state['payload']['game_id'] = 'other'
    c = deepcopy(calc(package))
    c.update(revision_id='revision:other', calculation_id='calc:other', coverage_revision_id='coverage:other', game=g)
    for row in c['statistics']:
        row['team'] = {'A': 'C', 'B': 'D'}[row['team']]
    c['completeness'] = append_evidence(package, 'PBP_COMPLETE', c['coverage_revision_id'], 'COMPLETE')
    c['model'] = append_evidence(package, 'METADATA', c['calculation_id'], 'model-v1')
    package['calculations'].append(c)
    q = {**query, 'windows': ['WEEK_OBSERVATION'], 'week': 1}
    args = aggregate_pair(package, {**q, 'team': 'A'}, {**q, 'team': 'C'})
    assert args[0]['gameIds'] == ['alpha'] and args[1]['gameIds'] == ['other']
    assert comparison(*args)['comparisonEligible']


def test_signature_ignores_bye_missing_source_and_actual_weeks(package, query):
    before = select(package, query)
    package['calculations'] = [c for c in package['calculations'] if c['game']['game_id'] != 'beta']
    after = select(package, query)
    for name in query['windows']:
        assert block(before, name)['requestedPeriod'] == block(after, name)['requestedPeriod']
    assert block(after)['requestedWeeks'] == [1, 2, 3]
    assert block(after)['actualWeeks'] == [1]
    assert block(before)['actualWeeks'] == [1, 3]


@pytest.mark.parametrize('window', ['WEEK_OBSERVATION', 'LAST_3_CALENDAR_WEEKS', 'SEASON_TO_CUTOFF', 'HISTORICAL_REFERENCE'])
def test_equivalent_signatures_offsets_and_unrelated_parameters(query, window):
    q = {**query, 'historicalSeason': 2025, 'historicalPhase': 'POST'}
    b = {'window': window, 'season': 2025 if window == 'HISTORICAL_REFERENCE' else 2026,
         'phase': 'POST' if window == 'HISTORICAL_REFERENCE' else 'REG',
         'origin': 'HISTORICAL_REFERENCE' if window == 'HISTORICAL_REFERENCE' else 'CURRENT',
         'actualWeeks': [1], 'requestedWeeks': [3, 2, 1, 1]}
    other = {**b, 'requestedWeeks': [1, 2, 3], 'actualWeeks': [3]}
    eq = {**q, 'asOfInstant': '2026-09-28T09:00:00-03:00', 'team': 'C', 'targetGameId': 'other'}
    if window != 'LAST_3_CALENDAR_WEEKS':
        eq['targetWeek'] = 18
    if window != 'WEEK_OBSERVATION':
        eq['week'] = 99
    assert requested_period(b, q) == requested_period(other, eq)


def test_comparison_accepts_equivalent_cutoffs(package, query):
    q = {**query, 'windows': ['WEEK_OBSERVATION'], 'week': 1}
    args = list(aggregate_pair(package, q, q))
    args[-1] = {**args[-1], 'asOfInstant': '2026-09-28T09:00:00-03:00'}
    assert comparison(*args)['comparisonEligible']


@pytest.mark.parametrize('invalid', ['legacy', 'mismatch', 'untrusted', 'dependency', 'future_prediction', 'contradiction'])
def test_lower_bound_proof_cannot_be_fabricated_or_misbound(package, query, invalid):
    gid, s = add_future(package, 8, CUTOFF)
    env = s['payload']['event_lower_bound']
    e = proof(package, env['evidence_id'])
    if invalid == 'legacy':
        package['inputVersion'] = 'metrics-temporal-input-v1'
        with pytest.raises(ValueError):
            select(package, query)
        return
    if invalid == 'contradiction':
        s['payload']['status'] = 'FINAL'
        s['payload']['event_upper_bound'] = append_evidence(package, 'EVENT_END_BOUND', s['revision_id'], EARLY, LATE)
        with pytest.raises(ValueError, match='EVENT_BOUNDS_CONFLICT'):
            select(package, retro_with(package, query))
        return
    if invalid == 'mismatch': e['subject_id'] = 'state:alpha'
    if invalid == 'untrusted': e['origin'] = 'untrusted'
    if invalid == 'future_prediction': e['recorded_at'] = EARLY
    if invalid == 'dependency': e['dependencies'] = [calc(package, 'alpha-corrected')['pbp_revision_id']]
    r = select(package, query if invalid == 'dependency' else retro_with(package, query))
    b = season(r)
    assert b['coverage']['expectedGames'] is None
    assert b['coverage']['outsideCutoffGameIds'] == []
    assert gid in b['coverage']['uncertainGameIds']


def test_permutation_general_property_with_open_target(package, query):
    next(g for g in revision(package, 'calendar-v1')['payload']['games'] if g['game_id'] == 'target')['week'] = 18
    before = select(package, query)
    rng = random.Random(4103)
    for _ in range(12):
        for key in ('resources', 'evidence', 'calculations'):
            rng.shuffle(package[key])
        rng.shuffle(revision(package, 'calendar-v1')['payload']['games'])
        after = select(package, query)
        assert after['result_id'] == before['result_id']
        assert season(after)['coverage']['expectedGames'] == 3


@pytest.mark.parametrize('dimension,value', [('populationVersion','other'), ('definitionVersion','other'),
    ('role','def'), ('foundation','classified_pass'), ('model','other'), ('scope','AUDITABLE_SUBSET_UNKNOWN')])
def test_existing_aggregate_compatibility_checks_preserved(package, query, dimension, value):
    q = {**query, 'windows': ['WEEK_OBSERVATION'], 'week': 1}
    args = list(aggregate_pair(package, q, q))
    args[1] = {**args[1], dimension: value}
    result = comparison(*args)
    assert 'MISMATCH_' + dimension in result['failures']
    assert not result['comparisonEligible']
    assert result['right'][dimension] == value


@pytest.mark.parametrize('dimension,value', [('season',2025), ('phase','POST'),
                                            ('origin','HISTORICAL_REFERENCE'), ('window','SEASON_TO_CUTOFF')])
def test_existing_block_compatibility_checks_preserved(package, query, dimension, value):
    q = {**query, 'windows': ['WEEK_OBSERVATION'], 'week': 1}
    args = list(aggregate_pair(package, q, q))
    args[3] = {**args[3], dimension: value}
    result = comparison(*args)
    assert 'MISMATCH_' + dimension in result['failures']
    assert 'MISMATCH_REQUESTED_PERIOD' in result['failures']


@pytest.mark.parametrize('dimension,value', [('mode','EVENT_RECONSTRUCTION'),
                                           ('asOfInstant','2026-09-28T13:00:00Z')])
def test_existing_knowledge_scope_compatibility_preserved(package, query, dimension, value):
    q = {**query, 'windows': ['WEEK_OBSERVATION'], 'week': 1}
    args = list(aggregate_pair(package, q, q))
    args[-1] = {**args[-1], dimension: value}
    result = comparison(*args)
    assert 'MISMATCH_' + dimension in result['failures']
    assert 'MISMATCH_REQUESTED_PERIOD' in result['failures']


def test_empty_recent_interval_and_date_equivalence(query):
    b = {'window':'LAST_3_CALENDAR_WEEKS','season':2026,'phase':'REG','origin':'CURRENT'}
    q = {**query, 'targetWeek': 1, 'asOfInstant': '2026-09-28T00:00:00Z'}
    date = {k:v for k,v in q.items() if k != 'asOfInstant'}
    date['asOfDate'] = '2026-09-28'
    assert requested_period(b, q) == requested_period(b, date)
    assert requested_period(b, q)['selection'] == {'weeks': []}
    assert requested_period(b, q) != requested_period(b, {**q, 'targetWeek': 2})


@pytest.mark.parametrize('week', [4, 9, 18])
def test_future_calendar_period_for_other_team_cannot_invalidate_coverage(package, query, week):
    cal = revision(package, 'calendar-v1')
    cal['payload']['games'].append({**cal['payload']['games'][0], 'game_id': 'other-future',
                                   'home_team':'C','away_team':'D','week':week})
    b = season(select(package, query))
    assert b['coverage']['expectedGames'] == 3
    assert b['coverage']['expectationFailures'] == []
    assert b['coverage']['knownEligibleGameIds'] == ['alpha','beta','gap']
    assert b['coverage']['sourceRatio']['exact'] == '2/3'


def test_cli_v2_future_example_publishes_version_and_auditable_ids(package, query, tmp_path):
    import json
    from nfl_sideline_etl.temporal_metrics.__main__ import main
    gid, _ = add_future(package, 18, CUTOFF)
    q = retro_with(package, query)
    input_path, retro_path, output = tmp_path/'v2.json', tmp_path/'choices.json', tmp_path/'result'
    input_path.write_text(json.dumps(package))
    retro_path.write_text(json.dumps(q['retrospective']))
    assert main(['--input',str(input_path),'--season','2026','--phase','REG','--team','A',
                 '--target-game-id','target','--target-week','4','--window','SEASON_TO_CUTOFF',
                 '--as-of-instant',CUTOFF,'--mode','EVENT_RECONSTRUCTION','--retrospective',str(retro_path),
                 '--derived-at',LATE,'--output',str(output)]) == 0
    result = json.loads((output/'result.json').read_text())
    marker = json.loads((output/'COMPLETED.json').read_text())
    assert marker['resultVersion'] == result['resultVersion'] == 'metrics-temporal-result-v2'
    assert result['algorithmVersion'] == 'metrics-temporal-1.0.1'
    assert season(result)['coverage']['expectedGames'] == 3
    assert season(result)['coverage']['outsideCutoffGameIds'] == [gid]
    assert result['guarantees']['postCutoffEvidenceIds']
    assert marker['result_id'] == result['result_id'] and marker['audit_id'] == result['audit_id']
