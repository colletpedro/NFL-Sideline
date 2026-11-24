"""Fixed features, train-only preprocessing, safe JSON serialization; no pickle."""
import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

RAW=['down','qtr','ydstogo','yardline_100','quarter_seconds_remaining','score_differential']
CAT=['down','qtr']
NUM=['ydstogo','log_ydstogo','yardline_100','redzone_distance','quarter_seconds_remaining','score_differential','deficit','end_half','deficit_end_half']
DEPTH=['air_yards','air_negative','air_above20']
FORBIDDEN={'interception','epa','wp','qb_hit','complete_pass','incomplete_pass','is_interception_worthy','passer_player_id','receiver_player_id','posteam','defteam','desc','score_differential_post','read_thrown','is_drop','is_catchable_ball','qb_location','wind','temp'}

def features(d,variant):
 if variant not in ['context','depth']: raise ValueError('Unknown variant')
 required=RAW+(['air_yards'] if variant=='depth' else [])
 x=d[required].astype(float).copy()
 x['log_ydstogo']=np.log1p(x.ydstogo)
 x['redzone_distance']=(20-x.yardline_100).clip(lower=0)
 x['deficit']=(-x.score_differential).clip(lower=0)
 x['end_half']=((x.qtr.isin([2,4]))&x.quarter_seconds_remaining.le(120)).astype(float)
 # Preserve missing state rather than infer end-half from a missing clock/quarter.
 x.loc[x.qtr.isna()|x.quarter_seconds_remaining.isna(),'end_half']=np.nan
 x['deficit_end_half']=x.deficit*x.end_half
 if variant=='depth':
  x['air_negative']=(-x.air_yards).clip(lower=0); x['air_above20']=(x.air_yards-20).clip(lower=0)
 cols=NUM+(DEPTH if variant=='depth' else [])+CAT
 assert not (set(cols)&FORBIDDEN)
 return x[cols]

def fit(d,variant,C,design):
 x=features(d,variant); num=NUM+(DEPTH if variant=='depth' else [])
 prep=ColumnTransformer([
  ('num',Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)),('scale',StandardScaler())]),num),
  ('cat',Pipeline([('impute',SimpleImputer(strategy='most_frequent',keep_empty_features=True)),('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),CAT)
 ],remainder='drop',verbose_feature_names_out=True)
 pipe=Pipeline([('preprocess',prep),('logistic',LogisticRegression(C=C,penalty='l2',solver=design['solver'],max_iter=design['max_iter'],tol=design['tol'],random_state=design['seed']))])
 pipe.fit(x,d.is_interception_worthy.to_numpy())
 if pipe.named_steps['logistic'].n_iter_.max()>=design['max_iter']: raise ValueError('Convergence failure')
 return pipe

def export_model(pipe,variant,C,train_years):
 prep=pipe.named_steps['preprocess']; n=prep.named_transformers_['num']; c=prep.named_transformers_['cat']; log=pipe.named_steps['logistic']
 return dict(format='qb-iw-json-logistic-v1',variant=variant,C=C,train_years=train_years,raw_features=RAW+(['air_yards'] if variant=='depth' else []),numeric_columns=NUM+(DEPTH if variant=='depth' else []),categorical_columns=CAT,median=n.named_steps['impute'].statistics_.tolist(),missing_indicators=n.named_steps['impute'].indicator_.features_.tolist(),mean=n.named_steps['scale'].mean_.tolist(),scale=n.named_steps['scale'].scale_.tolist(),category_imputation=c.named_steps['impute'].statistics_.tolist(),categories=[v.tolist() for v in c.named_steps['encode'].categories_],feature_names=prep.get_feature_names_out().tolist(),coefficients=log.coef_[0].tolist(),intercept=float(log.intercept_[0]),iterations=int(log.n_iter_[0]))

def predict_json(model,d):
 if model['format']!='qb-iw-json-logistic-v1': raise ValueError('Unsupported model format')
 x=features(d,model['variant']); num=x[model['numeric_columns']].to_numpy(); missing=np.isnan(num)
 num=np.where(missing,np.asarray(model['median']),num)
 if model['missing_indicators']: num=np.concatenate([num,missing[:,model['missing_indicators']].astype(float)],axis=1)
 num=(num-np.asarray(model['mean']))/np.asarray(model['scale'])
 cats=[]
 for i,c in enumerate(model['categorical_columns']):
  a=x[c].fillna(model['category_imputation'][i]).to_numpy()
  cats.extend([(a==v).astype(float) for v in model['categories'][i]])
 z=np.column_stack([num]+cats)
 if not np.isfinite(z).all(): raise ValueError('Nonfinite feature after preprocessing')
 return expit(z@np.asarray(model['coefficients'])+model['intercept'])
