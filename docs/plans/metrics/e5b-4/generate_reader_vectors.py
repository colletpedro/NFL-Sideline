"""Synthetic reader-only exact zero/mixed-model vector, independent of database proof.

Sums are synthetic declarations, not adapter-derived from these opaque temporal
fixture bytes. The real integration proof is database_proof.py, kept separate.
"""
import argparse
from copy import deepcopy
from pathlib import Path

from nfl_sideline_etl.offline_metrics.inputs import load_json
from nfl_sideline_etl.offline_metrics.artifact import identity
from nfl_sideline_etl.temporal_metrics.core import select
from nfl_sideline_etl.temporal_metrics.__main__ import publish

ROOT=Path(__file__).resolve().parents[4]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    fixtures=ROOT/'etl-pipeline/tests/fixtures/temporal_metrics'
    p=load_json((fixtures/'package.json').read_bytes())
    for c in p['calculations']:
        for row in c['statistics']:
            if row['epa_n']:row['epa_sum']='0'
            row['success_n']=0
        if c['game']['game_id']=='beta':
            for env in [c['model'],*c['source_models'].values()]:
                original=next(e for e in p['evidence'] if e['evidence_id']==env['evidence_id'])
                e=deepcopy(original);e['value']='model-v2';e['evidence_id']=identity(e)
                if e not in p['evidence']:p['evidence'].append(e)
                env.update(value='model-v2',evidence_id=e['evidence_id'])
    request=load_json((fixtures/'request-reconstruction.json').read_bytes())
    request['derivedAt']='2026-10-11T12:00:00.12345678901234567890123456789Z'
    request['retrospective']=load_json((fixtures/'retrospective.json').read_bytes())
    result=select(p,request)
    assert {a['model'] for b in result['blocks'] for a in b['aggregates']}=={'model-v1','model-v2'}
    assert all(a['epa']['exact']=='0' for b in result['blocks'] for a in b['aggregates'] if a['sums']['epa_n'])
    publish(args.output,result)
    print(result['result_id'])


if __name__=='__main__':main()
