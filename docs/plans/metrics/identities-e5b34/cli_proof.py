"""Real CLI parity/read-only proof after additional unselected batches exist."""
import argparse
from pathlib import Path
import json
import subprocess
import sys
from fixture_support import fixture
from nfl_sideline_etl.metrics_persistence.connection import configuration
import importlib.util
_spec=importlib.util.spec_from_file_location('identity_database_proof',Path(__file__).with_name('database_proof.py'))
_proof=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_proof)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--instance-root',type=Path,required=True);p.add_argument('--proof-workspace',type=Path,required=True)
    p.add_argument('--output-root',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--java',type=Path,required=True);a=p.parse_args()
    if a.output_root.exists() or a.report.exists():p.error('New destinations required')
    if not str(a.instance_root.resolve()).startswith('/private/tmp/nfl-e5b4-instance-'):p.error('Own disposable root required')
    config=configuration(a.instance_root/'writer.json');before=_proof.snapshot(config)
    flow=a.proof_workspace/'original-flow'
    roots=fixture.load_json((flow/'archives.json').read_bytes())
    before_archive={k:_proof.blobs(Path(v)) for k,v in roots.items()}
    base=[sys.executable,'-B','-m','nfl_sideline_etl.metrics_materialization']
    q=fixture.load_json((flow/'request-pit.json').read_bytes())
    materialized=a.output_root/'materialized';selected=a.output_root/'reconstruction'
    subprocess.run(base+['postgres','--config',str(a.instance_root/'writer.json'),'--selection',str(flow/'selection.json'),
        '--archives',str(flow/'archives.json'),'--auxiliary',str(flow/'auxiliary.json'),'--derived-at',q['derivedAt'],'--output',str(materialized)],check=True,capture_output=True,text=True)
    subprocess.run(base+['select','--materialized',str(materialized),'--request',str(flow/'request-reconstruction.json'),'--output',str(selected)],check=True,capture_output=True,text=True)
    hashes={}
    from nfl_sideline_etl.metrics_persistence.archive import digest
    for name,original in [('materialized',flow/'materialized'),('reconstruction',flow/'reconstruction')]:
        for path in original.iterdir():
            candidate=a.output_root/name/path.name
            assert candidate.read_bytes()==path.read_bytes();hashes[name+'/'+path.name]=digest(candidate.read_bytes())
    java=subprocess.run([str(a.java),'-jar',str(fixture.ROOT/'core-api/target/core-api-0.1.0.jar'),'metrics-temporal-read','--artifact',str(selected)],capture_output=True,text=True,check=True)
    assert 'EPA=-1/3 volume=3' in java.stdout
    after=_proof.snapshot(config);after_archive={k:_proof.blobs(Path(v)) for k,v in roots.items()}
    assert before==after and before_archive==after_archive
    report={'scope':'REAL_POSTGRESQL_CLI_PARITY','instance_id':config['instance_id'],'byteParity':hashes,
        'allRowsIncludingPersistedAtUnchanged':True,'archiveBlobsReceiptsMarkerUnchanged':True,
        'unselectedCalculationsPresent':len(before['metric_calculation'])-1,'java':java.stdout.strip()}
    with a.report.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'cliParity':'PASS','readOnly':True,'java':'PASS'}))


if __name__=='__main__':main()
