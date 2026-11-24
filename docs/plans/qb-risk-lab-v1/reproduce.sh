#!/bin/sh
# Fully offline data/model reproduction. Choose a NEW destination outside checkouts.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
DEST=${1:?Provide a new absolute reproduction destination}
RECOVERY=${NFL_RISK_LAB_RECOVERY:-'/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-lab-v1/recovery/20261104-v1'}
case "$DEST" in /*) ;; *) echo 'Use an absolute destination' >&2; exit 2;; esac
case "$DEST/" in "$ROOT/"*) echo 'Use a destination outside the checkout' >&2; exit 2;; esac
if [ -e "$DEST" ]; then echo 'Destination exists; choose a new directory' >&2; exit 2; fi
python3.11 -m venv "$DEST/env"
"$DEST/env/bin/python" -m pip install --no-index --find-links "$RECOVERY/wheelhouse" -r "$RECOVERY/requirements.lock"
"$DEST/env/bin/python" "$ROOT/research/qb_risk_lab/pipeline.py" --store "$DEST/store" --sources "$RECOVERY/sources"
"$DEST/env/bin/python" "$ROOT/research/qb_risk_lab/verify.py" --store "$DEST/store" --sources "$RECOVERY/sources" --output "$DEST/reconciliation.json"
"$DEST/env/bin/python" - "$DEST" "$RECOVERY" <<'PY'
import sys,json,hashlib
from pathlib import Path
dest,recovery=map(Path,sys.argv[1:]);active=json.loads((dest/'store/current.json').read_text());new=dest/'store/packages'/active['packageId'];old=recovery/'package'
def files(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
assert files(new)==files(old),'Package bytes differ; inspect numeric equivalence before any claim'
r=dict(status='PASS',packageId=active['packageId'],packageFiles=len(files(new)),packageByteEquality=True,sourceHashVerification=True,independentSQL=True,modelFit=False,offline=True)
(dest/'reproduction.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
PY
