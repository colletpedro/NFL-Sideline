import argparse
import json
from pathlib import Path

from .package import preflight, generate, read, reproduce
from .server import serve
from ..situational import encoded


def main():
    p = argparse.ArgumentParser(description='Private NYJ–TEN W1 comparison foundation; no acquisition/DB/UI')
    sub = p.add_subparsers(dest='command', required=True)
    g = sub.add_parser('generate')
    for arg in ('situational', 'observations', 'recovery', 'backup', 'request', 'policy', 'definitions', 'output'):
        g.add_argument('--'+arg, type=Path, required=True)
    v = sub.add_parser('validate'); v.add_argument('--bundle', type=Path, required=True)
    v.add_argument('--expected-pin')
    r = sub.add_parser('reproduce'); r.add_argument('--bundle', type=Path, required=True); r.add_argument('--output', type=Path, required=True)
    s = sub.add_parser('serve'); s.add_argument('--config', type=Path, required=True)
    a = p.parse_args()
    if a.command == 'generate':
        receipt = preflight(a.situational, a.observations, a.recovery, a.backup)
        marker = generate(a.output, a.situational, a.observations, json.loads(a.request.read_bytes()), a.policy.read_text(), receipt, a.definitions.read_text())
    elif a.command == 'validate':
        _, marker = read(a.bundle, a.expected_pin)
    elif a.command == 'reproduce':
        marker = reproduce(a.bundle, a.output)
    else:
        serve(a.config); return
    print(encoded(dict(bundleId=marker['bundleId'], version=marker['version'], files=len(marker['files']))).decode(), end='')


if __name__ == '__main__':
    main()
