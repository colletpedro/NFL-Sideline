#!/usr/bin/env python3
"""Build an internal inspection page from a successful real HTTP validation run."""
import argparse
from pathlib import Path
import evaluate_coverage as evaluation


def build(run, output):
    run = evaluation.safe_directory(run)
    output = evaluation.safe_directory(output)
    verification = evaluation.read(run / 'verification.json')
    if verification.get('status') != 'PASSED' or verification.get('transport') != 'REAL_LOOPBACK_HTTP':
        raise ValueError('A successful real HTTP run is required')
    base = evaluation.ROOT / 'editorial/coverage-clarity-v1'
    manifest = evaluation.read(base / 'manifest.json')
    checked = {c['gameId'] for c in verification['cases']}
    if checked != {c['gameId'] for c in manifest['cases']}:
        raise ValueError('Run does not cover the known manifest')
    cli = run / 'cli'
    records = [{'gameId': c['gameId'], 'cohort': c['cohort'], 'knownSix': c['knownSix'],
                'status': 'VALIDATED', 'exitCode': 0, 'failureCategory': []} for c in manifest['cases']]
    journal = {'results': records, 'independentEvaluation': False, 'operationalValidation': True}
    if (cli / 'execution.json').exists():
        if evaluation.read(cli / 'execution.json') != journal:
            raise ValueError('Existing journal differs; refusing overwrite')
    else:
        evaluation.write(cli / 'execution.json', journal)
    output.mkdir()
    evaluation.metrics(base, cli, output / 'metrics.json')
    evaluation.build_html(base, output / 'metrics.json', output / 'inspection.html')
    print(output / 'inspection.html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build(args.run, args.output)
