"""Read-only isolation gate; no network, DB, writes or dependency installation."""
from pathlib import Path
import hashlib,json,struct,subprocess
ROOT = Path(__file__).resolve().parents[3]
BASE = '13597af9dafb910e345ef0bcc519f3d1352ca941'
DOC = 'docs/plans/broadcast-media-pilot-v4/'
MEDIA = 'web-ui/broadcast-journey/media/'
ALLOWED = {'App.tsx','Discovery.tsx','ObservationChoice.tsx','choice.ts','choice.test.ts','discoveryModel.ts','discovery.test.tsx','journey.css'}
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data): return hashlib.sha256(data).hexdigest()
def original(path): return git('show',f'{BASE}:{path}')
changed=set(git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines())
assert all(p.startswith(DOC) or p.startswith(MEDIA) or p.startswith('web-ui/broadcast-journey/') and p.split('/')[-1] in ALLOWED for p in changed),changed
assert git('merge-base',BASE,'HEAD').decode().strip()==BASE
snapshots={}
for p in (ROOT/'web-ui/public/data').rglob('*.json'):
 name=p.relative_to(ROOT).as_posix();assert p.read_bytes()==original(name),name;snapshots[name]=sha(p.read_bytes())
legacy='web-ui/src/components/visual-preparation-regressions.test.tsx'
assert (ROOT/legacy).read_bytes()==original(legacy)
assert (ROOT/legacy).read_text().count('  it.fails(')==5
for name in ['web-ui/broadcast-journey/relations.ts','web-ui/broadcast-journey/sources.ts','web-ui/broadcast-journey/state.ts','web-ui/broadcast-real/identity.ts','web-ui/broadcast-real/Reading.tsx','web-ui/broadcast-experience/TeamLogo.tsx']:
 assert (ROOT/name).read_bytes()==original(name),name
catalog=json.loads((ROOT/MEDIA/'catalog.json').read_text())
assert catalog==json.loads((ROOT/DOC/'assets.json').read_text())
assert catalog['approvedForPublication']==[] and len(catalog['candidates'])==8
assert {(a['team'],a['type']) for a in catalog['candidates']}=={(t,k) for t in ['DAL','NE','BAL','IND'] for k in ['helmet','portrait']}
for a in catalog['candidates']:
 data=(ROOT/a['path']).read_bytes();assert sha(data)==a['sha256'],a['assetId']
 assert data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(a['width'],a['height'])
 assert data[25]==6 or b'tRNS' in data
 assert a['fileValidated'] and a['transparency'] and a['reusePermission']=='UNVERIFIED'
 assert a['status']=='LOCAL_RESEARCH_CANDIDATE' and a['rightsEvidenceUrl'] and a['obtainedAt']
old_logos=json.loads((ROOT/'docs/plans/broadcast-discovery-assets-v3/assets.json').read_text())
assert len(catalog['legacyLogos'])==len(old_logos)==32
for a in old_logos:
 data=(ROOT/a['path']).read_bytes();assert sha(data)==a['sha256'] and data==original(a['path'])
public={p.suffix:sha(p.read_bytes()) for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in {'.js','.css'}}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'},public
http=json.loads((ROOT/DOC/'evidence/http.json').read_text())
assert http['documents']==http['http']['documentsExactlyMatched']==48
assert len(http['http']['refusals'])==16 and http['primaryAndBackupUnchanged']
browser=json.loads((ROOT/DOC/'evidence/browser.json').read_text())
assert len(browser['layouts'])==48 and all(x['scrollWidth']<=x['width'] and x['bodyWidth']<=x['width'] for x in browser['layouts'])
assert len(browser['media'])==8 and len(browser['logos'])==32
assert all(x['complete'] and x['width']>0 for x in browser['media']+browser['logos'])
assert all(u.startswith('http://127.0.0.1:18095/') for u in browser['network'])
assert browser['flows']['portraitErrorRecovery']['unchangedAfterFailure']
assert browser['flows']['incompatibleNominalBlocked'] and browser['flows']['explicitNoAfterReload']
assert browser['keyboard']['enterSearch'] and browser['keyboard']['routeHeadingFocused']
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
print(json.dumps({'base':BASE,'changedOutsideAllowlist':False,'publicAssetsUnchanged':public,'snapshotsUnchanged':snapshots,'legacyExpectedFailuresUnchanged':5,'relationMatrixUnchanged':True,'sourceTransportAndReadingUnchanged':True,'originalLogosUnchanged':32,'newFilesTechnicallyValidated':8,'newFilesQualifiedForPublication':0,'layoutsWithoutHorizontalOverflow':48,'httpDocumentsExactlyMatched':48,'httpRefusals':16,'primaryAndBackupUnchanged':True,'noExternalImageRequests':True},indent=2))
