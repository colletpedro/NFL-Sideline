import sys,importlib.util
from pathlib import Path
import pandas as pd
import numpy as np
import pytest
spec=importlib.util.spec_from_file_location('progression_package',Path(__file__).with_name('package.py'));p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

@pytest.fixture(autouse=True)
def offline(monkeypatch):
 import urllib.request
 monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Offline test downloaded')))

def row(**k):
 r=dict(sack=0,qb_scramble=0,pass_attempt=1,rush_attempt=0,play_type='pass',aborted_play=0,is_throw_away=False,is_qb_out_of_pocket=False,read_thrown='DES',season=2026,charting_present=True,complete_pass=0,interception=0,passer_player_id='00-0000001',rusher_player_id=None,position='QB',identity_status='resolved');r.update(k);return r
@pytest.mark.parametrize('kw,cat', [({},'designed'),({'aborted_play':1},'indeterminate'),({'is_throw_away':True},'throwaway'),({'sack':1},'sack'),({'sack':1,'qb_scramble':1},'indeterminate'),({'charting_present':False},'indeterminate'),({'read_thrown':'0'},'progression'),({'read_thrown':'SD'},'scramble_drill'),({'read_thrown':None},'indeterminate'),({'qb_scramble':1,'pass_attempt':0,'rush_attempt':1,'play_type':'run','passer_player_id':None,'rusher_player_id':'00-0000001'},'scramble'),({'qb_scramble':1,'pass_attempt':0,'rush_attempt':1,'play_type':'run','passer_player_id':None,'rusher_player_id':'00-0000002','position':'WR'},'indeterminate')])
def test_des_precedence_and_identity(kw,cat):assert p.classify_v2(row(**kw))['category']==cat

def test_weighted_planned_and_missing():
 d=pd.DataFrame([dict(game_id='a',category='progression',epa=2.,charting_present=True,reason=None),dict(game_id='b',category='designed',epa=4.,charting_present=True,reason=None),dict(game_id='b',category='designed',epa=np.nan,charting_present=True,reason=None),dict(game_id='b',category='scramble',epa=0.,charting_present=True,reason=None)])
 s=p.summary(d);assert s['dropbacks']==4 and s['plannedDiagnostic']['n']==3 and s['plannedDiagnostic']['nEpa']==2 and s['plannedDiagnostic']['meanEpa']==3
 assert s['comparisons']['main']['frequency']==25 and s['comparisons']['main']['difference']==2
 assert s['categories']['sack']['meanEpa'] is None and s['categories']['sack']['sumEpa'] is None
 d.loc[d.category.eq('progression'),'epa']=np.nan;assert p.summary(d)['comparisons']['main']['difference'] is None

def test_all_categories_preserved_and_main_exact():
 d=pd.read_parquet(p.SCI/'package-release/plays.parquet');new=d.copy();labels=[p.classify_v2(r)['category'] for r in d.to_dict('records')];new['category']=labels
 changed=new.category.ne(d.category);assert d.loc[changed,'reason'].eq('designed_no_progression').all();assert new.category.isin(p.CATS).all()
 assert new[new.season.eq(2026)].category.value_counts()['designed']==797
 assert new[new.season.eq(2026)&new.position_class.eq('qb')].category.value_counts()['indeterminate']==1
 for cats in [['progression']]+list(p.GROUPS.values()):assert d.loc[d.category.isin(cats),p.KEY+['epa','player_id']].equals(new.loc[new.category.isin(cats),p.KEY+['epa','player_id']])

def test_replay_failure_keeps_pointer_and_recovers(tmp_path):
 root=p.publish(store=tmp_path);before=(tmp_path/'current.json').read_bytes();digest=p.sha(root/'index.json')
 with pytest.raises(OSError):p.publish(store=tmp_path,fail_pointer=True)
 assert (tmp_path/'current.json').read_bytes()==before and p.sha(root/'index.json')==digest
 assert p.publish(store=tmp_path)==root and not (tmp_path/'.updating').exists();assert p.check_package(root)['schemaVersion']==2

def test_update_rejects_changed_fixed_code_before_writing(tmp_path):
 import subprocess,json
 bad=tmp_path/'bad.json';bad.write_text(json.dumps(dict(schemaVersion=2,classificationVersion='2.0.0',codeSha256='0'*64)))
 out=tmp_path/'should-not-exist';result=subprocess.run([sys.executable,str(Path(__file__).with_name('update.py')),'--fixed-index',str(bad),'--frozen-science',str(p.SCI/'package-release'),'--store',str(tmp_path/'store'),'--out',str(out)],capture_output=True,text=True)
 assert result.returncode!=0 and 'Fixed v2 classification differs' in result.stderr and not out.exists()
