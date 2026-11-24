from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,hashlib
here=Path(__file__).resolve().parent
root=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle');source=root/'source/matchups'
marker=json.loads((root/'COMPLETED.json').read_bytes())
assert marker['bundleId']=='sha256:8971d767b6ec0557465aeb65aeb00533fd10255a62f4b916954b3854daa15cef'
for name,h in marker['files'].items():assert 'sha256:'+hashlib.sha256((root/name).read_bytes()).hexdigest()==h,name
result={};outcomes=Counter()
for e in json.loads((source/'index.json').read_bytes())['games']:
 d=json.loads((source/e['path']).read_bytes());families={}
 for name,r in d['leagueReferences'].items():
  points=r['teamRateDistribution']['points'];values={p['team']:Fraction(p['numerator'],p['denominator']) for p in points}
  positions={team:1+sum(other>value for other in values.values()) for team,value in values.items()}
  assert len(values)==len(points) and len(r['inventory'])==32
  assert r['pooledRate']['numerator']==sum(p['numerator'] for p in points) and r['pooledRate']['denominator']==sum(p['denominator'] for p in points)
  families[name]=dict(positions=positions,withoutRate={p['team']:p['status'] for p in r['teamsWithoutRate']},n=len(points),pooled=r['pooledRate'])
 for p in d['productions']:
  for c in p['redZoneCampaigns']:outcomes[c['outcome']]+=1
 result[e['gameId']]=families
assert result['2026_01_NE_SEA']['third']['positions']['NE']==21 and result['2026_01_NE_SEA']['third']['positions']['SEA']==29
assert 'ATL' not in result['2026_01_ATL_PIT']['redZone']['positions']
(here/'checks/representation.json').write_text(json.dumps(dict(rule='broadcast-observed-rate-position-1.0.0',oracle='Python Fraction; count all strictly greater rates independently of frontend sorting',games=result,campaignOutcomes=outcomes,sourceFilesVerified=len(marker['files'])),indent=2)+'\n')
print('PASS: independent positions for 32 games × 2 families; original pooled rates and 208 campaigns; immutable files verified')
