"""Compare all scientific outputs to the original frozen execution."""
import argparse,json
from pathlib import Path
from acquire import sha
from dataset import dump,verify_sources

def verify(store,reproduction,out):
 store=Path(store);rep=Path(reproduction);out=Path(out)
 if out.exists():raise FileExistsError(out)
 verify_sources(store);pairs=[]
 # All build outputs including independent audits and every pass key/split.
 for original in sorted((store/'build-v2').rglob('*')):
  if original.is_file():pairs.append((original,rep/'build'/original.relative_to(store/'build-v2')))
 for folder,newfolder in [('development-v3','development'),('evaluation-v1','evaluation'),('application-v1','application'),('figures-v4','figures')]:
  for original in sorted((store/folder).iterdir()):
   # Environment records explicitly capture different code versions/paths; model/freeze must be identical.
   if original.is_file() and original.name!='environment.json':pairs.append((original,rep/newfolder/original.name))
 records=[]
 for original,replayed in pairs:
  h=sha(original);r=sha(replayed) if replayed.exists() else None
  records.append(dict(original=str(original.relative_to(store)),reproduction=str(replayed.relative_to(rep)),sha256=h,reproduced_sha256=r,identical=h==r))
 result=dict(passed=all(v['identical'] for v in records),files=len(records),network='connections blocked in offline.py during reproduction',comparison='byte SHA-256, same pinned Python dependencies and platform',records=records)
 dump(out,result)
 if not result['passed']:raise ValueError('Reproduction mismatch; inspect durable comparison JSON')
 print(f'PASS: {len(records)} scientific artifacts identical byte-for-byte')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--reproduction',required=True);p.add_argument('--out',required=True);a=p.parse_args();verify(a.store,a.reproduction,a.out)
