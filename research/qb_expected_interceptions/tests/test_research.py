import json
import numpy as np
import pandas as pd
import pytest
from common import eligible, KEY, ROOT
from data import join, validate_rows, independent, identities
from risk_model import features, fit_context, predict, fit_reference, blocks, INPUTS, FORBIDDEN
from evaluate import aggregate, paired, metrics, performance, calibration

@pytest.fixture
def current(passes):
    from data import renamed
    p,f=raw(passes);p=p.copy();f=f.copy()
    for d in [p,f]:
        d['season']=2026;d['game_id']=d.game_id.str.replace('2022','2026')
    p['game_date']=p.week.map({1:'2026-09-13',2:'2026-09-20'})
    p['home_team']='B';p['away_team']='A';p['total_home_score']=0;p['total_away_score']=0
    endings=p.groupby('game_id').tail(1).copy();endings['desc']='END GAME';endings['play_type']='no_play';endings['play_id']+=5000
    p=pd.concat([p,endings],ignore_index=True)
    s=pd.DataFrame([dict(game_id=f'2026_{i+1:02}_A_B',season=2026,game_type='REG',week=i+1,
        gameday='2026-09-13' if i==0 else '2026-09-20',home_team='B',away_team='A',
        home_score=0 if i<2 else np.nan,away_score=0 if i<2 else np.nan,result=0 if i<2 else np.nan) for i in range(272)])
    r=pd.DataFrame([dict(gsis_id='00-0000001',season=2026,week=w,team='A',game_type='REG',position='QB',full_name='Actual QB') for w in [1,2]])
    return p,f,s,r

