"""Exclusive local persistence CLI, no work on import; dry-run is the default."""
import argparse
import json

from .connection import configuration
from .plan import prepare


def main(argv=None):
    parser = argparse.ArgumentParser(description='E5b-2 local immutable metrics persistence')
    parser.add_argument('--artifact', required=True)
    parser.add_argument('--calendar', action='append', required=True)
    parser.add_argument('--pbp', action='append', required=True)
    parser.add_argument('--archive', required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--dry-run', action='store_true')
    modes.add_argument('--persist', action='store_true')
    parser.add_argument('--local-config', help='Explicit six-field local JSON; required for --persist')
    args = parser.parse_args(argv)
    if args.persist and not args.local_config:
        parser.error('--persist requires --local-config')
    try:
        plan = prepare(args.artifact, args.calendar, args.pbp, args.archive)
        report = plan.summary()
        if args.persist:
            from .writer import persist
            report.update(persist(plan, args.archive, configuration(args.local_config)))
            report['database_connected'] = True
        report['mode'] = 'PERSISTED' if args.persist else 'DRY_RUN'
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception as exc:
        # Source/metadata paths and driver details may contain user secrets.
        # Never serialize exception text, connection file or DSN.
        category = 'validation_or_archive'
        if exc.__class__.__module__.startswith('psycopg2'):
            category = 'missing_reference' if getattr(exc, 'pgcode', None) == '23503' else 'database'
        print(json.dumps({'error': category, 'exception': type(exc).__name__,
                          'conflicts': int(isinstance(exc, ValueError) and 'conflict' in str(exc).lower()),
                          'transaction_committed': False,
                          'hint': ('Referenced game/team or source/coverage must already exist; writer never seeds domain.'
                                   if category == 'missing_reference' else
                                   'Verify artifact, explicit sources, archive integrity and local instance/role.')}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
