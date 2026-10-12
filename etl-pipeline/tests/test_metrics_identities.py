"""Independent v3 expectations; synthetic history is explicitly declared."""
from copy import deepcopy
import random

import pytest

from test_metrics_materialization import fixture, DERIVED, retro
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.recovery import recover
from nfl_sideline_etl.offline_metrics.artifact import calculate, write_artifact, identity
from nfl_sideline_etl.offline_metrics.inputs import read_inputs, load_json
from nfl_sideline_etl.metrics_persistence.plan import prepare
from nfl_sideline_etl.metrics_materialization.relations import records
from nfl_sideline_etl.temporal_metrics.validation import validate
from nfl_sideline_etl.temporal_metrics.core import select, comparison
from nfl_sideline_etl.temporal_metrics.__main__ import publish


@pytest.fixture
def batch(tmp_path):
    p,b,plan,ar=fixture.build(tmp_path/'batch',multi=True)
    t,l=materialize(p,b,fixture.auxiliary([plan]),DERIVED)
    return t,l,plan,ar


def revised(c, **changes):
    c=deepcopy(c);c.update(changes);c['revision_id']=identity({'temporalAssociation':{k:v for k,v in c.items() if k!='revision_id'}})
    return c


def test_legacy_versions_are_not_reinterpreted():
    base=fixture.ROOT/'etl-pipeline/tests/fixtures/temporal_metrics'
    p=load_json((base/'package.json').read_bytes());q=load_json((base/'request-pit.json').read_bytes())
    for v in ('metrics-temporal-input-v1','metrics-temporal-input-v2'):
        p['inputVersion']=v
        r=select(p,q)
        assert r['algorithmVersion']=='metrics-temporal-1.0.1'
        assert r['resultVersion']=='metrics-temporal-result-v2'


def test_duplicate_permutation_and_association_alternatives_do_not_add_volume(batch):
    t,_,plan,_=batch;q=retro(t);baseline=select(t,q)
    t['calculations'].append(deepcopy(t['calculations'][0]))
    # A different temporal revision of the same association is legitimate.
    t['calculations'].append(revised(t['calculations'][0],metadata_revision_ids=[]))
    for seed in range(5):
        random.Random(seed).shuffle(t['calculations']);random.Random(seed).shuffle(t['resources'])
        r=select(t,q)
        assert r['result_id']==baseline['result_id']
        assert r['blocks']==baseline['blocks']
    assert sum(a['volume'] for a in baseline['blocks'][0]['aggregates'] if a['role']=='off' and a['foundation']=='general')==3
    assert len(baseline['calculationsUsed'])==2


def test_same_revision_conflicting_content_aborts(batch):
    t,*_=batch;t['calculations'].append(deepcopy(t['calculations'][0]))
    t['calculations'][-1]['metadata_revision_ids']=[]
    with pytest.raises(ValueError,match='IDENTITY_CONFLICT'):validate(t)


@pytest.mark.parametrize('kind',['statistics','game','source','batch','coverage','calendar','envelope','completeness','model','version','provenance','missing-original'])
def test_conflicts_abort_even_with_distinct_revision_ids(batch,kind):
    t,*_=batch;c=deepcopy(t['calculations'][0]);c['revision_id']='distinct-temporal-revision'
    if kind=='statistics':
        # Reconciled twelve-group statistics with unchanged eligible counts.
        for s in c['statistics']:
            if s['team']=='A' and s['role']=='off' or s['team']=='B' and s['role']=='def':
                if s['foundation'] in ('general','classified_pass'):s['epa_sum']='123'
    elif kind=='game':c['game']['week']=5
    elif kind=='source':c['original']['coverage']['pbp_revision_id']='wrong-set'
    elif kind=='batch':c['original']['manifest']['limitations'].append('contradictory global property')
    elif kind=='coverage':c['original']['coverage']['raw_n']+=1;c['original']['coverage']['duplicate_rows_ignored']+=1
    elif kind=='calendar':
        cal=next(r for r in t['resources'] if r['revision_id']==c['calendar_revision_id'])
        cal['dependencies']=[d for d in cal['dependencies'] if d!=c['original']['coverage']['calendar_revision_id']]
    elif kind=='envelope':
        e=next(e for e in t['evidence'] if e['evidence_id']==c['completeness']['evidence_id']);e['subject_id']='wrong-coverage'
    elif kind=='completeness':c['completeness']['value']='COMPLETE'
    elif kind=='model':c['source_models'][next(iter(c['source_models']))]={'value':'model-x','evidence_id':c['completeness']['evidence_id']}
    elif kind=='version':c['versions']['definition']='999'
    elif kind=='provenance':c['original']['manifest']['metadata']['games'][c['game']['game_id']]={'completeness':'PARTIAL'}
    else:del c['original']
    t['calculations'].append(c)
    with pytest.raises((ValueError,KeyError)):validate(t)


