"""Read-only preservation proof, including scientific stores and original checkouts."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MAIN=Path('/Users/pedrocollet/Downloads/NFL Sideline')
BASE='a2466636dec1d7feb8c3975cf984d7b505711dde'
TREES={'visual':Path('/Users/pedrocollet/.codex/worktrees/qb-risk-lab-chart-focus-v3/NFL Sideline'),'b2':Path('/Users/pedrocollet/.codex/worktrees/qb-expected-interceptions-v1/NFL Sideline'),'main':MAIN}
STORES={name:MAIN/'editorial/local-artifacts'/name for name in ['qb-risk-lab-v1','qb-expected-interceptions-v1','qb-interception-risk-baseline-v1','qb-risk-temporal-calibration-v2']}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*a,cwd=ROOT):return subprocess.check_output(['git',*a],cwd=cwd,text=True).strip()
def snapshot():
 files={}
 for name,base in {**STORES,'visual-checkout':TREES['visual'],'b2-checkout':TREES['b2']}.items():
  for p in sorted(base.rglob('*')):
   rel=p.relative_to(base)
   if any(k in {'.git','.venv','node_modules','__pycache__','.pytest_cache'} for k in rel.parts):continue
   if p.is_file() and not p.is_symlink():files[f'{name}/{rel}']=sha(p)
 return dict(files=files,checkouts={n:dict(head=git('rev-parse','HEAD',cwd=p),status=git('status','--porcelain',cwd=p)) for n,p in TREES.items()},listeners=subprocess.run(['lsof','-nP','-iTCP','-sTCP:LISTEN'],capture_output=True,text=True).stdout)
def check(before):
 old=json.loads(Path(before).read_text());new=snapshot();assert old['files']==new['files'];assert old['checkouts']==new['checkouts']
 approved=[x for x in old['listeners'].splitlines() if ':18124 ' in x];assert all(x in new['listeners'] for x in approved)
 protected=['web-ui/src','web-ui/public','web-ui/package.json','web-ui/package-lock.json','web-ui/vite.config.ts','core-api','etl-pipeline','supabase','editorial','research/qb_interception_risk','research/qb_risk_temporal_v2','research/qb_expected_interceptions','research/qb_risk_lab','docs/plans/qb-expected-interceptions-v1','docs/plans/qb-risk-lab-chart-focus-v3','Spec.md','docs/static-snapshot-contract.md']
 assert not git('diff',BASE,'--',*protected),'Protected tracked paths changed'
 return dict(passed=True,sourceFiles=len(old['files']),checkouts=new['checkouts'],approvedListener=approved,protectedPaths=protected,base=BASE)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['snapshot','check']);a.add_argument('--before');a.add_argument('--out',required=True);v=a.parse_args();r=snapshot() if v.mode=='snapshot' else check(v.before);Path(v.out).write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
