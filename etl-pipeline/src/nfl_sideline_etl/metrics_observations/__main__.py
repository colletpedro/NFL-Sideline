"""Explicit offline CLI; never opens DB/network/.env or a temporal result."""
import argparse
from pathlib import Path

from ..offline_metrics.artifact import json_bytes
from ..offline_metrics.inputs import load_json
from .publication import generate, inspect, safe_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    cmd = commands.add_parser('generate')
    cmd.add_argument('--materialized', type=Path, required=True)
    cmd.add_argument('--request', type=Path, required=True)
    cmd.add_argument('--output', type=Path, required=True)
    for name in ('validate', 'inspect'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'generate':
            result = generate(args.materialized, load_json(safe_path(args.request).read_bytes()), args.output)
            print(result['bundleId'])
        else:
            print(json_bytes(inspect(args.bundle)).decode(), end='')
    except (ValueError, KeyError, TypeError, StopIteration, OSError, ArithmeticError) as error:
        parser.exit(2, 'E5c-2 validation failed: ' + str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
