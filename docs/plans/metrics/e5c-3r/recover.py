"""Bounded real recovery; existing runtimes, fresh destinations, no historical rewrites."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[4]
BASE = 'ce06a6291d1a2e935871fef04f543a54489755f5'
sys.path[:0] = [str(ROOT/'etl-pipeline/src'), str(ROOT/'docs/plans/metrics/e5b-6')]
import backfill as b
from audit import encoded, sha, ledger, summary, compare, compare_legacy, legacy_ledger
from nfl_sideline_etl.offline_metrics.artifact import json_bytes
from nfl_sideline_etl.metrics_materialization.postgres import extract
from nfl_sideline_etl.metrics_materialization.recovery import recover
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.publication import publish, read as read_materialized
from nfl_sideline_etl.metrics_observations.publication import generate, read
from nfl_sideline_etl.metrics_observations.core import COUNT_MAP
from nfl_sideline_etl.metrics_persistence.connection import configuration

SOURCES = {
 'pbp/season=2025/pbp.parquet':'5ed293fdf54d79e34426133829f3111faf577db29b8cfc25cf910d75eb55b2ef',
 'pbp/season=2026/pbp.parquet':'4e3707397912babcd0d7d02abd3be95db8e66785250e62bf9d874f37229d895e',
 'schedules/season=2025/schedules.parquet':'56818014e9d3d8f42bbfa5e8f787f1c6c412a4fe3f38b55b3d40a8ee3ce10a91',
 'schedules/season=2026/schedules.parquet':'fe33824f2d7519a7e550feccedb66d670d0de1af83e27c5af6084c45f488f81d'}
PG = '/nix/var/nix/profiles/default/bin/'


def now(): return datetime.now(timezone.utc).isoformat()
def save(path, value):
    with Path(path).open('xb') as f: f.write(encoded(value))
def command(args, *, input=None, check=True):
    r = subprocess.run(list(map(str,args)), input=input, capture_output=True, timeout=60)
    if check and r.returncode:
        # Do not print SQL/credentials supplied through stdin.
        raise RuntimeError(f'{args[0]} failed ({r.returncode}): {r.stderr.decode()[:1500]}')
    return r

def hashes(root):
    assert not any(p.is_symlink() for p in root.rglob('*'))
    return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}

def freeze(original, w):
    import polars as pl
    entries=[]
    for rel, expected in SOURCES.items():
        p=original/'etl-pipeline/data/raw'/rel
        assert p.is_file() and not p.is_symlink()
        actual=sha(p)
        assert actual==expected, f'DIFFERENT_SOURCE_REVISION: {p} {actual}; original preserved'
        f=pl.read_parquet(p); dest=w/'data/raw'/rel
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);dest.chmod(0o444)
        assert sha(dest)==expected==sha(p)
        entries.append(dict(relative=rel,path=str(p),frozen_path=str(dest),sha256=actual,bytes=p.stat().st_size,
            schema={k:str(v) for k,v in f.schema.items()},rows=f.height,
            seasons=sorted(f['season'].unique().to_list()),weeks=sorted(f['week'].unique().to_list()),
            phases=sorted(f['season_type' if rel.startswith('pbp/') else 'game_type'].unique().to_list()),
            games=sorted(f['game_id'].unique().to_list()),participants=sorted({t for k in ('posteam','defteam','home_team','away_team') if k in f.columns for t in f[k].drop_nulls().unique().to_list()}),
            completeness='UNKNOWN',epaModel='UNKNOWN',historicalAvailability='UNKNOWN',historicalIngestion='UNKNOWN',eventClosure='UNKNOWN'))
    assert sum(e['bytes'] for e in entries)==14995734
    inputs={'inputsVersion':1,'seasons':{str(s):{'calendar':[str(w/f'data/raw/schedules/season={s}/schedules.parquet')],
        'pbp':[str(w/f'data/raw/pbp/season={s}/pbp.parquet')],'metadata':None} for s in (2025,2026)}}
    save(w/'inventory.json',{'files':entries,'scope':'EXACT_FOUR_FILES','acquisition':False});save(w/'inputs.json',inputs)
    return inputs['seasons']


def code_inventory():
    paths=command(['git','ls-files','contracts/metrics','etl-pipeline/src/nfl_sideline_etl','etl-pipeline/tests',
                   'etl-pipeline/run_pipeline.py','etl-pipeline/load_games.py','etl-pipeline/load_metrics.py',
                   'etl-pipeline/seed_teams.py','etl-pipeline/run_local.py',
                   'docs/plans/metrics/e5b-6','docs/plans/metrics/e5b-5/proof.py','web-ui/build','web-ui/local-editorial',
                   'supabase/migrations']).stdout.decode().splitlines()
    result={}
    for p in paths:
        raw=command(['git','show',f'{BASE}:{p}']).stdout
        expected=hashlib.sha256(raw).hexdigest(); assert sha(ROOT/p)==expected,p
        result[p]=expected
    return result


class Instance:
    """New cluster only; relay preserves actual accepted backend endpoint checks."""
    def __init__(self, ops, image):
        self.ops=ops;self.image=image; self.created=False; self.started=False
        uid=str(uuid.uuid4());self.name='nfl-e5c3r-'+uid
        with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
        self.marker=dict(instance_id=uid,purpose='metrics-persistence-e5b2-disposable',
            database='nfl_e5b2_'+uid.replace('-','')[:12],port=self.port,container=self.name,image=image)
    def docker(self,*args,**kw):return command(['docker',*args],**kw)
    def execute(self,*args,**kw):return self.docker('exec','-i',self.name,*args,**kw)
    def sql(self, text, database='postgres'):
        return self.execute(PG+'psql','-X','-v','ON_ERROR_STOP=1','-h','/own','-p',self.port,
                            '-U','postgres','-d',database,input=text.encode()).stdout.decode()
    def start(self):
        o=self.ops;o.mkdir(mode=0o777);o.chmod(0o777)
        save(o/'INSTANCE.json',self.marker)
        (o/'relay.sh').write_text(f'#!/bin/sh\nexec /usr/bin/nc 127.0.0.1 {self.port}\n');(o/'relay.sh').chmod(0o755)
        boot=f'{PG}initdb -D /own/data -U postgres --auth-local=trust --auth-host=scram-sha-256 --encoding=UTF8 --no-locale > /own/initdb.log 2>&1 && {PG}pg_ctl -D /own/data -l /own/postgres.log -w start -o "-h 127.0.0.1 -p {self.port} -k /own" && exec /usr/bin/nc -lk -p 65432 -e /own/relay.sh'
        self.docker('create','--pull','never','--name',self.name,'--label',f'nfl.e5c3r.uuid={self.marker["instance_id"]}',
            '--user','100:101','--network','bridge','-p',f'127.0.0.1:{self.port}:65432',
            '--mount',f'type=bind,src={o},dst=/own','--entrypoint','/bin/sh',self.image,'-c',boot)
        self.created=True;self.docker('start',self.name);self.started=True
        for _ in range(100):
            r=self.execute(PG+'pg_isready','-h','/own','-p',self.port,check=False)
            if r.returncode==0:break
            time.sleep(.1)
        else:raise RuntimeError('Own PostgreSQL failed readiness; files preserved')
        self.sql(f'create database {self.marker["database"]};')
        self.sql('create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls; grant usage on schema public to public;\n'+
            '\n'.join(p.read_text() for p in sorted((ROOT/'supabase/migrations').glob('*.sql'))),self.marker['database'])
        writer,domain=secrets.token_urlsafe(24),secrets.token_urlsafe(24)
        self.sql(f"""
