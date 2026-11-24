#!/bin/sh
set -eu
cd "$(dirname "$0")/../../.."
export NFL_LOCAL_JOURNEY_PORT=18102
export NFL_MATCHUP_CONFIG="$PWD/docs/plans/broadcast-matchup-reading-v1/source-config.json"
export NFL_OBSERVATION_CONFIG="$PWD/docs/plans/broadcast-matchup-reading-v1/observations-config.json"
export NFL_SITUATIONAL_CONFIG="$PWD/docs/plans/broadcast-situational-w12-v1/situational-config.json"
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
cd web-ui
exec node scripts/matchup-dev.mjs
