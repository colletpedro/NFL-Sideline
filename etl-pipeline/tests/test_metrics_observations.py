"""Operational E5c-2 chain/projection/publication tests, entirely synthetic/offline."""
import base64
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from nfl_sideline_etl.metrics_observations.core import project_verified, semantic_id
from nfl_sideline_etl.metrics_observations.lineage import verify_source
from nfl_sideline_etl.metrics_observations.publication import generate, publish, read
from nfl_sideline_etl.metrics_materialization.core import materialize
from nfl_sideline_etl.metrics_materialization.publication import publish as publish_source, read as read_source
from nfl_sideline_etl.offline_metrics.artifact import identity, json_bytes
from nfl_sideline_etl.offline_metrics.statistics import exact_sum
from nfl_sideline_etl.metrics_persistence.archive import digest
from nfl_sideline_etl.temporal_metrics.core import canonical
from nfl_sideline_etl.temporal_metrics.validation import validate

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('e5c2_fixture', ROOT / 'docs/plans/metrics/e5c-2/build_fixture.py')
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)


@pytest.fixture
def chain():
    return fixture.source_fixture()


def one(docs, role='off', foundation='general', team='AAA'):
    return next(d for d in docs if d['subject'] == {'team': team, 'role': role, 'foundation': foundation})


def test_exact_sums_defensive_meaning_and_game_scoped_flags(chain):
    t, l = chain
    verify_source(t, l)
    _, docs, manifest = project_verified(t, l, fixture.nominal(t, l, teams=('AAA', 'BBB')))
    off = one(docs)
    defense = one(docs, role='def', team='BBB')
    assert off['totals'] == defense['totals']
    assert off['totals']['eligibleN'] == 3 and off['totals']['epaN'] == 2
    assert off['values']['epa'] == {'numerator': '-0.0000000000000000000000000000001', 'denominator': 2}
    assert off['values']['frequency'] is None
    passed = one(docs, foundation='classified_pass')
    assert passed['values']['frequency'] == {'numerator': '2', 'denominator': 3}
    assert Fraction(Decimal(passed['values']['epa']['numerator'])) / passed['values']['epa']['denominator'] == Fraction(-1, 2 * 10**31)
    assert passed['totals']['unknownFilterFlagsN'] == 1  # full-game context, not foundation measurement
    assert 'GAME_CONTEXT' in manifest['fieldScopes']['unknownFilterFlagsN']
    assert any(x['code'] == 'UNKNOWN_FILTER_FLAGS_GAME_SCOPE' for x in passed['limitations'])
    assert all(d['guarantees']['temporal']['state'] == 'UNKNOWN' for d in docs)
    assert manifest['comparison'] == 'NOT_IMPLEMENTED'


def test_absent_empty_unknown_complete_empty_and_zero(chain):
    t, l = chain
    _, docs, manifest = project_verified(t, l, fixture.nominal(t, l))
    d = one(docs, foundation='classified_pass')
    members = {m['gameId']: m for m in d['members']}
    assert members['synthetic-2']['sourceState'] == 'ABSENT' and members['synthetic-2']['statistics'] is None
    assert members['synthetic-3']['sourceState'] == 'PRESENT'
    assert members['synthetic-3']['completeness'] == 'UNKNOWN'
    assert members['synthetic-3']['statistics']['eligibleN'] == 0
    assert members['synthetic-4']['completeness'] == 'COMPLETE'
    assert members['synthetic-4']['statistics']['epaSum'] is None
    assert d['observed']['actualWeeks'] == [1, 2, 3]
    assert d['request']['period']['weeks'] == [1, 2, 3]
    assert d['guarantees']['coverage']['state'] == 'PARTIAL'
    assert d['guarantees']['coverage']['coverageRatio'] == {'numerator': '3', 'denominator': 4}
    missing_map = next(m for m in manifest['lineageByObservation'][d['observationId']]['associations'] if m['gameId'] == 'synthetic-2')
    assert missing_map['calculationId']  # original association preserved even when member number path is absent
    _, empty, _ = project_verified(t, l, fixture.nominal(t, l, weeks=(3,)))
    assert one(empty)['values']['volume'] == {'numerator': '0', 'denominator': 1}
    assert one(empty)['values']['epa'] is None
    # Exact EPA/success 0 are observations with positive denominator.
    assert one(docs, role='def')['values']['successRate'] == {'numerator': '1', 'denominator': 1}


