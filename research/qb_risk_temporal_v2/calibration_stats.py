"""Proper scores, paired game uncertainty, diagnostic calibration only."""
import numpy as np
import pandas as pd
from scipy.special import expit,logit
from scipy.optimize import brentq
from common import metrics,paired_game_bootstrap

def scores(y,p):
 y=np.asarray(y,dtype=float);p=np.asarray(p,dtype=float)
 if len(y)==0 or y.shape!=p.shape or not np.isfinite(p).all() or not ((p>0)&(p<1)).all() or not np.isin(y,[0,1]).all():raise ValueError('Invalid outcome/probability')
 if 0<y.sum()<len(y):r=metrics(y,p)
 else:r=dict(n=len(y),positives=int(y.sum()),prevalence=float(y.mean()),expected=float(p.sum()),mean_probability=float(p.mean()),log_loss=float(-(y*np.log(p)+(1-y)*np.log1p(-p)).mean()),brier=float(((y-p)**2).mean()),pr_auc_average_precision=float(y.mean()),roc_auc=None)
 r['observed_expected']=float(y.sum()/p.sum());return r

def intercept_shift(y,p):
 y=np.asarray(y,dtype=float);p=np.asarray(p,dtype=float)
 if not (0<y.sum()<len(y)):raise ValueError('Calibration has zero events or zero non-events; finite intercept not identifiable')
 if y.shape!=p.shape or not ((p>0)&(p<1)).all():raise ValueError('Invalid calibration prediction')
 x=logit(p);delta=brentq(lambda a:float(expit(x+a).sum()-y.sum()),-40,40,xtol=1e-13)
 return float(delta)

def _joint_fit(y,x,w,start=None):
 """Batched Newton MLE of diagnostic intercept/slope; no predictive refit."""
 w=np.atleast_2d(w);b=len(w);a=np.full(b,0. if start is None else start[0]);s=np.full(b,1. if start is None else start[1]);valid=np.ones(b,dtype=bool)
 for _ in range(60):
  prob=expit(a[:,None]+s[:,None]*x);v=w*prob*(1-prob);r=w*(prob-y);g0=r.sum(axis=1);g1=(r*x).sum(axis=1);h0=v.sum(axis=1);h1=(v*x).sum(axis=1);h2=(v*x*x).sum(axis=1);det=h0*h2-h1*h1
  good=(det>1e-10)&np.isfinite(det);valid &= good;den=np.where(good,det,1)
  da=(h2*g0-h1*g1)/den;ds=(h0*g1-h1*g0)/den;step=np.maximum(1,np.maximum(np.abs(da),np.abs(ds))/3)
  a-=np.where(good,da/step,0);s-=np.where(good,ds/step,0)
  if not valid.any():break
  if np.max(np.abs(da[valid]))<1e-9 and np.max(np.abs(ds[valid]))<1e-9:break
 if not valid.any():return np.column_stack([np.full(b,np.nan),np.full(b,np.nan)])
 grad0=(w*(expit(a[:,None]+s[:,None]*x)-y)).sum(axis=1);grad1=(w*(expit(a[:,None]+s[:,None]*x)-y)*x).sum(axis=1)
 valid &= np.maximum(np.abs(grad0),np.abs(grad1))<1e-5
 result=np.column_stack([a,s]);result[~valid]=np.nan;return result

def diagnostic_calibration(d,p,reps=2000,seed=20261104):
 y=d.is_interception_worthy.to_numpy(dtype=float);p=np.asarray(p);x=logit(p)
 if y.sum()==0 or y.sum()==len(y):return dict(status='unidentifiable_zero_class',offset_intercept=None,joint_intercept=None,slope=None,bootstrap_valid=0)
 offset=intercept_shift(y,p);flat=np.ptp(x)<1e-10
 point=None if flat else _joint_fit(y,x,np.ones(len(y)))[0]
 ids,game=np.unique(d.game_id.to_numpy(),return_inverse=True);rng=np.random.default_rng(seed);sample=rng.integers(0,len(ids),(reps,len(ids)));counts=np.array([np.bincount(row,minlength=len(ids)) for row in sample]);offsets=[];joint=[]
 for k in range(0,reps,20):
  w=counts[k:k+20,game].astype(float);n=w.sum(axis=1);positive=w@y;valid=(positive>0)&(positive<n)
  a=np.full(len(w),offset)
  if not valid.any():
   offsets.extend([float('nan')]*len(w))
   if not flat:joint.extend([[float('nan'),float('nan')]]*len(w))
   continue
  for _ in range(30):
   prob=expit(x[None,:]+a[:,None]);grad=(w*(prob-y)).sum(axis=1);hess=(w*prob*(1-prob)).sum(axis=1);step=grad/np.maximum(hess,1e-12);a-=np.clip(step,-3,3)
   if np.max(np.abs(step[valid]))<1e-10:break
  a[~valid]=np.nan;offsets.extend(a.tolist())
  if not flat:joint.extend(_joint_fit(y,x,w,start=point).tolist())
 def interval(a):
  z=np.asarray(a);z=z[np.isfinite(z)];return [float(v) for v in np.quantile(z,[.025,.975])] if len(z) else None
 j=np.asarray(joint);valid_joint=int(np.isfinite(j).all(axis=1).sum()) if len(j) else 0
 return dict(status='constant_slope_unidentifiable' if flat else 'diagnostic_only',offset_intercept=offset,offset_intercept_ci=interval(offsets),joint_intercept=None if flat else float(point[0]),joint_intercept_ci=None if flat else interval(j[:,0]),slope=None if flat else float(point[1]),slope_ci=None if flat else interval(j[:,1]),bootstrap_requested=reps,bootstrap_valid_offset=int(np.isfinite(offsets).sum()),bootstrap_valid_joint=valid_joint,method='game bootstrap; diagnostic MLE, not applied to predictions')

def stratified_paired(d,p,p1,reps,seed):
 y=d.is_interception_worthy.to_numpy();p=np.asarray(p);p1=np.asarray(p1);ll=lambda a:-(y*np.log(a)+(1-y)*np.log1p(-a))
 z=pd.DataFrame(dict(season=d.season,game_id=d.game_id,n=1,ll=ll(p)-ll(p1),brier=(y-p)**2-(y-p1)**2));rng=np.random.default_rng(seed);sums={c:np.zeros(reps) for c in ['n','ll','brier']}
 for _,g in z.groupby('season'):
  a=g.groupby('game_id').sum(numeric_only=True).sort_index();idx=rng.integers(0,len(a),(reps,len(a)))
  for c in sums:sums[c]+=a[c].to_numpy()[idx].sum(axis=1)
 result={}
 for c in ['ll','brier']:
  values=sums[c]/sums['n'];result[c]=dict(delta=float(z[c].sum()/len(z)),low=float(np.quantile(values,.025)),high=float(np.quantile(values,.975)))
 return result
