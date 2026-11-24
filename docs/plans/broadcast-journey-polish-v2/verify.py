"""Read-only preservation gate for the UX finish; no historical gate is changed."""
from pathlib import Path
import hashlib, json, subprocess
ROOT = Path(__file__).resolve().parents[3]
BASE = '46e2252476738c8240a26b38242e66ca20a75d42'
allowed = {
 'web-ui/broadcast-journey/App.tsx', 'web-ui/broadcast-journey/journey.css',
 'web-ui/broadcast-journey/ObservationChoice.tsx', 'web-ui/broadcast-journey/choice.ts',
 'web-ui/broadcast-journey/choice.test.ts', 'web-ui/broadcast-journey/guided-reading.test.tsx',
 'web-ui/broadcast-real/Reading.tsx',
}
docs = 'docs/plans/broadcast-journey-polish-v2/'
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT, text=True)
def digest(data): return hashlib.sha256(data).hexdigest()
changed = git('diff','--name-only',BASE).splitlines()
new = git('ls-files','--others','--exclude-standard').splitlines()
assert all(p in allowed or p.startswith(docs) for p in changed + new), (changed,new)
# The relation matrix, fetch/session guards, transport, exact formatter, adapter,
# original tests, contracts, sources and public application are outside this allowlist.
public = {p.suffix:digest(p.read_bytes()) for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in ('.js','.css')}
assert public == {'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}, public
snapshots = {}
for p in (ROOT/'web-ui/public/data').rglob('*.json'):
 rel=p.relative_to(ROOT).as_posix();old=subprocess.check_output(['git','show',f'{BASE}:{rel}'],cwd=ROOT)
 assert old == p.read_bytes();snapshots[rel]=digest(old)
legacy='web-ui/src/components/visual-preparation-regressions.test.tsx'
assert (ROOT/legacy).read_bytes().count(b'  it.fails(') == 5
report=json.loads((Path(__file__).parent/'evidence/http.json').read_text())
assert report['documents'] == report['reconciledProjection'] == report['http']['documentsExactlyMatched'] == 48
assert len(report['http']['refusals']) == 16 and report['http']['sessionRequired'] and report['http']['noCorsWildcard']
assert report['primaryAndBackupUnchanged'] and report['completeReaderValidated'] and report['backupCompleteReaderValidated']
source=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery/20261019T024130Z-50e03b27/bundle')
assert {p.relative_to(source).as_posix():digest(p.read_bytes()) for p in source.rglob('*') if p.is_file()} == report['sourceHashes']
layouts=json.loads((Path(__file__).parent/'evidence/layouts.json').read_text())
assert len(layouts)==24 and all(r['overflow']==0 for r in layouts)
assert {(r['screen'],r['width'],r['font']) for r in layouts} == {(screen,width,font) for screen in ['calendar','matchup','reading'] for width in [1440,900,390,320] for font in ['16px','32px']}
flows=json.loads((Path(__file__).parent/'evidence/flows.json').read_text())
assert flows['gap']['relation']=='gap' and flows['gap']['values']==flows['gap']['bars']==0
assert flows['noReading']['primaryLinks']==0
assert flows['historical']['relation']=='archive' and flows['inclusive']['relation']=='includes'
assert flows['incompatible']['relation']=='incompatible' and flows['incompatible']['readings']==flows['incompatible']['values']==0
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
print(json.dumps({'base':BASE,'allowedPresentationChanges':sorted(allowed),'changedOutsideAllowlist':False,'publicAssetsUnchanged':public,'snapshotsUnchanged':snapshots,'legacyExpectedFailures':5,'readerDocuments':48,'bundleUnchanged':True,'layoutChecks':len(layouts),'horizontalOverflow':False,'flowGuardsChecked':True},indent=2))
