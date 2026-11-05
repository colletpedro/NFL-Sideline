"""New observed-INT target metrics and paired game bootstrap, no recalibration."""
import pandas as pd
from sklearn.metrics import log_loss, brier_score_loss, average_precision_score, roc_auc_score
from common import *

def metrics(y,p):
    y=np.asarray(y);p=valid_prob(p)
    if len(y)!=len(p) or not len(y) or not np.isin(y,[0,1]).all():raise ValueError('Invalid observed target')
    obs=int(y.sum());exp=float(p.sum())
    return dict(n=len(y),observed_interceptions=obs,expected_interceptions=exp,observed_expected_ratio=obs/exp,
        prevalence=float(y.mean()),mean_prediction=float(p.mean()),log_loss=float(log_loss(y,p,labels=[0,1])),
        brier=float(brier_score_loss(y,p)),average_precision=float(average_precision_score(y,p)) if obs else None,
        roc_auc=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None)

def performance(d,pred):
    rows=[]
    for group,mask in [('all',np.ones(len(d),dtype=bool)),('ftn_1',d.is_interception_worthy.eq(1).to_numpy()),('ftn_0',d.is_interception_worthy.eq(0).to_numpy())]:
        g=d.loc[mask]
        if len(g):
            for kind,ps in pred.items():rows.append(dict(model=kind,group=group,**metrics(g.interception,np.asarray(ps)[mask])))
    return pd.DataFrame(rows)

def calibration(d,pred):
    rows=[];edges=config()['calibration_edges']
    for kind,ps in pred.items():
        z=d[['interception','is_interception_worthy']].copy();z['p']=ps;z['bin']=pd.cut(z.p,edges,right=False,include_lowest=True)
        for group,g in [('all',z),('ftn_1',z[z.is_interception_worthy.eq(1)]),('ftn_0',z[z.is_interception_worthy.eq(0)])]:
            for b,c in g.groupby('bin',observed=False):
                n=len(c);obs=int(c.interception.sum());exp=float(c.p.sum())
                rows.append(dict(model=kind,group=group,bin=str(b),n=n,observed_interceptions=obs,expected_interceptions=exp,
                    mean_prediction=float(c.p.mean()) if n else None,observed_rate=obs/n if n else None,
                    support_sufficient=n>=200 and obs>=10))
    return pd.DataFrame(rows)

def paired(d,a,b,reps=None,seed=None):
    cfg=config();reps=reps or cfg['bootstrap_replicates'];seed=cfg['seed'] if seed is None else seed
    y=d.interception.to_numpy();a=valid_prob(a);b=valid_prob(b)
    ll=lambda p:-(y*np.log(p)+(1-y)*np.log1p(-p))
    g=pd.DataFrame(dict(game_id=d.game_id.to_numpy(),n=1,log_loss=ll(a)-ll(b),brier=(y-a)**2-(y-b)**2)).groupby('game_id',sort=True).sum()
    rng=np.random.default_rng(seed);idx=rng.integers(0,len(g),(reps,len(g)));den=g.n.to_numpy()[idx].sum(axis=1)
    return {c:dict(delta=float(g[c].sum()/g.n.sum()),low=float(np.quantile(g[c].to_numpy()[idx].sum(axis=1)/den,.025)),
        high=float(np.quantile(g[c].to_numpy()[idx].sum(axis=1)/den,.975)),games=len(g),reps=reps,seed=seed) for c in ['log_loss','brier']}

def comparisons(d,pred):
    result={}
    for group,mask in [('all',np.ones(len(d),dtype=bool)),('ftn_1',d.is_interception_worthy.eq(1).to_numpy()),('ftn_0',d.is_interception_worthy.eq(0).to_numpy())]:
        result[group]={}
        for a,b in [('C','B0'),('C','B1'),('C','B2'),('B1','B0'),('B2','B1')]:
            result[group][a+'-'+b]=paired(d.loc[mask],np.asarray(pred[a])[mask],np.asarray(pred[b])[mask])
    return result

def aggregate(d,ps,model_id):
    z=d.copy();z['p_interception_given_ftn']=valid_prob(ps);rows=[]
    for (year,gsis),g in z.groupby(['season','passer_player_id'],sort=True):
        n=len(g);obs=int(g.interception.sum())
        e1=float(g.loc[g.is_interception_worthy.eq(1),'p_interception_given_ftn'].sum())
        e0=float(g.loc[g.is_interception_worthy.eq(0),'p_interception_given_ftn'].sum())
        expected=e1+e0 # Store this exact decomposition as the canonical total.
        classes=sorted(g.position_class.unique());positions=sorted(g.position.dropna().unique())
        rows.append(dict(model_id=model_id,season=int(year),gsis_id=gsis,name=' / '.join(sorted(g.audited_name.dropna().unique())),
            pbp_names=' / '.join(sorted(g.passer_player_name.dropna().unique())),teams=' / '.join(sorted(g.posteam.unique())),
            position=' / '.join(positions),position_class=classes[0] if len(classes)==1 and len(positions)==1 else 'unknown_or_conflicting',
            period_start=str(g.game_date.min()),period_end=str(g.game_date.max()),weeks=' / '.join(map(str,sorted(g.week.unique().astype(int)))),
            eligible_passes=n,games=g.game_id.nunique(),ftn_interception_worthy_passes=int(g.is_interception_worthy.sum()),
            observed_interceptions=obs,expected_interceptions=expected,expected_from_ftn_1=e1,expected_from_ftn_0=e0,
            observed_in_ftn_1=int(g.loc[g.is_interception_worthy.eq(1),'interception'].sum()),observed_in_ftn_0=int(g.loc[g.is_interception_worthy.eq(0),'interception'].sum()),
            observed_minus_expected=obs-expected,difference_per_100_passes=100*(obs-expected)/n,
            observed_per_100_passes=100*obs/n,expected_per_100_passes=100*expected/n,small_support=n<100,
            coverage='Only included eligible games; see coverage.json; not all official season attempts',player_interval_status='not_estimated'))
    q=pd.DataFrame(rows).sort_values(['season','name','gsis_id']).reset_index(drop=True)
    assert int(q.eligible_passes.sum())==len(d) and int(q.observed_interceptions.sum())==int(d.interception.sum())
    assert np.isclose(q.expected_interceptions.sum(),np.sum(ps),atol=1e-10,rtol=1e-12)
    assert np.array_equal((q.expected_from_ftn_1+q.expected_from_ftn_0).to_numpy(),q.expected_interceptions.to_numpy())
    return q
