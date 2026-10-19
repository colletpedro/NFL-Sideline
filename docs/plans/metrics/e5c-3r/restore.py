"""Restore a verified durable copy to a NEW destination; no DB, new receipts or writes to backup."""
import argparse
from pathlib import Path
import json
import shutil
from recover import hashes,save,now
from nfl_sideline_etl.metrics_observations.publication import read
from nfl_sideline_etl.metrics_materialization.publication import read as read_materialized


def restore(backup,destination,config,report):
    for p in (destination,config,report):
        if not p.is_absolute() or p.exists():raise ValueError('Absolute new destinations required')
        if 'web-ui' in p.parts:raise ValueError('Operational output must stay outside web-ui')
    if any(a==b or a.is_relative_to(b) or b.is_relative_to(a) for a,b in ((destination,config),(destination,report),(config,report))):
        raise ValueError('Output destinations must be disjoint')
    before=hashes(backup);declared=json.loads((backup/'SHA256SUMS.json').read_bytes())
    if declared!={k:v for k,v in before.items() if k!='SHA256SUMS.json'}:raise ValueError('Backup file manifest mismatch')
    read_materialized(backup/'materialized');docs,manifest=read(backup/'bundle')
    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(backup,destination)
    assert hashes(destination)==before
    read_materialized(destination/'materialized');copied,reread=read(destination/'bundle')
    assert copied==docs and reread==manifest and hashes(backup)==before
    operator=json.loads((backup/'lab-config.json').read_bytes())
    assert len(operator['bundles'])==1
    operator['bundles'][0].update(path=str(destination/'bundle'),expectedBundleId=manifest['bundleId'])
    config.parent.mkdir(parents=True,exist_ok=True);save(config,operator)
    save(report,dict(proof='RESTORE_FROM_DURABLE_BACKUP_NO_DATABASE',at=now(),backup=str(backup),destination=str(destination),
        config=str(config),bundleId=manifest['bundleId'],observations=len(docs),allFileHashesEqual=True,backupUnchanged=True,
        materializationAndBundlePublicReadersPassed=True,newReceipts=False,
        archiveRootRestriction='Raw copied archive receipts remain bound to their recorded original root; use the self-contained materialization/bundle at any safe physical path.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('backup','destination','config','report'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();restore(a.backup,a.destination,a.config,a.report)
