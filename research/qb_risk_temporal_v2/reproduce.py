"""Full offline v2 replay, including v1 reconstruction and scientific checks."""
from pathlib import Path
import argparse,json,socket
from common import HERE,V1_CODE,sha,dump,destination
from pipeline import main as v1_main
import sys
from experiment import run
from figures import run as figures

def disabled(*a,**k):raise RuntimeError('Network disabled during full reproduction')
def replay(store,out):
 socket.socket.connect=disabled;socket.create_connection=disabled
 store=Path(store);out=destination(out)
 # Reuse the complete v1 pipeline unchanged, in a fresh destination.
 old=sys.argv
 sys.argv=['v1','reproduce','--store',str(store/'inputs/v1'),'--development',str(store/'inputs/v1/development-v3'),'--out',str(out/'reference-v1')]
 try:v1_main()
 finally:sys.argv=old
 original=json.loads((store/'reference-v1-check.json').read_text());checks=[]
 for r in original['records']:
  actual=sha(out/'reference-v1'/r['reproduction']);checks.append(dict(path='reference-v1/'+r['reproduction'],expected=r['sha256'],actual=actual,byte_equal=actual==r['sha256']))
 if not all(r['byte_equal'] for r in checks):raise ValueError('V1 scientific reproduction mismatch')
 # An isolated logical store view: frozen inputs remain read-only; no copying/mutating originals.
 # run() accepts the reconstructed reference through the following explicit path override.
 run(store,out/'experiment',reference_dir=out/'reference-v1')
 figures(out/'experiment',out/'figures')
 return compare(store,out,checks)

def compare(store,out,checks=None,figures_dir='figures'):
 store=Path(store);out=Path(out)
 if checks is None:
  reference=json.loads((store/'reference-v1-check.json').read_text());checks=[dict(path='reference-v1/'+r['reproduction'],expected=r['sha256'],actual=sha(out/'reference-v1'/r['reproduction']),byte_equal=r['sha256']==sha(out/'reference-v1'/r['reproduction'])) for r in reference['records']]
 for source,target in [(store/'experiment-verified',out/'experiment'),(store/'figures-reviewed',out/figures_dir)]:
  for p in sorted(source.rglob('*')):
   if not p.is_file() or p.name=='environment.json':continue
   other=target/p.relative_to(source);expected=sha(p);actual=sha(other) if other.exists() else None
   checks.append(dict(path=str(other.relative_to(out)),expected=expected,actual=actual,byte_equal=expected==actual))
 summary=dict(passed=all(r['byte_equal'] for r in checks),scientific_files=len(checks),byte_identical=sum(r['byte_equal'] for r in checks),numerical_tolerance_policy='If bytes differ, inspect exact typed tables and predictions at atol1e-12/rtol1e-10; never report numerical equivalence as byte equality. This execution requires all listed scientific bytes equal.',expected_environment_differences='environment.json records code inventory/hashes and is excluded; dependencies pinned; platform-specific wheelhouse',network_connections_blocked=True,records=checks)
 report=out/('reproduction-check.json' if not (out/'reproduction-check.json').exists() else 'reproduction-check-rechecked.json')
 if report.exists():
  index=3
  while (out/f'reproduction-check-{index}.json').exists():index+=1
  report=out/f'reproduction-check-{index}.json'
 summary['figures_directory']=figures_dir
 dump(report,summary)
 if not summary['passed']:raise ValueError('Scientific replay mismatch; inspect preserved report')
 print('REPRODUCTION PASS',len(checks),'scientific files byte-identical',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--out',required=True);p.add_argument('--verify-existing',action='store_true');p.add_argument('--figures-dir',default='figures');a=p.parse_args()
 if a.verify_existing:compare(a.store,a.out,figures_dir=a.figures_dir)
 else:replay(a.store,a.out)
