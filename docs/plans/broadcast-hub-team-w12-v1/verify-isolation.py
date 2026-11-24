"""Scope, public output, frozen source and all previous listeners; no credentials."""
from pathlib import Path
import subprocess,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE='945368956571cfc63ec1604337245fe822a138bc'
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd)
shared={'.gitignore','web-ui/broadcast-journey/GameSearch.tsx','web-ui/broadcast-journey/discoveryModel.ts','web-ui/broadcast-journey/w12/Charts.tsx','web-ui/broadcast-journey/w12/Content.tsx'}
changed=set(git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines())
allowed=lambda p:p in shared or p.startswith(('docs/plans/broadcast-hub-team-w12-v1/','etl-pipeline/src/nfl_sideline_etl/team_w12/','web-ui/broadcast-journey/hub-team/','web-ui/build/team')) or p in {'etl-pipeline/tests/test_team_w12.py','web-ui/scripts/hub-team-dev.mjs','web-ui/tsconfig.hub-team.json','web-ui/vite.hub-team.config.ts'}
assert all(allowed(p) for p in changed),sorted(p for p in changed if not allowed(p))
untouched=[p for p in git('ls-tree','-r','--name-only',BASE).decode().splitlines() if p not in shared];assert not git('diff',BASE,'--',*untouched)
assert (ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(')==5
ref=Path('/Users/pedrocollet/.codex/worktrees/broadcast-matchup-w12-v1/NFL Sideline');assert git('rev-parse','HEAD',cwd=ref).decode().strip()==BASE and not git('status','--porcelain',cwd=ref)
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').glob('*') if p.suffix in {'.js','.css'}}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
private='\n'.join(p.read_text() for p in (ROOT/'web-ui/hub-team-dist/assets').glob('*.js'));pub='\n'.join(p.read_text() for p in (ROOT/'web-ui/dist/assets').glob('*.js'))
assert '/__team-w12/' in private and 'broadcast-team-w12-v1' in private and json.loads((HERE/'team-source-config.json').read_bytes())['expectedBundleId'] in private
assert '/__team-w12/' not in pub and '/__matchup-w12/' not in pub and 'broadcast-team-w12-v1' not in pub
listeners={18098:30244,18099:30251,18100:30265,18101:95101,18102:97976,18103:44780,18104:57181}
for port,pid in listeners.items():assert f'127.0.0.1:{port}' in subprocess.check_output(['lsof','-nP','-a','-p',str(pid),f'-iTCP:{port}','-sTCP:LISTEN'],text=True)
source=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-matchup-w12-v1/20261024-v1/bundle-final');manifest=json.loads((ROOT/'docs/plans/broadcast-matchup-w12-v1/collection-manifest.json').read_bytes())
assert manifest==json.loads((source/'COMPLETED.json').read_bytes())
embedded=Path(json.loads((HERE/'team-source-config.json').read_bytes())['path'])/'source/matchups'
assert all((source/n).stat().st_ino!=(embedded/n).stat().st_ino for n in manifest['files'])
assert all('sha256:'+hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in manifest['files'].items())
assert not (ROOT/'web-ui/public/data/teams').exists()
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
(HERE/'checks/isolation.json').write_text(json.dumps(dict(base=BASE,allowedChangedPaths=sorted(changed),untouchedHistoricalFiles=len(untouched),publicHashes=public,oldListeners=listeners,referenceClean=True,fiveExpectedFailuresPreserved=True,originalCollectionUnchanged=True,privateBuildVerified=True,publicBuildPrivateFree=True),indent=2)+'\n')
print('PASS: scope, historical files, public hashes, source pin and seven old listeners')
