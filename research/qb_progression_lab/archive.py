"""Recover this local reading over the exact Git base; no original store mutation."""
import argparse,tarfile
from pathlib import Path
from package import STORE,SCI,read,write,sha,check_package

def archive(store=STORE,out=None):
 store=Path(store);out=Path(out or store/'recovery')
 if out.exists():raise FileExistsError('Preserve earlier recovery')
 out.mkdir(parents=True);repo=Path(__file__).resolve().parents[2];pointer=read(store/'current.json');package=store/'packages'/pointer['packageId'];check_package(package);entries=[(store/'current.json','store/current.json')]
 for p in sorted(package.rglob('*')):
  if p.is_file():entries.append((p,'store/packages/'+pointer['packageId']+'/'+str(p.relative_to(package))))
 for rel in ['research/qb_progression_lab','web-ui/broadcast-journey/progression','docs/plans/qb-progression-improvisation-lab-v1']:
  for p in sorted((repo/rel).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts and p.name not in ['recovery.json','recovery.log','recovery-final.log']:entries.append((p,'code/'+str(p.relative_to(repo))))
 for rel in ['web-ui/broadcast-journey/risk-outcomes/Entry.tsx','web-ui/broadcast-journey/risk-outcomes/Navigation.tsx','web-ui/build/progression.ts','web-ui/vite.progression.config.ts','web-ui/scripts/progression-dev.mjs']:
  entries.append((repo/rel,'code/'+rel))
 manifest=dict(schemaVersion=1,baseGitHead='1f72767b514cc1617046378fe00824ad957ad8f8',packageId=pointer['packageId'],scope='Third-reading package, code patch, docs and source manifests. Pinned raw sources, M3/B2 and base checkout remain in their original preserved stores; not bundled.',files=[dict(path=rel,bytes=p.stat().st_size,sha256=sha(p)) for p,rel in entries]);write(out/'manifest.json',manifest)
 tar=out/'progression-lab-v1.tar.gz'
 with tarfile.open(tar,'w:gz') as t:
  for p,rel in entries:t.add(p,arcname=rel,recursive=False)
  t.add(out/'manifest.json',arcname='recovery-manifest.json')
 target=out/'restored';target.mkdir()
 with tarfile.open(tar) as t:t.extractall(target,filter='data')
 for f in manifest['files']:assert sha(target/f['path'])==f['sha256']
 check_package(target/'store/packages'/pointer['packageId'])
 receipt=dict(passed=True,archive=str(tar),sha256=sha(tar),bytes=tar.stat().st_size,filesVerified=len(entries)+1,manifestSha256=sha(out/'manifest.json'),restored=str(target),schemaVersion=2,packageId=pointer['packageId'],storage='durable local copy, no remote backup claim',scope=manifest['scope'])
 write(out/'receipt.json',receipt);return receipt
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--store',default=str(STORE));a.add_argument('--out');v=a.parse_args();r=archive(v.store,v.out);print(r)
