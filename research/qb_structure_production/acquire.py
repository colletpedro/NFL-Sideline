"""Explicit own source copies or free public downloads; immutable new destination."""
import argparse,datetime,shutil,urllib.request
from common import *

def prepare(out,source=PREVIOUS,refresh=False,year=2026):
 if year!=2026:raise ValueError('v1 update is fixed to current season 2026; a new season needs an explicit source contract')
 source=Path(source);old=verify(source) # verify ALL earlier files before reuse
 out=new(out);rows=[]
 wanted=[r for r in old['files'] if r['path'].startswith(('raw/','rosters/','documentation/','current/'))]
 for r in wanted:
  rel=r['path'];p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);r=dict(r)
  if refresh and (rel.startswith('current/') or rel==f'rosters/{year}.parquet'):
   url=r['url']
   if rel.startswith('current/') and rel!='current/schedule.csv':
    kind='pbp' if 'pbp' in rel else 'ftn'
    url=f'https://github.com/nflverse/nflverse-data/releases/download/{"pbp/play_by_play" if kind=="pbp" else "ftn_charting/ftn_charting"}_{year}.parquet'
   elif rel.startswith('rosters/'):
    url=f'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_{year}.parquet'
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NFL-Sideline-structure-production/1'}),timeout=120) as response,p.open('wb') as f:
    shutil.copyfileobj(response,f);r['headers']={k:response.headers.get(k) for k in ['ETag','Last-Modified','Content-Length']}
   r.update(url=url,acquiredAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=sha(p),bytes=p.stat().st_size)
  else:
   shutil.copyfile(source/rel,p)
   assert sha(p)==r['sha256']
  r['copiedFromManifest']=sha(source/'sources.json');rows.append(r)
  write(out/'acquisition-progress.json',dict(files=rows))
 shutil.copyfile(source/'sources.json',out/'parent-sources.json')
 write(out/'sources.json',dict(schemaVersion=1,files=rows,parentManifestSha256=sha(source/'sources.json'),mode='refresh_current' if refresh else 'verified_copy',currentSeason=year,attribution='FTN Data via nflverse; transformed data CC BY-SA 4.0. PBP/roster/schedule nflverse-data CC BY 4.0; underlying scope not legally certified',classificationVersion=VERSION))
 verify(out);return out

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);a.add_argument('--source',default=str(PREVIOUS));a.add_argument('--refresh-current',action='store_true');a.add_argument('--season',type=int,default=2026);v=a.parse_args();prepare(v.out,v.source,v.refresh_current,v.season)
