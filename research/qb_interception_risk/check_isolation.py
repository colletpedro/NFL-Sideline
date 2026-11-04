"""Read-only product isolation proof. Never restart/kill a server or read .env."""
from pathlib import Path
import argparse,json,subprocess,hashlib
from acquire import APPROVED,sha
from dataset import dump
BASE='5b38f04e559bad5fc1b4ef25116cc0afb93293d9'
ROOT=Path(__file__).resolve().parents[2]
APPROVED_TREE=Path('/Users/pedrocollet/.codex/worktrees/broadcast-score-curve-v2/NFL Sideline')
ALLOWED=('research/qb_interception_risk/','docs/plans/qb-interception-risk-baseline-v1/')
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def check(out):
 changed=git('diff','--name-only',BASE).splitlines();untracked=git('ls-files','--others','--exclude-standard').splitlines()
 if any(not p.startswith(ALLOWED) for p in changed+untracked):raise ValueError('Change outside research/documentation scope')
 # Compare both Git trees and physical file state for the complete operational product.
 protected=['web-ui','core-api','etl-pipeline','supabase','contracts','editorial','scripts','.github','AGENTS.md','Spec.md','docs/static-snapshot-contract.md','docs/current-state.md']
 trees={p:git('rev-parse',f'{BASE}:{p}') for p in protected}
 if git('diff',BASE,'--',*protected):raise ValueError('Operational files changed')
 approved_head=git('rev-parse','HEAD',cwd=APPROVED_TREE);approved_status=git('status','--porcelain',cwd=APPROVED_TREE)
 if approved_head!=BASE or approved_status:raise ValueError('Approved worktree changed')
 h=sha(APPROVED)
 if h!='7a5f4fa5b933b24474d8a5a8c76e57b23b8b50b7e62950ab1e5c9ea00cbf4507':raise ValueError('Pinned approved PBP changed')
 xfails=sum((ROOT/p).read_text().count('it.fails(') for p in git('ls-files','web-ui').splitlines() if p.endswith(('.test.ts','.test.tsx')))
 if xfails!=5:raise ValueError('Expected legacy failure definitions changed')
 listening=subprocess.run(['lsof','-nP','-iTCP:18111','-sTCP:LISTEN'],capture_output=True,text=True)
 dump(out,dict(passed=True,base=BASE,branch=git('branch','--show-current'),protected_git_objects=trees,approved_worktree_head=approved_head,approved_worktree_clean=True,pinned_pbp_sha256=h,legacy_expected_failure_definitions=xfails,changed_paths=changed,untracked_scoped_paths=untracked,server_18111=listening.stdout.strip(),server_probe='read-only lsof; no HTTP/browser requests or process changes',public_product_unchanged=True,no_merge_push_deploy=True))
 print('PASS: protected product, approved worktree, pinned source and five legacy failure definitions unchanged')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();check(Path(a.out))