create role nfl_e5b2_writer login inherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls password '{writer}';
grant metric_persistence_writer to nfl_e5b2_writer;
create schema e5b2_instance; revoke all on schema e5b2_instance from public;
grant usage on schema e5b2_instance to metric_persistence_writer;
create table e5b2_instance.identity(instance_id uuid primary key, purpose text not null);
revoke all on e5b2_instance.identity from public;
grant select on e5b2_instance.identity to metric_persistence_writer;
insert into e5b2_instance.identity values ('{self.marker['instance_id']}','{self.marker['purpose']}');
create role nfl_e5b5_domain login inherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls password '{domain}';
grant usage on schema public,e5b2_instance to nfl_e5b5_domain;
grant select on e5b2_instance.identity to nfl_e5b5_domain;
"""+'\n'.join(f'grant select,insert,update on public.{t} to nfl_e5b5_domain; create policy e5b5_domain_local on public.{t} to nfl_e5b5_domain using (true) with check (true);' for t in ('teams','games','market_implied','team_week_metrics','ingestion_runs'))+
        '\ngrant usage on sequence public.ingestion_runs_id_seq to nfl_e5b5_domain;',self.marker['database'])
        for label,user,password in [('writer','nfl_e5b2_writer',writer),('domain','nfl_e5b5_domain',domain)]:
            p=o/(label+'.json');save(p,dict(host='127.0.0.1',port=self.port,database=self.marker['database'],user=user,password=password,instance_id=self.marker['instance_id']));p.chmod(0o600)
        return configuration(o/'writer.json'),configuration(o/'domain.json')
    def stop(self):
        if not self.created:return {'created':False}
        labels=json.loads(self.docker('inspect','--format','{{json .Config.Labels}}',self.name).stdout)
        assert labels['nfl.e5c3r.uuid']==self.marker['instance_id']
        status=None;pid_absent=None
        if self.started:
            r=self.execute(PG+'pg_ctl','-D','/own/data','-m','fast','-w','stop',check=False)
            status=self.execute(PG+'pg_ctl','-D','/own/data','status',check=False).returncode
            pid_absent=self.execute('/bin/sh','-c','test ! -f /own/data/postmaster.pid',check=False).returncode==0
            assert status==3 and pid_absent, 'own cluster shutdown failed'
            self.docker('stop',self.name)
        running=json.loads(self.docker('inspect','--format','{{json .State.Running}}',self.name).stdout)
        with socket.socket() as s:s.bind(('127.0.0.1',self.port))
        listener=command(['lsof','-nP',f'-iTCP:{self.port}','-sTCP:LISTEN'],check=False)
        assert not listener.stdout and not running
        return dict(pgCtlStatus=status,pidAbsent=pid_absent,containerRunning=running,listenerAbsent=True,portBindReleased=True,filesPreserved=True,container=self.name,port=self.port)


def request_for(t,l):
    # Same nominal cohort as E5c-2, with the new associations and actual derivation time.
    q=json.loads((ROOT/'docs/plans/metrics/e5c-2/real-request.json').read_bytes())
    q['source']={'materializationId':l['materialization_id'],'temporalInputId':l['temporalInputId']};q['derivedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    calendars={(r['payload']['season'],r['payload']['phase']):r for r in t['resources'] if r['kind']=='CALENDAR'}
    choices={a['calculation_id']:a for a in l['relations']['selection']}
    for req in q['requests']:
        cal=calendars[req['season'],req['phase']];req['calendarSourceSetId']=cal['dependencies'][0];req['calendarRevisionId']=cal['revision_id']
        associations=[]
        for g in cal['payload']['games']:
            if g['week'] not in req['weeks'] or not set(req['teams']) & {g['home_team'],g['away_team']}:continue
            rows=[r for r in l['relations']['relations']['metric_calculation_coverage'] if r['game_id']==g['game_id']];assert len(rows)==1
            r=rows[0];choice=choices[r['calculation_id']]
            cs=[c for c in t['calculations'] if c['game']['game_id']==g['game_id'] and c['calculation_id']==r['calculation_id']];assert len(cs)<=1
            associations.append(dict(gameId=g['game_id'],calculationId=r['calculation_id'],coverageRevisionId=r['coverage_revision_id'],
                artifactId=choice['artifact_id'],archiveId=choice['archive_id'],temporalRevisionId=cs[0]['revision_id'] if cs else None))
        assert {a['gameId'] for a in associations}=={a['gameId'] for a in req['associations']}
        req['associations']=associations
    return q


def reconcile_docs(t,docs,manifest):
    by={c['revision_id']:c for c in t['calculations']};compared=0
    historical=json.loads((ROOT/'docs/plans/metrics/e5c-2/real-observations.json').read_bytes())
    def key(d):return (d['subject']['team'],d['subject']['role'],d['subject']['foundation'],d['request']['season'],d['request']['phase'],tuple(d['request']['period']['weeks']))
    old={key(d):d for d in historical};assert len(docs)==len(old)==48
    for d in docs:
        associations=manifest['lineageByObservation'][d['observationId']]['associations'];rows=[]
        for m in d['members']:
            a=next(a for a in associations if a['gameId']==m['gameId'])
            if m['statistics'] is None:assert a['temporalRevisionId'] is None;continue
            c=by[a['temporalRevisionId']]
            row=next(s for s in c['statistics'] if (s['team'],s['role'],s['foundation'])==(d['subject']['team'],d['subject']['role'],d['subject']['foundation']))
            general=next(s for s in c['statistics'] if (s['team'],s['role'],s['foundation'])==(d['subject']['team'],d['subject']['role'],'general'))
            for camel,snake in COUNT_MAP.items():assert m['statistics'][camel]==row[snake]
            assert m['statistics']['generalEligibleN']==general['eligible_n'];assert m['statistics']['epaSum']==row['epa_sum'];rows.append(row);compared+=1
        if rows:
            for camel,snake in COUNT_MAP.items():assert d['totals'][camel]==sum(s[snake] for s in rows)
            epa=sum((Fraction(Decimal(s['epa_sum'])) for s in rows if s['epa_n']),Fraction(0))
            if d['totals']['epaN']:assert Fraction(Decimal(d['values']['epa']['numerator']))/d['values']['epa']['denominator']==epa/sum(s['epa_n'] for s in rows)
        else:assert d['totals'] is None and all(v is None for v in d['values'].values())
        for k in ('values','totals','subject','observed','presentation'):
            assert d[k]==old[key(d)][k],(key(d),k)
        assert {k:v for k,v in d['request'].items() if k!='selectionManifestId'}=={k:v for k,v in old[key(d)]['request'].items() if k!='selectionManifestId'}
        for dimension,g in d['guarantees'].items():
            assert {k:v for k,v in g.items() if k!='evidenceIds'}=={k:v for k,v in old[key(d)]['guarantees'][dimension].items() if k!='evidenceIds'}
        assert d['guarantees']['temporal']['state']=='UNKNOWN' and d['guarantees']['temporal']['targetGameId'] is None
        assert d['guarantees']['completeness']['state']=='UNKNOWN' and d['guarantees']['coverage']['expectedCount'] is None
        assert d['guarantees']['compatibility']['epaModel']['state']=='UNKNOWN'
    assert compared==72
    return dict(observations=len(docs),memberGroupsReconciled=compared,historicalExtractNumbersEqual=True,
                historicalExtractUsedAsSource=False,gapGameIds=sorted({m['gameId'] for d in docs for m in d['members'] if m['sourceState']=='ABSENT'}))


def verify_copy(w, backup):
    before=hashes(w);assert before==hashes(backup)
    frozen=json.loads((backup/'SHA256SUMS.json').read_bytes())
    assert frozen=={k:v for k,v in before.items() if k!='SHA256SUMS.json'}
    hidden=w.with_name(w.name+'.copy-proof-hidden');assert not hidden.exists()
    w.rename(hidden)
    try:
        copied=json.loads((backup/'recovery-report.json').read_bytes())
        relocated=None
        if copied['success']:
            td,ld=read_materialized(backup/'materialized');ds,m=read(backup/'bundle')
            assert m['bundleId']==copied['bundleId'] and len(ds)==48
            # Receipts intentionally bind their recorded archive_root. Never rewrite them.
            rr=json.loads((backup/'relations.json').read_bytes())
            try:recover(rr,{copied['first']['2025']['archive_id']:str(backup/'archive')})
            except ValueError as e:
                assert str(e)=='Archive receipt integrity mismatch';relocated=str(e)
            else:raise AssertionError('Expected path-bound archive receipt rejection')
            for blob in (backup/'archive/blobs/sha256').glob('*/*'):assert sha(blob)==blob.name
        proof=dict(primaryTemporarilyUnavailable=True,fullFileHashesEqual=True,
            materializationAndBundleRead=bool(copied['success']),archiveBlobHashesChecked=bool(copied['success']),
            relocatedArchiveReceiptRefusal=relocated,archiveRecoveryAtDifferentPath='NOT_SUPPORTED_BY_ACCEPTED_RECEIPT_CONTRACT',
            backup=str(backup),primary=str(w),at=now(),sameDisk=True,disasterRecovery=False)
    finally:hidden.rename(w)
    assert hashes(w)==before==hashes(backup)
    return proof


def run(args):
    w,backup,ops=args.primary,args.backup,args.operations
    for p in (w,backup,ops):
        assert p.is_absolute() and not p.exists() and '/web-ui/' not in str(p) and '/tmp/' not in str(p)
    assert len({str(p) for p in (w,backup,ops)})==3
    assert not any(p.is_relative_to(q) for p in (w,backup,ops) for q in (w,backup,ops) if p!=q)
    assert shutil.disk_usage(w.parent if w.parent.exists() else args.original).free>=2*1024**3
    os.environ['PYTHONPATH']=str(ROOT/'etl-pipeline/src')
    code=code_inventory();image=json.loads(command(['docker','image','inspect',args.image]).stdout)[0]
    assert image['Id']==args.image, 'Use complete immutable local image ID'
    w.mkdir(parents=True);ops.parent.mkdir(parents=True,exist_ok=True)
    report=dict(kind='E5C3R_REAL_RECOVERY',base=BASE,startedAt=now(),testedHead=command(['git','rev-parse','HEAD']).stdout.decode().strip(),
        primary=str(w),backup=str(backup),operations=str(ops),success=False,acquisition=False,remote=False)
    save(w/'accepted-code-hashes.json',code)
    instance=Instance(ops,args.image)
    try:
        sources=freeze(args.original,w)
        save(w/'preflight.json',dict(at=now(),python=sys.version,pythonExecutable=sys.executable,
            imageId=image['Id'],imageRepoDigests=image.get('RepoDigests'),bytesFree=shutil.disk_usage(w).free,
            nativeRuntime='MISSING',runtime='Existing local Docker PostgreSQL 17.6; no pull',
            containersBefore=command(['docker','ps','--format','{{.ID}} {{.Names}}']).stdout.decode(),protocolSha256=sha(Path(__file__).with_name('PROTOCOL.md'))))
        print('Offline plan and independent reconciliation before database start',flush=True)
        plans=b.pipeline(w,'plan');ledgers={};report['independent']={};report['phaseTotals']=[]
        for s,selection in sources.items():
            season=int(s);led=ledger(selection['calendar'],selection['pbp']);ledgers[season]=led
            art=b.artifact(plans[season]);compare(led,art['game-audit.json'],art['statistics.json'],art['manifest.json'])
            report['independent'][s]=summary(led)
            for phase,target in (('REG',(272,32813) if season==2025 else (32,3830)),('POST',(13,1689))):
                gids={g for g,a in led['audits'].items() if a['phase']==phase}
                if not gids:continue
                observed=sum(led['audits'][g]['unique_n']>0 for g in gids)
                eligible=sum(v['eligible_n'] for (g,t,r,f),v in led['statistics'].items() if g in gids and r=='off' and f=='general')
                assert (observed,eligible)==target
                report['phaseTotals'].append(dict(season=season,phase=phase,observedGames=observed,eligible=eligible,completeness='UNKNOWN'))
        save(w/'before-load.json',report)
        print('Starting own UUID PostgreSQL cluster',flush=True)
        private,domain=instance.start();report['instance']=instance.marker
        assert not any(b.prior.snapshots(private).values())
        assert b.query(domain,'select game_id from public.games')==[]
        report['endpointAndRoles']=b.query(domain,'select current_user,host(inet_server_addr()) as address,inet_server_port() as port,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication from pg_roles where rolname=current_user')
        first=b.pipeline(w,'integrated',ops);report['first']=first
        for season,led in ledgers.items():
            art=b.artifact(first[season]);compare(led,art['game-audit.json'],art['statistics.json'],art['manifest.json'])
            assert first[season]['global_status']=='SUCCEEDED' and first[season]['stage_result']=='PERSISTED'
            assert first[season]['calculation_id']==plans[season]['calculation_id']
            sql=b.query(domain,'select game_id,season,week,game_type,home_team,away_team from public.games where season=%s',(season,))
            assert {r['game_id'] for r in sql}==set(led['games'])
            from audit import phase as normalize_phase
            for r in sql:
                expected=led['games'][r['game_id']]
                assert all(r[k]==expected[k] for k in ('game_id','season','week','home_team','away_team'))
                assert normalize_phase(r['game_type'])==(expected['phase'],expected['round'])
            report['independent'][str(season)]['legacy']=compare_legacy(legacy_ledger(sources[str(season)]['pbp']),b.query(domain,'select * from public.team_week_metrics where season=%s',(season,)))
        snapshot=b.prior.snapshots(private);cas=hashes(w/'archive');journals=hashes(w/'integrated')
        save(w/'private-snapshot.json',snapshot)
        report['repeat']=repeat=b.pipeline(w,'repeat',ops)
        assert snapshot==b.prior.snapshots(private) and cas==hashes(w/'archive') and journals==hashes(w/'integrated')
        for s in first:
            assert repeat[s]['writer_counts']['inserted']==0
            for k in ('calculation_id','artifact_id','coverages','descriptors','archive_id','receipts'):assert repeat[s].get(k)==first[s].get(k)
            assert repeat[s]['attempt_id']!=first[s]['attempt_id']
        report['idempotence']=dict(allRowsAndPersistedAtUnchanged=True,archiveAndReceiptsUnchanged=True,journalsUnchanged=True)
        choices=[{k:r[k] for k in ('calculation_id','artifact_id','archive_id')} for r in first.values()]
        relations=extract(private,choices);rs=relations['relations'];coverage={r['coverage_revision_id']:r for r in rs['game_metric_coverage_revision']}
        for season,led in ledgers.items():
            art=b.artifact(first[season]);assocs=[r for r in rs['metric_calculation_coverage'] if r['calculation_id']==first[season]['calculation_id']]
            assert {coverage[r['coverage_revision_id']]['game_id'] for r in assocs}==set(led['games']) and len(assocs)==len(led['games'])
            selected={r['coverage_revision_id'] for r in assocs};stats=[r for r in rs['team_game_metric_sums'] if r['coverage_revision_id'] in selected]
            compare(led,[coverage[r['coverage_revision_id']]['audit_json'] for r in assocs],[r['record_json'] for r in stats],art['manifest.json'])
            for r in stats:
                for k in ('eligible_n','epa_n','success_n','epa_missing_n','epa_nonfinite_n'):assert r[k]==r['record_json'][k]
                assert (r['epa_sum'] is None and r['record_json']['epa_sum'] is None) or Decimal(r['epa_sum'])==Decimal(r['record_json']['epa_sum'])
        assert len(rs['metric_calculation_coverage'])==557 and len(rs['team_game_metric_sums'])==3804
        save(w/'relations.json',relations);save(w/'selection.json',choices)
        save(w/'ingestion-runs.json',json.loads(json.dumps(b.query(domain,'select * from public.ingestion_runs order by id'),default=str)))
        buffers=recover(relations,{first[2025]['archive_id']:str(w/'archive')})
        auxiliary=json.loads((ROOT/'etl-pipeline/tests/fixtures/metrics_materialization/auxiliary-empty.json').read_bytes())
        t,l=materialize(relations,buffers,auxiliary,now());publish(w/'materialized',t,l)
        assert read_materialized(w/'materialized')==(t,l)
        report['materialization']={'materialization_id':l['materialization_id'],'input_id':l['temporalInputId'],'version':l['materializationVersion'],'inputVersion':t['inputVersion']}
        q=request_for(t,l);save(w/'request.json',q)
        manifest=generate(w/'materialized',q,w/'bundle');docs,reread=read(w/'bundle');assert manifest==reread
        report['projection']=reconcile_docs(t,docs,manifest);report['bundleId']=manifest['bundleId']
        config={'configVersion':'metrics-lab-config-v1','bundles':[dict(entryId='real-recovery',label='Arquivo 2026 W1, W2, W1–2; NE POST2025; lacuna BAL W3',dataKind='REAL_ARCHIVE',path=str(w/'bundle'),expectedBundleId=manifest['bundleId'])]}
        save(w/'lab-config.json',config);save(w/'review-observations.json',docs)
        assert code_inventory()==code
        assert all(sha(args.original/'etl-pipeline/data/raw'/rel)==expected for rel,expected in SOURCES.items())
        report['success']=True
    except Exception as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc)}
        raise
    finally:
        report['shutdown']=instance.stop();report['finishedAt']=now()
        save(w/'recovery-report.json',report)
        save(w/'SHA256SUMS.json',hashes(w))
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(w,backup)
        assert hashes(w)==hashes(backup)
        proof=verify_copy(w,backup)
        save(args.report,report|{'backupProof':proof,'fileManifestSha256':sha(w/'SHA256SUMS.json')})
    print(json.dumps({'success':report['success'],'bundleId':report.get('bundleId'),'primary':str(w),'backup':str(backup)}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('original','primary','backup','operations','report'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--image',required=True)
    a=p.parse_args();assert not a.report.exists();run(a)
