"""Offline bridge integrity/absence/publication tests; no DB or transport simulation."""
import base64
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from nfl_sideline_etl.metrics_materialization.core import materialize, ContractGap
from nfl_sideline_etl.metrics_materialization.publication import publish, read
from nfl_sideline_etl.metrics_materialization.recovery import recover
from nfl_sideline_etl.offline_metrics.artifact import identity, json_bytes
from nfl_sideline_etl.offline_metrics.inputs import load_json
from nfl_sideline_etl.temporal_metrics.core import select

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('e5b4_fixture', ROOT/'docs/plans/metrics/e5b-4/build_fixture.py')
fixture = importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
DERIVED = '2026-10-11T12:00:00.000000000001Z'


@pytest.fixture
def closed(tmp_path):
    return fixture.build(tmp_path/'fresh')


def retro(t):
    q = load_json((fixture.FIXTURE/'request-pit.json').read_bytes())
    q.update(mode='EVENT_RECONSTRUCTION',retrospective={'calendars':{},'states':{},'calculations':{}})
    for r in t['resources']:
        if r['kind']=='CALENDAR':q['retrospective']['calendars'][str(r['payload']['season'])+'/'+r['payload']['phase']]=r['revision_id']
        if r['kind']=='STATE':
            key=r['payload']['calendar_revision_id']+'/'+r['payload']['game_id']
            q['retrospective']['states'][key]=r['revision_id'];q['retrospective']['calculations'][key]=None
    for c in t['calculations']:q['retrospective']['calculations'][c['calendar_revision_id']+'/'+c['game']['game_id']]=c['revision_id']
    return q


def test_sources_multiplicity_ids_sums_and_no_pbp(closed):
    p,b,plan,archive=closed
    t,l=materialize(p,b,fixture.auxiliary([plan]),DERIVED)
    assert len(t['calculations'])==1
    c=t['calculations'][0]
    assert c['calculation_id']==plan.result['manifest.json']['calculation_id']
    assert c['coverage_revision_id']==plan.result['game-audit.json'][0]['coverage_revision_id']
    assert c['statistics']==[{k:s[k] for k in ('team','role','foundation','eligible_n','epa_n','success_n','epa_missing_n','epa_nonfinite_n','epa_sum')}
                              for s in plan.result['statistics.json']]
    pbp=next(r for r in t['resources'] if r['kind']=='SET' and r['payload']['source_kind']=='pbp')
    assert len(pbp['dependencies'])==3 and len(set(pbp['dependencies']))==2
    assert [r['ordinal'] for r in p['relations']['metric_source_member'] if r['kind']=='pbp']==[0,1,2]
    assert len(l['relations']['relations']['metric_calculation_coverage'])==4
    assert {d['game_id'] for d in l['diagnostics'] if d['reason']=='NO_SOURCE_OBSERVATION'}=={'synthetic-3','synthetic-5','synthetic-6'}
    result=select(t,retro(t));coverage=result['blocks'][0]['coverage']
    assert coverage['expectedGames']==3 and len(coverage['gaps'])==2
    assert coverage['observedGameIds']==['synthetic-1']
    assert result['guarantees']['knowledgeAtCutoff']=='NOT_DEMONSTRATED'
    g=next(a for a in result['blocks'][0]['aggregates'] if a['role']=='off' and a['foundation']=='general')
    assert g['sums']['epa_sum']=='-1' and g['epa']['exact']=='-1/3' and g['volume']==3
    assert g['scope']=='AUDITABLE_SUBSET_UNKNOWN' and g['model']=='UNKNOWN'


def test_complete_empty_and_no_source_are_distinct(tmp_path):
    p,b,plan,ar=fixture.build(tmp_path/'empty',empty=True)
    t,l=materialize(p,b,fixture.auxiliary([plan]),DERIVED)
    assert len(t['calculations'])==1 and t['calculations'][0]['game']['game_id']=='synthetic-6'
    assert all(s['eligible_n']==0 and s['epa_sum'] is None for s in t['calculations'][0]['statistics'])
    r=select(t,retro(t));g=r['blocks'][0]['aggregates'][0]
    assert g['scope']=='COMPLETE' and g['epa']=={'numerator':None,'denominator':0,'exact':None}
    assert r['blocks'][0]['coverage']['observedCompleteGameIds']==['synthetic-6']
    assert any(d['reason']=='NO_SOURCE_OBSERVATION' and d['game_id']=='synthetic-1' for d in l['diagnostics'])


