"""Availability by game; frozen M3; immutable packages and atomic active pointer."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,shutil,sys,urllib.request,tempfile,re
import numpy as np
import pandas as pd
from scipy.special import expit,logit
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/qb_interception_risk'))
from model import predict_json
from dataset import FILTERS,unique,KEY
MODEL=ROOT/'docs/plans/qb-risk-temporal-calibration-v2/evidence/frozen/M3.json'
MODEL_SHA='38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6'
URLS={'pbp':'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet','ftn':'https://github.com/nflverse/nflverse-data/releases/download/ftn_charting/ftn_charting_2026.parquet','schedule':'https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv','roster':'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2026.parquet'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encoded(obj):return json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
def write(p,obj):Path(p).write_bytes(encoded(obj)+b'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def number(x):return None if pd.isna(x) else float(x)
def clean(x):return None if pd.isna(x) else str(x)
def safe_mean(n,den):return n/den if den else None

def load_model():
 if sha(MODEL)!=MODEL_SHA:raise ValueError('Frozen M3 hash differs; data update cannot change model')
 return json.loads(MODEL.read_text())
def probabilities(model,d):
 return expit(logit(predict_json(model['structure'],d))+model['offset'])
def eligible(d):
 m=pd.Series(True,index=d.index)
 for name,rule in FILTERS:
  if name!='window_W1_W7_for_2026':m &= rule(d).fillna(False)
 return m

def position_map(roster):
 required={'gsis_id','season','week','team','game_type','position','full_name'}
 if not required.issubset(roster):raise ValueError('Roster schema incompatible')
 r=roster[roster.season.eq(2026)&roster.game_type.eq('REG')].copy();r['team']=r.team.replace({'LAR':'LA','JAC':'JAX','WSH':'WAS'})
 result={}
 for k,g in r.groupby(['gsis_id','week','team']):
  positions=sorted(g.position.dropna().unique());names=sorted(g.full_name.dropna().unique())
  result[k]=dict(position=positions[0] if len(positions)==1 else None,positionClass='qb' if positions==['QB'] else 'other' if len(positions)==1 else 'unknown',name=names[0] if len(names)==1 else None)
 return result

def aggregate(plays):
 n=len(plays);o=sum(p['worthy'] for p in plays);e=sum(p['probability'] for p in plays)
 return dict(passes=n,games=len({p['gameId'] for p in plays}),observed=o,expected=e,observedRate=safe_mean(o,n),expectedRate=safe_mean(e,n),difference=o-e,per100=safe_mean(100*(o-e),n),interceptions=sum(p['interception'] for p in plays))

def build_frames(pbp,ftn,schedule,roster,model):
 # Global structural failures abort the update. Coverage gaps quarantine a whole game.
 required={'season','season_type','week','game_id','play_id','play_type','pass_attempt','play_deleted','sack','qb_spike','qb_scramble','two_point_attempt','passer_player_id','passer_player_name','posteam','defteam','down','qtr','ydstogo','yardline_100','quarter_seconds_remaining','score_differential','interception','desc','game_date','home_team','away_team','total_home_score','total_away_score'}
 if not required.issubset(pbp):raise ValueError('PBP schema incompatible')
 ftn=ftn.rename(columns={'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})
 if not {'game_id','play_id','season','week','is_interception_worthy'}.issubset(ftn):raise ValueError('FTN schema incompatible')
 unique(pbp,KEY,'PBP');unique(ftn,KEY,'FTN')
 if not pbp.season.eq(2026).all() or not ftn.season.eq(2026).all():raise ValueError('Source season mismatch')
 if not ftn.is_interception_worthy.dropna().isin([True,False,0,1]).all():raise ValueError('Invalid FTN target')
 sc=schedule[schedule.season.eq(2026)&schedule.game_type.eq('REG')].sort_values(['week','game_id']).copy()
 if sc.game_id.isna().any() or sc.game_id.duplicated().any():raise ValueError('Schedule identity duplicate/null')
 if len(sc)!=272:raise ValueError('Calendar REG2026 universe changed: manual review required')
 score_present=sc[['home_score','away_score','result']].notna()
 if not (score_present.sum(axis=1).isin([0,3])).all():raise ValueError('Partial score trio')
 completed=sc[score_present.all(axis=1)]
 if not completed.result.eq(completed.home_score-completed.away_score).all():raise ValueError('Score trio inconsistent')
 if (completed[['home_score','away_score']]<0).any().any():raise ValueError('Invalid negative score')
 universe=set(sc.game_id)
 if not set(pbp[pbp.season_type.eq('REG')].game_id).issubset(universe):raise ValueError('PBP REG games outside calendar')
 if not set(ftn.game_id).issubset(set(schedule[schedule.season.eq(2026)].game_id)):raise ValueError('FTN games outside calendar')
 pos=position_map(roster);games=[];plays=[];pending=[];funnel=[]
 for g in sc.itertuples():
  base=dict(gameId=g.game_id,week=int(g.week),home=g.home_team,away=g.away_team,date=str(g.gameday))
  if pd.isna(g.home_score):pending.append(dict(**base,status='scheduled',reason='Jogo ainda sem resultado final'));continue
  raw=pbp[pbp.game_id.eq(g.game_id)];chart=ftn[ftn.game_id.eq(g.game_id)]
  if not len(raw):pending.append(dict(**base,status='pending',reason='PBP indisponível'));continue
  if not raw.week.eq(g.week).all() or not raw.season_type.eq('REG').all() or (len(chart) and not chart.week.eq(g.week).all()):raise ValueError('Game phase/week metadata mismatch')
  if not (raw.home_team.eq(g.home_team)&raw.away_team.eq(g.away_team)&raw.game_date.astype(str).eq(str(g.gameday))).all():raise ValueError('Game identity/date mismatch')
  terminal=raw[raw.desc.eq('END GAME')]
  if len(terminal)!=1 or terminal[['total_home_score','total_away_score']].isna().any().any():
   pending.append(dict(**base,status='pending',reason='Encerramento PBP não verificável; jogo inteiro fora do agregado'));continue
  if not (terminal.total_home_score.eq(g.home_score)&terminal.total_away_score.eq(g.away_score)).all():raise ValueError('PBP final score differs from calendar')
  mask=eligible(raw);d=raw[mask].copy();stages=[];remaining=pd.Series(True,index=raw.index)
  for name,rule in FILTERS:
   if name=='window_W1_W7_for_2026':continue
   after=remaining & rule(raw).fillna(False);stages.append(dict(stage=name,remaining=int(after.sum()),excluded=int((remaining&~after).sum())));remaining=after
  audit=dict(gameId=g.game_id,raw=len(raw),eligible=len(d),stages=stages,ftnRows=len(chart),ftnWithoutPbp=len(chart.merge(raw[KEY],on=KEY,how='left',indicator=True).query('_merge == "left_only"')),ftnOutsideEligible=len(chart.merge(d[KEY],on=KEY,how='left',indicator=True).query('_merge == "left_only"')))
  if not len(d):pending.append(dict(**base,status='pending',reason='Sem população de passes elegíveis verificável'));funnel.append(audit);continue
  d=d.merge(chart[KEY+['is_interception_worthy']],on=KEY,how='left',validate='one_to_one',indicator=True)
  audit.update(unmatched=int(d._merge.eq('left_only').sum()),missingLabel=int(d.is_interception_worthy.isna().sum()),missingPasser=int(d.passer_player_id.isna().sum()));funnel.append(audit)
  if audit['missingLabel'] or audit['missingPasser']:
   pending.append(dict(**base,status='pending',reason='Charting ou identificação incompletos; jogo inteiro fora do agregado',missingLabels=audit['missingLabel'],missingPassers=audit['missingPasser'],eligible=len(d)));continue
  if not d.passer_player_id.str.match(r'^00-\d{7}$').all():raise ValueError('Invalid GSIS ID')
  if not (d.posteam.isin([g.home_team,g.away_team])&d.defteam.isin([g.home_team,g.away_team])&d.posteam.ne(d.defteam)).all():raise ValueError('Pass team/opponent mismatch')
  if not d.interception.isin([0,1]).all():raise ValueError('Invalid INT field')
  if not d[['down','qtr','ydstogo','yardline_100','quarter_seconds_remaining','score_differential']].apply(lambda v:pd.to_numeric(v,errors='coerce').notna().all()).all():
   pending.append(dict(**base,status='pending',reason='Contexto pré-jogada ausente; jogo inteiro fora do agregado'));continue
  if not (d.down.between(1,4)&d.qtr.between(1,5)&d.ydstogo.between(0,100)&d.yardline_100.between(0,100)&d.quarter_seconds_remaining.between(0,900)&d.score_differential.between(-100,100)).all():raise ValueError('Invalid model feature range')
  ps=probabilities(model,d)
  if not np.isfinite(ps).all() or not ((ps>0)&(ps<1)).all():raise ValueError('Invalid model output')
  game_plays=[]
  for r,prob in zip(d.itertuples(),ps):
   identity=pos.get((r.passer_player_id,int(g.week),r.posteam),dict(position=None,positionClass='unknown',name=None))
   record=dict(id=f'{g.game_id}:{int(r.play_id)}',gameId=g.game_id,playId=int(r.play_id),week=int(g.week),date=str(g.gameday),team=r.posteam,opponent=r.defteam,passerId=r.passer_player_id,name=identity['name'] or r.passer_player_name,position=identity['position'],positionClass=identity['positionClass'],quarter=int(r.qtr),clock=f'{int(r.quarter_seconds_remaining)//60}:{int(r.quarter_seconds_remaining)%60:02}',down=int(r.down),distance=float(r.ydstogo),fieldPosition=float(r.yardline_100),scoreDifferential=float(r.score_differential),probability=float(prob),worthy=bool(r.is_interception_worthy),interception=bool(r.interception),description=clean(r.desc),evidence=dict(source='nflverse PBP + FTN Data via nflverse',gameId=g.game_id,playId=int(r.play_id)))
   game_plays.append(record)
  plays+=game_plays;games.append(dict(**base,homeScore=int(g.home_score),awayScore=int(g.away_score),**aggregate(game_plays)))
 if not games:raise ValueError('No usable completed games; keep previous version')
 players=[];details={}
 for ident in sorted({p['passerId'] for p in plays}):
  selected=[p for p in plays if p['passerId']==ident];classes={p['positionClass'] for p in selected};positions={p['position'] for p in selected};cls=next(iter(classes)) if len(classes)==1 and len(positions)==1 else 'unknown'
  name=selected[-1]['name'];teams=sorted({p['team'] for p in selected})
  summary=dict(id=ident,name=name,teams=teams,positionClass=cls,positions=sorted(p for p in positions if p),**aggregate(selected))
  summary['byGame']=[{**g,**aggregate([p for p in selected if p['gameId']==g['gameId']])} for g in games if any(p['gameId']==g['gameId'] for p in selected)]
  players.append(summary);details[ident]=dict(player=summary,plays=selected)
 included_weeks=sorted({g['week'] for g in games});complete_pending=[g for g in pending if g['status']=='pending']
 coverage=dict(games=len(games),completedGames=len(completed),scheduledGames=len(sc)-len(completed),weeks=included_weeks,pendingGames=complete_pending,scheduled=[g for g in pending if g['status']=='scheduled'],included=games,pbpWeeks=sorted(pbp[pbp.season_type.eq('REG')].week.unique().astype(int).tolist()),ftnWeeks=sorted(ftn.week.unique().astype(int).tolist()))
 return dict(schemaVersion=1,pipelineVersion='1.0.0',season=2026,phase='REG',model=dict(id='M3-2026-frozen-v2',sha256=MODEL_SHA,structureYears=[2023,2024],calibrationYear=2025,offset=model['offset']),coverage=coverage,summary=aggregate(plays),players=players,attribution='FTN Data via nflverse · CC BY-SA 4.0; fontes transformadas, sem endosso.',interpretation='Exploração contínua; não é confirmação independente da reserva v2 nem medida causal de decisão.'),details,funnel

def revision(old,new):
 before={p['id']:p for v in old.values() for p in v['plays']};after={p['id']:p for v in new.values() for p in v['plays']}
 changes=[]
 for k in sorted(set(before)&set(after)):
  fields=[f for f in after[k] if before[k].get(f)!=after[k].get(f)]
  if fields:changes.append(dict(id=k,fields=fields,before={f:before[k].get(f) for f in fields},after={f:after[k].get(f) for f in fields}))
 return dict(added=sorted(set(after)-set(before)),removed=sorted(set(before)-set(after)),changed=changes,labelChanges=[c for c in changes if 'worthy' in c['fields']])

def read_active(store):
 p=Path(store)/'current.json'
 if not p.exists():return None,None,{}
 active=json.loads(p.read_text())
 if not re.fullmatch('[a-f0-9]{24}',active['packageId']):raise ValueError('Invalid active package ID')
 base=Path(store)/'packages'/active['packageId'];verify_package(base);index=json.loads((base/'index.json').read_text())
 if sha(base/'index.json')!=active['indexSha256']:raise ValueError('Active package corrupt')
 details={p.stem:json.loads(p.read_text()) for p in (base/'players').glob('*.json')}
 return active,index,details

def verify_package(base):
 manifest=json.loads((base/'integrity.json').read_text())
 if not {'index.json','sources.json','funnel.json'}.issubset(manifest['files']):raise ValueError('Incomplete package manifest')
 for path,digest in manifest['files'].items():
  if not re.fullmatch(r'(index|sources|funnel)\.json|players/00-\d{7}\.json',path):raise ValueError('Invalid package path')
  if sha(base/path)!=digest:raise ValueError('Package integrity failed')

def activate(store,index,details,funnel,source_manifest,run_dir):
 store=Path(store);run_dir=Path(run_dir);old,oldindex,old_details=read_active(store);rev=revision(old_details,details)
 digest=hashlib.sha256(encoded(dict(index=index,details=details))).hexdigest();package_id=digest[:24]
 index=dict(index,packageId=package_id,acquiredAt=source_manifest['acquiredAt'])
 package=store/'packages'/package_id;store.joinpath('packages').mkdir(exist_ok=True,parents=True)
 # A previously used content-addressed package is immutable; no source-date-only rewrite.
 if not package.exists():
  temp=Path(tempfile.mkdtemp(prefix='.package-',dir=store/'packages'))
  try:
   (temp/'players').mkdir();write(temp/'index.json',index)
   for k,v in details.items():write(temp/'players'/f'{k}.json',dict(packageId=package_id,**v))
   write(temp/'sources.json',source_manifest);write(temp/'funnel.json',funnel)
   write(temp/'integrity.json',dict(files={str(p.relative_to(temp)):sha(p) for p in temp.rglob('*.json')}))
   os.replace(temp,package)
  finally:
   if temp.exists():shutil.rmtree(temp)
 verify_package(package)
 write(run_dir/'revision.json',rev)
 pointer=dict(packageId=package_id,indexSha256=sha(package/'index.json'),checkedAt=source_manifest['acquiredAt'])
 write(run_dir/'receipt.json',dict(status='unchanged' if old and old['packageId']==package_id else 'activated',previous=old['packageId'] if old else None,current=package_id,revision=rev,modelSha256=MODEL_SHA))
 # Commit point is a single atomic replace; any prior failure leaves current untouched.
 fd,path=tempfile.mkstemp(prefix='.current-',dir=store);os.close(fd)
 try:write(path,pointer);os.replace(path,store/'current.json')
 finally:
  if Path(path).exists():Path(path).unlink()
 return pointer

def acquire(run_dir):
 rows=[]
 for role,url in URLS.items():
  path=Path(run_dir)/(role+('.csv' if role=='schedule' else '.parquet'));at=now()
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NFL-Sideline-risk-lab/1'}),timeout=180) as r,path.open('wb') as f:shutil.copyfileobj(r,f)
  rows.append(dict(role=role,path=path.name,url=url,acquiredAt=at,bytes=path.stat().st_size,sha256=sha(path),attribution='FTN Data via nflverse' if role=='ftn' else 'nflverse / NFL.com',license='CC BY-SA 4.0' if role=='ftn' else 'nflverse data CC BY4.0; underlying scope not legally certified'))
 manifest=dict(acquiredAt=now(),files=rows);write(Path(run_dir)/'sources.json',manifest);return manifest

def update(store,sources=None):
 store=Path(store).resolve()
 # Updates never target a checkout or any pinned v1/v2/broadcast store.
 forbidden=[ROOT,ROOT/'web-ui',Path('/Users/pedrocollet/Downloads/NFL Sideline/web-ui')]
 if any(store==p or store.is_relative_to(p) for p in forbidden) or any(s in str(store) for s in ['/qb-interception-risk-baseline-v1/','/qb-risk-temporal-calibration-v2/','/broadcast-score-curve-v2/']):raise ValueError('Protected destination; use a separate lab artifact store')
 store.mkdir(parents=True,exist_ok=True)
 lock=store/'.updating'
 try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 except FileExistsError:raise ValueError('Another update is active; inspect stale lock manually')
 run_dir=store/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run_dir.mkdir(parents=True)
 try:
  if sources:
   src=Path(sources);manifest=json.loads((src/'sources.json').read_text())
   if sorted(r['role'] for r in manifest['files'])!=sorted(URLS):raise ValueError('Source roles incomplete or duplicate')
   for row in manifest['files']:
    if row['path']!=row['role']+('.csv' if row['role']=='schedule' else '.parquet'):raise ValueError('Unsafe pinned source path')
    if sha(src/row['path'])!=row['sha256']:raise ValueError('Pinned source hash mismatch')
    if (src/row['path']).stat().st_size!=row['bytes']:raise ValueError('Pinned source size mismatch')
    shutil.copyfile(src/row['path'],run_dir/row['path'])
   write(run_dir/'sources.json',manifest)
  else:manifest=acquire(run_dir)
  paths={r['role']:run_dir/r['path'] for r in manifest['files']}
  index,details,funnel=build_frames(pd.read_parquet(paths['pbp']),pd.read_parquet(paths['ftn']),pd.read_csv(paths['schedule']),pd.read_parquet(paths['roster']),load_model())
  write(run_dir/'audit.json',dict(funnel=funnel,coverage=index['coverage'],summary=index['summary'],modelSha256=MODEL_SHA))
  pointer=activate(store,index,details,funnel,manifest,run_dir);print(json.dumps(pointer));return pointer
 except Exception as e:
  write(run_dir/'failure.json',dict(error=type(e).__name__,message=str(e),previousPreserved=True));raise
 finally:lock.unlink()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--sources',help='Replay one previously acquired pinned run, without network');a=p.parse_args();update(a.store,a.sources)
