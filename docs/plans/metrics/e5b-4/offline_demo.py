"""Create fresh offline fixture archives/documents and demonstrate the supported bridge.

No database driver, SQL, acquisition or network. Relation rows are explicitly
synthetic in this harness; use database_proof.py for real PostgreSQL evidence.
"""
import argparse
from pathlib import Path

from build_fixture import build, merge, auxiliary, FIXTURE
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.recovery import recover
from nfl_sideline_etl.metrics_materialization.publication import publish
from nfl_sideline_etl.offline_metrics.artifact import json_bytes
from nfl_sideline_etl.offline_metrics.inputs import load_json
from nfl_sideline_etl.temporal_metrics.core import select
from nfl_sideline_etl.temporal_metrics.__main__ import publish as publish_result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True);args=parser.parse_args()
    root=args.workspace.resolve();root.mkdir(exist_ok=False)
    p1,b1,plan1,ar=build(root/'content')
    p2,b2,plan2,_=build(root/'empty',empty=True,archive=ar)
    package=merge([p1,p2]);aux=auxiliary([plan1,plan2]);archives={ar.archive_id:str(ar.root)}
    t,l=materialize(package,recover(package,archives),aux,'2026-10-11T12:00:00.000000000001Z')
    publish(root/'materialized',t,l)
    q=load_json((FIXTURE/'request-pit.json').read_bytes());publish_result(root/'pit',select(t,q))
    # Explicit fixture-only nominal choices; no materializer/selector default uses this helper.
    retro={**q,'mode':'EVENT_RECONSTRUCTION','retrospective':{'calendars':{},'states':{},'calculations':{}}}
    for r in t['resources']:
        if r['kind']=='CALENDAR':retro['retrospective']['calendars'][str(r['payload']['season'])+'/'+r['payload']['phase']]=r['revision_id']
        if r['kind']=='STATE':
            key=r['payload']['calendar_revision_id']+'/'+r['payload']['game_id']
            retro['retrospective']['states'][key]=r['revision_id'];retro['retrospective']['calculations'][key]=None
    for c in t['calculations']:retro['retrospective']['calculations'][c['calendar_revision_id']+'/'+c['game']['game_id']]=c['revision_id']
    publish_result(root/'reconstruction',select(t,retro))
    for name,document in [('relations',package),('auxiliary',aux),('archives',archives),('request-pit',q),('request-reconstruction',retro)]:
        (root/(name+'.json')).write_bytes(json_bytes(document))
    print(l['materialization_id'])


if __name__=='__main__':main()