def test_volume_available_without_epa():
    t, l = fixture.source_fixture(variant='no-epa')
    _, docs, _ = project_verified(t, l, fixture.nominal(t, l, weeks=(1,)))
    d = one(docs)
    assert d['values']['volume'] == {'numerator': '3', 'denominator': 1}
    assert d['values']['epa'] is None and d['values']['successRate'] is None
    assert one(docs, foundation='classified_pass')['values']['frequency']['denominator'] == 3


def test_raw_empty_unknown_is_not_promoted_to_observed_zero():
    t, l = fixture.source_fixture(variant='empty-file')
    _, docs, _ = project_verified(t, l, fixture.nominal(t, l, weeks=(1,)))
    d = one(docs)
    assert d['totals'] is None and all(x is None for x in d['values'].values())
    assert any(x['code'] == 'EMPTY_SOURCE_SET_WITHOUT_GAME_OBSERVATION' for x in d['limitations'])
    assert d['members'][0]['sourceState'] == 'ABSENT'


def test_partial_and_unknown_expectation_preserved():
    t, l = fixture.source_fixture(variant='partial')
    aux = deepcopy(l['auxiliary'])
    for r in aux['resources']:
        if r['kind'] == 'CALENDAR':
            r['payload']['complete'] = None
    t, l = materialize(l['relations'], l['recoveredArchives'], aux, l['derivedAt'])
    _, docs, _ = project_verified(t, l, fixture.nominal(t, l, weeks=(1,)))
    d = one(docs)
    assert d['guarantees']['completeness']['state'] == 'PARTIAL'
    assert d['guarantees']['coverage']['expectedCount'] is None
    assert d['guarantees']['coverage']['coverageRatio'] is None
    assert d['values']['epa'] is not None and d['guarantees']['compatibility']['epaModel']['state'] == 'UNKNOWN'


def test_request_permutation_and_replicas_do_not_duplicate_sample(chain):
    t, l = chain
    q = fixture.nominal(t, l)
    expected = project_verified(t, l, q)
    r = q['requests'][0]
    r['weeks'] = [3, 2, 1, 1]
    r['roles'] = ['def', 'off', 'off']
    r['associations'] = list(reversed(r['associations'])) * 2
    q['requests'] = [r, deepcopy(r)]
    assert project_verified(t, l, q) == expected


def test_presentation_and_derived_at_excluded_from_semantic_id(chain):
    t, l = chain; q = fixture.nominal(t, l)
    _, a, ma = project_verified(t, l, q)
    q['derivedAt'] = '2026-10-16T12:00:00Z'; q['presentation']['epaDecimals'] = 9
    _, b, mb = project_verified(t, l, q)
    assert [d['observationId'] for d in a] == [d['observationId'] for d in b]
    assert ma['bundleId'] == mb['bundleId']
    assert a != b


@pytest.mark.parametrize('kind', ['source', 'artifact', 'coverage', 'revision', 'calendar', 'participant', 'period', 'ambiguous', 'pit', 'version'])
def test_wrong_nominal_identity_scope_and_ambiguous_choices_refused(chain, kind):
    t, l = chain; q = fixture.nominal(t, l); r = q['requests'][0]
    if kind == 'source': q['source']['materializationId'] = 'sha256:' + 'f' * 64
    elif kind == 'artifact': r['associations'][0]['artifactId'] = 'sha256:' + 'f' * 64
    elif kind == 'coverage': r['associations'][0]['coverageRevisionId'] = 'sha256:' + 'f' * 64
    elif kind == 'revision': r['associations'][0]['temporalRevisionId'] = None
    elif kind == 'calendar': r['calendarSourceSetId'] = 'sha256:' + 'f' * 64
    elif kind == 'participant': r['teams'] = ['ZZZ']
    elif kind == 'period': r['weeks'] = [1]
    elif kind == 'ambiguous':
        alternate = deepcopy(r['associations'][0]); alternate['artifactId'] = 'wrong'; r['associations'].append(alternate)
    elif kind == 'pit': r['mode'] = 'POINT_IN_TIME'
    elif kind == 'version': q['requestVersion'] = 'unknown'
    with pytest.raises(ValueError): project_verified(t, l, q)


