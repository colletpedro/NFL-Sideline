"""Objective isolation proof. Read-only on approved checkouts and public builds."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE='a6d3672f770e7d5db3728edbff216b229fc6aba7'
APPROVED=Path('/Users/pedrocollet/.codex/worktrees/broadcast-score-curve-v2/NFL Sideline')
V2=Path('/Users/pedrocollet/.codex/worktrees/qb-risk-temporal-calibration-v2/NFL Sideline')
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
protected=['web-ui/src','web-ui/public','web-ui/vite.config.ts','web-ui/vercel.json','core-api','etl-pipeline','supabase','research/qb_interception_risk','research/qb_risk_temporal_v2','docs/plans/qb-interception-risk-baseline-v1','docs/plans/qb-risk-temporal-calibration-v2','docs/static-snapshot-contract.md','Spec.md']
assert not git(ROOT,'diff',BASE,'--',*protected)
assert git(APPROVED,'rev-parse','HEAD')=='5b38f04e559bad5fc1b4ef25116cc0afb93293d9'
assert git(V2,'rev-parse','HEAD')==BASE
assert not git(APPROVED,'status','--porcelain') and not git(V2,'status','--porcelain')
public={str(p.relative_to(ROOT/'web-ui/dist')):sha(p) for p in (ROOT/'web-ui/dist').rglob('*') if p.is_file()}
old={str(p.relative_to(APPROVED/'web-ui/dist')):sha(p) for p in (APPROVED/'web-ui/dist').rglob('*') if p.is_file()}
assert public==old,'Approved public build differs'
lab=ROOT/'web-ui/risk-lab-dist';assert not (lab/'data').exists()
assert b'risk-lab' not in (ROOT/'web-ui/dist/index.html').read_bytes()
receipt=dict(status='PASS',base=BASE,approvedHead=git(APPROVED,'rev-parse','HEAD'),v2Head=git(V2,'rev-parse','HEAD'),approvedClean=True,v2Clean=True,protectedPathsUnchanged=protected,publicBuildFiles=len(public),publicBuildByteEquality=True,publicAssetHashes={k:v for k,v in public.items() if k.startswith('assets/')},labBuildHasNoPublicDataDirectory=True,labBuildSeparate=str(lab))
out=ROOT/'docs/plans/qb-risk-lab-v1/evidence/isolation.json';out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
