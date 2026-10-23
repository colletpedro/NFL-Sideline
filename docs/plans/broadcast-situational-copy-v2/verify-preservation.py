"""Read-only proof for this bounded copy change; historical gates untouched."""
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
BASE='d410cc5ad9749255b241797a0f8c91a273b6a560'
REF=Path('/Users/pedrocollet/.codex/worktrees/broadcast-situational-w12-v1/NFL Sideline')
PRESENTATION='web-ui/broadcast-journey/situational/'
ALLOWED={PRESENTATION+p for p in ['SituationalReading.tsx','situational.css','compositionCopy.ts','compositionCopy.test.tsx']}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
changed=git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines()
assert all(p in ALLOWED or p.startswith('docs/plans/broadcast-situational-copy-v2/') for p in changed),changed
for path in git('ls-tree','-r','--name-only',BASE).decode().splitlines():
 if path not in ALLOWED:assert (ROOT/path).read_bytes()==git('show',BASE+':'+path),path
old=git('show',BASE+':'+PRESENTATION+'SituationalReading.tsx').decode();new=(ROOT/PRESENTATION/'SituationalReading.tsx').read_text()
for start,end in [('function DistanceChart','function DriveChart'),('function DriveChart','function Method'),('export function SituationalReading',None)]:
 def portion(text):return text[text.index(start):text.index(end)] if end else text[text.index(start):]
 assert portion(old)==portion(new),start
oldcss=git('show',BASE+':'+PRESENTATION+'situational.css').decode();css=(ROOT/PRESENTATION/'situational.css').read_text()
assert css.startswith(oldcss)
assert css[len(oldcss):]=='\n/* Editorial note only; preserve the existing caption font size and palette. */\n.situational-reading>.sit-rule-note{max-width:72ch;margin:8px 0 20px}\n'
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in ['.js','.css']}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'},public
copy=json.loads((ROOT/'docs/plans/broadcast-situational-w12-v1/checks/copy.json').read_bytes())
primary=Path(copy['primary']);assert hashes(primary)==hashes(Path(copy['copy']))=={k:v[7:] for k,v in copy['files'].items()}
prov=json.loads((primary/'provenance.json').read_bytes());assert hashes(Path(prov['source']))==prov['sourceHashes']==hashes(Path(prov['backup']))
assert hashes(Path(prov['oldBundlePath']))==prov['oldBundleHashes']
def get(port,path,marker):
 with urlopen(Request(f'http://127.0.0.1:{port}{path}',headers={marker:'1'})) as response:return json.load(response)
a=get(18098,'/__situational/','X-Local-Situational');b=get(18099,'/__situational/','X-Local-Situational')
assert a==b and a['data']==json.loads((primary/'situational.json').read_bytes()) and len(a['data']['documents'])==192
assert get(18098,'/__observations/','X-Local-Observations')==get(18099,'/__observations/','X-Local-Observations')
assert subprocess.check_output(['git','status','--porcelain'],cwd=REF)==b''
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REF).decode().strip()==BASE
reg=(ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text();assert reg.count('  it.fails(')==5
listener=subprocess.check_output(['lsof','-nP','-a','-p','49375','-iTCP:18098','-sTCP:LISTEN']).decode();assert '127.0.0.1:18098' in listener
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
report=dict(base=BASE,allowedPresentationPaths=sorted(ALLOWED),allOtherHistoricalFilesUnchanged=True,chartsAndSelectionSourceByteIdentical=True,cssOnlyAddsNoteSpacing=True,publicBuildHashes=public,fiveExpectedFailuresUnchanged=True,sourceAndBackupFiles=len(prov['sourceHashes']),sourceAndBackupAnd588BundleUnchanged=True,situationalPrimaryAndVerifiedCopyUnchanged=True,situationalHttpDocumentsIdentical=192,countsRatiosStatesAndGuaranteesIdentical=True,legacyCatalogIdentical=True,referenceCleanAtExactHead=True,referenceServer49375StillListening=True)
(HERE/'checks/preservation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
