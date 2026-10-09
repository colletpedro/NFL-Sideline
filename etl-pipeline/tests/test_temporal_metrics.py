"""Independent hand ledger + counterfactual selection/coverage properties."""
import base64
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys

import pytest

from nfl_sideline_etl.offline_metrics.artifact import identity, json_bytes
from nfl_sideline_etl.temporal_metrics.core import select, comparison
from nfl_sideline_etl.temporal_metrics.times import instant, eastern_kickoff
from nfl_sideline_etl.temporal_metrics.__main__ import main, publish

FIXTURES = Path(__file__).parent / 'fixtures' / 'temporal_metrics'
CUTOFF = '2026-09-28T12:00:00Z'
EARLY = '2026-09-01T00:00:00Z'
LATE = '2026-10-01T00:00:00Z'


@pytest.fixture
def package():
    return json.loads((FIXTURES / 'package.json').read_text())


@pytest.fixture
def query():
    return json.loads((FIXTURES / 'request-pit.json').read_text())


def revision(package, rid):
    return next(r for r in package['resources'] if r['revision_id'] == rid)


def calc(package, label='alpha-old'):
    return next(c for c in package['calculations'] if c['revision_id'] == 'revision:' + label)


def proof(package, eid):
    return next(e for e in package['evidence'] if e['evidence_id'] == eid)


def set_time(package, r, key, value):
    env = r[key]
    env['value'] = value
    for e in package['evidence']:
        if e['evidence_id'] == env['evidence_id']:
            e['recorded_at'] = value
            e['value'] = value
            if 'receipt' in e:
                receipt = e['receipt']
                receipt['observed_at'] = value
                receipt['receipt_id'] = identity({k: v for k, v in receipt.items() if k != 'receipt_id'})


def change_bound(package, gid, value, received=LATE):
    state = revision(package, 'state:' + gid)
    env = state['payload']['event_upper_bound']
    env['value'] = value
    e = proof(package, env['evidence_id'])
    e['value'] = value
    e['recorded_at'] = received


def reconstruction(query):
    result = deepcopy(query)
    result['mode'] = 'EVENT_RECONSTRUCTION'
    result['retrospective'] = json.loads((FIXTURES / 'retrospective.json').read_text())
    return result


def block(result, window='LAST_3_CALENDAR_WEEKS'):
    return next(b for b in result['blocks'] if b['window'] == window)


def event(result, gid):
    return next(e for e in block(result)['events'] if e['game']['game_id'] == gid)


def aggregate(result, foundation='general', role='off', scope='COMPLETE', model='model-v1'):
    return next(a for a in block(result)['aggregates'] if (a['foundation'], a['role'], a['scope'], a['model']) == (foundation, role, scope, model))


def delete_beta(package):
    package['calculations'] = [c for c in package['calculations'] if c['game']['game_id'] != 'beta']


def test_manual_ledger_two_modes(package, query):
    ledger = json.loads((FIXTURES / 'ledger.json').read_text())
    before = deepcopy(package)
    for mode, mode_query in [('pit', query), ('reconstruction', reconstruction(query))]:
        result = select(package, mode_query)
        expected = ledger[mode]
        for gid, rid in expected['selected'].items():
            assert event(result, gid)['calculationRevisionId'] == rid
        a = aggregate(result)
        assert a['sums']['epa_sum'] == expected['epa_sum']
        assert a['epa']['exact'] == expected['epa']
        assert block(result)['coverage']['expectedGames'] == 3
        assert block(result)['coverage']['sourceRatio']['exact'] == '2/3'
        assert event(result, 'target')['reasons'] == ['TARGET_GAME_EXCLUDED']
        assert event(result, 'gap')['reasons'] == ['SOURCE_UNKNOWN']
    pit = select(package, query)
    assert aggregate(pit)['successRate']['exact'] == ledger['pit']['successRate']
    assert aggregate(pit, 'classified_pass')['frequency']['exact'] == ledger['pit']['passFrequency']
    assert aggregate(pit, 'classified_rush')['frequency']['exact'] == ledger['pit']['rushFrequency']
    assert aggregate(pit)['sums']['eligible_n'] == 8
    assert aggregate(pit)['sums']['epa_n'] == 7
    assert set(aggregate(pit)['comparisonFailures']) == {'INCOMPLETE_SOURCE_COVERAGE', 'EPA_INCOMPLETE'}
    assert package == before


@pytest.mark.parametrize('bound,eligible', [
    ('2026-09-28T11:59:59.999999999Z', True), (CUTOFF, False),
    ('2026-09-28T12:00:00.000000001Z', False), ('2026-09-28T09:00:00-03:00', False)])
def test_event_exclusive_and_fractional_precision(package, query, bound, eligible):
    change_bound(package, 'alpha', bound)
    result = select(package, reconstruction(query))
    assert event(result, 'alpha')['eventEligible'] is eligible
    if not eligible:
        assert event(result, 'alpha')['reasons'] == ['EVENT_NOT_BEFORE_CUTOFF']


@pytest.mark.parametrize('key', ['available_at', 'ingested_at'])
@pytest.mark.parametrize('value,selected', [('2026-09-28T11:59:59.999999999Z', True), (CUTOFF, False), ('2026-09-28T12:00:00.000000001Z', False)])
def test_source_limits(package, query, key, value, selected):
    c = calc(package)
    source = revision(package, revision(package, c['pbp_revision_id'])['dependencies'][0])
    set_time(package, source, key, value)
    result = select(package, query)
    assert (event(result, 'alpha')['calculationRevisionId'] is not None) is selected
    assert block(result)['coverage']['expectedGames'] == 3
    if not selected:
        assert block(result)['coverage']['sourceRatio']['exact'] == '1/3'


