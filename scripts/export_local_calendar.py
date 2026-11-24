#!/usr/bin/env python3
"""Read existing local schedule Parquet only, using the project's already installed Polars."""
import argparse
from pathlib import Path
import polars as pl
from evaluate_coverage import ROOT, read, write, sha, rel


def build(manifest):
    seasons = sorted({c['descriptors']['season'] for c in manifest['cases'] if c['cohort'] != 'synthetic'})
    schedules = {}
    for season in seasons:
        p = ROOT / f'etl-pipeline/data/raw/schedules/season={season}/schedules.parquet'
        if not p.exists():
            continue
        df = pl.read_parquet(p).filter(pl.col('game_type') == 'REG').select('game_id', 'season', 'week', 'home_team', 'away_team')
        games = df.to_dicts()
        teams = sorted({g[t] for g in games for t in ['home_team', 'away_team']})
        counts = {t: sum(t in [g['home_team'], g['away_team']] for g in games) for t in teams}
        complete = (len(games) == 272 and len({g['game_id'] for g in games}) == 272 and len(teams) == 32
                    and set(counts.values()) == {17} and {g['week'] for g in games} == set(range(1, 19))
                    and all(len({g['week'] for g in games if t in [g['home_team'], g['away_team']]}) == 17 for t in teams))
        schedules[season] = {'path': rel(p), 'sha256': sha(p), 'completeModernRegularSeason': complete, 'games': games}
    cases = {}
    for c in manifest['cases']:
        if c['cohort'] == 'synthetic':
            continue
        schedule = schedules.get(c['descriptors']['season'])
        gaps = []
        for team, weeks in c['descriptors']['missingExpectedWeeks'].items():
            for week in weeks:
                matches = [] if not schedule else [g for g in schedule['games'] if g['week'] == week and team in [g['home_team'], g['away_team']]]
                bye = bool(schedule and schedule['completeModernRegularSeason'] and not matches)
                gaps.append({'team': team, 'week': week, 'byeConfirmed': bye,
                             'cause': 'bye_confirmed_from_complete_schedule' if bye else 'missing_data_cause_unknown',
                             'scheduledGameIds': [g['game_id'] for g in matches]})
        cases[c['gameId']] = {'gaps': gaps, 'source': schedule['path'] if schedule else None,
                              'byeConfirmed': any(g['byeConfirmed'] for g in gaps),
                              'unknownGap': any(not g['byeConfirmed'] for g in gaps)}
    return {'method': 'Modern REG completeness: 272 unique games, 32 teams, 17 distinct weeks/team, weeks 1..18. Missing scheduled week before matchup confirms bye; otherwise unknown.',
            'noScoresOrResultsConsumed': True, 'cases': cases, 'schedules': schedules}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    args = parser.parse_args()
    write(args.base / 'calendar-evidence.json', build(read(args.base / 'manifest.json')))
