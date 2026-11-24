#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
export NFL_GAME_STORY_CONFIG="$ROOT/docs/plans/broadcast-season-timeline-v1/source-config.json"
export NFL_SEASON_ANALYSIS_CONFIG="$ROOT/docs/plans/broadcast-season-timeline-v1/source-season-config.json"
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
cd "$ROOT"
exec node web-ui/scripts/story-dev.mjs
