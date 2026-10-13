"""Bounded real-data proof. Existing runtimes only; own cluster always stopped.

Freeze must precede execution; no acquisition, dotenv, remote SQL or publication.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import traceback

from audit import compare, compare_legacy, encoded, ident, ledger, legacy_ledger, sha, summary
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'etl-pipeline'),str(ROOT/'etl-pipeline/src')]
from nfl_sideline_etl.metrics_persistence.connection import configuration
from nfl_sideline_etl.metrics_materialization.postgres import extract
from nfl_sideline_etl.metrics_materialization.recovery import recover
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.publication import publish, read
from nfl_sideline_etl.temporal_metrics.core import select
from nfl_sideline_etl.temporal_metrics.__main__ import publish as publish_result
from nfl_sideline_etl.metrics_pipeline import connect_legacy


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


instance=module('e5b6_instance',Path(__file__).with_name('instance.py'))
# Reuse minimum-domain-grants and immutable snapshot helpers exactly as accepted.
sys.path.insert(0,str(ROOT/'etl-pipeline/tests'))
prior=module('e5b5_helpers',ROOT/'docs/plans/metrics/e5b-5/proof.py')


def run(args,log):
    result=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=600)
    log.write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(f'Command failed ({result.returncode}); preserved log {log}')


def reports(output):
    return {int(d.name.split('-')[0]):json.loads(sorted(d.glob('*.json'))[-1].read_text()) | {'artifact_root':str(d/'artifact')} for d in output.iterdir() if d.is_dir()}


def pipeline(workspace, label, root=None):
    args=[sys.executable,'-B',ROOT/'etl-pipeline/run_pipeline.py','--season','2025','--season','2026',
          '--game-metrics','local' if root else 'plan','--metrics-inputs',workspace/'inputs.json','--metrics-output',workspace/label]
    if root:args+=['--skip-acquire','--data-dir',workspace/'data','--legacy-local-config',root/'domain.json',
                  '--metrics-local-config',root/'writer.json','--metrics-archive',workspace/'archive']
    run(args,workspace/(label+'.log'))
    return reports(workspace/label)


def frozen(workspace):
    inventory=json.loads((workspace/'inventory.json').read_text());inputs=json.loads((workspace/'inputs.json').read_text())['seasons']
    for e in inventory['files']:
        assert sha(e['path'])==e['sha256'],'Original changed: preserve and identify a new revision'
        if e['selected']:assert sha(e['frozen_path'])==e['sha256']
    for season,selection in inputs.items():
        observed=sorted(str(p) for p in (workspace/'data/raw/pbp'/('season='+season)).glob('*.parquet'))
        assert observed==sorted(selection['pbp']) and selection['metadata'] is None
    return inventory,inputs


def artifact(report):
    path=Path(report['artifact_root']) if 'artifact_root' in report else None
    if path is None:raise ValueError('artifact root absent')
    return {p.name:json.loads(p.read_text()) for p in path.glob('*.json')}


def query(domain,sql,params=()):
    conn=connect_legacy(domain)
    try:
        with conn.cursor() as cur:
            cur.execute(sql,params);cols=[c.name for c in cur.description]
            return [dict(zip(cols,r)) for r in cur.fetchall()]
    finally:conn.close()


def references(led):
    result={}
    for label,predicate in [('pass_and_rush',lambda a:a['unique_n']>0 and all(any(s['eligible_n']>0 for (g,t,r,f),s in led['statistics'].items() if g==a['game_id'] and r=='off' and f==kind) for kind in ('classified_pass','classified_rush'))),
                            ('excluded_plays',lambda a:a['excluded_n']>0),('no_observation',lambda a:a['unique_n']==0),
                            ('postseason',lambda a:a['phase']=='POST'),('missing_epa',lambda a:any(s['epa_missing_n'] for (g,*_),s in led['statistics'].items() if g==a['game_id'])),
                            ('different_pass_rush_volume',lambda a:any(led['statistics'][a['game_id'],t,'off','classified_pass']['eligible_n']!=led['statistics'][a['game_id'],t,'off','classified_rush']['eligible_n'] for t in (a['home_team'],a['away_team'])) if a['unique_n'] else False)]:
        a=next((a for _,a in sorted(led['audits'].items()) if predicate(a)),None)
        result[label]=dict(audit=a,statistics=[dict(game_id=g,team=t,role=r,foundation=f,**{k:str(v) if k=='epa_sum' else v for k,v in s.items()}) for (g,t,r,f),s in led['statistics'].items() if a and g==a['game_id']]) if a else {'observed':False}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ('workspace','instance-root','pg-bin','java','output'):parser.add_argument('--'+k,type=Path,required=True)
    args=parser.parse_args();w=args.workspace
    if args.output.exists() or args.instance_root.exists():parser.error('New instance/output required')
    inventory,inputs=frozen(w)
    report=dict(proofVersion='metrics-real-backfill-e5b6-v1',base='f8a258b64116aa7f67f4d4d6253d3f00dc91f5e2',
                testedHead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
                workspace=str(w),instanceRoot=str(args.instance_root),acquisition=False,remote=False,supabaseFullAndAdvisors='PENDING',success=False)
    marker=None
    try:
        plans=reports(w/'plan') if (w/'plan').exists() else pipeline(w,'plan')
        ledgers={};report['plan']={};report['independent']={};report['references']={}
        for s,selection in inputs.items():
            season=int(s);led=ledger(selection['calendar'],selection['pbp']);ledgers[season]=led
            art=artifact(plans[season]);sets=compare(led,art['game-audit.json'],art['statistics.json'],art['manifest.json'])
            assert plans[season]['global_status']=='NOT_STARTED' and plans[season]['stage_result']=='PLANNED'
            report['plan'][s]={k:plans[season].get(k) for k in ('attempt_id','calculation_id','artifact_id','stage_result','global_status')}
            report['independent'][s]=summary(led)|{'sourceSetIds':sets,'allGameAuditsAndSufficientStatisticsMatch':True}
            report['references'][s]=references(led)
        frozen(w)  # all independent checks pass before administration or first write
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        marker=instance.start(args.instance_root,args.pg_bin,port);report['instance']=marker
        private=configuration(args.instance_root/'writer.json');domain=prior.domain_login(args.instance_root,marker)
        assert not any(prior.snapshots(private).values())
        assert query(domain,'select game_id from public.games')==[],'own harness must not seed fixtures'
        report['roles']=query(domain,'select current_user,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=current_user')
        first=pipeline(w,'integrated',args.instance_root);report['first']=first
        for season,led in ledgers.items():
            a=artifact(first[season]);compare(led,a['game-audit.json'],a['statistics.json'],a['manifest.json'])
            assert first[season]['global_status']=='SUCCEEDED' and first[season]['stage_result']=='PERSISTED'
            assert first[season]['calculation_id']==plans[season]['calculation_id']
            sql_games=query(domain,'select game_id,season,week,game_type,home_team,away_team from public.games where season=%s',(season,))
            actual={r['game_id']:r for r in sql_games}
            assert set(actual)==set(led['games'])
            for gid,g in led['games'].items():
                r=actual[gid]
                for k in ('game_id','season','week','home_team','away_team'):assert r[k]==g[k]
                from audit import phase
                assert phase(r['game_type'])==(g['phase'],g['round'])
            report['independent'][str(season)]['calendarSqlMatched']=len(actual)
            sql_week=query(domain,'select * from public.team_week_metrics where season=%s',(season,))
            canonical=[w/'data/raw/pbp'/f'season={season}'/'pbp.parquet']
            report['independent'][str(season)]['legacy']=compare_legacy(legacy_ledger(canonical),sql_week)
        before=prior.snapshots(private);cas=prior.file_hashes(w/'archive');journal=prior.file_hashes(w/'integrated')
        (w/'private-before.json').write_bytes(encoded(before));(w/'archive-before.json').write_bytes(encoded(cas))
        repeat=pipeline(w,'repeat',args.instance_root);report['repeat']=repeat
        assert before==prior.snapshots(private) and cas==prior.file_hashes(w/'archive') and journal==prior.file_hashes(w/'integrated')
        for season in first:
            assert repeat[season]['writer_counts']['inserted']==0
            for k in ('calculation_id','artifact_id','coverages','descriptors','archive_id','receipts'):assert repeat[season].get(k)==first[season].get(k)
            assert repeat[season]['attempt_id']!=first[season]['attempt_id']
        report['idempotence']=dict(allPrivateRowsIncludingPersistedAtPreserved=True,blobsAndReceiptsPreserved=True,previousJournalsPreserved=True,
            privateSnapshotSha256=sha(w/'private-before.json'),archiveFileHashesId=ident(cas),journalFileHashesId=ident(journal),
            tableRows={t:len(r) for t,r in before.items()},noRealCorrectionAvailable=inventory['noAdditionalRealRevisions'])
        report['ingestionRuns']=query(domain,'select * from public.ingestion_runs order by id')
        choices=[{k:r[k] for k in ('calculation_id','artifact_id','archive_id')} for r in first.values()]
        relations=extract(private,choices);report['selection']=choices
        # Independent association, membership, SQL numeric and record-json verification.
        rs=relations['relations'];coverage={r['coverage_revision_id']:r for r in rs['game_metric_coverage_revision']}
        for season,led in ledgers.items():
            a=artifact(first[season]);members={d['source_revision_id'] for d in a['manifest.json']['inputs']}
            selected_set_ids=set(report['independent'][str(season)]['sourceSetIds'].values())
            sql_members=[r for r in rs['metric_source_member'] if r['set_id'] in selected_set_ids]
            assert {r['source_id'] for r in sql_members}==members and len(sql_members)==len(a['manifest.json']['inputs'])
            associations=[r for r in rs['metric_calculation_coverage'] if r['calculation_id']==first[season]['calculation_id']]
            assert {coverage[r['coverage_revision_id']]['game_id'] for r in associations}==set(led['games']) and len(associations)==len(led['games'])
            sql_audits=[coverage[r['coverage_revision_id']]['audit_json'] for r in associations]
            sql_stats=[r for r in rs['team_game_metric_sums'] if r['coverage_revision_id'] in {r['coverage_revision_id'] for r in associations}]
            compare(led,sql_audits,[r['record_json'] for r in sql_stats],a['manifest.json'])
            for r in sql_stats:
                for k in ('eligible_n','epa_n','success_n','epa_missing_n','epa_nonfinite_n'):assert r[k]==r['record_json'][k]
                assert (r['epa_sum'] is None and r['record_json']['epa_sum'] is None) or Decimal(r['epa_sum'])==Decimal(r['record_json']['epa_sum'])
            report['independent'][str(season)]['sqlCompleteSourceSetsAndAssociationsMatched']=True
            report['independent'][str(season)]['sqlNumericSumsExactlyMatched']=len(sql_stats)
        (w/'relations.json').write_bytes(encoded(relations))
        buffers=recover(relations,{first[2025]['archive_id']:str(w/'archive')})
        auxiliary=json.loads((ROOT/'etl-pipeline/tests/fixtures/metrics_materialization/auxiliary-empty.json').read_text())
        derived=datetime.now(timezone.utc).isoformat()
        package,lineage=materialize(relations,buffers,auxiliary,derived)
        publish(w/'materialized',package,lineage);assert read(w/'materialized')==(package,lineage)
        report['materialization']=dict(version=lineage['materializationVersion'],inputVersion=package['inputVersion'],
            materialization_id=lineage['materialization_id'],input_id=lineage['temporalInputId'],
            associationCount=len(rs['metric_calculation_coverage']),coverageRows=len(coverage),statisticsRows=len(rs['team_game_metric_sums']),
            noObservationDiagnostics=sum(d['reason']=='NO_SOURCE_OBSERVATION' for d in lineage['diagnostics']),
            sourcesRecovered=len(rs['metric_source_revision']),auxiliaryEvidenceAdded=0)
        report['temporal']=[]
        for season,p in ((2025,'REG'),(2025,'POST'),(2026,'REG')):
            target=next(g for _,g in sorted(ledgers[season]['games'].items()) if g['phase']==p)
            request=dict(season=season,phase=p,team=target['home_team'],targetGameId=target['game_id'],targetWeek=target['week'],
                         mode='POINT_IN_TIME',windows=['SEASON_TO_CUTOFF'],derivedAt=derived,asOfInstant='2026-10-13T00:00:00Z')
            result=select(package,request);dest=w/f'temporal-{season}-{p}'
            assert result['algorithmVersion']=='metrics-temporal-1.1.0' and result['resultVersion']=='metrics-temporal-result-v3'
            assert all(b['aggregates']==[] and b['coverage']['expectedGames'] is None for b in result['blocks'])
            publish_result(dest,result);(dest/'request.json').write_bytes(encoded(request))
            log=w/f'java-{season}-{p}.txt'
            run([args.java,'-jar',ROOT/'core-api/target/core-api-0.1.0.jar','metrics-temporal-read','--artifact',dest],log)
            assert result['result_id'] in log.read_text()
            report['temporal'].append(dict(season=season,phase=p,request=request,result_id=result['result_id'],input_id=result['input_id'],audit_id=result['audit_id'],
                blocks=result['blocks'],javaOutput=log.read_text().strip(),resultSha256=sha(dest/'result.json'),mode='POINT_IN_TIME',state='UNKNOWN_NO_AGGREGATES'))
        report['jarSha256']=sha(ROOT/'core-api/target/core-api-0.1.0.jar');frozen(w)
        report['success']=True
    except Exception as exc:
        report['failure']=dict(type=type(exc).__name__,message=str(exc),classification='UNRESOLVED_DIAGNOSTIC; inspect preserved reproduction before assigning cause')
        (w/'failure-traceback.txt').write_text(traceback.format_exc())
        raise
    finally:
        if marker:
            instance.stop(args.instance_root,args.pg_bin)
            status=subprocess.run([str(args.pg_bin/'pg_ctl'),'-D',str(args.instance_root/'data'),'status'],capture_output=True,text=True)
            listener=subprocess.run(['lsof','-nP',f'-iTCP:{port}','-sTCP:LISTEN'],capture_output=True,text=True)
            with socket.socket() as probe:probe.bind(('127.0.0.1',port))
            report['shutdown']=dict(pgCtlStatus=status.returncode,pidAbsent=not (args.instance_root/'data/postmaster.pid').exists(),
                listenerAbsent=not bool(listener.stdout.strip()),portBindReleased=True,filesPreserved=True)
            assert status.returncode==3 and report['shutdown']['pidAbsent'] and report['shutdown']['listenerAbsent']
        def transport(v):
            if isinstance(v,(datetime,Decimal)):return str(v)
            raise TypeError(type(v).__name__)
        with args.output.open('x') as stream:json.dump(report,stream,sort_keys=True,indent=2,default=transport);stream.write('\n')
    print(json.dumps(dict(success=report['success'],shutdown=report['shutdown'])))


if __name__=='__main__':main()
