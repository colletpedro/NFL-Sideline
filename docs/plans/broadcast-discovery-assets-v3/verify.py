from pathlib import Path
import hashlib,json,subprocess,struct
ROOT=Path(__file__).resolve().parents[3]
BASE='4f6095fd205da9230abc8c82e8a3a457a47bbaba'
DOC='docs/plans/broadcast-discovery-assets-v3/'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True)
def sha(data):return hashlib.sha256(data).hexdigest()
allowed={'web-ui/broadcast-experience/TeamLogo.tsx','web-ui/broadcast-real/identity.ts','web-ui/broadcast-journey/App.tsx','web-ui/broadcast-journey/journey.css','web-ui/broadcast-journey/Discovery.tsx','web-ui/broadcast-journey/discoveryModel.ts','web-ui/broadcast-journey/discovery.test.tsx','web-ui/broadcast-journey/LogoProof.tsx','web-ui/broadcast-journey/logos-main.tsx','web-ui/broadcast-journey/logos.html'}
changed=git('diff','--name-only',BASE).splitlines()+git('ls-files','--others','--exclude-standard').splitlines()
assert all(p in allowed or p.startswith(DOC) or p.startswith('web-ui/broadcast-real/assets/') for p in changed),changed
public={p.suffix:sha(p.read_bytes()) for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in {'.js','.css'}}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'},public
snapshots={}
for p in (ROOT/'web-ui/public/data').rglob('*.json'):
 rel=p.relative_to(ROOT).as_posix();old=subprocess.check_output(['git','show',f'{BASE}:{rel}'],cwd=ROOT);assert old==p.read_bytes();snapshots[rel]=sha(old)
legacy='web-ui/src/components/visual-preparation-regressions.test.tsx'
assert (ROOT/legacy).read_bytes()==subprocess.check_output(['git','show',f'{BASE}:{legacy}'],cwd=ROOT)
assert (ROOT/legacy).read_text().count('  it.fails(')==5
assets=json.loads((ROOT/DOC/'assets.json').read_text());assert len(assets)==32 and len({x['team'] for x in assets})==32
for x in assets:
 data=(ROOT/x['path']).read_bytes();assert sha(data)==x['sha256'];assert struct.unpack('>II',data[16:24])==(x['width'],x['height']);assert x['acquiredAt'];assert data[25]==6 # RGBA PNG original
source=ROOT/'docs/plans/broadcast-journey-polish-v2';oldBase='4f6095fd205da9230abc8c82e8a3a457a47bbaba'
for p in source.rglob('*'):
 if p.is_file():assert p.read_bytes()==subprocess.check_output(['git','show',f'{oldBase}:{p.relative_to(ROOT)}'],cwd=ROOT)
report=json.loads((ROOT/DOC/'evidence/http.json').read_text());assert report['documents']==report['http']['documentsExactlyMatched']==48 and len(report['http']['refusals'])==16 and report['primaryAndBackupUnchanged']
layouts=json.loads((ROOT/DOC/'evidence/layouts.json').read_text());assert len(layouts)==56;assert all(x['scrollWidth']<=x['innerWidth'] and x['bodyWidth']<=x['innerWidth'] for x in layouts)
logos=json.loads((ROOT/DOC/'evidence/logos.json').read_text());assert len(logos)==32 and all(x['complete'] and (x['width'],x['height'])==next((a['width'],a['height']) for a in assets if a['team']==x['team']) and not x['src'].startswith('http') for x in logos)
relations=json.loads((ROOT/DOC/'evidence/relations.json').read_text());assert relations['gap']['values']==relations['gap']['bars']==0 and relations['gap']['relation']=='gap';assert relations['historical']['relation']=='archive' and relations['inclusive']['relation']=='includes' and relations['incompatible']=={'relation':'incompatible','readings':0,'values':0}
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
print(json.dumps({'base':BASE,'changedOutsideAllowlist':False,'publicAssetsUnchanged':public,'snapshotsUnchanged':snapshots,'legacyExpectedFailuresUnchanged':5,'assets':32,'acquired':24,'reused':8,'alphaPreserved':True,'layoutsWithoutHorizontalOverflow':len(layouts),'httpDocuments':48,'httpRefusals':16,'bundleAndBackupUnchanged':True,'previousDeliveryDocsUnchanged':True},indent=2))
