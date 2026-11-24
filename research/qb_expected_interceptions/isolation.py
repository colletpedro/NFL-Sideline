"""Hash the preserved stores and approved checkout, inspect listeners read-only."""
import argparse, subprocess
from common import *

def git(*args, cwd=ROOT): return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()

def snapshot():
    dirs = {'v1': V1, 'v2': V2, 'lab': LAB, 'approved': APPROVED}
    hashes = {}
    for name, base in dirs.items():
        for p in sorted(base.rglob('*')):
            rel = p.relative_to(base)
            if any(x in {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache'} for x in rel.parts): continue
            if p.is_file() and not p.is_symlink(): hashes[f'{name}/{rel}'] = sha(p)
    status = {name: dict(head=git('rev-parse', 'HEAD', cwd=p), status=git('status', '--porcelain', cwd=p))
              for name, p in [('approved', APPROVED), ('main', MAIN)]}
    listeners = subprocess.run(['lsof', '-nP', '-iTCP', '-sTCP:LISTEN'], capture_output=True, text=True).stdout
    return dict(files=hashes, checkouts=status, listeners=listeners)

def check(before, out):
    old = read(before); current = snapshot()
    assert old['files'] == current['files'], 'Preserved artifact bytes changed'
    assert old['checkouts'] == current['checkouts'], 'Preserved checkout HEAD/status changed'
    changed = git('diff', '--name-only', BASE).splitlines() + git('ls-files', '--others', '--exclude-standard').splitlines()
    allowed = ('research/qb_expected_interceptions/', 'docs/plans/qb-expected-interceptions-v1/')
    assert all(p.startswith(allowed) for p in changed), changed
    # Existing listener PID/endpoint must remain; do not require unrelated new listeners to vanish.
    expected = [x for x in old['listeners'].splitlines() if ':18124 ' in x]
    assert all(x in current['listeners'] for x in expected), 'Approved listener changed'
    write(out, dict(passed=True, sourceFiles=len(old['files']), beforeSha256=sha(before),
        approved=current['checkouts']['approved'], main=current['checkouts']['main'],
        approvedListenerBefore=expected, approvedListenerAfter=[x for x in current['listeners'].splitlines() if ':18124 ' in x],
        changedPaths=changed, publicProductAndPreviousResearchUnchanged=True))

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('mode', choices=['snapshot','check']); p.add_argument('--before'); p.add_argument('--out', required=True); a=p.parse_args()
    if a.mode == 'snapshot': write(a.out, snapshot())
    else: check(a.before, a.out)
