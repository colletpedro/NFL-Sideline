"""Optional read-only audit of existing sources, never a required checkout test.

Run with PYTHONPATH=etl-pipeline/src and the installed ETL Python runtime.
The destination is new, internal, and atomically published by the adapter writer.
"""
import argparse
import json
from pathlib import Path

from nfl_sideline_etl.offline_metrics.artifact import calculate, identity, write_artifact
from nfl_sideline_etl.offline_metrics.inputs import read_inputs

REPO = Path(__file__).resolve().parents[4]
EXPECTED_CONVERSIONS = {2023: 126, 2025: 130, 2026: 5}
EXPECTED_NULL_TEAMS = {2023: 2638, 2025: 2729, 2026: 297}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    previous = json.loads((REPO/'contracts/metrics/e5a-v1/local-audit.json').read_text())
    records = []
    for season in (2023, 2025, 2026):
        paths = {kind: args.source_root/directory/f'season={season}'/f'{directory}.parquet'
                 for kind,directory in [('calendar','schedules'),('pbp','pbp')]}
        if not all(p.is_file() for p in paths.values()):
            records.append({'season':season,'status':'LOCAL_INPUT_ABSENT',
                            'missing_kinds':[k for k,p in paths.items() if not p.is_file()]})
            continue
        calendars, plays, inputs = read_inputs([paths['calendar']],[paths['pbp']])
        result = calculate(calendars,plays,inputs,seasons=(season,))
        rec = result['reconciliation.json']
        comparison = {}
        for descriptor in inputs:
            old = next(i for i in previous['files'] if i['season']==season and i['kind']==('schedules' if descriptor['kind']=='calendar' else 'pbp'))
            comparison[descriptor['kind']]={'sha256':descriptor['sha256'],'previous_sha256':old['sha256'],
                'exact_previous_bytes':descriptor['sha256']==old['sha256'],
                'bytes':descriptor['bytes'],'relevant_schema':descriptor['relevant_schema']}
        same = all(i['exact_previous_bytes'] for i in comparison.values())
        conversions = rec['exclusions'].get('two_point_conversion',0)
        outside_null = rec['outside_pass_run_null_teams_n']
        checks = {'conversion_count':conversions==EXPECTED_CONVERSIONS[season],
                  'outside_null_teams_count':outside_null==EXPECTED_NULL_TEAMS[season]}
        if same and not all(checks.values()):
            raise ValueError(f'Prior bytes have a reconciliation discrepancy: {season}, {checks}')
        # Count each eligible play only once, using one off/general record per team.
        off = [s for s in result['statistics.json'] if s['role']=='off' and s['foundation']=='general']
        assert sum(s['eligible_n'] for s in off)==rec['eligible_content_n']
        records.append({'season':season,'status':'AUDITED_PRESENT_CONTENT','inputs':comparison,
            'exact_previous_hashes':same,'matches_previous_counts':checks if same else None,
            'hash_change_limitation':None if same else 'Prior counts are not acceptance targets for changed bytes.',
            'calculation_id':result['manifest.json']['calculation_id'],
            'reconciliation':rec,'statistics_records_n':len(result['statistics.json']),
            'off_general_epa_n':sum(s['epa_n'] for s in off),
            'completeness_states':sorted({a['completeness'] for a in result['game-audit.json']}),
            'scope_states':sorted({s['scope'] for s in result['statistics.json']}),
            'epa_model_version':'UNKNOWN','available_at':None,'event_upper_bound':None})
    summary={'artifactVersion':'metrics-offline-v1','optional':True,'acquired':False,
             'inputs_copied':False,'records':records}
    summary['calculation_id']=identity(summary)
    write_artifact(args.output,{'manifest.json':summary})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
