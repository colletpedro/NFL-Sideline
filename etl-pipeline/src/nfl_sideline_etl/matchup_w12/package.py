"""Atomic, self-contained collection; full rederivation before serving any bytes."""
import base64
from io import BytesIO
import json
from pathlib import Path
import shutil
import tempfile

import polars as pl

from ..situational import safe, encoded, digest
from ..comparison_foundation.package import hashes, verified_sources, read as read_pilot
from ..metrics_observations.publication import exact_tree
from ..offline_metrics.artifact import rename_exclusive
from . import VERSION, PILOT_PIN
from ..comparison_foundation import SITUATIONAL_PIN, OBSERVATION_PIN
from .project import project

REQUEST = dict(contractVersion=VERSION, season=2026, phase='REG', weeks=[1, 2],
               gameScope='EXACT_FROZEN_CALENDAR_AND_PBP_INVENTORY', context='RETROSPECTIVE',
               league='MATCHING_SINGLE_WEEK_OFFENSIVE_PRODUCTIONS', epaLeagueReference=False)


def calendar(temporal, inventory):
    resources = {r['revision_id']: r for r in temporal['resources'] if r['kind'] == 'FILE'}
    frames = {}
    result = []
    for g in sorted(inventory, key=lambda g: g['gameId']):
        candidates = [c for c in temporal['calculations'] if c['game']['game_id'] == g['gameId']]
        if not candidates:
            raise ValueError('Calendar calculation absent')
        inputs = {i['source_revision_id'] for c in candidates for i in c['original']['manifest']['inputs'] if i['kind'] == 'calendar'}
        if len(inputs) != 1:
            raise ValueError('Ambiguous calendar sources')
        pin = next(iter(inputs))
        if pin not in frames:
            b = base64.b64decode(resources[pin]['payload']['bytes_base64'], validate=True)
            if digest(b) != pin:
                raise ValueError('Calendar hash mismatch')
            frames[pin] = pl.read_parquet(BytesIO(b))
        selected = frames[pin].filter(pl.col('game_id') == g['gameId']).to_dicts()
        if len(selected) != 1:
            raise ValueError('Calendar identity not unique')
        row = selected[0]
        if (row['season'], row['game_type'], row['week'], row['away_team'], row['home_team']) != (2026, 'REG', g['week'], g['away'], g['home']):
            raise ValueError('Calendar/PBP participant or period mismatch')
        scores = [row[k] for k in ('away_score', 'home_score', 'result')]
        if not all(v is None for v in scores):
            if any(isinstance(v, bool) or not isinstance(v, int) for v in scores) or min(scores[:2]) < 0 or scores[1]-scores[0] != scores[2]:
                raise ValueError('Invalid atomic score trio')
        result.append(dict(**g, season=2026, phase='REG', gameday=row['gameday'], awayScore=scores[0], homeScore=scores[1], result=scores[2],
                           calendarSourceHash=pin, calendarOrigin=resources[pin]['payload']['origin']))
    if len(result) != 32 or len({g['gameId'] for g in result}) != 32:
        raise ValueError('Expected unique 32-game inventory')
    return result


def derive(root):
    if json.loads((root/'request.json').read_bytes()) != REQUEST:
        raise ValueError('Unsupported collection request')
    sit, ledger, observations, temporal = verified_sources(root/'sources/situational', root/'sources/observations')
    games = calendar(temporal, sit['games'])
    policy = (root/'policy.md').read_text()
    definitions = (root/'definitions.md').read_text()
    receipt = json.loads((root/'source-receipt.json').read_bytes())
    documents = {}
    for g in games:
        d = project(sit, ledger, observations, temporal, root/'sources/situational/pbp.parquet', REQUEST, policy, receipt, definitions, g)
        d['calendar'] = g
        documents[g['gameId']] = encoded(d)
    index = dict(contractVersion=VERSION, projectionVersion='1.0.0', request=REQUEST,
                 games=[dict(**g, documentHash=digest(documents[g['gameId']]), path='games/'+g['gameId']+'.json') for g in games],
                 sources=dict(situationalBundleId=SITUATIONAL_PIN, observationBundleId=OBSERVATION_PIN, pbpHash=sit['provenance']['rawHash']),
                 counts=dict(games=len(games), offensiveProductions=len(games)*2), historicalAvailability='UNKNOWN')
    return encoded(index), documents


