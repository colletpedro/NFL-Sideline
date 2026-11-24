"""Explicit current acquisition + fixed-model application. No fitting code called."""
import argparse, shutil, urllib.request
import pandas as pd
from common import *
from data import current_frames, identities, renamed, KEEP
from risk_model import predict
from run import load_fixed, package

URLS={'pbp':'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet',
    'ftn':'https://github.com/nflverse/nflverse-data/releases/download/ftn_charting/ftn_charting_2026.parquet',
    'schedule':'https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv',
    'roster':'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2026.parquet'}

def acquire_current(out):
    out=new_dir(out);rows=[]
    for role,url in URLS.items():
        path=out/(role+('.csv' if role=='schedule' else '.parquet'));at=now()
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NFL-Sideline-fixed-XINT-v1'}),timeout=120) as r,path.open('wb') as f:
            headers={k:r.headers.get(k) for k in ['ETag','Last-Modified','Content-Length']};shutil.copyfileobj(r,f)
        rows.append(dict(path=path.name,role=role,url=url,acquiredAt=at,bytes=path.stat().st_size,sha256=sha(path),headers=headers,
            attribution='FTN Data via nflverse' if role=='ftn' else 'nflverse / NFL.com',license='CC BY-SA 4.0' if role=='ftn' else 'nflverse-data CC BY4.0; underlying scope not certified'))
        write(out/'acquisition-progress.json',dict(files=rows))
    write(out/'sources.json',dict(schemaVersion=1,files=rows,acquisitionCompletedAt=now()))

def apply_current(sources,final,out):
    sources=Path(sources);manifest=verify_manifest(sources);fixed,m=load_fixed(final)
    paths={r['role']:sources/r['path'] for r in manifest['files']}
    if set(paths)!=set(URLS) or len(manifest['files'])!=4:raise ValueError('Current source roles invalid')
    d,cov=current_frames(pd.read_parquet(paths['pbp']),renamed(pd.read_parquet(paths['ftn'])),pd.read_csv(paths['schedule']))
    d['is_interception_worthy']=d.is_interception_worthy.astype(int)
    d['interception']=d.interception.astype(int)
    d=identities(d[KEEP],[pd.read_parquet(paths['roster'])]).sort_values(KEY).reset_index(drop=True)
    package(d,predict(m,d),final,out,cov,manifest)

def revisions(previous,current,out):
    if not previous:
        write(out,dict(previous=None,status='No previous package provided; no revision history inferred'));return
    old=pd.read_parquet(Path(previous)/'pass_predictions.parquet').set_index(KEY)
    new=pd.read_parquet(Path(current)/'pass_predictions.parquet').set_index(KEY);changes=[]
    fields=['interception','is_interception_worthy','passer_player_id']+RAW
    for k in old.index.intersection(new.index):
        diff=[c for c in fields if not (old.at[k,c]==new.at[k,c] or (pd.isna(old.at[k,c]) and pd.isna(new.at[k,c])))]
        if diff:changes.append(dict(game_id=k[0],play_id=int(k[1]),fields=diff,before={c:old.at[k,c] for c in diff},after={c:new.at[k,c] for c in diff}))
    write(out,dict(added=[f'{a}:{int(b)}' for a,b in new.index.difference(old.index)],removed=[f'{a}:{int(b)}' for a,b in old.index.difference(new.index)],changed=changes,
        previous_predictions_sha256=sha(Path(previous)/'pass_predictions.parquet'),current_predictions_sha256=sha(Path(current)/'pass_predictions.parquet')))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--final',required=True);a.add_argument('--out',required=True);a.add_argument('--previous');a.add_argument('--sources',help='Previously pinned current source directory; omit to acquire public data');v=a.parse_args()
    out=new_dir(v.out);load_fixed(v.final)
    if v.sources:sources=Path(v.sources)
    else:sources=out/'sources';acquire_current(sources)
    offline();apply_current(sources,v.final,out/'application')
    revisions(v.previous,out/'application',out/'revision.json')
