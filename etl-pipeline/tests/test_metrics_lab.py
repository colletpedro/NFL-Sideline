"""Restricted transport acceptance uses only full synthetic accepted bundles."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil

import pytest
from nfl_sideline_etl.metrics_lab.adapter import prepare, dto
from nfl_sideline_etl.metrics_observations.publication import read
from nfl_sideline_etl.offline_metrics.artifact import identity, json_bytes
from nfl_sideline_etl.metrics_persistence.archive import digest

ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('demo',ROOT/'docs/plans/metrics/e5c-3/prepare_demo.py');demo=importlib.util.module_from_spec(s);s.loader.exec_module(demo)

@pytest.fixture(scope='module')
def configured(tmp_path_factory):
    root=tmp_path_factory.mktemp('metrics-lab')/'demo'
    config=demo.build(root,root/'missing-real')
    return root,config


def test_full_read_only_reduced_transport_and_error_no_fallback(configured):
    root,c=configured; snapshot=prepare(c)
    assert snapshot['entries'][0]['status']=='ERROR'
    ready=snapshot['entries'][1:]; assert all(e['status']=='READY' for e in ready)
    documents=[d for e in ready for d in e['documents']]
    assert len(documents)==120
    wire=json.dumps(snapshot)
    for forbidden in ('archive_root','bytes_base64','receipts','prompt','supplied_path',str(root),'/private/','lineage.json','context_json'):
        assert forbidden not in wire
    for d in documents:
        assert d['guarantees']['temporal']['state']=='UNKNOWN'
        assert d['fieldScopes']['unknownFilterFlagsN'].startswith('GAME_CONTEXT:')
        if d['totals']: assert isinstance(d['totals']['eligibleN'],str)
        for r in d['values'].values():
            if r: assert isinstance(r['denominator'],str)
    assert any(d['request']['phase']=='POST' and d['request']['origin']=='HISTORICAL_REFERENCE' for d in documents)
    assert snapshot==prepare(c)


def test_no_extract_or_synthetic_disguised_as_real(configured,tmp_path):
    root,c=configured
    bad=deepcopy(c);bad['bundles']=[bad['bundles'][1]];bad['bundles'][0]['dataKind']='REAL_ARCHIVE'
    assert prepare(bad)['entries'][0]['errorCode']=='SYNTHETIC_KIND_MISMATCH'
    bad['bundles'][0]['path']=str(ROOT/'docs/plans/metrics/e5c-2/real-observations.json')
    assert prepare(bad)['entries'][0]['status']=='ERROR'
    bad['bundles'][0]['path']=str(root/'absent')
    assert prepare(bad)['entries'][0]['status']=='ERROR'


@pytest.mark.parametrize('kind',['dependency','version','rehash','pin'])
def test_bad_full_bundles_never_become_ready(configured,tmp_path,kind):
    root,c=configured;target=tmp_path/'bundle';shutil.copytree(root/'synthetic',target)
    entry=deepcopy(c['bundles'][1]);entry['path']=str(target)
    if kind=='dependency':(target/'shared-source/lineage.json').unlink()
    elif kind=='version':
        m=json.loads((target/'COMPLETED.json').read_bytes());m['bundleVersion']='unknown';(target/'COMPLETED.json').write_bytes(json_bytes(m))
    elif kind=='pin':entry['expectedBundleId']='sha256:'+'f'*64
    else:
        docs=json.loads((target/'observations.json').read_bytes());docs[0]['guarantees']['temporal']['state']='KNOWN_AT_CUTOFF'
        from nfl_sideline_etl.metrics_observations.core import semantic_id
        old=docs[0]['observationId'];docs[0]['observationId']=semantic_id(docs[0]);new=docs[0]['observationId']
        (target/'observations.json').write_bytes(json_bytes(docs))
        manifest=json.loads((target/'manifest.json').read_bytes());manifest['observationIds']=sorted(new if i==old else i for i in manifest['observationIds'])
        manifest['lineageByObservation'][new]=manifest['lineageByObservation'].pop(old)
        manifest['bundleId']=identity({k:v for k,v in manifest.items() if k!='bundleId'});entry['expectedBundleId']=manifest['bundleId']
        (target/'manifest.json').write_bytes(json_bytes(manifest))
        marker=json.loads((target/'COMPLETED.json').read_bytes());marker['bundleId']=manifest['bundleId']
        marker['files']={name:digest((target/name).read_bytes()) for name in marker['files']}
        (target/'COMPLETED.json').write_bytes(json_bytes(marker))
    assert prepare({'configVersion':'metrics-lab-config-v1','bundles':[entry]})['entries'][0]['status']=='ERROR'


def test_missing_scopes_and_flags_limitations_refused(configured):
    root,c=configured;docs,manifest=read(root/'synthetic');d=next(x for x in docs if x['totals'])
    missing=deepcopy(manifest);missing['fieldScopes'].pop('unknownFilterFlagsN')
    with pytest.raises(ValueError):dto(d,missing,c['bundles'][1])
    d['limitations']=[x for x in d['limitations'] if x['code']!='UNKNOWN_FILTER_FLAGS_GAME_SCOPE']
    with pytest.raises(ValueError):dto(d,manifest,c['bundles'][1])


def test_versioned_client_vectors_match_operational_projection(configured):
    root,c=configured
    current={e['entryId']:e for e in prepare(c)['entries']}
    vectors=json.loads((ROOT/'web-ui/local-editorial/observations/test-fixtures/session.json').read_bytes())
    assert vectors['sessionId']==identity({k:v for k,v in vectors.items() if k!='sessionId'})
    for entry in vectors['entries']:
        expected={d['observationId']:d for d in current[entry['entryId']]['documents']}
        assert entry['bundleId']==current[entry['entryId']]['bundleId']
        assert all(d==expected[d['observationId']] for d in entry['documents'])
