"""Compact review inventories/identity table derived from preserved complete artifacts."""
import argparse
import json
from pathlib import Path
import shutil
from recover import ROOT,BASE,save,hashes,sha


def summarize(artifacts,out):
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    report=json.loads((artifacts/'recovery-report.json').read_bytes())
    old=json.loads((ROOT/'docs/plans/metrics/e5b-6-review/real-proof-summary.json').read_bytes())
    oldq=json.loads((ROOT/'docs/plans/metrics/e5c-2/real-request.json').read_bytes())
    newq=json.loads((artifacts/'request.json').read_bytes())
    identities=[]
    for s in ('2025','2026'):
        oldrow=old['firstAndRepeat']['first'][s];new=report['first'][s]
        for k in ('calculation_id','artifact_id','archive_id','attempt_id'):
            equal=oldrow[k]==new[k]
            assert equal==(k in ('calculation_id','artifact_id'))
            identities.append(dict(kind=k,season=int(s),historical=oldrow[k],new=new[k],equal=equal,
                reason='Same source bytes, definitions and canonical content; no path/clock in calculation/artifact' if equal else 'New UUID archive/execution, never historical alias'))
    for field,k in (('materialization_id','materializationId'),('input_id','temporalInputId')):
        identities.append(dict(kind=k,historical=old['materialization'][field],new=report['materialization'][field],equal=False,
            reason=('Current receipts, SQL lineage and derivation' if field=='materialization_id' else 'Current FILE availability/receipt resources; calculations remain identical')))
    previous=json.loads((ROOT/'docs/plans/metrics/e5c-2/real-proof.json').read_bytes())
    identities.append(dict(kind='bundleId',historical=previous['bundleId'],new=report['bundleId'],equal=False,reason='New nominal source/derivation, current bundle pin verified'))
    oa={a['gameId']:a for req in oldq['requests'] for a in req['associations']};na={a['gameId']:a for req in newq['requests'] for a in req['associations']}
    assert set(oa)==set(na)
    nominal=[]
    for gid,a in sorted(na.items()):
        item={'gameId':gid,'historical':oa[gid],'new':a,'equalFields':[k for k in a if a[k]==oa[gid][k]]}
        assert all(a[k]==oa[gid][k] for k in ('gameId','calculationId','coverageRevisionId','artifactId'))
        assert a['archiveId']!=oa[gid]['archiveId']
        assert a['temporalRevisionId']==oa[gid]['temporalRevisionId']
        item['temporalIdentityReason']='Association projection excludes archive receipts and SQL timestamps; original calculation, coverage and auxiliary facts are unchanged'
        nominal.append(item)
    relations=json.loads((artifacts/'relations.json').read_bytes())['relations']
    receipts=relations['metric_archive_receipt']
    times=[r['receipt_json']['observed_at'] for r in receipts]
    persisted=[r['persisted_at'] for rows in relations.values() for r in rows if 'persisted_at' in r]
    save(out/'identities.json',dict(base=BASE,identities=identities,nominalAssociations=nominal,
        sourceRevisionIds=['sha256:'+x['sha256'] for x in json.loads((artifacts/'inventory.json').read_bytes())['files']],
        receipts=dict(historicalArchive=old['firstAndRepeat']['first']['2025']['archive_id'],historicalIndividualIds='NOT_RECOVERED; summary records count only',historicalCount=old['idempotence']['tableRows']['metric_archive_receipt'],
            newCount=len(receipts),newIds=sorted(r['receipt_id'] for r in receipts),newObservedAtMin=min(times),newObservedAtMax=max(times)),
        newPersistedAtMin=min(persisted),newPersistedAtMax=max(persisted),
        newMaterializationDerivedAt=json.loads((artifacts/'materialized/lineage.json').read_bytes())['derivedAt'],newProjectionDerivedAt=newq['derivedAt'],
        equalityDoesNotProveHistoricalKnowledge=True))
    for source,name in [('inventory.json','sources.json'),('accepted-code-hashes.json','accepted-code-hashes.json'),('SHA256SUMS.json','artifact-hashes.json')]:shutil.copyfile(artifacts/source,out/name)
    save(out/'files.json',dict(primary=str(artifacts),backup=report['backup'],files=[dict(path=str(p.relative_to(artifacts)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(artifacts.rglob('*')) if p.is_file()],
        bytesPerCopy=sum(p.stat().st_size for p in artifacts.rglob('*') if p.is_file()),fullReportSha256=sha(artifacts/'recovery-report.json')))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();summarize(a.artifacts,a.output)
