"""Offline publication, scientific invariance and atomic failure fixtures."""
import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import package as p

@pytest.fixture(scope='module')
def baseline():return p.presentation(p.SCIENTIFIC/'application-complete',p.SCIENTIFIC,p.M3_STORE)

def test_scientific_keys_and_probabilities_preserved(baseline):
 i,details,sources=baseline
 assert i['comparison']['sameEligiblePasses'] and i['comparison']['sharedPasses']==7970
 assert i['model']['sha256']==p.MODEL_SHA and i['summary']['observedInterceptions']==170
 for d in details.values():
  for r in d['plays']:
   expected=305/553 if r['ftnInterceptionWorthy'] else 75/16805
   assert p.near(r['pInterceptionGivenFtn'],expected)
  c=p.aggregate(d['plays']);assert c['expectedInterceptions']==c['expectedFromClassified']+c['expectedFromNotClassified']

def test_publication_determinism_and_m3_pointer_untouched(tmp_path,monkeypatch,baseline):
 monkeypatch.setattr(p,'presentation',lambda *a:copy.deepcopy(baseline));store=tmp_path/'outcomes';m3=p.sha(p.M3_STORE/'current.json')
 one=p.publish('ignored','ignored',store);two=p.publish('ignored','ignored',store)
 assert one['packageId']==two['packageId'] and one['indexSha256']==two['indexSha256']
 assert p.sha(p.M3_STORE/'current.json')==m3
 index=p.verify_package(store/'packages'/one['packageId']);assert index['target']=='observed_interception'

def test_failure_before_atomic_commit_preserves_valid_pointer_and_old_version(tmp_path,monkeypatch,baseline):
 monkeypatch.setattr(p,'presentation',lambda *a:copy.deepcopy(baseline));store=tmp_path/'outcomes';one=p.publish('ignored','ignored',store);pointer=(store/'current.json').read_bytes()
 newer=copy.deepcopy(baseline);newer[0]['acquiredAt']='2026-11-06T01:00:00+00:00';monkeypatch.setattr(p,'presentation',lambda *a:copy.deepcopy(newer));replace=p.os.replace
 def fail_pointer(source,dest):
  if Path(dest).name=='current.json':raise OSError('Simulated atomic pointer failure')
  return replace(source,dest)
 monkeypatch.setattr(p.os,'replace',fail_pointer)
 with pytest.raises(OSError):p.publish('ignored','ignored',store)
 assert (store/'current.json').read_bytes()==pointer
 assert p.verify_package(store/'packages'/one['packageId'])['packageId']==one['packageId']
 assert list((store/'runs').glob('*/failure.json')) and not (store/'.updating').exists()
 monkeypatch.setattr(p.os,'replace',replace);two=p.publish('ignored','ignored',store)
 assert two['packageId']!=one['packageId'] and (store/'packages'/one['packageId']).exists()

def test_missing_charting_never_imputed_and_manifest_tampering_fails(tmp_path,baseline):
 one=next(iter(baseline[1].values()))['plays'][0];assert isinstance(one['ftnInterceptionWorthy'],bool)
 source=tmp_path/'source';source.mkdir();(source/'data').write_text('pinned')
 with pytest.raises(ValueError,match='hash'):p.verify_files(source,{'data':'bad'})
 with pytest.raises(ValueError,match='Unsafe'):p.verify_files(source,{'../outside':'bad'})

def test_zero_events_small_support_and_identity_trades():
 plays=[dict(id='g:1',gameId='g',passerId='00-0000001',team='A',ftnInterceptionWorthy=False,observedInterception=False,pInterceptionGivenFtn=75/16805)]
 c=p.aggregate(plays);assert c['eligiblePasses']==1 and c['observedInterceptions']==0 and c['expectedInterceptions']>0 and c['differenceInterceptions']<0
 traded=plays+[dict(**{**plays[0],'id':'h:2','gameId':'h','team':'B'})];assert p.aggregate(traded)['games']==2

def test_protected_destination_refused():
 for path in [p.SCIENTIFIC,p.M3_STORE,p.ROOT,p.MAIN/'web-ui']:
  with pytest.raises(ValueError):p.safe_store(path)
