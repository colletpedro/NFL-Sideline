"""Future public acquisition only after the frozen time gate; never scheduled."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import argparse,json,shutil,urllib.request
import pandas as pd
from common import sha,dump
from reserved import validate_bundle,schedule_window,maturity,utcnow,GateError

def acquire(bundle,out):
 bundle=Path(bundle);out=Path(out);validate_bundle(bundle);pinned=pd.read_csv(bundle/'reserved_schedule.csv');w=schedule_window(pinned);now=utcnow()
 latest=max(datetime.fromisoformat(f'{r.gameday}T{r.gametime}').replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc) for r in w.itertuples());earliest=latest+timedelta(days=8)
 if now<earliest:raise GateError(f'PREMATURE: no acquisition before {earliest.isoformat()}; no network or label files opened')
 if out.exists():raise FileExistsError('Never overwrite future source acquisition')
 out.mkdir(parents=True);files=[]
 def get(role,url,filename):
  p=out/filename;at=utcnow().isoformat()
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NFL-Sideline-reserved-research-v2'}),timeout=180) as r,p.open('wb') as f:shutil.copyfileobj(r,f)
  files.append(dict(role=role,path=filename,url=url,sha256=sha(p),bytes=p.stat().st_size,acquired_at_utc=at,attribution='FTN Data via nflverse' if role=='ftn' else 'nflverse',license='CC BY-SA4.0' if role=='ftn' else 'nflverse data license; verify source-specific scope'))
  dump(out/'acquisition-progress.json',files);return p
 schedule=get('schedule','https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv','schedules.csv');gate=maturity(pinned,pd.read_csv(schedule),utcnow())
 get('pbp','https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet','pbp_2026.parquet');get('ftn','https://github.com/nflverse/nflverse-data/releases/download/ftn_charting/ftn_charting_2026.parquet','ftn_2026.parquet')
 dump(out/'manifest.json',dict(purpose='reserved_window_only',version=2,season=2026,weeks=[9,13],freeze_sha256=sha(bundle/'freeze.json'),files=files,maturity=gate))
 print('Sources pinned; run reserved.py evaluate once. No labels inspected or metrics computed by acquisition.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 try:acquire(a.freeze,a.out)
 except GateError as e:print(str(e));raise SystemExit(3)
