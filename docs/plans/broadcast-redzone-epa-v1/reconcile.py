"""Independent raw filter/oracle. Does not import the new projector or classifier."""
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
ROOT = Path(json.loads((HERE/'source-config.json').read_bytes())['path'])
payload = json.loads((ROOT/'redzone-epa.json').read_bytes())
raw = pl.read_parquet(ROOT/'source/sources/situational/pbp.parquet')
assert 'sha256:'+hashlib.sha256((ROOT/'source/sources/situational/pbp.parquet').read_bytes()).hexdigest() == payload['pbpHash']
# Separate columnar filter, including all five explicit zero flags and pre-snap position.
selection = raw.filter(pl.col('play_type').is_in(['pass', 'run']) & (pl.col('qb_kneel') == 0) &
                      (pl.col('qb_spike') == 0) & (pl.col('play_deleted') == 0) &
                      (pl.col('special_teams_play') == 0) & (pl.col('two_point_attempt') == 0) &
                      (pl.col('yardline_100') > 0) & (pl.col('yardline_100') <= 20)).sort('game_id', 'order_sequence')


def check(production, frame):
    rows = frame.to_dicts()
    ids = [f"{r['game_id']}:{int(r['play_id'])}" for r in rows]
    assert ids == [u['id'] for u in production['units']]
    valid = [r for r in rows if r['epa'] is not None and __import__('math').isfinite(r['epa'])]
    total = sum((Fraction(str(r['epa'])) for r in valid), Fraction())
    assert production['eligibleN'] == len(rows) and production['validN'] == len(valid)
    assert production['sum'] == dict(numerator=str(total.numerator), denominator=str(total.denominator))
    mean = total / len(valid) if valid else None
    assert production['mean'] == (dict(numerator=str(mean.numerator), denominator=str(mean.denominator)) if mean is not None else None)
    return dict(status=production['status'], eligibleN=len(rows), validN=len(valid),
                mean=float(mean) if mean is not None else None,
                unitHash=hashlib.sha256('\n'.join(ids).encode()).hexdigest())


games, teams = {}, {}
for game_id, game in payload['games'].items():
    games[game_id] = {p['offense']: check(p, selection.filter((pl.col('game_id') == game_id) & (pl.col('posteam') == p['offense']))) for p in game['productions']}
for team, entry in payload['teams'].items():
    teams[team] = {p['perspective']: check(p, selection.filter(pl.col('posteam' if p['perspective'] == 'off' else 'defteam') == team).sort('week', 'game_id', 'order_sequence')) for p in entry['productions']}

# Original packages stay byte-identical. Campaign counts are independently kept separate.
source = ROOT/'source'
marker = json.loads((source/'COMPLETED.json').read_bytes())
for name, digest in marker['files'].items():
    assert 'sha256:'+hashlib.sha256((source/name).read_bytes()).hexdigest() == digest
counts = Counter(p['status'] for g in payload['games'].values() for p in g['productions'])
report = dict(pin='sha256:'+hashlib.sha256((ROOT/'redzone-epa.json').read_bytes()).hexdigest(),
              rawRows=raw.height, selectedPlays=selection.height, gameProductions=64, teamPerspectives=64,
              states=dict(counts), games=games, teams=teams,
              sourceFilesVerified=len(marker['files']), differences=0)
(HERE/'checks').mkdir(exist_ok=True)
(HERE/'checks/reconciliation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('games','teams')}))
