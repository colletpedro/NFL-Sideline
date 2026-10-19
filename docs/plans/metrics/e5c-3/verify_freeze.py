"""Opt-in destructive probe ONLY for the generated synthetic demo; restores after restart.
Run before-restart, restart the lab, then after-restart using the same state directory.
"""
import argparse
import json
from pathlib import Path
from verify_http import request

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('phase',choices=['before-restart','after-restart'])
p.add_argument('--state',required=True,type=Path)
p.add_argument('--synthetic-bundle',type=Path)
a=p.parse_args()
if a.phase=='before-restart':
    assert a.synthetic_bundle and not a.state.exists()
    target=a.synthetic_bundle.resolve()/'observations.json'
    raw=target.read_bytes();docs=json.loads(raw)
    assert docs and all(d['subject']['team'] in ('AAA','BBB') and all(m['gameId'].startswith('synthetic-') for m in d['members']) for d in docs)
    status,catraw=request('/__observations/');assert status==200
    cat=json.loads(catraw);entry=next(e for e in cat['bundles'] if e['entryId']=='synthetic');s=entry['observations'][0]
    route=f"/__observations/synthetic/{s['observationId'][7:]}";headers={'X-Observation-Session':cat['sessionId']}
    status,docraw=request(route,headers=headers);assert status==200
    a.state.mkdir(parents=True);(a.state/'original.bin').write_bytes(raw)
    (a.state/'state.json').write_text(json.dumps({'target':str(target),'route':route,'sessionId':cat['sessionId'],'observationId':s['observationId']}))
    target.write_bytes(b'{"tampered":true}')
    assert request(route,headers=headers)==(200,docraw)
    assert request('/__observations/')==(200,catraw)
    print('PASS: disk changed; frozen catalog and document bytes identical. Restart lab now.')
else:
    state=json.loads((a.state/'state.json').read_text())
    try:
        status,raw=request('/__observations/');assert status==200
        cat=json.loads(raw);entry=next(e for e in cat['bundles'] if e['entryId']=='synthetic')
        assert entry['status']=='ERROR' and not entry['observations'] and cat['sessionId']!=state['sessionId']
        assert request(state['route'],headers={'X-Observation-Session':state['sessionId']})[0]==409
        print(json.dumps({'proof':'REAL_HTTP_SYNTHETIC_SESSION_FREEZE','frozenBytesIdentical':True,'restartInvalidEntry':'ERROR','oldSessionStatus':409,'oldSessionId':state['sessionId'],'newSessionId':cat['sessionId']},indent=2))
    finally:
        Path(state['target']).write_bytes((a.state/'original.bin').read_bytes())
        print('Original synthetic bytes restored. Restart required to make entry READY again.')