def system_history(t):
    """Fixture asserts history under a named synthetic policy; no real certification."""
    early='2026-09-28T11:59:59.999999999999Z'
    for e in t['evidence']:
        if e['kind']!='ARCHIVE_OBSERVATION':e['recorded_at']=early
    for r in t['resources']:
        if r['kind']=='METADATA':r['payload']['document']['received_at']=early
        if r['kind']=='SET':continue
        e={'kind':'SYSTEM_INGESTION','subject_id':r['revision_id'],'origin':'synthetic-e5b4',
           'reference':'explicit-synthetic-historical-ledger','recorded_at':early,'value':early,'dependencies':[]}
        e['evidence_id']=identity(e);t['evidence'].append(e)
        r['available_at']=r['ingested_at']={'value':early,'evidence_id':e['evidence_id']}


def test_pit_prior_revision_future_invariance_and_nominal_retrospective(batch):
    t,*_=batch;system_history(t)
    q=load_json((fixture.FIXTURE/'request-pit.json').read_bytes());old=select(t,q)
    assert old['blocks'][0]['coverage']['expectedGames']==3
    c=t['calculations'][0];e=deepcopy(next(e for e in t['evidence'] if e['evidence_id']==c['completeness']['evidence_id']))
    e['recorded_at']='2026-10-12T09:00:00.123456789012-03:00';e['evidence_id']=identity(e);t['evidence'].append(e)
    future=revised(c,completeness={'value':c['completeness']['value'],'evidence_id':e['evidence_id']})
    t['calculations'].append(future)
    pit=select(t,q)
    assert pit['result_id']==old['result_id'] and pit['blocks']==old['blocks']
    assert c['revision_id'] in {c['revision_id'] for c in pit['calculationsUsed']}
    assert future['revision_id'] not in {c['revision_id'] for c in pit['calculationsUsed']}
    rq=retro(t);r=select(t,rq)
    assert future['revision_id'] in {c['revision_id'] for c in r['calculationsUsed']}
    assert len(r['calculationsUsed'])==2
    assert r['guarantees']['knowledgeAtCutoff']=='NOT_DEMONSTRATED'
    assert e['evidence_id'] in r['guarantees']['postCutoffEvidenceIds']


def model_batch(root, ar, model, *, second_game=False):
    root.mkdir()
    calendars=[fixture.FIXTURE/'calendar.json'];pbps=[fixture.FIXTURE/'pbp-a.json',fixture.FIXTURE/'pbp-b.json',fixture.FIXTURE/'pbp-a.json']
    if second_game:
        document=load_json((fixture.FIXTURE/'pbp-a.json').read_bytes())
        row=deepcopy(document['rows'][0]);row.update(game_id='synthetic-3',week=3)
        document['rows']=[row]
        from nfl_sideline_etl.offline_metrics.artifact import json_bytes
        extra=root/'second-game.json';extra.write_bytes(json_bytes(document));pbps.append(extra)
    inputs=read_inputs(calendars,pbps)
    metadata={'metadataVersion':1,'calendar_sha256':sorted({d['sha256'] for d in inputs[2] if d['kind']=='calendar'}),
        'pbp_sha256':sorted({d['sha256'] for d in inputs[2] if d['kind']=='pbp'}),
        'games':{'synthetic-6':{'completeness':'COMPLETE','expected_unique_rows':0,'evidence':{'basis':'SYNTHETIC_FIXTURE','reference':'fixture-ledger'}}},
        'sources':{d['sha256']:{'source_model_version':{'value':model,'evidence':{'basis':'DECLARED','reference':'explicit-model-document'}}} for d in inputs[2] if d['kind']=='pbp'}}
    write_artifact(root/'artifact',calculate(*inputs,metadata,seasons=(2026,)))
    plan=prepare(root/'artifact',calendars,pbps,ar.root)
    rows=records(plan)
    all_bytes={sha:(data,{'type':'explicit_source',**origin}) for sha,(data,origin) in plan.source_bytes.items()}
    all_bytes.update({plan.file_hashes[n]:(data,{'type':'artifact_file','filename':n,'artifact_id':plan.artifact_id}) for n,data in plan.artifact_bytes.items()})
    for sha,(data,origin) in sorted(all_bytes.items()):
        r=ar.put(data,sha,origin);rows['metric_archive_receipt'].append({**{k:r[k] for k in ('receipt_id','sha256','archive_id','archive_root','locator','observed_at')},'receipt_json':r})
    for table in ('metric_archive_blob','metric_calculation','metric_archive_receipt'):
        for r in rows[table]:r['persisted_at']='2026-10-11T12:00:00+00:00'
    p={'relationsVersion':'metrics-relations-v1','selection':[{'calculation_id':plan.result['manifest.json']['calculation_id'],'artifact_id':plan.artifact_id,'archive_id':ar.archive_id}], 'relations':rows}
    return p,plan


