"""Read-only HTTP probe against the explicitly started local lab; no ETL or writes."""
import http.client
import json
from pathlib import Path
import argparse


def request(path, *, method='GET', headers=None, body=None):
    c=http.client.HTTPConnection('127.0.0.1',18083,timeout=10)
    h={'X-Local-Observations':'1', **(headers or {})}
    c.request(method,path,body=body,headers=h)
    r=c.getresponse(); data=r.read(); status=r.status;c.close()
    return status,data


def probe():
    status,raw=request('/__observations/');assert status==200
    catalog=json.loads(raw);assert catalog['transportVersion']=='metrics-lab-catalog-v1'
    docs=[]
    for e in catalog['bundles']:
        for s in e['observations']:
            path=f"/__observations/{e['entryId']}/{s['observationId'][7:]}"
            status,raw=request(path,headers={'X-Observation-Session':catalog['sessionId']});assert status==200
            d=json.loads(raw)['document'];assert d['observationId']==s['observationId'] and d['bundleId']==e['bundleId']
            assert d['guarantees']['temporal']['state']=='UNKNOWN';docs.append(d)
    cases=[('/__observations/?path=/etc/passwd',{},'GET',None,403),
        ('/__observations/../config.json',{},'GET',None,403),
        ('/__observations/%2e%2e/config.json',{},'GET',None,403),
        ('/__observations/',{'Origin':'http://evil.example'},'GET',None,403),
        ('/__observations/',{'Host':'evil.example'},'GET',None,403),
        ('/__observations/',{'X-Local-Observations':'0'},'GET',None,403),
        ('/__observations/',{},'POST',None,403),('/__observations/',{},'GET','{}',403),
        ('/__observations/',{},'HEAD',None,403),
        ('/__observations/missing/'+('0'*64),{'X-Observation-Session':catalog['sessionId']},'GET',None,404),
        ('/__observations/missing/'+('0'*64),{'X-Observation-Session':'stale'},'GET',None,409),
        ('/@fs/private/tmp/nfl-e5c3-demo-final/config.json',{},'GET',None,403)]
    for path,headers,method,body,expected in cases:
        actual,_=request(path,method=method,headers=headers,body=body);assert actual==expected,(path,actual,expected)
    wire=json.dumps(docs)
    for forbidden in ('archive_root','receipt_json','/private/tmp','lineage.json','context_json'):assert forbidden not in wire
    return {'proof':'REAL_HTTP_SYNTHETIC_BUNDLES','sessionId':catalog['sessionId'],
        'documents':len(docs),'refusals':len(cases),'entries':[{k:e[k] for k in ('entryId','status','bundleId','errorCode')} for e in catalog['bundles']]}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
    report=json.dumps(probe(),indent=2)+'\n'
    if a.output:a.output.write_text(report)
    print(report)
