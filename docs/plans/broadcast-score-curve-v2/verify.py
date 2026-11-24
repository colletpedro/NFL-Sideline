import hashlib,http.client,json,shutil,sys
from pathlib import Path
import polars as pl
from nfl_sideline_etl.score_curve.package import read,generate
from nfl_sideline_etl.season_analysis.package import hashes
PLAN=Path(__file__).resolve().parent;root=Path(json.loads((PLAN/'source-config.json').read_text())['bundle']);b,m=read(root);extra=json.loads(b);source=root/'source';story=json.loads((source/'story.json').read_text());season=source/'source';index=json.loads((season/'index.json').read_text())
def get(path,headers,method='GET',body=None):
 c=http.client.HTTPConnection('127.0.0.1',18111,timeout=30);c.request(method,path,body,headers);r=c.getresponse();out=(r.status,dict(r.getheaders()),r.read());c.close();return out
header={'X-Local-Curve-Events':'1','X-Curve-Collection':m['bundleId']};s,h,data=get('/__curve-events/',header);assert s==200 and data==b and h['X-Curve-Collection']==m['bundleId'];n=1
for method,path,head,body,status in [('POST','/__curve-events/',header,None,403),('HEAD','/__curve-events/',header,None,403),('GET','/__curve-events/?x=1',header,None,403),('GET','/__curve-events/',{},None,403),('GET','/__curve-events/',dict(header,Origin='https://example.com'),None,403),('GET','/__curve-events/',dict(header,Host='localhost:18111'),None,403),('GET','/__curve-events/',dict(header,**{'X-Curve-Collection':'wrong'}),None,409),('GET','/__curve-events/',header,'x',403)]:
 s,_,_=get(path,head,method,body);assert s==status;n+=1
s,h,data=get('/__game-story/',{'X-Local-Game-Story':'1','X-Game-Story-Collection':extra['sourcePin']});assert s==200 and data==(source/'story.json').read_bytes();n+=1
for p in ['index.json']+[g['path'] for g in index['games']]+[t['path'] for t in index['teams']]:
 s,h,data=get('/__season-analysis/'+('' if p=='index.json' else p[:-5]),{'X-Local-Season-Analysis':'1','X-Season-Collection':story['sourcePin']});assert s==200 and data==(season/p).read_bytes();n+=1
raw=pl.read_parquet(season/'source/pbp.parquet');rows=raw.filter((pl.col('play_deleted')==0)&((pl.col('interception')==1)|(pl.col('fumble_lost')==1))).to_dicts();events={(g,e['playId']):e for g,es in extra['games'].items() for e in es};assert len(events)==len(rows)==262
for r in rows:
 e=events[r['game_id'],int(r['play_id'])];assert e['score']==[r['total_away_score'],r['total_home_score']] and e['remaining']==r['quarter_seconds_remaining']
 if e['kind']=='INTERCEPTION':assert (e['lostTeam'],e['recoveredTeam'])==(r['posteam'],r['defteam'])
 else:assert any((e['lostTeam'],e['recoveredTeam'])==(r[f'fumbled_{j}_team'],r[f'fumble_recovery_{j}_team']) for j in (1,2))
result=dict(httpChecks=n,oldSeasonDocuments=140,sourceStoryUnchanged=True,turnovers=len(events),games=len(extra['games']),sourceScoringEvents=sum(len(t['events']) for t in story['timelines'].values()),divergences=0,pin=m['bundleId']);(PLAN/'checks/http-reconciliation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if '--recovery' in sys.argv:
 copy=root.parent/'verified-copy';repro=root.parent/'reproduced-from-copy'
 if not copy.exists():shutil.copytree(root,copy)
 read(copy,m['bundleId']);assert hashes(copy)==hashes(root)
 if not repro.exists():generate(copy/'source',repro)
 read(repro,m['bundleId']);assert hashes(repro)==hashes(root)
 (PLAN/'checks/recovery.json').write_text(json.dumps(dict(copy=str(copy),reproduction=str(repro),byteIdentical=True,files=len(hashes(root))),indent=2)+'\n')