def test_legitimate_batches_share_coverage_model_only_change(tmp_path,batch):
    t,l,old,ar=batch;p,new=model_batch(tmp_path/'model',ar,'epa-v2')
    assert old.result['game-audit.json']==new.result['game-audit.json']
    assert old.result['statistics.json']==new.result['statistics.json']
    assert old.result['manifest.json']['calculation_id']!=new.result['manifest.json']['calculation_id']
    # SQL-shaped closed offline relations; this is not a PostgreSQL proof.
    merged=fixture.merge([l['relations'],p]);b=recover(merged,{ar.archive_id:str(ar.root)})
    out,_=materialize(merged,b,fixture.auxiliary([old,new]),DERIVED)
    assert len(out['calculations'])==4
    assert len({c['coverage_revision_id'] for c in out['calculations']})==2
    r=select(out,retro(out))
    assert len(r['calculationsUsed'])==2
    assert r['blocks'][0]['coverage']['observedGameIds']==['synthetic-1','synthetic-6']
    assert sum(a['volume'] for a in r['blocks'][0]['aggregates'] if a['role']=='off' and a['foundation']=='general')==3


def test_no_history_remains_unknown_and_periods_remain_distinct(batch):
    t,*_=batch;q=load_json((fixture.FIXTURE/'request-pit.json').read_bytes());pit=select(t,q)
    assert pit['blocks'][0]['aggregates']==[]
    r=select(t,retro(t));rq=retro(t);rq['asOfInstant']='2026-09-29T12:00:00Z';r2=select(t,rq)
    a=next(a for a in r['blocks'][0]['aggregates'] if a['role']=='off' and a['foundation']=='general' and a['scope']=='AUDITABLE_SUBSET_UNKNOWN')
    a2=next(a for a in r2['blocks'][0]['aggregates'] if a['role']=='off' and a['foundation']=='general' and a['scope']=='AUDITABLE_SUBSET_UNKNOWN')
    result=comparison(a,a2,r['blocks'][0],r2['blocks'][0],r['request'],r2['request'])
    assert not result['comparisonEligible'] and 'MISMATCH_REQUESTED_PERIOD' in result['failures']
    assert result['left']==a and result['right']==a2


def test_two_nonempty_games_complete_empty_and_absent_in_one_batch(tmp_path,batch):
    _,_,_,ar=batch;p,plan=model_batch(tmp_path/'two-observed',ar,'UNKNOWN',second_game=True)
    t,l=materialize(p,recover(p,{ar.archive_id:str(ar.root)}),fixture.auxiliary([plan]),DERIVED)
    assert {c['game']['game_id'] for c in t['calculations']}=={'synthetic-1','synthetic-3','synthetic-6'}
    assert len(l['relations']['relations']['metric_calculation_coverage'])==4
    q=retro(t);q['targetGameId']='outside-inventory';r=select(t,q);b=r['blocks'][0]
    assert b['coverage']['expectedGames']==4
    assert b['coverage']['observedGameIds']==['synthetic-1','synthetic-3','synthetic-6']
    assert b['coverage']['sourceRatio']['exact']=='1/4'
    assert [g['gameId'] for g in b['coverage']['gaps']]==['synthetic-5']
    a=next(a for a in b['aggregates'] if a['role']=='off' and a['foundation']=='general' and a['scope']=='AUDITABLE_SUBSET_UNKNOWN')
    assert a['sums']['eligible_n']==4 and a['sums']['epa_n']==4 and a['sums']['success_n']==1
    assert a['sums']['epa_sum']=='-2.123456789012345678901234567890123456789'
    assert a['epa']['exact']=='-2123456789012345678901234567890123456789/4000000000000000000000000000000000000000'
    assert any(a['scope']=='COMPLETE' and a['volume']==0 for a in b['aggregates'])


