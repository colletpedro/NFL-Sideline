from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 'e5c36cee30813cb882536114f401e5bc34d5c754'
shared = {'.gitignore', 'web-ui/broadcast-journey/w12/Charts.tsx', 'web-ui/broadcast-journey/hub-team/TeamPage.tsx'}
files = {'web-ui/build/redzone-epa.ts', 'web-ui/build/redzone-epa-process.mjs', 'web-ui/build/redzone-epa-process.d.mts',
         'web-ui/scripts/redzone-epa-dev.mjs', 'web-ui/vite.redzone-epa.config.ts', 'web-ui/tsconfig.redzone-epa.json',
         'etl-pipeline/tests/test_redzone_epa.py'}
prefixes = ('docs/plans/broadcast-redzone-epa-v1/', 'etl-pipeline/src/nfl_sideline_etl/redzone_epa/', 'web-ui/broadcast-journey/redzone-epa/')


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True)


changed = set((git('diff', '--name-only', BASE)+git('ls-files', '--others', '--exclude-standard')).splitlines())
assert all(p in shared | files or p.startswith(prefixes) for p in changed), sorted(changed)
protected = [p for p in git('ls-tree', '-r', '--name-only', BASE).splitlines() if p not in shared]
assert not git('diff', BASE, '--', *protected)
assert (ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(') == 5
public = {p.suffix: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').glob('*') if p.suffix in ('.js', '.css')}
assert public == {'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5', '.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
js = '\n'.join(p.read_text() for p in (ROOT/'web-ui/dist/assets').glob('*.js'))
assert '/__redzone-epa/' not in js and 'classified-scrimmage-redzone-start-v1' not in js
ref = Path('/Users/pedrocollet/.codex/worktrees/broadcast-ranking-redzone-v1/NFL Sideline')
assert git('rev-parse','HEAD',cwd=ref).strip() == BASE and not git('status','--porcelain',cwd=ref)
config = json.loads((HERE/'source-config.json').read_bytes())
source = Path(config['path']); marker = json.loads((source/'COMPLETED.json').read_bytes())
for name, expected in marker['files'].items():
    assert 'sha256:'+hashlib.sha256((source/name).read_bytes()).hexdigest() == expected
for copy in ('verified-copy', 'reproduced-from-copy'):
    for p in source.rglob('*'):
        if p.is_file():assert p.read_bytes() == (source.parent/copy/p.relative_to(source)).read_bytes()
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
(HERE/'checks/isolation.json').write_text(json.dumps(dict(base=BASE,changedPaths=sorted(changed),
    publicHashes=public,referenceClean=True,sourcePin=config['expectedBundleId'],
    sourceFiles=len(marker['files'])+1,physicalCopyAndReproduction=True,fiveExpectedFailuresPreserved=True),indent=2)+'\n')
print('PASS: scope, public hashes, frozen original reference, new package, physical copy and reproduction')
