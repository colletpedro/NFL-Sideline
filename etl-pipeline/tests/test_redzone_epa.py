from copy import deepcopy
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil

import pytest

from nfl_sideline_etl.offline_metrics.validation import FLAGS
from nfl_sideline_etl.redzone_epa.project import production, aggregate, summarize
from nfl_sideline_etl.redzone_epa.package import read, reproduce
from nfl_sideline_etl.situational import encoded, digest


def row(id_=1, **changes):
    return dict(game_id='2026_01_NE_SEA', play_id=id_, posteam='NE', defteam='SEA',
                order_sequence=id_, play_type='pass', yardline_100=20, epa=0.1,
                sack=0, qb_scramble=0, **{k: 0 for k in FLAGS}) | changes


def calculate(rows):
    return production(rows, 'NE', 'SEA', '2026_01_NE_SEA', 1)


@pytest.mark.parametrize('yardline,included', [(20, True), (19.99, True), (.01, True), (20.01, False), (100, False), (0, False)])
def test_start_position_boundaries(yardline, included):
    p = calculate([row(yardline_100=yardline)])
    assert p['validN'] == int(included)
    assert (p['status'] == 'AVAILABLE') is included


def test_end_position_and_campaign_outcome_do_not_select_population():
    p = calculate([row(1, yardline_100=21, yards_gained=20, touchdown=1),
                   row(2, yardline_100=20, yards_gained=-15, fixed_drive_result='Punt')])
    assert [u['id'] for u in p['units']] == ['2026_01_NE_SEA:2']


@pytest.mark.parametrize('flag', FLAGS)
def test_classified_scrimmage_exclusions_are_reused(flag):
    assert calculate([row(**{flag: 1})])['status'] == 'NO_OPPORTUNITIES'


@pytest.mark.parametrize('kind', ['field_goal', 'punt', 'no_play', 'qb_kneel', 'qb_spike', 'extra_point', 'kickoff'])
def test_non_pass_run_plays_do_not_enter(kind):
    assert calculate([row(play_type=kind)])['eligibleN'] == 0


def test_sacks_scrambles_negative_and_zero_are_real_values():
    p = calculate([row(1, sack=1, epa=-2), row(2, play_type='run', qb_scramble=1, epa=2), row(3, epa=0)])
    assert (p['status'], p['validN'], p['mean']) == ('AVAILABLE', 3, {'numerator': '0', 'denominator': '1'})
    assert p['units'][0]['sack'] and p['units'][1]['scramble']


def test_missing_and_nonfinite_epa_are_counted_and_never_zero_imputed():
    p = calculate([row(1, epa=None), row(2, epa=float('nan')), row(3, epa=float('inf')), row(4, epa=.5)])
    assert (p['eligibleN'], p['validN'], p['missingN'], p['nonfiniteN']) == (4, 1, 1, 2)
    assert p['mean'] == {'numerator': '1', 'denominator': '2'}
    for v in [None, float('nan')]:
        q = calculate([row(epa=v)])
        assert q['status'] == 'INSUFFICIENT' and q['mean'] is None


@pytest.mark.parametrize('change', [{'yardline_100': None}, {'yardline_100': float('nan')}, {'yardline_100': -1}, {'qb_kneel': None}])
def test_ambiguous_candidates_cannot_look_like_zero_opportunities(change):
    p = calculate([row(**change), row(2)])
    assert p['status'] == 'INSUFFICIENT' and p['mean'] is None and p['ambiguityN'] == 1


def test_unknown_flags_outside_redzone_do_not_hide_known_redzone_plays():
    p = calculate([row(yardline_100=30, qb_spike=None), row(2)])
    assert p['status'] == 'AVAILABLE' and p['validN'] == 1


def test_duplicate_units_and_wrong_adversary_fail_closed():
    with pytest.raises(ValueError, match='Duplicate'):
        calculate([row(), row()])
    with pytest.raises(ValueError, match='participant'):
        calculate([row(defteam='DAL')])
    with pytest.raises(ValueError, match='flag'):
        calculate([row(qb_kneel=2)])


def test_aggregate_sums_unique_plays_and_weights_by_valid_denominator():
    a = calculate([row(epa=.1)])
    b = calculate([row(2, epa=.2), row(3, epa=.3), row(4, epa=.4)])
    total = aggregate([a, b])
    assert Fraction(**{k: int(v) for k, v in total['mean'].items()}) == Fraction(1, 4)
    assert total['validN'] == 4
    assert aggregate([a, calculate([])])['mean'] == a['mean']
    with pytest.raises(ValueError, match='Duplicate'):
        aggregate([a, deepcopy(a)])


def test_aggregate_missing_or_insufficient_component_never_becomes_available():
    a = calculate([row()])
    for bad, status in [(None, 'SOURCE_ABSENT'), (calculate([row(2, epa=None)]), 'INSUFFICIENT')]:
        q = aggregate([a, bad])
        assert q['status'] == status and q['mean'] is None
    q = summarize([], missing_source=True)
    assert q['status'] == 'SOURCE_ABSENT' and q['mean'] is None


@pytest.fixture
def real_source():
    path = os.environ.get('NFL_REDZONE_EPA_QA_BUNDLE')
    if not path:
        pytest.skip('Explicit private red zone EPA QA source required')
    return Path(path)


def test_real_reader_full_semantics_and_reproduction(real_source, tmp_path):
    payload, marker = read(real_source)
    d = json.loads(payload)
    assert len(d['games']) == 32 and len(d['teams']) == 32
    assert sum(p['eligibleN'] for g in d['games'].values() for p in g['productions']) == 580
    assert reproduce(real_source, tmp_path/'reproduced') == marker


def test_rehashed_forged_metrics_definition_and_units_are_rejected(real_source, tmp_path):
    root = tmp_path/'tampered'
    shutil.copytree(real_source, root)
    original = (root/'redzone-epa.json').read_bytes()
    for field in ('mean', 'units', 'rule'):
        d = json.loads(original)
        if field == 'rule':
            d['rule'] = 'different-population'
        elif field == 'mean':
            d['games']['2026_01_NE_SEA']['productions'][0]['mean']['numerator'] = '1'
        else:
            d['games']['2026_01_NE_SEA']['productions'][0]['units'].pop()
        b = encoded(d)
        (root/'redzone-epa.json').write_bytes(b)
        m = json.loads((root/'COMPLETED.json').read_bytes())
        m['bundleId'] = digest(b)
        m['files']['redzone-epa.json'] = digest(b)
        (root/'COMPLETED.json').write_bytes(encoded(m))
        with pytest.raises(ValueError, match='semantic'):
            read(root)
    with pytest.raises(ValueError, match='pin'):
        read(real_source, 'sha256:wrong')
