import json,sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).parent))
from common import *
from classify import classify,identity
from run import aggregate,revisions,closed_games
from acquire import prepare

@pytest.fixture(autouse=True)
def offline(monkeypatch):
 import urllib.request,socket
 def fail(*a,**k):raise AssertionError('Offline tests cannot download')
 monkeypatch.setattr(urllib.request,'urlopen',fail);monkeypatch.setattr(socket,'create_connection',fail)

def play(**kw):
 d=dict(sack=0,qb_scramble=0,pass_attempt=1,rush_attempt=0,play_type='pass',aborted_play=0,is_throw_away=False,is_qb_out_of_pocket=False,read_thrown='0',season=2026,charting_present=True,complete_pass=0,interception=0,passer_player_id='00-0000001',rusher_player_id=None,position='QB',identity_status='resolved')
 d.update(kw);return d

@pytest.mark.parametrize('changes,cat',[
 ({},'progression'),({'read_thrown':'  chk '},'progression'),({'read_thrown':'SD'},'scramble_drill'),
 ({'read_thrown':'DES'},'indeterminate'),({'read_thrown':'unknown'},'indeterminate'),({'read_thrown':None},'indeterminate'),
 ({'is_throw_away':True},'throwaway'),({'is_throw_away':True,'read_thrown':'SD'},'throwaway'),
 ({'sack':1},'sack'),({'sack':1,'read_thrown':'SD'},'sack'),
 ({'sack':1,'is_throw_away':True},'indeterminate'),({'sack':1,'qb_scramble':1},'indeterminate'),
 ({'qb_scramble':1,'pass_attempt':0,'rush_attempt':1,'play_type':'run','rusher_player_id':'00-0000001','passer_player_id':None,'read_thrown':'SD'},'scramble'),
 ({'qb_scramble':1,'pass_attempt':0,'rush_attempt':1,'play_type':'run','rusher_player_id':'00-0000001','passer_player_id':'00-0000002'},'indeterminate'),
 ({'charting_present':False,'is_throw_away':None},'indeterminate'),({'is_throw_away':None},'indeterminate'),
 ({'is_qb_out_of_pocket':True},'progression'),({'read_thrown':'2'},'progression'),
 ({'season':2022,'read_thrown':None},'indeterminate'),({'season':2022,'read_thrown':'0'},'indeterminate'),({'season':2022,'read_thrown':'1'},'progression'),
 ({'aborted_play':1},'indeterminate'),({'is_throw_away':True,'complete_pass':1},'indeterminate'),({'is_throw_away':True,'interception':1},'indeterminate'),
 ({'is_throw_away':7},'indeterminate'),({'sack':None},'indeterminate'),({'sack':1,'charting_present':False,'is_throw_away':None},'sack')])
def test_exclusive_rules(changes,cat):
 r=play(**changes);before=dict(r);a=classify(r);assert a['category']==cat and a['category'] in CATS and a['rule'];assert r==before

def frame():
 rows=[]
 for i,(cat,epa) in enumerate([('progression',2.),('progression',4.),('scramble_drill',1.),('scramble',3.),('throwaway',-1.),('sack',-5.),('indeterminate',None)]):
  rows.append(dict(game_id='g'+str(i%2),play_id=i,season=2026,player_id='00-0000001',audited_name='Test',position_class='qb',posteam='A' if i%2 else 'B',category=cat,epa=epa,charting_present=True,identity_status='resolved'))
 return pd.DataFrame(rows)

def test_means_denominators_sign_and_sensitivities():
 cats,c=aggregate(frame());a=c.set_index('definition');assert len(cats)==6 and cats.n.sum()==7
 assert a.loc['main','a_mean']==3 and a.loc['main','b_mean']==2 and a.loc['main','difference']==1
 assert a.loc['S1','b_mean']==1 and a.loc['S2','b_mean']==-.5 and a.loc['S3','b_mean']==1
 assert a.loc['main','b_pct_all']==pytest.approx(200/7) and a.loc['main','b_pct_classifiable']==pytest.approx(200/6)
 assert a.loc['main','teams']=='A|B' and a.loc['main','dropbacks']==7
 assert cats[cats.category.eq('indeterminate')].n_epa.iloc[0]==0
 assert np.isnan(cats[cats.category.eq('indeterminate')].pct_classifiable.iloc[0])

def test_zero_opportunity_and_missing_epa():
 d=frame();d=d[d.category.eq('progression')];d['epa']=np.nan;cats,c=aggregate(d)
 assert c.status.eq('unavailable_no_opportunities').all();assert c.b_mean.isna().all();assert c.a_mean.isna().all();assert stats(d)['sum_epa'] is None
 d=pd.concat([d,frame().query("category=='scramble'")]);_,c=aggregate(d);assert c[c.definition.eq('main')].status.iloc[0]=='unavailable_epa'

def test_nonfinite_epa():
 d=frame();d.loc[0,'epa']=np.inf;t=stats(d);assert t['n']==7 and t['n_epa']==5

