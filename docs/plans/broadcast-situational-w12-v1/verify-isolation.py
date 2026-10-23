"""Current delivery's explicit paths; all historical gates remain unchanged."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
BASE='3f4335691c9d4d126561ed03df4b775640cae7ed'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def hashes(p):return {str(x.relative_to(p)):hashlib.sha256(x.read_bytes()).hexdigest() for x in p.rglob('*') if x.is_file()}
allowed={'.gitignore','web-ui/broadcast-journey/App.tsx','web-ui/broadcast-journey/main.tsx','web-ui/vite.journey.config.ts','etl-pipeline/src/nfl_sideline_etl/situational.py','etl-pipeline/tests/test_situational.py','web-ui/build/situational.ts','web-ui/build/situational-process.mjs','web-ui/build/situational-process.d.mts'}
changed=git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines()
assert all(p in allowed or p.startswith(('docs/plans/broadcast-situational-w12-v1/','web-ui/broadcast-journey/situational/')) for p in changed),changed
# Every historical tracked file outside the exact authorized edits is byte-identical.
original=git('ls-tree','-r','--name-only',BASE).decode().splitlines()
for path in original:
 if path not in allowed:assert (ROOT/path).read_bytes()==git('show',BASE+':'+path),path
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in ['.js','.css']}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'},public
for p in (ROOT/'web-ui/dist/assets').iterdir():
 if p.suffix in ['.js','.css']:
  for marker in ['__situational','situational-v1','__observations','broadcast-journey','Archivo-Variable','RobotoCondensed-Variable']:assert marker not in p.read_text(),marker
reg=(ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_bytes();assert reg.count(b'  it.fails(')==5
copy=json.loads((HERE/'checks/copy.json').read_bytes());primary=Path(copy['primary']);portable=Path(copy['copy'])
assert hashes(primary)==hashes(portable)=={k:v[7:] for k,v in copy['files'].items()}
prov=json.loads((primary/'provenance.json').read_bytes())
assert hashes(Path(prov['source']))==prov['sourceHashes']==hashes(Path(prov['backup']))
assert hashes(Path(prov['oldBundlePath']))==prov['oldBundleHashes']
ref=Path('/Users/pedrocollet/.codex/worktrees/broadcast-live-hub-v1/NFL Sideline')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ref).decode().strip()==BASE
assert subprocess.check_output(['git','status','--porcelain'],cwd=ref)==b''
tracked=git('ls-files').decode().splitlines();assert not any(p.startswith('editorial/local-artifacts/broadcast-situational-w12-v1/') for p in tracked)
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
report=dict(base=BASE,authorizedExactEdits=sorted(allowed),allOtherHistoricalFilesUnchanged=True,publicJsCssHashes=public,fiveExpectedFailuresUnchanged=True,sourceAndBackupFiles=len(prov['sourceHashes']),sourceAndBackupUnchanged=True,accepted588BundleUnchanged=True,referenceCleanAtExactHead=True,durablePrimaryAndCopyIdentical=True,noPrivateArtifactTracked=True,historicalGatesUnchanged=True)
(HERE/'checks/isolation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
