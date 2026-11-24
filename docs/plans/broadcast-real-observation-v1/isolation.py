"""Current delivery scope against its exact base, without relaxing historical gates."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[3]
BASE='b59a8deb60aec318a6ed984a55b87a993b44b14d'
protected=['web-ui/src','web-ui/public','web-ui/local-editorial','web-ui/build','web-ui/scripts','web-ui/index.html','web-ui/vite.config.ts','web-ui/vite.editorial.config.ts','web-ui/vercel.json','web-ui/package-lock.json','core-api','etl-pipeline','supabase','.github','contracts','Spec.md','docs/static-snapshot-contract.md']
allowed={'web-ui/build/observations.ts','web-ui/scripts/real-dev.mjs'}
changed=subprocess.check_output(['git','diff','--name-only',BASE,'--',*protected],cwd=ROOT,text=True).splitlines()
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--',*protected],cwd=ROOT,text=True).splitlines()
assert set(changed+untracked)<=allowed,(changed,untracked)
assert subprocess.check_output(['git','show',f'{BASE}:web-ui/src/components/visual-preparation-regressions.test.tsx'],cwd=ROOT)==(ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_bytes()
assert (ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(')==5
public={}
for file in (ROOT/'web-ui/dist/assets').iterdir():
 if file.suffix in ('.js','.css'):
  wire=file.read_text()
  for marker in ('__observations','broadcast-real','REAL_ARCHIVE','broadcast-experience','dallas-new-england','Archivo-Variable','RobotoCondensed-Variable'):
   assert marker not in wire,(file.name,marker)
  public[file.suffix]=hashlib.sha256(file.read_bytes()).hexdigest()
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
for file in (ROOT/'web-ui/real-dist/assets').glob('*.js'):
 for marker in ('dallas-new-england','O passe abre o caminho','readSlice','thirdDown','redzone'):
  assert marker not in file.read_text(),marker
result={'base':BASE,'protectedChanges':changed,'protectedUntracked':untracked,'authorizedExceptions':sorted(allowed),'publicHashesUnchanged':public,'fiveLegacyExpectedFailuresUnchanged':True,'realBundleHasNoSimulationLogic':True,'historicalGate':'Preserved; refuses authorized observations.ts port adaptation as expected. It was not modified.'}
(ROOT/'docs/plans/broadcast-real-observation-v1/isolation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
