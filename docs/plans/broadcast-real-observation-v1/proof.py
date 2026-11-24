"""Read-only preflight/reconciliation using the complete accepted bundle reader.
No review extract, acquisition, SQL, generation or stored DTO input.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import http.client
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'etl-pipeline/src'))
from nfl_sideline_etl.metrics_observations.publication import read
from nfl_sideline_etl.metrics_lab.adapter import prepare, dto

PIN = 'sha256:2fae3be2b1ab7e5799287469ec29b9a98ff652a365ccafcb11b46c55d98ace8a'
BACKUP = Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/20261019T024130Z-50e03b27/bundle')

def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def request(port, path='/__observations/', method='GET', headers=None, body=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
    c.request(method,path,body=body,headers={'X-Local-Observations':'1',**(headers or {})})
    r=c.getresponse(); status=r.status; raw=r.read(); h=dict(r.getheaders()); c.close()
    return status,raw,h

def run(config, port, output):
    source=Path(config['bundles'][0]['path']); before=hashes(source); backup_before=hashes(BACKUP)
    docs,manifest=read(source)
    assert manifest['bundleId']==config['bundles'][0]['expectedBundleId']==PIN
    # Independent complete backup validation is evidence only, never selected as fallback.
    backup_docs,backup_manifest=read(BACKUP)
    assert backup_docs==docs and backup_manifest==manifest and backup_before==before
    snapshot=prepare(config)
    assert len(snapshot['entries'])==1
    entry=snapshot['entries'][0]
    assert entry['status']=='READY' and entry['dataKind']=='REAL_ARCHIVE' and len(docs)==len(entry['documents'])==48
    assert {d['subject']['team'] for d in docs}=={'BAL','DAL','NE'}
    expected_cohort={('BAL',2026,'REG',w) for w in [(1,),(2,),(1,2),(3,)]}|{('DAL',2026,'REG',w) for w in [(1,),(2,),(1,2)]}|{('NE',2025,'POST',(19,20,21,22))}
    assert {(d['subject']['team'],d['request']['season'],d['request']['phase'],tuple(d['request']['period']['weeks'])) for d in docs}==expected_cohort
    for d in docs:
        projected=next(p for p in entry['documents'] if p['observationId']==d['observationId'])
        assert projected==dto(d,manifest,config['bundles'][0])
        t=projected['totals']; values=projected['values']
        if t:
            stats=[m['statistics'] for m in projected['members'] if m['statistics'] is not None]
            for key in ['eligibleN','epaN','successN','epaMissingN','epaNonfiniteN','generalEligibleN','unknownFilterFlagsN']:
                assert int(t[key])==sum(int(m[key]) for m in stats)
            if t['epaSum'] is not None: assert Fraction(t['epaSum'])==sum(Fraction(m['epaSum']) for m in stats if m['epaSum'] is not None)
            assert values['volume']=={'numerator':t['eligibleN'],'denominator':'1'}
            if t['epaN']!='0':
                assert values['epa']=={'numerator':t['epaSum'],'denominator':t['epaN']}
                assert values['successRate']=={'numerator':t['successN'],'denominator':t['epaN']}
            if projected['subject']['foundation']=='general': assert values['frequency'] is None
            elif t['generalEligibleN']!='0': assert values['frequency']=={'numerator':t['eligibleN'],'denominator':t['generalEligibleN']}
        else: assert all(v is None for v in values.values())
    report={'bundleId':PIN,'sessionId':snapshot['sessionId'],'materializationId':manifest['source']['materializationId'], 'temporalInputId':manifest['source']['temporalInputId'],
        'completeReaderValidated':True,'backupCompleteReaderValidated':True,'pinMatched':True,'expectedCohortMatched':True,'documents':48,
        'reconciledProjection':48,'http':None,'sourceHashes':before,
        'states':dict(Counter('ABSENT' if d['totals'] is None else 'OBSERVED' for d in entry['documents'])),
        'guarantees':{k:sorted({d['guarantees'][k]['state'] for d in entry['documents']}) for k in ['integrity','completeness','coverage','temporal']},
        'epaModelStates':sorted({d['guarantees']['compatibility']['epaModel']['state'] for d in entry['documents']}),
        'identities':[{'observationId':d['observationId'],'dtoId':d['dtoId'],'subject':d['subject'],'request':d['request']} for d in entry['documents']]}
    if port:
        status,raw,headers=request(port,headers={'Origin':f'http://127.0.0.1:{port}'})
        assert status==200
        catalog=json.loads(raw); assert catalog['sessionId']==snapshot['sessionId']; assert len(catalog['bundles'])==1
        assert headers['Cache-Control']=='no-store' and headers['X-Content-Type-Options']=='nosniff'
        assert 'Access-Control-Allow-Origin' not in headers
        for e in catalog['bundles']:
            assert e['bundleId']==PIN and len(e['observations'])==48
            for s in e['observations']:
                status,raw,_=request(port,f"/__observations/{e['entryId']}/{s['observationId'][7:]}",headers={'X-Observation-Session':catalog['sessionId']})
                assert status==200; actual=json.loads(raw)
                d=next(p for p in entry['documents'] if p['observationId']==s['observationId'])
                assert actual['document']==d and actual['sessionId']==catalog['sessionId'] and s['dtoId']==d['dtoId']
        docpath=f"/__observations/{entry['entryId']}/{docs[0]['observationId'][7:]}"
        cases=[('/__observations/',{'Origin':'http://evil.invalid'},'GET',None,403),('/__observations/',{'Origin':'http://127.0.0.1:18083'},'GET',None,403),
            ('/__observations/',{'Host':'localhost:'+str(port)},'GET',None,403),('/__observations/',{'Host':'evil.invalid'},'GET',None,403),
            ('/__observations/',{'Host':'127.0.0.1:18083'},'GET',None,403),('/__observations/',{'X-Local-Observations':'0'},'GET',None,403),
            ('/__observations/',{},'POST',None,403),('/__observations/',{},'HEAD',None,403),('/__observations/',{},'OPTIONS',None,403),
            ('/__observations/',{},'GET','{}',403),('/__observations/?path=/etc/passwd',{},'GET',None,403),
            ('/__observations/../config.json',{},'GET',None,403),('/__observations/%2e%2e/config.json',{},'GET',None,403),
            (docpath,{},'GET',None,409),(docpath,{'X-Observation-Session':'stale'},'GET',None,409),
            ('/__observations/missing/'+'0'*64,{'X-Observation-Session':catalog['sessionId']},'GET',None,404)]
        results=[]
        for path,h,method,body,expected in cases:
            code,_,_=request(port,path,method,h,body); assert code==expected,(path,h,code)
            results.append({'path':path,'headers':h,'method':method,'status':code})
        report['http']={'origin':f'http://127.0.0.1:{port}','documentsExactlyMatched':48,'refusals':results,'sessionRequired':True,'noCorsWildcard':True}
    assert hashes(source)==before and hashes(BACKUP)==backup_before
    report['primaryAndBackupUnchanged']=True
    save(output,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['sourceHashes','identities','http']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--config',type=Path,default=Path(__file__).with_name('lab-config.json')); p.add_argument('--port',type=int); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); run(json.loads(a.config.read_text()),a.port,a.output)
