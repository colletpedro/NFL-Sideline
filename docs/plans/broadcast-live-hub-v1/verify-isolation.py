"""Current-base public-isolation/preservation gate; historical gates untouched."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'docs/plans/broadcast-w12-expansion-v1'))
from nominal_selection import hashes, save

BASE='30140bee6af3eb02d00fb4b624399c1ff6e88f3d'
HERE=Path(__file__).resolve().parent

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def main():
    changed=git('diff','--name-only',BASE).decode().splitlines()
    untracked=git('ls-files','--others','--exclude-standard').decode().splitlines()
    # User-authorized logo contrast correction: only this shared visual component is added.
    assert all(p in ('.gitignore','web-ui/broadcast-experience/TeamLogo.tsx') or p.startswith('docs/plans/broadcast-live-hub-v1/') or p.startswith('web-ui/broadcast-journey/') for p in changed+untracked),(changed,untracked)
    protected=['web-ui/src','web-ui/public','web-ui/broadcast-real','web-ui/local-editorial','web-ui/build','web-ui/scripts',
               'web-ui/vite.config.ts','web-ui/vite.real.config.ts','web-ui/vite.experience.config.ts',
               'web-ui/vite.editorial.config.ts','web-ui/vite.journey.config.ts','web-ui/package-lock.json',
               'web-ui/package.json','web-ui/vercel.json','etl-pipeline','core-api','supabase','contracts',
               '.github','Spec.md','docs/static-snapshot-contract.md','docs/visual-reference',
               'docs/plans/broadcast-real-observation-v1','docs/plans/metrics/e5c-3r','docs/plans/broadcast-w12-expansion-v1','docs/plans/broadcast-media-pilot-v4']
    assert git('diff','--name-only',BASE,'--',*protected)==b''
    snapshots={}
    for p in (ROOT/'web-ui/public/data').rglob('*.json'):
        rel=str(p.relative_to(ROOT));assert git('show',f'{BASE}:{rel}')==p.read_bytes()
        snapshots[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    reg='web-ui/src/components/visual-preparation-regressions.test.tsx'
    old=git('show',f'{BASE}:{reg}');assert (ROOT/reg).read_bytes()==old and old.count(b'  it.fails(')==5
    public={}
    for p in (ROOT/'web-ui/dist/assets').iterdir():
        if p.suffix not in ('.js','.css'):continue
        text=p.read_text()
        for marker in ['__observations','broadcast-journey','REAL_ARCHIVE','w12-expansion','Archivo-Variable','RobotoCondensed-Variable']:assert marker not in text
        public[p.suffix]=hashlib.sha256(p.read_bytes()).hexdigest()
    assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
    for p in (ROOT/'web-ui/journey-dist/assets').glob('*.js'):
        for marker in ['dallas-new-england','O passe abre o caminho','readSlice','thirdDown','redzone','VITE_API_BASE_URL','/api/v1']:assert marker not in p.read_text(),marker
    selection=json.loads((ROOT/'docs/plans/broadcast-w12-expansion-v1/selection.json').read_bytes()); before=json.loads((ROOT/'docs/plans/broadcast-w12-expansion-v1/preserved-hashes.json').read_bytes())
    assert hashes(Path(selection['source']))==before==hashes(Path(selection['backup']))
    reconciliation=json.loads((ROOT/'docs/plans/broadcast-w12-expansion-v1/reconciliation.json').read_bytes())
    assert hashes(Path(reconciliation['bundlePath']))==reconciliation['bundleHashes']==hashes(Path(reconciliation['portablePath']))
    reference=Path('/Users/pedrocollet/.codex/worktrees/broadcast-w12-expansion-v1/NFL Sideline')
    assert subprocess.check_output(['git','status','--porcelain'],cwd=reference)==b''
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=reference).decode().strip()==BASE
    tracked=git('ls-files').decode().splitlines()
    assert not any(p.startswith('editorial/local-artifacts/broadcast-w12-expansion-v1/') for p in tracked)
    assert not any('scaleX(-1)' in p.read_text() for p in (ROOT/'web-ui/broadcast-journey').rglob('*.css'))
    subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
    result=dict(base=BASE,protectedPathsUnchanged=protected,publicBuildHashes=public,snapshotsUnchanged=snapshots,
        fiveExpectedLegacyFailuresPreserved=True,sourceAndBackupFileCount=len(before),sourceAndBackupUnchanged=True,
        primaryAndPortableBundleUnchanged=True,referenceCheckoutCleanAtExactBase=True,
        noPrivateArtifactsTracked=True,noSyntheticEngineInRealJourney=True,transportBoundaryUnchanged=True,diffCheck=True)
    save(HERE/'checks/isolation.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
