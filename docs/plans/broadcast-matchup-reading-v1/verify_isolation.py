"""New pilot only. Exact bootstrap/ignore additions; every other historical byte preserved."""
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
BASE='3c1a99b675cb4182323952ab08be8a7d8658175a'
REF=Path('/Users/pedrocollet/.codex/worktrees/broadcast-comparison-foundation-v1/NFL Sideline')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
allowed_exact={'.gitignore','web-ui/broadcast-journey/main.tsx','web-ui/vite.matchup.config.ts','web-ui/tsconfig.matchup.json','web-ui/build/matchup.ts','web-ui/build/matchup-process.mjs','web-ui/build/matchup-process.d.mts','web-ui/scripts/matchup-dev.mjs'}
allowed=lambda p:p in allowed_exact or p.startswith(('docs/plans/broadcast-matchup-reading-v1/','web-ui/broadcast-journey/matchup/'))
changed=sorted(set(git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines()))
assert all(allowed(p) for p in changed),changed
historic=git('ls-tree','-r','--name-only',BASE).decode().splitlines();unchanged=[p for p in historic if not allowed(p)]
assert not git('diff',BASE,'--',*unchanged).strip()
old=git('show',BASE+':web-ui/broadcast-journey/main.tsx').decode()
expected=old.replace("import React from 'react';","import React, { lazy, Suspense } from 'react';").replace("ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><App/></BrowserRouter></React.StrictMode>);","const MatchupPage = lazy(() => import('./matchup/MatchupPage'));\nconst pilot = new URLSearchParams(window.location.search).get('view') === 'matchup-reading';\nReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter>{pilot ? <Suspense fallback={<p role=\"status\">Abrindo leitura do confronto…</p>}><MatchupPage/></Suspense> : <App/>}</BrowserRouter></React.StrictMode>);")
assert (ROOT/'web-ui/broadcast-journey/main.tsx').read_text()==expected
assert (ROOT/'.gitignore').read_bytes()==git('show',BASE+':.gitignore')+b'\n# Build isolado da leitura piloto; nenhum snapshot privado versionado.\nweb-ui/matchup-dist/\n'
copy=json.loads((ROOT/'docs/plans/broadcast-comparison-foundation-v1/checks/copy.json').read_bytes())
def hashes(p):return {str(x.relative_to(p)):'sha256:'+hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(p.rglob('*')) if x.is_file()}
for p in (copy['primary'],copy['recoveryCopy']):assert hashes(Path(p))==copy['files']
source=json.loads((ROOT/'docs/plans/broadcast-comparison-foundation-v1/source-verification.json').read_bytes())
for path,h in source['sources'].items():assert hashes(Path(path))==h
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in ('.js','.css')}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
assert (ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(')==5
def get(port,path,header,session=None):
    headers={header:'1'}
    if session:headers['X-Observation-Session']=session
    with urlopen(Request(f'http://127.0.0.1:{port}'+path,headers=headers)) as r:return json.load(r)
situational=[get(port,'/__situational/','X-Local-Situational') for port in (18098,18099,18100,18102)]
assert all(x==situational[0] for x in situational)
catalogs=[get(port,'/__observations/','X-Local-Observations') for port in (18098,18099,18100,18102)]
assert all(x==catalogs[0] for x in catalogs)
assert get(18101,'/__comparison/','X-Local-Comparison')==get(18102,'/__matchup-reading/','X-Local-Matchup')
catalog=catalogs[0];samples=0
for bundle in catalog['bundles']:
    for o in bundle['observations']:
        if o['subject']['team'] in ('NYJ','TEN') and o['request']['period']['weeks'] in ([1],[1,2]):
            path=f"/__observations/{bundle['entryId']}/{o['observationId'][7:]}"
            assert get(18100,path,'X-Local-Observations',catalog['sessionId'])==get(18102,path,'X-Local-Observations',catalog['sessionId']);samples+=1
listeners={}
restored=json.loads((HERE/'checks/restored-references.json').read_bytes())
expectedPids={18098:49375,18099:64333,18100:74464,18101:95101,18102:97976}
for item in restored:
    root=Path(item['worktree'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==item['head']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=root)
    expectedPids[item['port']]=item['pid']
for port,pid in expectedPids.items():
    s=subprocess.check_output(['lsof','-nP','-a','-p',str(pid),f'-iTCP:{port}','-sTCP:LISTEN']).decode();assert f'127.0.0.1:{port}' in s;listeners[port]=s
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REF).decode().strip()==BASE
assert subprocess.check_output(['git','status','--porcelain'],cwd=REF)==b''
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
report=dict(base=BASE,referenceCleanAtExactHead=True,changed=changed,unchangedHistoricalFiles=len(unchanged),onlyTwoExplicitHistoricalAdditions=True,oldAppAndExplorerAndConfigurationsUnchanged=True,sourceAndCopiesAndPublicSnapshotsUnchanged=True,publicBuildHashes=public,fiveExpectedFailuresUnchanged=True,situationalHttpIdenticalDocuments=192,oldObservationCatalogIdentical=True,pilotAndInclusiveObservationResponsesIdentical=samples,foundationHttpIdentical=True,listeners=listeners)
(HERE/'checks/isolation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
