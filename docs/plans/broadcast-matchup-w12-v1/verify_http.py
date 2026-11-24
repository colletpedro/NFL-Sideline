"""Real loopback HTTP: all documents and explicit negative cases."""
from http.client import HTTPConnection
import hashlib
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parent
cfg=json.loads((root/'source-config.json').read_bytes());bundle=Path(cfg['path']);index=json.loads((bundle/'index.json').read_bytes())
base={'X-Local-Matchup-W12':'1','X-Matchup-Collection':cfg['expectedBundleId']}
results=[]
def request(method,url,extra=None,body=None,expected=200,original=None,duplicate=None):
    c=HTTPConnection('127.0.0.1',18104,timeout=15)
    if duplicate:
        c.putrequest(method,url)
        for k,v in {**base,**(extra or {})}.items():c.putheader(k,v)
        for k,v in duplicate:c.putheader(k,v)
        c.endheaders()
    else:c.request(method,url,headers={**base,**(extra or {})},body=body)
    response=c.getresponse();b=response.read();status=response.status
    assert status==expected,(method,url,status,expected,b[:100])
    if original:
        assert b==original.read_bytes()
        assert response.getheader('X-Matchup-Collection')==cfg['expectedBundleId']
        assert response.getheader('X-Matchup-Document')=='sha256:'+hashlib.sha256(b).hexdigest()
        assert response.getheader('Cache-Control')=='no-store' and response.getheader('X-Content-Type-Options')=='nosniff'
    results.append(dict(method=method,path=url,status=status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),exactBytes=bool(original)));c.close()
request('GET','/__matchup-w12/',original=bundle/'index.json')
for e in index['games']:request('GET','/__matchup-w12/'+e['gameId'],original=bundle/e['path'])
request('GET','/__matchup-w12/',{'Origin':'http://127.0.0.1:18104'},original=bundle/'index.json')
for method in ('POST','PUT','DELETE','OPTIONS','HEAD'):request(method,'/__matchup-w12/',expected=403)
for extra in ({'Origin':'https://example.com'},{'Origin':'null'},{'Origin':'http://127.0.0.1:18103'},{'Host':'localhost:18104'},{'Host':'127.0.0.1:18103'},{'X-Local-Matchup-W12':'0'},{'Content-Length':'1'},{'Transfer-Encoding':'chunked'}):request('GET','/__matchup-w12/',extra,expected=403)
request('GET','/__matchup-w12/',body='x',expected=403)
for url in ('/__matchup-w12','/__matchup-w12/?path=/tmp/file','/__matchup-w12/../../private','/__matchup-w12/2026_01_NYJ_TEN/child','/__matchup-w12/2026_01_NYJ_TEN?x=1'):
    request('GET',url,expected=403)
request('GET','/__matchup-w12/2026_01_XXX_YYY',expected=404)
request('GET','/__matchup-w12/',{'X-Matchup-Collection':'sha256:'+'0'*64},expected=409)
request('GET','/__matchup-w12/',duplicate=[('Host','127.0.0.1:18104')],expected=403)
request('GET','/__matchup-w12/',duplicate=[('X-Local-Matchup-W12','1')],expected=403)
request('GET','/__matchup-w12/',duplicate=[('Origin','http://127.0.0.1:18104'),('Origin','http://127.0.0.1:18104')],expected=403)
# Expect: 100-continue receives an early 100 by Node unless checked on checkContinue.
request('GET','/__matchup-w12/',{'Expect':'something-else'},expected=417)
(root/'checks/http.json').write_text(json.dumps(dict(bundleId=cfg['expectedBundleId'],documents=32,requests=results),indent=2)+'\n')
print(f'{len(results)} requests; 32 documents exact, index exact, refusals verified')
