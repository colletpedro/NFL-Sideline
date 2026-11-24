"""Read-only proof: local presentation changes, unchanged historical data/transports/public build."""
import hashlib,json,subprocess
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
BASE='5348ab117bffd01c75323a0c56466e450b522260'
REF=Path('/Users/pedrocollet/.codex/worktrees/broadcast-situational-copy-v2/NFL Sideline')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
allowed=lambda p:p in {'web-ui/broadcast-journey/App.tsx','web-ui/broadcast-journey/situational/SituationalReading.tsx'} or p.startswith(('web-ui/broadcast-journey/explorer/','docs/plans/broadcast-explorer-v1/'))
changed=sorted(set(git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines()))
assert all(allowed(p) for p in changed),changed
for p in git('ls-tree','-r','--name-only',BASE).decode().splitlines():
 if not allowed(p):assert (ROOT/p).read_bytes()==git('show',BASE+':'+p),p
reading='web-ui/broadcast-journey/situational/SituationalReading.tsx'
old=git('show',BASE+':'+reading).decode()
expected=old.replace("export function SituationalContent({d,snapshot,family}:{d:SituationalDocument;snapshot:Snapshot;family:'third'|'redzone'})","export function SituationalContent({d,snapshot,family,announce=true}:{d:SituationalDocument;snapshot:Snapshot;family:'third'|'redzone';announce?:boolean})").replace('aria-live="polite"','aria-live={announce?\'polite\':\'off\'}')
assert (ROOT/reading).read_text()==expected
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in ['.js','.css']}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'},public
copy=json.loads((ROOT/'docs/plans/broadcast-situational-w12-v1/checks/copy.json').read_bytes());primary=Path(copy['primary'])
assert hashes(primary)==hashes(Path(copy['copy']))=={k:v[7:] for k,v in copy['files'].items()}
prov=json.loads((primary/'provenance.json').read_bytes());assert hashes(Path(prov['source']))==prov['sourceHashes']==hashes(Path(prov['backup']))
assert hashes(Path(prov['oldBundlePath']))==prov['oldBundleHashes']
def get(port,path,marker):
 with urlopen(Request(f'http://127.0.0.1:{port}{path}',headers={marker:'1'})) as r:return json.load(r)
a=get(18099,'/__situational/','X-Local-Situational');b=get(18100,'/__situational/','X-Local-Situational')
assert a==b and a['data']==json.loads((primary/'situational.json').read_bytes()) and len(a['data']['documents'])==192
refusals=0
for method,path,headers in [('POST','/__situational/',{'X-Local-Situational':'1'}),('GET','/__situational/',{}),('GET','/__situational/?q=1',{'X-Local-Situational':'1'}),('GET','/__situational/missing',{'X-Local-Situational':'1'}),('GET','/__situational/',{'X-Local-Situational':'1','Origin':'https://example.com'}),('GET','/__situational/',{'X-Local-Situational':'1','Host':'localhost:18100'})]:
 try:urlopen(Request('http://127.0.0.1:18100'+path,headers=headers,method=method));raise AssertionError('Untrusted request accepted')
 except HTTPError as e:assert e.code==403;refusals+=1
assert a['bundleId']=='sha256:2af2a33211c09658fb6b831188dc5c5ac3bee9b3fc4b2b6008748921ac7c339c'
assert get(18099,'/__observations/','X-Local-Observations')==get(18100,'/__observations/','X-Local-Observations')
assert subprocess.check_output(['git','status','--porcelain'],cwd=REF)==b''
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REF).decode().strip()==BASE
reg=(ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text();assert reg.count('  it.fails(')==5
listeners={}
for port in [18099,18100]:
 listeners[port]=subprocess.check_output(['lsof','-nP',f'-iTCP:{port}','-sTCP:LISTEN']).decode();assert f'127.0.0.1:{port}' in listeners[port]
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
report=dict(base=BASE,changed=changed,allOtherHistoricalFilesByteIdentical=True,originalReadingOnlyOptionalAnnouncementProp=True,publicBuildHashes=public,fiveExpectedFailuresUnchanged=True,sourceAndBackupFiles=len(prov['sourceHashes']),sourceAndBackupAnd588BundleUnchanged=True,situationalPrimaryAndVerifiedCopyUnchanged=True,situationalHttpDocumentsIdentical=192,situationalHttpRefusals=refusals,countsRatiosStatesAndGuaranteesIdentical=True,legacyCatalogIdentical=True,referenceCleanAtExactHead=True,listeners=listeners)
(HERE/'checks/preservation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
