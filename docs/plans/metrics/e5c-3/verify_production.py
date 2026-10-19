"""After a normal build, prove VITE_* cannot activate the observation laboratory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[4]
dist=ROOT/'web-ui/dist'
def files():return {str(p.relative_to(dist)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dist.rglob('*') if p.is_file()}
before=files();assert 'index.html' in before
for p in (dist/'assets').iterdir():
    if p.suffix in ('.js','.css'):
        wire=p.read_text()
        assert all(x not in wire for x in ('__observations','metrics-lab-','NFL_OBSERVATION_','metrics_lab','observations-process'))
subprocess.run(['npm','--prefix','web-ui','run','build'],cwd=ROOT,check=True,
    env={**os.environ,'VITE_EDITORIAL_UI':'true','VITE_OBSERVATION_CONFIG':'/tmp/never-read','VITE_API_BASE_URL':'http://127.0.0.1:18083/__observations/'})
assert before==files(),'Public build changed under laboratory VITE flags'
print(json.dumps({'proof':'STATIC_PRODUCTION_IDENTICAL_WITH_VITE_FLAGS','assets':{k:v for k,v in before.items() if k.startswith('assets/')}},indent=2))
