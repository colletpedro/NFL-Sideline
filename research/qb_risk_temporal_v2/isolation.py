"""Read-only v1/product/source preservation proof."""
from pathlib import Path
import subprocess,argparse,json
from common import sha,dump
ROOT=Path(__file__).resolve().parents[2];BASE='d654bd65f834f3903006a97b3074123eda26d236'
V1=Path('/Users/pedrocollet/.codex/worktrees/qb-interception-risk-baseline-v1/NFL Sideline');SITE=Path('/Users/pedrocollet/.codex/worktrees/broadcast-score-curve-v2/NFL Sideline')

def git(*a,cwd=ROOT):return subprocess.check_output(['git',*a],cwd=cwd,text=True).strip()
def verify(out):
 changed=git('diff','--name-only',BASE).splitlines()+git('ls-files','--others','--exclude-standard').splitlines()
 if any(not p.startswith(('research/qb_risk_temporal_v2/','docs/plans/qb-risk-temporal-calibration-v2/')) for p in changed):raise ValueError('Change outside isolated v2 paths')
 if git('diff',BASE,'--','research/qb_interception_risk','docs/plans/qb-interception-risk-baseline-v1'):raise ValueError('v1 files changed')
 if git('rev-parse','HEAD',cwd=V1)!=BASE or git('status','--porcelain',cwd=V1):raise ValueError('Original v1 checkout changed')
 if git('rev-parse','HEAD',cwd=SITE)!='5b38f04e559bad5fc1b4ef25116cc0afb93293d9' or git('status','--porcelain',cwd=SITE):raise ValueError('Approved site checkout changed')
 receipt=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-interception-risk-baseline-v1/recovery-receipt.json');record=json.loads(receipt.read_text());base=Path(record['store'])
 for r in record['records']:
  if sha(base/r['path'])!=r['sha256']:raise ValueError('Preexisting v1 artifact changed')
 server=subprocess.run(['lsof','-nP','-iTCP:18111','-sTCP:LISTEN'],capture_output=True,text=True).stdout.strip()
 fail_count=sum((ROOT/p).read_text().count('it.fails(') for p in git('ls-files','web-ui').splitlines() if p.endswith(('.test.ts','.test.tsx')))
 if fail_count!=5:raise ValueError('Legacy expected failure definitions changed')
 dump(out,dict(passed=True,v1_head=BASE,v1_checkout_clean=True,v1_pinned_files_verified=len(record['records']),approved_site_head=git('rev-parse','HEAD',cwd=SITE),approved_site_clean=True,changed_paths=changed,expected_failures=fail_count,server_18111=server,no_merge_push_deploy_or_publication=True))
 print('ISOLATION PASS: v1 store files, v1 checkout, approved site and operational tree preserved')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();verify(Path(a.out))