def test_atomic_publication_copy_and_no_overwrite(chain, tmp_path, monkeypatch):
    t, l = chain; q = fixture.nominal(t, l)
    dest = tmp_path / 'new'; publish(dest, t, l, q)
    copied = tmp_path / 'copied'; shutil.copytree(dest, copied)
    shutil.rmtree(dest)
    assert read(copied)[0] == project_verified(t, l, q)[1]
    with pytest.raises(FileExistsError): publish(copied, t, l, q)
    import nfl_sideline_etl.metrics_observations.publication as publication
    def fail(*args): raise OSError('injected atomic rename failure')
    monkeypatch.setattr(publication, 'rename_exclusive', fail)
    with pytest.raises(OSError): publish(tmp_path / 'fail', t, l, q)
    assert not (tmp_path / 'fail').exists() and not list(tmp_path.glob('.*.pending-*'))
    with pytest.raises(ValueError): publish(tmp_path / 'web-ui/public/data/not-allowed', t, l, q)


@pytest.mark.parametrize('kind', ['missing', 'bytes', 'symlink', 'extra', 'version', 'path'])
def test_closed_bundle_paths_and_hashes(chain, tmp_path, kind):
    t, l = chain; dest = tmp_path / 'bundle'; publish(dest, t, l, fixture.nominal(t, l))
    target = dest / 'shared-source/lineage.json'
    if kind == 'missing': target.unlink()
    elif kind == 'bytes': target.write_bytes(b'bad')
    elif kind == 'symlink':
        other = tmp_path / 'outside'; target.rename(other); target.symlink_to(other)
    elif kind == 'extra': (dest / 'connection.json').write_text('not allowed')
    elif kind == 'version':
        m = json.loads((dest / 'COMPLETED.json').read_bytes()); m['bundleVersion'] = 'unknown'; (dest / 'COMPLETED.json').write_bytes(json_bytes(m))
    elif kind == 'path': dest = dest / '..' / 'bundle'
    with pytest.raises((ValueError, OSError)): read(dest)


def test_rehashed_observation_cannot_diverge_from_originals(chain, tmp_path):
    t, l = chain; dest = tmp_path / 'bundle'; publish(dest, t, l, fixture.nominal(t, l))
    docs = json.loads((dest / 'observations.json').read_bytes())
    docs[0]['totals']['eligibleN'] += 1
    docs[0]['observationId'] = semantic_id(docs[0])
    (dest / 'observations.json').write_bytes(json_bytes(docs))
    marker = json.loads((dest / 'COMPLETED.json').read_bytes())
    marker['files']['observations.json'] = digest((dest / 'observations.json').read_bytes())
    (dest / 'COMPLETED.json').write_bytes(json_bytes(marker))
    with pytest.raises(ValueError, match='derivation differs'): read(dest)


def rehash_lineage(t, l):
    l['temporalInputId'] = identity(canonical(t))
    l['materialization_id'] = identity({k: v for k, v in l.items() if k != 'materialization_id'})


def test_forged_materialization_rehashed_but_not_reconciled(chain, tmp_path):
    t, l = chain
    # Preserve partition/general/opponent reconciliation while changing all EPA
    # sums. The accepted envelope reader alone accepts new external identities.
    for c in t['calculations']:
        for row in c['statistics']:
            if row['epa_sum'] is not None:
                from nfl_sideline_etl.offline_metrics.validation import decimal_text
                row['epa_sum'] = decimal_text(exact_sum([Decimal(row['epa_sum'])] * 2))
    rehash_lineage(t, l)
    source = tmp_path / 'forged'; publish_source(source, t, l)
    assert read_source(source) == (t, l)
    with pytest.raises(ValueError, match='diverges from accepted originals'):
        generate(source, fixture.nominal(t, l), tmp_path / 'never-published')
    assert not (tmp_path / 'never-published').exists()


