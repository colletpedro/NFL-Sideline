"""Optional read-only audit of explicitly supplied existing Parquet; no acquisition/DB/env.

Uses installed Polars only. Does not certify source completeness or historical availability.
Writes JSON to stdout; redirect explicitly if a review record is desired.
"""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import polars as pl

FLAGS = ['qb_kneel', 'qb_spike', 'play_deleted', 'special_teams_play', 'two_point_attempt']


def inspect_pbp(path):
    d = pl.read_parquet(path)
    legacy = d.filter(
        pl.col('epa').is_not_null() & pl.col('play_type').is_in(['pass', 'run'])
        & (pl.col('qb_kneel').fill_null(0) == 0) & (pl.col('qb_spike').fill_null(0) == 0)
        & pl.col('posteam').is_not_null() & pl.col('defteam').is_not_null())
    base = d.filter(pl.col('play_type').is_in(['pass', 'run'])
                    & pl.all_horizontal([pl.col(f) == 0 for f in FLAGS])
                    & pl.col('posteam').is_not_null() & pl.col('defteam').is_not_null())
    available = [c for c in ['game_id', 'play_id', 'drive', 'season_type', 'start_time',
                             'time_of_day', 'end_clock_time', 'play_deleted', 'special_teams_play',
                             'two_point_attempt', 'no_play', 'available_at'] if c in d.columns]
    return dict(rows=d.height, games=d['game_id'].n_unique(),
                weeks=d['week'].unique().sort().to_list(),
                phase_counts=d.group_by('season_type').len().sort('season_type').to_dicts(),
                legacy_eligible=legacy.height, proposed_base_before_identity_and_event_validation=base.height,
                eligible_conversions=legacy.filter(pl.col('two_point_attempt') == 1).height,
                eligible_deleted=legacy.filter(pl.col('play_deleted') == 1).height,
                eligible_special=legacy.filter(pl.col('special_teams_play') == 1).height,
                legacy_sacks_in_pass=legacy.filter((pl.col('play_type') == 'pass') & (pl.col('sack') == 1)).height,
                legacy_scrambles_in_run=legacy.filter((pl.col('play_type') == 'run') & (pl.col('qb_scramble') == 1)).height,
                missing_epa_pass_run=d.filter(pl.col('play_type').is_in(['pass', 'run']) & pl.col('epa').is_null()).height,
                nonfinite_epa=d.filter(pl.col('epa').is_not_null() & ~pl.col('epa').is_finite()).height,
                duplicate_game_play=d.height - d.unique(['game_id', 'play_id']).height,
                candidate_null_flags=d.filter(pl.col('play_type').is_in(['pass', 'run'])
                                             & pl.any_horizontal([pl.col(f).is_null() for f in FLAGS])).height,
                structural_mismatch_rows=d.filter(pl.col('play_type').is_in(['pass', 'run']) & (
                    ~pl.col('posteam').is_in(pl.concat_list('home_team', 'away_team'))
                    | ~pl.col('defteam').is_in(pl.concat_list('home_team', 'away_team'))
                    | (pl.col('posteam') == pl.col('defteam')))).height,
                relevant_schema={c: str(d.schema[c]) for c in available},
                classification_examples=legacy.filter((pl.col('qb_scramble') == 1) | (pl.col('sack') == 1))
                .select('game_id', 'play_id', 'drive', 'play_type', 'qb_dropback', 'qb_scramble',
                        'sack', 'pass_attempt', 'epa').head(2).to_dicts(),
                historical_available_at='UNKNOWN', event_end_semantics='NOT_CERTIFIED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--seasons', type=int, nargs='+', required=True)
    args = parser.parse_args()
    report = dict(packageVersion='1.0.0', inspectionDate='2026-10-08',
                  dataAcquired=False, runtime={p: version(p) for p in ['polars', 'nflreadpy', 'pytest']},
                  sourceRoot=str(args.source_root.resolve()), files=[])
    for season in sorted(set(args.seasons)):
        for kind in ['pbp', 'schedules']:
            path = args.source_root / kind / f'season={season}' / f'{kind}.parquet'
            raw = path.read_bytes()
            item = dict(path=str(path.resolve()), season=season, kind=kind,
                        bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            if kind == 'pbp':
                item.update(inspect_pbp(path))
            else:
                d = pl.read_parquet(path)
                item.update(rows=d.height, relevant_fields=[c for c in ['gametime', 'gameday', 'game_type',
                                                                       'status', 'end_time'] if c in d.columns])
            report['files'].append(item)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
