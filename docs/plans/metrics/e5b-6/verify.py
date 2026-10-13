"""E5b-6's own offline gate (historical verifiers left intact); never rewrites historical verifiers/evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[4]
BASE='f8a258b64116aa7f67f4d4d6253d3f00dc91f5e2'
PROTECTED=['etl-pipeline','docs/plans/metrics/e5b-5','docs/plans/metrics/e5b-5-review','contracts/metrics/e5a-v1','etl-pipeline/src/nfl_sideline_etl/offline_metrics',
    'etl-pipeline/src/nfl_sideline_etl/metrics_persistence','etl-pipeline/src/nfl_sideline_etl/metrics_materialization',
    'etl-pipeline/src/nfl_sideline_etl/temporal_metrics','etl-pipeline/src/nfl_sideline_etl/seasons.py',
    'etl-pipeline/load_metrics.py','etl-pipeline/load_games.py','etl-pipeline/seed_teams.py','etl-pipeline/run_local.py',
    'supabase','core-api','web-ui','.github','Spec.md','docs/current-state.md',
    *['docs/plans/metrics/'+p for p in ('e5b-1','e5b-2','e5b-3','e5b-3-review','e5b-4','e5b-4-review','identities-e5b34','identities-e5b34-review')]]


def run(*args):
    result=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
    if result.returncode:raise RuntimeError('Gate failed: '+str(args)+'\n'+result.stdout+result.stderr)
    return result.stdout,result.stderr


def python(*args):return run(sys.executable,'-B',*args)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('New output required')
    head=run('git','rev-parse','HEAD')[0].strip()
    if head!=args.candidate:parser.error('Gate must run on the exact declared candidate commit')
    if run('git','diff','HEAD','--','etl-pipeline',str(Path(__file__).relative_to(ROOT)))[0]:
        parser.error('Commit implementation/tests/gate before verification')
    if run('git','diff',BASE,'--',*PROTECTED)[0]:raise RuntimeError('Accepted/protected content changed')
    changed=run('git','diff','--name-only',BASE)[0].splitlines()
    allowed=('docs/plans/metrics/e5b-6/',)
    if any(not p.startswith(allowed) for p in changed):raise RuntimeError('Outside authorized integration scope')
    report={'gateVersion':'metrics-real-backfill-gate-v1','base':BASE,'candidate':head,
            'scope':'OFFLINE_ONLY','databaseConnected':False,'protectedPathsUnchanged':PROTECTED,
            'sourceHashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                [ROOT/'etl-pipeline/run_pipeline.py',*sorted((ROOT/'etl-pipeline/src').rglob('*.py')),
                 *sorted((ROOT/'etl-pipeline/tests').glob('*.py')),Path(__file__),Path(__file__).with_name('backfill.py'),Path(__file__).with_name('audit.py'),Path(__file__).with_name('freeze.py'),Path(__file__).with_name('instance.py'),Path(__file__).with_name('test_audit.py')]}}
    out,_=python('-m','pytest','etl-pipeline','-q','-p','no:cacheprovider')
    if re.search(r'\d+ (failed|skipped|xfailed)',out):raise RuntimeError('Offline suite has failures/skips')
    report['etlTestsPassed']=int(re.search(r'(\d+) passed',out).group(1));report['etlLog']=out
    report['independentAuditorTests']=python('-m','pytest','docs/plans/metrics/e5b-6/test_audit.py','-q','-p','no:cacheprovider')[0]
    report['e5aVerifier']=json.loads(python('contracts/metrics/e5a-v1/verify.py')[0])
    _,err=python('-m','unittest','discover','-s','contracts/metrics/e5a-v1','-p','test_*.py','-v')
    report['e5aTestsPassed']=int(re.search(r'Ran (\d+) tests',err).group(1))
    report['e5aFrozenHashes']=json.loads(python('docs/plans/metrics/e5a-review/reproduce_boundary.py')[0])
    with tempfile.TemporaryDirectory(prefix='nfl-e5b6-offline-gate-') as temp:
        temp=Path(temp)
        fixture=ROOT/'etl-pipeline/tests/fixtures/offline_metrics'
        artifact=temp/'adapter'
        python('-m','nfl_sideline_etl.offline_metrics','--calendar',fixture/'calendar.json','--pbp',fixture/'pbp.json',
            '--metadata',fixture/'metadata.json','--season','2026','--output',artifact)
        accepted=ROOT/'docs/plans/metrics/e5b-1/synthetic-result'
        for p in accepted.iterdir():assert p.read_bytes()==(artifact/p.name).read_bytes()
        report['e5b1ByteHashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in accepted.iterdir()}
        ar=temp/'archive-must-not-exist'
        report['e5b2DryRun']=json.loads(python('-m','nfl_sideline_etl.metrics_persistence','--dry-run','--artifact',artifact,
            '--calendar',fixture/'calendar.json','--pbp',fixture/'pbp.json','--archive',ar)[0])
        assert not ar.exists() and report['e5b2DryRun']['database_connected'] is False
        counter=temp/'counterexamples.json'
        python('docs/plans/metrics/e5b-3/correction-1.0.1/reproduce.py','--output',counter)
        actual=json.loads(counter.read_text())['cases']
        expected=json.loads((ROOT/'docs/plans/metrics/e5b-3/correction-1.0.1/counterexamples-after.json').read_text())['cases']
        assert actual==expected;report['temporalCounterexamples']=actual
        proof=temp/'identities.json';artifacts=temp/'identities'
        python('docs/plans/metrics/identities-e5b34/reproduce.py','--output',proof,'--artifacts',artifacts)
        report['identitiesMaterializerRegression']=json.loads(proof.read_text())['after']
        after=report['identitiesMaterializerRegression']
        assert after['observedGames']==['synthetic-1','synthetic-6'] and len(after['associations'])==4
        assert after['coverage']['expectedGames']==3 and after['coverage']['sourceRatio']['exact']=='1/3'
        # New archives have new receipts; temporal input/audit identities may change.
        # Verify golden integrity independently rather than requiring those new IDs to match.
        from nfl_sideline_etl.offline_metrics.artifact import identity
        report['preservedTemporalArtifacts']={}
        for name in ('pit','reconstruction'):
            golden=ROOT/'docs/plans/metrics/identities-e5b34/examples'/name
            result=json.loads((golden/'result.json').read_text())
            marker=json.loads((golden/'COMPLETED.json').read_text())
            sha=hashlib.sha256((golden/'result.json').read_bytes()).hexdigest()
            assert marker['files']['result.json']==sha
            assert identity({k:v for k,v in result.items() if k!='audit_id'})==result['audit_id']
            assert result['resultVersion']=='metrics-temporal-result-v3' and result['algorithmVersion']=='metrics-temporal-1.1.0'
            report['preservedTemporalArtifacts'][name]={'sha256':sha,'result_id':result['result_id'],'audit_id':result['audit_id']}
        report['freshArchiveTemporalIdentitiesValidated']=True
    run('git','diff','--check',BASE);report['diffCheck']='PASSED'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:json.dump(report,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps({k:report[k] for k in ('candidate','etlTestsPassed','e5aTestsPassed','diffCheck')}))


if __name__=='__main__':main()
