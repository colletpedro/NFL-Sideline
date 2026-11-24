"""Contraprovas do candidato E5b-3; nenhum banco, rede ou alteração no candidato."""
import argparse
from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess
import sys

CANDIDATE = '767cf7f1d15f26022a7c4a982545a6c24c125134'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.candidate.resolve(strict=True)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if head != CANDIDATE:
        parser.error('Use o checkout exato do candidato congelado: ' + CANDIDATE)
    sys.path.insert(0, str(root / 'etl-pipeline/src'))
    core = importlib.import_module('nfl_sideline_etl.temporal_metrics.core')
    fixtures = root / 'etl-pipeline/tests/fixtures/temporal_metrics'
    package = json.loads((fixtures / 'package.json').read_text())
    query = json.loads((fixtures / 'request-pit.json').read_text())
    report = {'candidate': head, 'scope': 'SYNTHETIC_OFFLINE_COUNTEREXAMPLES', 'cases': {}}

    # Somente o jogo alvo, sempre excluído por ID, passa para a Week 4 do pedido.
    # Nenhum jogo elegível ou somatório passado é alterado.
    changed = deepcopy(package)
    calendar = next(r for r in changed['resources'] if r['revision_id'] == 'calendar-v1')
    next(g for g in calendar['payload']['games'] if g['game_id'] == 'target')['week'] = 4
    q = {**query, 'windows': ['SEASON_TO_CUTOFF']}
    original = core.select(package, q)['blocks'][0]
    actual = core.select(changed, q)['blocks'][0]
    assert original['coverage']['expectedGames'] == 3
    assert actual['coverage']['knownEligibleGameIds'] == original['coverage']['knownEligibleGameIds']
    assert actual['coverage']['expectedGames'] is None
    assert actual['coverage']['expectationFailures'] == [{'reason': 'PERIOD_NOT_CLOSED', 'weeks': [4]}]
    report['cases']['season_target_open_week'] = {
        'change': 'Only excluded target week: 1 -> 4; closed prior weeks and eligible events unchanged.',
        'beforeExpectedGames': 3,
        'afterExpectedGames': None,
        'knownEligibleGameIds': actual['coverage']['knownEligibleGameIds'],
        'afterRequestedWeeks': actual['requestedWeeks'],
        'afterExpectationFailures': actual['coverage']['expectationFailures'],
        'expectedProperty': 'Excluded target/open future week must not invalidate proven prior-event coverage.',
    }

    def compare(p, lq, rq, foundation):
        left = core.select(p, lq)
        right = core.select(p, rq)
        lb, rb = left['blocks'][0], right['blocks'][0]
        la = next(a for a in lb['aggregates'] if a['role'] == 'off' and a['foundation'] == foundation)
        ra = next(a for a in rb['aggregates'] if a['role'] == 'off' and a['foundation'] == foundation)
        assert la['comparisonEligible'] and ra['comparisonEligible']
        result = core.comparison(la, ra, lb, rb, left['request'], right['request'])
        assert lb['requestedWeeks'] != rb['requestedWeeks']
        assert result['comparisonEligible'] and not result['failures']
        return {'leftWeeks': lb['requestedWeeks'], 'rightWeeks': rb['requestedWeeks'],
                'leftEPA': la['epa']['exact'], 'rightEPA': ra['epa']['exact'],
                'bothAggregatesEligible': True, 'comparisonEligible': result['comparisonEligible'],
                'failures': result['failures'],
                'expectedProperty': 'Different requested periods require explicit comparison failure.'}

    q = {**query, 'windows': ['LAST_3_CALENDAR_WEEKS'], 'targetWeek': 2}
    report['cases']['different_recent_windows'] = compare(package, q, {**q, 'targetWeek': 3}, 'general')

    # Um segundo cenário materializado sintético, sem a lacuna gap nem EPA ausente.
    # Conserva os 12 grupos e reconciliações general=pass+rush/off=opponent def.
    # Não certifica bytes reais ou recálculo de jogadas pelo adapter.
    changed = deepcopy(package)
    changed['resources'] = [r for r in changed['resources'] if r['revision_id'] != 'state:gap']
    calendar = next(r for r in changed['resources'] if r['revision_id'] == 'calendar-v1')
    calendar['payload']['games'] = [g for g in calendar['payload']['games'] if g['game_id'] != 'gap']
    for calculation in changed['calculations']:
        if calculation['game']['game_id'] == 'beta':
            for row in calculation['statistics']:
                row['eligible_n'] -= row['epa_missing_n']
                row['epa_missing_n'] = 0
    q = {**query, 'windows': ['WEEK_OBSERVATION'], 'week': 1}
    report['cases']['different_week_observations'] = compare(changed, q, {**q, 'week': 3}, 'classified_pass')
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'counterexamplesReproduced': len(report['cases']), 'candidate': head}))


if __name__ == '__main__':
    main()
