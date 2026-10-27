from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE='38aa975c0bdd8c3d49c0acff8475cc106d149ae4'
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd,text=True)
shared={'.gitignore','web-ui/broadcast-journey/GameSearch.tsx','web-ui/broadcast-journey/hub-team/Hub.tsx','web-ui/broadcast-journey/hub-team/TeamPage.tsx','web-ui/broadcast-journey/hub-team/model.ts','web-ui/broadcast-journey/ranking-redzone/RankingLeague.tsx','web-ui/broadcast-journey/redzone-epa/Panel.tsx','web-ui/broadcast-journey/redzone-epa/model.ts','web-ui/broadcast-journey/w12/Charts.tsx','web-ui/broadcast-journey/w12/Content.tsx','web-ui/broadcast-journey/w12/model.ts'}
files={'web-ui/broadcast-journey/presentation.tsx','web-ui/build/season.ts','web-ui/build/season-process.mjs','web-ui/build/season-process.d.mts','web-ui/scripts/season-dev.mjs','web-ui/vite.season.config.ts','web-ui/tsconfig.season.json','etl-pipeline/tests/test_season_analysis.py'}
prefixes=('docs/plans/broadcast-w1-7-v1/','web-ui/broadcast-journey/season/','etl-pipeline/src/nfl_sideline_etl/season_analysis/')
changed=set((git('diff','--name-only',BASE)+git('ls-files','--others','--exclude-standard')).splitlines());assert all(p in shared|files or p.startswith(prefixes) for p in changed),sorted(changed)
protected=[p for p in git('ls-tree','-r','--name-only',BASE).splitlines() if p not in shared];assert not git('diff',BASE,'--',*protected)
assert (ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(')==5
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').glob('*') if p.suffix in ('.js','.css')}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
config=json.loads((HERE/'source-config.json').read_text());js='\n'.join(p.read_text() for p in (ROOT/'web-ui/dist/assets').glob('*.js'));assert '/__season-analysis/' not in js and config['pin'] not in js
reference=Path('/Users/pedrocollet/.codex/worktrees/broadcast-redzone-epa-v1/NFL Sideline');assert git('rev-parse','HEAD',cwd=reference).strip()==BASE and not git('status','--porcelain',cwd=reference)
original=Path('/Users/pedrocollet/Downloads/NFL Sideline');assert not git('diff','--name-only',cwd=original)
package=Path(config['bundle']);marker=json.loads((package/'COMPLETED.json').read_text());assert marker['bundleId']==config['pin']
for name,h in marker['files'].items():assert 'sha256:'+hashlib.sha256((package/name).read_bytes()).hexdigest()==h
for copy in ('verified-copy','reproduced-from-copy'):
 for p in package.rglob('*'):
  if p.is_file():assert p.read_bytes()==(package.parent/copy/p.relative_to(package)).read_bytes()
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
report=dict(base=BASE,changedPaths=sorted(changed),publicHashes=public,referenceClean=True,originalTrackedFilesUnchanged=True,newPackagePin=config['pin'],sourceFiles=len(marker['files'])+1,physicalCopyAndReproduction=True,fiveExpectedFailuresPreserved=True)
(HERE/'checks/isolation.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: scope, public bytes, original checkout, frozen W1–2 reference, exact recovery')
