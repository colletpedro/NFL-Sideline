"""Exact HTTP bytes and transport refusals; no projector as oracle."""
from pathlib import Path
import hashlib,json,http.client
root=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle')
idx=json.loads((root/'index.json').read_bytes());pin='sha256:'+hashlib.sha256((root/'index.json').read_bytes()).hexdigest();requests=[]
def get(path,headers=None,method='GET',port=18105,expected=200):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=10);c.request(method,path,headers=headers or {});r=c.getresponse();body=r.read();h=dict(r.getheaders());assert r.status==expected,(path,r.status,body[:160]);requests.append(dict(path=path,port=port,method=method,status=r.status));c.close();return body,h
headers={'X-Local-Team-W12':'1','X-Team-Collection':pin}
b,h=get('/__team-w12/',headers);assert b==(root/'index.json').read_bytes() and h['X-Team-Collection']==pin
for e in idx['teams']:
 b,h=get('/__team-w12/'+e['team'],headers);assert b==(root/e['path']).read_bytes();assert 'sha256:'+hashlib.sha256(b).hexdigest()==e['documentHash']==h['X-Team-Document'];assert h['Cache-Control']=='no-store'
for path,method,h,status in [('/__team-w12/','GET',{},403),('/__team-w12/','POST',headers,403),('/__team-w12/?path=/tmp/other','GET',headers,403),('/__team-w12/../BAL','GET',headers,403),('/__team-w12/','GET',{**headers,'Origin':'http://127.0.0.1:18104'},403),('/__team-w12/','GET',{**headers,'Host':'localhost:18105'},403),('/__team-w12/','GET',{**headers,'X-Team-Collection':'wrong'},409),('/__team-w12/ZZZ','GET',headers,404),('/__team-w12/','OPTIONS',headers,403),('/__team-w12/','GET',{**headers,'Content-Length':'1'},403)]:get(path,h,method,expected=status)
si=json.loads((root/'source/matchups/index.json').read_bytes());mh={'X-Local-Matchup-W12':'1','X-Matchup-Collection':idx['sourceCollection']}
# Reuse actual established boundary header names, without changing its policy.
for e in si['games']:
 path='/__matchup-w12/'+e['gameId'];b,_=get(path,mh);old,_=get(path,mh,port=18104);assert b==old==(root/'source/matchups'/e['path']).read_bytes()
for duplicate in ['Host','Origin','X-Local-Team-W12','X-Team-Collection']:
 c=http.client.HTTPConnection('127.0.0.1',18105,timeout=10);c.putrequest('GET','/__team-w12/',skip_host=True)
 base={'Host':'127.0.0.1:18105','Origin':'http://127.0.0.1:18105',**headers}
 for k,v in base.items():c.putheader(k,v)
 c.putheader(duplicate,base[duplicate]);c.endheaders();r=c.getresponse();r.read();assert r.status==403;c.close();requests.append(dict(path='/__team-w12/',duplicate=duplicate,status=403))
Path('docs/plans/broadcast-hub-team-w12-v1/checks/http.json').write_text(json.dumps(dict(teams=32,matchupsUnchanged=32,requests=requests),indent=2)+'\n')
print(f'PASS: {len(requests)} HTTP checks, 32 exact team documents and 32 unchanged matchups')
