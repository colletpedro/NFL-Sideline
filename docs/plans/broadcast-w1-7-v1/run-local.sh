#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
export NFL_SEASON_ANALYSIS_CONFIG="$ROOT/docs/plans/broadcast-w1-7-v1/source-config.json"
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
cd "$ROOT"
exec node web-ui/scripts/season-dev.mjs
