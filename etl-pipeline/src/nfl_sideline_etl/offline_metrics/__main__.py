"""python -m nfl_sideline_etl.offline_metrics --calendar FILE --pbp FILE --output NEW_DIR"""
import argparse
from pathlib import Path

from ..seasons import normalize_seasons
from .artifact import calculate, ensure_destination, write_artifact
from .inputs import load_json, read_inputs


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline dry-run: explicit local inputs, no DB/network/env")
    parser.add_argument("--calendar", type=Path, action="append", required=True)
    parser.add_argument("--pbp", type=Path, action="append", required=True)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--season", type=int, action="append")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        output = ensure_destination(args.output)
        seasons = normalize_seasons(args.season) if args.season else None
        calendars, plays, inputs = read_inputs(args.calendar, args.pbp)
        metadata = load_json(args.metadata.read_bytes()) if args.metadata else None
        result = calculate(calendars, plays, inputs, metadata, seasons=seasons)
        write_artifact(output, result)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"Offline validation failed: {exc}\n")
    print(result["manifest.json"]["calculation_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
