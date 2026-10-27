from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent/'checks';base='0e9855da47e7e1a77acea860296eb3c8b7d87435'
def git(*args,cwd=root):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
protected=['web-ui/src','web-ui/public/data','web-ui/build/runtime-client-mode.ts','web-ui/vite.config.ts','core-api','supabase','etl-pipeline/src/nfl_sideline_etl/season_analysis','etl-pipeline/src/nfl_sideline_etl/situational','etl-pipeline/src/nfl_sideline_etl/game_story','web-ui/broadcast-journey/season','web-ui/broadcast-journey/ranking-redzone/positions.ts','docs/static-snapshot-contract.md','Spec.md']
assert not git('diff',base,'--',*protected)
changes=git('diff','--name-only',base).splitlines();assert all(not c.startswith(('web-ui/src/','web-ui/public/data/','core-api/','supabase/')) for c in changes)
expected={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
assets={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'web-ui/dist/assets').iterdir() if p.suffix in expected};assert assets==expected,assets
reference=Path('/Users/pedrocollet/.codex/worktrees/broadcast-season-timeline-v1/NFL Sideline');assert git('rev-parse','HEAD',cwd=reference)==base and not git('status','--porcelain',cwd=reference)
tracked=git('ls-files','web-ui').splitlines();xfails=sum((root/p).read_text().count('it.fails(') for p in tracked if p.endswith(('.test.ts','.test.tsx')));assert xfails==5,xfails
r=dict(protectedPathsUnchanged=protected,publicAssetHashes=assets,referenceHead=base,referenceClean=True,expectedFailures=xfails,publicUnchanged=True)
(out/'isolation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
