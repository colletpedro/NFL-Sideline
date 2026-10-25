"""Independent audit: raw PBP, original ledger/aggregates and Fraction; no new projector/reader import."""
import argparse
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction
import hashlib
import json
from math import isfinite
from pathlib import Path
import polars as pl
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.bundle
hash_=lambda b:'sha256:'+hashlib.sha256(b).hexdigest()
marker=json.loads((root/'COMPLETED.json').read_bytes())
assert all(hash_((root/n).read_bytes())==h for n,h in marker['files'].items())
index=json.loads((root/'index.json').read_bytes());assert marker['bundleId']==hash_((root/'index.json').read_bytes())
src=root/'source/matchups';si=json.loads((src/'index.json').read_bytes());assert hash_((src/'index.json').read_bytes())==index['sourceCollection']
sit=json.loads((src/'sources/situational/situational.json').read_bytes());ledger=json.loads((src/'sources/situational/ledger.json').read_bytes());obs=json.loads((src/'sources/observations/observations.json').read_bytes())
rows=pl.read_parquet(src/'sources/situational/pbp.parquet').sort('game_id','order_sequence').to_dicts();by_play={f"{r['game_id']}:{int(r['play_id'])}":r for r in rows}
report=dict(teams=[],epa=0,perspectives=0,uniqueThirdUnits=set(),uniqueCampaigns=set(),rounding={},sourcePin=index['sourceCollection'])
original_s={d['id']:d for d in sit['documents']}
for entry in index['teams']:
 doc=json.loads((root/entry['path']).read_bytes());team=entry['team'];assert hash_((root/entry['path']).read_bytes())==entry['documentHash']
 games=[g for g in si['games'] if team in (g['away'],g['home'])];games.sort(key=lambda g:g['week']);ids=[g['gameId'] for g in games]
 assert len(games)==2 and [g['week'] for g in games]==[1,2] and [g['gameId'] for g in doc['games']]==ids==entry['gameIds']
 assert [x['perspective'] for x in doc['productions']]==['off','def']
 for prod in doc['productions']:
  role=prod['perspective'];field='posteam' if role=='off' else 'defteam';offkey='offense' if role=='off' else 'defense'
  old=original_s[f'{team}/{role}/1-2'];assert {g['gameId'] for g in old['games']}==set(ids)
  for foundation in ('general','classified_pass','classified_rush'):
   e=next(e for e in prod['epa'] if e['foundation']==foundation)
   eligible=[r for r in rows if r['game_id'] in ids and r[field]==team and r['play_type'] in ('pass','run') and all(r[c]==0 for c in ('qb_kneel','qb_spike','play_deleted','special_teams_play','two_point_attempt')) and (foundation=='general' or r['play_type']==('pass' if foundation=='classified_pass' else 'run'))]
   finite=[r for r in eligible if r['epa'] is not None and isfinite(r['epa'])];total=sum((Fraction(str(r['epa'])) for r in finite),Fraction())
   legacy=next(o for o in obs if o['subject']==dict(team=team,role=role,foundation=foundation) and o['request']['season']==2026 and o['request']['phase']=='REG' and o['request']['period']['weeks']==[1,2])
   assert Fraction(e['descriptor']['numerator'])==total==Fraction(legacy['totals']['epaSum']) and e['descriptor']['denominator']==len(finite)==legacy['totals']['epaN']
   keys=lambda rs:{f"{r['game_id']}:{int(r['play_id'])}" for r in rs}
   assert set(e['eligibleUnitIds'])==keys(eligible) and len(e['eligibleUnitIds'])==len(eligible)
   assert set(e['finiteEpaUnitIds'])==keys(finite) and len(e['finiteEpaUnitIds'])==len(finite)
   assert e['calculatedTotals']['epaMissingN']==sum(r['epa'] is None for r in eligible)
   assert e['calculatedTotals']['epaNonfiniteN']==sum(r['epa'] is not None and not isfinite(r['epa']) for r in eligible)
   assert e['originalObservation']==legacy and e['descriptor']['sourceHash']==hash_((src/'sources/situational/pbp.parquet').read_bytes()) and e['descriptor']['sourceColumn']=='epa'
   assert {k:v for k,v in e['descriptor']['definition'].items() if k!='foundation'}==legacy['definition']
   assert e['descriptor']['definition']['foundation']==foundation
   with localcontext() as ctx:
    ctx.prec=100;v=(Decimal(total.numerator)/Decimal(total.denominator)/len(finite)).quantize(Decimal('.001'),rounding=ROUND_HALF_UP)
   report['rounding'][team+'/'+role+'/'+foundation]=(('−' if total<0 else '+')+'<0,001') if v==0 and total else ('−' if v<0 else '+' if total else '')+format(abs(v),'.3f').replace('.',',')
   report['epa']+=1
  for family,units_key,ledger_key in [('third','thirdAttempts','third'),('redZone','redZoneCampaigns','campaigns')]:
   expected=[u for u in ledger[ledger_key] if u['included'] and u['gameId'] in ids and u[offkey]==team]
   actual=prod[units_key];m=prod['metrics'][family];n=sum(u['converted'] if family=='third' else u['outcome']=='TOUCHDOWN' for u in expected);den=len(expected)
   assert len({u['id'] for u in actual})==len(actual)==den and {u['id'] for u in actual}=={u['id'] for u in expected}==set(old[family]['unitIds'])
   assert (m['descriptor']['numerator'],m['descriptor']['denominator'])==(n,den)==(old[family]['numerator'],old[family]['denominator'])
   assert m['descriptor']['status']==old[family]['status']==('AVAILABLE' if den else 'NO_OPPORTUNITIES')
   assert m['display']['allowed'] and m['aggregation']['allowed'] and m['originalAggregate']==old[family]
   lookup={u['id']:u for u in expected}
   assert all(all(u[k]==v for k,v in lookup[u['id']].items()) for u in actual)
   if family=='third':
    for u in actual:
     raw=by_play[u['id']];assert u['converted']==int(raw['third_down_converted']) and u['yardsToGo']==raw['ydstogo'] and u['kind']==('pass' if raw['play_type']=='pass' else 'run')
    for b in ('short','medium','long','unknown'):
     for k in ('pass','run'):
      us=[u for u in expected if u['distance']==b and u['kind']==k];joint=next(j for j in prod['thirdDistanceByType'] if j['distance']==b and j['kind']==k)
      assert (joint['numerator'],joint['denominator'],set(joint['unitIds']))==(sum(u['converted'] for u in us),len(us),{u['id'] for u in us})
    report['uniqueThirdUnits'].update(u['id'] for u in actual)
   else:
    assert Counter(u['outcome'] for u in actual)==old[family]['outcomes']
    for u in actual:
     assert {f"{r['game_id']}:{int(r['play_id'])}" for r in u['entryEvidence']}==set(u['entryPlayIds'])
     assert all(0<r['yardline_100']<=20 and by_play[f"{r['game_id']}:{int(r['play_id'])}"]['desc']==r['desc'] for r in u['entryEvidence'])
     assert u['outcomeEvidence']
     for evidence in u['entryEvidence']+u['outcomeEvidence']:
      raw=by_play[f"{evidence['game_id']}:{int(evidence['play_id'])}"];assert all(raw[k]==v for k,v in evidence.items() if k in raw)
     assert u['chronologicalPlayIds']==sorted(u['playIds'],key=lambda x:by_play[x]['order_sequence'])
    report['uniqueCampaigns'].update(u['id'] for u in actual)
  assert all(e['aggregation']['allowed'] for e in prod['epa']) and all(x=='UNKNOWN' for x in doc['guarantees'].values())
  report['perspectives']+=1
 report['teams'].append(dict(team=team,gameIds=ids,opponents=entry['opponents'],offRedZone=doc['productions'][0]['metrics']['redZone']['descriptor']['status']))
assert len(report['teams'])==32 and report['perspectives']==64 and report['epa']==192
report['uniqueThirdUnits']=len(report['uniqueThirdUnits']);report['uniqueCampaigns']=len(report['uniqueCampaigns'])
assert (report['uniqueThirdUnits'],report['uniqueCampaigns'])==(787,208)
report.update(pin=marker['bundleId'],independentOfProjector=True,allOriginalAggregatesMatched=True)
a.output.write_text(json.dumps(report,indent=2)+'\n');print('Independent audit PASS: 32 teams, 64 perspectives, 192 EPA, 787 third units and 208 campaigns; exact originals matched.')
