"""One-time durable recovery copy; refuses overwrites, verifies every byte."""
from pathlib import Path
import argparse,shutil
from acquire import sha
from dataset import dump,verify_sources

def archive(store,backup,receipt):
 store=Path(store).resolve();backup=Path(backup).resolve();receipt=Path(receipt)
 if backup.exists() or receipt.exists():raise FileExistsError('Recovery destination/receipt already exists')
 if store in backup.parents or backup in store.parents:raise ValueError('Backup must be disjoint')
 verify_sources(store); records=[]
 for p in sorted(store.rglob('*')):
  if p.is_symlink():raise ValueError('No symlinks in scientific archive')
  if p.is_file():records.append(dict(path=str(p.relative_to(store)),bytes=p.stat().st_size,sha256=sha(p)))
 backup.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(store,backup)
 for r in records:
  if sha(backup/r['path'])!=r['sha256']:raise ValueError(f'Recovery copy differs: {r["path"]}')
 verify_sources(backup)
 dump(receipt,dict(version=1,passed=True,store=str(store),backup=str(backup),files=len(records),bytes=sum(r['bytes'] for r in records),records=records,restore='Copy preserved store tree into a new directory and run offline reproduction with that path; no original approved source path or network required after acquisition. Wheels are specific to current CPython/macOS arm64.'))
 print(f'Recovery copy PASS: {len(records)} files, {sum(r["bytes"] for r in records)} bytes')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--backup',required=True);p.add_argument('--receipt',required=True);a=p.parse_args();archive(a.store,a.backup,a.receipt)
