"""Audit-first population and reconciliation. No model or network access."""
from pathlib import Path
import json, sqlite3
import numpy as np
import pandas as pd
from acquire import sha

KEY=['game_id','play_id']
FILTERS=[('regular_season',lambda d:d.season_type.eq('REG')),
 ('window_W1_W7_for_2026',lambda d:d.season.ne(2026)|d.week.between(1,7)),
 ('not_deleted',lambda d:d.play_deleted.eq(0)),
 ('pass_type',lambda d:d.play_type.eq('pass')),
 ('official_attempt',lambda d:d.pass_attempt.eq(1)),
 ('not_sack',lambda d:d.sack.eq(0)),
 ('not_scramble',lambda d:d.qb_scramble.eq(0)),
 ('not_spike',lambda d:d.qb_spike.eq(0)),
 ('not_two_point',lambda d:d.two_point_attempt.eq(0))]
PBP_KEEP=KEY+['season','season_type','week','game_date','passer_player_id','passer_player_name','posteam','defteam','receiver_player_id','down','ydstogo','yardline_100','qtr','quarter_seconds_remaining','game_seconds_remaining','score_differential','air_yards','interception','penalty','penalty_type','aborted_play','roof','wind','temp','stadium_id','game_stadium','incomplete_pass','complete_pass']
FTN_KEEP=KEY+['is_interception_worthy','is_throw_away','read_thrown','date_pulled']

def dump(path,obj):
 Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False,default=lambda x:x.item() if hasattr(x,'item') else str(x))+'\n')
def unique(d,key,side):
 if d[key].isna().any().any(): raise ValueError(f'{side}: null key')
 if d.duplicated(key).any(): raise ValueError(f'{side}: duplicate key, no arbitrary correction accepted')
 if not np.equal(d[key[-1]],np.floor(d[key[-1]])).all(): raise ValueError(f'{side}: noninteger play ID')
def eligible(d):
 mask=pd.Series(True,index=d.index); funnel=[dict(stage='raw',remaining=len(d),excluded=0)]
 for name,rule in FILTERS:
  keep=rule(d).fillna(False); after=mask & keep
  funnel.append(dict(stage=name,remaining=int(after.sum()),excluded=int((mask & ~keep).sum())))
  mask=after
 return mask,funnel

def reconcile(pbp,ftn):
 unique(pbp,KEY,'PBP'); unique(ftn,KEY,'FTN')
 mask,funnel=eligible(pbp)
 j=pbp.loc[mask].merge(ftn[FTN_KEEP],on=KEY,how='left',validate='one_to_one',indicator=True)
 info=dict(funnel=funnel,eligible_before_identity=len(j),unmatched=int(j._merge.eq('left_only').sum()),null_labels=int(j.is_interception_worthy.isna().sum()),missing_passer=int(j.passer_player_id.isna().sum()))
 nonnull=j.is_interception_worthy.dropna()
 if not nonnull.isin([True,False,0,1]).all(): raise ValueError('Invalid target; not a binary FTN label')
 if info['null_labels']: raise ValueError('Eligible passes missing label: never impute False; audit sources before training')
 j=j[j.passer_player_id.notna()].copy()
 if not j.passer_player_id.str.match(r'^00-\d{7}$').all(): raise ValueError('Invalid GSIS passer ID')
 j['is_interception_worthy']=j.is_interception_worthy.astype(int)
 info['funnel'].append(dict(stage='identified_passer',remaining=len(j),excluded=info['missing_passer']))
 if not j.interception.isin([0,1]).all(): raise ValueError('Invalid observed INT audit field')
 return j,info

