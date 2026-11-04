"""Offline preservation proof and independent reconciliation of browser DOM receipts."""
from pathlib import Path
import hashlib,json,math,subprocess,urllib.parse
ROOT=Path(__file__).resolve().parents[3]
DOC=Path(__file__).parent
BASE='8e98296dd9352b5ea51ea69b2be67ea0f163f473'
REF=Path('/Users/pedrocollet/.codex/worktrees/qb-risk-lab-v1/NFL Sideline')
APPROVED=Path('/Users/pedrocollet/.codex/worktrees/broadcast-score-curve-v2/NFL Sideline')
APPROVED_HEAD='5b38f04e559bad5fc1b4ef25116cc0afb93293d9'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def files(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file()}
def write(name,obj):(DOC/'evidence'/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
before=json.loads((DOC/'evidence/inputs-before.json').read_text());store=Path(before['store']);package=store/'packages'/before['active']['packageId']
for path,h in before['files'].items():assert sha(ROOT/'docs/plans/qb-risk-temporal-calibration-v2/evidence/frozen/M3.json' if path=='model' else store/path)==h,path
assert git(REF,'rev-parse','HEAD')==BASE and not git(REF,'status','--porcelain')
assert git(APPROVED,'rev-parse','HEAD')==APPROVED_HEAD and not git(APPROVED,'status','--porcelain')
protected=['research','etl-pipeline','core-api','supabase','web-ui/src','web-ui/public','web-ui/vercel.json','web-ui/vite.config.ts','Spec.md','docs/static-snapshot-contract.md','docs/plans/qb-risk-lab-v1','docs/plans/qb-risk-temporal-calibration-v2','docs/plans/qb-interception-risk-baseline-v1','docs/plans/broadcast-final-audit-v1']
assert not git(ROOT,'diff',BASE,'--',*protected)
source=json.loads((package/'sources.json').read_text());pinned=store/'runs/20261104T144706530236Z'
for row in source['files']:assert sha(pinned/row['path'])==row['sha256']
assert sha(DOC/'captures/before-v1.png')==sha(REF/'docs/plans/qb-risk-lab-v1/captures/comparison-desktop.png')
assert files(ROOT/'web-ui/dist')==files(REF/'web-ui/dist')
newroutes=json.loads((ROOT/'web-ui/risk-lab-dist/local-routes.json').read_text());oldbuild=store/'recovery/20261104-v1/web-ui/risk-lab-dist';oldroutes=json.loads((oldbuild/'local-routes.json').read_text());assert newroutes==oldroutes
for item in newroutes['routes'].values():assert sha(ROOT/'web-ui/risk-lab-dist'/item['file'])==item['sha256']==sha(oldbuild/item['file'])
index=json.loads((package/'index.json').read_text());people={p['id']:p for p in index['players']};details={p['id']:json.loads((package/'players'/f"{p['id']}.json").read_text()) for p in index['players']}
def counts(ident,period):
 plays=[p for p in details[ident]['plays'] if period=='all' or p['week']==int(period)]
 return dict(passes=len(plays),games=len({p['gameId'] for p in plays}),classified=sum(p['worthy'] for p in plays),expected=sum(p['probability'] for p in plays),interceptions=sum(p['interception'] for p in plays))
cases=json.loads((DOC/'evidence/browser-cases.json').read_text());total_points=0
for case in cases:
 query=urllib.parse.parse_qs(urllib.parse.urlparse(case['url']).query);period=query.get('period',['all'])[0];scale=query.get('scale',['total'])[0];scope=query.get('position',['qb'])[0]
 assert case['period']==period
 assert case['scale']==('Por 100 passes' if scale=='per100' else 'Totais')
 expected={ident:counts(ident,period) for ident,p in people.items() if scope=='all' or p['positionClass']==scope};expected={ident:c for ident,c in expected.items() if c['passes']}
 assert set(p['id'] for p in case['points'])==set(expected),(case['name'],'population')
 line=case['line']
 if line:
  size=line['x2']-line['x1'];assert math.isclose(size,line['y1']-line['y2'],abs_tol=1e-10)
  for point in case['points']:
   c=expected[point['id']];den=c['passes']/100 if scale=='per100' else 1;x=c['expected']/den;y=c['classified']/den
   assert math.isclose(point['x'],x,abs_tol=1e-10) and math.isclose(point['y'],y,abs_tol=1e-10)
   assert math.isclose(point['cx'],line['x1']+x/line['domain']*size,abs_tol=1e-8)
   assert math.isclose(point['cy'],line['y1']-y/line['domain']*size,abs_tol=1e-8)
   assert 0<=x<=line['domain'] and 0<=y<=line['domain']
   total_points+=1
 assert case['layout']['scroll']==case['layout']['client'],(case['name'],'horizontal overflow')
 rows=case['roster'];assert len({r['id'] for r in rows})==len(rows)
 if 'group' not in query:assert {r['id'] for r in rows}==set(expected)
 else:assert {r['id'] for r in rows}.issubset(expected)
 for row in rows:assert people[row['id']]['name'] in row['label']
 selected=query.get('player',[None])[0]
 if selected:
  c=counts(selected,period);actual=case['selected'];assert actual['name']==people[selected]['name'];assert f"{c['passes']} passes" in actual['support'] and str(c['games']) in actual['support']
  for m in actual['metrics']:
   if not c['passes']:assert m['value']=='—'
   else:assert abs(float(m['value'].replace(',','.'))-c[m['metric']])<=.00500001,(case['name'],m)
write('preservation.json',dict(status='PASS',base=BASE,referenceCheckoutClean=True,approvedSiteHead=APPROVED_HEAD,approvedSiteCheckoutClean=True,packageId=before['active']['packageId'],modelSha256=before['files']['model'],unchangedPackageAndPointerFiles=len(before['files'])-1,unchangedRawSources=len(source['files']),unchangedCompiledDataDocuments=len(newroutes['routes']),publicBuildByteIdentical=True,protectedPathsUnchanged=protected,acquisition=False,training=False,recalibration=False))
write('browser-reconciliation.json',dict(status='PASS',cases=len(cases),pointChecks=total_points,source='Independent sums from per-pass frozen JSON evidence; not frontend aggregation',tolerances=dict(coordinates=1e-10,svgProjection=1e-8,displayRounding=.00500001),sameUnitAndDomainBothAxes=True,noCoordinateJitter=True,interceptionsKeptSeparate=True,zeroPassPresentation='em dash; no rate',allCasesWithoutPageHorizontalOverflow=True))
report=json.loads((DOC/'checks/frontend.json').read_text());assert report['numFailedTests']==0 and report['numPendingTests']==0
legacy='web-ui/src/components/visual-preparation-regressions.test.tsx';assert git(ROOT,'show',BASE+':'+legacy)==(ROOT/legacy).read_text().strip();xfails=(ROOT/legacy).read_text().count('it.fails(');assert xfails==5
write('checks.json',dict(vitestPassedIncludingExpectedFailures=report['numPassedTests'],ordinaryPassed=report['numPassedTests']-xfails,expectedFailures=xfails,skipped=report['numPendingTests'],failed=report['numFailedTests'],configuredLocalSources=True,legacyExpectationsUnchanged=True))
print(json.dumps(dict(status='PASS',cases=len(cases),points=total_points,preservedDataDocuments=len(newroutes['routes']),tests=report['numPassedTests'],expectedFailures=xfails),indent=2))
