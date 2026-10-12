"""Real E5b-4 proof on an identified NEW disposable instance; never provisions SQL.

Harness instance.py prepares domain/schema separately. Writer inserts fixtures;
reader only SELECTs. Results explicitly separate supported flow and contract gap.
"""
import argparse
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import json

from build_fixture import build, merge, auxiliary, FIXTURE
from nfl_sideline_etl.metrics_persistence.connection import configuration, connect
from nfl_sideline_etl.metrics_persistence.writer import persist
from nfl_sideline_etl.metrics_materialization.postgres import extract, transport
from nfl_sideline_etl.metrics_materialization.recovery import recover
from nfl_sideline_etl.metrics_materialization.core import materialize, ContractGap
from nfl_sideline_etl.metrics_materialization.relations import TABLES
from nfl_sideline_etl.metrics_materialization.publication import publish, read
from nfl_sideline_etl.offline_metrics.artifact import identity, json_bytes
from nfl_sideline_etl.offline_metrics.inputs import load_json
from nfl_sideline_etl.metrics_persistence.archive import digest
from nfl_sideline_etl.temporal_metrics.core import select
from nfl_sideline_etl.temporal_metrics.__main__ import publish as publish_result


def snapshot(config):
    conn=connect(config)
    try:
        conn.set_session(isolation_level='REPEATABLE READ',readonly=True)
        with conn.cursor() as cur:
            data={}
            for t in TABLES:
                cur.execute('select * from metrics_private.'+t)
                cols=[d.name for d in cur.description]
                data[t]=sorted([transport(dict(zip(cols,row))) for row in cur.fetchall()],key=json_bytes)
            return data
    finally:conn.close()


def retrospective(t,q):
    q=deepcopy(q);q['mode']='EVENT_RECONSTRUCTION'
    q['retrospective']={'calendars':{},'states':{},'calculations':{}}
    # Fixture harness is the user explicitly choosing every nominal revision.
    # This function is NOT part of the materializer or selection CLI.
    for r in t['resources']:
        if r['kind']=='CALENDAR':q['retrospective']['calendars'][str(r['payload']['season'])+'/'+r['payload']['phase']]=r['revision_id']
        if r['kind']=='STATE':
            key=r['payload']['calendar_revision_id']+'/'+r['payload']['game_id']
            q['retrospective']['states'][key]=r['revision_id'];q['retrospective']['calculations'][key]=None
    for c in t['calculations']:q['retrospective']['calculations'][c['calendar_revision_id']+'/'+c['game']['game_id']]=c['revision_id']
    return q