def independent(pbp,ftn,joined):
 """SQLite SQL from RAW inputs; no reuse of pandas population/filter/join routines."""
 cols=['game_id','play_id','season','week','season_type','play_type','pass_attempt','sack','qb_scramble','qb_spike','play_deleted','two_point_attempt','passer_player_id','interception']
 with sqlite3.connect(':memory:') as con:
  pbp[cols].to_sql('p',con,index=False)
  ftn[KEY+['is_interception_worthy']].to_sql('f',con,index=False)
  q="""SELECT p.game_id,p.play_id,p.season,p.week,p.passer_player_id,
 f.is_interception_worthy AS y,p.interception AS i
 FROM p LEFT JOIN f ON p.game_id=f.game_id AND p.play_id=f.play_id
 WHERE p.season_type='REG' AND (p.season<>2026 OR p.week BETWEEN 1 AND 7)
 AND p.play_type='pass' AND p.pass_attempt=1 AND p.sack=0 AND p.qb_spike=0
 AND p.qb_scramble=0 AND p.play_deleted=0 AND p.two_point_attempt=0
 AND p.passer_player_id IS NOT NULL"""
  con.execute('CREATE TABLE independent AS '+q)
  rows=con.execute('SELECT game_id,play_id,y,i FROM independent ORDER BY game_id,play_id').fetchall()
  expected=[tuple(r) for r in joined.sort_values(KEY)[KEY+['is_interception_worthy','interception']].itertuples(index=False,name=None)]
  assert rows==expected, 'Independent RAW SQLite pass keys/labels/INT diverge'
  groups={}
  for name,cols2 in [('season',['season']),('week',['season','week']),('game',['game_id']),('qb',['passer_player_id']),('cross',['y','i'])]:
   columns=','.join(cols2)
   actual=con.execute(f'SELECT {columns},COUNT(*),SUM(y),SUM(i) FROM independent GROUP BY {columns} ORDER BY {columns}').fetchall()
   compare=joined.rename(columns={'is_interception_worthy':'y','interception':'i'}).groupby(cols2,sort=True,dropna=False).agg(n=('y','size'),sum_y=('y','sum'),sum_i=('i','sum')).reset_index()
   assert actual==list(compare.itertuples(index=False,name=None)), name
   groups[name]=len(actual)
 return dict(method='Independent SQLite WHERE / LEFT JOIN / GROUP BY from raw PBP and FTN, exact keys/labels/INT + season/week/game/QB/cross',rows=len(rows),groups=groups,passed=True)

def verify_sources(store):
 manifest=json.loads((store/'sources.json').read_text())
 for x in manifest['files']:
  if sha(store/x['path'])!=x['sha256']: raise ValueError(f'Source changed: {x["path"]}')
 return manifest

