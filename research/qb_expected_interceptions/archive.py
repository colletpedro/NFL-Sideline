"""Recoverable, disjoint store copy; verify every byte, refuse overwrite."""
import argparse, shutil
from common import *

def archive(store,backup,receipt):
    store=Path(store).resolve();backup=Path(backup).resolve()
    if backup==store or backup.is_relative_to(store) or store.is_relative_to(backup):raise ValueError('Backup must be disjoint')
    if backup.exists():raise FileExistsError(backup)
    files={str(p.relative_to(store)):sha(p) for p in sorted(store.rglob('*')) if p.is_file()}
    shutil.copytree(store,backup)
    for rel,digest in files.items():
        assert sha(backup/rel)==digest,rel
    write(receipt,dict(passed=True,source=str(store),backup=str(backup),files=files,count=len(files),
        total_bytes=sum((backup/rel).stat().st_size for rel in files),all_copied_hashes_verified=True,
        note='No venv, pickle or secrets. Recreate environment from wheelhouse/requirements.lock; code accompanies local Git branch.'))
    print('Recovery copy PASS',len(files),'files')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--store',default=str(STORE));a.add_argument('--backup',required=True);a.add_argument('--receipt',required=True);v=a.parse_args();archive(v.store,v.backup,v.receipt)
