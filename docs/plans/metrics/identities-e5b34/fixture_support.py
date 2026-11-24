"""Fresh fixture preparation, never a SQL reader or production component."""
from copy import deepcopy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'e5b-4'))
import build_fixture as fixture
from nfl_sideline_etl.offline_metrics.artifact import calculate, write_artifact
from nfl_sideline_etl.offline_metrics.inputs import read_inputs, load_json
from nfl_sideline_etl.metrics_persistence.plan import prepare
from nfl_sideline_etl.metrics_materialization.relations import records

def model_batch(root, ar, model, *, second_game=False):
    root.mkdir()
    calendars=[fixture.FIXTURE/'calendar.json'];pbps=[fixture.FIXTURE/'pbp-a.json',fixture.FIXTURE/'pbp-b.json',fixture.FIXTURE/'pbp-a.json']
    if second_game:
        document=load_json((fixture.FIXTURE/'pbp-a.json').read_bytes())
        row=deepcopy(document['rows'][0]);row.update(game_id='synthetic-3',week=3)
        document['rows']=[row]
        from nfl_sideline_etl.offline_metrics.artifact import json_bytes
        extra=root/'second-game.json';extra.write_bytes(json_bytes(document));pbps.append(extra)
    inputs=read_inputs(calendars,pbps)
    metadata={'metadataVersion':1,'calendar_sha256':sorted({d['sha256'] for d in inputs[2] if d['kind']=='calendar'}),
        'pbp_sha256':sorted({d['sha256'] for d in inputs[2] if d['kind']=='pbp'}),
        'games':{'synthetic-6':{'completeness':'COMPLETE','expected_unique_rows':0,'evidence':{'basis':'SYNTHETIC_FIXTURE','reference':'fixture-ledger'}}},
        'sources':{d['sha256']:{'source_model_version':{'value':model,'evidence':{'basis':'DECLARED','reference':'explicit-model-document'}}} for d in inputs[2] if d['kind']=='pbp'}}
    write_artifact(root/'artifact',calculate(*inputs,metadata,seasons=(2026,)))
    plan=prepare(root/'artifact',calendars,pbps,ar.root)
    rows=records(plan)
    all_bytes={sha:(data,{'type':'explicit_source',**origin}) for sha,(data,origin) in plan.source_bytes.items()}
    all_bytes.update({plan.file_hashes[n]:(data,{'type':'artifact_file','filename':n,'artifact_id':plan.artifact_id}) for n,data in plan.artifact_bytes.items()})
    for sha,(data,origin) in sorted(all_bytes.items()):
        r=ar.put(data,sha,origin);rows['metric_archive_receipt'].append({**{k:r[k] for k in ('receipt_id','sha256','archive_id','archive_root','locator','observed_at')},'receipt_json':r})
    for table in ('metric_archive_blob','metric_calculation','metric_archive_receipt'):
        for r in rows[table]:r['persisted_at']='2026-10-11T12:00:00+00:00'
    p={'relationsVersion':'metrics-relations-v1','selection':[{'calculation_id':plan.result['manifest.json']['calculation_id'],'artifact_id':plan.artifact_id,'archive_id':ar.archive_id}], 'relations':rows}
    return p,plan
