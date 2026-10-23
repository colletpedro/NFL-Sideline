"""Create physical no-clobber recovery copy; reader in a fresh source-denied process."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
source=Path(sys.argv[1]);target=Path(sys.argv[2]);assert not target.exists()
shutil.copytree(source,target,symlinks=False)
code='''import sys,json
from pathlib import Path
from nfl_sideline_etl.situational import read,digest
copy=Path(sys.argv[1]);principal=Path(sys.argv[2])
def deny(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=str(args[0]);assert not any(x in p for x in (str(principal),'/real-recovery/','/backups/','/broadcast-w12-expansion-v1/')),p
sys.addaudithook(deny)
data,marker=read(copy)
print(json.dumps(dict(bundleId=marker['bundleId'],documents=len(data['documents']),files={str(p.relative_to(copy)):digest(p.read_bytes()) for p in copy.rglob('*') if p.is_file()},freshProcessSourceAccessDenied=True)))
'''
env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin','PYTHONPATH':str(ROOT/'etl-pipeline/src'),'PYTHONDONTWRITEBYTECODE':'1'}
report=json.loads(subprocess.check_output([sys.executable,'-B','-c',code,str(target),str(source)],cwd='/private/tmp',env=env))
import hashlib
assert report['files']=={str(p.relative_to(source)):'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
report.update(primary=str(source),copy=str(target),physicalNoSymlinks=not any(p.is_symlink() for p in target.rglob('*')))
(Path(sys.argv[3]) if len(sys.argv)>3 else Path(__file__).parent/'checks/copy.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