def test_eligibility_penalties_and_design_runs():
 d=pd.DataFrame([dict(season_type='REG',qb_dropback=1,play_deleted=0,qb_spike=0,qb_kneel=0,two_point_attempt=0,play_type='pass',penalty=1,qtr=5)])
 assert eligible(d).iloc[0]
 for col,val in [('play_deleted',1),('qb_spike',1),('qb_kneel',1),('two_point_attempt',1),('play_type','no_play'),('qb_dropback',0),('season_type','POST'),('play_deleted',None)]:
  x=d.copy();x[col]=val;assert not eligible(x).iloc[0]
 x=d.copy();x['play_type']='run';x['qb_dropback']=0;assert not eligible(x).iloc[0]

def test_rusher_only_for_verified_scrambles():
 roster=pd.DataFrame([dict(season=2026,week=1,team='A',gsis_id='00-0000001',position='QB',full_name='QB One',game_type='REG'),dict(season=2026,week=1,team='A',gsis_id='00-0000002',position='WR',full_name='WR Two',game_type='REG')])
 p=play(qb_scramble=1,pass_attempt=0,rush_attempt=1,play_type='run',passer_player_id=None,rusher_player_id='00-0000001');p.update(week=1,posteam='A',passer_player_name=None,rusher_player_name='QB')
 for col in ['position','identity_status']:p.pop(col)
 d=identity(pd.DataFrame([p]),roster);assert d.player_id.iloc[0]=='00-0000001' and classify(d.iloc[0].to_dict())['category']=='scramble'
 p.update(qb_scramble=0,pass_attempt=1,rush_attempt=0,play_type='pass');d=identity(pd.DataFrame([p]),roster);assert d.player_id.iloc[0] is None
 p.update(passer_player_id='00-0000002');d=identity(pd.DataFrame([p]),roster);assert d.position_class.iloc[0]=='other'

def test_determinism_no_name_or_epa_effect():
 p=play();a=classify(p);assert a==classify(play(epa=-99,audited_name='Different'))
 c1,m1=aggregate(frame());c2,m2=aggregate(frame().sample(frac=1,random_state=4));pd.testing.assert_frame_equal(c1,c2);pd.testing.assert_frame_equal(m1,m2)

def test_duplicate_abort():
 with pytest.raises(ValueError):unique(pd.DataFrame([{'game_id':'g','play_id':1}]*2),'fixture')

def test_revisions_preserve_previous(tmp_path):
 d=frame();old=tmp_path/'old';old.mkdir();d.to_parquet(old/'plays.parquet',index=False);write(old/'manifest.json',{'files':[]});before=sha(old/'plays.parquet')
 n=d.copy();n.loc[0,'epa']=7.;n=n.iloc[:-1];newrow=d.iloc[[0]].copy();newrow['play_id']=99;n=pd.concat([n,newrow]);r=revisions(old,tmp_path,n)
 assert len(r['changed'])==1 and len(r['added'])==1 and len(r['removed'])==1;assert sha(old/'plays.parquet')==before

def test_acquire_copy_hash_and_no_overwrite(tmp_path):
 s=tmp_path/'s';(s/'raw').mkdir(parents=True);(s/'raw/a').write_bytes(b'original');write(s/'sources.json',dict(files=[dict(path='raw/a',bytes=8,sha256=sha(s/'raw/a'))]));out=tmp_path/'out';prepare(out,s)
 assert (out/'raw/a').read_bytes()==b'original'
 with pytest.raises(FileExistsError):prepare(out,s)
 (s/'raw/a').write_bytes(b'revision')
 with pytest.raises(ValueError):verify(s)

def test_support_is_not_robustness():
 assert support(100,25,5)=='legible' and support(100,24,5)=='low_support' and support(100,25,4)=='low_support'

def test_non_qb_scramble_keeps_known_identity():
 roster=pd.DataFrame([dict(season=2026,week=1,team='A',gsis_id='00-0000002',position='WR',full_name='WR Two',game_type='REG')])
 p=play(qb_scramble=1,pass_attempt=0,rush_attempt=1,play_type='run',passer_player_id=None,rusher_player_id='00-0000002');p.update(week=1,posteam='A',passer_player_name=None,rusher_player_name='WR');p.pop('position');p.pop('identity_status')
 d=identity(pd.DataFrame([p]),roster);assert d.player_id.iloc[0]=='00-0000002' and d.position_class.iloc[0]=='other';assert classify(d.iloc[0].to_dict())['reason']=='scramble_non_qb_position'

def test_all_event_patterns_are_exhaustive():
 import itertools
 for sack,scramble,pa,ra,ptype,code,ta in itertools.product([0,1],[0,1],[0,1],[0,1],['pass','run','no_play'],['0','1','2','CHK','SD','DES',None],[False,True,None]):
  r=classify(play(sack=sack,qb_scramble=scramble,pass_attempt=pa,rush_attempt=ra,play_type=ptype,read_thrown=code,is_throw_away=ta));assert r['category'] in CATS and isinstance(r['rule'],str)

