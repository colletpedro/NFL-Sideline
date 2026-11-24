"""Transparent artifacts and strict offline paths; no product imports or secrets."""
from pathlib import Path
import datetime, hashlib, json, sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = ROOT / 'docs/plans/qb-expected-interceptions-v1'
BASE = '5d7d7769ce71a6864edce4c7393a75913563595f'
MAIN = Path('/Users/pedrocollet/Downloads/NFL Sideline')
APPROVED = Path('/Users/pedrocollet/.codex/worktrees/qb-risk-lab-chart-focus-v3/NFL Sideline')
STORE = MAIN / 'editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1'
V1 = MAIN / 'editorial/local-artifacts/qb-interception-risk-baseline-v1/20261104-v1'
V2 = MAIN / 'editorial/local-artifacts/qb-risk-temporal-calibration-v2/20261104-v2'
LAB = MAIN / 'editorial/local-artifacts/qb-risk-lab-v1'
sys.path.insert(0, str(ROOT / 'research/qb_interception_risk'))
from dataset import FILTERS, KEY, unique
from model import features as context_features, RAW, NUM, CAT

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
        allow_nan=False, default=lambda x: x.item() if hasattr(x, 'item') else str(x)) + '\n')

def read(path): return json.loads(Path(path).read_text())
def config(): return read(HERE / 'config.json')
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def new_dir(path):
    p = Path(path).resolve()
    protected = [APPROVED, V1, V2, LAB, ROOT / 'web-ui', MAIN / 'web-ui']
    if any(p == x or p.is_relative_to(x) for x in protected): raise ValueError('Protected destination')
    if p.exists(): raise FileExistsError(p)
    p.mkdir(parents=True)
    return p

def verify_manifest(base, manifest='sources.json'):
    base = Path(base); m = read(base / manifest)
    paths = []
    for r in m['files']:
        p = (base / r['path']).resolve()
        if not p.is_relative_to(base.resolve()) or r['path'] in paths: raise ValueError('Unsafe source path')
        paths.append(r['path'])
        if sha(p) != r['sha256'] or p.stat().st_size != r['bytes']: raise ValueError(f'Source hash/size mismatch: {r["path"]}')
    return m

def eligible(d):
    import pandas as pd
    m = pd.Series(True, index=d.index)
    for name, rule in FILTERS:
        if name != 'window_W1_W7_for_2026': m &= rule(d).fillna(False)
    return m

def valid_prob(p):
    p = np.asarray(p, dtype=float)
    if not np.isfinite(p).all() or not ((p > 0) & (p < 1)).all(): raise ValueError('Invalid probability')
    return p

def offline():
    import socket
    def denied(*a, **kw): raise RuntimeError('Network disabled for offline research')
    socket.socket.connect = denied
    socket.create_connection = denied
