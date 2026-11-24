import json,copy
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from common import blocks,known_only,sha,dump
from calibration_stats import scores,intercept_shift,diagnostic_calibration
from experiment import context_artifact,predict,select
from reserved import maturity,GateError,window_only,reserved_population,evaluate
from identity import classify_positions
from drift import standardize

@pytest.fixture
def data():
 rng=np.random.default_rng(83);rows=[]
 for year in [2022,2023,2024,2025,2026]:
  for i in range(160):
   rows.append(dict(season=year,week=i//40+1,season_type='REG',game_id=f'{year}_{i//20:02}_A_B',play_id=i+1,game_date=f'{year}-09-{i//20+1:02}',is_interception_worthy=int(rng.uniform()<.08),passer_player_id='00-0030000',passer_player_name='Same.Name',posteam='A',interception=0,down=i%4+1,qtr=i%4+1,ydstogo=float(i%15+1),yardline_100=float(i%95+1),quarter_seconds_remaining=float(i*5%900),score_differential=float(i%21-10),air_yards=float(i%30),is_throw_away=False,penalty=0,roof='outdoors',wind=np.nan))
 return pd.DataFrame(rows)

def schedule():
 return pd.DataFrame([dict(season=2026,week=w,game_type='REG',game_id=f'2026_{w}_A_B',gameday=f'2026-11-{w:02}',gametime='20:15',home_score=14,away_score=10,result=4) for w in range(9,14)])

def test_temporal_blocks_and_games(data):
 tr,ca,ev=blocks(data,[2022,2023],2024,2025);assert set(tr.season)=={2022,2023} and set(ca.season)=={2024} and set(ev.season)=={2025}
 assert not set(tr.game_id)&set(ca.game_id) and not set(ca.game_id)&set(ev.game_id)
 for args in [([2024],2024,2025),([2025],None,2025),([2022],2025,2024)]:
  with pytest.raises(ValueError,match='Chronological'):blocks(data,*args)
 data.loc[data.season.eq(2024),'game_id']='shared';data.loc[data.season.eq(2025),'game_id']='shared'
 with pytest.raises(ValueError,match='shared'):blocks(data,[2023],2024,2025)
@pytest.mark.parametrize('week',[0,8,9,13,14])
def test_reserved_never_selection(data,week):
 data.loc[data.season.eq(2026),'week']=week
 with pytest.raises(ValueError,match='Reserved'):known_only(data)
@pytest.mark.parametrize('week',[8,14])
def test_window_rejects_unauthorized_weeks(data,week):
 d=data[data.season.eq(2026)].copy();d['week']=week
 with pytest.raises(GateError,match='Outside'):window_only(d)

def test_prematurity_and_full_mature_window():
 p=schedule();now=datetime(2026,11,4,tzinfo=timezone.utc)
 with pytest.raises(GateError,match='PREMATURE'):maturity(p,p,now)
 good=maturity(p,p,datetime(2027,1,1,tzinfo=timezone.utc));assert good['games']==5
 p.loc[0,'home_score']=np.nan
 with pytest.raises(GateError,match='not complete'):maturity(schedule(),p,datetime(2027,1,1,tzinfo=timezone.utc))
def test_missing_calendar_and_postponement():
 p=schedule();u=p.iloc[:-1]
 with pytest.raises(GateError):maturity(p,u,datetime(2027,1,1,tzinfo=timezone.utc))
 u=p.copy();u.loc[0,'gameday']='2027-01-01'
 with pytest.raises(GateError,match='PREMATURE'):maturity(p,u,datetime(2027,1,4,tzinfo=timezone.utc))

def test_guard_before_any_parquet_read(tmp_path,monkeypatch):
 import reserved
 f=dict(reserved=dict(season=2026,weeks=[9,13],maturity_days_after_latest_kickoff=8),files={},contracts={},code_hashes={})
 (tmp_path/'freeze.json').write_text(json.dumps(f));schedule().to_csv(tmp_path/'reserved_schedule.csv',index=False)
 manifest=dict(purpose='reserved_window_only',season=2026,weeks=[9,13],freeze_sha256=sha(tmp_path/'freeze.json'),files=[dict(role='schedule',path='reserved_schedule.csv',sha256=sha(tmp_path/'reserved_schedule.csv'),acquired_at_utc='2026-11-04T00:00:00+00:00'),dict(role='pbp',path='DO_NOT_OPEN',sha256='x',acquired_at_utc='2026-11-04T00:00:00+00:00'),dict(role='ftn',path='DO_NOT_OPEN_EITHER',sha256='x',acquired_at_utc='2026-11-04T00:00:00+00:00')]);(tmp_path/'manifest.json').write_text(json.dumps(manifest));monkeypatch.setattr(reserved,'utcnow',lambda:datetime(2026,11,4,tzinfo=timezone.utc))
 def forbidden(*a,**k):raise AssertionError('Opened labels before guard')
 monkeypatch.setattr(pd,'read_parquet',forbidden)
 with pytest.raises(GateError,match='PREMATURE'):evaluate(tmp_path,tmp_path/'manifest.json',tmp_path/'out')
 assert not (tmp_path/'out').exists()

def test_intercept_only_adjustment_has_separate_calibration(data):
 tr,ca,ev=blocks(data,[2022,2023],2024,2025);m=context_artifact(tr,ca,[2022,2023],2024);structure=copy.deepcopy(m['structure']);before=predict(m,ev)
 from model import predict_json
 p=predict_json(structure,ca);assert intercept_shift(ca.is_interception_worthy,p)==pytest.approx(m['offset'])
 assert predict(m,ca).sum()==pytest.approx(ca.is_interception_worthy.sum(),abs=1e-8)
 # Evaluation outcomes cannot influence either the offset or preprocessing.
 ev['is_interception_worthy']=1-ev.is_interception_worthy;np.testing.assert_equal(predict(m,ev),before);assert m['structure']==structure
 assert m['structure']['mean'][0]==pytest.approx(tr.ydstogo.mean())
 assert context_artifact(tr,ca,[2022,2023],2024)==m

def test_scores_oe_and_zero_events(data):
 r=scores([0,1,0,1],[.1,.2,.3,.4]);assert r['observed_expected']==pytest.approx(2)
 assert r['log_loss']==pytest.approx(-np.log([.9,.2,.7,.4]).mean())
 z=data.iloc[:20].copy();z['is_interception_worthy']=0;diag=diagnostic_calibration(z,np.full(len(z),.03),10,1);assert diag['slope'] is None and diag['status']=='unidentifiable_zero_class'
 assert scores(z.is_interception_worthy,np.full(len(z),.03))['pr_auc_average_precision']==0
 with pytest.raises(ValueError,match='zero events'):intercept_shift(z.is_interception_worthy,np.full(len(z),.03))
def test_constant_diagnostic_slope_and_determinism(data):
 d=data[data.season.eq(2025)];a=diagnostic_calibration(d,np.full(len(d),.05),40,1);b=diagnostic_calibration(d,np.full(len(d),.05),40,1);assert a==b and a['slope'] is None

def test_position_unknown_conflict_and_stable_id(data):
 p=data[data.season.eq(2026)].copy();r=pd.DataFrame([dict(gsis_id='00-0030000',season=2026,week=1,team='A',game_type='REG',position='QB'),dict(gsis_id='00-0030000',season=2026,week=2,team='A',game_type='REG',position='WR'),dict(gsis_id='00-0030000',season=2026,week=2,team='A',game_type='REG',position='QB')]);t=classify_positions(p,r)
 assert t.loc[t.week.eq(1),'position_class'].iloc[0]=='QB_identified';assert t.loc[t.week.eq(2),'position_class'].iloc[0]=='unknown_or_conflicting';assert t.loc[t.week.eq(3),'position_class'].iloc[0]=='unknown_or_conflicting';assert t.passes.sum()==len(p)

def test_standardization_no_extrapolation_weights(data):
 rows,c,s,m=standardize(data,'coarse',min_n=1);assert max(r['max_weight'] for r in rows)<=5 and all(r['n_common']<=r['n_full'] for r in rows)
 changed=data.copy();changed.loc[changed.season.eq(2026),'ydstogo']=50
 rows,c,s,m=standardize(changed,'coarse',min_n=1);assert all('>10' in k for k in m['included_cells'])

def test_missing_reserved_labels_fail_without_false():
 from dataset import FTN_KEEP
 p=[];f=[]
 for w in range(9,14):
  gid=f'2026_{w}_A_B';p.append(dict(game_id=gid,play_id=1,season=2026,season_type='REG',week=w,play_deleted=0,play_type='pass',pass_attempt=1,sack=0,qb_scramble=0,qb_spike=0,two_point_attempt=0,passer_player_id='00-0030000'))
  f.append(dict(nflverse_game_id=gid,nflverse_play_id=1,season=2026,week=w,is_interception_worthy=None if w==9 else False,is_throw_away=False,read_thrown='0',date_pulled='2027-01-01'))
 with pytest.raises(GateError,match='label/identity'):reserved_population(pd.DataFrame(p),pd.DataFrame(f),[x['game_id'] for x in p])

def test_no_advantage_no_context_promotion_and_2026_excluded(data):
 z=data.copy()
 for c in ['M0','M1','M2','M3']:z[c]=.08
 records=[]
 for year in [2024,2025]:
  for name in ['M2','M3']:
   score=scores(z[z.season.eq(year)].is_interception_worthy,np.full(160,.08));records.append(dict(year=year,candidate=name,model=score,M1=score))
 a=select(records,z);assert a['selected_contextual_candidate'] is None
 z.loc[z.season.eq(2026),'M3']=.999
 assert select(records,z)==a

def test_repeat_opening_refused_before_labels(tmp_path,monkeypatch):
 (tmp_path/'OPENED.json').write_text('{}')
 def forbidden(*a,**k):raise AssertionError('Repeat opened labels')
 monkeypatch.setattr(pd,'read_parquet',forbidden)
 with pytest.raises(GateError,match='already opened'):evaluate(tmp_path,tmp_path/'missing_manifest',tmp_path/'out')

def test_bootstrap_rare_events_reports_invalid_replicates(data):
 d=data.iloc[:80].copy();d['is_interception_worthy']=0;d.iloc[0,d.columns.get_loc('is_interception_worthy')]=1
 result=diagnostic_calibration(d,np.full(len(d),.02),40,2)
 assert result['bootstrap_valid_offset']<40 and result['bootstrap_valid_offset']>0

def test_frozen_model_manifest_tampering(tmp_path):
 from reserved import validate_bundle
 from common import protocol
 f=dict(reserved=protocol()['reserved'],files={'M1.json':'wrong'},contracts={},code_hashes={});(tmp_path/'M1.json').write_text('{}');(tmp_path/'freeze.json').write_text(json.dumps(f))
 with pytest.raises(GateError,match='hash differs'):validate_bundle(tmp_path)

def test_position_other_is_not_removed(data):
 p=data[data.season.eq(2026)].copy();r=pd.DataFrame([dict(gsis_id='00-0030000',season=2026,week=w,team='A',game_type='REG',position='WR') for w in range(1,5)])
 t=classify_positions(p,r);assert set(t.position_class)=={'other_position'} and t.passes.sum()==len(p)

def test_v1_code_and_document_paths_not_modified():
 import subprocess
 root=Path(__file__).resolve().parents[3]
 changed=subprocess.check_output(['git','diff','d654bd65f834f3903006a97b3074123eda26d236','--','research/qb_interception_risk','docs/plans/qb-interception-risk-baseline-v1'],cwd=root,text=True)
 assert changed==''

def test_future_acquisition_refuses_network_before_maturity(tmp_path,monkeypatch):
 import acquire_reserved as a
 monkeypatch.setattr(a,'validate_bundle',lambda p:{})
 monkeypatch.setattr(a,'utcnow',lambda:datetime(2026,11,4,tzinfo=timezone.utc));schedule().to_csv(tmp_path/'reserved_schedule.csv',index=False)
 def forbidden(*args,**kwargs):raise AssertionError('Premature network acquisition')
 monkeypatch.setattr(a.urllib.request,'urlopen',forbidden)
 with pytest.raises(GateError,match='PREMATURE'):a.acquire(tmp_path,tmp_path/'not_created')
 assert not (tmp_path/'not_created').exists()
