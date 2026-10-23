"""Synthetic events only. Real application inputs are always pinned preserved PBP."""
import pytest
from nfl_sideline_etl.situational import third, campaign, measure, scrimmage


def event(**changes):
    r=dict(game_id='SYNTHETIC',play_id=1,week=1,posteam='AAA',defteam='BBB',down=3,play_type='pass',order_sequence=1,
        ydstogo=5,yardline_100=15,third_down_converted=1,third_down_failed=0,first_down_penalty=0,play_deleted=0,
        aborted_play=0,qb_kneel=0,qb_spike=0,qb_scramble=0,sack=0,extra_point_attempt=0,two_point_attempt=0,penalty=0,
        fixed_drive=1.0,drive=1.0,fixed_drive_result='Touchdown',touchdown=1,td_team='AAA',field_goal_result=None,
        interception=0,fumble_lost=0,fourth_down_failed=0,safety=0,qtr=1,game_seconds_remaining=3000,
        drive_inside20=1,drive_ended_with_score=1,desc='Synthetic touchdown')
    r.update(changes);return r


def test_nullifying_penalty_and_penalty_first_down_are_separate():
    r=third(event(play_type='no_play',penalty=1,first_down_penalty=1,third_down_converted=0,third_down_failed=0))
    m=measure([r],'third');assert r['reason']=='NO_PLAY' and m['denominator']==0 and m['ratio'] is None
    assert m['penaltyFirstDowns']==dict(included=0,excluded=1)
    r=third(event(first_down_penalty=1,third_down_converted=0,third_down_failed=1))
    m=measure([r],'third');assert m['numerator']==0 and m['denominator']==1 and m['status']=='AVAILABLE'
    assert m['penaltyFirstDowns']['included']==1


@pytest.mark.parametrize('changes,kind',[({'sack':1},'pass'),({'play_type':'run','qb_scramble':1},'run')])
def test_sack_and_scramble_keep_source_play_type(changes,kind):
    assert third(event(**changes))['kind']==kind


@pytest.mark.parametrize('changes,reason',[({'play_deleted':1},'DELETED'),({'aborted_play':1},'ABORTED'),({'qb_kneel':1},'KNEEL'),({'play_type':'qb_spike'},'SPIKE'),({'play_type':'field_goal'},'OTHER_TYPE'),({'two_point_attempt':1},'TRY')])
def test_exclusions(changes,reason):
    assert third(event(**changes))['reason']==reason


@pytest.mark.parametrize('converted,failed',[(1,1),(0,0),(None,0),(2,0)])
def test_contradictory_flags_block_rate(converted,failed):
    m=measure([third(event(third_down_converted=converted,third_down_failed=failed))],'third')
    assert m['status']=='INSUFFICIENT' and m['ratio'] is None


def test_duplicate_is_never_selected():
    assert third(event(),True)['reason']=='DUPLICATE'
    assert campaign([event()],{'SYNTHETIC:1'})['uncertain']


@pytest.mark.parametrize('yards,bucket',[(1,'short'),(3,'short'),(4,'medium'),(6,'medium'),(7,'long'),(None,'unknown'),(0,'unknown')])
def test_exact_project_distance_boundaries(yards,bucket):
    assert third(event(ydstogo=yards))['distance']==bucket


def test_multiple_plays_and_exit_reentry_still_one_opportunity():
    rows=[event(play_id=1,order_sequence=1,touchdown=0,td_team=None),event(play_id=2,order_sequence=2,yardline_100=25,touchdown=0,td_team=None),event(play_id=3,order_sequence=3,yardline_100=10)]
    c=campaign(rows,set());assert c['included'] and len(c['entryPlayIds'])==2
    assert measure([c],'redZone')['ratio']==dict(numerator=1,denominator=1)


def test_td_outside_then_try_does_not_create_entry():
    rows=[event(yardline_100=35),event(play_id=2,order_sequence=2,down=None,play_type='extra_point',extra_point_attempt=1,yardline_100=2,touchdown=0)]
    c=campaign(rows,set());assert c['reason']=='NO_ENTRY' and not c['entryPlayIds']


@pytest.mark.parametrize('changes,expected',[
    ({'interception':1,'fixed_drive_result':'Turnover'},'TURNOVER'),
    ({'touchdown':1,'td_team':'BBB','fixed_drive_result':'Opp touchdown'},'OPPONENT_TOUCHDOWN'),
    ({'play_type':'field_goal','field_goal_result':'made','fixed_drive_result':'Field goal'},'FIELD_GOAL'),
    ({'play_type':'field_goal','field_goal_result':'missed','fixed_drive_result':'Missed field goal'},'MISSED_FIELD_GOAL'),
    ({'down':4,'fourth_down_failed':1,'fixed_drive_result':'Turnover on downs'},'DOWNS'),
    ({'play_type':'punt','fumble_lost':1,'fixed_drive_result':'Punt'},'PUNT'),
    ({'play_type':'no_play','penalty':1,'safety':1,'fixed_drive_result':'Safety'},'SAFETY'),
])
def test_terminal_outcomes(changes,expected):
    r=event(touchdown=0,td_team=None,**{k:v for k,v in changes.items() if k not in ('touchdown','td_team')})
    for k in ('touchdown','td_team'):
        if k in changes:r[k]=changes[k]
    c=campaign([r],set());assert c['outcome']==expected
    assert c['included'] and measure([c],'redZone')['numerator']==0


def test_end_quarter_one_does_not_close_drive_but_half_does():
    r=event(touchdown=0,td_team=None,fixed_drive_result='End of half')
    q=event(play_id=2,order_sequence=2,down=None,play_type=None,touchdown=None,desc='END QUARTER 1',qtr=1,game_seconds_remaining=2700,fixed_drive_result='End of half')
    assert campaign([r,q],set())['uncertain']
    q.update(qtr=2,game_seconds_remaining=1800,desc='END QUARTER 2')
    c=campaign([r,q],set());assert c['included'] and c['outcome']=='END_HALF_GAME'


def test_incomplete_campaign_and_unknown_positions_block_rate():
    for r in [event(touchdown=0,td_team=None,fixed_drive_result=None),event(yardline_100=None),event(play_deleted=None)]:
        c=campaign([r],set());assert c['uncertain'] and measure([c],'redZone')['status']=='INSUFFICIENT'


def test_established_penalty_position_counts_but_nullified_td_does_not():
    rows=[event(play_type='no_play',penalty=1,touchdown=1),event(play_id=2,order_sequence=2,play_type='field_goal',field_goal_result='made',touchdown=0,td_team=None)]
    for r in rows:r['fixed_drive_result']='Field goal'
    c=campaign(rows,set());assert c['included'] and c['outcome']=='FIELD_GOAL' and c['touchdownPlayIds']==[]


def test_zero_opportunities_has_null_rate_and_union_uses_original_units():
    m=measure([],'third');assert m['status']=='NO_OPPORTUNITIES' and m['denominatorState']=='ZERO' and m['ratio'] is None
    a=third(event());b=third(event(play_id=2,third_down_converted=0,third_down_failed=1))
    m=measure([a,b],'third');assert m['ratio']==dict(numerator=1,denominator=2)
    assert not scrimmage(event(two_point_attempt=1))