def test_pregame_with_without_kickoff_and_wrong_target_week(package, query):
    result = select(package, query)
    assert result['pregame']['timeStatus'] == 'PREGAME_TIME_VERIFIED_BY_POLICY'
    state = revision(package, 'state:target')
    state['payload']['kickoff'] = None
    result = select(package, query)
    assert result['pregame']['timeStatus'] == 'PREGAME_TIME_UNVERIFIED'
    # Calendar calls target W1/FINAL, while explicit targetWeek is W4.
    assert event(result, 'target')['reasons'] == ['TARGET_GAME_EXCLUDED']


def test_after_proven_kickoff_fails(package, query):
    query['asOfInstant'] = '2026-09-28T16:00:01Z'
    with pytest.raises(ValueError, match='PREGAME_CUTOFF_AFTER_KICKOFF'):
        select(package, query)


def test_at_kickoff_is_pregame(package, query):
    query['asOfInstant'] = '2026-09-28T16:00:00Z'
    assert select(package, query)['pregame']['timeStatus'] == 'PREGAME_TIME_VERIFIED_BY_POLICY'


def test_same_week_distinct_events_and_week_rollup(package, query):
    result = select(package, query)
    week = block(result, 'WEEK_OBSERVATION')
    assert set(week['scheduledGameIds']) == {'beta', 'gap'}
    assert week['coverage']['expectedGames'] == 2
    assert week['coverage']['sourceRatio']['exact'] == '1/2'
    # Same-day bound does not collapse game identity.
    change_bound(package, 'alpha', '2026-09-21T23:00:00Z', '2026-09-22T00:00:00Z')
    assert block(select(package, query))['coverage']['expectedGames'] == 3


def test_later_corrected_and_composite_revisions_rejected(package, query):
    result = select(package, query)
    rejected = {r['revision_id']: r['reasons'] for r in result['revisionDecisions'] if not r['selected']}
    assert any('NOT_KNOWN_AT_CUTOFF' in r['reason'] for r in rejected['revision:alpha-corrected'])
    assert any('NOT_KNOWN_AT_CUTOFF' in r['reason'] for r in rejected['revision:beta-composed'])
    assert event(result, 'beta')['calculationRevisionId'] == 'revision:beta'
    assert aggregate(result)['sums']['epa_sum'] == '0.5'


def test_corrected_calendar_after_cutoff_cannot_contaminate(package, query):
    old = revision(package, 'calendar-v1')
    new = deepcopy(old)
    new['revision_id'] = 'calendar-v2'
    new['payload']['games'][0]['week'] = 18
    for key in ('available_at', 'ingested_at'):
        new[key] = append_evidence(package, 'SYSTEM_INGESTION', new['revision_id'], LATE, LATE)
    package['resources'].append(new)
    before = select(package, query)
    assert block(before)['calendarRevisionId'] == old['revision_id']
    assert event(before, 'alpha')['eventEligible']
    assert any(r['revision_id'] == 'calendar-v2' and not r['selected'] for r in before['revisionDecisions'])


def test_corrected_state_after_cutoff_cannot_contaminate(package, query):
    old = revision(package, 'state:alpha')
    new = deepcopy(old)
    new.update(revision_id='state:alpha-corrected')
    for key in ('available_at', 'ingested_at'):
        new[key] = append_evidence(package, 'SYSTEM_INGESTION', new['revision_id'], LATE, LATE)
    new['payload']['status'] = 'POSTPONED'
    package['resources'].append(new)
    assert event(select(package, query), 'alpha')['stateRevisionId'] == old['revision_id']


def test_metadata_received_after_cutoff_blocks_calculation(package, query):
    late = {'revision_id': 'metadata-late', 'kind': 'METADATA', 'dependencies': [], 'available_at': None, 'ingested_at': None, 'payload': {'origin': 'synthetic', 'document': {'model': 'changed'}}}
    package['resources'].append(late)
    calc(package)['metadata_revision_ids'] = ['metadata-late']
    result = select(package, query)
    assert event(result, 'alpha')['calculationId'] is None
    assert block(result)['coverage']['expectedGames'] == 3


def test_evidence_received_after_cutoff_blocks_calculation(package, query):
    proof(package, calc(package)['completeness']['evidence_id'])['recorded_at'] = LATE
    result = select(package, query)
    assert event(result, 'alpha')['calculationId'] is None
    assert any(r['reason'] == 'EVIDENCE_NOT_KNOWN_AT_CUTOFF' for d in result['revisionDecisions'] for r in d['reasons'])


def test_receipt_does_not_prove_manifest_earlier_availability(package, query):
    c = calc(package)
    source = revision(package, revision(package, c['pbp_revision_id'])['dependencies'][0])
    set_time(package, source, 'available_at', LATE)
    source['available_at']['value'] = EARLY
    result = select(package, query)
    assert event(result, 'alpha')['calculationId'] is None
    assert any('DECLARATION_UNPROVEN' in r['reason'] for d in result['revisionDecisions'] for r in d['reasons'])


def test_hash_and_envelope_do_not_prove_time_or_completeness(package, query):
    state = revision(package, 'state:alpha')
    proof(package, state['payload']['event_upper_bound']['evidence_id'])['kind'] = 'HASH_CHECK'
    c = calc(package, 'beta')
    proof(package, c['completeness']['evidence_id'])['origin'] = 'external-untrusted'
    result = select(package, query)
    assert event(result, 'alpha')['eventUncertain']
    assert block(result)['coverage']['expectedGames'] is None
    assert event(result, 'beta')['completeness'] == 'UNKNOWN'
    assert aggregate(result, scope='AUDITABLE_SUBSET_UNKNOWN')['volume'] == 6


