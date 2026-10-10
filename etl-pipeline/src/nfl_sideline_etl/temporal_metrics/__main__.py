"""Explicit offline CLI. JSON only; never imports persistence/acquisition."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile

from ..offline_metrics.artifact import ensure_destination, json_bytes, rename_exclusive
from ..offline_metrics.inputs import load_json
from . import RESULT_VERSION
from .core import select


def publish(destination, result):
    destination = ensure_destination(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json_bytes(result)
    # Round-trip verification happens before creating a final directory.
    if load_json(payload) != result:
        raise ValueError('Output JSON validation failed')
    temporary = Path(tempfile.mkdtemp(prefix='.' + destination.name + '.pending-', dir=destination.parent))
    try:
        (temporary / 'result.json').write_bytes(payload)
        (temporary / 'COMPLETED.json').write_bytes(json_bytes({
            'resultVersion': RESULT_VERSION, 'result_id': result['result_id'], 'audit_id': result['audit_id'],
            'files': {'result.json': hashlib.sha256(payload).hexdigest()}}))
        rename_exclusive(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--season', required=True, type=int)
    parser.add_argument('--phase', required=True, choices=('REG', 'POST'))
    parser.add_argument('--team', required=True)
    parser.add_argument('--target-game-id', required=True)
    parser.add_argument('--target-week', required=True, type=int)
    parser.add_argument('--window', required=True, action='append', choices=('SEASON_TO_CUTOFF', 'LAST_3_CALENDAR_WEEKS', 'WEEK_OBSERVATION', 'HISTORICAL_REFERENCE'))
    parser.add_argument('--week', type=int)
    parser.add_argument('--historical-season', type=int)
    parser.add_argument('--historical-phase', choices=('REG', 'POST'))
    cut = parser.add_mutually_exclusive_group(required=True)
    cut.add_argument('--as-of-instant')
    cut.add_argument('--as-of-date')
    parser.add_argument('--mode', required=True, choices=('POINT_IN_TIME', 'EVENT_RECONSTRUCTION'))
    parser.add_argument('--retrospective', type=Path, help='Explicit revision choice map, required for reconstruction')
    parser.add_argument('--derived-at', required=True, help='Execution instant, separate from source knowledge')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    request = {'season': args.season, 'phase': args.phase, 'team': args.team, 'targetGameId': args.target_game_id,
               'targetWeek': args.target_week, 'mode': args.mode, 'windows': args.window, 'derivedAt': args.derived_at}
    for key, value in (('week', args.week), ('historicalSeason', args.historical_season), ('historicalPhase', args.historical_phase), ('asOfInstant', args.as_of_instant), ('asOfDate', args.as_of_date)):
        if value is not None:
            request[key] = value
    try:
        ensure_destination(args.output)
        document = load_json(args.input.read_bytes())
        if args.retrospective:
            request['retrospective'] = load_json(args.retrospective.read_bytes())
        result = select(document, request)
        publish(args.output, result)
    except (ValueError, OSError, KeyError, TypeError, ArithmeticError) as error:
        parser.exit(2, f'Offline temporal validation failed: {error}\n')
    print(result['result_id'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
