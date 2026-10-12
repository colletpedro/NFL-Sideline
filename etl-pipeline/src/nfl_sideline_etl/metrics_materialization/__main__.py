"""Explicit isolated bridge commands. PostgreSQL is loaded only in postgres mode."""
import argparse
from pathlib import Path

from ..offline_metrics.inputs import load_json
from ..offline_metrics.artifact import ensure_destination
from .core import materialize
from .publication import publish, read
from .recovery import recover


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    for mode in ('offline', 'postgres'):
        cmd = commands.add_parser(mode)
        if mode == 'offline':
            cmd.add_argument('--relations', type=Path, required=True)
        else:
            cmd.add_argument('--config', type=Path, required=True)
            cmd.add_argument('--selection', type=Path, required=True)
        cmd.add_argument('--archives', type=Path, required=True, help='Explicit archive_id -> original root map')
        cmd.add_argument('--auxiliary', type=Path, required=True)
        cmd.add_argument('--derived-at', required=True)
        cmd.add_argument('--output', type=Path, required=True)
    cmd = commands.add_parser('select')
    cmd.add_argument('--materialized', type=Path, required=True)
    cmd.add_argument('--request', type=Path, required=True)
    cmd.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    def document(path):
        return load_json(path.read_bytes())
    try:
        ensure_destination(args.output)
        if args.mode == 'select':
            from ..temporal_metrics.core import select
            from ..temporal_metrics.__main__ import publish as publish_result
            temporal, _ = read(args.materialized)
            result = select(temporal, document(args.request))
            publish_result(args.output, result)
            print(result['result_id'])
        else:
            if args.mode == 'postgres':
                from ..metrics_persistence.connection import configuration
                from .postgres import extract
                package = extract(configuration(args.config), document(args.selection))
            else:
                package = document(args.relations)
            recovered = recover(package, document(args.archives))
            temporal, lineage = materialize(package, recovered, document(args.auxiliary), args.derived_at)
            publish(args.output, temporal, lineage)
            print(lineage['materialization_id'])
    except (ValueError, KeyError, TypeError, OSError, ArithmeticError) as error:
        parser.exit(2, 'E5b-4 validation failed: ' + str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
