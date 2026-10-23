#!/bin/zsh
set -eu
NFL_EXPLORER_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$NFL_EXPLORER_ROOT"
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export NFL_OBSERVATION_CONFIG="$NFL_EXPLORER_ROOT/docs/plans/broadcast-live-hub-v1/lab-config.json"
export NFL_SITUATIONAL_CONFIG="$NFL_EXPLORER_ROOT/docs/plans/broadcast-situational-w12-v1/situational-config.json"
export NFL_LOCAL_JOURNEY_PORT=18100
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
exec npm --prefix web-ui run journey:dev
