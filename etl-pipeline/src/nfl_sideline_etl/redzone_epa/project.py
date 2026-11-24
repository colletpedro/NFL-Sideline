"""Exact projection. Campaign outcomes never define this play population."""
from collections import Counter
from fractions import Fraction
from math import isfinite

from ..offline_metrics.population import exclusion_reason
from ..offline_metrics.validation import FLAGS
from . import RULE, VERSION, SOURCE_PIN

GUARANTEES = {k: 'UNKNOWN' for k in ('completeness', 'expectedCoverage', 'epaModel', 'historicalAvailability')}


def rational(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def key(row):
    return f"{row['game_id']}:{int(row['play_id'])}"


def summarize(units, exclusions=None, ambiguity=0, missing_source=False, insufficient=False):
    ids = [u['id'] for u in units]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate EPA play identity')
    finite = [u for u in units if u['epaStatus'] == 'VALID']
    total = sum((Fraction(u['epa']) for u in finite), Fraction())
    status = ('SOURCE_ABSENT' if missing_source else 'INSUFFICIENT' if insufficient or ambiguity or (units and not finite)
              else 'AVAILABLE' if finite else 'NO_OPPORTUNITIES')
    return dict(status=status, eligibleN=len(units), validN=len(finite),
                missingN=sum(u['epaStatus'] == 'MISSING' for u in units),
                nonfiniteN=sum(u['epaStatus'] == 'NONFINITE' for u in units), ambiguityN=ambiguity,
                sum=rational(total), mean=rational(total / len(finite)) if status == 'AVAILABLE' else None,
                units=units, exclusions=dict(sorted((exclusions or {}).items())))


def production(rows, offense, defense, game_id, week):
    units, excluded, ambiguity = [], Counter(), 0
    for row in rows:
        if row['game_id'] != game_id or row['posteam'] != offense:
            continue
        if row['defteam'] != defense:
            raise ValueError('EPA participant mismatch')
        if any(row.get(f) not in (None, 0, 1) for f in FLAGS):
            raise ValueError('Invalid EPA filter flag')
        reason = exclusion_reason(row)
        if reason is not None and reason != 'unknown_filter_flags':
            excluded[reason] += 1
            continue
        y = row.get('yardline_100')
        if y is None or not isinstance(y, (int, float)) or isinstance(y, bool) or not isfinite(y) or not 0 <= y <= 100:
            excluded['unknown_position'] += 1
            ambiguity += 1
            continue
        if not 0 < y <= 20:
            excluded['outside_redzone_start'] += 1
            continue
        if reason == 'unknown_filter_flags':
            excluded[reason] += 1
            ambiguity += 1
            continue
        value = row['epa']
        valid = value is not None and isfinite(value)
        units.append(dict(id=key(row), gameId=game_id, week=week, playId=int(row['play_id']),
                          sourceOrder=row['order_sequence'], offense=offense, defense=defense,
                          yardline=y, kind=row['play_type'], sack=row.get('sack') == 1,
                          scramble=row.get('qb_scramble') == 1,
                          epa=str(value) if valid else None,
                          epaStatus='VALID' if valid else 'MISSING' if value is None else 'NONFINITE'))
    units.sort(key=lambda u: (u['sourceOrder'], u['id']))
    return dict(offense=offense, defense=defense, gameIds=[game_id], weeks=[week],
                **summarize(units, excluded, ambiguity))


def aggregate(components):
    present = [c for c in components if c is not None]
    excluded = Counter()
    for c in present:
        excluded.update(c['exclusions'])
    units = sorted([u for c in present for u in c['units']], key=lambda u: (u['week'], u['gameId'], u['sourceOrder'], u['id']))
    return summarize(units, excluded, sum(c['ambiguityN'] for c in present),
                     missing_source=len(present) != len(components) or any(c['status'] == 'SOURCE_ABSENT' for c in present),
                     insufficient=any(c['status'] == 'INSUFFICIENT' for c in present))


def project(index, documents, rows, pbp_hash):
    ids = [key(r) for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Ambiguous raw play identities')
    if {r['game_id'] for r in rows} != {g['gameId'] for g in index['games']}:
        raise ValueError('PBP/calendar inventory mismatch')
    games = {}
    for g in index['games']:
        game_id, week = g['gameId'], g['week']
        game_rows = [r for r in rows if r['game_id'] == game_id]
        if any((r['season'], r['season_type'], r['week'], r['away_team'], r['home_team']) !=
               (2026, 'REG', week, g['away'], g['home']) for r in game_rows):
            raise ValueError('EPA source game context mismatch')
        original = documents[game_id]
        productions = []
        for offense, defense in ((g['away'], g['home']), (g['home'], g['away'])):
            p = production(game_rows, offense, defense, game_id, week)
            old = next(p for p in original['productions'] if p['offense'] == offense)
            eligible = next(e for e in old['epa'] if e['foundation'] == 'general')['eligibleUnitIds']
            if not {u['id'] for u in p['units']} <= set(eligible):
                raise ValueError('Red zone plays must be a subset of classified-scrimmage-v1')
            productions.append(p)
        games[game_id] = dict(gameId=game_id, week=week, away=g['away'], home=g['home'], productions=productions)
    teams = {}
    for team in sorted({g[t] for g in index['games'] for t in ('away', 'home')}):
        members = [g for g in games.values() if team in (g['away'], g['home'])]
        members.sort(key=lambda g: g['week'])
        if [g['week'] for g in members] != [1, 2]:
            raise ValueError('Team W1–2 needs two distinct game components')
        productions = []
        for perspective in ('off', 'def'):
            components = [next(p for p in g['productions'] if p['offense' if perspective == 'off' else 'defense'] == team) for g in members]
            productions.append(dict(perspective=perspective, gameIds=[g['gameId'] for g in members], weeks=[1, 2],
                                     components=[dict(gameId=c['gameIds'][0], week=c['weeks'][0], status=c['status'],
                                                      validN=c['validN'], sum=c['sum'], mean=c['mean']) for c in components],
                                     **aggregate(components)))
        teams[team] = dict(team=team, productions=productions)
    return dict(contractVersion=VERSION, rule=RULE, season=2026, phase='REG', weeks=[1, 2],
                sourcePin=SOURCE_PIN, pbpHash=pbp_hash, guarantees=GUARANTEES,
                policy=dict(display='OBSERVED_SAMPLE', sideBySide='SAME_RULE_SOURCE_PERIOD_AVAILABLE_ONLY',
                            leagueReference=False, prediction=False, qualitySuperiority=False,
                            opponentDefense='SAME_OFFENSIVE_EVIDENCE_NOT_INDEPENDENT'), games=games, teams=teams)