def blobs(root):
    return {str(p.relative_to(root)):digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance-root',type=Path,required=True);parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--java',type=Path,required=True)
    args=parser.parse_args()
    if args.workspace.exists() or args.output.exists():parser.error('New workspace/output required')
    marker=load_json((args.instance_root/'INSTANCE.json').read_bytes())
    if not str(args.instance_root.resolve()).startswith('/private/tmp/nfl-e5b4-instance-'):
        parser.error('Only this delivery own disposable root allowed')
    config=configuration(args.instance_root/'writer.json')
    if marker['instance_id']!=config['instance_id']:parser.error('Instance identity mismatch')
    if any(snapshot(config).values()):parser.error('Instance must be empty; proof never resets it')
    args.workspace.mkdir()
    p1,b1,plan1,ar=build(args.workspace/'content')
    p2,b2,plan2,_=build(args.workspace/'empty',empty=True,archive=ar)
    writes=[persist(plan,ar.root,config) for plan in (plan1,plan2)]
    nominal=merge([p1,p2])['selection']
    before=snapshot(config);before_blobs=blobs(ar.root)
    package=extract(config,nominal)
    recovered=recover(package,{ar.archive_id:str(ar.root)})
    aux=auxiliary([plan1,plan2]);q=load_json((FIXTURE/'request-pit.json').read_bytes())
    t,l=materialize(package,recovered,aux,q['derivedAt']);publish(args.workspace/'materialized',t,l)
    assert read(args.workspace/'materialized')==(t,l)
    for plan in (plan1,plan2):
        cid=plan.result['manifest.json']['calculation_id']
        c=next(c for c in t['calculations'] if c['calculation_id']==cid)
        original=[s for s in plan.result['statistics.json'] if s['coverage_revision_id']==c['coverage_revision_id']]
        assert c['statistics']==[{k:s[k] for k in ('team','role','foundation','eligible_n','epa_n','success_n','epa_missing_n','epa_nonfinite_n','epa_sum')} for s in original]
        assert any(s['artifact_id']==plan.artifact_id for s in package['selection'])
    pit=select(t,q);assert pit['blocks'][0]['coverage']['expectedGames'] is None and pit['blocks'][0]['aggregates']==[]
    publish_result(args.workspace/'pit',pit)
    request=retrospective(t,q);r=select(t,request);publish_result(args.workspace/'reconstruction',r)
    assert r['blocks'][0]['coverage']['expectedGames']==3
    assert r['blocks'][0]['coverage']['sourceRatio']['exact']=='1/3'
    assert r['blocks'][0]['coverage']['gaps'][0]['gameId']=='synthetic-5'
    assert r['guarantees']['knowledgeAtCutoff']=='NOT_DEMONSTRATED'
    general=next(a for a in r['blocks'][0]['aggregates'] if a['role']=='off' and a['foundation']=='general' and a['scope']=='AUDITABLE_SUBSET_UNKNOWN')
    assert general['sums']['epa_sum']=='-1' and general['epa']['exact']=='-1/3' and general['volume']==3
    repo=Path(__file__).resolve().parents[4]
    java_reports={}
    for name in ('pit','reconstruction'):
        command=[str(args.java),'-jar',str(repo/'core-api/target/core-api-0.1.0.jar'),'metrics-temporal-read','--artifact',str(args.workspace/name)]
        completed=subprocess.run(command,capture_output=True,text=True,check=True,timeout=60)
        java_reports[name]=completed.stdout.strip()
        assert r['result_id'] in completed.stdout if name=='reconstruction' else pit['result_id'] in completed.stdout
        if name=='reconstruction':assert 'EPA=-1/3 volume=3' in completed.stdout
    after=snapshot(config);unchanged_archive=before_blobs==blobs(ar.root);assert before==after and unchanged_archive
    # PostgreSQL itself enforces the transaction's read-only property, even for a writer-member login.
    conn=connect(config)
    try:
        conn.set_session(readonly=True,isolation_level='REPEATABLE READ')
        with conn.cursor() as cur:
            cur.execute('show transaction_read_only');assert cur.fetchone()==('on',)
            import psycopg2
            try:cur.execute('insert into metrics_private.metric_archive_blob (sha256,byte_length) values (%s,%s)', ('0'*64,0))
            except psycopg2.errors.ReadOnlySqlTransaction:readonly=True
            else:raise AssertionError('Read-only transaction accepted DELETE')
        conn.rollback()
    finally:conn.close()
    assert snapshot(config)==before
    # Negative integration fixture: writer accepts a legitimate two-game batch;
    # materializer refuses incompatible temporal identity contract without output.
    pm,bm,planm,_=build(args.workspace/'multi',multi=True,archive=ar)
    persist(planm,ar.root,config)
    before_multi=snapshot(config);before_multi_blobs=blobs(ar.root)
    extracted_multi=extract(config,pm['selection'])
    try:materialize(extracted_multi,recover(extracted_multi,{ar.archive_id:str(ar.root)}),auxiliary([planm]),q['derivedAt'])
    except ContractGap as e:gap=str(e)
    else:raise AssertionError('Batch identity gap silently bypassed')
    assert before_multi==snapshot(config) and before_multi_blobs==blobs(ar.root)
    # Reproducible commands consume these new explicit documents, never implicit DB.
    for name,value in [('relations',package),('archives',{ar.archive_id:str(ar.root)}),('auxiliary',aux),('selection',nominal),('request-pit',q),('request-reconstruction',request)]:
        (args.workspace/(name+'.json')).write_bytes(json_bytes(value))
    report={'base':'8f583c4ec9ed83f86c2229b0f1656d32403bcc31','scope':'REAL_POSTGRESQL_AND_JAVA_SUPPORTED_PATH',
        'instance':{k:config[k] for k in ('host','port','database','instance_id')},'writerReports':writes,
        'relationCounts':{t:len(rows) for t,rows in before.items()},'snapshotBeforeSha256':identity(before),
        'snapshotAfterSha256':identity(after),'allRowsIncludingPersistedAtUnchanged':before==after,
        'archiveBlobsReceiptsMarkerUnchanged':unchanged_archive,
        'archiveBeforeHashes':before_blobs,'transactionReadOnlyEnforced':readonly,
        'materialization_id':l['materialization_id'],'temporalInputId':l['temporalInputId'],
        'originalIds':nominal,'pit':{'result_id':pit['result_id'],'coverage':pit['blocks'][0]['coverage'],'guarantees':pit['guarantees']},
        'reconstruction':{'result_id':r['result_id'],'coverage':r['blocks'][0]['coverage'],'general':general,'guarantees':r['guarantees']},
        'java':java_reports,'batchContractGap':gap,'batchReadUnchanged':before_multi==snapshot(config),
        'fullDeliveryComplete':False,'supabaseStackAndAdvisors':'PENDING_SEPARATE','workspace':str(args.workspace.resolve())}
    with args.output.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps({'supportedPath':'PASS','fullDelivery':'BLOCKED_BY_BATCH_ID_CONTRACT','readOnly':readonly,'java':True}))


if __name__=='__main__':main()