def test_retrospective_requires_explicit_map(package, query):
    query['mode'] = 'EVENT_RECONSTRUCTION'
    with pytest.raises(ValueError, match='Invalid fields'):
        select(package, query)
    query = reconstruction(query)
    query['retrospective']['calendars'].clear()
    with pytest.raises(ValueError, match='Explicit retrospective'):
        select(package, query)


def test_revision_tie_is_id_only(package, query):
    new = deepcopy(calc(package))
    new['revision_id'] = 'revision:zz-tie'
    package['calculations'].append(new)
    result = select(package, query)
    assert event(result, 'alpha')['calculationRevisionId'] == 'revision:zz-tie'
    assert aggregate(result)['sums']['eligible_n'] == 8


@pytest.mark.parametrize('kind', ['resource', 'calculation', 'coverage', 'proof'])
def test_conflicting_identity_fails(package, query, kind):
    if kind == 'resource':
        r = deepcopy(package['resources'][0]); r['payload']['origin'] = 'different'; package['resources'].append(r)
    elif kind == 'proof':
        e = deepcopy(package['evidence'][0]); e['origin'] = 'different'; package['evidence'].append(e)
    else:
        c = deepcopy(calc(package)); c['revision_id'] = 'revision:conflict'; c['unknown_filter_flags_n'] = 1
        if kind == 'coverage':
            c['calculation_id'] = 'calculation:other'
        package['calculations'].append(c)
    with pytest.raises(ValueError, match='IDENTITY_CONFLICT'):
        select(package, query)


@pytest.mark.parametrize('value', ['2026-09-28T12:00:00', '2026-09-28', 'bad', '2026-02-30T00:00:00Z', '2026-09-28T12:00:00+99:00', '2026-09-28T12:00:00.1Z'])
def test_bad_cutoff_rejected(package, query, value):
    query['asOfInstant'] = value
    with pytest.raises(ValueError):
        select(package, query)


def test_offsets_precision_and_date_shortcut(package, query):
    assert instant('2026-09-28T09:00:00.000000001-03:00') > instant(CUTOFF)
    assert instant('2026-09-28T09:00:00-03:00') == instant(CUTOFF)
    query['asOfInstant'] = '2026-09-28T09:00:00-03:00'
    result = select(package, query)
    assert result['request']['asOfInstant'] == CUTOFF
    del query['asOfInstant']; query['asOfDate'] = '2026-09-28'
    result = select(package, query)
    assert result['asOfDateMapping'] == {'asOfDate': '2026-09-28', 'mappedAsOfInstant':'2026-09-28T00:00:00Z'}


@pytest.mark.parametrize('day,time,expected', [('2026-09-28','13:00','2026-09-28T17:00:00Z'), ('2026-12-28','13:00','2026-12-28T18:00:00Z'), ('2026-09-28',None,None)])
def test_eastern_dst_and_missing_time(day, time, expected):
    assert eastern_kickoff(day,time) == expected


@pytest.mark.parametrize('day,time', [('2026-03-08','02:30'), ('2026-11-01','01:30')])
def test_dst_ambiguous_nonexistent_rejected(day,time):
    with pytest.raises(ValueError, match='Ambiguous or nonexistent'):
        eastern_kickoff(day,time)


def test_calendar_kickoff_preserves_origin(package, query):
    state = revision(package, 'state:target')
    env = state['payload']['kickoff']
    proof(package, env['evidence_id'])['value'] = '2026-09-28T17:00:00Z'
    state['payload']['kickoff'] = {'gameday':'2026-09-28','gametime':'13:00','evidence_id':env['evidence_id']}
    result = select(package, query)
    assert result['pregame']['kickoff']['zone'] == 'America/New_York'
    assert result['pregame']['kickoff']['original']['gametime'] == '13:00'


@pytest.mark.parametrize('target_week,weeks', [(1, []), (2,[1]), (4,[1,2,3]), (5,[2,3,4])])
def test_calendar_weeks_not_extended(package, query, target_week, weeks):
    query['targetWeek'] = target_week
    result = select(package, query)
    assert block(result)['requestedWeeks'] == weeks
    if target_week == 1:
        assert block(result)['aggregates'] == []
        assert block(result)['coverage']['expectedGames'] == 0
        assert block(result)['coverage']['sourceRatio']['exact'] is None
    if target_week == 5:
        assert 'alpha' not in block(result)['scheduledGameIds']


def test_bye_requires_complete_closed_calendar(package, query):
    result = select(package, query)
    assert next(w for w in block(result)['weeklyStates'] if w['week'] == 2)['status'] == 'BYE'
    revision(package,'calendar-v1')['payload']['closed_weeks'] = []
    result = select(package, query)
    assert all(w['status'] == 'NOT_YET_CLOSED' for w in block(result)['weeklyStates'])
    assert block(result)['coverage']['expectedGames'] is None
    revision(package,'calendar-v1')['payload']['complete'] = None
    result = select(package, query)
    assert all(w['status'] == 'CALENDAR_UNKNOWN' for w in block(result)['weeklyStates'])


def test_no_bound_does_not_infer_from_scores_or_date(package, query):
    revision(package,'state:alpha')['payload']['event_upper_bound'] = None
    result = select(package, query)
    assert event(result, 'alpha')['reasons'] == ['EVENT_TIME_UNKNOWN']
    assert block(result)['coverage']['expectedGames'] is None
    assert block(result)['coverage']['uncertainGameIds'] == ['alpha']


