"""New physical recovery copy, fresh reader denying every original root."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
source,target,output=map(Path,sys.argv[1:])
assert not target.exists()
shutil.copytree(source,target,symlinks=False)
code='''import sys,json
from pathlib import Path
from nfl_sideline_etl.comparison_foundation.package import read,hashes
copy,principal=map(Path,sys.argv[1:])
def deny(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(args[0]).absolute()
  blocked=[principal,Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery'),Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups')]
  if any(p==b or b in p.parents for b in blocked) or '/broadcast-w12-expansion-v1/' in str(p) or '/broadcast-situational-w12-v1/' in str(p):
   raise RuntimeError('Original source access denied: '+str(p))
sys.addaudithook(deny)
d,m=read(copy)
print(json.dumps(dict(bundleId=m['bundleId'],files=hashes(copy),productions=len(d['productions']),freshProcessOriginalRootsDenied=True)))
'''
env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin',PYTHONPATH=str(ROOT/'etl-pipeline/src'),PYTHONDONTWRITEBYTECODE='1')
proof=json.loads(subprocess.check_output([sys.executable,'-B','-c',code,str(target),str(source)],cwd='/private/tmp',env=env))
sys.path.insert(0,str(ROOT/'etl-pipeline/src'))
from nfl_sideline_etl.comparison_foundation.package import hashes
assert proof['files']==hashes(source) and not any(p.is_symlink() for p in target.rglob('*'))
proof.update(primary=str(source),recoveryCopy=str(target),physicalCopy=True,sameDisk=True)
output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k!='files'}))
