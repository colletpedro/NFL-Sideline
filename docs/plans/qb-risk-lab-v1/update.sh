#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
STORE=${NFL_RISK_LAB_STORE:-'/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-lab-v1'}
exec "$ROOT/research/qb_risk_lab/.venv/bin/python" "$ROOT/research/qb_risk_lab/pipeline.py" --store "$STORE" "$@"
