import json,os
from pathlib import Path
import pytest
from nfl_sideline_etl.game_story.project import timeline,score_kind,clock
from nfl_sideline_etl.game_story.package import read

def row(**kw):
 r=dict(game_id='g',play_id=1,order_sequence=1,qtr=1,quarter_seconds_remaining=600,total_away_score=3,total_home_score=0,play_deleted=0,touchdown=0,td_team=None,field_goal_result='made',posteam='A',defteam='B',extra_point_result=None,two_point_conv_result=None,defensive_two_point_conv=0,safety=0,fixed_drive=1,desc='evidence');r.update(kw);return r

def test_field_goal_then_td_and_extra_crosses_zero_without_probability():
 rs=[row(),row(play_id=2,order_sequence=2,quarter_seconds_remaining=500,total_away_score=3,total_home_score=6,touchdown=1,td_team='B',posteam='B',defteam='A',field_goal_result=None),row(play_id=3,order_sequence=3,quarter_seconds_remaining=495,total_away_score=3,total_home_score=7,posteam='B',defteam='A',field_goal_result=None,extra_point_result='good')]
 d=timeline(dict(gameId='g',away='A',home='B',awayScore=3,homeScore=7),dict(productions=[]),rs)
 assert d['status']=='AVAILABLE' and [e['margin'] for e in d['events']]==[3,-3,-4]
 assert [e['points'] for e in d['events']]==[3,6,1]

@pytest.mark.parametrize('mutate',[lambda r:r.update(total_away_score=-1),lambda r:r.update(total_home_score=None),lambda r:r.update(play_deleted=1),lambda r:r.update(field_goal_result='missed'),lambda r:r.update(quarter_seconds_remaining=None)])
def test_unsupported_score_or_clock_is_not_invented(mutate):
 r=row();mutate(r);d=timeline(dict(gameId='g',away='A',home='B',awayScore=3,homeScore=0),dict(productions=[]),[r]);assert d['status']=='INSUFFICIENT' and not d['events']

def test_score_reversal_and_calendar_mismatch_block_curve():
 g=dict(gameId='g',away='A',home='B',awayScore=3,homeScore=0)
 assert timeline(g,dict(productions=[]),[row(),row(play_id=2,order_sequence=2,total_away_score=0)])['status']=='INSUFFICIENT'
 assert timeline({**g,'awayScore':7},dict(productions=[]),[row()])['status']=='INSUFFICIENT'

@pytest.mark.parametrize('kind,updates,team',[('SAFETY',dict(safety=1,field_goal_result=None),'B'),('DEFENSIVE_TWO_POINT',dict(defensive_two_point_conv=1,field_goal_result=None),'B'),('TWO_POINT',dict(two_point_conv_result='success',field_goal_result=None),'A')])
def test_two_points_have_explicit_evidence(kind,updates,team):assert score_kind(row(**updates),2,team)==kind

def test_overtime_uses_own_clock_and_no_regulation_reset():
 assert clock(row(qtr=5,quarter_seconds_remaining=600))['elapsed']==3600
 assert clock(row(qtr=5,quarter_seconds_remaining=300))['elapsed']==3900
 with pytest.raises(ValueError):clock(row(qtr=6))

@pytest.fixture(scope='module')
def package():
 path=os.environ.get('NFL_STORY_QA_BUNDLE')
 if not path:pytest.skip('Explicit private story package required')
 b,_=read(Path(path));return Path(path),json.loads(b)

def test_all_107_ends_and_all_1418_transitions_match_raw_score_deltas(package):
 root,d=package
 import polars as pl
 raw=pl.read_parquet(root/'source/source/pbp.parquet')
 for id,t in d['timelines'].items():
  rs=raw.filter(pl.col('game_id')==id).sort('order_sequence').to_dicts();previous=[0,0];events=[]
  for r in rs:
   s=[int(r['total_away_score']),int(r['total_home_score'])]
   if s!=previous:events.append((int(r['play_id']),previous,s));previous=s
  assert t['status']=='AVAILABLE' and previous==t['final']
  assert [(e['playId'],e['before'],e['after']) for e in t['events']]==events
 assert sum(len(t['events']) for t in d['timelines'].values())==1418

def test_season_uses_exact_sums_and_does_not_drop_bad_components(package):
 root,d=package
 for f,r in d['seasonReferences'].items():
  assert len(r['candidateTeams'])==32
  for p in r['inventory']:
   team=json.loads((root/f"source/teams/{p['team']}.json").read_text());m=team['productions'][0]['metrics'][f]
   assert p['numerator']==m['descriptor']['numerator'] and p['denominator']==m['descriptor']['denominator']
   assert p['unitIds']==m['descriptor']['unitIds']
  assert r['pooledRate']['denominator']==sum(p['denominator'] for p in r['teamRateDistribution']['points'])
 assert d['seasonReferences']['third']['representedTeams']==sorted(set(d['seasonReferences']['third']['candidateTeams'])-{'MIN','CHI'})
 assert len(d['seasonReferences']['redZone']['representedTeams'])==32
