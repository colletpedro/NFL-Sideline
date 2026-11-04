"""Reserved evaluation gate: reject prematurity BEFORE reading PBP/FTN labels."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import argparse,json
import numpy as np
import pandas as pd
from common import sha,dump,protocol,HERE,V1_CODE,calibration,paired_game_bootstrap
from dataset import FILTERS,unique,FTN_KEEP,KEY
from calibration_stats import scores,diagnostic_calibration

class GateError(ValueError):pass

def utcnow():return datetime.now(timezone.utc)
def schedule_window(schedule):
 s=schedule[schedule.season.eq(2026)&schedule.game_type.eq('REG')&schedule.week.between(9,13)].copy()
 if s.empty or s.game_id.isna().any() or s.game_id.duplicated().any() or set(s.week)!={9,10,11,12,13}:raise GateError('Incomplete/duplicate reserved calendar')
 if s[['gameday','gametime']].isna().any().any():raise GateError('Missing reserved kickoff date/time')
 return s

def maturity(pinned,updated=None,now=None):
 now=now or utcnow()
 if now.tzinfo is None:raise GateError('UTC-aware clock required')
 a=schedule_window(pinned);b=schedule_window(updated) if updated is not None else a
 if set(a.game_id)!=set(b.game_id):raise GateError('Reserved game universe changed; suspend before label opening')
 for _,r in a.iterrows():
  other=b[b.game_id.eq(r.game_id)].iloc[0]
  if int(r.week)!=int(other.week):raise GateError('Reserved game week changed; review before labels')
 def last(s):
  dates=[datetime.fromisoformat(f'{r.gameday}T{r.gametime}').replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc) for r in s.itertuples()]
  return max(dates)
 latest=max(last(a),last(b));not_before=latest+timedelta(days=8)
 if now<not_before:raise GateError(f'PREMATURE: not before {not_before.isoformat()} UTC; no PBP/FTN opened')
 if updated is None:raise GateError('Updated completed calendar required; pinned schedule alone cannot open labels')
 if b[['home_score','away_score']].isna().any().any():raise GateError('Window not complete: missing final scores')
 if not np.isfinite(b[['home_score','away_score']].to_numpy()).all() or (b[['home_score','away_score']]<0).any().any():raise GateError('Invalid final scores')
 if 'result' not in b or not b.result.eq(b.home_score-b.away_score).all():raise GateError('Invalid final score atomic trio')
 return dict(not_before_utc=not_before.isoformat(),latest_kickoff_utc=latest.isoformat(),games=len(a),weeks=[9,13],clock_utc=now.isoformat(),maturity='operational margin, not source completeness guarantee')

def validate_bundle(bundle):
 bundle=Path(bundle);f=json.loads((bundle/'freeze.json').read_text())
 if f['reserved']!=protocol()['reserved']:raise GateError('Reserved protocol changed')
 for name,h in f['files'].items():
  if sha(bundle/name)!=h:raise GateError('Frozen model/calendar hash differs')
 for rel,h in f['code_hashes'].items():
  if sha(HERE.parents[1]/rel)!=h:raise GateError('Frozen research code changed')
 for name,h in f['contracts'].items():
  p=HERE/'protocol.json' if name=='protocol.json' else HERE.parents[1]/'docs/plans/qb-risk-temporal-calibration-v2'/name
  if sha(p)!=h:raise GateError('Frozen contract changed')
 return f

def reserved_population(pbp,ftn,expected_games):
 # Raw seasonal files can contain other weeks; no metrics or summaries for them.
 p=pbp[pbp.season.eq(2026)&pbp.season_type.eq('REG')&pbp.week.between(9,13)].copy()
 f=ftn.rename(columns={'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})
 f=f[f.season.eq(2026)&f.week.between(9,13)].copy()
 if set(p.game_id)!=set(expected_games) or set(f.game_id)!=set(expected_games):raise GateError('Incomplete reserved games; no partial evaluation')
 unique(p,KEY,'reserved PBP');unique(f,KEY,'reserved FTN')
 shared=p[KEY+['week']].merge(f[KEY+['week']],on=KEY,validate='one_to_one',suffixes=('_p','_f'))
 if not shared.week_p.eq(shared.week_f).all():raise GateError('Reserved week mismatch')
 mask=pd.Series(True,index=p.index)
 for name,rule in FILTERS:
  if name!='window_W1_W7_for_2026':mask &= rule(p).fillna(False)
 j=p[mask].merge(f[FTN_KEEP],on=KEY,how='left',validate='one_to_one',indicator=True)
 if j.empty or j.passer_player_id.isna().any() or j.is_interception_worthy.isna().any() or not j.is_interception_worthy.isin([False,True,0,1]).all():raise GateError('Reserved eligible label/identity gap; never fill False')
 j['is_interception_worthy']=j.is_interception_worthy.astype(int);window_only(j)
 return j

def window_only(d):
 if not (d.season.eq(2026)&d.season_type.eq('REG')&d.week.between(9,13)).all():raise GateError('Outside authorized reserved window')

def evaluate(bundle,manifest_path,out):
 # One logical opening; successful output sentinel refuses a second invocation.
 bundle=Path(bundle);out=Path(out)
 if out.exists():raise FileExistsError('Never overwrite a reserved evaluation')
 f=validate_bundle(bundle);manifest_path=Path(manifest_path);manifest=json.loads(manifest_path.read_text());now=utcnow()
 if manifest.get('purpose')!='reserved_window_only' or manifest.get('season')!=2026 or manifest.get('weeks')!=[9,13] or manifest.get('freeze_sha256')!=sha(bundle/'freeze.json'):raise GateError('Evaluation manifest does not bind exact frozen window/models')
 entries={r['role']:r for r in manifest['files']}
 if set(entries)!={'schedule','pbp','ftn'} or len(manifest['files'])!=3:raise GateError('Exactly one schedule, PBP and FTN required')
 paths={k:(manifest_path.parent/v['path']).resolve() for k,v in entries.items()}
 if sha(paths['schedule'])!=entries['schedule']['sha256']:raise GateError('Calendar hash differs')
 updated=pd.read_csv(paths['schedule']);pinned=pd.read_csv(bundle/'reserved_schedule.csv');gate=maturity(pinned,updated,now)
 for k,r in entries.items():
  acquired=datetime.fromisoformat(r['acquired_at_utc'])
  if acquired.tzinfo is None or acquired>now or acquired<datetime.fromisoformat(gate['not_before_utc']):raise GateError('Sources must be acquired after maturity, never future-dated')
  if sha(paths[k])!=r['sha256']:raise GateError('Evaluation source hash differs')
 # No PBP or FTN read above this line.
 data=reserved_population(pd.read_parquet(paths['pbp']),pd.read_parquet(paths['ftn']),set(schedule_window(updated).game_id))
 opening=bundle/'OPENED.json'
 try:
  with opening.open('x') as lock:json.dump(dict(manifest_sha256=sha(manifest_path),opened_at_utc=now.isoformat(),output=str(out),notice='If evaluation fails, preserve this receipt and diagnose; do not delete to tune/reopen.'),lock,indent=2)
 except FileExistsError:raise GateError('Reserved bundle already opened; preserve first result')
 from experiment import predict
 out.mkdir(parents=True);pred=data[KEY+['season','season_type','week','is_interception_worthy']].copy();result={};names=['M0','M1']+([f['selected']] if f['selected'] else [])
 for name in names:pred[name]=predict(json.loads((bundle/f'{name}.json').read_text()),data)
 for name in names:
  p=pred[name].to_numpy();result[name]=dict(scores=scores(data.is_interception_worthy,p),vs_M1=paired_game_bootstrap(data,p,pred.M1.to_numpy(),protocol()['bootstrap_replicates'],protocol()['seed']),calibration=calibration(data.is_interception_worthy,p,design_edges()),diagnostic=diagnostic_calibration(data,p))
 pred.to_parquet(out/'reserved_predictions.parquet',index=False);dump(out/'reserved_metrics.json',result);dump(out/'opening_receipt.json',dict(gate=gate,manifest_sha256=sha(manifest_path),freeze_sha256=sha(bundle/'freeze.json'),window_complete=True,no_partial_results=True))

def design_edges():
 from common import design
 return design()['calibration_edges']
if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);a=sub.add_parser('preflight');a.add_argument('--freeze',required=True);b=sub.add_parser('evaluate');b.add_argument('--freeze',required=True);b.add_argument('--manifest',required=True);b.add_argument('--out',required=True);a=p.parse_args()
 try:
  if a.command=='preflight':validate_bundle(a.freeze);maturity(pd.read_csv(Path(a.freeze)/'reserved_schedule.csv'))
  else:evaluate(a.freeze,a.manifest,a.out)
 except GateError as e:print(str(e));raise SystemExit(3)
