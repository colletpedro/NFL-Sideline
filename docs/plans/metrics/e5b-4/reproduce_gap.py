"""Minimal fresh-archive reproduction: accepted batch identity versus temporal validation."""
import argparse
import json
from pathlib import Path
import tempfile

from build_fixture import build, auxiliary
from nfl_sideline_etl.metrics_materialization.core import materialize, ContractGap


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nfl-e5b4-gap-') as tmp:
        p,b,plan,ar=build(Path(tmp)/'fixture',multi=True)
        try:materialize(p,b,auxiliary([plan]),'2026-10-11T12:00:00Z')
        except ContractGap as error:
            report={'base':'8f583c4ec9ed83f86c2229b0f1656d32403bcc31',
                'acceptedAlgorithm':'metrics-temporal-1.0.1','result':'BLOCKED_BY_ACCEPTED_CONTRACT',
                'calculation_id':plan.result['manifest.json']['calculation_id'],
                'artifact_id':plan.artifact_id,
                'observedGameIds':sorted({s['game_id'] for s in plan.result['statistics.json']}),
                'associations':p['relations']['metric_calculation_coverage'],
                'failure':str(error),'acceptedValidatorFailure':str(error.__cause__),
                'outputPublished':False,'priorContractsModified':False,
                'proposal':'Validate calculation_id as a batch manifest identity; compare the per-game projection by (calculation_id, coverage_revision_id), preserving both original IDs. Review/version the accepted temporal validator separately.'}
        else:raise AssertionError('Expected the batch identity conflict')
    with args.output.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
    print(report['result'])


if __name__=='__main__':main()
