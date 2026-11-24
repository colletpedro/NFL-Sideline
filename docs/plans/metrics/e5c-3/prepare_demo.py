"""Explicit synthetic test preparation, never invoked by Vite/browser access.

Does not restore missing real provenance. Real entry remains ERROR when absent.
"""
import argparse
import base64
import importlib.util
from pathlib import Path
import tempfile
from copy import deepcopy

from nfl_sideline_etl.offline_metrics.artifact import identity, json_bytes, calculate, write_artifact
from nfl_sideline_etl.offline_metrics.inputs import read_inputs, load_json
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.relations import records
from nfl_sideline_etl.metrics_persistence.plan import prepare
from nfl_sideline_etl.metrics_persistence.archive import Archive
from nfl_sideline_etl.metrics_observations.publication import publish

ROOT = Path(__file__).resolve().parents[4]

def helpers():
    spec = importlib.util.spec_from_file_location('accepted_e5c2_fixture', ROOT / 'docs/plans/metrics/e5c-2/build_fixture.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def historical(m):
    """Fresh SYNTHETIC POST source via accepted adapter, not an edited DTO."""
    t, l = m.source_fixture()
    manifest = t['calculations'][0]['original']['manifest']
    archive = next(iter(l['recoveredArchives'].values()))
    with tempfile.TemporaryDirectory(prefix='nfl-e5c3-history-') as tmp:
        root = Path(tmp); paths = {'calendar': [], 'pbp': []}
        for i, source in enumerate(manifest['inputs']):
            doc = load_json(base64.b64decode(archive['blobs'][source['sha256']]))
            for row in doc['rows']:
                row['season'] = 2025
                row['game_type' if source['kind'] == 'calendar' else 'season_type'] = 'POST'
            path = root / f'{i}.json'; path.write_bytes(json_bytes(doc)); paths[source['kind']].append(path)
        inputs = read_inputs(paths['calendar'], paths['pbp'])
        metadata = deepcopy(manifest['metadata'])
        for kind in ('calendar', 'pbp'):
            metadata[kind + '_sha256'] = sorted({d['sha256'] for d in inputs[2] if d['kind'] == kind})
        write_artifact(root / 'artifact', calculate(*inputs, metadata, seasons=(2025,)))
        plan = prepare(root / 'artifact', paths['calendar'], paths['pbp'], root / 'unused')
    rel = records(plan)
    buffers = {sha: data for sha, (data, _) in plan.source_bytes.items()}
    buffers.update({plan.file_hashes[n]: data for n, data in plan.artifact_bytes.items()})
    receipts = {}
    aid = m.ARCHIVE_ID; ar_root = '/synthetic/nfl-e5c3/history'
    for sha in buffers:
        receipt = {'receiptVersion': 1, 'archive_id': aid, 'archive_root': ar_root, 'sha256': sha,
            'locator': Archive.locator(sha), 'observed_at': m.DERIVED, 'origin': {'type': 'SYNTHETIC_FIXTURE', 'reference': 'e5c3-history'}}
        receipt['receipt_id'] = identity(receipt); receipts[sha] = receipt
        rel['metric_archive_receipt'].append({**{k: receipt[k] for k in ('receipt_id','sha256','archive_id','archive_root','locator','observed_at')},'receipt_json':receipt})
    for table in ('metric_archive_blob', 'metric_calculation', 'metric_archive_receipt'):
        for r in rel[table]: r['persisted_at'] = m.DERIVED
    package = {'relationsVersion':'metrics-relations-v1','selection':[{'calculation_id':manifest['calculation_id'],'artifact_id':plan.artifact_id,'archive_id':aid}],'relations':rel}
    package['selection'][0]['calculation_id'] = plan.result['manifest.json']['calculation_id']
    recovered = {aid:{'archive_id':aid,'archive_root':ar_root,'blobs':{sha:base64.b64encode(raw).decode() for sha,raw in buffers.items()},'receipts':receipts}}
    aux = load_json((ROOT / 'etl-pipeline/tests/fixtures/metrics_materialization/auxiliary-empty.json').read_bytes())
    return materialize(package,recovered,aux,m.DERIVED)


def build(root, real_path):
    if root.exists(): raise FileExistsError('New preparation root required')
    root.mkdir(parents=True)
    m = helpers(); entries = []
    for name, variant in [('synthetic','default'),('zero','zero'),('no-epa','no-epa'),('history','history'),('absent','empty-file')]:
        t,l = historical(m) if variant == 'history' else m.source_fixture(variant=variant)
        q = m.nominal(t,l)
        q['requests'] = [m.nominal(t,l,weeks=weeks)['requests'][0] for weeks in [(1,), (2,), (3,), (1,2,3)]]
        if variant == 'history':
            for r in q['requests']: r.update(season=2025,phase='POST',origin='HISTORICAL_REFERENCE')
        bundle = root / name; manifest = publish(bundle,t,l,q)
        entries.append({'entryId':name,'label':{'synthetic':'Demonstração de estados','zero':'Zero conhecido','no-epa':'Volume sem EPA','history':'Referência histórica sintética','absent':'Fontes ausentes sintéticas'}[name],
            'dataKind':'SYNTHETIC','path':str(bundle),'expectedBundleId':manifest['bundleId']})
    entries.insert(0, {'entryId':'real-archive','label':'Arquivo aceito BAL e DAL 2026 e NE POST2025','dataKind':'REAL_ARCHIVE','path':str(real_path),
        'expectedBundleId':'sha256:8016e8dd854a3c400f05758fca61f1a13011a7e93e5169694255c87ac2bce46e'})
    config = {'configVersion':'metrics-lab-config-v1','bundles':entries}
    (root/'config.json').write_bytes(json_bytes(config))
    return config

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--real-bundle',type=Path,default=Path('/private/tmp/nfl-e5c2-orchestrator-real-20261015/copied'))
    a=p.parse_args();build(a.output.absolute(),a.real_bundle.absolute());print(a.output.absolute()/'config.json')
