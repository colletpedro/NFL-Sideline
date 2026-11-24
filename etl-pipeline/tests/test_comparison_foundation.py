"""Operation semantics and the isolated local boundary; optional real pinned QA."""
from copy import deepcopy
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import socket
import threading

import pytest

from nfl_sideline_etl.comparison_foundation.policy import decision
from nfl_sideline_etl.comparison_foundation.server import make_server, snapshot
from nfl_sideline_etl.comparison_foundation.package import read, reproduce, hashes
from nfl_sideline_etl.situational import digest, encoded


def observation(team='A', n=1, d=1):
    return dict(id=team+'/third', metric='third', team=team, perspective='off', season=2026, phase='REG', weeks=[1],
                definition='situational-1.0.0', population='third-eligible-1.0.0', unit='attempt', sourceHash='same-file',
                sourceColumn='third_down_converted', numerator=n, denominator=d, status='AVAILABLE' if d else 'NO_OPPORTUNITIES',
                unitIds=[team+str(i) for i in range(d)], gameIds=['same-game'], ambiguousIds=[], integrityVerified=True,
                provenanceVerified=True, guarantees={'completeness':'UNKNOWN'})


def test_one_of_one_is_descriptive_with_unknowns_untouched():
    a,b=observation(),observation('B',2,3);before=deepcopy([a,b])
    for op in ('sideBySide','difference','leagueReference'):
        result=decision(op,[a,b]);assert result['allowed']
        assert result['interpretation']=='OBSERVED_SAMPLE_DESCRIPTIVE'
        assert result['independence']=='NOT_ASSERTED' and result['commonGameIds']==['same-game']
    assert [a,b]==before


@pytest.mark.parametrize('field,value,reason',[
    ('sourceHash','other','INCOMPATIBLE_SOURCEHASH'),('definition','2','INCOMPATIBLE_DEFINITION'),
    ('population','other','INCOMPATIBLE_POPULATION'),('unit','campaign','INCOMPATIBLE_UNIT'),
    ('sourceColumn','first_down','INCOMPATIBLE_SOURCECOLUMN'),('weeks',[2],'OUTSIDE_PILOT_PERIOD_OR_FUTURE_CONTEXT'),
    ('phase','POST','OUTSIDE_PILOT_PERIOD_OR_FUTURE_CONTEXT'),('season',2025,'OUTSIDE_PILOT_PERIOD_OR_FUTURE_CONTEXT'),
    ('integrityVerified',False,'UNVERIFIED_SOURCE'),('provenanceVerified',False,'UNVERIFIED_SOURCE'),
    ('status','SOURCE_ABSENT','SOURCE_ABSENT'),('status','INSUFFICIENT','INSUFFICIENT'),
    ('ambiguousIds',['play'],'AMBIGUOUS_UNITS'),('numerator',2,'INVALID_NUMERATOR_DENOMINATOR'),
    ('numerator',None,'INVALID_NUMERATOR_DENOMINATOR'),('denominator',-1,'INVALID_NUMERATOR_DENOMINATOR'),
    ('denominator',True,'INVALID_NUMERATOR_DENOMINATOR')])
def test_concrete_operation_rejects_unproven_requirements(field,value,reason):
    a,b=observation(),observation('B');b[field]=value
    result=decision('difference',[a,b]);assert not result['allowed'] and reason in result['reasonCodes']


def test_available_does_not_authorize_every_comparison():
    a,b=observation(),observation('B');b['definition']='other'
    assert decision('display',[b])['allowed'] and not decision('sideBySide',[a,b])['allowed']


def test_zero_denominator_is_inventory_not_zero_rate():
    zero=observation('Z',0,0)
    assert decision('display',[zero])['allowed']
    assert not decision('sideBySide',[observation(),zero])['allowed']
    assert not decision('leagueReference',[zero])['allowed']
    real_zero=observation('R',0,5)
    assert decision('difference',[observation(),real_zero])['allowed']


def test_opponent_defense_same_units_cannot_be_subtracted_or_pooled():
    a=observation();mirror=deepcopy(a);mirror.update(id='defense',team='B',perspective='def')
    assert decision('sideBySide',[a,mirror])['allowed']
    assert 'OVERLAPPING_UNITS' in decision('difference',[a,mirror])['reasonCodes']
    assert not decision('leagueReference',[a,mirror])['allowed']


def test_league_must_have_unique_offensive_teams_and_no_epa():
    a,b=observation(),observation('B');b['team']='A'
    assert not decision('leagueReference',[a,b])['allowed']
    a['metric']='epa';a['numerator']='-2.45'
    assert decision('display',[a])['allowed']
    assert 'EPA_LEAGUE_OUT_OF_SCOPE' in decision('leagueReference',[a])['reasonCodes']


def unused_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]


