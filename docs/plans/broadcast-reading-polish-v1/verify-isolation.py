from pathlib import Path
import subprocess,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE='cb4e2cd181fdca5c2b0c11ff38c6c3ea20df6ad4'
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd)
shared={'.gitignore','web-ui/broadcast-journey/hub-team/Hub.tsx','web-ui/broadcast-journey/hub-team/TeamPage.tsx','web-ui/broadcast-journey/w12/Charts.tsx','web-ui/broadcast-journey/w12/Content.tsx'}
newfiles={'web-ui/scripts/reading-polish-dev.mjs','web-ui/tsconfig.reading-polish.json','web-ui/vite.reading-polish.config.ts'}
changed=set(git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines())
allowed=lambda p:p in shared|newfiles or p.startswith(('docs/plans/broadcast-reading-polish-v1/','web-ui/broadcast-journey/reading-polish/'))
assert all(allowed(p) for p in changed),sorted(p for p in changed if not allowed(p))
untouched=[p for p in git('ls-tree','-r','--name-only',BASE).decode().splitlines() if p not in shared];assert not git('diff',BASE,'--',*untouched)
assert (ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(')==5
ref=Path('/Users/pedrocollet/.codex/worktrees/broadcast-hub-team-w12-v1/NFL Sideline');assert git('rev-parse','HEAD',cwd=ref).decode().strip()==BASE and not git('status','--porcelain',cwd=ref)
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').glob('*') if p.suffix in {'.js','.css'}}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
pub='\n'.join(p.read_text() for p in (ROOT/'web-ui/dist/assets').glob('*.js'));private='\n'.join(p.read_text() for p in (ROOT/'web-ui/reading-polish-dist/assets').glob('*.js'))
assert all(x not in pub for x in ['/__team-w12/','/__matchup-w12/','broadcast-team-w12-v1','rp-attempt-symbol'])
assert '/__team-w12/' in private and 'rp-attempt-symbol' in private
listeners={18098:30244,18099:30251,18100:30265,18101:95101,18102:97976,18103:44780,18104:57181,18105:59966,18106:25458}
for port,pid in listeners.items():assert f'127.0.0.1:{port}' in subprocess.check_output(['lsof','-nP','-a','-p',str(pid),f'-iTCP:{port}','-sTCP:LISTEN'],text=True)
source=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle');marker=json.loads((source/'COMPLETED.json').read_bytes());assert marker['bundleId']=='sha256:8971d767b6ec0557465aeb65aeb00533fd10255a62f4b916954b3854daa15cef'
for name,h in marker['files'].items():assert 'sha256:'+hashlib.sha256((source/name).read_bytes()).hexdigest()==h,name
assert json.loads((source/'source/matchups/COMPLETED.json').read_bytes())['bundleId']=='sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc'
# No regeneration, new pin, or dependency on the reference checkout/process.
config=(ROOT/'web-ui/vite.reading-polish.config.ts').read_text();assert all(f'{reader}(18106)' in config for reader in ['teamBoundary','w12Boundary','observationBoundary','situationalBoundary','matchupBoundary']);assert "host:'127.0.0.1'" in config and 'strictPort:true' in config and 'cors:false' in config
assert not (ROOT/'web-ui/public/data/teams').exists()
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
(HERE/'checks/isolation.json').write_text(json.dumps(dict(base=BASE,changedPaths=sorted(changed),untouchedHistoricalFiles=len(untouched),publicHashes=public,listeners=listeners,referenceClean=True,fiveExpectedFailuresPreserved=True,sourceFilesVerified=len(marker['files']),sourcePin=marker['bundleId'],allReaders18106=True),indent=2)+'\n')
print('PASS: scope, historical files, frozen package, fixed public hashes, all eight prior listeners and own loopback')