@pytest.mark.parametrize('status,scope', [('UNKNOWN','AUDITABLE_SUBSET_UNKNOWN'),('PARTIAL','AUDITABLE_SUBSET_PARTIAL')])
def test_subset_not_promoted(package, query, status, scope):
    c=calc(package); c['completeness']['value']=status
    proof(package,c['completeness']['evidence_id'])['value']=status
    result=select(package, query)
    assert aggregate(result, scope=scope)['volume']==2
    assert aggregate(result)['volume']==6
    assert block(result)['coverage']['sourceRatio']['exact']=='1/3'
    assert not aggregate(result,scope=scope)['comparisonEligible']


def test_remove_source_never_improves_coverage(package, query):
    original=select(package,query)
    delete_beta(package)
    changed=select(package,query)
    assert block(changed)['coverage']['expectedGames']==block(original)['coverage']['expectedGames']==3
    assert block(changed)['coverage']['sourceRatio']['exact']=='1/3'
    assert aggregate(changed)['sums']['eligible_n']==2


@pytest.mark.parametrize('version', ['population','definition'])
def test_versions_not_mixed(package, query, version):
    calc(package)['versions'][version]='incompatible'
    result=select(package,query)
    assert event(result,'alpha')['calculationId'] is None
    assert any(r['reason']=='INCOMPATIBLE_DEFINITION_OR_POPULATION' for d in result['revisionDecisions'] for r in d['reasons'])


def test_model_incompatibility_separates_groups(package,query):
    c=calc(package); c['model']['value']='model-v2'; proof(package,c['model']['evidence_id'])['value']='model-v2'
    for env in c['source_models'].values():
        env['value']='model-v2'; proof(package,env['evidence_id'])['value']='model-v2'
    result=select(package,query)
    a=aggregate(result,model='model-v2'); b=aggregate(result)
    assert a['volume']==2 and b['volume']==6
    assert 'INCOMPATIBLE_EPA_MODELS_SEPARATED' in a['comparisonFailures']


def test_model_unknown_separate_and_flags_restrict_comparison(package,query):
    c=calc(package); c['model']=None; c['unknown_filter_flags_n']=1
    c['source_models']={source:None for source in c['source_models']}
    result=select(package,query)
    a=aggregate(result,model='UNKNOWN')
    assert 'EPA_MODEL_UNKNOWN' in a['comparisonFailures']
    assert 'UNKNOWN_FILTER_FLAGS' in a['comparisonFailures']


def test_invalid_sums_and_cross_phase_rejected(package,query):
    calc(package)['statistics'][0]['epa_n']=100
    with pytest.raises(ValueError,match='counts'):
        select(package,query)
    package=json.loads((FIXTURES/'package.json').read_text())
    calc(package)['game']['phase']='POST'
    with pytest.raises(ValueError,match='phase/round'):
        select(package,query)


def test_historical_separate_no_fallback(package,query):
    query['windows'].append('HISTORICAL_REFERENCE')
    query.update(historicalSeason=2025,historicalPhase='REG')
    result=select(package,query)
    h=block(result,'HISTORICAL_REFERENCE')
    assert h['season']==2025 and h['origin']=='HISTORICAL_REFERENCE'
    assert h['calendarRevisionId'] is None and h['aggregates']==[]
    assert h['coverage']['expectedGames'] is None
    assert aggregate(result)['volume']==8
    query['historicalSeason']=2026
    with pytest.raises(ValueError,match='earlier'):
        select(package,query)


def test_defense_is_allowed_production_and_no_mean_of_means(package,query):
    query['team']='B'
    result=select(package,query)
    assert aggregate(result,role='def')['epa']['exact']=='1/14'
    assert aggregate(result,role='def')['successRate']['exact']=='3/7'
    assert aggregate(result,role='off')['epa']['exact'] is None


def test_permutation_duplicates_and_reexecution(package,query):
    original=select(package,query)
    rng=random.Random(903)
    def shuffle(value):
        if isinstance(value,dict):
            for v in value.values(): shuffle(v)
        elif isinstance(value,list):
            rng.shuffle(value)
            for v in value: shuffle(v)
    shuffled=deepcopy(package); shuffle(shuffled)
    assert select(shuffled,query)==original
    package['calculations'].append(deepcopy(calc(package)))
    duplicated=select(package,query)
    assert duplicated['result_id']==original['result_id']
    assert aggregate(duplicated)['volume']==8
    assert select(package,query)==duplicated


def test_future_revision_cannot_change_pit_semantic_identity(package,query):
    original=select(package,query)
    c=deepcopy(calc(package,'alpha-corrected'))
    c.update(revision_id='revision:future',calculation_id='calculation:future',coverage_revision_id='coverage:future')
    c['completeness']=None; c['model']=None
    package['calculations'].append(c)
    future_cal=deepcopy(revision(package,'calendar-v1'))
    future_cal.update(revision_id='future-calendar',available_at=None,ingested_at=None)
    future_cal['payload']['games'].append({'game_id':'future','season':2026,'phase':'REG','round':'REG','week':18,'home_team':'A','away_team':'B'})
    package['resources'].append(future_cal)
    result=select(package,query)
    assert result['result_id']==original['result_id']
    assert result['audit_id']!=original['audit_id']
    assert aggregate(result)['sums']==aggregate(original)['sums']


def test_derivation_today_does_not_need_old_artifact(package,query):
    before=select(package,query)
    query['derivedAt']='2026-11-01T00:00:00Z'
    after=select(package,query)
    assert before['result_id']==after['result_id']
    assert before['audit_id']!=after['audit_id']


def test_comparison_preserves_values(package,query):
    result=select(package,query); b=block(result); a=aggregate(result)
    compared=comparison(a,a,b,b,result['request'],result['request'])
    assert compared['left']==a and compared['right']==a
    assert not compared['comparisonEligible']
    changed={**b,'origin':'HISTORICAL_REFERENCE','season':2025}
    compared=comparison(a,a,b,changed,result['request'],result['request'])
    assert 'MISMATCH_origin' in compared['failures']