@pytest.fixture
def passes():
    rng=np.random.default_rng(71);n=240
    d=pd.DataFrame(dict(game_id=['2022_01_A_B']*120+['2022_02_A_B']*120,play_id=np.arange(n),
        season=2022,season_type='REG',week=np.repeat([1,2],120),game_date=np.repeat(['2022-09-11','2022-09-18'],120),
        play_type='pass',pass_attempt=1,play_deleted=0,sack=0,qb_scramble=0,qb_spike=0,two_point_attempt=0,
        passer_player_id='00-0000001',passer_player_name='A.QB',posteam='A',defteam='B',
        down=rng.integers(1,5,n),qtr=rng.integers(1,6,n),ydstogo=rng.integers(1,20,n),yardline_100=rng.integers(1,100,n),
        quarter_seconds_remaining=rng.integers(1,900,n),score_differential=0,posteam_score=0,defteam_score=0,
        is_interception_worthy=np.tile([1,1,0,0],n//4),interception=np.tile([1,0,1,0],n//4),
        desc='audit-only text',penalty=0,penalty_type=None,aborted_play=0,complete_pass=0,incomplete_pass=1,
        audited_name='Audited QB',position='QB',position_class='qb'))
    return d

def raw(d):return d.drop(columns=['is_interception_worthy']),d[KEY+['season','week','is_interception_worthy']]

def test_join_unique_cardinality_and_four_crosses(passes):
    p,f=raw(passes);d=join(p,f);assert len(d)==len(p)
    tables,receipt=independent(p,f,d);assert receipt['passed']
    assert tables['season'].n.tolist()==[60]*4
    assert tables['season'].denominator.tolist()==[240]*4
    assert tables['season'].group_denominator.tolist()==[120]*4
    for side in ['p','f']:
        with pytest.raises(ValueError,match='duplicate'):
            join(pd.concat([p,p.iloc[:1]]) if side=='p' else p,pd.concat([f,f.iloc[:1]]) if side=='f' else f)

@pytest.mark.parametrize('column,value',[('play_deleted',1),('play_deleted',np.nan),('play_type','no_play'),('pass_attempt',0),('sack',1),('qb_scramble',1),('qb_spike',1),('two_point_attempt',1),('season_type','POST')])
def test_eligibility_exact_explicit_flags(passes,column,value):
    passes.loc[0,column]=value;assert not eligible(passes).iloc[0];assert eligible(passes).iloc[1:].all()

def test_overtime_penalty_and_ftn_zero_retained(passes):
    passes['qtr']=5;passes['penalty']=1;p,f=raw(passes);d=validate_rows(join(p,f))
    assert len(d)==240 and d.is_interception_worthy.eq(0).sum()==120

@pytest.mark.parametrize('column',['interception','is_interception_worthy','passer_player_id'])
def test_missing_target_risk_identity_fail_without_imputation(passes,column):
    passes.loc[0,column]=np.nan
    with pytest.raises(ValueError,match='Missing'):validate_rows(passes)

def test_missing_ftn_join_stays_missing(passes):
    p,f=raw(passes);d=join(p,f.iloc[1:]);assert pd.isna(d.is_interception_worthy.iloc[0])
    with pytest.raises(ValueError):validate_rows(d)

def test_temporal_metadata_and_invalid_target(passes):
    p,f=raw(passes);f.loc[0,'week']=8
    with pytest.raises(ValueError,match='temporal'):join(p,f)
    p.loc[0,'interception']=2;f.loc[0,'week']=1
    with pytest.raises(ValueError,match='Nonbinary'):join(p,f)

def test_temporal_blocks_and_game_exclusivity(passes):
    future=passes.copy();future['season']=2023;future['game_id']=future.game_id.str.replace('2022','2023');future['game_date']='2023-09-17'
    tr,ev=blocks(pd.concat([passes,future]),2023);assert set(tr.game_id).isdisjoint(ev.game_id)
    with pytest.raises(ValueError,match='Temporal'):fit_context(future,.1,2023)
    future['game_id']=passes.game_id
    with pytest.raises(ValueError,match='shared-game'):blocks(pd.concat([passes,future]),2023)

def test_preprocessing_train_only_and_forbidden_columns(passes):
    passes.loc[0,'ydstogo']=np.nan;m=fit_context(passes,.1,2023);assert set(INPUTS).isdisjoint(FORBIDDEN)
    shifted=passes.copy();shifted['ydstogo']=99
    snapshot=json.dumps(m,sort_keys=True);predict(m,shifted);assert json.dumps(m,sort_keys=True)==snapshot
    altered=passes.copy()
    for c in FORBIDDEN:altered[c]=777 if c!='desc' else 'INTERCEPTED secret audit text'
    np.testing.assert_array_equal(predict(m,passes),predict(m,altered))
    assert not set(features(passes).columns)&FORBIDDEN

def test_group_references_and_recent_season(passes):
    d=passes.copy();d.loc[d.is_interception_worthy.eq(1),'interception']=1
    d.loc[d.is_interception_worthy.eq(0),'interception']=0
    m=fit_reference(d,'B1',2023);p=predict(m,d)
    assert p[d.is_interception_worthy.eq(1)].mean()>.9 and p[d.is_interception_worthy.eq(0)].mean()<.01
    newer=d.copy();newer['season']=2023;newer['interception']=1-newer.interception
    recent=fit_reference(pd.concat([d,newer]),'B2',2024)
    assert recent['train_years']==[2023] and recent['groups']['0']['probability']>.9
    with pytest.raises(ValueError,match='Prior complete'):fit_reference(d,'B2',2024)

def test_absent_group_zero_events_boundary_support(passes):
    d=passes.copy();d['is_interception_worthy']=0;d['interception']=0
    for k in ['B0','B1','B2']:
        m=fit_reference(d,k,2023);p=predict(m,passes);assert np.all((p>0)&(p<1))
        assert m['groups']['1']['fallback_global'] and m['groups']['1']['group_n']==0
    with pytest.raises(ValueError):fit_reference(d.iloc[:0],'B0',2023)

def test_sum_decomposition_sign_units_trades_small_zero(passes):
    passes.loc[0,'passer_player_id']='00-0000002';passes.loc[0,'interception']=0
    passes.loc[1:10,'posteam']='C';p=np.full(len(passes),.1);q=aggregate(passes,p,'XINT-test')
    assert q.expected_interceptions.sum()==pytest.approx(p.sum())
    assert np.array_equal(q.expected_from_ftn_1+q.expected_from_ftn_0,q.expected_interceptions)
    a=q[q.gsis_id.eq('00-0000002')].iloc[0];assert a.eligible_passes==1 and a.observed_interceptions==0
    assert a.observed_minus_expected==-.1 and a.difference_per_100_passes==-10 and a.small_support
    assert a.player_interval_status=='not_estimated'
    assert q[q.gsis_id.eq('00-0000001')].teams.iloc[0]=='A / C'

def test_weekly_position_and_team_not_name(passes):
    r=pd.DataFrame([dict(gsis_id='00-0000001',season=2022,week=w,team='A',game_type='REG',position='QB',full_name='Actual QB') for w in [1,2]])
    q=identities(passes,[r]);assert q.position_class.eq('qb').all();assert q.audited_name.eq('Actual QB').all()
    q=identities(passes.assign(posteam='C'),[r]);assert q.position_class.eq('unknown_or_conflicting').all()
    r=pd.concat([r,r.assign(position='WR')]);assert identities(passes,[r]).position_class.eq('unknown_or_conflicting').all()

def test_determinism_json_roundtrip_and_m3_rejection(passes):
    a=fit_context(passes,.1,2023);b=fit_context(passes,.1,2023);assert a==b
    np.testing.assert_array_equal(predict(a,passes),predict(json.loads(json.dumps(a)),passes))
    with pytest.raises(ValueError,match='M3'):predict(dict(target='is_interception_worthy'),passes)
    assert a['format'].startswith('xint-') and a['target']=='interception'

def test_metrics_groups_bootstrap_deterministic_zero_events(passes):
    p=np.full(len(passes),.3);p0=np.full(len(passes),.2)
    a=paired(passes,p,p0,reps=100,seed=17);assert a==paired(passes,p,p0,reps=100,seed=17)
    assert a['log_loss']['games']==2 and a['log_loss']['delta']<0
    pm=performance(passes,{'B1':p});assert set(pm.group)=={'all','ftn_0','ftn_1'}
    cal=calibration(passes,{'B1':p});assert cal[cal.group.eq('all')].n.sum()==len(passes)
    assert metrics(np.zeros(3),np.full(3,.1))['average_precision'] is None
    with pytest.raises(ValueError):metrics([0],[0])

def test_pinned_research_and_product_no_import_of_new_model():
    for base in [ROOT/'web-ui/src',ROOT/'etl-pipeline/src',ROOT/'core-api/src']:
        for p in base.rglob('*'):
            if p.is_file():assert b'qb_expected_interceptions' not in p.read_bytes()

@pytest.mark.parametrize('missing',['chart','target','gsis','context','end_marker'])
def test_partial_week_keeps_other_valid_game_and_records_gap(current,missing):
    from data import current_frames
    p,f,s,r=current
    if missing=='chart':f=f.iloc[1:]
    elif missing=='target':p.loc[0,'interception']=np.nan
    elif missing=='gsis':p.loc[0,'passer_player_id']=None
    elif missing=='context':p.loc[0,'down']=np.nan
    else:p.loc[p.game_id.eq('2026_01_A_B')&p.desc.eq('END GAME'),'desc']='not finalized'
    d,cov=current_frames(p,f,s)
    assert cov['included_games']==1 and len(cov['pending_games'])==1
    assert set(d.game_id)=={'2026_02_A_B'} and cov['pending_games'][0]['game_id']=='2026_01_A_B'

def test_current_final_score_conflict_is_fatal(current):
    from data import current_frames
    p,f,s,r=current;p.loc[p.desc.eq('END GAME'),'total_home_score']=6
    with pytest.raises(ValueError,match='score'):current_frames(p,f,s)

def test_update_applies_fixed_model_without_any_fit(current,tmp_path,monkeypatch):
    from common import write,sha,HERE,read
    from update import apply_current
    import run
    p,f,s,r=current;src=tmp_path/'sources';src.mkdir();p.to_parquet(src/'pbp.parquet',index=False);f.to_parquet(src/'ftn.parquet',index=False);s.to_csv(src/'schedule.csv',index=False);r.to_parquet(src/'roster.parquet',index=False)
    records=[dict(role=role,path=role+('.csv' if role=='schedule' else '.parquet'),sha256=sha(src/(role+('.csv' if role=='schedule' else '.parquet'))),bytes=(src/(role+('.csv' if role=='schedule' else '.parquet'))).stat().st_size) for role in ['pbp','ftn','schedule','roster']]
    write(src/'sources.json',dict(files=records))
    d=p[p.play_type.eq('pass')].merge(f[KEY+['is_interception_worthy']],on=KEY,validate='one_to_one');d['season']=2025
    final=tmp_path/'final';final.mkdir();m=fit_reference(d,'B2',2026);m['model_id']='XINT-test-fixed';write(final/'model.json',m)
    write(final/'fixed.json',dict(model_id=m['model_id'],selected='B2',model_sha256=sha(final/'model.json'),code_sha256={q.name:sha(q) for q in [HERE/'common.py',HERE/'risk_model.py']}))
    def no_fit(*a,**kw):raise AssertionError('Data updates cannot fit models')
    monkeypatch.setattr(run,'fit_reference',no_fit);monkeypatch.setattr(run,'fit_context',no_fit)
    apply_current(src,final,tmp_path/'application')
    q=read(tmp_path/'application/consumer/index.json');assert q['model']['model_sha256']==sha(final/'model.json')
    for player in q['players']:
        assert player['expected_interceptions']==player['expected_from_ftn_1']+player['expected_from_ftn_0']
    before=sha(final/'model.json')
    with pytest.raises(FileExistsError):apply_current(src,final,tmp_path/'application')
    assert sha(final/'model.json')==before

def test_wrong_fixed_model_hash_refused_before_inference(tmp_path):
    from common import write
    from run import load_fixed
    write(tmp_path/'model.json',dict(target='interception'))
    write(tmp_path/'fixed.json',dict(model_sha256='bad'))
    with pytest.raises(ValueError,match='hash'):load_fixed(tmp_path)
