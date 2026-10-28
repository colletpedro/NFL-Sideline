"""Independent source/HTTP reconciliation of the presentation join; no artifacts are written."""
import http.client,json
from collections import Counter
from fractions import Fraction
from pathlib import Path
import polars as pl
from nfl_sideline_etl.score_curve.package import read

PLAN=Path(__file__).resolve().parent
ROOT=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-score-curve-v2/20261027-v1/bundle')
PIN='sha256:86fd64d2e3ac628cf8a99ca1befe95d4528e8cf7acba1f4937235fe9fb3f7ecd'
b,_=read(ROOT,PIN)
season=ROOT/'source/source'
index=json.loads((season/'index.json').read_bytes())
raw={f"{r['game_id']}:{int(r['play_id'])}":r for r in pl.read_parquet(season/'source/pbp.parquet').to_dicts()}
counters=Counter();reentries=[];example=None
for g in index['games']:
 d=json.loads((season/g['path']).read_bytes())
 for p,r in zip(d['productions'],d['redzoneEpa']['productions']):
  joined={u['id']:[] for u in r['units']};subtotal=Fraction()
  for c in p['redZoneCampaigns']:
   counters['campaigns']+=1
   for e in c['entryEvidence']:
    k=f"{e['game_id']}:{int(e['play_id'])}";row=raw[k]
    assert e['desc']==row['desc'] and e['down']==row['down'] and e['ydstogo']==row['ydstogo'] and e['qtr']==row['qtr'] and e['yardline_100']==row['yardline_100']
    remain=e['game_seconds_remaining']-(4-e['qtr'])*900 if e['qtr']<=4 else e['game_seconds_remaining']
    assert remain==row['quarter_seconds_remaining'];counters['contexts']+=1
    if k in joined:joined[k].append(c['id'])
   entered=False;outside=False
   for k in c['chronologicalPlayIds']:
    row=raw[k]
    if row['play_deleted']!=0 or row['posteam']!=c['offense'] or row['down'] is None:continue
    y=row['yardline_100']
    if y is None:continue
    if 0<y<=20:
     if entered and outside:reentries.append(c['id']);break
     entered=True
    elif entered:outside=True
  assert all(len(cs)==1 for cs in joined.values())
  for u in r['units']:
   row=raw[u['id']];assert row['fixed_drive']==float(joined[u['id']][0].split(':')[-1])
   if u['epaStatus']=='VALID':assert Fraction(u['epa'])==Fraction(str(row['epa']));subtotal+=Fraction(u['epa'])
   counters['plays']+=1
  assert subtotal==Fraction(int(r['sum']['numerator']),int(r['sum']['denominator']))
  if r['mean']:assert subtotal/r['validN']==Fraction(int(r['mean']['numerator']),int(r['mean']['denominator']))
  if g['gameId']=='2026_07_CIN_BAL' and p['offense']=='BAL':
   unit=max((u for u in r['units'] if u['epaStatus']=='VALID'),key=lambda u:abs(Fraction(u['epa'])))
   assert unit['playId']==2836
   example={k:raw[unit['id']][k] for k in ['play_id','down','ydstogo','qtr','time','desc','epa','fixed_drive']}

def get(path,headers):
 c=http.client.HTTPConnection('127.0.0.1',18111,timeout=30);c.request('GET',path,headers=headers);r=c.getresponse();v=r.read();assert r.status==200;c.close();return v
assert get('/__curve-events/',{'X-Local-Curve-Events':'1','X-Curve-Collection':PIN})==b
story_pin=json.loads(b)['sourcePin'];story=(ROOT/'source/story.json').read_bytes()
assert get('/__game-story/',{'X-Local-Game-Story':'1','X-Game-Story-Collection':story_pin})==story
season_pin=json.loads(story)['sourcePin']
paths=['index.json']+[g['path'] for g in index['games']]+[t['path'] for t in index['teams']]
for p in paths:
 assert get('/__season-analysis/'+('' if p=='index.json' else p[:-5]),{'X-Local-Season-Analysis':'1','X-Season-Collection':season_pin})==(season/p).read_bytes()
assert counters['campaigns']==723 and counters['plays']==2096
result=dict(counts=dict(counters),reentryCampaigns=sorted(set(reentries)),example=example,divergences=0,httpExactResponses=len(paths)+2,pinsUnchanged=[PIN,story_pin,season_pin])
(PLAN/'checks/reconciliation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