def test_two_batches_single_observed_each_are_representable(tmp_path):
    p1,b1,plan1,ar=fixture.build(tmp_path/'one')
    p2,b2,plan2,_=fixture.build(tmp_path/'two',empty=True,archive=ar)
    p=fixture.merge([p1,p2]);b=recover(p,{ar.archive_id:str(ar.root)})
    t,l=materialize(p,b,fixture.auxiliary([plan1,plan2]),DERIVED)
    assert {c['calculation_id'] for c in t['calculations']}=={s['calculation_id'] for s in p['selection']}
    r=select(t,retro(t))
    assert r['blocks'][0]['coverage']['sourceRatio']['exact']=='1/3'
    assert {a['scope'] for a in r['blocks'][0]['aggregates']}=={'COMPLETE','AUDITABLE_SUBSET_UNKNOWN'}


def test_confirmed_batch_contract_gap_no_publication(tmp_path):
    p,b,plan,ar=fixture.build(tmp_path/'multi',multi=True)
    assert len({s['game_id'] for s in plan.result['statistics.json']})==2
    output=tmp_path/'must-not-exist'
    with pytest.raises(ContractGap,match='E5B3_BATCH_CALCULATION_ID_CONFLICT'):
        t,l=materialize(p,b,fixture.auxiliary([plan]),DERIVED);publish(output,t,l)
    assert not output.exists()


def test_receipt_now_does_not_certify_old_pit(closed):
    p,b,plan,ar=closed
    t,l=materialize(p,b,fixture.auxiliary([plan]),DERIVED)
    q=load_json((fixture.FIXTURE/'request-pit.json').read_bytes());r=select(t,q)
    assert r['blocks'][0]['coverage']['expectedGames'] is None
    assert r['blocks'][0]['aggregates']==[]
    assert any('NOT_KNOWN_AT_CUTOFF' in reason['reason'] or 'INGESTED_AT_UNKNOWN'==reason['reason']
               for d in r['resourceDecisions'] for reason in d['reasons'])
    assert all(res['ingested_at'] is None for res in t['resources'] if res['kind']=='FILE')


def test_missing_auxiliary_is_unknown_not_fabricated(closed):
    p,b,plan,ar=closed
    aux=load_json((fixture.FIXTURE/'auxiliary-empty.json').read_bytes())
    t,l=materialize(p,b,aux,DERIVED)
    r=select(t,retro(t));assert r['blocks'][0]['coverage']['expectedGames'] is None
    assert {s['payload']['status'] for s in t['resources'] if s['kind']=='STATE'}=={'UNKNOWN'}
    assert t['policy']['trustedOrigins']==[]
    assert any(d['reason']=='AUXILIARY_CALENDAR_UNKNOWN' for d in l['diagnostics'])


def test_untrusted_declaration_preserved(closed):
    p,b,plan,ar=closed;aux=fixture.auxiliary([plan]);aux['policy']['trustedOrigins']=[]
    t,l=materialize(p,b,aux,DERIVED);r=select(t,retro(t))
    assert r['blocks'][0]['coverage']['expectedGames'] is None
    assert any(e['status']=='DECLARATION_UNPROVEN' for e in r['evidenceQualifications'])
    assert t['evidence'] and t['calculations'][0]['completeness']['value']=='UNKNOWN'


@pytest.mark.parametrize('table',fixture.TABLES)
def test_missing_relation_rejected(closed,table):
    p,b,plan,ar=closed
    assert p['relations'][table]
    p['relations'][table].pop()
    with pytest.raises((ValueError,KeyError)):materialize(p,b,fixture.auxiliary([plan]),DERIVED)


@pytest.mark.parametrize('table,key,value',[
 ('metric_calculation','adapter_version','wrong'),('metric_source_member','ordinal',77),
 ('metric_source_member','raw_rows',123),('metric_source_member','source_id','wrong'),
 ('team_game_metric_sums','epa_sum','99'),('team_game_metric_sums','eligible_n',99),
 ('game_metric_coverage_revision','home_team','WRONG'),('game_metric_coverage_revision','completeness','COMPLETE'),
 ('metric_calculation_coverage','coverage_revision_id','wrong'),('metric_artifact_file','sha256','a'*64),
 ('metric_archive_blob','byte_length',99),('metric_archive_receipt','archive_root','/moved'),
 ('metric_archive_receipt','observed_at','2000-01-01T00:00:00Z'),
 ('metric_source_revision','revision_id','wrong'),('metric_artifact','calculation_id','wrong')])
def test_divergent_relation_rejected(closed,table,key,value):
    p,b,plan,ar=closed;p['relations'][table][0][key]=value
    with pytest.raises((ValueError,KeyError)):materialize(p,b,fixture.auxiliary([plan]),DERIVED)


