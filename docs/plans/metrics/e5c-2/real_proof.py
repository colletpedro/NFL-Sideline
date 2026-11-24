"""Read-only E5b-6 consumption proof. No harness/ETL/DB/acquisition or new receipts."""
import argparse
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil

from nfl_sideline_etl.offline_metrics.artifact import json_bytes
from nfl_sideline_etl.metrics_materialization.publication import read as source_read
from nfl_sideline_etl.metrics_observations import REQUEST_VERSION
from nfl_sideline_etl.metrics_observations.core import COUNT_MAP
from nfl_sideline_etl.metrics_observations.publication import generate, read

def hashes(root):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir()) if p.is_file()}


def proof(materialized, accepted_summary, workspace):
    if workspace.exists():
        raise FileExistsError('Proof workspace must be new')
    summary = json.loads(accepted_summary.read_bytes())
    marker = json.loads((materialized / 'COMPLETED.json').read_bytes())
    assert marker['materialization_id'] == summary['materialization']['materialization_id']
    assert marker['temporalInputId'] == summary['materialization']['input_id']
    full_report = Path(summary['fullLocalReport']['path'])
    if full_report.is_file():
        assert hashlib.sha256(full_report.read_bytes()).hexdigest() == summary['fullLocalReport']['sha256']
    # The supplied originals, not this summary, are the actual input.
    before = hashes(materialized)
    t, l = source_read(materialized)
    original_sources = {sid: resource['payload']['sha256'] for resource in t['resources']
                        if resource['kind'] == 'FILE' for sid in [resource['revision_id']]}
    expected_hashes = {row['sha256'] for row in summary['selectedSourceFiles']}
    if expected_hashes:
        assert expected_hashes == set(original_sources.values())
    workspace.mkdir(parents=True)
    calendars = {(r['payload']['season'], r['payload']['phase']): r for r in t['resources'] if r['kind'] == 'CALENDAR'}
    choices = {a['calculation_id']: a for a in l['relations']['selection']}
    # Concrete demonstration cohorts, independent of performance or any clock.
    specs = [(2026, 'REG', [1], ['BAL', 'DAL'], 'CURRENT'),
             (2026, 'REG', [2], ['BAL', 'DAL'], 'CURRENT'),
             (2026, 'REG', [1, 2], ['BAL', 'DAL'], 'CURRENT'),
             (2025, 'POST', sorted({g['week'] for g in calendars[2025, 'POST']['payload']['games']}), ['NE'], 'HISTORICAL_REFERENCE'),
             (2026, 'REG', [3], ['BAL'], 'CURRENT')]
    requests = []
    for season, phase, weeks, teams, origin in specs:
        cal = calendars[season, phase]
        associations = []
        for game in cal['payload']['games']:
            if game['week'] not in weeks or not set(teams) & {game['home_team'], game['away_team']}:
                continue
            rows = [row for row in l['relations']['relations']['metric_calculation_coverage'] if row['game_id'] == game['game_id']]
            assert len(rows) == 1, 'Demo requires explicit unique archived association'
            row = rows[0]; chosen = choices[row['calculation_id']]
            candidates = [c for c in t['calculations'] if c['game']['game_id'] == game['game_id'] and c['calculation_id'] == row['calculation_id']]
            assert len(candidates) <= 1
            associations.append({'gameId': game['game_id'], 'calculationId': row['calculation_id'],
                'coverageRevisionId': row['coverage_revision_id'], 'artifactId': chosen['artifact_id'],
                'archiveId': chosen['archive_id'], 'temporalRevisionId': candidates[0]['revision_id'] if candidates else None})
        requests.append({'season': season, 'phase': phase, 'weeks': weeks, 'origin': origin,
            'teams': teams, 'roles': ['off', 'def'], 'foundations': ['general', 'classified_pass', 'classified_rush'],
            'calendarSourceSetId': cal['dependencies'][0], 'calendarRevisionId': cal['revision_id'], 'associations': associations})
    q = {'requestVersion': REQUEST_VERSION, 'source': {'materializationId': l['materialization_id'], 'temporalInputId': l['temporalInputId']},
         'derivedAt': '2026-10-15T12:00:00Z', 'presentation': {'epaDecimals': 3, 'ratePercentDecimals': 1, 'rounding': 'HALF_UP'}, 'requests': requests}
    (workspace / 'request.json').write_bytes(json_bytes(q))
    print('Generating real closed bundle (accepted source chain reverified)...', flush=True)
    m = generate(materialized, q, workspace / 'bundle')
    print('Reading copied bundle independently of the old physical location...', flush=True)
    shutil.copytree(workspace / 'bundle', workspace / 'copied')
    shutil.rmtree(workspace / 'bundle')
    docs, reread = read(workspace / 'copied')
    assert m == reread
    by_revision = {c['revision_id']: c for c in t['calculations']}
    compared = 0
    for d in docs:
        mapping = m['lineageByObservation'][d['observationId']]['associations']
        rows = []
        for member in d['members']:
            choice = next(a for a in mapping if a['gameId'] == member['gameId'])
            if member['statistics'] is None:
                assert choice['temporalRevisionId'] is None
                continue
            c = by_revision[choice['temporalRevisionId']]
            row = next(s for s in c['statistics'] if (s['team'], s['role'], s['foundation']) == (d['subject']['team'], d['subject']['role'], d['subject']['foundation']))
            general = next(s for s in c['statistics'] if (s['team'], s['role'], s['foundation']) == (d['subject']['team'], d['subject']['role'], 'general'))
            for camel, snake in COUNT_MAP.items():
                assert member['statistics'][camel] == row[snake]
            assert member['statistics']['generalEligibleN'] == general['eligible_n']
            assert member['statistics']['epaSum'] == row['epa_sum']
            rows.append(row); compared += 1
        if rows:
            for camel, snake in COUNT_MAP.items():
                assert d['totals'][camel] == sum(s[snake] for s in rows)
            summed = sum((Fraction(Decimal(s['epa_sum'])) for s in rows if s['epa_n']), Fraction(0))
            if d['totals']['epaN']:
                assert Fraction(Decimal(d['values']['epa']['numerator'])) / d['values']['epa']['denominator'] == summed / sum(s['epa_n'] for s in rows)
            assert d['totals']['unknownFilterFlagsN'] == sum(by_revision[a['temporalRevisionId']]['unknown_filter_flags_n'] for a in mapping if a['temporalRevisionId'])
        assert d['guarantees']['temporal']['state'] == 'UNKNOWN'
        assert d['guarantees']['temporal']['targetGameId'] is None
        assert d['guarantees']['completeness']['state'] == 'UNKNOWN'
        assert d['guarantees']['compatibility']['epaModel']['state'] == 'UNKNOWN'
        assert d['guarantees']['coverage']['expectedCount'] is None
    assert before == hashes(materialized)
    marker_copy = json.loads((workspace / 'copied/COMPLETED.json').read_bytes())
    report = {'kind': 'REAL_LOCAL_E5B6_CONSUMPTION', 'source': q['source'], 'sourceFileHashes': before,
        'sourceFileRevisionHashes': original_sources, 'sourceUnchanged': True, 'bundleId': m['bundleId'],
        'bundleFiles': marker_copy['files'], 'cohorts': [{'season': s, 'phase': p, 'weeks': w, 'teams': team, 'origin': o} for s,p,w,team,o in specs],
        'observations': len(docs), 'memberGroupsReconciled': compared, 'copyReadPassed': True,
        'gapGameIds': sorted({member['gameId'] for d in docs for member in d['members'] if member['sourceState'] == 'ABSENT'}),
        'unknown': ['completeness', 'coverageExpectation', 'epaModel', 'historicalAvailability', 'historicalIngestion', 'eventFinal'],
        'comparison': 'NOT_IMPLEMENTED', 'pregame': 'NOT_DEMONSTRATED', 'operationalBundle': str(workspace / 'copied'),
        'versionedExtractIsSelfContained': False, 'originalSourceFilesRequiredForRealReproduction': True}
    (workspace / 'report.json').write_bytes(json_bytes(report))
    print(json.dumps({'observations': len(docs), 'memberGroupsReconciled': compared, 'bundleId': m['bundleId'], 'gaps': report['gapGameIds']}), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materialized', type=Path, required=True)
    parser.add_argument('--accepted-summary', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    a = parser.parse_args()
    proof(a.materialized, a.accepted_summary, a.workspace)