@pytest.mark.parametrize('kind', ['sql-statistics', 'association', 'receipt', 'original-coverage', 'source-bytes'])
def test_original_relations_and_provenance_cannot_be_rehashed_away(chain, kind):
    t, l = chain
    if kind == 'sql-statistics':
        l['relations']['relations']['team_game_metric_sums'][0]['eligible_n'] += 1
    elif kind == 'association':
        l['relations']['relations']['metric_calculation_coverage'][0]['game_id'] = 'different'
    elif kind == 'receipt':
        ar = next(iter(l['recoveredArchives'].values())); receipt = next(iter(ar['receipts'].values()))
        receipt['origin']['reference'] = 'tampered'
        receipt['receipt_id'] = identity({k: v for k, v in receipt.items() if k != 'receipt_id'})
    elif kind == 'original-coverage': t['calculations'][0]['original']['coverage']['home_team'] = 'ZZZ'
    elif kind == 'source-bytes':
        ar = next(iter(l['recoveredArchives'].values())); sha = next(iter(ar['blobs'])); ar['blobs'][sha] = base64.b64encode(b'wrong').decode()
    rehash_lineage(t, l)
    with pytest.raises((ValueError, KeyError)): verify_source(t, l)


def test_alternative_batches_shared_coverage_nominal_choice_only():
    t1, l1 = fixture.source_fixture()
    t2, l2 = fixture.source_fixture(model='synthetic-model-v1')
    p = deepcopy(l1['relations']); p['selection'].extend(l2['relations']['selection'])
    for table, rows in l2['relations']['relations'].items():
        p['relations'][table] = list({json_bytes(row): row for row in p['relations'][table] + rows}.values())
    recovered = deepcopy(l1['recoveredArchives'])
    for aid, ar in l2['recoveredArchives'].items():
        recovered[aid]['blobs'].update(ar['blobs']); recovered[aid]['receipts'].update(ar['receipts'])
    aux = deepcopy(l1['auxiliary'])
    for key in ('resources', 'evidence', 'bindings'):
        aux[key] = list({json_bytes(x): x for x in aux[key] + l2['auxiliary'][key]}.values())
    t, l = materialize(p, recovered, aux, fixture.DERIVED)
    q = fixture.nominal(t, l, weeks=(1,))
    _, docs, _ = project_verified(t, l, q)
    assert one(docs)['totals']['eligibleN'] == 3
    assert len([c for c in t['calculations'] if c['game']['game_id'] == 'synthetic-1']) == 2
    assert len(one(docs)['members']) == 1


@pytest.mark.parametrize('variant', ['mixed-model', 'mixed-unknown'])
def test_mixed_source_models_refuse_instead_of_hiding_epa(variant):
    if variant == 'mixed-model':
        with pytest.raises(ValueError, match='Known EPA model versions differ'):
            fixture.source_fixture(variant=variant)
        return
    t, l = fixture.source_fixture(variant=variant)
    verify_source(t, l)  # Genuine complete accepted chain, not injected premises.
    with pytest.raises(ValueError, match='INCOMPATIBLE_EPA_MODELS_SEPARATED'):
        project_verified(t, l, fixture.nominal(t, l))


def test_no_temporal_or_comparison_input_and_cli(chain, tmp_path):
    t, l = chain; source = tmp_path / 'source'; publish_source(source, t, l)
    req = tmp_path / 'request.json'; req.write_bytes(json_bytes(fixture.nominal(t, l)))
    cmd = [sys.executable, '-B', '-m', 'nfl_sideline_etl.metrics_observations']
    output = tmp_path / 'result'
    subprocess.run(cmd + ['generate', '--materialized', str(source), '--request', str(req), '--output', str(output)], check=True, capture_output=True)
    result = subprocess.run(cmd + ['inspect', '--bundle', str(output)], check=True, capture_output=True)
    assert json.loads(result.stdout)['temporalGuarantee'] == 'NOT_DEMONSTRATED'
    assert subprocess.run(cmd + ['generate', '--materialized', str(source), '--request', str(req), '--output', str(output)], capture_output=True).returncode == 2