@pytest.mark.parametrize('case',['missing','corrupt','receipt','root','locator','duplicate-observation','extra-bytes'])
def test_closed_byte_receipt_corruption_rejected(closed,case):
    p,b,plan,ar=closed;archive=b[ar.archive_id];sha=next(iter(archive['blobs']))
    if case=='missing':archive['blobs'].pop(sha)
    elif case=='corrupt':archive['blobs'][sha]=base64.b64encode(b'corrupt').decode()
    elif case=='extra-bytes':archive['blobs']['a'*64]=base64.b64encode(b'corrupt').decode()
    elif case=='receipt':archive['receipts'][sha]['observed_at']='2000-01-01T00:00:00Z'
    elif case=='root':archive['archive_root']='/moved'
    elif case=='locator':archive['receipts'][sha]['locator']='../../outside'
    elif case=='duplicate-observation':p['relations']['metric_archive_receipt'].append(deepcopy(p['relations']['metric_archive_receipt'][0]))
    with pytest.raises((ValueError,KeyError)):materialize(p,b,fixture.auxiliary([plan]),DERIVED)


@pytest.mark.parametrize('case',['blob-missing','blob-corrupt','blob-symlink','receipt-symlink','copied-root','uuid','root-symlink'])
def test_recovery_never_writes_or_follows_other_archive(closed,tmp_path,case):
    p,b,plan,ar=closed;sha=next(iter(b[ar.archive_id]['blobs']));path=ar.path(ar.locator(sha))
    roots={ar.archive_id:str(ar.root)}
    if case=='blob-missing':path.unlink()
    elif case=='blob-corrupt':path.write_bytes(b'wrong')
    elif case=='blob-symlink':
        other=tmp_path/'other';other.write_bytes(path.read_bytes());path.unlink();path.symlink_to(other)
    elif case=='receipt-symlink':
        target=ar.path('receipts/'+sha+'.json');other=tmp_path/'receipt';other.write_bytes(target.read_bytes());target.unlink();target.symlink_to(other)
    elif case=='copied-root':
        import shutil
        copy=tmp_path/'copy';shutil.copytree(ar.root,copy);roots[ar.archive_id]=str(copy)
    elif case=='uuid':roots={'00000000-0000-0000-0000-000000000000':str(ar.root)}
    elif case=='root-symlink':
        link=tmp_path/'link';link.symlink_to(ar.root,target_is_directory=True);roots[ar.archive_id]=str(link)
    before={str(f):f.read_bytes() for f in ar.root.rglob('*') if f.is_file()}
    with pytest.raises((ValueError,OSError)):recover(p,roots)
    assert before=={str(f):f.read_bytes() for f in ar.root.rglob('*') if f.is_file()}


def test_determinism_exact_precision_read_and_no_overwrite(closed,tmp_path):
    p,b,plan,ar=closed;aux=fixture.auxiliary([plan]);t,l=materialize(p,b,aux,DERIVED)
    assert (t,l)==materialize(deepcopy(p),deepcopy(b),deepcopy(aux),DERIVED)
    assert next(r for r in t['resources'] if r['kind']=='STATE')['payload']['event_upper_bound']['value'].endswith('.999999999999Z')
    output=tmp_path/'published';publish(output,t,l);assert read(output)==(t,l)
    with pytest.raises(FileExistsError):publish(output,t,l)
    assert not list(tmp_path.glob('.*.pending-*'))
    for r in p['relations']['metric_archive_blob']:r['persisted_at']='2000-01-01T00:00:00+00:00'
    t2,l2=materialize(p,b,aux,DERIVED)
    assert t==t2 and l!=l2


def test_atomic_failure_and_public_destination(closed,tmp_path,monkeypatch):
    p,b,plan,ar=closed;t,l=materialize(p,b,fixture.auxiliary([plan]),DERIVED)
    import nfl_sideline_etl.metrics_materialization.publication as publication
    def fail(*args):raise OSError('injected rename failure')
    monkeypatch.setattr(publication,'rename_exclusive',fail)
    output=tmp_path/'failed'
    with pytest.raises(OSError):publish(output,t,l)
    assert not output.exists() and not list(tmp_path.glob('.*.pending-*'))
    with pytest.raises(ValueError):publish(tmp_path/'web-ui/public/data/new',t,l)


