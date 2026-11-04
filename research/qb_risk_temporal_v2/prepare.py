"""Copy verified v1 sources; acquire only public roster/docs, no new FTN/PBP."""
from pathlib import Path
import argparse,json,shutil,datetime,urllib.request
import pyarrow.parquet as pq
from common import sha,dump,verify_sources
DOCS={
 'ftn_dictionary':'https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html',
 'ftn_loader':'https://nflreadr.nflverse.com/reference/load_ftn_charting.html',
 'data_schedule':'https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html',
 'weekly_rosters':'https://nflreadr.nflverse.com/reference/load_rosters_weekly.html',
 'roster_dictionary':'https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_rosters.csv',
 'ftn_release':'https://github.com/nflverse/nflverse-data/releases/tag/ftn_charting',
 'news':'https://raw.githubusercontent.com/nflverse/nflverse-data/main/NEWS.md',
 'ftn_loader_source':'https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_ftn_charting.R',
 'ftn_release_metadata':'https://api.github.com/repos/nflverse/nflverse-data/releases/tags/ftn_charting',
 'ftn_dictionary_history':'https://api.github.com/repos/nflverse/nflreadr/commits?path=data-raw/dictionary_ftn_charting.csv&per_page=30',
 'data_license':'https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md'
}
def prepare(v1,store):
 v1=Path(v1);store=Path(store);store.mkdir(parents=True,exist_ok=True)
 verify_sources(v1)
 inp=store/'inputs';inp.mkdir(exist_ok=True)
 # Preserve exact source hashes and pre-test config. Original never mutated.
 for name in ['raw','documentation','sources.json','development-v3']:
  src=v1/name;dest=inp/'v1'/name
  if not dest.exists():
   dest.parent.mkdir(parents=True,exist_ok=True)
   if src.is_dir():shutil.copytree(src,dest)
   else:shutil.copyfile(src,dest)
 verify_sources(inp/'v1')
 for src in ['evaluation-v1/test_predictions_context.parquet','application-v1/application_predictions_context.parquet']:
  dest=inp/'v1'/src;dest.parent.mkdir(exist_ok=True)
  if not dest.exists():shutil.copyfile(v1/src,dest)
 manifest=store/'additional-sources.json'
 if manifest.exists():
  for x in json.loads(manifest.read_text())['files']:
   if sha(store/x['path'])!=x['sha256']:raise ValueError('Additional source changed')
  return
 progress=store/'acquisition-progress.json';files=json.loads(progress.read_text()) if progress.exists() else []
 def get(rel,url,kind):
  p=store/rel;p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists():
   record=next((x for x in files if x['path']==rel),None)
   if record and sha(p)==record['sha256']:return
   raise FileExistsError('Unverified partial download; preserve and investigate')
  now=datetime.datetime.now(datetime.timezone.utc).isoformat()
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NFL-Sideline-local-research/2'}),timeout=120) as r,p.open('wb') as f:shutil.copyfileobj(r,f)
  item=dict(path=rel,url=url,acquired_at_utc=now,bytes=p.stat().st_size,sha256=sha(p),kind=kind,attribution='nflverse / NFL.com roster position' if kind=='roster' else 'nflverse / nflreadr contributors',license='nflverse-data CC BY4.0; check underlying scope; FTN docs specify charting CC BY-SA4.0')
  if kind=='roster':
   t=pq.read_table(p);item.update(rows=t.num_rows,schema={x.name:str(x.type) for x in t.schema},season=2026,scope='weekly roster; position classification only; match only REG W1-7 in this experiment')
  files.append(item);dump(progress,files);print(rel,flush=True)
 get('inputs/roster_weekly_2026.parquet','https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2026.parquet','roster')
 for name,url in DOCS.items():get(f'inputs/provider/{name}.txt',url,'documentation')
 dump(manifest,dict(version=1,files=files,no_new_pbp_or_ftn_acquired=True))
 dump(store/'v1-lineage.json',dict(source_manifest_sha256=sha(inp/'v1/sources.json'),v1_freeze_sha256=sha(inp/'v1/development-v3/frozen_config.json'),v1_head='d654bd65f834f3903006a97b3074123eda26d236'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--v1-store',required=True);p.add_argument('--store',required=True);a=p.parse_args();prepare(a.v1_store,a.store)
