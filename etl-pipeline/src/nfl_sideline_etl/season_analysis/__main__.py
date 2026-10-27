import argparse
import json
from pathlib import Path
from .package import generate, read, reproduce
from ..situational import encoded

p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
for name in ('generate','reproduce'):
 s=sub.add_parser(name);s.add_argument('--source',required=True);s.add_argument('--output',required=True)
s=sub.add_parser('verify');s.add_argument('--source',required=True);s.add_argument('--pin')
s=sub.add_parser('serve-snapshot');s.add_argument('--config',required=True)
a=p.parse_args()
if a.command=='generate':result=generate(Path(a.source),Path(a.output))
elif a.command=='reproduce':result=reproduce(Path(a.source),Path(a.output))
elif a.command=='verify':_,result=read(Path(a.source),a.pin)
else:
 config=json.loads(Path(a.config).read_text());root=Path(config['bundle']);index,marker=read(root,config['pin'])
 result=dict(bundleId=marker['bundleId'],files={name:(root/name).read_text() for name in ['index.json',*[g['path'] for g in index['games']],*[t['path'] for t in index['teams']]]})
print(encoded(result).decode(),end='')