def test_closed_game_gate_partial_score_and_final_conflict():
 s=pd.DataFrame([dict(season=2026,game_type='REG',game_id='g',week=1,gameday='2026-09-01',home_team='A',away_team='B',home_score=10,away_score=7,result=3)])
 p=pd.DataFrame([dict(game_id='g',season_type='REG',week=1,home_team='A',away_team='B',game_date='2026-09-01',desc='END GAME',total_home_score=10,total_away_score=7)])
 games,c=closed_games(p,s,2026);assert games=={'g'} and len(c['included'])==1
 q=s.copy();q['away_score']=None
 with pytest.raises(ValueError):closed_games(p,q,2026)
 q=p.copy();q['total_home_score']=17
 with pytest.raises(ValueError):closed_games(q,s,2026)
 q=p.copy();q['desc']='not closed';games,c=closed_games(q,s,2026);assert not games and c['pending'][0]['reason']=='end_marker_missing_or_ambiguous'

def test_missing_roster_does_not_invent_identity():
 p=play(qb_scramble=1,pass_attempt=0,rush_attempt=1,play_type='run',passer_player_id=None,rusher_player_id='00-0000001');p.update(week=1,posteam='A',passer_player_name=None,rusher_player_name='QB');p.pop('position');p.pop('identity_status')
 roster=pd.DataFrame(columns=['season','week','team','gsis_id','position','full_name','game_type']);d=identity(pd.DataFrame([p]),roster);assert d.identity_status.iloc[0]=='unknown_or_conflicting' and classify(d.iloc[0].to_dict())['category']=='indeterminate'

def test_end_to_end_frozen_source_revision(tmp_path):
 """Exercise raw files, closure gate, roster, fixed rules and immutable revisions offline."""
 import shutil
 from run import build
 from verify import verify_package
 s=tmp_path/'sources';s.mkdir();records=[]
 def put(rel,df):
  p=s/rel;p.parent.mkdir(exist_ok=True);df.to_parquet(p,index=False);records.append(dict(path=rel,bytes=p.stat().st_size,sha256=sha(p)))
 for year in range(2022,2027):
  gid=f'{year}_01_A_B';rows=[];ft=[]
  for i in [1,2,3,4]:
   r={col:None for col in PBP};r.update(game_id=gid,play_id=i,season=year,season_type='REG',week=1,game_date=f'{year}-09-01',home_team='A',away_team='B',posteam='A',defteam='B',play_type='pass',qb_dropback=1,play_deleted=0,qb_spike=0,qb_kneel=0,two_point_attempt=0,aborted_play=0,pass_attempt=1,rush_attempt=0,qb_scramble=0,sack=0,complete_pass=0,interception=0,passer_player_id='00-0000001',passer_player_name='QB',epa=float(i),penalty=0,desc='fixture',time='10:00',yrdln='A 30',total_home_score=10,total_away_score=7,down=1,ydstogo=10,yardline_100=70,qtr=1,quarter_seconds_remaining=600,score_differential=0)
   if i==2:r.update(qb_scramble=1,pass_attempt=0,rush_attempt=1,play_type='run',passer_player_id=None,rusher_player_id='00-0000001',rusher_player_name='QB')
   if i==3:r.update(sack=1)
   if i==4:r.update(desc='END GAME',qb_dropback=0,play_type=None)
   rows.append(r)
   t={k:False for k in FTN};t.update(nflverse_game_id=gid,nflverse_play_id=i,season=year,week=1,read_thrown='1' if i==1 else 'SD');ft.append(t)
  put('current/pbp.parquet' if year==2026 else f'raw/pbp_{year}.parquet',pd.DataFrame(rows));put('current/ftn.parquet' if year==2026 else f'raw/ftn_{year}.parquet',pd.DataFrame(ft))
  put(f'rosters/{year}.parquet',pd.DataFrame([dict(season=year,week=1,team='A',gsis_id='00-0000001',position='QB',full_name='QB One',game_type='REG')]))
 schedule=pd.DataFrame([dict(season=2026,game_type='REG',game_id='2026_01_A_B',week=1,gameday='2026-09-01',home_team='A',away_team='B',home_score=10,away_score=7,result=3)]);schedule.to_csv(s/'current/schedule.csv',index=False);p=s/'current/schedule.csv';records.append(dict(path='current/schedule.csv',bytes=p.stat().st_size,sha256=sha(p)));write(s/'sources.json',dict(files=records,currentSeason=2026))
 base=build(s,tmp_path/'baseline');before=sha(base/'manifest.json');assert verify_package(base)['main_rows']==12
 ns=tmp_path/'revised_sources';shutil.copytree(s,ns);p=ns/'current/pbp.parquet';raw=pd.read_parquet(p);raw.loc[raw.play_id.eq(1),'epa']=9.;raw.to_parquet(p,index=False);manifest=read(ns/'sources.json')
 for r in manifest['files']:
  if r['path']=='current/pbp.parquet':r.update(bytes=p.stat().st_size,sha256=sha(p))
 write(ns/'sources.json',manifest);out=build(ns,tmp_path/'revised',base);rev=read(out/'revision.json');assert len(rev['changed'])==1 and rev['changed'][0]['fields']==['epa'] and not rev['added'] and not rev['removed'];assert sha(base/'manifest.json')==before;assert verify_package(out)['passed']
 with pytest.raises(FileExistsError):build(ns,tmp_path/'baseline')
