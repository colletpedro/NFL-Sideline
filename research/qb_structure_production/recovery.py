"""Durable local recovery archive and verified extraction. No external publication."""
import argparse,tarfile,shutil
from common import *

def recover(s,out):
 s=Path(s);verify(s);out=new(out);repo=Path(__file__).parents[2]
 archive=out/'frozen-sources-and-code.tar.gz'
 with tarfile.open(archive,'w:gz') as t:
  t.add(s,arcname='sources')
  for p in sorted((repo/'research/qb_structure_production').iterdir()):
   if p.suffix in ['.py','.txt']:t.add(p,arcname=str(p.relative_to(repo)))
  p=repo/'docs/plans/qb-structure-production-v1/RESEARCH-CONTRACT.md';t.add(p,arcname=str(p.relative_to(repo)))
 target=out/'restored';target.mkdir()
 with tarfile.open(archive) as t:t.extractall(target,filter='data')
 verify(target/'sources');checks=[]
 for p in sorted(s.rglob('*')):
  if p.is_file():assert sha(p)==sha(target/'sources'/p.relative_to(s));checks.append(str(p.relative_to(s)))
 write(out/'receipt.json',dict(archive=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),restored_sources=str(target/'sources'),source_files_byte_identical=len(checks),code_verified=all(sha(p)==sha(target/p.relative_to(repo)) for p in (repo/'research/qb_structure_production').glob('*.py')),status='local_durable_copy_verified_no_remote_backup_claim'))
 return target

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--sources',required=True);a.add_argument('--out',required=True);v=a.parse_args();print(recover(v.sources,v.out))
