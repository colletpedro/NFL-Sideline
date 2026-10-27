import json,os
from pathlib import Path
import polars as pl
import pytest
from nfl_sideline_etl.score_curve.package import project,read

@pytest.fixture(scope='module')
def bundle():
    p=os.environ.get('NFL_CURVE_QA_BUNDLE')
    if not p:pytest.skip('Explicit private curve fixture required')
    return Path(p)

def test_punt_muff_uses_actual_fumbled_and_recovered_teams(bundle):
    rows=pl.read_parquet(bundle/'source/source/source/pbp.parquet').to_dicts();story=json.loads((bundle/'source/story.json').read_text());out=project(rows,story['timelines']);r=next(e for e in out['games']['2026_01_CHI_CAR'] if e['playId']==1812)
    assert (r['lostTeam'],r['recoveredTeam'])==('CAR','CHI')

@pytest.mark.parametrize('field,value',[('fumble_recovery_1_team',None),('fumbled_1_team','XX'),('qtr',6),('total_home_score',None)])
def test_incomplete_or_invalid_event_is_not_invented(bundle,field,value):
    rows=pl.read_parquet(bundle/'source/source/source/pbp.parquet').filter(pl.col('game_id')=='2026_01_CHI_CAR').to_dicts();r=next(r for r in rows if r['play_id']==1812);r[field]=value;story=json.loads((bundle/'source/story.json').read_text())
    with pytest.raises((ValueError,TypeError)):project(rows,story['timelines'])

def test_all_262_events_reconcile_with_source_flags_clocks_and_scores(bundle):
    out=json.loads((bundle/'events.json').read_text());rows=pl.read_parquet(bundle/'source/source/source/pbp.parquet').to_dicts();flags=[r for r in rows if r['play_deleted']==0 and (r['interception']==1 or r['fumble_lost']==1)];events=[(g,e) for g,es in out['games'].items() for e in es]
    assert len(events)==len(flags)==262
    source={(r['game_id'],int(r['play_id'])):r for r in flags}
    assert {(g,e['playId']) for g,e in events}==set(source)
    for g,e in events:
        r=source[g,e['playId']];assert e['score']==[r['total_away_score'],r['total_home_score']];assert (e['quarter'],e['remaining'])==(r['qtr'],r['quarter_seconds_remaining'])
        if e['kind']=='INTERCEPTION':assert e['lostTeam']==r['posteam'] and e['recoveredTeam']==r['defteam']
        else:assert any(e['lostTeam']==r[f'fumbled_{n}_team'] and e['recoveredTeam']==r[f'fumble_recovery_{n}_team'] for n in (1,2))

def test_package_hashes_and_semantic_reproduction(bundle):
    b,m=read(bundle);assert json.loads(b)['sourcePin'].startswith('sha256:93b6') and m['bundleId'].startswith('sha256:86fd')
