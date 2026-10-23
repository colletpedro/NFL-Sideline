"""Exact new paths only; old consumers, source trees and public bytes unchanged."""
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
BASE='d7e8aa35c7ea6605fd443992668b2b1d2c8fe7d2'
REF=Path('/Users/pedrocollet/.codex/worktrees/broadcast-explorer-v1/NFL Sideline')
ART=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1')


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def hashes(path):
    assert not any(p.is_symlink() for p in path.rglob('*'))
    return {str(p.relative_to(path)):'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}


def allowed(p):
    return p.startswith(('docs/plans/broadcast-comparison-foundation-v1/','etl-pipeline/src/nfl_sideline_etl/comparison_foundation/')) or p=='etl-pipeline/tests/test_comparison_foundation.py'


changed=sorted(set(git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines()))
assert all(allowed(p) for p in changed),changed
# Git compares every historical tracked path, including public snapshots, UI,
# all old contracts/readers, Spring, weekly ETL, migrations and previous gates.
tracked=git('ls-tree','-r','--name-only',BASE).decode().splitlines()
assert not any(allowed(p) for p in tracked)
assert not git('diff',BASE,'--',*[p for p in tracked]).strip()
assert (ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(')==5
receipt=json.loads((ART/'bundle-reconciled/source-receipt.json').read_bytes())
for path,expected in receipt['sources'].items():
    assert hashes(Path(path))==expected,path
assert hashes(ART/'bundle-reconciled')==hashes(ART/'verified-copy')==hashes(ART/'reproduced-bundle')
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in ('.js','.css')}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
responses={}
for port in (18098,18099,18100):
    responses[port]={}
    for route,header in (('/__situational/','X-Local-Situational'),('/__observations/','X-Local-Observations')):
        with urlopen(Request(f'http://127.0.0.1:{port}'+route,headers={header:'1'})) as r:
            responses[port][route]=json.load(r)
assert responses[18098]==responses[18099]==responses[18100]
assert responses[18100]['/__situational/']['data']==json.loads((ART/'bundle-reconciled/sources/situational/situational.json').read_bytes())
assert responses[18100]['/__situational/']['bundleId']=='sha256:2af2a33211c09658fb6b831188dc5c5ac3bee9b3fc4b2b6008748921ac7c339c'
listeners={}
for port,pid in ((18098,49375),(18099,64333),(18100,74464)):
    listener=subprocess.check_output(['lsof','-nP','-a','-p',str(pid),f'-iTCP:{port}','-sTCP:LISTEN']).decode()
    assert f'127.0.0.1:{port}' in listener;listeners[port]=listener
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REF).decode().strip()==BASE
assert subprocess.check_output(['git','status','--porcelain'],cwd=REF)==b''
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
report=dict(base=BASE,referenceCleanAtExactHead=True,changed=changed,allHistoricalTrackedPathsUnchanged=True,
            historicalFilesCompared=len(tracked),fiveExpectedFailuresUnchanged=True,publicBuildHashes=public,
            preservedSourceTreesUnchanged=True,durableCopiesByteIdentical=True,legacyHttpThreeInstancesIdentical=True,
            situationalDocuments=192,listeners=listeners)
(HERE/'checks/isolation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
