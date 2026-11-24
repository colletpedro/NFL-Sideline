"""Durable v2 recovery copy, disjoint fresh destination, all bytes checked."""
from pathlib import Path
import argparse,shutil,json
from common import sha,dump,verify_sources

def archive(store,backup,receipt):
 s=Path(store).resolve();b=Path(backup).resolve();r=Path(receipt)
 if b.exists() or r.exists():raise FileExistsError('Recovery destination/receipt already exists')
 if s in b.parents or b in s.parents:raise ValueError('Recovery must be disjoint')
 verify_sources(s/'inputs/v1')
 for x in json.loads((s/'additional-sources.json').read_text())['files']:
  if sha(s/x['path'])!=x['sha256']:raise ValueError('Supplementary source changed')
 records=[]
 for p in sorted(s.rglob('*')):
  if p.is_symlink():raise ValueError('No symlinks in frozen research store')
  if p.is_file():records.append(dict(path=str(p.relative_to(s)),bytes=p.stat().st_size,sha256=sha(p)))
 b.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(s,b)
 for x in records:
  if sha(b/x['path'])!=x['sha256']:raise ValueError('Recovery bytes differ')
 dump(r,dict(passed=True,store=str(s),backup=str(b),files=len(records),bytes=sum(x['bytes'] for x in records),records=records,restore='Restore copied tree to a new path; offline reproduce with pinned code and wheelhouse. No database, network, original v1 path or paid service is required.'))
 print('RECOVERY PASS',len(records),'files',sum(x['bytes'] for x in records),'bytes')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--backup',required=True);p.add_argument('--receipt',required=True);a=p.parse_args();archive(a.store,a.backup,a.receipt)
