"""Own disposable PostgreSQL proof, real pipeline and freshly rebuilt Java JAR.

No downloads, .env or external database. Always shuts down only its own cluster.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT/'etl-pipeline'), str(ROOT/'etl-pipeline/src'), str(ROOT/'etl-pipeline/tests')]
from metrics_pipeline_support import fixtures, specification
import run_pipeline as pipeline
from nfl_sideline_etl import metrics_pipeline as stage
from nfl_sideline_etl.offline_metrics.artifact import json_bytes
from nfl_sideline_etl.metrics_persistence.connection import configuration, connect
from nfl_sideline_etl.metrics_persistence.writer import TABLES
from nfl_sideline_etl.metrics_materialization.postgres import extract
from nfl_sideline_etl.metrics_materialization.recovery import recover
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.publication import publish, read
from nfl_sideline_etl.temporal_metrics.core import select
from nfl_sideline_etl.temporal_metrics.__main__ import publish as publish_result

module_spec=importlib.util.spec_from_file_location('e5b2_own_instance', ROOT/'docs/plans/metrics/e5b-2/instance.py')
instance=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(instance)


def snapshots(config):
    conn=connect(config)
    try:
        with conn.cursor() as cur:
            rows={}
            for table in TABLES:
                cur.execute('select row_to_json(t)::text from metrics_private.'+table+' t')
                rows[table]=sorted(r[0] for r in cur.fetchall())
            return rows
    finally:conn.close()


def file_hashes(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def domain_login(root, marker):
    import psycopg2
    from psycopg2 import sql
    secret=secrets.token_urlsafe(24)
    conn=psycopg2.connect(host=str(root),port=marker['port'],dbname=marker['database'],user='postgres')
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute('create role nfl_e5b5_domain login inherit nosuperuser nocreatedb nocreaterole '
                            'noreplication nobypassrls password %s',(secret,))
                cur.execute('grant usage on schema public,e5b2_instance to nfl_e5b5_domain; '
                            'grant select on e5b2_instance.identity to nfl_e5b5_domain')
                # Disposable instance only. Versioned schema and RLS remain unchanged.
                for table in ('teams','games','market_implied','team_week_metrics','ingestion_runs'):
                    cur.execute(sql.SQL('grant select,insert,update on public.{} to nfl_e5b5_domain').format(sql.Identifier(table)))
                    cur.execute(sql.SQL('create policy e5b5_domain_local on public.{} to nfl_e5b5_domain using (true) with check (true)').format(sql.Identifier(table)))
                cur.execute('grant usage on sequence public.ingestion_runs_id_seq to nfl_e5b5_domain')
    finally:conn.close()
    config=dict(host='127.0.0.1',port=marker['port'],database=marker['database'],user='nfl_e5b5_domain',
                password=secret,instance_id=marker['instance_id'])
    path=root/'domain.json';path.write_bytes(json_bytes(config));path.chmod(0o600)
    return configuration(path)


def real_statuses(domain):
    conn=stage.connect_legacy(domain)
    try:
        with conn.cursor() as cur:
            cur.execute('select id,season,status,rows_pbp,rows_games,error_message from public.ingestion_runs order by id')
            return cur.fetchall()
    finally:conn.close()


def last_report(root):
    attempt=next(root.iterdir())
    return json.loads(sorted(attempt.glob('*.json'))[-1].read_text())


def execute(workspace,source,root,label,*,seasons=(2026,),failure=None,data_dir=None,allow_missing=False):
    args=['--game-metrics','local','--skip-acquire','--data-dir',str(data_dir or workspace/'data'),
          '--metrics-inputs',str(source),'--metrics-output',str(workspace/label),
          '--legacy-local-config',str(root/'domain.json'),'--metrics-local-config',str(root/'writer.json'),
          '--metrics-archive',str(workspace/'archive')]
    for s in seasons:args+=['--season',str(s)]
    if allow_missing:args+=['--allow-missing-pbp']
    original_event=stage.Attempt.event
    if failure:
        def event(self,s,**kw):
            original_event(self,s,**kw)
            if s==failure:raise RuntimeError('controlled boundary '+s)
        stage.Attempt.event=event
    try:
        status=pipeline.main(args)
    finally:stage.Attempt.event=original_event
    assert status==(1 if failure else 0)
    return last_report(workspace/label)


def temporal(workspace,private,report,java):
    choices=[{k:report[k] for k in ('calculation_id','artifact_id','archive_id')}]
    relations=extract(private,choices)
    buffers=recover(relations,{report['archive_id']:report['archive_root']})
    auxiliary=json.loads((ROOT/'etl-pipeline/tests/fixtures/metrics_materialization/auxiliary-empty.json').read_text())
    # No tactical or historical documents invented. Current batch alone is unqualified PIT.
    package,lineage=materialize(relations,buffers,auxiliary,'2026-10-12T12:00:00Z')
    assert package['inputVersion']=='metrics-temporal-input-v3'
    publish(workspace/'materialized',package,lineage)
    assert read(workspace/'materialized')==(package,lineage)
    request=json.loads((ROOT/'etl-pipeline/tests/fixtures/metrics_materialization/request-pit.json').read_text())
    request['derivedAt']='2026-10-12T12:00:00Z'
    result=select(package,request)
    assert result['algorithmVersion']=='metrics-temporal-1.1.0'
    assert result['resultVersion']=='metrics-temporal-result-v3'
    assert all(b['aggregates']==[] and b['coverage']['expectedGames'] is None for b in result['blocks'])
    publish_result(workspace/'temporal-pit',result)
    jar=ROOT/'core-api/target/core-api-0.1.0.jar'
    completed=subprocess.run([str(java),'-jar',str(jar),'metrics-temporal-read','--artifact',str(workspace/'temporal-pit')],
                             capture_output=True,text=True,timeout=60,check=True)
    assert result['result_id'] in completed.stdout
    (workspace/'relations.json').write_bytes(json_bytes(relations))
    return {'calculation_id':report['calculation_id'],'artifact_id':report['artifact_id'],
            'materialization_id':lineage['materialization_id'],'input_id':result['input_id'],
            'result_id':result['result_id'],'audit_id':result['audit_id'],
            'javaOutput':completed.stdout.strip(),'jarSha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
            'PIT':'UNKNOWN_NO_AGGREGATES','associations':len(relations['relations']['metric_calculation_coverage']),
            'statisticsRows':len(relations['relations']['team_game_metric_sums'])}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('instance-root','workspace','output','pg-bin','java'):parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args()
    if args.workspace.exists() or args.output.exists() or args.instance_root.exists():parser.error('New roots/output required')
    args.workspace.mkdir(parents=True)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    marker=None
    evidence={'proofVersion':'metrics-pipeline-proof-v1','scope':'REAL_OWN_POSTGRESQL_SYNTHETIC',
              'base':'b6b244bb68f17d089135f8ad3665747bb6c140c5',
              'testedHead':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'supabaseFullAndAdvisors':'PENDING','workspace':str(args.workspace),
              'testedSourceHashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  (ROOT/'etl-pipeline/run_pipeline.py',ROOT/'etl-pipeline/src/nfl_sideline_etl/metrics_pipeline.py',
                   ROOT/'etl-pipeline/tests/metrics_pipeline_support.py',Path(__file__))}}
    try:
        marker=instance.start(args.instance_root,args.pg_bin,port)
        evidence['instance']=marker
        private=configuration(args.instance_root/'writer.json');domain=domain_login(args.instance_root,marker)
        assert not any(snapshots(private).values())
        # Prove actual writer cannot serve as legacy loader; no grants expanded.
        conn=connect(private)
        try:
            with conn.cursor() as cur:
                cur.execute("select has_table_privilege(current_user,'public.teams','INSERT')")
                assert cur.fetchone()==(False,)
        finally:conn.close()
        evidence['writerCannotSeedTeams']=True
        entry=fixtures(args.workspace/'data',metadata=False)
        source=specification(args.workspace/'inputs.json',{2026:entry})
        # Same real legacy orchestrator/API and unchanged defaults, explicit own connection only.
        disabled=pipeline.run_pipeline((2026,),data_dir=args.workspace/'data',allow_missing_pbp=False,
            skip_acquire=True,connection_factory=lambda:stage.connect_legacy(domain))[0]
        assert (disabled.rows_games,disabled.rows_market,disabled.rows_pbp,disabled.rows_metrics)==(4,1,4,2)
        assert not any(snapshots(private).values())
        evidence['disabled']={k:v for k,v in vars(disabled).items()}
        first=execute(args.workspace,source,args.instance_root,'integrated')
        assert first['global_status']=='SUCCEEDED' and first['stage_result']=='PERSISTED'
        # Independent expectations, not counts copied from the implementation.
        stats=json.loads(next((args.workspace/'integrated').glob('*/artifact/statistics.json')).read_text())
        s=next(s for s in stats if s['game_id']=='synthetic-1' and s['team']=='A' and s['role']=='off' and s['foundation']=='general')
        assert (s['eligible_n'],s['epa_n'],s['epa_missing_n'],s['success_n'],s['epa_sum'])==(3,2,1,1,'-0.5')
        assert (first['reconciliation']['pbp_raw_n'],first['reconciliation']['pbp_unique_n'])==(6,5)
        before=snapshots(private);cas_before=file_hashes(args.workspace/'archive')
        repeat=execute(args.workspace,source,args.instance_root,'repeat')
        assert repeat['attempt_id']!=first['attempt_id'] and repeat['artifact_id']==first['artifact_id']
        assert repeat['writer_counts']['inserted']==0 and repeat['writer_counts']['reused']>0
        assert before==snapshots(private) and cas_before==file_hashes(args.workspace/'archive')
        evidence['idempotence']={'allPrivateRowsIncludingPersistedAtPreserved':True,'archiveReceiptsPreserved':True,'counts':repeat['writer_counts']}
        # Correction changes one unique row; prior content/receipts remain.
        import polars as pl
        original=Path(entry['pbp'][0])
        pl.read_parquet(original).with_columns(pl.when(pl.col('play_id')==2).then(pl.lit(-1.25)).otherwise(pl.col('epa')).alias('epa')).write_parquet(original)
        corrected=execute(args.workspace,source,args.instance_root,'corrected')
        after=snapshots(private)
        assert corrected['calculation_id']!=first['calculation_id'] and len(after['metric_calculation'])==2
        assert all(set(rows)<=set(after[t]) for t,rows in before.items())
        assert all(file_hashes(args.workspace/'archive')[p]==h for p,h in cas_before.items())
        evidence['correction']={'previousRowsAndReceiptsPreserved':True,'first':first['calculation_id'],'corrected':corrected['calculation_id']}
        # New legitimate revision with COMPLETE empty and game without observation.
        entry=fixtures(args.workspace/'data')
        source=specification(source,{2026:entry})
        entry2=fixtures(args.workspace/'data',2027,metadata=False)
        multi=specification(args.workspace/'multi-inputs.json',{2026:entry,2027:entry2})
        before_failure=snapshots(private)
        failed=execute(args.workspace,multi,args.instance_root,'failed-after-archive',seasons=(2026,2027),failure='ARCHIVED')
        assert failed['global_status']=='FAILED' and failed['stage_result']=='FAILED'
        assert snapshots(private)==before_failure
        assert all(row[1]!=2027 for row in real_statuses(domain))
        archived=file_hashes(args.workspace/'archive')
        recovered=execute(args.workspace,source,args.instance_root,'recovered')
        assert recovered['receipts']==failed['receipts']
        assert all(file_hashes(args.workspace/'archive')[p]==h for p,h in archived.items())
        evidence['failureRecovery']={'failedAttempt':failed['attempt_id'],'recoveredAttempt':recovered['attempt_id'],
            'sameArtifact':failed['artifact_id']==recovered['artifact_id'],'sameReceipts':True,
            'nextSeasonNotProcessed':True,'privateUnchangedOnFailure':True}
        # Private content remains valid when failure happens after private commit.
        committed=snapshots(private)
        failed_commit=execute(args.workspace,multi,args.instance_root,'failed-after-private',seasons=(2026,2027),failure='PRIVATE_COMMITTED')
        assert failed_commit['stage_result']=='PERSISTED' and failed_commit['global_status']=='FAILED'
        assert committed==snapshots(private)
        assert all(row[1]!=2027 for row in real_statuses(domain))
        recovery2=execute(args.workspace,source,args.instance_root,'recovered-commit')
        assert recovery2['writer_counts']['inserted']==0 and committed==snapshots(private)
        evidence['afterCommitFailure']={'global':'FAILED','private':'PERSISTED','recoveryReused':recovery2['writer_counts']['reused']}
        # The privileged probe is provisioned only on this own disposable instance.
        import psycopg2
        privileged_secret=secrets.token_urlsafe(24)
        with psycopg2.connect(host=str(args.instance_root),port=port,dbname=marker['database'],user='postgres') as admin:
            with admin.cursor() as cur:
                cur.execute('create role nfl_e5b5_privileged login createdb password %s',(privileged_secret,))
                cur.execute('grant usage on schema e5b2_instance to nfl_e5b5_privileged; grant select on e5b2_instance.identity to nfl_e5b5_privileged')
        # Actual endpoint/role guard checks.
        for name, changes in [('remote',{'host':'example.invalid'}),('admin',{'user':'nfl_e5b5_privileged','password':privileged_secret})]:
            bad={**dict(domain),**changes};p=args.workspace/(name+'-guard.json');p.write_bytes(json_bytes(bad))
            try:
                c=stage.connect_legacy(configuration(p))
            except Exception as exc:
                if name=='admin':assert isinstance(exc,ValueError) and 'Privileged' in str(exc)
                evidence[name+'Refused']=True
            else:c.close();raise AssertionError(name+' accepted')
            p.unlink()
        temporal_before=snapshots(private);archive_before=file_hashes(args.workspace/'archive')
        evidence['temporal']=temporal(args.workspace,private,recovered,args.java)
        assert snapshots(private)==temporal_before and file_hashes(args.workspace/'archive')==archive_before
        evidence['readsDidNotMutateSQLOrArchive']=True
        evidence['first']=first;evidence['newBatch']=recovered
        before_absent=snapshots(private)
        missing_entry=fixtures(args.workspace/'data-missing',missing=True)
        missing_source=specification(args.workspace/'missing-inputs.json',{2026:missing_entry})
        absent=execute(args.workspace,missing_source,args.instance_root,'missing',data_dir=args.workspace/'data-missing',allow_missing=True)
        assert absent['stage_result']=='UNAVAILABLE_MISSING_PBP' and 'calculation_id' not in absent
        assert snapshots(private)==before_absent
        empty_entry=fixtures(args.workspace/'data-empty',empty=True)
        empty_source=specification(args.workspace/'empty-inputs.json',{2026:empty_entry})
        empty=execute(args.workspace,empty_source,args.instance_root,'empty',data_dir=args.workspace/'data-empty',allow_missing=True)
        assert empty['stage_result']=='PERSISTED' and empty['statistics']==12 and empty['pbp_state']=='EMPTY_PRESENT'
        evidence['absenceAndEmpty']={'missing':absent,'empty':empty,'missingDidNotPersist':True}
        evidence['runs']=real_statuses(domain)
        evidence['success']=True
    finally:
        if marker:
            instance.stop(args.instance_root,args.pg_bin)
            status=subprocess.run([str(args.pg_bin/'pg_ctl'),'-D',str(args.instance_root/'data'),'status'],capture_output=True,text=True)
            with socket.socket() as probe:probe.bind(('127.0.0.1',port))
            evidence['shutdown']={'pgCtlStatus':status.returncode,'pidAbsent':not (args.instance_root/'data/postmaster.pid').exists(),'portBindReleased':True,'filesPreserved':True}
            assert status.returncode==3 and evidence['shutdown']['pidAbsent']
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x') as stream:json.dump(evidence,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps({'success':evidence['success'],'instance':marker['instance_id'],'port':port,'shutdown':evidence['shutdown']}))


if __name__=='__main__':main()
