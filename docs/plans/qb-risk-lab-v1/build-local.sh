#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
export NFL_CURVE_EVENTS_CONFIG="$ROOT/docs/plans/broadcast-score-curve-v2/source-config.json"
export NFL_GAME_STORY_CONFIG="$ROOT/docs/plans/broadcast-score-curve-v2/story-config.json"
export NFL_SEASON_ANALYSIS_CONFIG="$ROOT/docs/plans/broadcast-score-curve-v2/season-config.json"
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
cd "$ROOT/web-ui"
npx --no-install tsc -p tsconfig.journey.json
npx --no-install vite build --config vite.risk-lab.config.ts
