import argparse
import json
from pathlib import Path
from .package import generate, read, reproduce
from ..situational import safe
p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
g=s.add_parser('generate');g.add_argument('--source',type=Path,required=True);g.add_argument('--policy',type=Path,required=True);g.add_argument('--output',type=Path,required=True)
v=s.add_parser('validate');v.add_argument('--bundle',type=Path,required=True);v.add_argument('--expected-pin')
r=s.add_parser('reproduce');r.add_argument('--bundle',type=Path,required=True);r.add_argument('--output',type=Path,required=True)
f=s.add_parser('serve-snapshot');f.add_argument('--config',type=Path,required=True)
a=p.parse_args()
if a.command=='generate':print(json.dumps(generate(a.source,a.output,a.policy.read_text())))
elif a.command=='reproduce':print(json.dumps(reproduce(a.bundle,a.output)))
elif a.command=='validate':
 i,d,m=read(a.bundle,a.expected_pin);print(json.dumps(dict(bundleId=m['bundleId'],teams=len(d))))
else:
 c=json.loads(safe(a.config).read_bytes())
 if set(c)!={'configVersion','path','expectedBundleId'} or c['configVersion']!='broadcast-team-w12-source-v1':raise ValueError('Explicit team config required')
 root=safe(Path(c['path']));i,docs,m=read(root,c['expectedBundleId'])
 print(json.dumps(dict(bundleId=m['bundleId'],index=(root/'index.json').read_text(),documents={t:b.decode() for t,b in docs.items()})))