def test_cli_new_destination_deterministic_and_failure_atomic(package,query,tmp_path):
    args=['--input',str(FIXTURES/'package.json'),'--season','2026','--phase','REG','--team','A','--target-game-id','target','--target-week','4','--window','LAST_3_CALENDAR_WEEKS','--as-of-instant',CUTOFF,'--mode','POINT_IN_TIME','--derived-at',query['derivedAt']]
    first=tmp_path/'first'; second=tmp_path/'second'
    assert main(args+['--output',str(first)])==0
    assert main(args+['--output',str(second)])==0
    assert (first/'result.json').read_bytes()==(second/'result.json').read_bytes()
    with pytest.raises(SystemExit) as error:
        main(args+['--output',str(first)])
    assert error.value.code==2
    bad=tmp_path/'bad.json'; package['resources'][0]['payload']['bytes_base64']=base64.b64encode(b'corrupt').decode(); bad.write_bytes(json_bytes(package))
    args[1]=str(bad); destination=tmp_path/'failed'
    with pytest.raises(SystemExit): main(args+['--output',str(destination)])
    assert not destination.exists() and not list(tmp_path.glob('.*.pending-*'))


def test_atomic_publish_failure_and_public_destination(package,query,tmp_path,monkeypatch):
    import nfl_sideline_etl.temporal_metrics.__main__ as cli
    result=select(package,query)
    def fail(*args): raise OSError('simulated no-clobber publication error')
    monkeypatch.setattr(cli,'rename_exclusive',fail)
    with pytest.raises(OSError): publish(tmp_path/'failed',result)
    assert not (tmp_path/'failed').exists() and not list(tmp_path.glob('.*.pending-*'))
    with pytest.raises(ValueError,match='forbidden'): publish(tmp_path/'web-ui/public/data/new',result)


