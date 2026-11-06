"""Schema 2: separate audited DES, project immutable local presentation; never fits."""
import argparse,datetime,os,sys,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'qb_structure_production'))
from common import sha,read,write,clean,verify,KEY,VERSION as METRIC_VERSION,BASE
from classify import classify as classify_v1
import pandas as pd
import numpy as np
SCHEMA=2
CLASSIFICATION='2.0.0'
CATS=['progression','designed','scramble_drill','scramble','throwaway','sack','indeterminate']
GROUPS={'main':['scramble_drill','scramble'],'S1':['scramble_drill','scramble','throwaway'],'S2':['scramble_drill','scramble','throwaway','sack'],'S3':['scramble_drill']}
SCI=BASE/'editorial/local-artifacts/qb-structure-production-v1/20261105-v1'
STORE=BASE/'editorial/local-artifacts/qb-progression-improvisation-lab-v1'

def classify_v2(r):
 v=classify_v1(r)
 if v['category']=='indeterminate' and v['reason']=='designed_no_progression':
  v.update(category='designed',rule='07_DES_audited_throw')
 return v

def moment():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def metric(g):
 e=pd.to_numeric(g.epa,errors='coerce');e=e[np.isfinite(e)]
 return dict(n=len(g),nEpa=len(e),sumEpa=float(e.sum()) if len(e) else None,meanEpa=float(e.mean()) if len(e) else None,status='unavailable_no_opportunities' if not len(g) else 'unavailable_epa' if not len(e) else 'available')
def summary(g):
 cats={c:metric(g[g.category.eq(c)]) for c in CATS};a=cats['progression'];comparisons={}
 for name,group in GROUPS.items():
  part=g[g.category.isin(group)];b=metric(part);games=g[g.category.isin(['progression']+group)].game_id.nunique()
  diff=a['meanEpa']-b['meanEpa'] if a['meanEpa'] is not None and b['meanEpa'] is not None else None
  status='unavailable_no_opportunities' if not a['n'] or not b['n'] else 'unavailable_epa' if diff is None else 'supported_volume' if a['nEpa']>=100 and b['nEpa']>=25 and games>=5 else 'low_support'
  comparisons[name]=dict(a=a,b=b,difference=diff,status=status,games=games,frequency=100*b['n']/len(g) if len(g) else None)
 return dict(dropbacks=len(g),games=g.game_id.nunique(),nEpa=int(g.epa.notna().sum()),missingCharting=int((~g.charting_present).sum()),categories=cats,comparisons=comparisons,plannedDiagnostic=metric(g[g.category.isin(['progression','designed'])]),indeterminateReasons=g[g.category.eq('indeterminate')].reason.value_counts().to_dict())

def sources_valid(science):
 science=Path(science);m=read(science/'manifest.json')
 for f in m['files']:
  if sha(science/f['path'])!=f['sha256']:raise ValueError('Prior scientific package hash mismatch '+f['path'])
 index=read(science/'index.json');verify(Path(index['sourceManifest']).parent)
 return index,m