def test_http_frozen_bytes_and_strict_port_and_refusals():
    port=unused_port();payload=b'{"frozen":true}\n';config=dict(port=port,expectedBundleId=digest(payload))
    server=make_server(config,payload);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pytest.raises(OSError):make_server(config,payload)
        base={'X-Local-Comparison':'1'}
        cases=[('GET','/__comparison/',base,None,200),('GET','/__comparison/',{**base,'Origin':f'http://127.0.0.1:{port}'},None,200),
               ('POST','/__comparison/',base,None,403),('OPTIONS','/__comparison/',base,None,403),
               ('GET','/__comparison/',{},None,403),('GET','/__comparison/?path=/etc/passwd',base,None,403),
               ('GET','/__comparison/child',base,None,403),('GET','/__situational/',base,None,403),
               ('GET','/__comparison/',{**base,'Host':f'localhost:{port}'},None,403),
               ('GET','/__comparison/',{**base,'Origin':'null'},None,403),
               ('GET','/__comparison/',{**base,'Origin':'https://example.com'},None,403),
               ('GET','/__comparison/',base,'x',403),('GET','/__comparison/',{**base,'Transfer-Encoding':'chunked'},None,403)]
        for method,path,headers,body,status in cases:
            c=HTTPConnection('127.0.0.1',port);c.request(method,path,body=body,headers=headers);r=c.getresponse();b=r.read()
            assert r.status==status
            if status==200:assert b==payload and r.getheader('Cache-Control')=='no-store' and r.getheader('X-Content-Type-Options')=='nosniff'
            c.close()
        c=HTTPConnection('127.0.0.1',port);c.putrequest('GET','/__comparison/');c.putheader('Host',f'127.0.0.1:{port}');c.putheader('X-Local-Comparison','1');c.endheaders()
        assert c.getresponse().status==403;c.close()
    finally:
        server.shutdown();server.server_close();thread.join()


@pytest.fixture
def real():
    path=os.environ.get('NFL_COMPARISON_QA_BUNDLE')
    if not path:pytest.skip('Explicit private comparison QA bundle required')
    return Path(path)


def test_real_reader_and_nominal_operations(real):
    d,m=read(real);assert m['bundleId']==digest((real/'comparison.json').read_bytes())
    assert len(d['productions'])==2 and len(d['facts'])==3
    assert all(c['difference']['allowed'] for c in d['comparisons'].values())
    assert d['guarantees']['epaModel']=='UNKNOWN'
    assert d['leagueReferences']['redZone']['teamsWithoutRate'][0]['team']=='ATL'


def test_real_startup_pin_and_freeze(real,tmp_path):
    _,marker=read(real)
    cfg=dict(configVersion='broadcast-comparison-config-v1',path=str(real),expectedBundleId=marker['bundleId'],port=18101,strictPort=True)
    p=tmp_path/'config.json';p.write_bytes(encoded(cfg))
    _,payload=snapshot(p);assert payload==(real/'comparison.json').read_bytes()
    cfg['expectedBundleId']='sha256:'+'0'*64;p.write_bytes(encoded(cfg))
    with pytest.raises(ValueError,match='pin mismatch'):snapshot(p)
    cfg['path']='/no/such/source';p.write_bytes(encoded(cfg))
    with pytest.raises(FileNotFoundError):snapshot(p)
    cfg['strictPort']=False;p.write_bytes(encoded(cfg))
    with pytest.raises(ValueError,match='Strict'):snapshot(p)


def test_real_reproduction_and_semantic_tamper_and_physical_rules(real,tmp_path):
    target=tmp_path/'reproduction';marker=reproduce(real,target)
    assert hashes(target)==hashes(real)
    cfg=dict(configVersion='broadcast-comparison-config-v1',path=str(target),expectedBundleId=marker['bundleId'],port=unused_port(),strictPort=True)
    config_path=tmp_path/'frozen-config.json';config_path.write_bytes(encoded(cfg))
    validated_config,frozen=snapshot(config_path)
    with pytest.raises(ValueError,match='New destination'):reproduce(real,target)
    path=target/'comparison.json';data=json.loads(path.read_bytes());data['productions'][0]['thirdAttempts'][0]['yardsToGo']+=1
    path.write_bytes(encoded(data))
    # Corrupt the disposable copy after startup validation; requests still return
    # the original frozen snapshot rather than rereading a now-invalid file.
    server=make_server(validated_config,frozen);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        c=HTTPConnection('127.0.0.1',cfg['port']);c.request('GET','/__comparison/',headers={'X-Local-Comparison':'1'})
        r=c.getresponse();assert r.status==200 and r.read()==(real/'comparison.json').read_bytes();c.close()
    finally:
        server.shutdown();server.server_close();thread.join()
    with pytest.raises(ValueError,match='hash mismatch'):read(target)
    marker['files']['comparison.json']=digest(path.read_bytes());marker['bundleId']=digest(path.read_bytes())
    (target/'COMPLETED.json').write_bytes(encoded(marker))
    with pytest.raises(ValueError,match='derivation mismatch'):read(target)
    path.write_bytes((real/'comparison.json').read_bytes());(target/'COMPLETED.json').write_bytes((real/'COMPLETED.json').read_bytes())
    (target/'extra').mkdir()
    with pytest.raises(ValueError,match='Unexpected package directory'):read(target)
    (target/'extra').rmdir();path.unlink();path.symlink_to(real/'comparison.json')
    with pytest.raises(ValueError):read(target)