def test_no_network_database_env_or_persistence_imports():
    # Fresh interpreter; block forbidden imports, then run the pure JSON path.
    code='''
import importlib.abc, json, sys
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'socket','psycopg2','dotenv','boto3','nflreadpy','requests','urllib'} or 'metrics_persistence' in fullname:
   raise AssertionError('Forbidden import: '+fullname)
sys.meta_path.insert(0,Guard())
from nfl_sideline_etl.temporal_metrics.core import select
from pathlib import Path
p=Path(sys.argv[1])
r=select(json.loads((p/'package.json').read_text()),json.loads((p/'request-pit.json').read_text()))
assert r['structuralValidation']=='PASSED'
'''
    run=subprocess.run([sys.executable,'-B','-c',code,str(FIXTURES)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr


def append_evidence(package, kind, subject, value, recorded_at=EARLY, dependencies=None):
    eid='test:'+str(len(package['evidence']))
    package['evidence'].append({'evidence_id':eid,'kind':kind,'subject_id':subject,'origin':'synthetic-system','reference':'independent-counterfactual-ledger','recorded_at':recorded_at,'value':value,'dependencies':dependencies or []})
    return {'value':value,'evidence_id':eid}


def clone_state(package,gid,new_id,when):
    r=deepcopy(revision(package,'state:'+gid)); r['revision_id']=new_id
    for key in ('available_at','ingested_at'):
        r[key]=append_evidence(package,'SYSTEM_INGESTION',new_id,when,when)
    r['payload']['event_upper_bound']=append_evidence(package,'EVENT_END_BOUND',new_id,'2026-09-07T23:00:00Z','2026-09-08T00:00:00Z')
    package['resources'].append(r)
    return r


def test_available_order_wins_over_lexical_id(package,query):
    # state:z has earlier availability than state:0. Revision IDs are not clocks.
    proof(package,revision(package,'state:alpha')['payload']['event_upper_bound']['evidence_id'])['recorded_at']='2026-09-08T00:00:00Z'
    clone_state(package,'alpha','state:z','2026-09-08T00:00:00Z')
    latest=clone_state(package,'alpha','state:0','2026-09-09T00:00:00Z')
    result=select(package,query)
    assert event(result,'alpha')['stateRevisionId']==latest['revision_id']


def test_final_observed_bound_is_observation_not_kickoff(package,query):
    state=revision(package,'state:alpha')
    value='2026-09-22T00:00:00Z'
    state['payload']['event_upper_bound']=append_evidence(package,'FINAL_OBSERVATION',state['revision_id'],value,value)
    result=select(package,query)
    assert event(result,'alpha')['eventEligible']
    # Cannot lower the bound while retaining this receipt of final state.
    state['payload']['event_upper_bound']['value']='2026-09-07T23:00:00Z'
    result=select(package,query)
    assert event(result,'alpha')['reasons']==['EVENT_TIME_UNKNOWN']


def test_late_document_dependency_blocks_earlier_claim(package,query):
    late={'revision_id':'late-doc','kind':'METADATA','dependencies':[], 'available_at':None,'ingested_at':None,'payload':{'origin':'counterfactual','document':{'final':True}}}
    package['resources'].append(late)
    e=proof(package,revision(package,'state:alpha')['payload']['event_upper_bound']['evidence_id'])
    e['dependencies']=['late-doc']
    result=select(package,query)
    assert event(result,'alpha')['reasons']==['STATE_UNKNOWN_OR_INELIGIBLE']
    assert any(r['reason']=='EVIDENCE_DEPENDENCY_INELIGIBLE' for d in result['revisionDecisions'] for r in d['reasons'])
    assert block(result)['coverage']['expectedGames'] is None


def test_known_state_correction_is_selected_before_event_filter(package,query):
    newest=clone_state(package,'alpha','state:changed','2026-09-23T00:00:00Z')
    newest['payload']['status']='POSTPONED'
    result=select(package,query)
    assert event(result,'alpha')['stateRevisionId']==newest['revision_id']
    assert event(result,'alpha')['reasons']==['EVENT_NOT_FINAL']
    assert block(result)['coverage']['expectedGames'] is None


def test_target_exclusion_never_creates_bye(package,query):
    cal=revision(package,'calendar-v1')
    cal['payload']['games']=[g for g in cal['payload']['games'] if g['game_id']!='alpha']
    package['resources']=[r for r in package['resources'] if r['revision_id']!='state:alpha']
    package['calculations']=[c for c in package['calculations'] if c['game']['game_id']!='alpha']
    # Remove now unbound proofs of state alpha from the materialization.
    package['evidence']=[e for e in package['evidence'] if e['subject_id']!='state:alpha']
    result=select(package,query)
    assert next(w for w in block(result)['weeklyStates'] if w['week']==1)['status']=='TARGET_GAME_EXCLUDED'


def test_historical_positive_block_and_phase_separation(package,query):
    original=revision(package,'calendar-v1')
    historical=deepcopy(original); historical['revision_id']='calendar-historical'
    historical['payload']['season']=2025
    hg={'game_id':'old-game','season':2025,'phase':'POST','round':'WC','week':1,'home_team':'A','away_team':'B'}
    historical['payload'].update(phase='POST',games=[hg])
    for key in ('available_at','ingested_at'):
        historical[key]=append_evidence(package,'SYSTEM_INGESTION',historical['revision_id'],EARLY)
    historical['payload']['complete']=append_evidence(package,'CALENDAR_COMPLETE',historical['revision_id'],True)
    historical['payload']['closed_weeks']=[{'week':1,'evidence_id':append_evidence(package,'PERIOD_CLOSED',historical['revision_id'],1)['evidence_id']}]
    package['resources'].append(historical)
    state=clone_state(package,'alpha','state:old-game',EARLY)
    state['dependencies']=[historical['revision_id']]
    state['payload'].update(game_id='old-game',calendar_revision_id=historical['revision_id'])
    c=deepcopy(calc(package)); c.update(revision_id='revision:history',calculation_id='calculation:history',coverage_revision_id='coverage:history',calendar_revision_id=historical['revision_id'],game=hg)
    c['completeness']=append_evidence(package,'PBP_COMPLETE',c['coverage_revision_id'],'COMPLETE')
    c['model']=append_evidence(package,'METADATA',c['calculation_id'],'model-v1')
    package['calculations'].append(c)
    query.update(historicalSeason=2025,historicalPhase='POST'); query['windows'].append('HISTORICAL_REFERENCE')
    result=select(package,query)
    h=block(result,'HISTORICAL_REFERENCE')
    assert h['coverage']['expectedGames']==1
    assert h['aggregates'][0]['gameIds']==['old-game']
    assert h['phase']=='POST' and h['origin']=='HISTORICAL_REFERENCE'
    assert block(result)['coverage']['expectedGames']==3
    assert aggregate(result)['volume']==8


def test_no_historical_proof_returns_unknown_not_synthetic_receipts(package,query):
    # Historical E5b-1 style declarations have no trusted archive timestamp.
    for r in package['resources']:
        if r['kind']!='SET':
            r['available_at']=None; r['ingested_at']=None
    result=select(package,query)
    assert all(b['coverage']['expectedGames'] is None and not b['aggregates'] for b in result['blocks'])
    assert result['pregame']['timeStatus']=='PREGAME_TIME_UNVERIFIED'


def test_complete_zero_and_all_missing_are_distinct(package,query):
    c=calc(package)
    for row in c['statistics']:
        row.update(eligible_n=0,epa_n=0,success_n=0,epa_missing_n=0,epa_nonfinite_n=0,epa_sum=None)
    delete_beta(package)
    result=select(package,query)
    assert aggregate(result)['volume']==0
    assert aggregate(result)['epa']['exact'] is None
    assert 'alpha' in block(result)['coverage']['observedCompleteGameIds']
    for row in c['statistics']:
        if (row['team'],row['role']) in [('A','off'),('B','def')] and row['foundation']!='classified_rush':
            row.update(eligible_n=2,epa_missing_n=2)
    result=select(package,query)
    assert aggregate(result)['volume']==2 and aggregate(result)['sums']['epa_n']==0
    assert next(w for w in block(result)['weeklyStates'] if w['week']==1)['status']=='NO_EPA_OBSERVATIONS'


def test_high_precision_sums_no_decimal_context_rounding(package,query):
    c=calc(package)
    for row in c['statistics']:
        if row['epa_n']:
            row['epa_sum']='1.123456789012345678901234567890123456789'
    delete_beta(package)
    result=select(package,query)
    assert aggregate(result)['sums']['epa_sum']=='1.123456789012345678901234567890123456789'
    assert aggregate(result)['epa']['denominator']==2


def test_reconstruction_records_later_knowledge_actually_used(package,query):
    result=select(package,reconstruction(query))
    assert result['guarantees']['knowledgeAtCutoff']=='NOT_DEMONSTRATED'
    assert result['guarantees']['postCutoffEvidenceIds']
    assert result['guarantees']['postCutoffResourceIds']
    assert 'alpha' not in block(result)['coverage']['availabilityKnownGameIds']


def test_missing_and_invalid_evidence_timestamps(package,query):
    state=revision(package,'state:alpha')
    env=state['payload']['event_upper_bound']
    proof(package,env['evidence_id'])['recorded_at']='2026-09-21T23:00:00'
    with pytest.raises(ValueError,match='timezone'):
        select(package,query)


def test_receipt_cannot_prove_ingestion_or_event_closure(package,query):
    c=calc(package)
    file=revision(package,revision(package,c['pbp_revision_id'])['dependencies'][0])
    file['ingested_at']=deepcopy(file['available_at'])
    result=select(package,query)
    assert event(result,'alpha')['calculationId'] is None
    env=deepcopy(file['available_at'])
    revision(package,'state:beta')['payload']['event_upper_bound']=env
    result=select(package,query)
    assert event(result,'beta')['reasons']==['EVENT_TIME_UNKNOWN']


@pytest.mark.parametrize('case_id', ['unequal_week_volumes','bye_and_unknown_source_gap', 'exclusive_cut_boundary', 'season_start_empty', 'two_events_same_period', 'two_events_same_period_both_eligible', 'target_future_unknown_bound', 'calendar_unknown_not_bye'])
def test_e5a_temporal_ledgers_regressions(case_id):
    """Materialize E5a assertions under explicit synthetic trust, without changing them.

    Only sufficient stats come from the accepted E5b-1 adapter. Expected temporal
    IDs, counts and fractions remain those of the independently written E5a ledger.
    E5a's bare receipt labels are not treated as real archive receipts.
    """
    from nfl_sideline_etl.offline_metrics.artifact import calculate
    from nfl_sideline_etl.offline_metrics.validation import CALENDAR_FIELDS, PBP_FIELDS
    source=Path(__file__).resolve().parents[2]/'contracts/metrics/e5a-v1/fixtures/cases.json'
    case=next(c for c in json.loads(source.read_text())['cases'] if c['id']==case_id)
    q=case['query']; cal_id='regression-calendar'
    package={'inputVersion':'metrics-temporal-input-v1','policy':{'policyVersion':'materialized-evidence-v1','trustedOrigins':['synthetic-system']},'resources':[],'evidence':[],'calculations':[]}
    def file_set(label,kind):
        raw=label.encode(); sha=hashlib.sha256(raw).hexdigest(); rid='sha256:'+sha
        package['resources'].append({'revision_id':rid,'kind':'FILE','dependencies':[], 'available_at':None,'ingested_at':None,'payload':{'source_revision_id':rid,'sha256':sha,'bytes_base64':base64.b64encode(raw).decode(),'origin':'E5a-synthetic-materialization'}})
        sid=identity([rid])
        package['resources'].append({'revision_id':sid,'kind':'SET','dependencies':[rid], 'available_at':None,'ingested_at':None,'payload':{'source_set_id':sid,'source_kind':kind}})
        return sid
    games=[{'game_id':g['game_id'],'season':g['season'],'phase':g['phase'],'round':g['round'],'week':g['week'],'home_team':g['teams'][0],'away_team':g['teams'][1]} for g in case['games']]
    calendar_rows=[{'game_id':g['game_id'],'season':g['season'],'game_type':g['phase'] if g['phase']=='REG' else g['round'] or 'POST','week':g['week'],'home_team':g['home_team'],'away_team':g['away_team']} for g in games]
    # Accepted adapter's descriptor count contract, with synthetic actual rows.
    descriptor=lambda kind,rows: {'kind':kind,'sha256':hashlib.sha256(json_bytes(rows)).hexdigest(),'source_revision_id':identity(rows),'raw_rows':len(rows)}
    plays=case.get('plays',[])
    computed=calculate(calendar_rows,plays,[descriptor('calendar',calendar_rows),descriptor('pbp',plays)])
    calset=file_set('e5a-calendar:'+case_id,'calendar')
    complete=append_evidence(package,'CALENDAR_COMPLETE',cal_id,case['calendar']['complete'],LATE)
    closed=[{'week':w,'evidence_id':append_evidence(package,'PERIOD_CLOSED',cal_id,w,LATE)['evidence_id']} for w in case['calendar']['closed_weeks']]
    package['resources'].append({'revision_id':cal_id,'kind':'CALENDAR','dependencies':[calset], 'available_at':None,'ingested_at':None,'payload':{'season':q['season'],'phase':q['phase'],'games':games,'complete':complete,'closed_weeks':closed}})
    retro={'calendars':{f"{q['season']}/{q['phase']}":cal_id},'states':{},'calculations':{}}
    for g,fg in zip(case['games'],games):
        gid=g['game_id']; sid='state:'+gid; bound=g['event_upper_bound']
        env=append_evidence(package,'EVENT_END_BOUND',sid,bound,LATE) if bound else None
        package['resources'].append({'revision_id':sid,'kind':'STATE','dependencies':[cal_id],'available_at':None,'ingested_at':None,'payload':{'game_id':gid,'calendar_revision_id':cal_id,'status':g['status'],'event_upper_bound':env,'kickoff':None}})
        retro['states'][cal_id+'/'+gid]=sid
        retro['calculations'][cal_id+'/'+gid]=None
        rows=[{k:r[k] for k in ('team','role','foundation','eligible_n','epa_n','epa_sum','success_n','epa_missing_n','epa_nonfinite_n')} for r in computed['statistics.json'] if r['game_id']==gid]
        if rows and g['pbp_status']=='COMPLETE':
            cid='calculation:'+gid; cov='coverage:'+gid; rid='revision:'+gid
            package['calculations'].append({'revision_id':rid,'calculation_id':cid,'coverage_revision_id':cov,'calendar_revision_id':cal_id,'pbp_revision_id':file_set('pbp:'+gid,'pbp'),'metadata_revision_ids':[],'game':fg,'versions':{'population':'classified-scrimmage-v1','definition':'1.0.0','adapter':'1.0.0'},'completeness':append_evidence(package,'PBP_COMPLETE',cov,'COMPLETE',LATE),'model':None,'source_models':{},'unknown_filter_flags_n':0,'statistics':rows})
            package['calculations'][-1]['source_models']={source:None for source in revision(package,package['calculations'][-1]['pbp_revision_id'])['dependencies']}
            retro['calculations'][cal_id+'/'+gid]=rid
    query={'season':q['season'],'phase':q['phase'],'team':q['team'],'targetGameId':q['target_game_id'],'targetWeek':q['target_week'],'asOfInstant':q['as_of_instant'],'mode':'EVENT_RECONSTRUCTION','windows':[q['window']],'derivedAt':LATE,'retrospective':retro}
    if 'observation_week' in q: query['week']=q['observation_week']
    result=select(package,query); b=block(result,q['window']); expected=case['expected']
    if 'game_ids' in expected:
        assert sorted(b['coverage']['knownEligibleGameIds'])==sorted(expected['game_ids'])
    if 'coverage' in expected:
        e=expected['coverage']
        if 'expected_games' in e: assert b['coverage']['expectedGames']==e['expected_games']
        if 'source_ratio' in e:
            got=b['coverage']['sourceRatio']
            assert (got['exact'] if got else None)==e['source_ratio']
    if 'weekly_states' in expected:
        assert {str(w['week']):w['status'] for w in b['weeklyStates']}==expected['weekly_states']
    mean=expected.get('stats',{}).get('general',{}).get('epa_mean','UNSPECIFIED')
    if mean!='UNSPECIFIED':
        groups=[a for a in b['aggregates'] if a['role']==q['role'] and a['foundation']=='general']
        assert (groups[0]['epa']['exact'] if groups else None)==mean


@pytest.mark.parametrize('cause', ['PBP_ABSENT','SOURCE_DELAY','INGESTION_FAILED'])
def test_source_specific_cause_needs_proof(package,query,cause):
    state=revision(package,'state:gap')
    env=append_evidence(package,'METADATA',state['revision_id'],cause)
    state['payload']['source_cause']=env
    result=select(package,query)
    assert event(result,'gap')['sourceState']==cause
    assert block(result)['coverage']['gaps'][0]['reason']==cause
    proof(package,env['evidence_id'])['origin']='untrusted'
    result=select(package,query)
    assert event(result,'gap')['sourceState']=='SOURCE_UNKNOWN'
    assert block(result)['coverage']['expectedGames']==3


def test_later_statement_cannot_replace_eligible_state(package,query):
    new=clone_state(package,'alpha','state:late-statement','2026-09-09T00:00:00Z')
    proof(package,new['payload']['event_upper_bound']['evidence_id'])['recorded_at']=LATE
    result=select(package,query)
    assert event(result,'alpha')['stateRevisionId']=='state:alpha'
    assert event(result,'alpha')['eventEligible']


def test_receipt_tamper_and_unresolved_references_are_structural(package,query):
    e=next(e for e in package['evidence'] if 'receipt' in e)
    e['receipt']['archive_root']='/different'
    with pytest.raises(ValueError,match='receipt'):
        select(package,query)
    package=json.loads((FIXTURES/'package.json').read_text())
    revision(package,'state:alpha')['payload']['event_upper_bound']['evidence_id']='not-materialized'
    with pytest.raises(ValueError,match='Unresolved evidence'):
        select(package,query)


def test_composite_known_models_incompatible_are_not_pooled(package,query):
    c=calc(package,'beta-composed')
    sources=list(c['source_models'])
    env=c['source_models'][sources[-1]]
    env['value']='model-v2'; proof(package,env['evidence_id'])['value']='model-v2'
    r=reconstruction(query)
    r['retrospective']['calculations']['calendar-v1/beta']=c['revision_id']
    result=select(package,r)
    assert event(result,'beta')['calculationId'] is None
    assert block(result)['coverage']['expectedGames']==3
    assert any(reason['reason']=='INCOMPATIBLE_EPA_MODELS_IN_SOURCE_SET' for d in result['revisionDecisions'] for reason in d['reasons'])


def test_source_model_declaration_late_or_unknown_not_promoted(package,query):
    c=calc(package)
    for source in c['source_models']:
        c['source_models'][source]=None
    result=select(package,query)
    assert event(result,'alpha')['epaModel']=='UNKNOWN'
    assert aggregate(result,model='UNKNOWN')['volume']==2
    package=json.loads((FIXTURES/'package.json').read_text()); c=calc(package)
    for env in c['source_models'].values():
        proof(package,env['evidence_id'])['recorded_at']=LATE
    result=select(package,query)
    assert event(result,'alpha')['calculationId'] is None


def test_temporal_metadata_decimal_strings_required(package,query):
    package['resources'].append({'revision_id':'floating-metadata','kind':'METADATA','dependencies':[],'available_at':None,'ingested_at':None,'payload':{'origin':'synthetic','document':{'value':1.25}}})
    with pytest.raises(ValueError,match='decimal strings'):
        select(package,query)


def test_selected_calculations_preserve_per_game_audit(package,query):
    result=select(package,query)
    selected={c['revision_id']:c for c in result['calculationsUsed']}
    assert set(selected)=={'revision:alpha-old','revision:beta'}
    for label in ('alpha-old','beta'):
        actual=selected['revision:'+label]; expected=calc(package,label)
        assert {k:v for k,v in actual.items() if k!='statistics'}=={k:v for k,v in expected.items() if k!='statistics'}
        groups=lambda c:{(r['team'],r['role'],r['foundation']):r for r in c['statistics']}
        assert groups(actual)==groups(expected)
    assert sum(next(r['epa_n'] for r in c['statistics'] if (r['team'],r['role'],r['foundation'])==('A','off','general')) for c in selected.values())==aggregate(result)['sums']['epa_n']
