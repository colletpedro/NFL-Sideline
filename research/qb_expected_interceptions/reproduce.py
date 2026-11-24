"""Full offline reconstruction into a NEW destination, with byte/numeric receipts."""
import argparse
import pandas as pd
from common import *
from data import build
from run import develop, evaluate, refit, apply, verified_freeze
from figures import figures

def compare(expected,actual,skip=()):
    expected=Path(expected);actual=Path(actual);rows=[]
    old={str(p.relative_to(expected)):p for p in expected.rglob('*') if p.is_file() and p.name!='environment.json'}
    new={str(p.relative_to(actual)):p for p in actual.rglob('*') if p.is_file() and p.name!='environment.json'}
    assert set(old)==set(new),dict(missing=set(old)-set(new),added=set(new)-set(old))
    for rel,a in old.items():
        b=new[rel]
        if rel in skip:continue
        equal=sha(a)==sha(b)
        numeric=None
        if a.suffix=='.parquet':
            x=pd.read_parquet(a);y=pd.read_parquet(b)
            pd.testing.assert_frame_equal(x,y,check_exact=False,atol=1e-12,rtol=1e-10);numeric=True
        elif a.suffix=='.csv':
            x=pd.read_csv(a);y=pd.read_csv(b)
            pd.testing.assert_frame_equal(x,y,check_exact=False,atol=1e-12,rtol=1e-10);numeric=True
        rows.append(dict(path=rel,byte_equal=equal,numerically_equivalent=numeric,sha256=sha(b)))
        assert equal,f'Byte mismatch: {a} / {b}'
    return rows

def reproduce(store,out):
    offline();store=Path(store);verify_manifest(store);out=new_dir(out);checks={}
    build(store,out/'build');checks['build']=compare(store/'build',out/'build')
    develop(out/'build',out/'development')
    old=read(store/'development/freeze.json');new=read(out/'development/freeze.json');amendment=read(DOC/'evidence/output-fix.json')
    assert old['code_sha256']['run.py']==amendment['before'] and new['code_sha256']['run.py']==amendment['after']
    old_semantic={**old,'code_sha256':{k:v for k,v in old['code_sha256'].items() if k!='run.py'}}
    new_semantic={**new,'code_sha256':{k:v for k,v in new['code_sha256'].items() if k!='run.py'}}
    assert old_semantic==new_semantic,'Original pre-evaluation freeze not reproduced'
    checks['development']=compare(store/'development',out/'development',skip=('freeze.json',))
    # Models/config/selection have JUST been reproduced byte for byte. Retain the original
    # pre-evaluation freeze for subsequent provenance, never overwrite either freeze.
    verified_freeze(store/'development')
    evaluate(out/'build',store/'development',out/'evaluation');checks['evaluation']=compare(store/'evaluation',out/'evaluation')
    refit(out/'build',store/'development',out/'final');checks['final']=compare(store/'final',out/'final')
    apply(out/'build',store,out/'final',out/'application');checks['application']=compare(store/'application-complete',out/'application')
    figures(out/'evaluation',out/'application',out/'figures');checks['figures']=compare(store/'figures-reviewed',out/'figures')
    receipt=dict(passed=True,offline=True,source_manifest_sha256=sha(store/'sources.json'),
        comparisons=checks,byte_equal_files=sum(len(x) for x in checks.values()),
        numeric_tolerance=dict(atol=1e-12,rtol=1e-10),
        exclusions=['environment.json (runtime inventory)',
            'development/freeze.json: only run.py hash differs due to recorded cases-directory output fix; specification, configuration, selection, all model JSONs and results exact. Both freezes preserved. Original pre-2025 freeze used only after verifying fresh model byte identity.'],
        output_fix=amendment,no_labels_reused_for_calibration=True)
    write(out/'reproduction.json',receipt);print('OFFLINE REPRODUCTION PASS:',receipt['byte_equal_files'],'byte-identical scientific files',flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--store',default=str(STORE));a.add_argument('--out',required=True);v=a.parse_args();reproduce(v.store,v.out)
