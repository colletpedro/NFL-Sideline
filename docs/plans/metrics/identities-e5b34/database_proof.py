"""Full original batch and shared coverage proof on own NEW real PostgreSQL."""
import argparse
from pathlib import Path
import json
import subprocess
from fixture_support import fixture, model_batch
import importlib.util
_spec=importlib.util.spec_from_file_location('historical_e5b4_proof',Path(__file__).resolve().parents[1]/'e5b-4/database_proof.py')
_old=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_old)
snapshot,blobs,retrospective=_old.snapshot,_old.blobs,_old.retrospective
from nfl_sideline_etl.metrics_persistence.connection import configuration
from nfl_sideline_etl.metrics_persistence.writer import persist
from nfl_sideline_etl.metrics_materialization.postgres import extract
from nfl_sideline_etl.metrics_materialization.recovery import recover
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.publication import publish,read
from nfl_sideline_etl.offline_metrics.artifact import identity,json_bytes
from nfl_sideline_etl.temporal_metrics.core import select
from nfl_sideline_etl.temporal_metrics.__main__ import publish as publish_result


def flow(config,choices,plans,ar,root,java,*,include_target=False):
    before=snapshot(config);before_archive=blobs(ar.root)
    p=extract(config,choices);b=recover(p,{ar.archive_id:str(ar.root)});aux=fixture.auxiliary(plans)
    q=fixture.load_json((fixture.FIXTURE/'request-pit.json').read_bytes())
    if include_target:q['targetGameId']='outside-inventory'
    t,l=materialize(p,b,aux,q['derivedAt']);publish(root/'materialized',t,l)
    assert read(root/'materialized')==(t,l)
    original_associations=p['relations']['metric_calculation_coverage']
    assert len(original_associations)==4*len(plans)
    for c in t['calculations']:
        plan=next(plan for plan in plans if plan.result['manifest.json']['calculation_id']==c['calculation_id'])
        a=next(a for a in plan.result['game-audit.json'] if a['coverage_revision_id']==c['coverage_revision_id'])
        assert c['original']=={'manifest':plan.result['manifest.json'],'coverage':a}
        original=[s for s in plan.result['statistics.json'] if s['coverage_revision_id']==c['coverage_revision_id']]
        assert c['statistics']==[{k:s[k] for k in ('team','role','foundation','eligible_n','epa_n','success_n','epa_missing_n','epa_nonfinite_n','epa_sum')} for s in original]
    pit=select(t,q);rq=retrospective(t,q);result=select(t,rq)
    assert pit['blocks'][0]['coverage']['expectedGames'] is None and pit['blocks'][0]['aggregates']==[]
    assert result['guarantees']['knowledgeAtCutoff']=='NOT_DEMONSTRATED'
    assert len(result['calculationsUsed'])==(3 if include_target else 2)
    assert result['blocks'][0]['coverage']['expectedGames']==(4 if include_target else 3)
    assert result['blocks'][0]['coverage']['sourceRatio']['exact']==('1/4' if include_target else '1/3')
    assert [g['gameId'] for g in result['blocks'][0]['coverage']['gaps']]==['synthetic-5']
    general=next(a for a in result['blocks'][0]['aggregates'] if a['role']=='off' and a['foundation']=='general' and a['scope']=='AUDITABLE_SUBSET_UNKNOWN')
    assert general['volume']==(4 if include_target else 3)
    if not include_target:assert general['epa']['exact']=='-1/3' and general['sums']['epa_sum']=='-1'
    assert any(a['scope']=='COMPLETE' and a['volume']==0 and a['sums']['epa_sum'] is None for a in result['blocks'][0]['aggregates'])
    java_reports={}
    for name,value in [('pit',pit),('reconstruction',result)]:
        publish_result(root/name,value)
        command=[str(java),'-jar',str(fixture.ROOT/'core-api/target/core-api-0.1.0.jar'),'metrics-temporal-read','--artifact',str(root/name)]
        completed=subprocess.run(command,capture_output=True,text=True,check=True,timeout=60)
        assert value['result_id'] in completed.stdout;java_reports[name]=completed.stdout.strip()
    for name,value in [('relations',p),('archives',{ar.archive_id:str(ar.root)}),('auxiliary',aux),('selection',choices),('request-pit',q),('request-reconstruction',rq)]:
        (root/(name+'.json')).write_bytes(json_bytes(value))
    after=snapshot(config);after_archive=blobs(ar.root)
    assert before==after and before_archive==after_archive
    assert result['input_id']==l['temporalInputId']
    return {'originalIds':choices,'associations':original_associations,
        'coverageIds':[a['coverage_revision_id'] for a in p['relations']['game_metric_coverage_revision']],
        'sourceIds':[a['revision_id'] for a in p['relations']['metric_source_revision']],
        'receipts':p['relations']['metric_archive_receipt'],
        'relationCounts':{k:len(v) for k,v in before.items()},
        'snapshotBeforeSha256':identity(before),'snapshotAfterSha256':identity(after),
        'allRowsIncludingPersistedAtUnchanged':before==after,'archiveBlobsReceiptsMarkerUnchanged':before_archive==after_archive,
        'archiveBeforeHashes':before_archive,'archiveAfterHashes':after_archive,
        'materialization_id':l['materialization_id'],'temporalInputId':l['temporalInputId'],
        'pit':{'result_id':pit['result_id'],'coverage':pit['blocks'][0]['coverage'],'guarantees':pit['guarantees']},
        'reconstruction':{'result_id':result['result_id'],'coverage':result['blocks'][0]['coverage'],
            'general':general,'guarantees':result['guarantees'],'calculationIds':[c['calculation_id'] for c in result['calculationsUsed']]},
        'java':java_reports}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance-root',type=Path,required=True);parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--java',type=Path,required=True)
    args=parser.parse_args()
    if args.workspace.exists() or args.output.exists():parser.error('New workspace/output required')
    if not str(args.instance_root.resolve()).startswith('/private/tmp/nfl-e5b4-instance-'):parser.error('Own new root required')
    config=configuration(args.instance_root/'writer.json')
    marker=fixture.load_json((args.instance_root/'INSTANCE.json').read_bytes())
    assert marker['instance_id']==config['instance_id'] and not any(snapshot(config).values())
    args.workspace.mkdir()
    p,b,plan,ar=fixture.build(args.workspace/'original',multi=True)
    writer=[persist(plan,ar.root,config)]
    original=flow(config,p['selection'],[plan],ar,args.workspace/'original-flow',args.java)
    p2,model=model_batch(args.workspace/'model',ar,'epa-v2');writer.append(persist(model,ar.root,config))
    assert model.result['game-audit.json']==plan.result['game-audit.json'] and model.result['statistics.json']==plan.result['statistics.json']
    assert model.result['manifest.json']['calculation_id']!=plan.result['manifest.json']['calculation_id']
    shared=flow(config,p['selection']+p2['selection'],[plan,model],ar,args.workspace/'shared-flow',args.java)
    p3,second=model_batch(args.workspace/'second',ar,'UNKNOWN',second_game=True);writer.append(persist(second,ar.root,config))
    nonempty=flow(config,p3['selection'],[second],ar,args.workspace/'nonempty-flow',args.java,include_target=True)
    conn=_old.connect(config)
    try:
        conn.set_session(readonly=True,isolation_level='REPEATABLE READ')
        with conn.cursor() as cur:
            cur.execute('show transaction_read_only');assert cur.fetchone()==('on',)
            import psycopg2
            try:cur.execute('insert into metrics_private.metric_archive_blob (sha256,byte_length) values (%s,%s)',('0'*64,0))
            except psycopg2.errors.ReadOnlySqlTransaction:readonly=True
            else:raise AssertionError('Read-only transaction accepted INSERT')
        conn.rollback()
    finally:conn.close()
    report={'base':'f2d946593d1e6b2ed32ad1aa331c630f271c44db','scope':'REAL_POSTGRESQL_AND_JAVA_FULL_BATCH',
        'instance':{k:config[k] for k in ('host','port','database','instance_id')},'writerReports':writer,
        'originalBatch':original,'sharedCoverageModelChange':shared,'twoNonemptyAndEmpty':nonempty,
        'transactionReadOnlyEnforced':readonly,'fullDeliveryComplete':True,'supabaseStackAndAdvisors':'PENDING_SEPARATE',
        'workspace':str(args.workspace.resolve())}
    with args.output.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps({'fullBatch':'PASS','sharedCoverage':'PASS','twoNonempty':'PASS','readOnly':readonly,'java':True}))


if __name__=='__main__':main()
