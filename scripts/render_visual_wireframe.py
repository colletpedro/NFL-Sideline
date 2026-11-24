#!/usr/bin/env python3
"""Materialize the E1 static wireframe in a NEW directory, using validated fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from verify_visual_contract import CONTRACT, ROOT, verify_fixtures

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
args = parser.parse_args()
verify_fixtures()
args.output.mkdir(parents=True, exist_ok=False)
manifest = json.loads((CONTRACT / 'fixtures/manifest.json').read_text())
fixtures = {Path(p).stem: json.loads((CONTRACT / 'fixtures' / p).read_text()) for p in manifest['valid']}
for file in (ROOT / 'docs/plans/visual-v1/wireframe').iterdir():
    shutil.copyfile(file, args.output / file.name)
(args.output / 'data.js').write_text('window.visualFixtures = ' + json.dumps(fixtures,ensure_ascii=False).replace('<','\\u003c') + ';\n')
(args.output / 'provenance.json').write_text(json.dumps({'contractFixtures':{p:hashlib.sha256((CONTRACT / 'fixtures' / p).read_bytes()).hexdigest() for p in manifest['valid']},'synthetic':True},indent=2)+'\n')
print(args.output.resolve())
