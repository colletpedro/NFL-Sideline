"""Offline, tiny fixtures. No downloads or model fitting."""
import copy,json,sys
from pathlib import Path
import pandas as pd
import numpy as np
import pytest
from research.qb_risk_lab import pipeline as p

@pytest.fixture
def frames(monkeypatch):
 monkeypatch.setattr(p,'probabilities',lambda model,d:np.full(len(d),.1))
 sc=pd.DataFrame([dict(game_id=f'2026_{i//16+1:02}_{i:03}_AAA',season=2026,game_type='REG',week=i//16+1,home_team='AAA',away_team='BBB',gameday='2026-09-01',home_score=20 if i<3 else None,away_score=10 if i<3 else None,result=10 if i<3 else None) for i in range(272)])
 rows=[]
 for i in range(3):
  rows.append(dict(season=2026,season_type='REG',week=1,game_id=sc.iloc[i].game_id,play_id=1,play_type='pass',pass_attempt=1,play_deleted=0,sack=0,qb_spike=0,qb_scramble=0,two_point_attempt=0,passer_player_id='00-0000001',passer_player_name='Test',posteam='AAA' if i<2 else 'BBB',defteam='BBB' if i<2 else 'AAA',down=1,qtr=1,ydstogo=10,yardline_100=60,quarter_seconds_remaining=900,score_differential=0,interception=0,desc='A pass',game_date='2026-09-01',home_team='AAA',away_team='BBB',total_home_score=20,total_away_score=10))
 pb=pd.DataFrame(rows);ft=pb[['game_id','play_id','season','week']].copy();ft['is_interception_worthy']=pd.Series([True,False,False],dtype=object)
 end=pb.copy();end['play_id']=2;end['desc']='END GAME';end['play_type']=None;end['pass_attempt']=0;pb=pd.concat([pb,end],ignore_index=True)
 roster=pd.DataFrame([dict(gsis_id='00-0000001',season=2026,week=1,team='AAA',game_type='REG',position='QB',full_name='Test')])
 return pb,ft,sc,roster,{'offset':0}

def build(f):return p.build_frames(*f)
def test_partial_week_whole_game_and_unknown_team(frames):
 frames[1].loc[1,'is_interception_worthy']=None
 i,d,f=build(frames)
 assert i['coverage']['games']==2 and i['coverage']['completedGames']==3
 assert len(i['coverage']['pendingGames'])==1 and i['summary']['passes']==2
 assert i['players'][0]['teams']==['AAA','BBB']
 assert i['players'][0]['positionClass']=='unknown'
 assert i['summary']['expected']==pytest.approx(.2) and i['summary']['per100']==40
 assert f[0]['stages'][-1]['remaining']==1

def test_duplicate_and_null_keys_refused(frames):
 pb,ft,sc,r,m=frames
 with pytest.raises(ValueError,match='duplicate'):build((pd.concat([pb,pb.iloc[[0]]]),ft,sc,r,m))
 ft.loc[0,'play_id']=None
 with pytest.raises(ValueError,match='null key'):build(frames)

def test_missing_passer_quarantines(frames):
 frames[0].loc[0,'passer_player_id']=None
 i,_,_=build(frames);assert i['summary']['passes']==2
 assert i['coverage']['pendingGames'][0]['missingPassers']==1

def test_missing_label_never_false_and_global_invalid(frames):
 frames[1].loc[0,'is_interception_worthy']=None
 assert build(frames)[0]['summary']['observed']==0
 frames[1].loc[0,'is_interception_worthy']='false'
 with pytest.raises(ValueError,match='Invalid FTN'):build(frames)

def test_population_penalty_attempt_and_exclusions(frames):
 row=frames[0].iloc[[0]].copy();row['penalty']=1
 assert p.eligible(row).all() # an official attempt with penalty remains
 for col,val in [('play_type','no_play'),('sack',1),('qb_scramble',1),('qb_spike',1),('play_deleted',1),('two_point_attempt',1),('pass_attempt',0)]:
  changed=row.copy();changed[col]=val;assert not p.eligible(changed).any()
 row['week']=9;assert p.eligible(row).all() # explicit replacement of old window

def test_zero_events_and_zero_denominator():
 empty=p.aggregate([]);assert empty['per100'] is None and empty['observedRate'] is None
 z=p.aggregate([dict(gameId='x',worthy=False,probability=.2,interception=False)])
 assert z['per100']==-20 and z['observed']==0 and z['expected']==.2

def test_invalid_game_and_team_metadata(frames):
 frames[0].loc[0,'posteam']='CCC'
 with pytest.raises(ValueError,match='team/opponent'):build(frames)
 frames[0].loc[0,'posteam']='AAA';frames[1].loc[0,'week']=2
 with pytest.raises(ValueError,match='metadata'):build(frames)

def test_activation_unchanged_revision_and_failure_preserves(tmp_path,frames):
 i,d,f=build(frames);store=tmp_path/'lab';run=tmp_path/'run';run.mkdir()
 src={'acquiredAt':'2026-11-04T10:00:00Z','files':[]}
 a=p.activate(store,i,d,f,src,run);before=(store/'current.json').read_bytes();pkg=store/'packages'/a['packageId'];original=(pkg/'index.json').read_bytes()
 b=p.activate(store,i,d,f,dict(src,acquiredAt='2026-11-04T11:00:00Z'),run)
 assert a['packageId']==b['packageId'] and (pkg/'index.json').read_bytes()==original
 assert json.loads((run/'receipt.json').read_text())['status']=='unchanged'
 changed=copy.deepcopy(d);changed['00-0000001']['plays'][0]['worthy']=False
 rev=p.revision(d,changed);assert len(rev['labelChanges'])==1
 removed=p.revision(d,{});assert len(removed['removed'])==3
 frames[1].loc[0,'is_interception_worthy']=False
 i2,d2,f2=build(frames);a2=p.activate(store,i2,d2,f2,src,run)
 assert a2['packageId']!=a['packageId'] and (pkg/'index.json').read_bytes()==original
 assert len(json.loads((run/'receipt.json').read_text())['revision']['labelChanges'])==1
 pkg=store/'packages'/a2['packageId']
 before=(store/'current.json').read_bytes();(pkg/'players/00-0000001.json').write_text('{}')
 with pytest.raises(ValueError,match='integrity'):p.activate(store,i,d,f,src,run)
 assert (store/'current.json').read_bytes()==before

def test_failure_and_protected_store(tmp_path,monkeypatch):
 store=tmp_path/'lab';store.mkdir();(store/'current.json').write_text('preserved')
 def fail(d):raise ValueError('Fixture failure')
 monkeypatch.setattr(p,'acquire',fail)
 with pytest.raises(ValueError,match='Fixture'):p.update(store)
 assert (store/'current.json').read_text()=='preserved' and not (store/'.updating').exists()
 assert list(store.glob('runs/*/failure.json'))
 with pytest.raises(ValueError,match='Protected'):p.update(p.ROOT/'data')

def test_truncated_game_quarantined_and_score_conflict_fatal(frames):
 frames[0].loc[3,'desc']='Truncated'
 assert build(frames)[0]['coverage']['games']==2
 frames[0].loc[3,'desc']='END GAME';frames[0].loc[3,'total_home_score']=99
 with pytest.raises(ValueError,match='final score'):build(frames)

def test_frozen_model_load_and_no_fit(frames):
 model=p.load_model();assert model['offset']==pytest.approx(-.1593395890254225)
 assert p.sha(p.MODEL)==p.MODEL_SHA
 assert 'fit(' not in Path(p.__file__).read_text()


def test_pointer_swap_failure_preserves_last_valid(tmp_path,frames,monkeypatch):
 i,d,f=build(frames);store=tmp_path/'lab';run=tmp_path/'run';run.mkdir();src={'acquiredAt':'2026-11-04T10:00:00Z','files':[]}
 p.activate(store,i,d,f,src,run);before=(store/'current.json').read_bytes()
 replace=p.os.replace
 def fail_pointer(a,b):
  if Path(b).name=='current.json':raise OSError('Fixture swap error')
  return replace(a,b)
 monkeypatch.setattr(p.os,'replace',fail_pointer)
 with pytest.raises(OSError,match='swap'):p.activate(store,i,d,f,src,run)
 assert (store/'current.json').read_bytes()==before
 p.read_active(store)
