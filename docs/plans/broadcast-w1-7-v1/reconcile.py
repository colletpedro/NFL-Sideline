"""Independent columnar/raw reconciliation; no season projector imported."""
from collections import Counter,defaultdict
from fractions import Fraction
import hashlib,json,math
from pathlib import Path
import polars as pl
HERE=Path(__file__).resolve().parent
ROOT=Path(json.loads((HERE/'source-config.json').read_text())['bundle'])
load=lambda p:json.loads(p.read_text())
hash_=lambda b:'sha256:'+hashlib.sha256(b).hexdigest()
i=load(ROOT/'index.json');marker=load(ROOT/'COMPLETED.json');assert hash_((ROOT/'index.json').read_bytes())==marker['bundleId']
for name,h in marker['files'].items():assert hash_((ROOT/name).read_bytes())==h,name
raw=pl.read_parquet(ROOT/'source/pbp.parquet').filter((pl.col('season')==2026)&(pl.col('season_type')=='REG')&pl.col('week').is_between(1,7)).sort('game_id','order_sequence')
rs=raw.to_dicts();by_game=defaultdict(list)
for r in rs:by_game[r['game_id']].append(r)
assert len({(r['game_id'],r['play_id']) for r in rs})==len(rs)
base=raw.filter(pl.col('play_type').is_in(['pass','run'])&(pl.col('qb_kneel')==0)&(pl.col('qb_spike')==0)&(pl.col('play_deleted')==0)&(pl.col('special_teams_play')==0)&(pl.col('two_point_attempt')==0))
keys=lambda us:[f"{r['game_id']}:{int(r['play_id'])}" for r in us]
finite=lambda us:[r for r in us if r['epa'] is not None and math.isfinite(r['epa'])]
sum_=lambda us:sum((Fraction(str(r['epa'])) for r in finite(us)),Fraction())
third_ok=lambda r:r['down']==3 and r['play_deleted']==0 and r['extra_point_attempt']==0 and r['two_point_attempt']==0 and r['play_type'] in ('pass','run') and all(r[c]==0 for c in ('qb_kneel','qb_spike','aborted_play')) and (r['third_down_converted'],r['third_down_failed']) in ((1,0),(0,1))
scr=lambda r:r['down'] in (1,2,3,4) and r['play_deleted']==0 and r['extra_point_attempt']==0 and r['two_point_attempt']==0 and r['play_type'] in ('pass','run','qb_kneel','qb_spike','field_goal','punt','no_play') and (r['play_type']!='no_play' or r['penalty']==1)
ambiguous=[r for r in rs if r['down']==3 and r['play_type'] in ('pass','run') and all(r[c]==0 for c in ('play_deleted','extra_point_attempt','two_point_attempt','qb_kneel','qb_spike','aborted_play')) and (r['third_down_converted'],r['third_down_failed']) not in ((1,0),(0,1))]
def check_epa(e,rows):
 us=[r for r in rows if e['foundation']=='general' or r['play_type']==('pass' if e['foundation']=='classified_pass' else 'run')];vs=finite(us);d=e['descriptor']
 assert set(e['eligibleUnitIds'])==set(keys(us)) and set(e['finiteEpaUnitIds'])==set(keys(vs))
 assert Fraction(str(d['numerator']))==sum_(us) and d['denominator']==len(vs)
 assert Fraction(e['originalObservation']['totals']['epaSum'])==sum_(us)
 return 1

def check_rz(p,rows):
 us=[r for r in rows if r['yardline_100'] is not None and 0<r['yardline_100']<=20];vs=finite(us);s=sum_(us)
 assert set(u['id'] for u in p['units'])==set(keys(us)) and p['eligibleN']==len(us) and p['validN']==len(vs)
 assert Fraction(int(p['sum']['numerator']),int(p['sum']['denominator']))==s
 if vs:assert Fraction(int(p['mean']['numerator']),int(p['mean']['denominator']))==s/len(vs)
 else:assert p['mean'] is None
 return 1
