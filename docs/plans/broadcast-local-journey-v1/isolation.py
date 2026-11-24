"""Local journey gate; does not change any historical verifier or baseline."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[3]
BASE='c193bb8116e347a76ac31f8fbe78cdbf57cda8a6'
def digest(b): return hashlib.sha256(b).hexdigest()
protected=['web-ui/src','web-ui/public','web-ui/local-editorial','web-ui/build','web-ui/scripts','web-ui/vite.config.ts','web-ui/vite.real.config.ts','web-ui/vite.experience.config.ts','web-ui/vite.editorial.config.ts','web-ui/package-lock.json','web-ui/vercel.json','etl-pipeline','core-api','supabase','contracts','.github','Spec.md','docs/static-snapshot-contract.md','docs/visual-reference','docs/plans/broadcast-real-observation-v1']
allowed={'web-ui/local-editorial/observations/ObservationReading.tsx','web-ui/scripts/journey-dev.mjs'}
changed=subprocess.check_output(['git','diff','--name-only',BASE,'--',*protected],cwd=ROOT,text=True).splitlines()
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--',*protected],cwd=ROOT,text=True).splitlines()
assert set(changed+untracked)<=allowed,(changed,untracked)
snapshots={}
for p in (ROOT/'web-ui/public/data').rglob('*.json'):
 rel=str(p.relative_to(ROOT));old=subprocess.check_output(['git','show',f'{BASE}:{rel}'],cwd=ROOT)
 assert old==p.read_bytes();snapshots[rel]=digest(old)
assert snapshots=={'web-ui/public/data/manifest.json':'deca3888625d74dd2ac81e4b500a0c1f767251387dd38a60f016be04f81dc71d','web-ui/public/data/seasons/2026.json':'9c378a2951c3333015d02b083e9a450424becc0bf1083fdffd34694cf08d867d'}
reg='web-ui/src/components/visual-preparation-regressions.test.tsx';before=subprocess.check_output(['git','show',f'{BASE}:{reg}'],cwd=ROOT);assert (ROOT/reg).read_bytes()==before and before.count(b'  it.fails(')==5
public={}
for p in (ROOT/'web-ui/dist/assets').iterdir():
 if p.suffix not in ('.js','.css'): continue
 wire=p.read_text()
 for marker in ['__observations','broadcast-journey','REAL_ARCHIVE','dallas-new-england','Archivo-Variable','RobotoCondensed-Variable'] : assert marker not in wire
 public[p.suffix]=digest(p.read_bytes())
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
for p in (ROOT/'web-ui/journey-dist/assets').glob('*.js'):
 for marker in ['dallas-new-england','O passe abre o caminho','readSlice','thirdDown','redzone','VITE_API_BASE_URL','/api/v1'] : assert marker not in p.read_text(),marker
http=json.loads((Path(__file__).with_name('http.json')).read_text());source=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery/20261019T024130Z-50e03b27/bundle')
actual={str(p.relative_to(source)):digest(p.read_bytes()) for p in sorted(source.rglob('*')) if p.is_file()};assert actual==http['sourceHashes']
result={'base':BASE,'protectedChanges':changed,'protectedUntracked':untracked,'authorizedExceptions':sorted(allowed),'snapshotsUnchanged':snapshots,'publicHashesUnchanged':public,'fiveLegacyExpectedFailuresUnchanged':True,'bundleHashesUnchanged':True,'noSyntheticOrLegacyFallbackInJourney':True,'transportBoundaryUnchanged':True}
Path(__file__).with_name('isolation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
