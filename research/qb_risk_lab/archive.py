"""Local durable recovery bundle, explicit paths; refuses to overwrite."""
import argparse,json,shutil,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import pipeline as p

def archive(store,sources,destination,archive_path,wheels):
 store=Path(store);src=Path(sources);dest=Path(destination);tar=Path(archive_path)
 if dest.exists() or tar.exists():raise FileExistsError('Recovery destination exists; use a new version')
 active,index,_=p.read_active(store);manifest=json.loads((store/'packages'/active['packageId']/'sources.json').read_text())
 assert manifest['acquiredAt']==index['acquiredAt']
 for row in manifest['files']:assert p.sha(src/row['path'])==row['sha256']
 dest.mkdir(parents=True);(dest/'sources').mkdir()
 p.write(dest/'sources/sources.json',manifest)
 for file in [r['path'] for r in manifest['files']]:shutil.copyfile(src/file,dest/'sources'/file)
 shutil.copytree(store/'packages'/active['packageId'],dest/'package')
 shutil.copyfile(p.MODEL,dest/'M3.json');shutil.copyfile(Path(__file__).parent/'requirements.lock',dest/'requirements.lock')
 shutil.copytree(wheels,dest/'wheelhouse')
 shutil.copytree(p.ROOT/'web-ui/risk-lab-dist',dest/'web-ui/risk-lab-dist')
 (dest/'web-ui/scripts').mkdir();shutil.copyfile(p.ROOT/'web-ui/scripts/risk-lab-built.mjs',dest/'web-ui/scripts/risk-lab-built.mjs')
 (dest/'history').mkdir()
 for run in (store/'runs').iterdir():
  for file in ['receipt.json','revision.json','failure.json','audit.json']:
   if (run/file).exists():
    (dest/'history'/run.name).mkdir(exist_ok=True);shutil.copyfile(run/file,dest/'history'/run.name/file)
 inventory={str(f.relative_to(dest)):p.sha(f) for f in dest.rglob('*') if f.is_file()};p.write(dest/'recovery-manifest.json',dict(modelSha256=p.MODEL_SHA,active=active,files=inventory))
 tar.parent.mkdir(parents=True,exist_ok=True)
 with tarfile.open(tar,'w:gz') as out:out.add(dest,arcname=dest.name)
 # Validate every tar member's bytes in memory; no extraction over existing files.
 with tarfile.open(tar,'r:gz') as check:
  for path,h in inventory.items():
   import hashlib
   assert hashlib.sha256(check.extractfile(dest.name+'/'+path).read()).hexdigest()==h
 receipt=dict(archive=str(tar),bytes=tar.stat().st_size,sha256=p.sha(tar),recovery=str(dest),fileCount=len(inventory),packageId=active['packageId'],allArchivedFilesVerified=True)
 p.write(p.ROOT/'docs/plans/qb-risk-lab-v1/evidence/recovery.json',receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser()
 for v in ['store','sources','destination','archive','wheels']:a.add_argument('--'+v,required=True)
 x=a.parse_args();archive(x.store,x.sources,x.destination,x.archive,x.wheels)
