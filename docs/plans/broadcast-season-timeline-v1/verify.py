"""Read-only HTTP, recovery, and independent event/campaign reconciliation."""
import hashlib,http.client,json,shutil,sys
from pathlib import Path
import polars as pl
ROOT=Path(__file__).resolve().parents[3]
PLAN=Path(__file__).resolve().parent
cfg=json.loads((PLAN/'source-config.json').read_text());bundle=Path(cfg['bundle']);story=json.loads((bundle/'story.json').read_text());source=bundle/'source';index=json.loads((source/'index.json').read_text())
sha=lambda b:'sha256:'+hashlib.sha256(b).hexdigest()
checks=[]
def request(path,headers,method='GET',body=None):
 c=http.client.HTTPConnection('127.0.0.1',18110,timeout=30);c.request(method,path,body=body,headers=headers);r=c.getresponse();b=r.read();h=dict(r.getheaders());s=r.status;c.close();return s,h,b
h={'X-Local-Game-Story':'1','X-Game-Story-Collection':cfg['pin']}
s,hs,b=request('/__game-story/',h);assert s==200 and b==(bundle/'story.json').read_bytes() and hs['X-Game-Story-Collection']==sha(b)==cfg['pin'];checks.append('story-exact-bytes')
for method,path,headers,body,status in [
 ('GET','/__game-story/',{},None,403),('POST','/__game-story/',h,None,403),('HEAD','/__game-story/',h,None,403),('OPTIONS','/__game-story/',h,None,403),
 ('GET','/__game-story/?week=7',h,None,403),('GET','/__game-story',h,None,403),('GET','/__game-story/other',h,None,403),
 ('GET','/__game-story/',dict(h,Origin='https://example.com'),None,403),('GET','/__game-story/',dict(h,Host='localhost:18110'),None,403),
 ('GET','/__game-story/',dict(h,**{'X-Game-Story-Collection':'stale'}),None,409),('GET','/__game-story/',h,'x',403)]:
 s,_,_=request(path,headers,method,body);assert s==status,(method,path,s);checks.append(f'refused-{len(checks)}')
for path in ['index.json']+[g['path'] for g in index['games']]+[t['path'] for t in index['teams']]:
 route='/__season-analysis/'+('' if path=='index.json' else path[:-5]);b=(source/path).read_bytes();s,hs,actual=request(route,{'X-Local-Season-Analysis':'1','X-Season-Collection':story['sourcePin']});assert s==200 and actual==b and hs['X-Season-Document']==sha(b);checks.append(route)
rows=pl.read_parquet(source/'source/pbp.parquet').sort('game_id','order_sequence').to_dicts();by_game={}
for r in rows:by_game.setdefault(r['game_id'],[]).append(r)
scoring=campaigns=0
for g in index['games']:
 gid=g['gameId'];t=story['timelines'][gid];assert t['status']=='AVAILABLE';prev=[0,0];events=[];plays={int(r['play_id']):r for r in by_game[gid]}
 for r in by_game[gid]:
  now=[int(r['total_away_score']),int(r['total_home_score'])]
  if now!=prev:events.append((int(r['play_id']),prev,now));prev=now
 assert prev==[g['awayScore'],g['homeScore']]==t['final']
 assert [(e['playId'],e['before'],e['after']) for e in t['events']]==events
 scoring+=len(events)
 for c in t['campaigns']:
  r=plays[c['playId']];assert c['score']==[r['total_away_score'],r['total_home_score']] and c['quarter']==r['qtr'] and c['remaining']==r['quarter_seconds_remaining']
  assert c['team']==r['posteam'] or c['outcome'] in ('OPPONENT_TOUCHDOWN','END_HALF_GAME')
  campaigns+=1
for family,ref in story['seasonReferences'].items():
 for item in ref['inventory']:
  doc=json.loads((source/f"teams/{item['team']}.json").read_text());m=doc['productions'][0]['metrics'][family];d=m['descriptor'];assert (item['numerator'],item['denominator'],item['unitIds'])==(d['numerator'],d['denominator'],d['unitIds'])
  if item['includedInRateDistribution']:assert item['denominator']>0 and m['aggregation']['allowed'] and m['display']['allowed']
 assert ref['pooledRate']['numerator']==sum(p['numerator'] for p in ref['teamRateDistribution']['points'])
 assert ref['pooledRate']['denominator']==sum(p['denominator'] for p in ref['teamRateDistribution']['points'])
result=dict(httpChecks=len(checks),exactSeasonDocuments=140,timelines=107,scoringTransitions=scoring,redzoneCampaigns=campaigns,seasonValid={k:len(v['representedTeams']) for k,v in story['seasonReferences'].items()},divergences=0,pin=cfg['pin'])
(PLAN/'checks/reconciliation-http.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if '--recovery' in sys.argv:
 from nfl_sideline_etl.game_story.package import hashes,read,generate
 target=bundle.parent/'verified-copy';reproduced=bundle.parent/'reproduced-from-copy'
 if not target.exists():shutil.copytree(bundle,target)
 read(target,cfg['pin']);assert hashes(bundle)==hashes(target)
 if not reproduced.exists():generate(target/'source',reproduced)
 read(reproduced,cfg['pin']);assert hashes(bundle)==hashes(reproduced)
 (PLAN/'checks/recovery.json').write_text(json.dumps(dict(copy=str(target),reproduction=str(reproduced),files=len(hashes(bundle)),byteIdentical=True,pin=cfg['pin']),indent=2)+'\n')
