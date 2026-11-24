import copy,json
import numpy as np
import pandas as pd
import pytest
from dataset import eligible,reconcile as reconcile_raw,unique,independent,verify_sources,FTN_KEEP
from model import features,fit,export_model,predict_json,FORBIDDEN
from evaluation import qb_aggregate,metrics,paired_game_bootstrap,calibration
from pipeline import temporal
from acquire import sha

def reconcile(p,f):
 return reconcile_raw(p.drop(columns=['is_interception_worthy'],errors='ignore'),f)

def raw(n=8,season=2023):
 return pd.DataFrame([dict(game_id=f'{season}_{i//2+1:02}_A_B',play_id=i+1,season=season,week=i//2+1,season_type='REG',play_type='pass',pass_attempt=1,sack=0,qb_scramble=0,qb_spike=0,play_deleted=0,two_point_attempt=0,passer_player_id='00-0030000',passer_player_name='Same Name',posteam='A' if i<4 else 'B',interception=int(i%4==0),down=i%4+1,qtr=i%4+1,ydstogo=float(i+1),yardline_100=float(20+i),quarter_seconds_remaining=float(100+i*10),score_differential=float(i-3),air_yards=float(i),game_date=f'{season}-09-{i//2+1:02}',is_interception_worthy=i%3==0,penalty=0) for i in range(n)])
def chart(p):
 f=p[['game_id','play_id','is_interception_worthy']].copy(); f['is_throw_away']=False; f['read_thrown']='0'; f['date_pulled']='2026-11-04'; return f

@pytest.mark.parametrize('side',['PBP','FTN'])
def test_duplicate_even_identical_rejected(side):
 p=raw(); f=chart(p)
 if side=='PBP': p=pd.concat([p,p.iloc[:1]])
 else: f=pd.concat([f,f.iloc[:1]])
 with pytest.raises(ValueError,match='duplicate'): reconcile(p,f)
@pytest.mark.parametrize('missing',['null','unmatched'])
def test_label_missing_never_false(missing):
 p=raw(); f=chart(p)
 if missing=='null': f['is_interception_worthy']=f.is_interception_worthy.astype(object); f.loc[0,'is_interception_worthy']=None
 else: f=f.iloc[1:]
 with pytest.raises(ValueError,match='missing label'): reconcile(p,f)
def test_invalid_label():
 p=raw();f=chart(p); f['is_interception_worthy']=f.is_interception_worthy.astype(object);f.loc[0,'is_interception_worthy']='False'
 with pytest.raises(ValueError,match='binary'): reconcile(p,f)
@pytest.mark.parametrize('column,value',[('sack',1),('qb_scramble',1),('qb_spike',1),('play_deleted',1),('two_point_attempt',1),('play_type','no_play'),('pass_attempt',0),('sack',None)])
def test_excluded_population_and_unknown_flags(column,value):
 p=raw();p.loc[0,column]=value;mask,_=eligible(p);assert not mask.iloc[0] and mask.sum()==len(p)-1
def test_penalty_valid_attempt_kept_no_play_excluded_and_throwaway_kept():
 p=raw();p.loc[0,'penalty']=1;p.loc[1,'play_type']='no_play';f=chart(p);f.loc[0,'is_throw_away']=True
 j,_=reconcile(p,f);assert 1 in j.play_id.values and 2 not in j.play_id.values;assert bool(j.loc[j.play_id.eq(1),'is_throw_away'].iloc[0])
def test_w7_boundary_and_postseason_overtime():
 p=raw(season=2026);p.loc[0,'week']=7;p.loc[1,'week']=8;p.loc[2,'season_type']='POST';p.loc[3,'qtr']=5
 m,_=eligible(p);assert m.iloc[0] and not m.iloc[1] and not m.iloc[2] and m.iloc[3]
def test_identity_stable_over_team_and_name_collision():
 p=raw();p.loc[7,'passer_player_id']='00-0030001';q=qb_aggregate(p,np.full(len(p),.1),100,1)
 assert len(q)==2 and q.loc[q.passer_player_id.eq('00-0030000'),'teams'].iloc[0]=='A / B'
 p.loc[0,'passer_player_id']=None;j,info=reconcile(p,chart(p));assert len(j)==7 and info['missing_passer']==1
def test_independent_reconciliation_reads_raw_and_catches_tamper():
 p=raw();f=chart(p);j,_=reconcile(p.drop(columns='is_interception_worthy'),f)
 assert independent(p,f,j)['passed']
 j.loc[0,'is_interception_worthy']=1-j.loc[0,'is_interception_worthy']
 with pytest.raises(AssertionError,match='diverge'):independent(p,f,j)
def test_no_forbidden_features_and_results_cannot_influence_x():
 p=raw();x=features(p,'context'); p2=p.copy()
 for c in FORBIDDEN: p2[c]='forbidden'
 pd.testing.assert_frame_equal(x,features(p2,'context')); assert 'air_yards' not in x and 'air_yards' in features(p,'depth')
def design():return dict(solver='lbfgs',max_iter=2000,tol=1e-9,seed=20261104)
def test_preprocessing_train_only_and_json_match_and_repeatable():
 p=raw(40); p.loc[0,'air_yards']=np.nan; m=fit(p,'depth',.1,design()); art=export_model(m,'depth',.1,[2023]); before=copy.deepcopy(art)
 test=raw();test['air_yards']=1e6;test['ydstogo']=np.nan
 np.testing.assert_allclose(predict_json(art,test),m.predict_proba(features(test,'depth'))[:,1],atol=1e-13)
 assert before==art
 assert art['median'][art['numeric_columns'].index('air_yards')]==float(p.air_yards.median())
 assert export_model(fit(p,'depth',.1,design()),'depth',.1,[2023])==art
 assert json.loads(json.dumps(art))==art

def test_temporal_separation_and_disjoint_games():
 p=pd.concat([raw(season=2022),raw(season=2023)]);a,b=temporal(p,[2022],2023);assert not set(a.game_id)&set(b.game_id)
 with pytest.raises(ValueError,match='reaches'):temporal(p,[2023],2023)
 p.loc[p.season.eq(2022),'game_id']='shared';p.loc[p.season.eq(2023),'game_id']='shared'
 with pytest.raises(ValueError,match='leakage'):temporal(p,[2022],2023)
def test_sum_units_sign_determinism_and_small_support():
 p=raw();probs=np.full(len(p),.1);q=qb_aggregate(p,probs,200,42)
 assert q.expected.sum()==pytest.approx(probs.sum());assert q.difference_per100.iloc[0]==pytest.approx(100*(3-.8)/8)
 assert q.difference_per100.iloc[0]>0;pd.testing.assert_frame_equal(q,qb_aggregate(p,probs,200,42))
 small=qb_aggregate(p.iloc[:2],probs[:2],100,42);assert small.ci_low_per100.isna().all()
 with pytest.raises(ValueError,match='probabilities'):qb_aggregate(p,np.ones(len(p)),100,1)
def test_bootstrap_pairs_games_and_metrics_probability_validation():
 p=raw();v=paired_game_bootstrap(p,np.full(len(p),.2),np.full(len(p),.2),100,3)
 assert v['log_loss']==dict(delta=0.,low=0.,high=0.)
 with pytest.raises(ValueError):metrics([0,1],[np.nan,.2])
 c=calibration([0,1],[.03,.08],[0,.05,.1,1]);assert sum(i['n'] for i in c)==2 and c[-1]['n']==0
def test_frozen_source_tampering_blocks_offline(tmp_path):
 p=tmp_path/'source';p.write_text('a');(tmp_path/'sources.json').write_text(json.dumps({'files':[{'path':'source','sha256':sha(p)}]}));verify_sources(tmp_path)
 p.write_text('b')
 with pytest.raises(ValueError,match='Source changed'):verify_sources(tmp_path)
