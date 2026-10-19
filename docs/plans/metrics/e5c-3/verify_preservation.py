"""Scoped base preservation; optional check of the original checkout inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[4]
BASE='152313edf7d74c2175f5b3727c521e69bb71b30d'
PREFIXES=('docs/plans/metrics/e5c-3/','etl-pipeline/src/nfl_sideline_etl/metrics_lab/','web-ui/local-editorial/observations/')
FILES={'web-ui/build/observations.ts','web-ui/build/observations-process.mjs','web-ui/build/observations-process.d.mts','web-ui/vite.editorial.config.ts','web-ui/local-editorial/App.tsx','docs/local-editorial-ui.md','etl-pipeline/tests/test_metrics_lab.py'}
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd).decode()
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--original',type=Path);p.add_argument('--inventory',type=Path);a=p.parse_args()
assert git('merge-base',BASE,'HEAD').strip()==BASE
changed=set(git('diff','--name-only',BASE).splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
assert all(n in FILES or n.startswith(PREFIXES) for n in changed),changed
assert git('diff',BASE,'--','web-ui/src','web-ui/public','web-ui/vite.config.ts','core-api','contracts','supabase','.github','etl-pipeline/src/nfl_sideline_etl/metrics_observations')==''
if a.original or a.inventory:
    assert a.original and a.inventory
    old=json.loads(a.inventory.read_bytes())
    assert git('rev-parse','HEAD',cwd=a.original).strip()==old['head']
    assert git('status','--porcelain','-z',cwd=a.original)==old['status']
    for name,digest in old['untracked'].items():
        assert not Path(name).name.startswith('.env')
        assert hashlib.sha256((a.original/name).read_bytes()).hexdigest()==digest,name
    print(f"Original checkout preserved: HEAD, status, {len(old['untracked'])} untracked file hashes")
print('PASS: scope and frozen components preserved against '+BASE)