checks=Counter();states=Counter();weekly={};docs={}
for g in i['games']:
 d=load(ROOT/g['path']);docs[g['gameId']]=d;gr=by_game[g['gameId']];assert gr
 assert all((r['away_team'],r['home_team'],r['week'])==(g['away'],g['home'],g['week']) for r in gr)
 for p in d['productions']:
  selected=base.filter((pl.col('game_id')==g['gameId'])&(pl.col('posteam')==p['offense'])).to_dicts()
  for e in p['epa']:checks['gameEpa']+=check_epa(e,selected)
  thirds=[r for r in gr if r['posteam']==p['offense'] and third_ok(r)];m=p['metrics']['third']['descriptor']
  assert set(keys(thirds))==set(m['unitIds']) and len(thirds)==m['denominator'] and sum(r['third_down_converted'] for r in thirds)==m['numerator']
  bad=[r for r in ambiguous if r['game_id']==g['gameId'] and r['posteam']==p['offense']]
  assert (m['status']=='INSUFFICIENT')==bool(bad)
  if bad:assert not p['metrics']['third']['display']['allowed']
  checks['thirdProductions']+=1;states['third:'+m['status']]+=1
  drives=defaultdict(list)
  for r in gr:drives[r['fixed_drive']].append(r)
  observed=[]
  for drive,dr in drives.items():
   live=[r for r in dr if scr(r)]
   if not live or live[0]['posteam']!=p['offense']:continue
   entries=[r for r in live if r['yardline_100'] is not None and 0<r['yardline_100']<=20]
   if entries:
    u=next(u for u in p['redZoneCampaigns'] if u['id']==f"{g['gameId']}:drive:{drive}")
    assert set(u['entryPlayIds'])==set(keys(entries)) and u['chronologicalPlayIds']==keys(dr)
    assert u['outcomeEvidence'] and all(e['game_id']==g['gameId'] for e in u['outcomeEvidence'])
    outcome=dr[0]['fixed_drive_result'];assert all(r['fixed_drive_result']==outcome for r in dr)
    assert (u['outcome']=='TOUCHDOWN')==(outcome=='Touchdown')
    observed.append(u)
  rz=p['metrics']['redZone']['descriptor'];assert rz['denominator']==len(observed) and rz['numerator']==sum(u['outcome']=='TOUCHDOWN' for u in observed)
  checks['campaignProductions']+=1;states['redZone:'+rz['status']]+=1
  rp=next(z for z in d['redzoneEpa']['productions'] if z['offense']==p['offense']);checks['gameRedzoneEpa']+=check_rz(rp,selected)
 for family,r in d['leagueReferences'].items():
  active=next(w['participants'] for w in i['weekInventory'] if w['week']==g['week']);assert set(r['candidateTeams'])==set(active)
  assert set(r['representedTeams']).isdisjoint(set(r['byeTeams']))
  pts=r['teamRateDistribution']['points'];assert len({p['team'] for p in pts})==len(pts)
  assert r['pooledRate']['numerator']==sum(p['numerator'] for p in pts) and r['pooledRate']['denominator']==sum(p['denominator'] for p in pts)
  if g['week'] not in weekly:weekly[g['week']]={}
  weekly[g['week']][family]=dict(r['pooledRate'],withRate=len(pts),withoutRate=[p['team'] for p in r['teamsWithoutRate']],byes=r['byeTeams'])
for t in i['teams']:
 d=load(ROOT/t['path']);members=[g for g in i['games'] if t['team'] in (g['away'],g['home'])];assert len(members) in (6,7) and t['gameIds']==[g['gameId'] for g in members]
 assert set(d['byeWeeks'])==set(range(1,8))-{g['week'] for g in members}
 for p in d['productions']:
  col='posteam' if p['perspective']=='off' else 'defteam';selected=base.filter(pl.col(col)==t['team']).to_dicts()
  for e in p['epa']:checks['teamEpa']+=check_epa(e,selected)
  for family in ('third','redZone'):
   m=p['metrics'][family];components=m['components'];all_ids=[x for c in components for x in c['descriptor']['unitIds']]
   assert len(all_ids)==len(set(all_ids)) and set(m['descriptor']['unitIds'])==set(all_ids)
   if any(c['descriptor']['status']=='INSUFFICIENT' for c in components):assert m['descriptor']['status']=='INSUFFICIENT' and m['descriptor']['denominator'] is None and not m['aggregation']['allowed']
   else:assert m['descriptor']['denominator']==sum(c['descriptor']['denominator'] for c in components) and m['descriptor']['numerator']==sum(c['descriptor']['numerator'] for c in components)
   checks['teamSituational']+=1
  rp=next(z for z in d['redzoneEpa']['productions'] if z['perspective']==p['perspective']);checks['teamRedzoneEpa']+=check_rz(rp,selected)
old=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle/source/matchups')
o=pl.read_parquet(old/'sources/situational/pbp.parquet').sort('game_id','order_sequence');n=raw.filter(pl.col('week')<=2)
changed_columns=[c for c in o.columns if not o[c].equals(n[c])];value_changes=[]
for g in i['games']:
 if g['week']>2:continue
 prior=load(old/f"games/{g['gameId']}.json");now=docs[g['gameId']]
 for a,b in zip(prior['productions'],now['productions']):
  for f in ('third','redZone'):
   x,y=a['metrics'][f]['descriptor'],b['metrics'][f]['descriptor']
   if any(x[k]!=y[k] for k in ('status','numerator','denominator','unitIds')):value_changes.append(dict(game=g['gameId'],team=a['offense'],family=f))
  for a_e,b_e in zip(a['epa'],b['epa']):
   if any(Fraction(str(a_e['descriptor'][k]))!=Fraction(str(b_e['descriptor'][k])) for k in ('numerator','denominator')):value_changes.append(dict(game=g['gameId'],team=a['offense'],family=a_e['foundation']))
report=dict(pin=marker['bundleId'],games=len(i['games']),teams=len(i['teams']),rows=len(rs),checks=dict(checks),states=dict(states),weekly=weekly,ambiguousThirds=[{k:r[k] for k in ('game_id','play_id','posteam','third_down_converted','third_down_failed','desc')} for r in ambiguous],revisionW12=dict(oldRows=o.height,newRows=n.height,changedColumns=changed_columns,metricChanges=value_changes),differences=0)
(HERE/'checks/reconciliation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('weekly','ambiguousThirds')},ensure_ascii=False))
