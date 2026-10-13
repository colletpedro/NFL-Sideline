"""Selected raw evidence and exact denominator examples, never temporal certification."""
import argparse
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
from audit import encoded, FIELDS, FLAGS, ledger, parquet, sha


def supplement(workspace,output):
    inputs=json.loads((workspace/'inputs.json').read_text())['seasons'];inventory=json.loads((workspace/'inventory.json').read_text())
    result=dict(evidenceVersion='metrics-real-selected-evidence-v1',synthetic=False,selectionRule='lexicographically first observed game/play for each condition',seasons={})
    for season,selection in inputs.items():
        expected={e['frozen_path']:e['sha256'] for e in inventory['files'] if e['selected']}
        assert all(sha(p)==expected[p] for p in selection['calendar']+selection['pbp'])
        led=ledger(selection['calendar'],selection['pbp']);plays=[]
        for path in selection['pbp']:plays.extend(parquet(path).select(FIELDS).to_dicts())
        plays.sort(key=lambda r:(r['game_id'],Decimal(str(r['play_id']))))
        def sample(predicate):
            r=next((r for r in plays if predicate(r)),None)
            if r is None:return {'observed':False}
            return {k:str(v) if isinstance(v,float) else v for k,v in r.items()}
        cases={}
        for ph in sorted({g['phase'] for g in led['games'].values()}):
            gid=next(g for g,a in sorted(led['audits'].items()) if a['phase']==ph and a['unique_n'])
            cases[ph]=dict(game=led['games'][gid],counts=led['audits'][gid],offGroups=[])
            for (game,team,role,f),s in sorted(led['statistics'].items()):
                if game!=gid or role!='off':continue
                general=led['statistics'][game,team,role,'general']
                cases[ph]['offGroups'].append(dict(team=team,foundation=f,**{k:str(v) if isinstance(v,Fraction) else v for k,v in s.items()},
                    epa_exact=str(s['epa_sum']/s['epa_n']) if s['epa_n'] else None,
                    success_rate_exact=str(Fraction(s['success_n'],s['epa_n'])) if s['epa_n'] else None,
                    frequency_exact=str(Fraction(s['eligible_n'],general['eligible_n'])) if general['eligible_n'] else None,
                    interpretation='AUDITABLE_SUBSET only; not comparison-certified'))
        result['seasons'][season]=dict(cases=cases,rawMissingEPA=sample(lambda r:r['epa'] is None),
            conversionExcluded=sample(lambda r:r['play_type'] in ('pass','run') and r['two_point_attempt']==1),
            rawUnknownFlag=sample(lambda r:any(r[k] is None for k in FLAGS)),
            candidateMissingEPA=sum(r['epa'] is None and r['play_type'] in ('pass','run') for r in plays),
            candidateUnknownFlags=sum(r['play_type'] in ('pass','run') and any(r[k] is None for k in FLAGS) for r in plays),
            rawMissingEPAByType=dict(__import__('collections').Counter(str(r['play_type']) for r in plays if r['epa'] is None)),
            rawUnknownFlagByType=dict(__import__('collections').Counter(str(r['play_type']) for r in plays if any(r[k] is None for k in FLAGS))))
    with output.open('xb') as stream:stream.write(encoded(result))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();supplement(args.workspace,args.output)