def publish(science=SCI/'package-release',store=STORE,activate=True,fail_pointer=False):
 science=Path(science);store=Path(store);si,manifest=sources_valid(science)
 d=pd.read_parquet(science/'plays.parquet');old=d.copy(deep=True)
 labels=pd.DataFrame([classify_v2(r) for r in d.to_dict('records')]);d['previous_category']=d.category;d['previous_rule']=d.rule
 for col in labels:d[col]=labels[col].to_numpy()
 # Only the audited DES residual may change; unchanged scientific fields are exact.
 changed=d.category.ne(old.category);assert old.loc[changed,'reason'].eq('designed_no_progression').all() and d.loc[changed,'category'].eq('designed').all()
 for col in ['epa','player_id','identity_status','event_type','read_thrown','game_id','play_id']:pd.testing.assert_series_equal(d[col],old[col],check_names=False)
 for group in [['progression']]+list(GROUPS.values()):
  a=old.category.isin(group);b=d.category.isin(group);assert a.equals(b);np.testing.assert_array_equal(old.loc[a,'epa'],d.loc[b,'epa'])
 store.mkdir(parents=True,exist_ok=True);run=store/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 lock=store/'.updating';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 before=read(store/'current.json') if (store/'current.json').exists() else None
 try:
  parent=read(science/'fixed.json');identity=dict(schemaVersion=SCHEMA,classificationVersion=CLASSIFICATION,metricVersion=METRIC_VERSION,scientificManifestSha256=sha(science/'manifest.json'),codeSha256=sha(__file__),frozenRules=parent)
  import hashlib,json
  package_id=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
  root=store/'packages'/package_id
  if not root.exists():
   root.mkdir(parents=True);(root/'players').mkdir();d.to_parquet(root/'plays.parquet',index=False)
   hist=[]
   for (season,pid),g in d[d.season.ge(2023)].groupby(['season','player_id'],dropna=False):hist.append(dict(season=season,id=pid,**summary(g)))
   write(root/'history.json',hist)
   current=d[d.season.eq(2026)];players=[]
   for pid,g in current[current.player_id.notna()].groupby('player_id',sort=True):
    meta=dict(id=pid,name=' / '.join(sorted(g.audited_name.dropna().unique())),teams=sorted(g.posteam.unique()),positionClass='qb' if g.position_class.eq('qb').all() else 'other' if g.position_class.eq('other').all() else 'unknown',positions=sorted(g.position.dropna().unique()))
    byGame=[dict(gameId=gid,week=int(part.week.iloc[0]),date=str(part.game_date.iloc[0]),teams=sorted(part.posteam.unique()),**summary(part)) for gid,part in g.groupby('game_id',sort=True)]
    p=dict(**meta,**summary(g),byGame=byGame);players.append(p);plays=[]
    for r in g.to_dict('records'):
     plays.append(dict(id=f"{r['game_id']}:{int(r['play_id'])}",gameId=r['game_id'],playId=int(r['play_id']),week=int(r['week']),date=str(r['game_date']),playerId=pid,name=r['audited_name'],team=r['posteam'],opponent=r['defteam'],quarter=r['qtr'],clock=r['time'],down=r['down'],distance=r['ydstogo'],fieldPosition=r['yardline_100'],fieldLabel=r['yrdln'],scoreDifferential=r['score_differential'],epa=r['epa'],category=r['category'],rule=r['rule'],reason=r['reason'],eventType=r['event_type'],description=r['desc'],raw=r,evidence=dict(source='PBP nflverse + FTN Data via nflverse',gameId=r['game_id'],playId=int(r['play_id']))))
    write(root/f'players/{pid}.json',dict(schemaVersion=SCHEMA,packageId=package_id,player=p,plays=plays))
   cov=read(science/'coverage.json');coverage=next(v for v in cov if v['season']==2026);weeks=sorted(current.week.unique().astype(int).tolist());league={}
   for period in ['all']+list(map(str,weeks)):
    g=current[current.position_class.eq('qb')];g=g if period=='all' else g[g.week.eq(int(period))];league[period]=summary(g)
   source=Path(si['sourceManifest']);write(root/'sources.json',dict(parentManifest=read(source),parentSha256=sha(source),science=identity))
   index=dict(**identity,packageId=package_id,presentationVersion='1.0.0',season=2026,phase='REG',acquiredAt=read(source).get('files',[{}])[0].get('acquiredAt') or '2026-11-05T17:34:52Z',coverage=dict(games=current.game_id.nunique(),weeks=weeks,included=coverage['included'],pending=coverage['pending'],future=coverage['future'],through=str(current.game_date.max()),missingCharting=int((~current.charting_present).sum()),missingEpa=int(current.epa.isna().sum())),summary=summary(current),league=league,players=players,attribution='FTN Data via nflverse, dados transformados CC BY-SA 4.0; PBP/rosters nflverse; sem endosso.',categories=CATS)
   write(root/'index.json',index)
   transition=d.groupby(['season','previous_category','category','reason'],dropna=False).size().rename('n').reset_index();transition.to_csv(root/'classification-transition.csv',index=False)
   write(root/'reconciliation.json',dict(passed=True,population=len(d),mainPopulation=int(d.season.ge(2023).sum()),migrated=int(changed.sum()),currentMigrated=int((changed&d.season.eq(2026)).sum()),currentResidual=int((d.category.eq('indeterminate')&d.season.eq(2026)).sum()),currentQBResidual=int((d.category.eq('indeterminate')&d.season.eq(2026)&d.position_class.eq('qb')).sum()),mainABKeysAndEPAExactlyPreserved=True,identityExactlyPreserved=True))
   write(root/'integrity.json',dict(schemaVersion=SCHEMA,files={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}))
  check_package(root)
  revision=dict(previous=before,packageId=package_id,samePackage=bool(before and before['packageId']==package_id),scienceManifestSha256=sha(science/'manifest.json'))
  if before:
   previous=pd.read_parquet(store/'packages'/before['packageId']/'plays.parquet').set_index(KEY);new=d.set_index(KEY);revision.update(added=[list(k) for k in new.index.difference(previous.index)],removed=[list(k) for k in previous.index.difference(new.index)],changed=[])
   common=previous.index.intersection(new.index)
   for key in common:
    fields=[col for col in d.columns if col not in KEY and not ((pd.isna(previous.at[key,col]) and pd.isna(new.at[key,col])) or previous.at[key,col]==new.at[key,col])]
    if fields:revision['changed'].append(dict(key=list(key),fields=fields))
  write(run/'revision.json',revision)
  if activate:
   pointer=dict(schemaVersion=SCHEMA,packageId=package_id,indexSha256=sha(root/'index.json'),checkedAt=moment());write(run/'next.json',pointer)
   if fail_pointer:raise OSError('Simulated pointer swap failure')
   os.replace(run/'next.json',store/'current.json')
  write(run/'receipt.json',dict(passed=True,packageId=package_id,activated=activate,sourcePackageUnchanged=sha(science/'manifest.json')==identity['scientificManifestSha256']))
  return root
 except Exception as e:
  write(run/'failure.json',dict(error=type(e).__name__,previousPointerPreserved=(read(store/'current.json') if (store/'current.json').exists() else None)==before));raise
 finally:lock.unlink()

def check_package(root):
 root=Path(root);integrity=read(root/'integrity.json')
 for name,h in integrity['files'].items():
  if sha(root/name)!=h:raise ValueError('Presentation package corrupt')
 i=read(root/'index.json');assert i['schemaVersion']==2 and i['classificationVersion']==CLASSIFICATION and i['categories']==CATS
 for p in i['players']:
  detail=read(root/f"players/{p['id']}.json");assert detail['packageId']==i['packageId'] and len(detail['plays'])==p['dropbacks']
  assert sum(v['n'] for v in p['categories'].values())==p['dropbacks']
 return i

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--science',default=str(SCI/'package-release'));a.add_argument('--store',default=str(STORE));a.add_argument('--no-activate',action='store_true');v=a.parse_args();print(publish(v.science,v.store,not v.no_activate))
