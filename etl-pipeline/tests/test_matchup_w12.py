"""Synthetic operation cases and explicit, complete frozen-data QA."""
from copy import deepcopy
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil

import pytest

from nfl_sideline_etl.matchup_w12.policy import decision
from nfl_sideline_etl.matchup_w12.project import editorial_facts
from nfl_sideline_etl.matchup_w12.package import read, reproduce, calendar
from nfl_sideline_etl.comparison_foundation.package import hashes
from nfl_sideline_etl.situational import digest, encoded


def observation(team='A',n=1,d=1,week=1):
    return dict(id=team+'/third',metric='third',team=team,perspective='off',season=2026,phase='REG',weeks=[week],
        definition='situational-1.0.0',population='third-eligible-1.0.0',unit='attempt',sourceHash='same-file',sourceColumn='third_down_converted',
        numerator=n,denominator=d,status='AVAILABLE' if d else 'NO_OPPORTUNITIES',unitIds=[team+str(i) for i in range(d)],gameIds=['same-game'],ambiguousIds=[],integrityVerified=True,provenanceVerified=True)


@pytest.mark.parametrize('week',[1,2])
def test_one_of_one_and_original_unknowns(week):
    a,b=observation(week=week),observation('B',2,3,week);before=deepcopy([a,b])
    for op in ('display','sideBySide','difference','leagueReference','editorialFact'):
        assert decision(op,[a] if op=='display' else [a,b])['allowed']
    assert [a,b]==before


@pytest.mark.parametrize('field,value', [('definition','other'),('sourceHash','other'),('population','other'),('unit','campaign'),('sourceColumn','other'),('weeks',[2])])
def test_individual_display_survives_comparison_refusal(field,value):
    a,b=observation(),observation('B');b[field]=value
    assert decision('display',[b])['allowed'] and not decision('sideBySide',[a,b])['allowed']


@pytest.mark.parametrize('status',['SOURCE_ABSENT','INSUFFICIENT'])
def test_unavailable_states_are_not_zero(status):
    a=observation();a['status']=status
    for op in ('display','sideBySide','difference','editorialFact'):
        assert not decision(op,[a] if op=='display' else [a,observation('B')])['allowed']
    assert decision('display',[observation('Z',0,0)])['allowed']
    assert not decision('sideBySide',[observation('Z',0,0),observation('B')])['allowed']


@pytest.mark.parametrize('weeks',[[1,2],[3],[]])
def test_reference_refuses_aggregate_or_outside_scope(weeks):
    a=observation();a['weeks']=weeks;assert not decision('leagueReference',[a])['allowed']


def test_defense_is_not_another_independent_sample():
    a=observation();b=deepcopy(a);b.update(id='defense',team='B',perspective='def')
    assert not decision('difference',[a,b])['allowed'] and not decision('leagueReference',[a,b])['allowed']
    a['metric']='epa';a['numerator']='-1.230000000001';assert decision('display',[a])['allowed'];assert not decision('leagueReference',[a])['allowed']
    b=observation('B');b['metric']='epa';b['numerator']='1.0';assert not decision('editorialFact',[a,b])['allowed']


def facts(a,b):
    prods=[dict(offense=x['team'],metrics={k:dict(descriptor={**x,'id':x['id']+'/'+k,'metric':k}) for k in ('third','thirdLong','redZone')}) for x in (a,b)]
    comparisons={k:dict(difference=decision('difference',[p['metrics'][k]['descriptor'] for p in prods])) for k in ('third','thirdLong','redZone')}
    return editorial_facts(prods,comparisons,'synthetic-only',a['weeks'][0])


def test_facts_use_exact_order_equal_rounding_and_equal_rates_with_different_counts():
    a,b=observation('A',1,3),observation('B',2,6)
    assert all('mesma taxa' in f['text'] or 'taxas observadas foram iguais' in f['text'] for f in facts(a,b))
    # These both round to 40.0%; exact ordering must still name B.
    a,b=observation('A',2,5),observation('B',4001,10000)
    assert Fraction(a['numerator'],a['denominator'])<Fraction(b['numerator'],b['denominator'])
    fs=facts(a,b);assert fs[0]['text'].startswith('B teve maior')
    b=observation('B',0,0);assert facts(a,b)==[]


@pytest.fixture(scope='module')
def real():
    name=os.environ.get('NFL_W12_QA_BUNDLE')
    if not name:pytest.skip('Explicit frozen collection required')
    return Path(name)


def test_full_real_reader_and_per_game_inventory(real):
    index,docs,marker=read(real)
    assert len(docs)==32 and index['counts']==dict(games=32,offensiveProductions=64)
    assert marker['bundleId']==digest((real/'index.json').read_bytes())
    assert sum(len(json.loads(b)['productions']) for b in docs.values())==64
    assert sum(len(p['epa']) for b in docs.values() for p in json.loads(b)['productions'])==192
    assert sum(p['metrics']['redZone']['descriptor']['status']=='NO_OPPORTUNITIES' for b in docs.values() for p in json.loads(b)['productions'])==2
    with pytest.raises(ValueError,match='pin mismatch'):read(real,'sha256:'+'0'*64)


def test_real_independent_reproduction_and_tamper_even_after_rehash(real,tmp_path):
    with pytest.raises(ValueError,match='disjoint'):reproduce(real,real/'nested-forbidden')
    out=tmp_path/'copy';reproduce(real,out);assert hashes(out)==hashes(real)
    with pytest.raises(ValueError,match='New destination'):reproduce(real,out)
    index=json.loads((out/'index.json').read_bytes());gid=index['games'][0]['gameId'];p=out/'games'/(gid+'.json');d=json.loads(p.read_bytes());d['productions'][0]['thirdAttempts'][0]['yardsToGo']+=1;p.write_bytes(encoded(d))
    with pytest.raises(ValueError,match='hash mismatch'):read(out)
    index['games'][0]['documentHash']=digest(p.read_bytes());(out/'index.json').write_bytes(encoded(index));m=json.loads((out/'COMPLETED.json').read_bytes());m['bundleId']=digest(encoded(index));m['files']['index.json']=m['bundleId'];m['files']['games/'+gid+'.json']=digest(p.read_bytes());(out/'COMPLETED.json').write_bytes(encoded(m))
    with pytest.raises(ValueError,match='derivation mismatch'):read(out)
    shutil.copyfile(real/'index.json',out/'index.json');shutil.copyfile(real/'games'/(gid+'.json'),p);shutil.copyfile(real/'COMPLETED.json',out/'COMPLETED.json')
    (out/'unexpected').mkdir()
    with pytest.raises(ValueError):read(out)
    (out/'unexpected').rmdir();p.unlink();p.symlink_to(real/'games'/(gid+'.json'))
    with pytest.raises(ValueError):read(out)


def test_absent_source_does_not_fall_back(tmp_path):
    with pytest.raises(FileNotFoundError):read(tmp_path/'missing')
