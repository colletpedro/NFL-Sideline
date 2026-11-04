"""Evaluation and conditional game-cluster uncertainty, no model selection."""
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss,brier_score_loss,average_precision_score,roc_auc_score

def metrics(y,p):
 y=np.asarray(y); p=np.asarray(p)
 if p.shape!=y.shape or not np.isfinite(p).all() or not ((p>0)&(p<1)).all(): raise ValueError('Invalid probabilities')
 return dict(n=len(y),positives=int(y.sum()),prevalence=float(y.mean()),expected=float(p.sum()),mean_probability=float(p.mean()),log_loss=float(log_loss(y,p,labels=[0,1])),brier=float(brier_score_loss(y,p)),pr_auc_average_precision=float(average_precision_score(y,p)),roc_auc=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None)

def calibration(y,p,edges):
 z=pd.DataFrame({'y':np.asarray(y),'p':p}); z['bin']=pd.cut(z.p,edges,include_lowest=True,right=False)
 rows=[]
 for b,g in z.groupby('bin',observed=False):
  n=len(g); pos=int(g.y.sum())
  if n:
   rate=pos/n; den=1+1.96**2/n; center=(rate+1.96**2/(2*n))/den; half=1.96*np.sqrt(rate*(1-rate)/n+1.96**2/(4*n*n))/den
   rows.append(dict(bin=str(b),n=n,positives=pos,mean_probability=float(g.p.mean()),observed_rate=rate,wilson_low=center-half,wilson_high=center+half))
  else: rows.append(dict(bin=str(b),n=0,positives=0,mean_probability=None,observed_rate=None,wilson_low=None,wilson_high=None))
 return rows

def paired_game_bootstrap(d,p,p0,reps,seed):
 y=d.is_interception_worthy.to_numpy(); p=np.asarray(p); p0=np.asarray(p0)
 ll=lambda a:-(y*np.log(a)+(1-y)*np.log1p(-a))
 a=pd.DataFrame({'game_id':d.game_id,'n':1,'log_loss':ll(p)-ll(p0),'brier':(y-p)**2-(y-p0)**2}).groupby('game_id').sum().sort_index()
 rng=np.random.default_rng(seed); idx=rng.integers(0,len(a),(reps,len(a))); n=a.n.to_numpy()[idx].sum(axis=1)
 return {c:dict(delta=float(a[c].sum()/a.n.sum()),low=float(np.quantile(a[c].to_numpy()[idx].sum(axis=1)/n,.025)),high=float(np.quantile(a[c].to_numpy()[idx].sum(axis=1)/n,.975))) for c in ['log_loss','brier']}

def groups(d,p,p0):
 z=d.copy(); z['p']=p; z['p0']=p0
 z['distance_group']=pd.cut(z.ydstogo,[-1,3,7,10,100],labels=['1-3','4-7','8-10','11+']).astype(str)
 z['score_group']=pd.cut(z.score_differential,[-101,-9,-1,0,8,101],labels=['trailing9+','trailing1-8','tied','leading1-8','leading9+']).astype(str)
 rows=[]
 for col in ['down','qtr','distance_group','score_group','roof']:
  for val,g in z.groupby(col,dropna=False):
   if g.is_interception_worthy.nunique()<2: continue
   m=metrics(g.is_interception_worthy,g.p); m0=metrics(g.is_interception_worthy,g.p0)
   rows.append(dict(group=col,value=str(val),support_sufficient=len(g)>=200 and int(g.is_interception_worthy.sum())>=10,**m,constant_log_loss=m0['log_loss'],constant_brier=m0['brier']))
 return rows

def qb_aggregate(d,p,reps,seed):
 if d.passer_player_id.isna().any(): raise ValueError('Cannot attribute missing passer')
 p=np.asarray(p)
 if len(p)!=len(d) or not np.isfinite(p).all() or not ((p>0)&(p<1)).all(): raise ValueError('Invalid probabilities')
 z=d.copy(); z['probability']=p; rows=[]; rng=np.random.default_rng(seed)
 for ident,g in z.groupby('passer_player_id',sort=True):
  n=len(g); obs=int(g.is_interception_worthy.sum()); exp=float(g.probability.sum()); games=g.game_id.nunique()
  lo=hi=None
  if games>=3:
   a=g.groupby('game_id',sort=True).agg(n=('play_id','size'),obs=('is_interception_worthy','sum'),exp=('probability','sum')); idx=rng.integers(0,games,(reps,games))
   stat=100*(a.obs.to_numpy()[idx].sum(axis=1)-a.exp.to_numpy()[idx].sum(axis=1))/a.n.to_numpy()[idx].sum(axis=1)
   lo,hi=[float(v) for v in np.quantile(stat,[.025,.975])]
  rows.append(dict(passer_player_id=ident,names=' / '.join(sorted(g.passer_player_name.dropna().unique())),teams=' / '.join(sorted(g.posteam.dropna().unique())),passes=n,games=games,observed=obs,expected=exp,observed_rate=obs/n,expected_rate=exp/n,difference_count=obs-exp,difference_per100=100*(obs-exp)/n,interceptions=int(g.interception.sum()),ci_low_per100=lo,ci_high_per100=hi,ci_games=games,plot_convention_n100=n>=100))
 q=pd.DataFrame(rows)
 assert q.passes.sum()==len(d) and q.observed.sum()==d.is_interception_worthy.sum()
 assert np.isclose(q.expected.sum(),p.sum(),atol=1e-10)
 return q
