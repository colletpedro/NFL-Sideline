"""Full operational reader → DTO → HTTP; all active docs and transport negatives."""
import argparse
import http.client
import json
from pathlib import Path
from nominal_selection import save
from nfl_sideline_etl.metrics_lab.adapter import prepare


def request(port,path='/__observations/',headers=None,method='GET',body=None):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=30)
    c.request(method,path,body=body,headers={'X-Local-Observations':'1',**(headers or {})})
    r=c.getresponse(); result=(r.status,json.loads(r.read() or '{}'),dict(r.getheaders()));c.close();return result


def run(config,port,output):
    expected=prepare(json.loads(config.read_bytes()));assert all(e['status']=='READY' for e in expected['entries'])
    status,catalog,headers=request(port);assert status==200 and not catalog['errorCode']
    assert catalog['sessionId']==expected['sessionId'] and len(catalog['bundles'])==1
    assert headers['Cache-Control']=='no-store' and headers['X-Content-Type-Options']=='nosniff'
    assert 'Access-Control-Allow-Origin' not in headers
    entry=expected['entries'][0]; docs={d['observationId']:d for d in entry['documents']}
    assert len(docs)==588 and len(catalog['bundles'][0]['observations'])==588
    for s in catalog['bundles'][0]['observations']:
        status,actual,h=request(port,f"/__observations/{entry['entryId']}/{s['observationId'][7:]}",{'X-Observation-Session':catalog['sessionId']})
        assert status==200 and actual['sessionId']==catalog['sessionId'] and actual['document']==docs[s['observationId']]
        assert s['dtoId']==actual['document']['dtoId'] and h['Cache-Control']=='no-store'
    docpath=f"/__observations/{entry['entryId']}/{next(iter(docs))[7:]}"
    cases=[('/__observations/',{'Origin':'http://evil.invalid'},'GET',None,403),
           ('/__observations/',{'Host':f'localhost:{port}'},'GET',None,403),
           ('/__observations/',{'X-Local-Observations':'0'},'GET',None,403),
           ('/__observations/',{},'POST',None,403),('/__observations/',{},'GET','{}',403),
           ('/__observations/?path=/etc/passwd',{},'GET',None,403),
           ('/__observations/%2e%2e/config.json',{},'GET',None,403),
           (docpath,{},'GET',None,409),(docpath,{'X-Observation-Session':'stale'},'GET',None,409),
           ('/__observations/missing/'+'0'*64,{'X-Observation-Session':catalog['sessionId']},'GET',None,404)]
    results=[]
    for path,h,method,body,status_expected in cases:
        code,actual,_=request(port,path,h,method,body);assert code==status_expected,(path,code)
        results.append(dict(path=path,method=method,status=code,error=actual['error']))
    save(output,dict(origin=f'http://127.0.0.1:{port}',documentsExactlyMatched=588,bundleId=entry['bundleId'],
        sessionId=catalog['sessionId'],refusals=results,fullOperationalReader=True))
    print('588 HTTP documents exactly matched; 10 transport refusals passed')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True)
    p.add_argument('--port',type=int,default=18096);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.config,a.port,a.output)