def test_offline_import_driver_network_and_environment_guard():
    source="""
import builtins,socket,sys
original=builtins.__import__
def guarded(name,*a,**k):
 if name.startswith(('psycopg','dotenv','nflreadpy','requests')): raise AssertionError(name)
 return original(name,*a,**k)
builtins.__import__=guarded
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network'))
import nfl_sideline_etl.metrics_materialization.core
import nfl_sideline_etl.metrics_materialization.__main__
assert 'psycopg2' not in sys.modules
"""
    subprocess.run([sys.executable,'-B','-c',source],check=True,cwd=ROOT)


def test_cli_offline_and_selection(closed,tmp_path):
    p,b,plan,ar=closed
    relations=tmp_path/'relations.json';relations.write_bytes(json_bytes(p))
    archives=tmp_path/'roots.json';archives.write_bytes(json_bytes({ar.archive_id:str(ar.root)}))
    aux=tmp_path/'aux.json';aux.write_bytes(json_bytes(fixture.auxiliary([plan])))
    out=tmp_path/'cli'
    command=[sys.executable,'-B','-m','nfl_sideline_etl.metrics_materialization','offline','--relations',str(relations),
     '--archives',str(archives),'--auxiliary',str(aux),'--derived-at',DERIVED,'--output',str(out)]
    subprocess.run(command,check=True,cwd=ROOT,capture_output=True)
    t,l=read(out);request=tmp_path/'request.json';request.write_bytes(json_bytes(retro(t)))
    subprocess.run([sys.executable,'-B','-m','nfl_sideline_etl.metrics_materialization','select','--materialized',str(out),
      '--request',str(request),'--output',str(tmp_path/'selected')],check=True,cwd=ROOT,capture_output=True)
    assert (tmp_path/'selected/COMPLETED.json').is_file()
    assert subprocess.run(command,cwd=ROOT,capture_output=True).returncode==2


def test_explicit_ingestion_is_linked_but_not_inferred(closed):
    p,b,plan,ar=closed;aux=fixture.auxiliary([plan])
    source='sha256:'+next(iter(plan.source_bytes))
    meta=next(r for r in aux['resources'] if r['kind']=='METADATA')['revision_id']
    e={'evidence_id':'explicit-source-ingestion','kind':'SYSTEM_INGESTION','subject_id':source,
       'origin':'synthetic-e5b4','reference':'explicit-ingestion-document',
       'recorded_at':'2026-10-11T12:00:00.000000000001Z','value':'2026-10-11T12:00:00.000000000001Z','dependencies':[meta]}
    aux['evidence'].append(e);aux['file_ingestion']={source:{'value':e['value'],'evidence_id':e['evidence_id']}}
    t,l=materialize(p,b,aux,DERIVED)
    assert next(r for r in t['resources'] if r['revision_id']==source)['ingested_at']==aux['file_ingestion'][source]
    assert all(r['ingested_at'] is None for r in t['resources'] if r['kind']=='FILE' and r['revision_id']!=source)


@pytest.mark.parametrize('case',['document-origin','document-receipt','evidence-before-document','unbound-ingestion','extra-scope','missing-document-dependency'])
def test_explicit_auxiliary_document_integrity(closed,case):
    p,b,plan,ar=closed;aux=fixture.auxiliary([plan]);doc=aux['resources'][0]['payload']['document']
    if case=='document-origin':doc['origin']='different'
    elif case=='document-receipt':doc.pop('received_at')
    elif case=='evidence-before-document':aux['evidence'][0]['recorded_at']='2026-09-01T00:00:00Z'
    elif case=='unbound-ingestion':aux['file_ingestion']={'wrong':None}
    elif case=='extra-scope':aux['bindings'][0]['calendars']['2025/REG']='wrong'
    elif case=='missing-document-dependency':aux['evidence'][0]['dependencies']=[]
    with pytest.raises((ValueError,KeyError)):materialize(p,b,aux,DERIVED)


def test_sql_boolean_does_not_alias_integer_count(closed):
    p,b,plan,ar=closed
    row=next(r for r in p['relations']['metric_source_member'] if r['raw_rows']==1)
    row['raw_rows']=True
    with pytest.raises(ValueError,match='Persisted relation diverges'):materialize(p,b,fixture.auxiliary([plan]),DERIVED)


def test_receipt_utc_is_required_even_in_closed_memory(closed):
    p,b,plan,ar=closed;archive=b[ar.archive_id];sha=next(iter(archive['blobs']));r=archive['receipts'][sha]
    r['observed_at']='2026-10-11T12:00:00+01:00';r['receipt_id']=identity({k:v for k,v in r.items() if k!='receipt_id'})
    with pytest.raises(ValueError,match='must be UTC'):materialize(p,b,fixture.auxiliary([plan]),DERIVED)
