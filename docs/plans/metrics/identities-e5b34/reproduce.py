"""Current success counterpart of preserved historical E5b-4 contract-gap.json."""
import argparse
import json
from pathlib import Path
import tempfile
from fixture_support import fixture
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.publication import publish
from nfl_sideline_etl.temporal_metrics.core import select
from nfl_sideline_etl.temporal_metrics.__main__ import publish as publish_result
import importlib.util
_spec=importlib.util.spec_from_file_location('identity_proof',Path(__file__).with_name('database_proof.py'))
_proof=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_proof)
retrospective=_proof.retrospective


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.artifacts.exists():parser.error('New destinations required')
    with tempfile.TemporaryDirectory(prefix='nfl-e5b34-reproduction-') as tmp:
        p,b,plan,ar=fixture.build(Path(tmp)/'batch',multi=True)
        q=fixture.load_json((fixture.FIXTURE/'request-pit.json').read_bytes())
        t,l=materialize(p,b,fixture.auxiliary([plan]),q['derivedAt'])
        publish(args.artifacts/'materialized',t,l)
        pit=select(t,q);rq=retrospective(t,q);result=select(t,rq)
        publish_result(args.artifacts/'pit',pit);publish_result(args.artifacts/'reconstruction',result)
        historic=fixture.load_json((fixture.ROOT/'docs/plans/metrics/e5b-4/contract-gap.json').read_bytes())
        report={'before':historic,'after':{'status':'PASSED','calculation_id':plan.result['manifest.json']['calculation_id'],
            'associations':p['relations']['metric_calculation_coverage'],
            'observedGames':sorted(c['game']['game_id'] for c in t['calculations']),
            'coverage':result['blocks'][0]['coverage'],'algorithmVersion':result['algorithmVersion'],
            'resultVersion':result['resultVersion'],'materialization_id':l['materialization_id'],
            'input_id':result['input_id'],'result_id':result['result_id'],'audit_id':result['audit_id']}}
        assert report['after']['observedGames']==['synthetic-1','synthetic-6']
        assert len(report['after']['associations'])==4
        with args.output.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps({'status':'PASSED','originalCalculationId':report['after']['calculation_id']}))


if __name__=='__main__':main()
