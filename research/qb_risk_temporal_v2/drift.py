"""Descriptive composition and direct standardization, no causal decomposition."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from common import known_only,dump,sha,protocol

def diagnostic_bins(d):
 x=pd.DataFrame(index=d.index)
 x['down']=d.down.astype(str)
 for name,col,edges,labels in [
  ('distance','ydstogo',[-1,3,7,10,100],['<=3','4-7','8-10','>10']),
  ('field','yardline_100',[-1,20,50,80,101],['<=20','21-50','51-80','>80']),
  ('clock','quarter_seconds_remaining',[-1,120,300,900],['<=120','121-300','>300']),
  ('score','score_differential',[-101,-9,-1,0,8,101],['behind9+','behind1-8','tied','ahead1-8','ahead9+']),
  ('depth','air_yards',[-101,-.0001,9.999,19.999,101],['<0','0-9','10-19','20+'])]:
  x[name]=pd.cut(d[col],edges,labels=labels).astype(object).fillna('unknown')
 x['quarter']=d.qtr.astype(str);x['throwaway']=d.is_throw_away.astype(str);x['penalty']=d.penalty.astype(str);x['roof']=d.roof.fillna('unknown');x['wind_observed']=d.wind.notna().astype(str)
 return x

def cells(d,spec):
 down=np.where(d.down.le(2),'d12','d34');score=np.where(d.score_differential.lt(0),'behind','not_behind')
 if spec=='coarse':dist=np.where(d.ydstogo.le(10),'<=10','>10');return pd.Series(down+'|'+dist+'|'+score,index=d.index)
 dist=np.select([d.ydstogo.le(7),d.ydstogo.le(10)],['<=7','8-10'],default='>10')
 field=np.select([d.yardline_100.le(20),d.yardline_100.le(80)],['red','middle'],default='own20')
 quarter=np.where(d.qtr.le(3),'q123','q4ot')
 return pd.Series(down+'|'+dist+'|'+field+'|'+quarter+'|'+score,index=d.index)

def standardize(d,spec,min_n=30,cap=5):
 known_only(d);z=d[['season','is_interception_worthy']].copy();z['cell']=cells(d,spec)
 tab=z.groupby(['cell','season']).agg(n=('is_interception_worthy','size'),y=('is_interception_worthy','sum')).reset_index();counts=tab.pivot(index='cell',columns='season',values='n').fillna(0)
 initial=list(counts.index[(counts>=min_n).all(axis=1)]);keep=initial.copy();removed=[]
 while keep:
  c=counts.loc[keep];ref=c[[2023,2024,2025]].sum(axis=1);ref=ref/ref.sum();freq=c/c.sum(axis=0);weights=freq.rdiv(ref,axis=0)
  bad=list(weights.index[weights.max(axis=1).gt(cap)])
  if not bad:break
  removed.extend(bad);keep=[c for c in keep if c not in bad]
 if not keep:raise ValueError('No common support after predeclared cell constraints')
 rates=tab.pivot(index='cell',columns='season',values='y').loc[keep]/counts.loc[keep];rows=[]
 for year,g in d.groupby('season'):
  n=int(counts.loc[keep,year].sum());w=weights[year];ess=float(n*n/np.sum(counts.loc[keep,year]*w*w));raw=float((rates[year]*counts.loc[keep,year]).sum()/n);std=float((ref*rates[year]).sum())
  rows.append(dict(spec=spec,season=int(year),n_full=len(g),y_full=int(g.is_interception_worthy.sum()),prevalence_full=float(g.is_interception_worthy.mean()),n_common=n,excluded=len(g)-n,retained_fraction=n/len(g),y_common=int(tab[tab.season.eq(year)&tab.cell.isin(keep)].y.sum()),prevalence_common=raw,standardized=std,min_weight=float(w.min()),max_weight=float(w.max()),effective_sample_size=ess,cells=len(keep)))
 cellout=tab.copy();cellout['included']=cellout.cell.isin(keep);cellout['reference_weight']=cellout.cell.map(ref);cellout['density_weight']=[float(weights.loc[r.cell,r.season]) if r.cell in keep else None for r in cellout.itertuples()]
 summary=[];a=next(x for x in rows if x['season']==2022)
 for year in [2023,2024,2025,2026]:
  b=next(x for x in rows if x['season']==year);raw_drop=a['prevalence_common']-b['prevalence_common'];std_drop=a['standardized']-b['standardized']
  summary.append(dict(spec=spec,from_year=2022,to_year=year,raw_drop_same_support=raw_drop,standardized_drop=std_drop,composition_associated_difference=raw_drop-std_drop,fraction_of_same_support_drop=(raw_drop-std_drop)/raw_drop if abs(raw_drop)>1e-12 else None,notice='descriptive, not causal; no extrapolation; reference/cell specification conditional'))
 return rows,cellout,summary,dict(spec=spec,all_cells=len(counts),initial_common_cells=len(initial),removed_by_weight=removed,included_cells=keep,min_cell_n=min_n,max_weight=cap,empty_or_low_support_cells_removed=len(counts)-len(initial),reference_years=[2023,2024,2025])

def run_drift(d,source_manifest,audit,out):
 out=Path(out);out.mkdir(parents=True);known_only(d);b=diagnostic_bins(d);rows=[]
 for col in b:
  z=d[['season','is_interception_worthy','game_id']].copy();z['level']=b[col]
  for (year,level),g in z.groupby(['season','level'],dropna=False):rows.append(dict(group=col,level=str(level),season=int(year),n=len(g),y=int(g.is_interception_worthy.sum()),prevalence=float(g.is_interception_worthy.mean()),games=g.game_id.nunique(),fraction=len(g)/int(d.season.eq(year).sum()),support_sufficient=len(g)>=200 and g.is_interception_worthy.sum()>=10))
 pd.DataFrame(rows).to_csv(out/'composition.csv',index=False)
 std=[];decomp=[];meta=[]
 for spec in ['primary','coarse']:
  r,c,s,m=standardize(d,spec);std+=r;decomp+=s;meta.append(m);c.to_csv(out/f'standardization_cells_{spec}.csv',index=False)
 pd.DataFrame(std).to_csv(out/'standardization.csv',index=False);dump(out/'standardization_differences.json',decomp);dump(out/'standardization_contract.json',meta)
 summary=d.groupby('season').agg(n=('game_id','size'),positive=('is_interception_worthy','sum'),games=('game_id','nunique'),passers=('passer_player_id','nunique'),weeks=('week','nunique')).reset_index();summary['prevalence']=summary.positive/summary.n;summary.to_csv(out/'population.csv',index=False)
 m=json.loads(Path(source_manifest).read_text());files=[x for x in m['files'] if x['kind'] in ['pbp','ftn']];schemas=[]
 for kind in ['pbp','ftn']:
  base=next(x for x in files if x['kind']==kind)
  for x in files:
   if x['kind']==kind:schemas.append(dict(kind=kind,season=x['season'],columns=len(x['schema']),added=sorted(set(x['schema'])-set(base['schema'])),removed=sorted(set(base['schema'])-set(x['schema'])),types_changed={k:[base['schema'][k],x['schema'][k]] for k in set(base['schema'])&set(x['schema']) if base['schema'][k]!=x['schema'][k]},acquired_at=x['acquired_at_utc'],sha256=x['sha256']))
 dump(out/'schema_comparison.json',schemas);dump(out/'integrity_v1_reconciled.json',json.loads(Path(audit).read_text()))
