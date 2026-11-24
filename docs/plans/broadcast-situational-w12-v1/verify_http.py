"""Compare the full HTTP snapshot with the validated durable package, plus refusals."""
import argparse
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'etl-pipeline/src'))
from nfl_sideline_etl.situational import read
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18098);a=p.parse_args()
config=json.loads((Path(__file__).parent/'situational-config.json').read_bytes());data,marker=read(config['bundle'])
origin=f'http://127.0.0.1:{a.port}'
def get(path='/__situational/',method='GET',headers=None,body=None):
 h={'X-Local-Situational':'1'} if headers is None else headers
 try:
  with urlopen(Request(origin+path,method=method,headers=h,data=body)) as r:return r.status,json.load(r),dict(r.headers)
 except HTTPError as e:return e.code,json.load(e),dict(e.headers)
status,value,headers=get();assert status==200
assert value==dict(transportVersion='situational-response-v1',bundleId=marker['bundleId'],data=data)
refusals=[]
for kwargs in [dict(method='POST'),dict(headers={}),dict(headers={'X-Local-Situational':'1','Origin':'https://example.com'}),dict(headers={'X-Local-Situational':'1','Host':'localhost:'+str(a.port)}),dict(path='/__situational/?path=/tmp'),dict(path='/__situational/pbp.parquet'),dict(body=b'x')]:
 status,_,_=get(**kwargs);assert status==403;refusals.append(dict(request=kwargs if not kwargs.get('body') else {'body':'x'},status=status))
assert headers['Cache-Control']=='no-store' and headers['X-Content-Type-Options']=='nosniff'
report=dict(bundleId=marker['bundleId'],documents=len(data['documents']),integralResponseMatchesValidatedArtifact=True,refusals=refusals)
(Path(__file__).parent/'checks/http.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