def read(root, expected_pin=None):
    root = safe(root)
    marker = json.loads((root/'COMPLETED.json').read_bytes())
    if set(marker) != {'version', 'bundleId', 'files'} or marker['version'] != VERSION:
        raise ValueError('Invalid collection marker')
    index_bytes = (root/'index.json').read_bytes()
    pin = digest(index_bytes)
    if marker['bundleId'] != pin or expected_pin is not None and pin != expected_pin:
        raise ValueError('Collection pin mismatch')
    index = json.loads(index_bytes)
    # Names come from validated inventory, never from a request path.
    ids = [g['gameId'] for g in index['games']]
    if len(ids) != 32 or len(set(ids)) != 32 or any(not isinstance(i, str) or not __import__('re').fullmatch(r'2026_0[12]_[A-Z]{2,3}_[A-Z]{2,3}', i) for i in ids):
        raise ValueError('Invalid collection game inventory')
    names = {'index.json', 'request.json', 'policy.md', 'definitions.md', 'source-receipt.json'} | {'games/'+i+'.json' for i in ids}
    names |= {'sources/'+name+'/'+f for name in ('situational', 'observations') for f in hashes(root/'sources'/name)}
    exact_tree(root, names | {'COMPLETED.json'})
    if marker['files'] != {n: digest((root/n).read_bytes()) for n in names}:
        raise ValueError('Collection file hash mismatch')
    actual_index, docs = derive(root)
    if actual_index != index_bytes or any((root/'games'/(i+'.json')).read_bytes() != b for i, b in docs.items()):
        raise ValueError('Collection derivation mismatch')
    return index, docs, marker


def publish(output, populate):
    output = safe(output)
    if output.exists():
        raise ValueError('New destination required; overwriting forbidden')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.'+output.name+'.pending-', dir=output.parent))
    try:
        populate(stage)
        b, docs = derive(stage)
        (stage/'index.json').write_bytes(b)
        (stage/'games').mkdir()
        for i, payload in docs.items():
            (stage/'games'/(i+'.json')).write_bytes(payload)
        marker = dict(version=VERSION, bundleId=digest(b), files=hashes(stage))
        (stage/'COMPLETED.json').write_bytes(encoded(marker))
        read(stage, marker['bundleId'])
        rename_exclusive(stage, output)
        return marker
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def generate(pilot, output, policy):
    pilot, output = safe(pilot), safe(output)
    if pilot == output or pilot in output.parents or output in pilot.parents:
        raise ValueError('Source and output must be disjoint')
    read_pilot(pilot, PILOT_PIN)
    before = hashes(pilot)
    def populate(stage):
        shutil.copytree(pilot/'sources', stage/'sources')
        (stage/'request.json').write_bytes(encoded(REQUEST))
        (stage/'definitions.md').write_bytes((pilot/'definitions.md').read_bytes())
        (stage/'policy.md').write_text(policy)
        (stage/'source-receipt.json').write_bytes(encoded(dict(version=VERSION, pilotReadPin=PILOT_PIN,
             pilotFiles=before, sourceReader='comparison-foundation full reader + original situational/observations readers',
             meaning='Pilot pin identifies the read source only, never authorizes other matchups; this collection has its own pin and policy.')))
        if hashes(pilot) != before:
            raise ValueError('Original changed during copy')
    return publish(output, populate)


def reproduce(source, output):
    source, output = safe(source), safe(output)
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('Source and output must be disjoint')
    _, _, original = read(source)
    def populate(stage):
        shutil.copytree(source/'sources', stage/'sources')
        for name in ('request.json', 'definitions.md', 'policy.md', 'source-receipt.json'):
            shutil.copyfile(source/name, stage/name)
    marker = publish(output, populate)
    if marker != original or hashes(source) != hashes(output):
        raise ValueError('Reproduction differs')
    return marker
