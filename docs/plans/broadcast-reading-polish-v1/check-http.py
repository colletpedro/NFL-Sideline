from pathlib import Path
import hashlib,json,http.client
base=Path(__file__).resolve().parents[3]
root=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle')
pin='sha256:8971d767b6ec0557465aeb65aeb00533fd10255a62f4b916954b3854daa15cef'
sourcepin='sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc'
requests=[]
def get(path,headers=None,method='GET',port=18106,expected=200):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=15);c.request(method,path,headers=headers or {});r=c.getresponse();b=r.read();h=dict(r.getheaders());assert r.status==expected,(path,r.status,b[:160]);requests.append(dict(path=path,port=port,method=method,status=r.status));c.close();return b,h
for source,prefix,marker,pinhead,pinned,items,key,dh in [(root,'/__team-w12/','X-Local-Team-W12','X-Team-Collection',pin,'teams','team','X-Team-Document'),(root/'source/matchups','/__matchup-w12/','X-Local-Matchup-W12','X-Matchup-Collection',sourcepin,'games','gameId','X-Matchup-Document')]:
 assert 'sha256:'+hashlib.sha256((source/'index.json').read_bytes()).hexdigest()==pinned
 idx=json.loads((source/'index.json').read_bytes());headers={marker:'1',pinhead:pinned};b,h=get(prefix,headers);assert b==(source/'index.json').read_bytes()
 for e in idx[items]:
  path=prefix+e[key];b,h=get(path,headers);old,_=get(path,headers,port=18105);assert b==old==(source/e['path']).read_bytes();assert 'sha256:'+hashlib.sha256(b).hexdigest()==e['documentHash']==h[dh];assert h['Cache-Control']=='no-store'
 for path,method,h,status in [(prefix,'GET',{},403),(prefix,'POST',headers,403),(prefix+'?path=/tmp/other','GET',headers,403),(prefix+'../other','GET',headers,403),(prefix,'GET',{**headers,'Origin':'http://127.0.0.1:18105'},403),(prefix,'GET',{**headers,'Host':'localhost:18106'},403),(prefix,'GET',{**headers,pinhead:'wrong'},409),(prefix+'ZZZ','GET',headers,404 if items=='teams' else 403),(prefix,'OPTIONS',headers,403),(prefix,'GET',{**headers,'Content-Length':'1'},403)]:get(path,h,method,expected=status)
 for duplicate in ['Host','Origin',marker,pinhead]:
  c=http.client.HTTPConnection('127.0.0.1',18106,timeout=15);c.putrequest('GET',prefix,skip_host=True);hh={'Host':'127.0.0.1:18106','Origin':'http://127.0.0.1:18106',**headers}
  for k,v in hh.items():c.putheader(k,v)
  c.putheader(duplicate,hh[duplicate]);c.endheaders();r=c.getresponse();r.read();assert r.status==403;c.close();requests.append(dict(path=prefix,duplicate=duplicate,status=403))
(base/'docs/plans/broadcast-reading-polish-v1/checks/http.json').write_text(json.dumps(dict(teamPin=pin,matchupPin=sourcepin,exactTeams=32,exactMatchups=32,identicalTo18105=True,requests=requests),indent=2)+'\n')
print('PASS:',len(requests),'requests; team and matchup bytes unchanged versus durable source and reference')
