"""Small deterministic SYNTHETIC accepted chain; no DB, archive acquisition or network.

Synthetic receipts are explicit fixture premises, never real historical evidence.
All source bytes are embedded in the resulting materialization, independent of tmp.
"""
import base64
from copy import deepcopy
from pathlib import Path
import tempfile

from nfl_sideline_etl.offline_metrics.artifact import calculate, identity, json_bytes, write_artifact
from nfl_sideline_etl.offline_metrics.inputs import read_inputs, load_json
from nfl_sideline_etl.offline_metrics.validation import CALENDAR_FIELDS, PBP_FIELDS
from nfl_sideline_etl.metrics_persistence.plan import prepare
from nfl_sideline_etl.metrics_materialization.relations import records
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.publication import publish
from nfl_sideline_etl.metrics_observations import REQUEST_VERSION

DERIVED = '2026-10-15T12:00:00Z'
ARCHIVE_ID = '05050505-5555-4555-8555-555555555555'


def source_fixture(*, variant='default', model='UNKNOWN'):
    with tempfile.TemporaryDirectory(prefix='nfl-e5c2-synthetic-') as tmp:
        root = Path(tmp)
        games = [{'game_id': 'synthetic-' + str(i), 'season': 2026, 'game_type': 'REG',
                  'week': week, 'home_team': 'AAA', 'away_team': 'BBB'}
                 for i, week in ((1, 1), (2, 2), (3, 2), (4, 3))]
        row = dict(game_id='synthetic-1', play_id=1, drive=1, season=2026,
                   season_type='REG', week=1, posteam='AAA', defteam='BBB', play_type='pass',
                   qb_kneel=0, qb_spike=0, play_deleted=0, special_teams_play=0,
                   two_point_attempt=0, epa='0')
        plays = [row, {**row, 'play_id': 2, 'play_type': 'run', 'epa': None},
                 {**row, 'play_id': 3, 'epa': '-0.0000000000000000000000000000001'},
                 {**row, 'play_id': 4, 'posteam': 'BBB', 'defteam': 'AAA', 'epa': '0.1'},
                 {**row, 'play_id': 5, 'qb_spike': None, 'epa': '2'},
                 {**row, 'game_id': 'synthetic-3', 'week': 2, 'play_type': 'no_play', 'epa': None}]
        if variant == 'empty-file':
            plays = []
        if variant == 'no-epa':
            plays = [{**r, 'epa': None} for r in plays]
        if variant == 'zero':
            plays = [{**r, 'epa': '0' if r['epa'] is not None else None} for r in plays]
        calendar = root / 'calendar.json'
        calendar.write_bytes(json_bytes({'columns': list(CALENDAR_FIELDS), 'rows': games}))
        pbp = root / 'pbp.json'
        pbp.write_bytes(json_bytes({'columns': list(PBP_FIELDS), 'rows': plays}))
        pbps = [pbp]
        if variant in ('mixed-model', 'mixed-unknown'):
            second = root / 'pbp-second.json'
            pbp.write_bytes(json_bytes({'columns': list(PBP_FIELDS), 'rows': plays[:2]}))
            second.write_bytes(json_bytes({'columns': list(PBP_FIELDS), 'rows': plays[2:]}))
            pbps.append(second)
        inputs = read_inputs([calendar], pbps)
        metadata = {'metadataVersion': 1,
            'calendar_sha256': sorted({i['sha256'] for i in inputs[2] if i['kind'] == 'calendar'}),
            'pbp_sha256': sorted({i['sha256'] for i in inputs[2] if i['kind'] == 'pbp'}),
            'games': {'synthetic-4': {'completeness': 'COMPLETE', 'expected_unique_rows': 0,
                'evidence': {'basis': 'SYNTHETIC_FIXTURE', 'reference': 'synthetic-empty-population'}}},
            'sources': {i['sha256']: {'source_model_version': {'value': model,
                'evidence': {'basis': 'SYNTHETIC_FIXTURE', 'reference': 'synthetic-model'}}}
                for i in inputs[2] if i['kind'] == 'pbp'} if model != 'UNKNOWN' else {}}
        if variant == 'partial':
            metadata['games']['synthetic-1'] = {'completeness': 'PARTIAL',
                'evidence': {'basis': 'SYNTHETIC_FIXTURE', 'reference': 'synthetic-partial'}}
        if variant in ('mixed-model', 'mixed-unknown'):
            sources = sorted({i['sha256'] for i in inputs[2] if i['kind'] == 'pbp'})
            metadata['sources'] = {sha: {'source_model_version': {'value': 'synthetic-model-' + str(i),
                'evidence': {'basis': 'SYNTHETIC_FIXTURE', 'reference': 'synthetic-model'}}}
                for i, sha in enumerate(sources) if not (variant == 'mixed-unknown' and i == 1)}
        write_artifact(root / 'artifact', calculate(*inputs, metadata, seasons=(2026,)))
        plan = prepare(root / 'artifact', [calendar], pbps, root / 'unused')
    # Receipt roots are inert literal synthetic identities, no locator dependency.
    archive_root = '/synthetic/nfl-e5c2/archive'
    buffers = {sha: data for sha, (data, _) in plan.source_bytes.items()}
    buffers.update({plan.file_hashes[n]: data for n, data in plan.artifact_bytes.items()})
    receipts = {}
    for sha in sorted(buffers):
        receipt = {'receiptVersion': 1, 'archive_id': ARCHIVE_ID, 'archive_root': archive_root,
            'sha256': sha, 'locator': 'blobs/' + sha[:2] + '/' + sha,
            'observed_at': DERIVED, 'origin': {'type': 'SYNTHETIC_FIXTURE', 'reference': 'e5c2-finite-fixture'}}
        from nfl_sideline_etl.metrics_persistence.archive import Archive
        receipt['locator'] = Archive.locator(sha)
        receipt['receipt_id'] = identity(receipt)
        receipts[sha] = receipt
    rel = records(plan)
    for receipt in receipts.values():
        rel['metric_archive_receipt'].append({**{k: receipt[k] for k in
            ('receipt_id', 'sha256', 'archive_id', 'archive_root', 'locator', 'observed_at')}, 'receipt_json': receipt})
    for table in ('metric_archive_blob', 'metric_calculation', 'metric_archive_receipt'):
        for r in rel[table]:
            r['persisted_at'] = DERIVED
    package = {'relationsVersion': 'metrics-relations-v1', 'selection': [{
        'calculation_id': plan.result['manifest.json']['calculation_id'],
        'artifact_id': plan.artifact_id, 'archive_id': ARCHIVE_ID}], 'relations': rel}
    recovered = {ARCHIVE_ID: {'archive_id': ARCHIVE_ID, 'archive_root': archive_root,
        'blobs': {sha: base64.b64encode(data).decode('ascii') for sha, data in buffers.items()}, 'receipts': receipts}}
    # Reuse accepted synthetic auxiliary construction, then explicitly close weeks.
    import importlib.util
    helper = Path(__file__).resolve().parents[1] / 'e5b-4/build_fixture.py'
    spec = importlib.util.spec_from_file_location('e5c2_accepted_fixture', helper)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    aux = module.auxiliary([plan])
    meta = aux['resources'][0]['revision_id']
    for cal in (r for r in aux['resources'] if r['kind'] == 'CALENDAR'):
        for week in (1, 2, 3):
            e = {'kind': 'PERIOD_CLOSED', 'subject_id': cal['revision_id'], 'origin': 'synthetic-e5b4',
                 'reference': 'SYNTHETIC_FIXTURE', 'recorded_at': DERIVED, 'value': week, 'dependencies': [meta]}
            e['evidence_id'] = identity(e); aux['evidence'].append(e)
            cal['payload']['closed_weeks'].append({'week': week, 'evidence_id': e['evidence_id']})
    for binding in aux['bindings']:
        for sid in binding['source_models']:
            model_value = plan.result['manifest.json']['source_model_versions'][sid[7:]]['value']
            if model_value == 'UNKNOWN':
                continue
            e = {'kind': 'METADATA', 'subject_id': sid, 'origin': 'synthetic-e5b4',
                'reference': 'SYNTHETIC_FIXTURE', 'recorded_at': DERIVED,
                'value': model_value, 'dependencies': [meta]}
            e['evidence_id'] = identity(e); aux['evidence'].append(e)
            binding['source_models'][sid] = {'value': model_value, 'evidence_id': e['evidence_id']}
    return materialize(package, recovered, aux, DERIVED)


