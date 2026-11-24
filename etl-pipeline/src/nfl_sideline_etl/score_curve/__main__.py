import argparse,json
from pathlib import Path
from .package import generate,read
from ..situational import encoded
p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
a=s.add_parser('generate');a.add_argument('--source',required=True);a.add_argument('--output',required=True)
a=s.add_parser('serve-snapshot');a.add_argument('--config',required=True)
a=s.add_parser('verify');a.add_argument('--source',required=True);a.add_argument('--pin')
a=p.parse_args()
if a.command=='generate':r=generate(Path(a.source),Path(a.output))
elif a.command=='verify':_,r=read(Path(a.source),a.pin)
else:
 c=json.loads(Path(a.config).read_text());b,m=read(Path(c['bundle']),c['pin']);r=dict(bundleId=m['bundleId'],payload=b.decode())
print(encoded(r).decode(),end='')
