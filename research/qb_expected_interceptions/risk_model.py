"""P(observed INT | retrospective FTN, authorized context), never M3."""
import pandas as pd
from scipy.special import expit
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from common import *

INPUTS=RAW+['is_interception_worthy']
NUMERIC=NUM+['is_interception_worthy']
FORBIDDEN={'interception','epa','desc','score_differential_post','is_drop','is_catchable_ball',
    'passer_player_id','receiver_player_id','posteam','defteam','air_yards','qb_hit','wp',
    'complete_pass','incomplete_pass','read_thrown','n_pass_rushers','n_blitzers'}

def features(d):
    if set(INPUTS)&FORBIDDEN: raise ValueError('Forbidden feature specification')
    if not d.is_interception_worthy.isin([0,1,True,False]).all(): raise ValueError('FTN input missing/nonbinary')
    x=context_features(d[RAW], 'context')
    x['is_interception_worthy']=d.is_interception_worthy.astype(float)
    return x[NUMERIC+CAT]

def rate(y):
    y=np.asarray(y)
    if len(y)==0 or not np.isin(y,[0,1]).all(): raise ValueError('Empty/invalid rate training target')
    k=int(y.sum()); n=len(y)
    return dict(n=n,events=k,probability=k/n if 0<k<n else (k+.5)/(n+1),boundary_adjusted=k in [0,n])

def fit_reference(train,kind,evaluation_year):
    if kind not in ['B0','B1','B2']:raise ValueError('Unknown reference')
    check_train(train,evaluation_year)
    d=train[train.season.eq(evaluation_year-1)] if kind=='B2' else train
    if d.empty: raise ValueError('Prior complete season absent for B2')
    global_rate=rate(d.interception)
    groups={}
    for flag in [0,1]:
        g=d[d.is_interception_worthy.eq(flag)]
        groups[str(flag)]=dict(**(rate(g.interception) if len(g) else global_rate),fallback_global=not len(g),group_n=len(g))
    return dict(format='xint-ftn-reference-v1',target='interception',risk_input='is_interception_worthy',
        kind=kind,train_years=sorted(d.season.unique().astype(int).tolist()),global_rate=global_rate,groups=groups)

def check_train(d,evaluation_year):
    if d.empty or not d.season.lt(evaluation_year).all(): raise ValueError('Temporal fit leakage/empty training')
    if not d.interception.isin([0,1]).all(): raise ValueError('Missing/nonbinary target')

def blocks(d,year):
    tr=d[d.season.lt(year)&d.season.ge(2022)].copy();ev=d[d.season.eq(year)].copy()
    check_train(tr,year)
    if ev.empty or set(tr.game_id)&set(ev.game_id):raise ValueError('Empty or shared-game temporal blocks')
    if pd.to_datetime(tr.game_date).max()>=pd.to_datetime(ev.game_date).min():raise ValueError('Dates overlap temporal blocks')
    return tr,ev

def fit_context(train,C,evaluation_year):
    check_train(train,evaluation_year);cfg=config();x=features(train)
    prep=ColumnTransformer([
        ('num',Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)),('scale',StandardScaler())]),NUMERIC),
        ('cat',Pipeline([('impute',SimpleImputer(strategy='most_frequent',keep_empty_features=True)),('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),CAT)
    ],remainder='drop',verbose_feature_names_out=True)
    pipe=Pipeline([('preprocess',prep),('logistic',LogisticRegression(C=C,penalty='l2',solver=cfg['solver'],max_iter=cfg['max_iter'],tol=cfg['tol'],random_state=cfg['seed']))])
    pipe.fit(x,train.interception.to_numpy())
    pre=pipe.named_steps['preprocess'];n=pre.named_transformers_['num'];c=pre.named_transformers_['cat'];log=pipe.named_steps['logistic']
    if log.n_iter_.max()>=cfg['max_iter']: raise ValueError('Logistic convergence failed')
    m=dict(format='xint-ftn-logistic-json-v1',kind='C',target='interception',risk_input='is_interception_worthy',C=C,
        train_years=sorted(train.season.unique().astype(int).tolist()),raw_features=INPUTS,numeric_columns=NUMERIC,categorical_columns=CAT,
        median=n.named_steps['impute'].statistics_.tolist(),missing_indicators=n.named_steps['impute'].indicator_.features_.tolist(),
        mean=n.named_steps['scale'].mean_.tolist(),scale=n.named_steps['scale'].scale_.tolist(),
        category_imputation=c.named_steps['impute'].statistics_.tolist(),categories=[v.tolist() for v in c.named_steps['encode'].categories_],
        feature_names=pre.get_feature_names_out().tolist(),coefficients=log.coef_[0].tolist(),intercept=float(log.intercept_[0]),iterations=int(log.n_iter_[0]))
    np.testing.assert_allclose(predict(m,train),pipe.predict_proba(x)[:,1],atol=1e-12,rtol=1e-10)
    return m

def predict(m,d):
    if m.get('target')!='interception' or m.get('risk_input')!='is_interception_worthy':raise ValueError('Wrong model target/risk input; M3 is incompatible')
    if m['format']=='xint-ftn-reference-v1':
        if not d.is_interception_worthy.isin([0,1,True,False]).all():raise ValueError('FTN input absent/nonbinary')
        p=np.full(len(d),m['global_rate']['probability']) if m['kind']=='B0' else np.array([m['groups'][str(int(v))]['probability'] for v in d.is_interception_worthy])
    elif m['format']=='xint-ftn-logistic-json-v1':
        if m['numeric_columns']!=NUMERIC or m['categorical_columns']!=CAT or m['raw_features']!=INPUTS:raise ValueError('Feature schema changed')
        x=features(d);num=x[NUMERIC].to_numpy();missing=np.isnan(num)
        num=np.where(missing,np.asarray(m['median']),num)
        if m['missing_indicators']:num=np.concatenate([num,missing[:,m['missing_indicators']].astype(float)],axis=1)
        num=(num-np.asarray(m['mean']))/np.asarray(m['scale']);cats=[]
        for i,col in enumerate(CAT):
            a=x[col].fillna(m['category_imputation'][i]).to_numpy();cats.extend([(a==v).astype(float) for v in m['categories'][i]])
        z=np.column_stack([num]+cats)
        if not np.isfinite(z).all():raise ValueError('Nonfinite preprocessing')
        p=expit(z@np.asarray(m['coefficients'])+m['intercept'])
    else:raise ValueError('Unsupported transparent model format')
    return valid_prob(p)
