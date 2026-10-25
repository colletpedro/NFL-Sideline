from copy import deepcopy
import json
import os
from pathlib import Path
import pytest
from nfl_sideline_etl.team_w12.project import aggregate_descriptor, permission
from nfl_sideline_etl.team_w12.package import read


def component(week,n=1,d=2,status='AVAILABLE'):
    return dict(id=str(week),metric='third',team='TEST',perspective='off',season=2026,phase='REG',weeks=[week],gameIds=['g'+str(week)],
                definition={'version':'1'},population='test',unit='attempt',sourceHash='same',sourceColumn='converted',numerator=n,denominator=d,
                status=status,unitIds=[f'g{week}:{i}' for i in range(d)],ambiguousIds=[],integrityVerified=True,provenanceVerified=True)


def test_zero_opportunities_contributes_zero_without_removing_week_or_making_zero_rate():
    a=component(1,0,0,'NO_OPPORTUNITIES');b=component(2,1,2)
    out=aggregate_descriptor([a,b],'TEST','off','third',['g1','g2'])
    assert (out['numerator'],out['denominator'],out['weeks'],out['status'])==(1,2,[1,2],'AVAILABLE')
    zero=aggregate_descriptor([a,component(2,0,0,'NO_OPPORTUNITIES')],'TEST','off','third',['g1','g2'])
    assert (zero['numerator'],zero['denominator'],zero['status'])==(0,0,'NO_OPPORTUNITIES')
    assert permission('display',[zero])['allowed'] and not permission('sideBySide',[zero,out])['allowed']


@pytest.mark.parametrize('state',['SOURCE_ABSENT','INSUFFICIENT'])
def test_unavailable_component_blocks_intended_aggregate_and_preserves_input(state):
    a=component(1);b=component(2);b['status']=state;before=deepcopy([a,b])
    out=aggregate_descriptor([a,b],'TEST','off','third',['g1','g2'])
    assert out['status']==state and out['numerator'] is None and out['denominator'] is None
    assert not permission('display',[out])['allowed'] and [a,b]==before


@pytest.mark.parametrize('change',[lambda p:p.update(weeks=[3]),lambda p:p.update(sourceHash='different'),lambda p:p.update(unitIds=['g1:0','g1:1']),lambda p:p.update(denominator=7),lambda p:p.update(numerator=9)])
def test_incompatible_future_duplicate_and_invalid_counts_never_become_available(change):
    a,b=component(1),component(2);change(b)
    out=aggregate_descriptor([a,b],'TEST','off','third',['g1','g2'])
    assert out['status']=='INSUFFICIENT' and out['numerator'] is None


def test_missing_component_not_silently_renamed_to_two_weeks():
    out=aggregate_descriptor([component(1)],'TEST','off','third',['g1','g2'])
    assert out['status']=='INSUFFICIENT' and out['denominator'] is None


def test_real_package_reader_integrity_and_all_original_reconciliation():
    name=os.environ.get('NFL_TEAM_QA_BUNDLE')
    if not name:pytest.skip('Real frozen team bundle not operator configured')
    index,docs,marker=read(Path(name))
    assert len(index['teams'])==32 and len(docs)==32 and marker['bundleId']
    for data in docs.values():
        d=json.loads(data)
        for p in d['productions']:
            assert all(e['originalReconciliation']=='MATCHED' for e in p['epa'])
            assert all(m['originalReconciliation']=='MATCHED' for m in p['metrics'].values())
    atl=json.loads(docs['ATL'])
    assert atl['productions'][0]['metrics']['redZone']['descriptor']['status']=='NO_OPPORTUNITIES'


def test_existing_destination_is_refused_before_write(tmp_path):
    from nfl_sideline_etl.team_w12.package import publish
    with pytest.raises(ValueError,match='New destination'):
        publish(tmp_path,lambda p:pytest.fail('Must not populate existing output'))


def test_new_package_tamper_after_rehash_and_physical_boundaries(tmp_path):
    import shutil
    from nfl_sideline_etl.situational import encoded, digest
    name=os.environ.get('NFL_TEAM_QA_BUNDLE')
    if not name:pytest.skip('Real frozen team bundle required')
    source=Path(name);root=tmp_path/'copy';shutil.copytree(source,root)
    target=root/'teams/BAL.json';d=json.loads(target.read_bytes());d['productions'][0]['thirdAttempts'][0]['yardsToGo']+=1;target.write_bytes(encoded(d))
    with pytest.raises(ValueError,match='integrity'):read(root)
    index=json.loads((root/'index.json').read_bytes());entry=next(t for t in index['teams'] if t['team']=='BAL');entry['documentHash']=digest(target.read_bytes());(root/'index.json').write_bytes(encoded(index))
    marker=json.loads((root/'COMPLETED.json').read_bytes());marker['bundleId']=digest(encoded(index));marker['files']['index.json']=marker['bundleId'];marker['files']['teams/BAL.json']=digest(target.read_bytes());(root/'COMPLETED.json').write_bytes(encoded(marker))
    with pytest.raises(ValueError,match='derivation'):read(root)
    for path in ['teams/BAL.json','index.json','COMPLETED.json']:shutil.copyfile(source/path,root/path)
    target.unlink();target.symlink_to(source/'teams/BAL.json')
    with pytest.raises(ValueError):read(root)
