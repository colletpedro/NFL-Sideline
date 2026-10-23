"""Offline situational-v1. Raw preserved PBP only; no DB, acquisition or EPA filters."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import polars as pl

VERSION = 'situational-v1'
DEFINITIONS = '1.0.0'
CALCULATION = '1.0.0'
RAW_HASH = 'sha256:4e3707397912babcd0d7d02abd3be95db8e66785250e62bf9d874f37229d895e'
MATERIALIZATION = 'sha256:f7a70f61b442d8d631e858ac05c5c6191652b8d0ed0ffd5a7ac8094939a8d3fa'
INPUT = 'sha256:9dc7e6de11af1d0e494877c82f6cc234be3cbe002ab5ee47bf29cc2cf1d3a0e6'
FIELDS = '''game_id play_id season season_type week home_team away_team posteam defteam down play_type order_sequence ydstogo yardline_100 third_down_converted third_down_failed first_down_penalty play_deleted aborted_play qb_kneel qb_spike qb_scramble sack qb_dropback pass_attempt rush_attempt penalty extra_point_attempt two_point_attempt fixed_drive drive fixed_drive_result touchdown td_team field_goal_result interception fumble_lost fourth_down_failed safety qtr game_seconds_remaining drive_inside20 drive_ended_with_score desc'''.split()


def encoded(v):
    return (json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(b):
    return 'sha256:' + hashlib.sha256(b).hexdigest()


def save(p, v):
    p.write_bytes(encoded(v))


def safe(p):
    p = Path(p)
    if not p.is_absolute() or '..' in p.parts or any(x.is_symlink() for x in (p, *p.parents)):
        raise ValueError('Absolute physical path required')
    return p


def play_key(r):
    return f"{r['game_id']}:{int(r['play_id'])}"


def scrimmage(r):
    return (r['down'] in (1, 2, 3, 4) and r['play_deleted'] == 0 and
            r['extra_point_attempt'] == 0 and r['two_point_attempt'] == 0 and
            r['play_type'] in ('pass', 'run', 'qb_kneel', 'qb_spike', 'field_goal', 'punt', 'no_play') and
            (r['play_type'] != 'no_play' or r['penalty'] == 1))


def third(r, duplicate=False):
    """Classification reason is exclusive. Penalty advances are orthogonal metadata."""
    reason = None
    if duplicate:
        reason = 'DUPLICATE'
    elif r['play_deleted'] != 0:
        reason = 'DELETED' if r['play_deleted'] == 1 else 'UNKNOWN_FLAGS'
    elif r['extra_point_attempt'] != 0 or r['two_point_attempt'] != 0:
        reason = 'TRY'
    elif r['play_type'] == 'no_play':
        reason = 'NO_PLAY'
    elif r['qb_kneel'] == 1 or r['play_type'] == 'qb_kneel':
        reason = 'KNEEL'
    elif r['qb_spike'] == 1 or r['play_type'] == 'qb_spike':
        reason = 'SPIKE'
    elif r['aborted_play'] == 1:
        reason = 'ABORTED'
    elif r['play_type'] not in ('pass', 'run'):
        reason = 'OTHER_TYPE'
    elif any(r[c] != 0 for c in ('aborted_play', 'qb_kneel', 'qb_spike')):
        reason = 'UNKNOWN_FLAGS'
    elif (r['third_down_converted'], r['third_down_failed']) not in ((1, 0), (0, 1)):
        reason = 'CONTRADICTORY_FLAGS'
    bucket = 'unknown'
    yards = r['ydstogo']
    if isinstance(yards, (int, float)) and yards > 0 and yards == int(yards):
        bucket = 'short' if yards <= 3 else 'medium' if yards <= 6 else 'long'
    return dict(id=play_key(r), gameId=r['game_id'], week=r['week'], offense=r['posteam'], defense=r['defteam'],
                included=reason is None, reason=reason, converted=int(r['third_down_converted']) if reason is None else None,
                kind=r['play_type'] if reason is None else None, distance=bucket,
                penaltyFirstDown=r['first_down_penalty'] == 1, sack=r['sack'] == 1, scramble=r['qb_scramble'] == 1,
                uncertain=reason in ('DUPLICATE', 'UNKNOWN_FLAGS', 'CONTRADICTORY_FLAGS'))


RESULTS = {'TOUCHDOWN': 'Touchdown', 'FIELD_GOAL': 'Field goal', 'MISSED_FIELD_GOAL': 'Missed field goal',
           'TURNOVER': 'Turnover', 'OPPONENT_TOUCHDOWN': 'Opp touchdown', 'DOWNS': 'Turnover on downs',
           'PUNT': 'Punt', 'END_HALF_GAME': 'End of half', 'SAFETY': 'Safety'}


def campaign(rows, duplicates):
    rows = sorted(rows, key=lambda r: r['order_sequence'])
    s = [r for r in rows if scrimmage(r)]
    base = dict(id=f"{rows[0]['game_id']}:drive:{rows[0]['fixed_drive']}", gameId=rows[0]['game_id'], week=rows[0]['week'],
                offense=None, defense=None, included=False, reason='NO_SCRIMMAGE', uncertain=False,
                entryPlayIds=[], playIds=[play_key(r) for r in rows], rawDrives=sorted({r['drive'] for r in rows if r['drive'] is not None}),
                touchdownPlayIds=[], outcome=None, auxiliaryInside20=any(r['drive_inside20'] == 1 for r in rows),
                auxiliaryScored=any(r['drive_ended_with_score'] == 1 for r in rows))
    if not s:
        suspect = [r for r in rows if r['down'] in (1, 2, 3, 4) and r['play_deleted'] not in (0, 1)]
        if suspect:
            base.update(offense=suspect[0]['posteam'], defense=suspect[0]['defteam'], uncertain=True, reason='INSUFFICIENT_CAMPAIGN')
        return base
    pairs = {(r['posteam'], r['defteam']) for r in s}
    base['offense'], base['defense'] = s[0]['posteam'], s[0]['defteam']
    entries = [r for r in s if r['yardline_100'] is not None and 0 < r['yardline_100'] <= 20]
    base['entryPlayIds'] = [play_key(r) for r in entries]
    # Each entry is evidence, but the opportunity remains exactly one drive.
    invalid = (len(pairs) != 1 or None in next(iter(pairs)) or rows[0]['fixed_drive'] is None or
               any(play_key(r) in duplicates for r in rows) or
               any(r['play_deleted'] not in (0, 1) for r in rows if r['down'] in (1, 2, 3, 4)) or
               any(r['yardline_100'] is None or not 0 <= r['yardline_100'] <= 100 for r in s))
    live = [r for r in s if r['play_type'] != 'no_play']
    tds = [r for r in live if r['touchdown'] == 1 and r['td_team'] == base['offense'] and r['play_type'] in ('pass', 'run')]
    base['touchdownPlayIds'] = [play_key(r) for r in tds]
    outcome = None
    if s:
        last = s[-1]
        if tds:
            outcome = 'TOUCHDOWN'
            invalid |= len(tds) != 1 or tds[-1] is not last
        elif last['touchdown'] == 1 and last['td_team'] == base['defense']:
            outcome = 'OPPONENT_TOUCHDOWN'
        elif last['play_type'] == 'punt':
            outcome = 'PUNT'
        elif last['interception'] == 1 or last['fumble_lost'] == 1:
            outcome = 'TURNOVER'
        elif last['safety'] == 1:
            outcome = 'SAFETY'
        elif last['play_type'] == 'field_goal' and last['field_goal_result'] in ('made', 'missed', 'blocked'):
            outcome = 'FIELD_GOAL' if last['field_goal_result'] == 'made' else 'MISSED_FIELD_GOAL'
        elif last['down'] == 4 and last['fourth_down_failed'] == 1:
            outcome = 'DOWNS'
        elif any((r['qtr'] == 2 and r['game_seconds_remaining'] == 1800 or r['qtr'] >= 4 and r['game_seconds_remaining'] == 0)
                 and r['desc'] and ('END QUARTER' in r['desc'] or 'END GAME' in r['desc']) for r in rows):
            outcome = 'END_HALF_GAME'
        invalid |= any(r['touchdown'] not in (0, 1) or (r['touchdown'] == 1 and r['td_team'] not in (base['offense'], base['defense'])) for r in live)
    fixed = {r['fixed_drive_result'] for r in rows}
    invalid |= outcome is None or fixed != {RESULTS.get(outcome)}
    base.update(outcome=outcome, uncertain=bool(invalid), included=bool(entries) and not invalid,
                reason='INSUFFICIENT_CAMPAIGN' if invalid else None if entries else 'NO_ENTRY')
    return base


def measure(units, family):
    included = [u for u in units if u['included']]
    # Non-entry campaigns with proven positions cannot change the denominator.
    ambiguous = [u for u in units if u['uncertain'] and (family == 'third' or u['entryPlayIds'] or u['reason'] == 'INSUFFICIENT_CAMPAIGN')]
    n = sum(u['converted'] if family == 'third' else u['outcome'] == 'TOUCHDOWN' for u in included)
    den = len(included)
    status = 'INSUFFICIENT' if ambiguous else 'AVAILABLE' if den else 'NO_OPPORTUNITIES'
    out = dict(status=status, numerator=n, denominator=den, denominatorState='POSITIVE' if den else 'ZERO',
               ratio=dict(numerator=n, denominator=den) if status == 'AVAILABLE' else None,
               unitIds=[u['id'] for u in included], excludedIds=[u['id'] for u in units if not u['included']],
               exclusions=dict(sorted(Counter(u['reason'] for u in units if not u['included']).items())), ambiguousIds=[u['id'] for u in ambiguous])
    if family == 'third':
        out['byType'] = {k: dict(numerator=sum(u['converted'] for u in included if u['kind'] == k), denominator=sum(u['kind'] == k for u in included)) for k in ('pass', 'run')}
        out['byDistance'] = {k: dict(numerator=sum(u['converted'] for u in included if u['distance'] == k), denominator=sum(u['distance'] == k for u in included)) for k in ('short', 'medium', 'long', 'unknown')}
        out['penaltyFirstDowns'] = dict(included=sum(u['penaltyFirstDown'] for u in included), excluded=sum(u['penaltyFirstDown'] for u in units if not u['included']))
        out['sacks'] = sum(u['sack'] for u in included)
        out['scrambles'] = sum(u['scramble'] for u in included)
    else:
        out['outcomes'] = dict(sorted(Counter(u['outcome'] for u in included).items()))
        out['observedEntries'] = sum(bool(u['entryPlayIds']) for u in units)
    return out


def calculate(raw, provenance):
    df = pl.read_parquet(raw)
    if set(FIELDS) - set(df.columns):
        raise ValueError('Missing PBP schema fields')
    rs = df.select(FIELDS).sort('game_id', 'order_sequence').to_dicts()
    if not rs or any((r['season'], r['season_type'], r['week']) not in ((2026, 'REG', 1), (2026, 'REG', 2)) for r in rs):
        raise ValueError('Only preserved 2026 REG W1–2 allowed')
    games = {}
    for r in rs:
        g = dict(gameId=r['game_id'], week=r['week'], home=r['home_team'], away=r['away_team'])
        if r['game_id'] in games and games[r['game_id']] != g:
            raise ValueError('Contradictory game metadata')
        games[r['game_id']] = g
    duplicates = {k for k, n in Counter(play_key(r) for r in rs).items() if n > 1}
    thirds = [third(r, play_key(r) in duplicates) for r in rs if r['down'] == 3]
    grouped = defaultdict(list)
    for r in rs:
        grouped[(r['game_id'], r['fixed_drive'])].append(r)
    drives = [campaign(rows, duplicates) for rows in grouped.values()]
    blocks = defaultdict(list)
    for r in rs:
        b = blocks[r['game_id']]
        if not b or b[-1] != r['fixed_drive']:
            b.append(r['fixed_drive'])
    reopened = {(g, d) for g, b in blocks.items() for d, n in Counter(b).items() if n > 1}
    for u in drives:
        if any(u['gameId'] == g and u['id'] == f'{g}:drive:{d}' for g, d in reopened):
            u.update(included=False, uncertain=True, reason='INSUFFICIENT_CAMPAIGN')
    teams = sorted({g[k] for g in games.values() for k in ('home', 'away')})
    if len(games) != 32 or len(teams) != 32:
        raise ValueError('Expected observed 32 games / 32 teams')
    for w in (1, 2):
        if Counter(g[k] for g in games.values() if g['week'] == w for k in ('home', 'away')) != Counter({t: 1 for t in teams}):
            raise ValueError('Participant/week association mismatch')
    if any(r['posteam'] not in (r['home_team'], r['away_team']) or r['defteam'] not in (r['home_team'], r['away_team']) or r['posteam'] == r['defteam'] for r in rs if scrimmage(r)):
        raise ValueError('Unattributed scrimmage')
    documents = []
    for t in teams:
        for side in ('off', 'def'):
            for weeks in ([1], [2], [1, 2]):
                members = [g for g in games.values() if g['week'] in weeks and t in (g['home'], g['away'])]
                ids = {g['gameId'] for g in members}
                key = 'offense' if side == 'off' else 'defense'
                ts = [u for u in thirds if u['gameId'] in ids and u[key] == t]
                ds = [u for u in drives if u['gameId'] in ids and u[key] == t]
                documents.append(dict(id=f"{t}/{side}/{'-'.join(map(str,weeks))}", team=t, perspective=side, season=2026, phase='REG', weeks=weeks,
                                      games=[dict(**g, opponent=g['away'] if t == g['home'] else g['home']) for g in members],
                                      third=measure(ts, 'third'), redZone=measure(ds, 'redZone')))
    ledger = dict(version=VERSION, third=thirds, campaigns=drives)
    payload = dict(contractVersion=VERSION, definitionsVersion=DEFINITIONS, calculationVersion=CALCULATION,
                   provenance=provenance, guarantees={k: 'UNKNOWN' for k in ('completeness', 'expectedCoverage', 'epaModel', 'temporalKnowledge')},
                   games=list(games.values()), documents=documents, ledgerHash=digest(encoded(ledger)))
    return payload, ledger


def read(root):
    root = safe(root)
    files = ('pbp.parquet', 'provenance.json', 'situational.json', 'ledger.json')
    if {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} != {*files, 'COMPLETED.json'} or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Invalid physical package')
    marker = json.loads((root / 'COMPLETED.json').read_bytes())
    if marker['version'] != VERSION or marker['files'] != {f: digest((root / f).read_bytes()) for f in files}:
        raise ValueError('Package integrity mismatch')
    provenance = json.loads((root / 'provenance.json').read_bytes())
    if provenance['materializationId'] != MATERIALIZATION or provenance['inputId'] != INPUT:
        raise ValueError('Lineage pin mismatch')
    if provenance['rawHash'] != RAW_HASH or digest((root / 'pbp.parquet').read_bytes()) != RAW_HASH:
        raise ValueError('Preserved PBP pin mismatch')
    data, ledger = calculate(root / 'pbp.parquet', provenance)
    if encoded(data) != (root / 'situational.json').read_bytes() or encoded(ledger) != (root / 'ledger.json').read_bytes() or marker['bundleId'] != digest(encoded(data)):
        raise ValueError('Derivation mismatch')
    return data, marker


def generate(raw, provenance_path, output):
    raw, output = safe(raw), safe(output)
    if output.exists():
        raise ValueError('Refusing to overwrite bundle')
    provenance = json.loads(Path(provenance_path).read_bytes())
    if digest(raw.read_bytes()) != RAW_HASH or provenance['rawHash'] != RAW_HASH or provenance['materializationId'] != MATERIALIZATION or provenance['inputId'] != INPUT:
        raise ValueError('Source pins mismatch')
    data, ledger = calculate(raw, provenance)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.situational-', dir=output.parent))
    try:
        shutil.copyfile(raw, stage / 'pbp.parquet')
        save(stage / 'provenance.json', provenance)
        save(stage / 'situational.json', data)
        save(stage / 'ledger.json', ledger)
        save(stage / 'COMPLETED.json', dict(version=VERSION, bundleId=digest(encoded(data)), files={f: digest((stage / f).read_bytes()) for f in ('pbp.parquet', 'provenance.json', 'situational.json', 'ledger.json')}))
        read(stage)
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return digest(encoded(data))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    g = sub.add_parser('generate'); g.add_argument('--raw', required=True); g.add_argument('--provenance', required=True); g.add_argument('--output', required=True)
    v = sub.add_parser('validate'); v.add_argument('--bundle', required=True)
    s = sub.add_parser('serve-snapshot'); s.add_argument('--config', required=True)
    a = p.parse_args()
    if a.command == 'generate':
        print(generate(a.raw, a.provenance, a.output))
    elif a.command == 'validate':
        data, marker = read(a.bundle); print(json.dumps(dict(bundleId=marker['bundleId'], documents=len(data['documents']))))
    else:
        cfg = json.loads(safe(a.config).read_bytes())
        if set(cfg) != {'configVersion', 'bundle', 'expectedBundleId'} or cfg['configVersion'] != 'situational-config-v1':
            raise ValueError('Invalid operator config')
        data, marker = read(cfg['bundle'])
        if cfg['expectedBundleId'] != marker['bundleId']:
            raise ValueError('Configured pin mismatch')
        print(encoded(dict(transportVersion='situational-response-v1', bundleId=marker['bundleId'], data=data)).decode(), end='')


if __name__ == '__main__':
    main()
