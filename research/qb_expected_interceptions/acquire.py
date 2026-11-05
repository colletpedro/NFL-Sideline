"""Explicit public acquisition only; separate pinned copies, incremental receipts."""
import argparse, shutil, urllib.request
from common import *

DOCUMENTS = {
    'pbp_dictionary.csv': 'https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv',
    'ftn_dictionary.csv': 'https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_ftn_charting.csv',
    'ftn_loader.html': 'https://nflreadr.nflverse.com/reference/load_ftn_charting.html',
    'license.md': 'https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md',
}

def prepare(store, v1=V1):
    store=Path(store); store.mkdir(parents=True, exist_ok=True)
    if (store/'sources.json').exists(): verify_manifest(store); return
    records=read(store/'acquisition-progress.json')['files'] if (store/'acquisition-progress.json').exists() else []
    def get(rel, url=None, source=None, source_record=None, role=None):
        path=store/rel; path.parent.mkdir(parents=True,exist_ok=True)
        prior=next((r for r in records if r['path']==rel),None)
        if prior:
            if sha(path)!=prior['sha256']: raise ValueError('Partial acquisition hash changed')
            return
        if path.exists(): raise FileExistsError(f'Unreceipted partial file preserved: {path}')
        at=now(); headers={}
        if source:
            shutil.copyfile(source,path)
        else:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NFL-Sideline-expected-INT-research/1'}),timeout=120) as r, path.open('wb') as f:
                headers={k:r.headers.get(k) for k in ['ETag','Last-Modified','Content-Length']}
                shutil.copyfileobj(r,f)
        record=dict(path=rel,role=role,url=url or source_record.get('url'),copiedAt=at if source else None,
            acquiredAt=source_record.get('acquired_at_utc',source_record.get('acquiredAt')) if source_record else at,
            bytes=path.stat().st_size,sha256=sha(path),headers=headers,
            attribution='FTN Data via nflverse' if 'ftn' in rel else 'nflverse / NFL.com; nflreadr contributors',
            license='CC BY-SA 4.0' if 'ftn' in rel else 'nflverse-data CC BY 4.0; underlying scope not legally certified')
        if source_record and record['sha256']!=source_record['sha256']: raise ValueError('Copy differs from pinned source')
        records.append(record); write(store/'acquisition-progress.json',dict(files=records)); print(rel,record['sha256'],flush=True)
    old=verify_manifest(v1)
    for r in old['files']:
        if r['path'] in [f'raw/{kind}_{year}.parquet' for kind in ['pbp','ftn'] for year in range(2022,2026)]:
            get(r['path'],source=Path(v1)/r['path'],source_record=r,role=f'historical_{r["path"]}')
    for rel,src in [('lineage/v1-sources.json',Path(v1)/'sources.json'),('lineage/historical-dataset.parquet',Path(v1)/'build-v2/dataset.parquet')]:
        get(rel,source=src,source_record=dict(sha256=sha(src),acquiredAt=None),role='lineage')
    active=read(LAB/'current.json'); lab_sources=LAB/'runs/20261104T144706530236Z'
    m=verify_manifest(lab_sources)
    for r in m['files']:
        get('previous-lab/'+r['path'],source=lab_sources/r['path'],source_record=r,role='previous_lab')
    get('lineage/lab-current.json',source=LAB/'current.json',source_record=dict(sha256=sha(LAB/'current.json'),acquiredAt=None),role='lineage')
    urls={'pbp':'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet',
          'ftn':'https://github.com/nflverse/nflverse-data/releases/download/ftn_charting/ftn_charting_2026.parquet',
          'schedule':'https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv'}
    for role,url in urls.items(): get('current/'+role+('.csv' if role=='schedule' else '.parquet'),url=url,role=role)
    for year in range(2022,2027):
        get(f'rosters/{year}.parquet',url=f'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_{year}.parquet',role=f'roster_{year}')
    for name,url in DOCUMENTS.items(): get('documentation/'+name,url=url,role='documentation')
    write(store/'sources.json',dict(schemaVersion=1,acquisitionCompletedAt=now(),files=records,
        originalSourcesManifestSha256=sha(Path(v1)/'sources.json'),historicalRevisions='Pinned 2022–2025 reused unchanged, not redownloaded',
        noPaidServices=True,previousLabPackageId=active['packageId']))
    verify_manifest(store)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--store',default=str(STORE));a.add_argument('--v1',default=str(V1));v=a.parse_args();prepare(v.store,Path(v.v1))
