"""Small deterministic Parquet fixtures shared by offline tests and own DB proof."""
from pathlib import Path

import polars as pl

from nfl_sideline_etl.offline_metrics.artifact import json_bytes
from nfl_sideline_etl.offline_metrics.inputs import read_inputs


def fixtures(root, season=2026, *, empty=False, missing=False, metadata=True):
    root = Path(root)
    schedule = root / 'raw/schedules' / f'season={season}' / 'schedules.parquet'
    pbp_dir = root / 'raw/pbp' / f'season={season}'
    schedule.parent.mkdir(parents=True, exist_ok=True)
    pbp_dir.mkdir(parents=True, exist_ok=True)
    suffix = '' if season == 2026 else '-' + str(season)
    games = ['synthetic-' + str(n) + suffix for n in (1, 3, 5, 6)]
    rows = [dict(game_id=g, season=season, week=w, game_type='REG', gameday='2026-09-01',
                 home_team='A', away_team='B', home_score=None, away_score=None, result=None,
                 spread_line=None, total_line=None, home_moneyline=None, away_moneyline=None)
            for g, w in zip(games, (1, 3, 5, 6))]
    rows[0].update(home_moneyline=-120, away_moneyline=110)
    pl.DataFrame(rows).write_parquet(schedule)
    plays = [dict(game_id=games[0], play_id=n, drive=1, season=season, season_type='REG', week=1,
                  posteam='A', defteam='B', play_type=t, qb_kneel=0, qb_spike=0,
                  play_deleted=0, special_teams_play=0, two_point_attempt=0, epa=e)
             for n, t, e in ((1, 'pass', .25), (2, 'run', -.75), (3, 'pass', None))]
    plays.append({**plays[1], 'play_id':4, 'posteam':'B', 'defteam':'A', 'epa':.125})
    last = {**plays[0], 'game_id': games[1], 'week': 3, 'epa': .5}
    pbps = []
    if not missing:
        main = pbp_dir / 'pbp.parquet'
        frame = pl.DataFrame(plays)
        (frame.head(0) if empty else frame).write_parquet(main)
        pbps.append(main)
        if not empty:
            extra = pbp_dir / 'extra.parquet'
            # Exact replica plus another game proves entire partition consumption.
            pl.DataFrame([plays[0], last]).write_parquet(extra)
            pbps.append(extra)
    meta = None
    if metadata and not missing:
        meta = root / f'metadata-{season}.json'
        descriptors = read_inputs([schedule], pbps)[2]
        meta.write_bytes(json_bytes({'metadataVersion': 1,
            'calendar_sha256': sorted({d['sha256'] for d in descriptors if d['kind'] == 'calendar'}),
            'pbp_sha256': sorted({d['sha256'] for d in descriptors if d['kind'] == 'pbp'}),
            'games': {games[-1]: {'completeness': 'COMPLETE', 'expected_unique_rows': 0,
                'evidence': {'basis': 'SYNTHETIC_FIXTURE', 'reference': 'e5b5-fixture-ledger'}}}}))
    return {'calendar': [str(schedule.resolve())], 'pbp': [str(p.resolve()) for p in pbps],
            'metadata': str(meta.resolve()) if meta else None}


def specification(path, entries):
    Path(path).write_bytes(json_bytes({'inputsVersion': 1, 'seasons': {str(k): v for k, v in entries.items()}}))
    return Path(path)
