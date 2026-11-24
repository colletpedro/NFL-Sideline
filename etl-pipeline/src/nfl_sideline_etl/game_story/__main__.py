import argparse,json
from pathlib import Path
from .package import generate,read,hashes
from ..situational import encoded
p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
for name in ('generate','reproduce'):
 a=s.add_parser(name);a.add_argument('--source',required=True);a.add_argument('--output',required=True)
a=s.add_parser('verify');a.add_argument('--source',required=True);a.add_argument('--pin')
a=s.add_parser('serve-snapshot');a.add_argument('--config',required=True)
a=p.parse_args()
if a.cmd=='generate':result=generate(Path(a.source),Path(a.output))
elif a.cmd=='reproduce':
 _,old=read(Path(a.source));result=generate(Path(a.source)/'source',Path(a.output))
 if old!=result or hashes(Path(a.source))!=hashes(Path(a.output)):raise ValueError('Reproduction differs')
elif a.cmd=='verify':_,result=read(Path(a.source),a.pin)
else:
 c=json.loads(Path(a.config).read_text());b,m=read(Path(c['bundle']),c['pin']);result=dict(bundleId=m['bundleId'],payload=b.decode())
print(encoded(result).decode(),end='')
