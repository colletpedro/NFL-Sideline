"""Independent finite mutations of an operational synthetic bundle."""
import argparse
import json
from pathlib import Path
import tempfile

from nfl_sideline_etl.metrics_observations.publication import generate, read, FILES
from nfl_sideline_etl.metrics_observations.core import semantic_id
from nfl_sideline_etl.metrics_persistence.archive import digest
from nfl_sideline_etl.offline_metrics.artifact import identity, json_bytes


def run(real_observations, output):
    root = Path.cwd()
    real = json.loads(real_observations.read_bytes())
    groups = {(m['coverageRevisionId'], d['subject']['team'], d['subject']['role'],
               d['subject']['foundation']) for d in real for m in d['members']
              if m['statistics'] is not None}
    source = root / 'etl-pipeline/tests/fixtures/metrics_observations/materialized'
    request = json.loads((source.parent / 'request.json').read_bytes())
    results = []
    with tempfile.TemporaryDirectory(prefix='nfl-e5c2-review-probes-', dir='/private/tmp') as tmp:
        for kind in ('invented_epa', 'invented_complete', 'invented_temporal'):
            out = Path(tmp) / kind
            generate(source, request, out)
            docs = json.loads((out / 'observations.json').read_bytes())
            manifest = json.loads((out / 'manifest.json').read_bytes())
            doc = next(x for x in docs if x['values']['epa'] is not None)
            old_id = doc['observationId']
            if kind == 'invented_epa':
                doc['values']['epa']['numerator'] = '777'
            elif kind == 'invented_complete':
                doc['guarantees']['completeness']['state'] = 'COMPLETE'
            else:
                doc['guarantees']['temporal']['state'] = 'KNOWN_AT_CUTOFF'
            new_id = semantic_id(doc)
            doc['observationId'] = new_id
            docs.sort(key=lambda x: x['observationId'])
            manifest['observationIds'] = sorted(x['observationId'] for x in docs)
            manifest['lineageByObservation'][new_id] = manifest['lineageByObservation'].pop(old_id)
            manifest['bundleId'] = identity({k: v for k, v in manifest.items() if k != 'bundleId'})
            (out / 'observations.json').write_bytes(json_bytes(docs))
            (out / 'manifest.json').write_bytes(json_bytes(manifest))
            marker = json.loads((out / 'COMPLETED.json').read_bytes())
            marker['bundleId'] = manifest['bundleId']
            marker['files'] = {name: digest((out / name).read_bytes()) for name in FILES}
            (out / 'COMPLETED.json').write_bytes(json_bytes(marker))
            try:
                read(out)
            except ValueError as error:
                assert 'derivation differs' in str(error)
                results.append({'case': kind, 'externallyRehashed': True,
                                'outcome': 'REFUSED', 'reason': str(error)})
            else:
                raise AssertionError('Adulteration accepted')
    report = {'realMemberGroupsCompared': sum(m['statistics'] is not None
                                              for d in real for m in d['members']),
              'uniqueCoverageTeamRoleFoundationGroups': len(groups),
              'counterexamples': results,
              'limits': 'No temporal selection, authority authentication or consumer implemented'}
    with output.open('xb') as handle:
        handle.write(json_bytes(report))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-observations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.real_observations, args.output)
