"""Standalone descriptive research; no operational imports or environment secrets."""
from pathlib import Path
import hashlib, json, math
import numpy as np
import pandas as pd

VERSION='1.0.0'
BASE=Path('/Users/pedrocollet/Downloads/NFL Sideline')
PREVIOUS=BASE/'editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1'
STORE=BASE/'editorial/local-artifacts/qb-structure-production-v1/20261105-v1'
KEY=['game_id','play_id']
CATS=['progression','scramble_drill','scramble','throwaway','sack','indeterminate']
GROUPS={'main':['scramble_drill','scramble'],'S1':['scramble_drill','scramble','throwaway'],'S2':['scramble_drill','scramble','throwaway','sack'],'S3':['scramble_drill']}
CONTEXT=['down','ydstogo','yardline_100','qtr','quarter_seconds_remaining','score_differential']
FTN=['read_thrown','is_throw_away','is_qb_out_of_pocket','is_screen_pass','is_rpo','is_play_action','is_trick_play','is_qb_sneak']
PBP=KEY+['season','season_type','week','game_date','home_team','away_team','posteam','defteam','play_type','qb_dropback','play_deleted','qb_spike','qb_kneel','two_point_attempt','aborted_play','pass_attempt','rush_attempt','qb_scramble','sack','complete_pass','interception','passer_player_id','passer_player_name','rusher_player_id','rusher_player_name','epa','penalty','penalty_type','desc','time','yrdln','total_home_score','total_away_score']+CONTEXT

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
 if v is None or v is pd.NA:return None
 if isinstance(v,(np.integer,)):return int(v)
 if isinstance(v,(np.bool_,)):return bool(v)
 if isinstance(v,(float,np.floating)):return float(v) if math.isfinite(v) else None
 if isinstance(v,(pd.Timestamp,)):return v.isoformat()
 return v

def write(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(clean(v),ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def read(p):return json.loads(Path(p).read_text())
def new(p):
 p=Path(p)
 if p.exists():raise FileExistsError(f'Preserved existing destination: {p}')
 p.mkdir(parents=True);return p

def verify(s):
 s=Path(s);m=read(s/'sources.json')
 for r in m['files']:
  if sha(s/r['path'])!=r['sha256'] or (s/r['path']).stat().st_size!=r['bytes']:raise ValueError('Source hash/size mismatch: '+r['path'])
 return m

def unique(d,label):
 if d[KEY].isna().any().any() or d.duplicated(KEY).any():raise ValueError('Missing/duplicate key '+label)

def eligible(d):
 return (d.season_type.eq('REG') & d.qb_dropback.eq(1) & d.play_deleted.eq(0) & d.qb_spike.eq(0)&d.qb_kneel.eq(0)&d.two_point_attempt.eq(0)&d.play_type.isin(['pass','run'])).fillna(False)

def stats(d):
 e=pd.to_numeric(d.epa,errors='coerce');e=e[np.isfinite(e)]
 return dict(n=len(d),n_epa=len(e),sum_epa=float(e.sum()) if len(e) else None,mean_epa=float(e.mean()) if len(e) else None,games=d.game_id.nunique(),status='unavailable_no_opportunities' if not len(d) else 'unavailable_epa' if not len(e) else 'available')

def support(a,b,games):return 'legible' if a>=100 and b>=25 and games>=5 else 'low_support'
