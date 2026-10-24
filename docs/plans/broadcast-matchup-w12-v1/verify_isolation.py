"""Exact historical-file/public/source/listener preservation; no environment file."""
from http.client import HTTPConnection
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE='d82d4a6eafb85acb3cd9c94736a2160a4036281f'
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd)
changed=set(git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines())
def allowed(p):return p in ('.gitignore','web-ui/broadcast-journey/Discovery.tsx','etl-pipeline/tests/test_matchup_w12.py','web-ui/vite.w12.config.ts','web-ui/tsconfig.w12.json','web-ui/scripts/w12-dev.mjs') or p.startswith(('docs/plans/broadcast-matchup-w12-v1/','etl-pipeline/src/nfl_sideline_etl/matchup_w12/','web-ui/broadcast-journey/w12/','web-ui/build/w12'))
assert all(allowed(p) for p in changed),sorted(p for p in changed if not allowed(p))
history=git('ls-tree','-r','--name-only',BASE).decode().splitlines();untouched=[p for p in history if p not in ('.gitignore','web-ui/broadcast-journey/Discovery.tsx')]
assert not git('diff',BASE,'--',*untouched)
assert (ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(')==5
ref=Path('/Users/pedrocollet/.codex/worktrees/broadcast-comprehension-v1/NFL Sideline')
assert git('rev-parse','HEAD',cwd=ref).decode().strip()==BASE and not git('status','--porcelain',cwd=ref)
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in ('.js','.css')}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
private_js='\n'.join(p.read_text() for p in (ROOT/'web-ui/w12-dist/assets').glob('*.js'))
assert '/__matchup-w12/' in private_js and 'broadcast-matchup-w12-v1' in private_js
assert json.loads((HERE/'source-config.json').read_bytes())['expectedBundleId'] in private_js
assert '/__matchup-w12/' not in '\n'.join(p.read_text() for p in (ROOT/'web-ui/dist/assets').glob('*.js'))
wire=[]
for port in (18102,18103,18104):
    c=HTTPConnection('127.0.0.1',port,timeout=15);c.request('GET','/__matchup-reading/',headers={'X-Local-Matchup':'1'});response=c.getresponse();b=response.read();assert response.status==200
    original=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled/comparison.json')
    assert b==original.read_bytes();wire.append(dict(port=port,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()));c.close()
listeners={}
expected={18098:30244,18099:30251,18100:30265,18101:95101,18102:97976,18103:44780}
for port,pid in expected.items():
    text=subprocess.check_output(['lsof','-nP','-a','-p',str(pid),f'-iTCP:{port}','-sTCP:LISTEN'],text=True)
    assert f'127.0.0.1:{port}' in text;listeners[port]=pid
# Every original pilot file, including copies of frozen sources, remains byte identical.
manifest=json.loads((HERE/'collection-manifest.json').read_bytes());cfg=json.loads((HERE/'source-config.json').read_bytes());bundle=Path(cfg['path'])
receipt=json.loads((bundle/'source-receipt.json').read_bytes());pilot=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled')
assert receipt['pilotFiles']=={str(p.relative_to(pilot)):'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in pilot.rglob('*') if p.is_file()}
assert not (ROOT/'web-ui/public/data/index.json').exists()
assert manifest==json.loads((bundle/'COMPLETED.json').read_bytes())
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
report=dict(base=BASE,allowedChangedPaths=sorted(changed),untouchedHistoricalFiles=len(untouched),publicAssetHashes=public,
    oldPilotHttpUnchanged=wire,oldListeners= listeners,referenceWorktreeClean=True,fiveLegacyExpectedFailuresPreserved=True,
    originalFrozenSourceFilesUnchanged=True,privateCollectionOutsidePublic=True,privateBuildContainsW12Entry=True,publicBuildHasNoW12Endpoint=True,noBackendDatabaseEtlPublicationChanges=True)
(HERE/'checks/isolation.json').write_text(json.dumps(report,indent=2)+'\n');print('Isolation PASS; historical files, public hashes, pins and all six old listeners preserved')
