"""All published private bytes and request counterexamples through real HTTP."""
import hashlib,http.client,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;config=json.loads((HERE/'source-config.json').read_text());root=Path(config['bundle']);pin=config['pin'];index=json.loads((root/'index.json').read_text());results=[]
def req(path,method='GET',headers=None,body=None):
 c=http.client.HTTPConnection('127.0.0.1',18109,timeout=30);h={'X-Local-Season-Analysis':'1','X-Season-Collection':pin};h.update(headers or {});c.request(method,path,headers=h,body=body);r=c.getresponse();b=r.read();out=(r.status,dict(r.getheaders()),b);c.close();return out
for path,source in [('', 'index.json'),*[(g['path'][:-5],g['path']) for g in index['games']],*[(t['path'][:-5],t['path']) for t in index['teams']]]:
 s,h,b=req('/__season-analysis/'+path);expected=(root/source).read_bytes();actual='sha256:'+hashlib.sha256(b).hexdigest()
 assert s==200 and b==expected and h['X-Season-Collection']==pin and h['X-Season-Document']==actual and h.get('Access-Control-Allow-Origin') is None,(path,s)
 results.append(dict(path=path,status=s,bytes=len(b),hash=actual))
bad=[('GET','/__season-analysis/?file=/tmp/x',{},None,403),('POST','/__season-analysis/',{},None,403),('HEAD','/__season-analysis/',{},None,403),('GET','/__season-analysis/',{'X-Local-Season-Analysis':'0'},None,403),('GET','/__season-analysis/',{'Origin':'https://example.test'},None,403),('GET','/__season-analysis/',{'Host':'localhost:18109'},None,403),('GET','/__season-analysis/',{},'x',403),('GET','/__season-analysis/',{'X-Season-Collection':'sha256:'+'0'*64},None,409),('GET','/__season-analysis/games/2026_07_BUF_JAX',{},None,404),('GET','/__season-analysis/teams/XYZ',{},None,404),('GET','/__season-analysis/teams/BUF/extra',{},None,403),('GET','/__season-analysis/../source/pbp.parquet',{},None,403),('GET','/__season-analysis/games/2026_08_A_B',{},None,403)]
for method,path,h,body,expected in bad:
 s,_,_=req(path,method,h,body);assert s==expected,(method,path,s,expected)
for name,value in [('X-Local-Season-Analysis','1'),('X-Season-Collection',pin),('Host','127.0.0.1:18109')]:
 c=http.client.HTTPConnection('127.0.0.1',18109);c.putrequest('GET','/__season-analysis/');c.putheader('X-Local-Season-Analysis','1');c.putheader('X-Season-Collection',pin);c.putheader(name,value);c.endheaders();r=c.getresponse();r.read();assert r.status==403;c.close()
report=dict(pin=pin,exactDocuments=len(results),counterexamples=len(bad)+3,documents=results,passed=True)
(HERE/'checks/http.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='documents'}))
