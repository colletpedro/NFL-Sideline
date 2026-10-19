"""Real bundle counterexamples in disposable copies and exact real HTTP parity."""
import argparse
from copy import deepcopy
import http.client
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'etl-pipeline/src'))
from nfl_sideline_etl.metrics_observations.publication import read, FILES
from nfl_sideline_etl.metrics_observations.core import semantic_id
from nfl_sideline_etl.metrics_lab.adapter import prepare
from nfl_sideline_etl.offline_metrics.artifact import identity,json_bytes
from nfl_sideline_etl.metrics_persistence.archive import digest
from recover import hashes,save


def rehash(root):
    docs=json.loads((root/'observations.json').read_bytes());m=json.loads((root/'manifest.json').read_bytes())
    for d in docs:
        old=d['observationId'];new=semantic_id(d);d['observationId']=new
        if old!=new:m['lineageByObservation'][new]=m['lineageByObservation'].pop(old)
    docs.sort(key=lambda d:d['observationId']);m['observationIds']=sorted(d['observationId'] for d in docs)
    m['bundleId']=identity({k:v for k,v in m.items() if k!='bundleId'})
    (root/'manifest.json').write_bytes(json_bytes(m));(root/'observations.json').write_bytes(json_bytes(docs))
    marker=json.loads((root/'COMPLETED.json').read_bytes());marker['bundleId']=m['bundleId']
    marker['files']={n:digest((root/n).read_bytes()) for n in FILES}
    (root/'COMPLETED.json').write_bytes(json_bytes(marker))


def negatives(bundle,config,output):
    before=hashes(bundle);results=[]
    with tempfile.TemporaryDirectory(prefix='nfl-e5c3r-negative-',dir='/private/tmp') as temporary:
        tmp=Path(temporary)
        for case in ('invented_epa','missing_dependency','mandatory_field_removed','mandatory_limit_removed','isolated_extract','wrong_pin'):
            dest=tmp/case;shutil.copytree(bundle,dest)
            if case=='missing_dependency':(dest/'shared-source/input.json').unlink()
            elif case=='isolated_extract':
                for p in list(dest.iterdir()):
                    if p.name!='observations.json':shutil.rmtree(p) if p.is_dir() else p.unlink()
            elif case=='wrong_pin':
                c=deepcopy(config);c['bundles'][0]['path']=str(dest);c['bundles'][0]['expectedBundleId']='sha256:'+'0'*64
                entry=prepare(c)['entries'][0];assert entry['status']=='ERROR' and entry['errorCode']=='BUNDLE_ID_MISMATCH'
                results.append(dict(case=case,outcome='REFUSED',reason=entry['errorCode'],disposableCopy=True));continue
            else:
                docs=json.loads((dest/'observations.json').read_bytes());d=next(d for d in docs if d['totals'] is not None)
                if case=='invented_epa':d['values']['epa']['numerator']='777'
                elif case=='mandatory_field_removed':d.pop('guarantees')
                else:d['limitations']=[x for x in d['limitations'] if x['code']!='UNKNOWN_FILTER_FLAGS_GAME_SCOPE']
                (dest/'observations.json').write_bytes(json_bytes(docs));rehash(dest)
            try:read(dest)
            except (ValueError,OSError,KeyError) as e:results.append(dict(case=case,outcome='REFUSED',reason=str(e),externallyRehashed=case in ('invented_epa','mandatory_field_removed','mandatory_limit_removed'),disposableCopy=True))
            else:raise AssertionError('Adulteration accepted: '+case)
            shutil.rmtree(dest)
    assert hashes(bundle)==before
    save(output,dict(proof='REAL_BUNDLE_DISPOSABLE_COUNTEREXAMPLES',cases=results,preservedBundleUnchanged=True))


def request(path,method='GET',headers=None,body=None):
    c=http.client.HTTPConnection('127.0.0.1',18083,timeout=10)
    c.request(method,path,body=body,headers={'X-Local-Observations':'1',**(headers or {})})
    r=c.getresponse();status=r.status;headers=dict(r.getheaders());raw=r.read();c.close();return status,raw,headers


def http_probe(config,output):
    expected=prepare(config);assert expected['entries'][0]['status']=='READY'
    status,raw,headers=request('/__observations/');assert status==200
    catalog=json.loads(raw);assert catalog['sessionId']==expected['sessionId']
    assert headers['Cache-Control']=='no-store' and headers['X-Content-Type-Options']=='nosniff'
    docs=[]
    for e in catalog['bundles']:
        local=next(x for x in expected['entries'] if x['entryId']==e['entryId']);assert e['dataKind']=='REAL_ARCHIVE' and e['status']=='READY'
        assert len(e['observations'])==48
        for s in e['observations']:
            path=f"/__observations/{e['entryId']}/{s['observationId'][7:]}"
            status,raw,h=request(path,headers={'X-Observation-Session':catalog['sessionId']});assert status==200
            actual=json.loads(raw);assert actual['sessionId']==catalog['sessionId']
            dto=next(d for d in local['documents'] if d['observationId']==s['observationId']);assert actual['document']==dto
            assert dto['dtoId']==s['dtoId'];docs.append(dto)
    assert len(docs)==48
    for d in docs:
        assert all(d['guarantees'][k]['state']=='UNKNOWN' for k in ('completeness','coverage','temporal'))
        assert d['guarantees']['compatibility']['epaModel']['state']=='UNKNOWN'
        if d['request']['period']['weeks']==[3]:assert d['totals'] is None and all(v is None for v in d['values'].values())
    cases=[('/__observations/?path=/etc/passwd',{},'GET',None,403),('/__observations/../config.json',{},'GET',None,403),
        ('/__observations/%2e%2e/config.json',{},'GET',None,403),('/__observations/',{'Origin':'http://evil.example'},'GET',None,403),
        ('/__observations/',{'Host':'evil.example'},'GET',None,403),('/__observations/',{'X-Local-Observations':'0'},'GET',None,403),
        ('/__observations/',{},'POST',None,403),('/__observations/',{},'GET','{}',403),('/__observations/',{},'HEAD',None,403),
        ('/__observations/missing/'+'0'*64,{'X-Observation-Session':catalog['sessionId']},'GET',None,404),
        ('/__observations/missing/'+'0'*64,{'X-Observation-Session':'stale'},'GET',None,409)]
    for path,h,method,body,code in cases:assert request(path,method,h,body)[0]==code
    wire=json.dumps(docs)
    for forbidden in ('archive_root','receipt_json','/private/tmp','lineage.json','context_json','password'):assert forbidden not in wire
    save(output,dict(proof='REAL_HTTP_REAL_ARCHIVED_PARQUET_CHAIN',sessionId=catalog['sessionId'],documents=len(docs),refusals=len(cases),
        exactReaderDtoParity=True,bundleId=catalog['bundles'][0]['bundleId'],catalog=catalog))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['negatives','http']);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists();config=json.loads(a.config.read_bytes())
    if a.action=='negatives':negatives(Path(config['bundles'][0]['path']),config,a.output)
    else:http_probe(config,a.output)
