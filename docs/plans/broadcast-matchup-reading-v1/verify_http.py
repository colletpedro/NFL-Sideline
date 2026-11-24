"""Real local wire bytes and refusals; startup adapter negatives use operator configs."""
import hashlib
from http.client import HTTPConnection
import json
from pathlib import Path
import subprocess
import tempfile
import os

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
cfg=json.loads((HERE/'source-config.json').read_bytes());raw=(Path(cfg['path'])/'comparison.json').read_bytes()
assert 'sha256:'+hashlib.sha256(raw).hexdigest()==cfg['expectedBundleId']
base={'X-Local-Matchup':'1'};port=18102;path='/__matchup-reading/'
cases=[('GET',path,base,None,200),('GET',path,{**base,'Origin':'http://127.0.0.1:18102'},None,200),
       ('POST',path,base,None,403),('OPTIONS',path,base,None,403),('PUT',path,base,None,403),
       ('GET',path,{},None,403),('GET',path,{**base,'X-Local-Matchup':'0'},None,403),
       ('GET',path+'?path=/tmp/another',base,None,403),('GET',path+'file',base,None,403),
       ('GET',path,{**base,'Host':'localhost:18102'},None,403),
       ('GET',path,{**base,'Origin':'http://127.0.0.1:18101'},None,403),('GET',path,{**base,'Origin':'https://example.com'},None,403),
       ('GET',path,base,'x',403),('GET',path,{**base,'Transfer-Encoding':'chunked'},None,403)]
report=[]
for method,url,headers,body,status in cases:
    c=HTTPConnection('127.0.0.1',port);c.request(method,url,headers=headers,body=body);r=c.getresponse();b=r.read()
    assert r.status==status,(method,url,r.status)
    if status==200:
        assert b==raw and r.getheader('X-Comparison-Bundle')==cfg['expectedBundleId']
    assert r.getheader('Cache-Control')=='no-store' and r.getheader('X-Content-Type-Options')=='nosniff'
    report.append(dict(method=method,path=url,status=status));c.close()
c=HTTPConnection('127.0.0.1',port);c.putrequest('GET',path);c.putheader('Host','127.0.0.1:18102');c.putheader('X-Local-Matchup','1');c.endheaders();r=c.getresponse();assert r.status==403;r.read();c.close()
report.append(dict(method='GET',path=path,status=403,case='duplicate Host'))
# Full Python reader through the same Node process adapter rejects mismatched pin
# and missing source. No live source/config is edited, no other listener is stopped.
negatives=[]
with tempfile.TemporaryDirectory(prefix='nfl-matchup-startup-',dir='/private/tmp') as temp:
    script="import {prepareComparison} from './web-ui/build/matchup-process.mjs';try{await prepareComparison();process.exitCode=9}catch{console.log('SOURCE_REJECTED')}"
    for name,change in [('wrong-pin',dict(expectedBundleId='sha256:'+'0'*64)),('missing-source',dict(path='/private/tmp/source-that-does-not-exist'))]:
        p=Path(temp)/(name+'.json');p.write_text(json.dumps({**cfg,**change}))
        env={**os.environ,'NFL_MATCHUP_CONFIG':str(p),'NFL_OBSERVATION_PYTHON':'/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'}
        run=subprocess.run(['/opt/homebrew/opt/node@24/bin/node','--input-type=module','-e',script],cwd=ROOT,env=env,capture_output=True,text=True)
        assert run.returncode==0 and run.stdout.strip()=='SOURCE_REJECTED',(name,run.returncode)
        negatives.append(dict(case=name,fullReaderRejected=True,noFallback=True))
(HERE/'checks/http.json').write_text(json.dumps(dict(bundleId=cfg['expectedBundleId'],responseBytes=len(raw),exactArtifactBytes=True,cases=report,startupNegatives=negatives),indent=2)+'\n')
print('HTTP:',len(report),'real requests; exact artifact bytes; startup negatives:',len(negatives))
