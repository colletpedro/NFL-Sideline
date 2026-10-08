"""Read-only E5a diagnostic; does not implement or modify the candidate adapter.

Default: stdlib-only synthetic counterexample. Optional: inspect existing Parquets
from an explicitly supplied source root, using already installed Polars.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PACKAGE = REPO / 'contracts/metrics/e5a-v1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('e5a_example_model', PACKAGE / 'verify.py')
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    case = next(c for c in json.loads((PACKAGE / 'fixtures/cases.json').read_text())['cases']
                if c['id'] == 'single_tiny_positive')
    row = copy.deepcopy(case['plays'][0])
    row.update(play_type=None, posteam=None, defteam=None, epa=None)
    outcomes = {}
    for label, record in [('outside_population_null_teams', row),
                          ('candidate_null_teams', {**row, 'play_type': 'pass'})]:
        try:
            model.normalized_plays([record])
            outcomes[label] = 'ACCEPTED'
        except ValueError as exc:
            outcomes[label] = str(exc)
    assert outcomes == {'outside_population_null_teams': 'Invalid play teams',
                        'candidate_null_teams': 'Invalid play teams'}, outcomes
    hashes = json.loads((PACKAGE / 'verification.json').read_text())['packageContentSha256']
    assert all(hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == digest
               for name, digest in hashes.items())
    output = {'diagnostic': 'E5A_RAW_PBP_BOUNDARY', 'candidateUnmodified': True,
              'candidateCommit': '5e976a315a167795222061175e582148bc570c33',
              'candidateHashesChecked': len(hashes), 'synthetic': outcomes,
              'goldenCasesPassed': model.verify_cases(), 'localFiles': []}
    if args.source_root:
        import polars as pl
        for season in (2023, 2025, 2026):
            path = args.source_root / 'pbp' / f'season={season}' / 'pbp.parquet'
            frame = pl.read_parquet(path, columns=model.CONTRACT['population']['requiredPlayFields'])
            classified = pl.col('play_type').is_in(['pass', 'run']).fill_null(False)
            missing_team = pl.col('posteam').is_null() | pl.col('defteam').is_null()
            output['localFiles'].append({
                'season': season, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'rawRows': frame.height, 'outsideRows': frame.filter(~classified).height,
                'outsideNullTeams': frame.filter(~classified & missing_team).height,
                'candidateNullTeams': frame.filter(classified & missing_team).height,
                'completenessCertified': False, 'historicalAvailabilityCertified': False})
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
