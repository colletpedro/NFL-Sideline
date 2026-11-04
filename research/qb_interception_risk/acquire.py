"""Public sources only. Never refresh an existing frozen acquisition."""
from pathlib import Path
import argparse, datetime, hashlib, json, shutil, urllib.request, platform
import pyarrow.parquet as pq

APPROVED = Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-score-curve-v2/20261027-v1/bundle/source/source/source/pbp.parquet')
DOCS = {
 'ftn_dictionary': 'https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html',
 'ftn_loader': 'https://nflreadr.nflverse.com/reference/load_ftn_charting.html',
 'ftn_release': 'https://github.com/nflverse/nflverse-data/releases/tag/ftn_charting',
 'pbp_loader': 'https://nflreadr.nflverse.com/reference/load_pbp.html',
 'schedule': 'https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html',
 'participation_dictionary': 'https://nflreadr.nflverse.com/articles/dictionary_participation.html',
 'ftn_license': 'https://creativecommons.org/licenses/by-sa/4.0/',
 'pbp_license': 'https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md',
 'pbp_dictionary_csv': 'https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv',
}
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def acquire(root, approved=APPROVED):
 root=Path(root); root.mkdir(parents=True,exist_ok=True)
 manifest=root/'sources.json'
 if manifest.exists():
  data=json.loads(manifest.read_text())
  for x in data['files']:
   assert sha(root/x['path'])==x['sha256'], x['path']
  print('Existing frozen sources verified; no network refresh.'); return
 progress=root/'acquisition-progress.json'
 files=json.loads(progress.read_text()) if progress.exists() else []
 def get(rel,url,season=None,kind='documentation',local=None):
  p=root/rel; p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists():
   old=next((x for x in files if x['path']==rel),None)
   if old and sha(p)==old['sha256']:
    print('Resume verified',rel,flush=True); return
   raise FileExistsError(f'Unverified partial acquisition exists: {p}; preserve and use a new root')
  now=datetime.datetime.now(datetime.timezone.utc).isoformat()
  headers={}
  if local:
   shutil.copyfile(local,p); headers={'local_origin':str(local),'origin_sha256':sha(local)}
  else:
   req=urllib.request.Request(url,headers={'User-Agent':'NFL-Sideline-local-research/1.0'})
   with urllib.request.urlopen(req,timeout=180) as r, p.open('wb') as f:
    headers={k:r.headers.get(k) for k in ['ETag','Last-Modified','Content-Length']}; shutil.copyfileobj(r,f)
  item=dict(path=rel,url=url,acquired_at_utc=now,bytes=p.stat().st_size,sha256=sha(p),season=season,kind=kind,headers=headers)
  if kind in ['pbp','ftn']:
   table=pq.read_table(p); df=table.select([c for c in ['season','week','game_id','nflverse_game_id','season_type'] if c in table.column_names]).to_pandas()
   gid='game_id' if kind=='pbp' else 'nflverse_game_id'
   item.update(rows=len(df),games=df[gid].nunique(),weeks=sorted(df.week.dropna().astype(int).unique().tolist()),schema={f.name:str(f.type) for f in table.schema},parquet_metadata={str(k):str(v) for k,v in (table.schema.metadata or {}).items()},license='CC BY-SA 4.0' if kind=='ftn' else 'See frozen nflverse-data LICENSE (CC BY 4.0)',attribution='FTN Data / ftndata.com via nflverse' if kind=='ftn' else 'nflverse / nflfastR; underlying NFL play-by-play')
  files.append(item)
  (root/'acquisition-progress.json').write_text(json.dumps(files,indent=2,default=int))
  print(rel,item['bytes'],item['sha256'],flush=True)
 for year in range(2022,2027):
  get(f'raw/pbp_{year}.parquet',f'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.parquet',year,'pbp',approved if year==2026 else None)
  get(f'raw/ftn_{year}.parquet',f'https://github.com/nflverse/nflverse-data/releases/download/ftn_charting/ftn_charting_{year}.parquet',year,'ftn')
 get('raw/schedules.csv','https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv',kind='schedule')
 for name,url in DOCS.items(): get(f'documentation/{name}.txt',url)
 manifest.write_text(json.dumps(dict(version=1,python=platform.python_version(),files=files,notice='2026 PBP is approved local frozen source, NOT current remote download. FTN can extend beyond W7; application must filter.'),indent=2,default=int)+'\n')
if __name__=='__main__':
 a=argparse.ArgumentParser(); a.add_argument('--store',required=True,type=Path); a.add_argument('--approved-pbp',type=Path,default=APPROVED); args=a.parse_args(); acquire(args.store,args.approved_pbp)
