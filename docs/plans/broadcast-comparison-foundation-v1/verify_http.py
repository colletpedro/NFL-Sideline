"""HTTP wire bytes equal pinned artifact; no projection functions as oracle."""
from http.client import HTTPConnection
import hashlib
import json
from pathlib import Path
import sys

config=json.loads(Path(sys.argv[1]).read_bytes());output=Path(sys.argv[2]);port=config['port']
raw=(Path(config['path'])/'comparison.json').read_bytes()
assert 'sha256:'+hashlib.sha256(raw).hexdigest()==config['expectedBundleId']
base={'X-Local-Comparison':'1'}
cases=[('GET','/__comparison/',base,None,200),('GET','/__comparison/',{**base,'Origin':f'http://127.0.0.1:{port}'},None,200),
       ('POST','/__comparison/',base,None,403),('PUT','/__comparison/',base,None,403),('OPTIONS','/__comparison/',base,None,403),
       ('GET','/__comparison/',{},None,403),('GET','/__comparison/',{**base,'X-Local-Comparison':'0'},None,403),
       ('GET','/__comparison/?path=/etc/passwd',base,None,403),('GET','/__comparison/child',base,None,403),
       ('GET','/__situational/',base,None,403),('GET','/__observations/',base,None,403),
       ('GET','/__comparison/',{**base,'Host':f'localhost:{port}'},None,403),('GET','/__comparison/',{**base,'Host':'evil.example'},None,403),
       ('GET','/__comparison/',{**base,'Origin':'https://example.com'},None,403),('GET','/__comparison/',{**base,'Origin':'null'},None,403),
       ('GET','/__comparison/',base,'x',403),('GET','/__comparison/',{**base,'Transfer-Encoding':'chunked'},None,403)]
result=[]
for method,path,headers,body,status in cases:
    c=HTTPConnection('127.0.0.1',port);c.request(method,path,body=body,headers=headers);r=c.getresponse();b=r.read()
    assert r.status==status,(method,path,r.status)
    assert r.getheader('Cache-Control')=='no-store' and r.getheader('X-Content-Type-Options')=='nosniff'
    if status==200:
        assert b==raw and r.getheader('X-Comparison-Bundle')==config['expectedBundleId']
    result.append(dict(method=method,path=path,status=status));c.close()
output.write_text(json.dumps(dict(bundleId=config['expectedBundleId'],responseBytes=len(raw),exactArtifactBytes=True,cases=result),indent=2)+'\n')
print('HTTP:',len(result),'checks; exact frozen artifact bytes')