def test_auxiliary_calendar_is_not_original_set_and_model_docs_do_not_rewrite_id(batch):
    t,*_=batch;c=t['calculations'][0]
    cal=deepcopy(next(r for r in t['resources'] if r['revision_id']==c['calendar_revision_id']))
    old_cal=cal['revision_id'];cal['revision_id']='calendar-document-revision-two'
    cal['payload']['complete']=None;t['resources'].append(cal)
    for state in list(t['resources']):
        if state['kind']=='STATE' and state['payload']['calendar_revision_id']==old_cal:
            new=deepcopy(state);new['revision_id']='second:'+state['revision_id'];new['payload']['calendar_revision_id']=cal['revision_id']
            new['dependencies']=[cal['revision_id'] if d==old_cal else d for d in new['dependencies']]
            e=deepcopy(next(e for e in t['evidence'] if e['evidence_id']==new['payload']['event_upper_bound']['evidence_id']))
            e['subject_id']=new['revision_id'];e['evidence_id']=identity(e);t['evidence'].append(e)
            new['payload']['event_upper_bound']['evidence_id']=e['evidence_id'];t['resources'].append(new)
    def model_doc(subject):
        e={'kind':'METADATA','subject_id':subject,'origin':'synthetic-e5b4','reference':'second-qualified-model-document',
           'recorded_at':'2026-10-12T12:00:00Z','value':'qualified-model-v2','dependencies':c['metadata_revision_ids']}
        e['evidence_id']=identity(e);t['evidence'].append(e);return {'value':e['value'],'evidence_id':e['evidence_id']}
    for original in list(t['calculations']):
        t['calculations'].append(revised(original,calendar_revision_id=cal['revision_id'],
            model=model_doc(original['calculation_id']),source_models={sid:model_doc(sid) for sid in original['source_models']}))
    validate(t);q=retro(t);q['retrospective']['calendars']['2026/REG']=cal['revision_id'];r=select(t,q)
    assert {c['calculation_id'] for c in r['calculationsUsed']}=={c['calculation_id']}
    assert all(c['calendar_revision_id']!=c['original']['coverage']['calendar_revision_id'] for c in r['calculationsUsed'])
    assert {a['model'] for a in r['blocks'][0]['aggregates']}=={'qualified-model-v2'}
    assert r['blocks'][0]['coverage']['expectedGames'] is None


def test_original_manifest_arrays_are_preserved_exactly_in_result(batch):
    t,_,plan,_=batch;r=select(t,retro(t))
    assert all(c['original']['manifest']==plan.result['manifest.json'] for c in r['calculationsUsed'])
    changed=deepcopy(t['calculations'][0]);changed['revision_id']='another-revision'
    changed['original']['manifest']['replica_projection']['pbp'].reverse()
    t['calculations'].append(changed)
    with pytest.raises(ValueError,match='IDENTITY_CONFLICT'):validate(t)


@pytest.mark.parametrize('dimension',['input','materializer'])
def test_no_silent_materialization_version_promotion(batch,tmp_path,dimension):
    from nfl_sideline_etl.metrics_materialization.publication import publish
    from nfl_sideline_etl.temporal_metrics.core import canonical
    t,l,*_=batch
    if dimension=='input':
        t['inputVersion']='metrics-temporal-input-v2'
        for c in t['calculations']:c.pop('original')
        # One observed candidate makes this a structurally valid legacy input.
        t['calculations']=t['calculations'][:1]
    else:l['materializationVersion']='metrics-materialization-v1'
    l['temporalInputId']=identity(canonical(t));l['materialization_id']=identity({k:v for k,v in l.items() if k!='materialization_id'})
    with pytest.raises(ValueError,match='version pair'):publish(tmp_path/'must-not-exist',t,l)
    assert not (tmp_path/'must-not-exist').exists()


def test_distinct_coverage_alternatives_for_same_game_are_selected_once(tmp_path,batch):
    t,l,old,ar=batch;p,new=model_batch(tmp_path/'alternative-source',ar,'UNKNOWN',second_game=True)
    merged=fixture.merge([l['relations'],p]);out,_=materialize(merged,recover(merged,{ar.archive_id:str(ar.root)}),fixture.auxiliary([old,new]),DERIVED)
    candidates=[c for c in out['calculations'] if c['game']['game_id']=='synthetic-1']
    assert len(candidates)==2 and len({c['coverage_revision_id'] for c in candidates})==2
    r=select(out,retro(out));block=r['blocks'][0]
    assert len([c for c in r['calculationsUsed'] if c['game']['game_id']=='synthetic-1'])==1
    assert block['coverage']['observedGameIds']==['synthetic-1','synthetic-6']
    assert sum(a['volume'] for a in block['aggregates'] if a['role']=='off' and a['foundation']=='general')==3