def test_driver_network_and_fixture_verifier_not_imported():
    program = '''
import builtins,socket,sys
old=builtins.__import__
def guarded(name,*a,**kw):
 if name.startswith(('psycopg','dotenv','requests','nflreadpy')) or name=='verify': raise AssertionError(name)
 return old(name,*a,**kw)
builtins.__import__=guarded
socket.create_connection=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('network'))
import nfl_sideline_etl.metrics_observations.core
import nfl_sideline_etl.metrics_observations.publication
import nfl_sideline_etl.metrics_observations.__main__
assert not any(x in sys.modules for x in ('psycopg2','dotenv','verify'))
'''
    subprocess.run([sys.executable, '-B', '-c', program], check=True)


@pytest.mark.parametrize('kind', ['basic-conflict', 'different-cutoff', 'included-target'])
def test_review_corrections_cannot_be_injected_as_guarantees(chain, tmp_path, kind):
    t, l = chain; dest = tmp_path / 'bundle'; publish(dest, t, l, fixture.nominal(t, l))
    docs = json.loads((dest / 'observations.json').read_bytes())
    if kind == 'basic-conflict':
        docs[0]['guarantees']['compatibility']['state'] = 'CONFLICT'
    elif kind == 'different-cutoff':
        docs[0]['guarantees']['temporal']['cutoff'] = '2026-01-01T00:00:00Z'
    else:
        docs[0]['guarantees']['temporal'].update(state='KNOWN_AT_CUTOFF',
            targetGameId=docs[0]['members'][0]['gameId'])
    docs[0]['observationId'] = semantic_id(docs[0])
    (dest / 'observations.json').write_bytes(json_bytes(docs))
    marker = json.loads((dest / 'COMPLETED.json').read_bytes())
    marker['files']['observations.json'] = digest((dest / 'observations.json').read_bytes())
    (dest / 'COMPLETED.json').write_bytes(json_bytes(marker))
    with pytest.raises(ValueError, match='derivation differs'): read(dest)
    assert project_verified(t, l, fixture.nominal(t, l))[1][0]['guarantees']['temporal']['targetGameId'] is None


def test_accepted_e5c1_exact_value_and_identity_vectors():
    from nfl_sideline_etl.metrics_observations.core import sufficient_values
    vectors = json.loads((ROOT / 'contracts/metrics/consumption-e5c1-v1/examples.json').read_bytes())
    for d in vectors['observations'].values():
        assert sufficient_values(d['totals'], d['subject']['foundation']) == d['values']
        assert semantic_id(d) == d['observationId']


def test_zero_is_not_missing_and_known_source_model_is_explicit():
    t, l = fixture.source_fixture(variant='zero', model='synthetic-model-v1')
    verify_source(t, l)
    _, docs, _ = project_verified(t, l, fixture.nominal(t, l, weeks=(1,)))
    d = one(docs)
    assert d['values']['epa'] == {'numerator': '0', 'denominator': 2}
    assert d['values']['successRate'] == {'numerator': '0', 'denominator': 2}
    assert d['guarantees']['compatibility']['epaModel'] == {'state': 'KNOWN', 'id': 'synthetic-model-v1'}
    assert all(m['evidenceIds'] for m in d['guarantees']['compatibility']['sourceModels'])
    assert d['guarantees']['temporal']['state'] == 'UNKNOWN'


def test_versioned_small_closed_fixture():
    path = ROOT / 'etl-pipeline/tests/fixtures/metrics_observations/materialized'
    t, l = read_source(path)
    verify_source(t, l)
    request = json.loads((path.parent / 'request.json').read_bytes())
    expected = json.loads((path.parent / 'observations.json').read_bytes())
    assert project_verified(t, l, request)[1] == expected
