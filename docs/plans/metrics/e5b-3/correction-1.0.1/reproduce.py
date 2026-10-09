"""Reproduce corrected review cases offline, on any correction HEAD; new output only."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[5]
    sys.path.insert(0, str(root / 'etl-pipeline/src'))
    from nfl_sideline_etl.temporal_metrics.core import select, comparison
    fixtures = root / 'etl-pipeline/tests/fixtures/temporal_metrics'
    package = json.loads((fixtures / 'package.json').read_text())
    query = json.loads((fixtures / 'request-pit.json').read_text())
    report = {'candidate': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
              'scope': 'SYNTHETIC_OFFLINE_COUNTEREXAMPLES', 'cases': {}}
    changed = deepcopy(package)
    cal = next(r for r in changed['resources'] if r['revision_id'] == 'calendar-v1')
    next(g for g in cal['payload']['games'] if g['game_id'] == 'target')['week'] = 4
    q = {**query, 'windows':['SEASON_TO_CUTOFF']}
    original, actual = select(package,q), select(changed,q)
    ob, ab = original['blocks'][0], actual['blocks'][0]
    assert ob['coverage']['expectedGames'] == ab['coverage']['expectedGames'] == 3
    assert ob['aggregates'] == ab['aggregates']
    assert ab['coverage']['knownEligibleGameIds'] == ['alpha','beta','gap']
    assert ab['coverage']['expectationFailures'] == []
    report['cases']['season_target_open_week'] = {
        'beforeExpectedGames':3, 'afterExpectedGames':3,
        'knownEligibleGameIds':ab['coverage']['knownEligibleGameIds'],
        'afterRequestedWeeks':ab['requestedWeeks'], 'afterExpectationFailures':[],
        'originalResultId':original['result_id'], 'changedResultId':actual['result_id'],
        'originalAuditId':original['audit_id'], 'changedAuditId':actual['audit_id']}
    def compare(p,lq,rq,foundation):
        l,r = select(p,lq),select(p,rq)
        lb,rb = l['blocks'][0],r['blocks'][0]
        la,ra = [next(a for a in b['aggregates'] if a['role']=='off' and a['foundation']==foundation) for b in (lb,rb)]
        assert la['comparisonEligible'] and ra['comparisonEligible']
        result = comparison(la,ra,lb,rb,l['request'],r['request'])
        assert result['failures'] == ['MISMATCH_REQUESTED_PERIOD']
        assert not result['comparisonEligible']
        return {'leftWeeks':lb['requestedWeeks'], 'rightWeeks':rb['requestedWeeks'],
                'leftEPA':la['epa']['exact'], 'rightEPA':ra['epa']['exact'],
                'bothAggregatesEligible':True, 'comparisonEligible':False, 'failures':result['failures'],
                'leftSignature':lb['requestedPeriod'],'rightSignature':rb['requestedPeriod'],
                'leftResultId':l['result_id'],'rightResultId':r['result_id'],
                'leftAuditId':l['audit_id'],'rightAuditId':r['audit_id']}
    q = {**query,'windows':['LAST_3_CALENDAR_WEEKS'],'targetWeek':2}
    report['cases']['different_recent_windows'] = compare(package,q,{**q,'targetWeek':3},'general')
    changed = deepcopy(package)
    changed['resources'] = [r for r in changed['resources'] if r['revision_id'] != 'state:gap']
    cal = next(r for r in changed['resources'] if r['revision_id'] == 'calendar-v1')
    cal['payload']['games'] = [g for g in cal['payload']['games'] if g['game_id'] != 'gap']
    for c in changed['calculations']:
        if c['game']['game_id']=='beta':
            for row in c['statistics']:
                row['eligible_n'] -= row['epa_missing_n']; row['epa_missing_n'] = 0
    q = {**query,'windows':['WEEK_OBSERVATION'],'week':1}
    report['cases']['different_week_observations'] = compare(changed,q,{**q,'week':3},'classified_pass')
    assert report['cases']['different_week_observations']['leftEPA'] == '1/2'
    assert report['cases']['different_week_observations']['rightEPA'] == '-1/3'
    with args.output.open('x') as stream:
        json.dump(report,stream,indent=2,sort_keys=True); stream.write('\n')
    print(json.dumps({'counterexamplesCorrected':3}))


if __name__ == '__main__':
    main()
