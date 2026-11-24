"""V2 namespace: reuse the immutable v1 implementation, never fork its model."""
from pathlib import Path
import sys,json
V1_CODE=Path(__file__).resolve().parents[1]/'qb_interception_risk'
sys.path.insert(0,str(V1_CODE))
from acquire import sha
from dataset import dump,verify_sources
from model import fit,features,export_model,predict_json
from evaluation import metrics,calibration,paired_game_bootstrap,groups
from pipeline import load_dataset,destination
HERE=Path(__file__).resolve().parent

def design():return json.loads((V1_CODE/'design.json').read_text())
def protocol():return json.loads((HERE/'protocol.json').read_text())
def known_only(d):
 if not d.season.between(2022,2026).all() or not (d.season.ne(2026)|d.week.between(1,7)).all():
  raise ValueError('Reserved/outside known-data boundary; never use for selection')
 if not d.season_type.eq('REG').all():raise ValueError('Only REG is authorized')
 return d

def blocks(d,train_years,cal_year,eval_year):
 known_only(d)
 if not train_years or max(train_years)>=eval_year or (cal_year is not None and not max(train_years)<cal_year<eval_year):
  raise ValueError('Chronological train/calibration/evaluation boundary')
 tr=d[d.season.isin(train_years)].copy();ca=d[d.season.eq(cal_year)].copy() if cal_year else d.iloc[:0].copy();ev=d[d.season.eq(eval_year)].copy()
 sets=[set(b.game_id) for b in [tr,ca,ev]]
 if any(sets[i]&sets[j] for i in range(3) for j in range(i+1,3)):raise ValueError('Games shared across blocks')
 if tr.empty or ev.empty or (cal_year is not None and ca.empty):raise ValueError('Empty chronological block')
 dates=[pd_dates(b) for b in [tr,ca,ev] if len(b)]
 if any(a[1]>=b[0] for a,b in zip(dates,dates[1:])):raise ValueError('Dates overlap chronological blocks')
 return tr,ca,ev

def pd_dates(d):
 import pandas as pd
 a=pd.to_datetime(d.game_date);return a.min(),a.max()
