"""Nominal selection only after full operational lineage readers; no acquisition."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'etl-pipeline/src'))
from nfl_sideline_etl.metrics_observations.lineage import load_source
from nfl_sideline_etl.metrics_observations.publication import read, safe_path


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*')) if p.is_file()}


def select(source, backup, output):
    for p in (source, backup, output):
        assert p.is_absolute(); safe_path(p)
    assert not output.exists(), 'New durable destination required'
    before = hashes(source)
    assert before == hashes(backup), 'Preserved copies differ'
    print('Full operational materialization readers: primary and backup...', flush=True)
    temporal, lineage = load_source(source / 'materialized')
    bt, bl = load_source(backup / 'materialized')
    assert temporal == bt and lineage == bl
    old, old_manifest = read(source / 'bundle')
    bd, bm = read(backup / 'bundle')
    assert old == bd and old_manifest == bm and len(old) == 48
    calendars = [r for r in temporal['resources'] if r['kind'] == 'CALENDAR' and
                 (r['payload']['season'], r['payload']['phase']) == (2026, 'REG')]
    assert len(calendars) == 1
    cal = calendars[0]
    games = sorted([g for g in cal['payload']['games'] if g['week'] in (1, 2)], key=lambda g: g['game_id'])
    assert len(games) == len({g['game_id'] for g in games}) == 32
    teams = sorted({g[k] for g in games for k in ('home_team', 'away_team')})
    assert len(teams) == 32
    for week in (1, 2):
        assert Counter(g[k] for g in games if g['week'] == week for k in ('home_team', 'away_team')) == Counter({t: 1 for t in teams})
    counts = Counter((c['game']['season'], c['game']['phase']) for c in temporal['calculations'])
    assert counts == {(2025, 'REG'): 272, (2025, 'POST'): 13, (2026, 'REG'): 32}
    original_request = json.loads((source / 'bundle/request.json').read_bytes())
    calendars_2026 = {r['calendarSourceSetId'] for r in original_request['requests'] if r['season'] == 2026}
    assert len(calendars_2026) == 1
    calendar_set = next(iter(calendars_2026))
    assert calendar_set in cal['dependencies']
    choices = {s['calculation_id']: s for s in lineage['relations']['selection']}
    associations = []
    for g in games:
        rows = [r for r in lineage['relations']['relations']['metric_calculation_coverage'] if r['game_id'] == g['game_id']]
        assert len(rows) == 1, 'Ambiguous association; refuse selection'
        row = rows[0]; chosen = choices[row['calculation_id']]
        candidates = [c for c in temporal['calculations'] if c['game'] == g and
                      c['calculation_id'] == row['calculation_id'] and c['coverage_revision_id'] == row['coverage_revision_id']]
        assert len(candidates) == 1
        c = candidates[0]
        assert c['calendar_revision_id'] == cal['revision_id']
        associations.append(dict(gameId=g['game_id'], calculationId=row['calculation_id'],
            coverageRevisionId=row['coverage_revision_id'], artifactId=chosen['artifact_id'],
            archiveId=chosen['archive_id'], temporalRevisionId=c['revision_id']))
    requests = []
    for weeks in ([1], [2], [1, 2]):
        ids = {g['game_id'] for g in games if g['week'] in weeks}
        requests.append(dict(season=2026, phase='REG', weeks=weeks, origin='CURRENT', teams=teams,
            roles=['off', 'def'], foundations=['general', 'classified_pass', 'classified_rush'],
            calendarSourceSetId=calendar_set, calendarRevisionId=cal['revision_id'],
            associations=[a for a in associations if a['gameId'] in ids]))
    retained = [r for r in original_request['requests'] if
                (r['season'], r['phase'], r['teams'], r['weeks']) in
                [(2025, 'POST', ['NE'], [19, 20, 21, 22]), (2026, 'REG', ['BAL'], [3])]]
    assert len(retained) == 2
    requests.extend(retained)
    request = dict(requestVersion=original_request['requestVersion'], source=original_request['source'],
        derivedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        presentation=original_request['presentation'], requests=requests)
    assert request['source'] == dict(materializationId=lineage['materialization_id'], temporalInputId=lineage['temporalInputId'])
    output.mkdir(parents=True)
    save(output / 'request.json', request)
    inventory = dict(source=str(source), backup=str(backup), sourceIdentities=request['source'],
        fullOperationalMaterializationReaders=2, fullOperationalOldBundleReaders=2,
        observedCohorts=[dict(season=s, phase=p, games=n) for (s,p),n in sorted(counts.items())],
        games=games, teams=teams, associations=associations, expectedIndividual=384,
        expectedInclusive=192, expectedExpansion=576, retainedLegacy=12, expectedActive=588,
        activePolicy='Single explicit new bundle: 576 expansion + unchanged nominal NE POST2025/BAL W3 selections. Old 36 BAL/DAL W1–2 documents retained only in untouched historical bundle.',
        sourceFileHashes={r['revision_id']: r['payload']['sha256'] for r in temporal['resources'] if r['kind'] == 'FILE'})
    save(output / 'selection.json', inventory)
    save(output / 'preserved-hashes.json', before)
    assert hashes(source) == before == hashes(backup)
    print(json.dumps({k: inventory[k] for k in ('expectedIndividual','expectedInclusive','expectedExpansion','expectedActive')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('source','backup','output'): p.add_argument('--'+key, type=Path, required=True)
    a = p.parse_args(); select(a.source, a.backup, a.output)
