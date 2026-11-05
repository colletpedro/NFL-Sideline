"""Validate scientific B2 artifacts; project explicit outcome fields; atomic local activation."""
from pathlib import Path
import argparse,datetime,hashlib,json,math,os,re,shutil,tempfile

MODEL_SHA='ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8'
MODEL_ID='XINT-FTN-B2-v1-fit2025'
M3_SHA='38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6'
MAIN=Path('/Users/pedrocollet/Downloads/NFL Sideline')
SCIENTIFIC=MAIN/'editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1'
DEFAULT=MAIN/'editorial/local-artifacts/qb-risk-outcomes-lab-v1'
M3_STORE=MAIN/'editorial/local-artifacts/qb-risk-lab-v1'
ROOT=Path(__file__).resolve().parents[2]
def encoded(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()+b'\n'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_bytes(encoded(x))
def read(p):return json.loads(Path(p).read_text())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def near(a,b):return isinstance(a,(int,float)) and math.isfinite(a) and math.isclose(a,b,abs_tol=1e-10,rel_tol=1e-12)
def require(x,message):
 if not x:raise ValueError(message)
def verify_files(base,files):
 base=Path(base).resolve()
 for rel,h in files.items():
  p=(base/rel).resolve();require(p.is_relative_to(base),'Unsafe manifest path');require(sha(p)==h,'Scientific artifact hash mismatch: '+rel)
def aggregate(plays):
 n=len(plays);o=sum(p['observedInterception'] for p in plays);w=sum(p['ftnInterceptionWorthy'] for p in plays)
 e1=math.fsum(p['pInterceptionGivenFtn'] for p in plays if p['ftnInterceptionWorthy']);e0=math.fsum(p['pInterceptionGivenFtn'] for p in plays if not p['ftnInterceptionWorthy']);e=e1+e0
 return dict(eligiblePasses=n,games=len({p['gameId'] for p in plays}),interceptionWorthyPasses=w,observedInterceptions=o,expectedInterceptions=e,
  expectedFromClassified=e1,expectedFromNotClassified=e0,differenceInterceptions=o-e,differencePer100=100*(o-e)/n if n else None)
def validate_scientific(application,source_root):
 application=Path(application);source_root=Path(source_root)
 verify_files(application,read(application/'integrity.json')['files'])
 model=read(application/'model.json');fixed=read(application/'fixed.json');i=read(application/'consumer/index.json')
 require(sha(application/'model.json')==MODEL_SHA and fixed['model_sha256']==MODEL_SHA and i['model']['model_sha256']==MODEL_SHA,'B2 fixed model SHA mismatch')
 require(model['model_id']==MODEL_ID and model['target']=='interception' and model['risk_input']=='is_interception_worthy' and model['kind']=='B2' and model['train_years']==[2025],'B2 fixed model schema mismatch')
 require(near(model['groups']['1']['probability'],305/553) and near(model['groups']['0']['probability'],75/16805),'Fixed reference rates changed')
 require(i['schemaVersion']==1 and i['season']==2026 and i['packageKind']=='expected-observed-interceptions-research','Scientific consumer schema mismatch')
 sources=read(application/'sources.json')
 for row in sources['files']:
  path=(source_root/row['path']).resolve();require(path.is_relative_to(source_root.resolve()),'Unsafe source path')
  require(sha(path)==row['sha256'] and path.stat().st_size==row['bytes'],'Pinned source changed')
 return i,model,sources
def presentation(application,source_root,m3_store):
 application=Path(application);i,model,sources=validate_scientific(application,source_root)
 cov=i['coverage'];games={g['game_id']:dict(gameId=g['game_id'],week=g['week'],home=g['home'],away=g['away'],date=g['date'],passes=g['passes']) for g in cov['included']}
 require(len(games)==cov['included_games'] and cov['completed_games']==len(games)+len(cov['pending_games']),'Coverage does not reconcile')
 details={};players=[];all_plays=[];keys=set()
 for s in sorted(i['players'],key=lambda p:p['gsis_id']):
  ident=s['gsis_id'];require(re.fullmatch(r'00-\d{7}',ident),'Invalid GSIS');detail=read(application/f'consumer/players/{ident}.json')
  require(detail['gsis_id']==ident and detail['model_id']==MODEL_ID,'Scientific player identity mismatch');plays=[]
  for r in detail['plays']:
   require(r['season']==2026 and r['season_type']=='REG' and r['passer_player_id']==ident and r['game_id'] in games,'Scientific pass identity/coverage mismatch')
   require(r['is_interception_worthy'] in [0,1] and r['interception'] in [0,1] and isinstance(r['play_id'],(int,float)) and int(r['play_id'])==r['play_id'],'Missing/nonbinary target or FTN')
   key=f'{r["game_id"]}:{int(r["play_id"])}';require(key not in keys,'Duplicate pass key');keys.add(key)
   flag=bool(r['is_interception_worthy']);prob=r['p_interception_given_ftn'];require(near(prob,model['groups'][str(int(flag))]['probability']) and 0<prob<1,'Scientific B2 probability changed')
   game=games[r['game_id']];require(r['week']==game['week'] and r['game_date']==game['date'] and {r['posteam'],r['defteam']}=={game['home'],game['away']},'Pass game metadata mismatch')
   for c,low,high in [('down',1,4),('qtr',1,5),('ydstogo',0,100),('yardline_100',0,100),('quarter_seconds_remaining',0,900),('score_differential',-100,100)]:require(isinstance(r[c],(int,float)) and math.isfinite(r[c]) and low<=r[c]<=high,'Invalid situation field')
   p=dict(id=key,gameId=r['game_id'],playId=int(r['play_id']),week=r['week'],date=r['game_date'],team=r['posteam'],opponent=r['defteam'],passerId=ident,name=r['audited_name'],position=r['position'],positionClass=r['position_class'],quarter=int(r['qtr']),clock=f"{int(r['quarter_seconds_remaining'])//60}:{int(r['quarter_seconds_remaining'])%60:02}",down=int(r['down']),distance=r['ydstogo'],fieldPosition=r['yardline_100'],scoreDifferential=r['score_differential'],ftnInterceptionWorthy=flag,observedInterception=bool(r['interception']),pInterceptionGivenFtn=prob,description=r['desc'],evidence=dict(source='nflverse PBP + FTN Data via nflverse',gameId=r['game_id'],playId=int(r['play_id'])))
   plays.append(p)
  c=aggregate(plays)
  for f,raw in [('eligiblePasses','eligible_passes'),('games','games'),('interceptionWorthyPasses','ftn_interception_worthy_passes'),('observedInterceptions','observed_interceptions'),('expectedInterceptions','expected_interceptions'),('expectedFromClassified','expected_from_ftn_1'),('expectedFromNotClassified','expected_from_ftn_0')]:require(near(c[f],s[raw]),'Player scientific totals differ: '+f)
  by_game=[dict(**{k:v for k,v in games[gid].items() if k!='passes'},**aggregate([p for p in plays if p['gameId']==gid])) for gid in sorted({p['gameId'] for p in plays})]
  player=dict(id=ident,name=s['name'],teams=s['teams'].split(' / '),positions=s['position'].split(' / ') if s['position'] else [],positionClass=s['position_class'] if s['position_class'] in ['qb','other'] else 'unknown',byGame=by_game,**c)
  players.append(player);details[ident]=dict(player=player,plays=plays);all_plays+=plays
 total=aggregate(all_plays)
 require(total['eligiblePasses']==i['summary']['passes'] and total['observedInterceptions']==i['summary']['observed_interceptions'] and near(total['expectedInterceptions'],i['summary']['expected_interceptions']),'Scientific global totals differ')
 require(total['games']==len(games) and set(p['week'] for p in all_plays)==set(cov['weeks']),'Scientific coverage/period mismatch')
 active=read(Path(m3_store)/'current.json');require(re.fullmatch('[a-f0-9]{24}',active['packageId']),'M3 ID invalid')
 mb=Path(m3_store)/'packages'/active['packageId'];verify_files(mb,read(mb/'integrity.json')['files']);mi=read(mb/'index.json');require(mi['model']['sha256']==M3_SHA and sha(mb/'index.json')==active['indexSha256'],'M3 pin mismatch')
 m3={p['id']:(p['passerId'],p['worthy'],p['interception'],p['week']) for s in mi['players'] for p in read(mb/f'players/{s["id"]}.json')['plays']}
 b2={p['id']:(p['passerId'],p['ftnInterceptionWorthy'],p['observedInterception'],p['week']) for p in all_plays}
 shared=set(m3)&set(b2);mismatch=sorted(k for k in shared if m3[k]!=b2[k]);same=m3==b2
 comparison=dict(m3PackageId=mi['packageId'],sameEligiblePasses=same,sharedPasses=len(shared),onlyM3=len(set(m3)-set(b2)),onlyB2=len(set(b2)-set(m3)),revisedPasses=len(mismatch),revisedKeys=mismatch)
 acquired=max((r.get('acquiredAt') or r.get('acquired_at_utc') or '' for r in sources['files'] if r.get('role') in ['pbp','ftn','schedule','roster','roster_2026']),default='')
 require(acquired and datetime.datetime.fromisoformat(acquired.replace('Z','+00:00')),'Missing acquisition timestamp')
 def meta(g):return dict(gameId=g['game_id'],week=g['week'],date=g['date'],home=g['home'],away=g['away'],reason=g.get('reason',''))
 index=dict(schemaVersion=1,presentationVersion='1.0.0',target='observed_interception',season=2026,phase='REG',acquiredAt=acquired,
  model=dict(id=MODEL_ID,sha256=MODEL_SHA,referenceSeason=2025,rateClassified=model['groups']['1']['probability'],rateNotClassified=model['groups']['0']['probability'],referenceClassified=dict(events=305,passes=553),referenceNotClassified=dict(events=75,passes=16805)),
  scientific=dict(consumerIndexSha256=sha(application/'consumer/index.json'),integritySha256=sha(application/'integrity.json'),sourceManifestSha256=sha(application/'sources.json')),
  coverage=dict(games=len(games),completedGames=cov['completed_games'],scheduledGames=len(cov['scheduled_games']),weeks=cov['weeks'],pendingGames=[meta(g) for g in cov['pending_games']],scheduled=[meta(g) for g in cov['scheduled_games']],included=list(games.values()),pbpWeeks=cov['pbp_weeks'],ftnWeeks=cov['ftn_weeks']),
  summary=total,players=players,comparison=comparison,attribution='FTN Data via nflverse · CC BY-SA 4.0. Dados transformados, sem endosso.',interpretation='Comparação retrospectiva condicionada à classificação FTN, que pode conhecer o desfecho. Residual não atribui responsabilidade, sorte ou qualidade de decisão.')
 return index,details,sources
def safe_store(store):
 p=Path(store).resolve()
 protected=[SCIENTIFIC.parent,M3_STORE,ROOT,MAIN/'web-ui',
  MAIN/'editorial/local-artifacts/qb-interception-risk-baseline-v1',MAIN/'editorial/local-artifacts/qb-risk-temporal-calibration-v2',
  Path('/Users/pedrocollet/.codex/worktrees/qb-risk-lab-chart-focus-v3/NFL Sideline'),Path('/Users/pedrocollet/.codex/worktrees/qb-expected-interceptions-v1/NFL Sideline')]
 require(not any(p==x or p.is_relative_to(x) for x in protected),'Protected destination; use a separate outcome store')
 return p
def verify_package(base):
 base=Path(base);m=read(base/'integrity.json');verify_files(base,m['files']);return read(base/'index.json')
def publish(application,source_root,store=DEFAULT,m3_store=M3_STORE):
 store=safe_store(store);store.mkdir(parents=True,exist_ok=True);lock=store/'.updating'
 fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 run=store/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 old=read(store/'current.json') if (store/'current.json').exists() else None
 try:
  index,details,sources=presentation(application,source_root,m3_store)
  ident=hashlib.sha256(encoded(dict(index=index,details=details))).hexdigest()[:24]
  index['packageId']=ident;base=store/'packages'/ident;base.parent.mkdir(exist_ok=True)
  if not base.exists():
   temp=Path(tempfile.mkdtemp(prefix='.outcome-',dir=base.parent))
   try:
    write(temp/'index.json',index);write(temp/'sources.json',sources)
    for gsis,d in details.items():write(temp/f'players/{gsis}.json',dict(packageId=ident,**d))
    write(temp/'integrity.json',dict(files={str(p.relative_to(temp)):sha(p) for p in sorted(temp.rglob('*')) if p.is_file()}));verify_package(temp);os.replace(temp,base)
   finally:
    if temp.exists():shutil.rmtree(temp)
  verify_package(base)
  before={}
  if old:
   ob=store/'packages'/old['packageId'];oi=verify_package(ob)
   before={p['id']:p for player in oi['players'] for p in read(ob/f'players/{player["id"]}.json')['plays']}
  after={p['id']:p for d in details.values() for p in d['plays']}
  fields=['passerId','ftnInterceptionWorthy','observedInterception','pInterceptionGivenFtn']
  changed=[dict(id=k,fields=[f for f in fields if before[k][f]!=after[k][f]]) for k in sorted(before.keys()&after.keys()) if any(before[k][f]!=after[k][f] for f in fields)]
  revision=dict(added=sorted(after.keys()-before.keys()),removed=sorted(before.keys()-after.keys()),changed=changed)
  write(run/'revision.json',revision)
  pointer=dict(packageId=ident,indexSha256=sha(base/'index.json'),checkedAt=now())
  write(run/'receipt.json',dict(status='unchanged' if old and old['packageId']==ident else 'activated',previous=old['packageId'] if old else None,current=ident,modelSha256=MODEL_SHA,m3PointerSha256=sha(Path(m3_store)/'current.json'),comparison=index['comparison']))
  fd,path=tempfile.mkstemp(prefix='.current-',dir=store);os.close(fd)
  try:write(path,pointer);os.replace(path,store/'current.json')
  finally:
   if Path(path).exists():Path(path).unlink()
  return pointer
 except Exception as e:
  write(run/'failure.json',dict(type=type(e).__name__,message=str(e),previousPreserved=True));raise
 finally:lock.unlink()
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--application',default=str(SCIENTIFIC/'application-complete'));a.add_argument('--source-root',default=str(SCIENTIFIC));a.add_argument('--store',default=str(DEFAULT));a.add_argument('--m3-store',default=str(M3_STORE));v=a.parse_args();print(json.dumps(publish(v.application,v.source_root,v.store,v.m3_store)))
