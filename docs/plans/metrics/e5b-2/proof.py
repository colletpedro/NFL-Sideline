"""Reproducible selected evidence in an already provisioned EMPTY E5b-2 instance.

Does not prepare domain, reset tables or read .env. Failures preserve CAS files.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from nfl_sideline_etl.offline_metrics.artifact import calculate, write_artifact
from nfl_sideline_etl.offline_metrics.inputs import read_inputs
from nfl_sideline_etl.metrics_persistence.archive import Archive
from nfl_sideline_etl.metrics_persistence.connection import configuration, connect
from nfl_sideline_etl.metrics_persistence.plan import prepare
from nfl_sideline_etl.metrics_persistence.writer import persist, TABLES

REPO = Path(__file__).resolve().parents[4]
FIXTURE = REPO / 'etl-pipeline/tests/fixtures/offline_metrics'
ORIGINAL = REPO / 'docs/plans/metrics/e5b-1/synthetic-result'


def query(config, statement, params=()):
    conn=connect(config)
    try:
        with conn.cursor() as cur:
            cur.execute(statement,params)
            return cur.fetchall()
    finally:conn.close()


def counts(config):
    return {t:query(config,f'select count(*) from metrics_private.{t}')[0][0] for t in TABLES}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance-root',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.workspace.exists() or args.output.exists():parser.error('Use new workspace/output; never overwrite evidence')
    config=configuration(args.instance_root/'writer.json')
    if any(counts(config).values()):parser.error('Instance must be empty; this command never resets it')
    args.workspace.mkdir(parents=True)
    archive_path=args.workspace/'archive'
    original=prepare(ORIGINAL,[FIXTURE/'calendar.json'],[FIXTURE/'pbp.json'],archive_path)
    first=persist(original,archive_path,config)
    first_counts=counts(config)
    receipts=query(config,'select receipt_id,observed_at,persisted_at from metrics_private.metric_archive_receipt order by receipt_id')
    repeat=persist(original,archive_path,config)
    assert repeat['inserted']==0 and counts(config)==first_counts
    assert receipts==query(config,'select receipt_id,observed_at,persisted_at from metrics_private.metric_archive_receipt order by receipt_id')
    original_sums=query(config,'select record_json from metrics_private.team_game_metric_sums')
    original_files=query(config,'select filename,sha256 from metrics_private.metric_artifact_file')
    assert {name:Archive(archive_path).read(sha) for name,sha in original_files}==original.artifact_bytes

    def revised(name,epa=None,model=False):
        document=json.loads((FIXTURE/'pbp.json').read_text())
        if epa is not None:document['rows'][0]['epa']=epa
        source=args.workspace/(name+'.json')
        source.write_text(json.dumps(document))
        inputs=read_inputs([FIXTURE/'calendar.json'],[source])
        metadata=json.loads((FIXTURE/'metadata.json').read_text())
        sha=inputs[2][1]['sha256']
        metadata['pbp_sha256']=[sha]
        if model:
            metadata['sources']={sha:{'source_model_version':{'value':'synthetic-model-2',
                'evidence':{'basis':'SYNTHETIC_DECLARATION','reference':'proof.py'}}}}
        result=calculate(*inputs,metadata,seasons=(2026,))
        artifact=args.workspace/(name+'-artifact')
        write_artifact(artifact,result)
        return prepare(artifact,[FIXTURE/'calendar.json'],[source],archive_path)

    correction=revised('correction',epa='-123.12345678901234567890123456789012345')
    corrected=persist(correction,archive_path,config)
    assert all(s in query(config,'select record_json from metrics_private.team_game_metric_sums') for s in original_sums)
    model=revised('model',epa='-123.12345678901234567890123456789012345',model=True)
    assert correction.result['game-audit.json']==model.result['game-audit.json']
    before_model=counts(config)
    model_report=persist(model,archive_path,config)
    assert counts(config)['team_game_metric_sums']==before_model['team_game_metric_sums']
    failed=revised('recover',epa='-124.000000000000000000000000000000000001')
    before_failure=counts(config)
    def fail(stage):
        if stage=='after_sources':raise RuntimeError('Injected after initial SQL inserts')
    try:persist(failed,archive_path,config,_checkpoint=fail)
    except RuntimeError:pass
    else:raise AssertionError('Injected rollback did not happen')
    assert counts(config)==before_failure
    orphan_receipts={p.name:p.read_bytes() for p in (archive_path/'receipts').glob('*.json')}
    recovered=persist(failed,archive_path,config)
    assert orphan_receipts=={p.name:p.read_bytes() for p in (archive_path/'receipts').glob('*.json')}
    states=query(config,'select completeness,scope,statistics_status,count(*) from metrics_private.game_metric_coverage_revision group by 1,2,3 order by 1,2,3')
    access={role:{t:query(config,"select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')",
              (role,'metrics_private.'+t))[0][0] for t in TABLES} for role in ('anon','authenticated','service_role')}
    assert not any(any(v.values()) for v in access.values())
    hashes=json.loads((REPO/'contracts/metrics/e5a-v1/verification.json').read_text())['packageContentSha256']
    assert all(hashlib.sha256((REPO/'contracts/metrics/e5a-v1'/name).read_bytes()).hexdigest()==sha for name,sha in hashes.items())
    report={'base':'882c9013ec1a1cd08f2d0b7049fb74ff1cdb8491',
        'instance':{k:config[k] for k in ('host','port','database','instance_id')},
        'server':query(config,'show server_version')[0][0], 'python':sys.version.split()[0],
        'first':first,'firstCounts':first_counts,'repeat':repeat,
        'correction':corrected,'modelEvidenceRevision':model_report,
        'rollbackAfterSources':True,'rollbackRowCountsUnchanged':True,
        'recovery':recovered,'receiptsPreservedOnRecovery':True,
        'firstReceiptsPreservedOnRepeat':True,'exactOriginalArtifactRecovery':True,
        'oldStatisticsPreserved':True,'modelRevisionReusesCoverage':True,
        'originalCalculationId':original.result['manifest.json']['calculation_id'],
        'correctionCalculationId':correction.result['manifest.json']['calculation_id'],
        'modelCalculationId':model.result['manifest.json']['calculation_id'],
        'finalCounts':counts(config),'coverageStates':states,'publicAccess':access,
        'frozenE5aHashesChecked':len(hashes), 'archiveRoot':str(archive_path.resolve()),
        'historicalPointInTimeCertified':False}
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'result':'PASS','firstInserted':first['inserted'], 'repeatInserted':repeat['inserted'],
                      'rollback':True,'report':str(args.output)},sort_keys=True))


if __name__=='__main__':main()