def nominal(t, l, weeks=(1, 2, 3), teams=('AAA',), foundations=('general', 'classified_pass', 'classified_rush')):
    cal = next(r for r in t['resources'] if r['kind'] == 'CALENDAR')
    choice = l['relations']['selection'][0]
    assocs = []
    for row in l['relations']['relations']['metric_calculation_coverage']:
        if row['calculation_id'] != choice['calculation_id']:
            continue
        game = next(g for g in cal['payload']['games'] if g['game_id'] == row['game_id'])
        if game['week'] not in weeks or not set(teams) & {game['home_team'], game['away_team']}:
            continue
        c = next((c for c in t['calculations'] if c['coverage_revision_id'] == row['coverage_revision_id'] and c['calculation_id'] == row['calculation_id']), None)
        assocs.append({'gameId': row['game_id'], 'calculationId': row['calculation_id'],
            'coverageRevisionId': row['coverage_revision_id'], 'artifactId': choice['artifact_id'],
            'archiveId': choice['archive_id'], 'temporalRevisionId': c['revision_id'] if c else None})
    return {'requestVersion': REQUEST_VERSION, 'source': {'materializationId': l['materialization_id'],
        'temporalInputId': l['temporalInputId']}, 'derivedAt': DERIVED,
        'presentation': {'epaDecimals': 3, 'ratePercentDecimals': 1, 'rounding': 'HALF_UP'},
        'requests': [{'season': 2026, 'phase': 'REG', 'weeks': list(weeks), 'origin': 'CURRENT',
            'teams': list(teams), 'roles': ['off', 'def'], 'foundations': list(foundations),
            'calendarRevisionId': cal['revision_id'], 'calendarSourceSetId': cal['dependencies'][0], 'associations': assocs}]}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    t, l = source_fixture()
    publish(args.output, t, l)
    (args.output.parent / (args.output.name + '-request.json')).write_bytes(json_bytes(nominal(t, l)))
