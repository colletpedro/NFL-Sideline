"""Scope/operation failures and real frozen seven-week data, not HTML snapshots."""
from copy import deepcopy
from fractions import Fraction
import json,os
from pathlib import Path
import pytest
from nfl_sideline_etl.season_analysis.project import aggregated_descriptor, game_productions, descriptor, decimal
from nfl_sideline_etl.season_analysis.policy import decision
from nfl_sideline_etl.season_analysis.package import read
from nfl_sideline_etl.redzone_epa.project import aggregate as rz_aggregate

HASH='sha256:'+'a'*64

def desc(week=7,n=1,den=2,team='A'):
 return descriptor(f'{team}/{week}','third',team,n,den,'AVAILABLE',[f'{team}:{week}:{j}' for j in range(den)],[f'game-{week}'],[week],HASH)

@pytest.mark.parametrize('week',range(1,8))
def test_new_scope_accepts_seven_individual_weeks(week):
 assert decision('sideBySide',[desc(week),desc(week,team='B')])['allowed']

@pytest.mark.parametrize('mutate',[
 lambda d:d.update(weeks=[8]),lambda d:d.update(weeks=[7,7]),lambda d:d.update(weeks=[7,1]),
 lambda d:d.update(sourceHash='other'),lambda d:d.update(unitIds=['A:7:0','A:7:0']),
 lambda d:d.update(status='INSUFFICIENT'),lambda d:d.update(status='SOURCE_ABSENT'),
 lambda d:d.update(guarantees={'epaModel':'UNKNOWN'},provenanceVerified=False),
])
def test_incompatible_comparisons_are_refused(mutate):
 a,b=desc(),desc(team='B');mutate(b)
 assert not decision('sideBySide',[a,b])['allowed']

def test_bye_is_not_a_missing_component_and_sums_are_weighted():
 parts=[desc(w,n=w,den=w+1) for w in [1,2,3,4,6,7]]
 games=[p['gameIds'][0] for p in parts]
 d=aggregated_descriptor(parts,'A','off','third',games,HASH)
 assert d['status']=='AVAILABLE' and d['weeks']==[1,2,3,4,5,6,7] and d['denominator']==sum(w+1 for w in [1,2,3,4,6,7])
 assert d['numerator']==sum([1,2,3,4,6,7]) and len(d['gameIds'])==6
 with pytest.raises(ValueError,match='component'):aggregated_descriptor(parts[:-1],'A','off','third',games,HASH)

@pytest.mark.parametrize('state',['SOURCE_ABSENT','INSUFFICIENT'])
def test_bad_played_component_blocks_full_aggregate(state):
 parts=[desc(1),desc(2)];parts[1]['status']=state
 d=aggregated_descriptor(parts,'A','off','third',['game-1','game-2'],HASH)
 assert d['status']==state and d['numerator'] is None and d['denominator'] is None
 assert not decision('display',[d])['allowed']

def test_zero_opportunities_is_not_zero_percent():
 a=desc(1,n=0,den=0);a['status']='NO_OPPORTUNITIES'
 d=aggregated_descriptor([a,desc(2)],'A','off','third',['game-1','game-2'],HASH)
 assert (d['numerator'],d['denominator'],d['status'])==(1,2,'AVAILABLE')
 assert not decision('difference',[a,desc(1,team='B')])['allowed']

def test_same_play_cannot_be_added_as_independent_evidence():
 a=desc(1);b=deepcopy(a);b.update(team='B',id='mirror')
 assert not decision('difference',[a,b])['allowed']
 assert not decision('leagueReference',[a,b])['allowed']
 with pytest.raises(ValueError,match='Duplicate'):aggregated_descriptor([a,b],'A','off','third',['game-1','game-1'],HASH)

def test_missing_source_does_not_create_zero_rate():
 g=dict(gameId='2026_07_A_B',week=7,away='A',home='B')
 pp,_=game_productions(g,[],HASH)
 assert all(p['metrics']['third']['descriptor']['status']=='SOURCE_ABSENT' for p in pp)
 assert all(e['descriptor']['status']=='SOURCE_ABSENT' for p in pp for e in p['epa'])

def test_decimal_exactness_and_missing_rz_components():
 assert Fraction(decimal(Fraction('0.1')+Fraction('0.2')))==Fraction('0.3')
 r=rz_aggregate([None]);assert r['status']=='SOURCE_ABSENT' and r['mean'] is None

BUNDLE=os.environ.get('NFL_SEASON_QA_BUNDLE')
@pytest.fixture(scope='module')
def archive():
 if not BUNDLE:pytest.skip('Explicit private season bundle not configured')
 root=Path(BUNDLE);i,m=read(root);return root,i,m

def test_all_game_and_team_documents_are_reproducible(archive):
 root,i,m=archive
 assert len(i['games'])==107 and len(i['teams'])==32 and i['counts']['rawRows']==18738
 assert [w['games'] for w in i['weekInventory']]==[16,16,16,16,15,14,14]
 assert i['weekInventory'][-1]['byes']==['BUF','JAX','LAC','WAS']
 for t in i['teams']:
  d=json.loads((root/t['path']).read_text())
  assert len(d['games'])+len(d['byeWeeks'])==7
  for p in d['productions']:
   assert set(p['gameIds'])==set(t['gameIds'])
   for e in p['epa']:
    assert len(e['eligibleUnitIds'])==len(set(e['eligibleUnitIds']))
    assert Fraction(e['descriptor']['numerator'])==sum((Fraction(c['descriptor']['numerator']) for c in e['components']),Fraction())

def test_penalty_flags_do_not_become_guessed_conversions(archive):
 root,i,_=archive
 for game,team in [('2026_03_MIN_TB','MIN'),('2026_07_NE_CHI','CHI')]:
  d=json.loads((root/f'games/{game}.json').read_text());p=next(p for p in d['productions'] if p['offense']==team)
  assert p['metrics']['third']['descriptor']['status']=='INSUFFICIENT'
  assert not p['metrics']['third']['display']['allowed']
  r=d['leagueReferences']['third'];assert team not in r['representedTeams'] and team in [p['team'] for p in r['teamsWithoutRate']]
  assert all(e['display']['allowed'] for e in p['epa'])
  a=json.loads((root/f'teams/{team}.json').read_text())
  assert a['productions'][0]['metrics']['third']['descriptor']['status']=='INSUFFICIENT'

def test_weekly_league_excludes_byes_and_includes_available_zero(archive):
 root,i,_=archive
 for w in i['weekInventory']:
  g=next(g for g in i['games'] if g['week']==w['week']);d=json.loads((root/g['path']).read_text())
  for f in ('third','redZone'):
   r=d['leagueReferences'][f]
   assert set(r['candidateTeams'])==set(w['participants'])
   assert not set(r['representedTeams'])&set(w['byes'])
   assert all(p['denominator']>0 for p in r['teamRateDistribution']['points'])
   assert r['pooledRate']['numerator']==sum(p['numerator'] for p in r['teamRateDistribution']['points'])