def build(store,out):
 store=Path(store); out=Path(out)
 if out.exists(): raise FileExistsError(out)
 out.mkdir(parents=True); (out/'audit').mkdir(); verify_sources(store)
 allrows=[]; audit={}; external=[]
 schedules=pd.read_csv(store/'raw/schedules.csv')
 for year in range(2022,2027):
  p=pd.read_parquet(store/f'raw/pbp_{year}.parquet'); f=pd.read_parquet(store/f'raw/ftn_{year}.parquet').rename(columns={'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})
  if not p.season.eq(year).all() or not f.season.eq(year).all(): raise ValueError('Wrong season in source')
  unique(p,KEY,'PBP'); unique(f,KEY,'FTN')
  if not f.is_interception_worthy.dropna().isin([True,False,0,1]).all(): raise ValueError('Invalid FTN target in source')
  j,info=reconcile(p,f)
  shared=p[KEY+['season','week']].merge(f[KEY+['season','week']],on=KEY,how='inner',validate='one_to_one',suffixes=('_p','_f'))
  if not (shared.season_p.eq(shared.season_f)&shared.week_p.eq(shared.week_f)).all(): raise ValueError('FTN/PBP metadata mismatch')
  ind=independent(p,f,j); info['independent']=ind
  mask,_=eligible(p); reasons=pd.Series('eligible',index=p.index)
  # First exclusion reason, retaining full universe distinction.
  current=pd.Series(True,index=p.index)
  for name,rule in FILTERS:
   keep=rule(p).fillna(False); reasons[current & ~keep]=name; current &= keep
  pkeys=p[KEY].copy(); pkeys['population_status']=reasons
  outer=f[FTN_KEEP].merge(pkeys,on=KEY,how='outer',validate='one_to_one',indicator=True)
  outer['population_status']=outer.population_status.fillna('not_in_frozen_PBP')
  info['source_join']={str(k):int(v) for k,v in outer._merge.value_counts().items()}
  info['ftn_outside_eligible_by_reason']=outer[outer._merge.ne('right_only')].groupby('population_status').size().to_dict()
  info['ftn_worthy_outside_eligible_by_reason']=outer[outer._merge.ne('right_only') & outer.is_interception_worthy.eq(True)].groupby('population_status').size().to_dict()
  outer[outer.population_status.ne('eligible')].to_parquet(out/f'audit/outside_eligible_{year}.parquet',index=False)
  sc=schedules[schedules.season.eq(year)&schedules.game_type.eq('REG')].copy()
  if year==2026: sc=sc[sc.week.between(1,7)]
  reg=p[p.season_type.eq('REG') & (p.week.between(1,7) if year==2026 else True)]
  info['coverage']={'raw_rows':len(p),'raw_games':p.game_id.nunique(),'reg_games':reg.game_id.nunique(),'eligible_games':j.game_id.nunique(),'schedule_games':len(sc),'schedule_without_pbp':sorted(set(sc.game_id)-set(reg.game_id)),'pbp_without_schedule':sorted(set(reg.game_id)-set(sc.game_id)),'ftn_weeks':sorted(f.week.unique().tolist()),'ftn_games':f.game_id.nunique()}
  info['target']={'n':len(j),'worthy':int(j.is_interception_worthy.sum()),'interceptions':int(j.interception.sum()),'prevalence':float(j.is_interception_worthy.mean())}
  info['nulls']={str(k):int(v) for k,v in j[PBP_KEEP+['is_interception_worthy','is_throw_away']].isna().sum().items()}
  info['filter_nulls']={c:int(p[c].isna().sum()) for c in ['play_type','pass_attempt','sack','qb_scramble','qb_spike','play_deleted','two_point_attempt']}
  info['filter_values']={c:{str(k):int(v) for k,v in p[c].value_counts(dropna=False).items()} for c in ['play_type','pass_attempt','sack','qb_scramble','qb_spike','play_deleted','two_point_attempt']}
  info['read_thrown_raw']={str(k):int(v) for k,v in f.read_thrown.value_counts(dropna=False).items()}
  info['date_pulled']={str(k):int(v) for k,v in f.date_pulled.value_counts(dropna=False).items()}
  info['read_thrown_eligible']={str(k):int(v) for k,v in j.read_thrown.value_counts(dropna=False).items()}
  info['flag_counts']={c:int(j[c].eq(1).sum()) for c in ['penalty','aborted_play','is_throw_away','incomplete_pass']}
  info['flag_counts']['unknown_receiver']=int(j.receiver_player_id.isna().sum()); info['flag_counts']['overtime']=int(j.qtr.gt(4).sum())
  info['cross']=pd.crosstab(j.is_interception_worthy,j.interception).to_dict()
  # Keep auditable cases locally, including descriptions; never model inputs.
  for tag,m in [('penalty',j.penalty.eq(1)),('aborted',j.aborted_play.eq(1)),('unknown_receiver',j.receiver_player_id.isna())]:
   j.loc[m,KEY+['desc','passer_player_id','penalty_type','is_interception_worthy','interception']].to_csv(out/f'audit/{tag}_{year}.csv',index=False)
  no_play=p[p.season_type.eq('REG')].merge(f[KEY+['is_interception_worthy']],on=KEY,how='left',validate='one_to_one')
  no_play=no_play[no_play.play_type.eq('no_play') & no_play.is_interception_worthy.eq(True)]
  no_play[KEY+['play_type','pass_attempt','penalty_type','desc','is_interception_worthy']].to_csv(out/f'audit/no_play_worthy_{year}.csv',index=False)
  j[PBP_KEEP+['is_interception_worthy','is_throw_away','read_thrown','date_pulled']].to_parquet(out/f'audit/eligible_{year}.parquet',index=False)
  env=j.groupby(['stadium_id','game_stadium','roof'],dropna=False).agg(n=('play_id','size'),games=('game_id','nunique'),wind_present=('wind','count'),temp_present=('temp','count')).reset_index(); env.insert(0,'season',year); external.append(env)
  allrows.append(j[PBP_KEEP+['is_interception_worthy','is_throw_away','read_thrown']]); audit[str(year)]=info
 d=pd.concat(allrows,ignore_index=True).sort_values(KEY).reset_index(drop=True); unique(d,KEY,'derived')
 for col,low,high in [('down',1,4),('qtr',1,5),('yardline_100',0,100),('ydstogo',0,100),('quarter_seconds_remaining',0,900),('score_differential',-100,100),('air_yards',-100,100)]:
  if not d[col].dropna().between(low,high).all(): raise ValueError(f'Invalid feature range {col}')
 # Verify named pre-play score against the source pre-play component fields independently in build.
 for year in range(2022,2027):
  p=pd.read_parquet(store/f'raw/pbp_{year}.parquet'); mask,_=eligible(p)
  assert (p.loc[mask,'score_differential']==p.loc[mask,'posteam_score']-p.loc[mask,'defteam_score']).all()
 distributions=[]
 for year,g in d.groupby('season'):
  for c in ['down','qtr','ydstogo','yardline_100','quarter_seconds_remaining','score_differential','air_yards','wind','temp']:
   col=g[c]; distributions.append(dict(season=int(year),feature=c,n=len(col),missing=int(col.isna().sum()),mean=float(col.mean()),p01=float(col.quantile(.01)),p50=float(col.median()),p99=float(col.quantile(.99)),min=float(col.min()),max=float(col.max())))
 pd.DataFrame(distributions).to_csv(out/'audit/feature_distributions.csv',index=False)
 for c in ['down','qtr','roof','penalty_type']:
  d.groupby(['season',c],dropna=False).size().rename('n').to_csv(out/f'audit/distribution_{c}.csv')
 d.to_parquet(out/'dataset.parquet',index=False)
 for name,keys in [('season',['season']),('week',['season','week']),('game',['season','week','game_id']),('qb',['season','passer_player_id'])]:
  d.groupby(keys,dropna=False).agg(passes=('play_id','size'),games=('game_id','nunique'),worthy=('is_interception_worthy','sum'),interceptions=('interception','sum')).reset_index().to_csv(out/f'audit/counts_by_{name}.csv',index=False)
 pd.concat(external).to_csv(out/'audit/environment_by_stadium.csv',index=False)
 identities=d.groupby(['passer_player_id','passer_player_name','season','posteam'],dropna=False).size().rename('passes').reset_index(); identities.to_csv(out/'audit/identities.csv',index=False)
 collisions=identities.groupby('passer_player_name').passer_player_id.nunique(); dump(out/'audit/name_collisions.json',collisions[collisions.gt(1)].to_dict())
 split=d[KEY+['season','week']].copy()
 split['role']=np.select([split.season.le(2024),split.season.eq(2025)],['development','final_test_2025'],default='application_2026_W1_7')
 for v in [2023,2024]: split[f'fold_{v}']=np.select([split.season.lt(v),split.season.eq(v)],['train','validation'],default='unused')
 split.to_csv(out/'splits.csv',index=False)
 dump(out/'audit.json',audit)
 dump(out/'build_manifest.json',dict(dataset_sha256=sha(out/'dataset.parquet'),sources_sha256=sha(store/'sources.json'),rows=len(d),gate='PASS',independent_raw_reconciliation=True))
 print(d.groupby('season').is_interception_worthy.agg(['size','sum','mean']).to_string(),flush=True)
 return d
