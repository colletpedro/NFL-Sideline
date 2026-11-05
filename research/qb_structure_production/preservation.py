"""Read-only receipts; no process control or mutation outside this research."""
import argparse,subprocess,urllib.request
from common import *
LAB=Path('/Users/pedrocollet/.codex/worktrees/qb-risk-outcomes-lab-v1/NFL Sideline')

def receipt():
 def git(p,*args):return subprocess.check_output(['git','-C',str(p),*args],text=True).strip()
 stores={}
 for name in ['qb-risk-lab-v1','qb-risk-outcomes-lab-v1']:
  root=BASE/'editorial/local-artifacts'/name
  stores[name]={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
 tracked={str(p.relative_to(LAB)):sha(p) for rel in git(LAB,'ls-files').splitlines() if (p:=LAB/rel).is_file()}
 try:
  with urllib.request.urlopen('http://127.0.0.1:18125/?view=risk-lab&season=2026',timeout=10) as r:server=dict(status=r.status,sha256=hashlib.sha256(r.read()).hexdigest())
 except Exception as e:server=dict(status='unreachable',error=type(e).__name__)
 return dict(lab_head=git(LAB,'rev-parse','HEAD'),lab_branch=git(LAB,'branch','--show-current'),lab_status=git(LAB,'status','--porcelain'),main_head=git(BASE,'rev-parse','HEAD'),main_status=git(BASE,'status','--porcelain'),tracked_lab_files=tracked,active_stores=stores,server=server)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);a.add_argument('--before');v=a.parse_args();r=receipt()
 if v.before:
  old=read(v.before)
  # New ignored research store may add an untracked path under already-untracked local-artifacts; exact status otherwise.
  assert r==old,'Preexisting lab/main/store/server changed'
 write(v.out,r)
