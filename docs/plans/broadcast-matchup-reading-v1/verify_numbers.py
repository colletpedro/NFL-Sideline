"""Independent rational presentation oracle; reads immutable JSON, never imports the projector/UI."""
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent
config = json.loads((HERE / 'source-config.json').read_bytes())
raw = (Path(config['path']) / 'comparison.json').read_bytes()
assert 'sha256:' + hashlib.sha256(raw).hexdigest() == config['expectedBundleId']
doc = json.loads(raw)
oracle = {'epa': {}}
details = {'pin': config['expectedBundleId'], 'productions': {}}
for production in doc['productions']:
    team = production['offense']
    detail = {}
    for epa in production['epa']:
        original = epa['originalObservation']
        value = original['values']['epa']
        assert value['numerator'] == original['totals']['epaSum']
        assert value['denominator'] == original['totals']['epaN']
        exact = Fraction(value['numerator']) / value['denominator']
        decimals = original['presentation']['epaDecimals']
        with localcontext() as context:
            context.prec = 100
            rounded = (Decimal(exact.numerator) / Decimal(exact.denominator)).quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)
        text = ('−' if rounded < 0 else '+') + format(abs(rounded), f'.{decimals}f').replace('.', ',')
        oracle['epa'][team + '/' + epa['foundation']] = dict(text=text, denominator=value['denominator'], exact=dict(numerator=str(exact.numerator), denominator=exact.denominator))
    attempts = production['thirdAttempts']
    thirds = production['metrics']['third']['descriptor']
    assert set(u['id'] for u in attempts) == set(thirds['unitIds'])
    assert (sum(u['converted'] for u in attempts), len(attempts)) == (thirds['numerator'], thirds['denominator'])
    joint = []
    for distance in ('short', 'medium', 'long', 'unknown'):
        for kind in ('pass', 'run'):
            units = [u for u in attempts if u['distance'] == distance and u['kind'] == kind]
            marginal = next(r for r in production['thirdDistanceByType'] if r['distance'] == distance and r['kind'] == kind)
            assert set(marginal['unitIds']) == {u['id'] for u in units}
            ratio = (sum(u['converted'] for u in units), len(units))
            assert ratio == (marginal['numerator'], marginal['denominator'])
            joint.append(dict(distance=distance, kind=kind, numerator=ratio[0], denominator=ratio[1]))
    long = [u for u in attempts if u['distance'] == 'long']
    assert (sum(u['converted'] for u in long), len(long)) == (1, 5)
    campaigns = production['redZoneCampaigns']
    red = production['metrics']['redZone']['descriptor']
    assert set(u['id'] for u in campaigns) == set(red['unitIds'])
    outcomes = Counter(u['outcome'] for u in campaigns)
    assert (outcomes['TOUCHDOWN'], len(campaigns)) == (red['numerator'], red['denominator'])
    assert all(u['entryEvidence'] and u['outcomeEvidence'] for u in campaigns)
    assert [u['sourceOrder'] for u in campaigns] == sorted(u['sourceOrder'] for u in campaigns)
    expected = {'NYJ': (2, 10, 2, 3), 'TEN': (4, 12, 1, 1)}[team]
    assert (thirds['numerator'], thirds['denominator'], red['numerator'], red['denominator']) == expected
    detail.update(thirdJoint=joint, thirdUnitIds=[u['id'] for u in attempts], redZoneUnitIds=[u['id'] for u in campaigns], outcomes=dict(outcomes))
    details['productions'][team] = detail
for family, expected in (('third', (32, 154, 377)), ('redZone', (31, 70, 108))):
    reference = doc['leagueReferences'][family]
    points = reference['teamRateDistribution']['points']
    assert all(p['perspective'] == 'off' and p['denominator'] > 0 for p in points)
    assert len({p['team'] for p in points}) == len(points)
    numerator, denominator = (sum(p[k] for p in points) for k in ('numerator', 'denominator'))
    assert (len(points), numerator, denominator) == expected
    assert (numerator, denominator) == (reference['pooledRate']['numerator'], reference['pooledRate']['denominator'])
    oracle[family] = dict(numerator=numerator, denominator=denominator)
    assert {'NYJ', 'TEN'} <= {p['team'] for p in points}
    if family == 'redZone':
        atl = next(p for p in reference['inventory'] if p['team'] == 'ATL')
        assert atl['status'] == 'NO_OPPORTUNITIES' and atl['denominator'] == 0 and atl['ratio'] is None
        assert 'ATL' not in {p['team'] for p in points}
# Keep the numerical fixture reproducible and independent of the TS formatter.
(HERE / 'checks/numerical-oracle.json').write_text(json.dumps(oracle, indent=2) + '\n')
browser = json.loads((HERE / 'evidence/browser.json').read_bytes())
for foundation in browser['epa']:
    for row in foundation['rows']:
        expected = oracle['epa'][row['team'] + '/' + foundation['foundation']]
        assert row['text'] == expected['text']
        assert row['denominator'] == str(expected['denominator']) + ' jogadas com EPA válido'
    assert foundation['third'] == 22 and foundation['redZone'] == 4
assert all((p['thirdMarks'], p['campaigns'], p['thirdPoints'], p['redZonePoints']) == (22, 4, 32, 31) for p in browser['layouts'])
details['browserAllSixEpaMatchIndependentOracle'] = True
(HERE / 'checks/numerical-details.json').write_text(json.dumps(details, indent=2) + '\n')
print('Independent Fraction/Decimal oracle: six EPA, real units/joint counts, 32/31 references and browser values verified.')
