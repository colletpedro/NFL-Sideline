"""Reconcile saved browser DOM receipts against immutable pass-derived packages, offline."""
import argparse,math,xml.etree.ElementTree as ET
from pathlib import Path
from package import read,write,verify_package,verify_files,sha,DEFAULT,M3_STORE,ROOT,MODEL_SHA,SCIENTIFIC

def verify(evidence,store,m3_store):
 evidence=Path(evidence);store=Path(store);m3_store=Path(m3_store);receipt=read(evidence/'browser-reconciliation.json')
 mb=m3_store/'packages'/receipt['m3PackageId'];bb=store/'packages'/receipt['b2PackageId'];b=verify_package(bb);m=read(mb/'index.json');verify_files(mb,read(mb/'integrity.json')['files'])
 assert b['model']['sha256']==MODEL_SHA and b['scientific']['consumerIndexSha256']==sha(SCIENTIFIC/'application-complete/consumer/index.json')
 views=read(evidence/'browser-chart-periods.json');tested=0
 for view in views:
  source=m if view['question']=='passes' else b;expected={}
  for player in source['players']:
   groups=[player] if view['period']=='all' else [g for g in player['byGame'] if g['week']==int(view['period'])]
   n=sum(g['passes'] if view['question']=='passes' else g['eligiblePasses'] for g in groups)
   x=math.fsum(g['expected'] if view['question']=='passes' else g['expectedInterceptions'] for g in groups)
   y=sum(g['observed'] if view['question']=='passes' else g['observedInterceptions'] for g in groups)
   if n:expected[player['id']]=(x/(n/100 if view['scale']=='per100' else 1),y/(n/100 if view['scale']=='per100' else 1))
  assert {p['id'] for p in view['points']}==set(expected)
  line=ET.fromstring(view['equality']);a={k:float(v) for k,v in line.attrib.items() if k in ['x1','x2','y1','y2','data-domain']}
  for point in view['points']:
   x,y=expected[point['id']];assert math.isclose(point['x'],x,abs_tol=1e-10) and math.isclose(point['y'],y,abs_tol=1e-10)
   assert math.isclose(point['cx'],a['x1']+point['x']/a['data-domain']*(a['x2']-a['x1']),abs_tol=1e-9)
   assert math.isclose(point['cy'],a['y1']-point['y']/a['data-domain']*(a['y1']-a['y2']),abs_tol=1e-9);tested+=1
 players={p['id']:p for p in b['players']};cases=read(evidence/'browser-real-cases.json')
 for case in cases:
  player=players[case['caseId']];assert math.isclose(case['expectedTotal'],player['expectedInterceptions'],abs_tol=1e-10)
  for group,key in [('classified','expectedFromClassified'),('not-classified','expectedFromNotClassified')]:assert math.isclose(next(x for x in case['contributions'] if x['group']==group)['contribution'],player[key],abs_tol=1e-10)
  assert case['contributions'][0]['passes']==player['interceptionWorthyPasses']
  assert case['contributions'][1]['passes']==player['eligiblePasses']-player['interceptionWorthyPasses']
 assert next(c for c in cases if c['caseName']=='Aaron Rodgers')['crosses'][3]['count']==5
 build=ROOT/'web-ui/risk-outcomes-dist';routes=read(build/'local-routes.json')['routes']
 for path,info in routes.items():assert sha(build/info['file'])==info['sha256']
 return dict(passed=True,offline=True,browserViews=len(views),browserPoints=tested,allCoordinatesAndIdentityProjection=True,
  realCases=len(cases),allContributionsVerified=True,m3PackageId=m['packageId'],b2PackageId=b['packageId'],frozenGetDocuments=len(routes),
  note='Saved browser observations are frozen evidence, not a fresh browser run. Vitest additionally renders every player-period calculation from pinned sources.')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',default=str(ROOT/'docs/plans/qb-risk-outcomes-lab-v1/evidence'));a.add_argument('--store',default=str(DEFAULT));a.add_argument('--m3-store',default=str(M3_STORE));a.add_argument('--out',required=True);v=a.parse_args();r=verify(v.evidence,v.store,v.m3_store);write(v.out,r);print(r)
