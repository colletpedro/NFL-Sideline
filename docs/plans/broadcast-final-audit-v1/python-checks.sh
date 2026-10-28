#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
cd "$ROOT"
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
export NFL_CURVE_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-score-curve-v2/20261027-v1/bundle'
export NFL_STORY_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-season-timeline-v1/20261027-v1/bundle'
export NFL_SEASON_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-w1-7-v1/20261027-v1/bundle'
export NFL_REDZONE_EPA_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-redzone-epa-v1/20261026-v1/bundle'
export NFL_TEAM_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle'
export NFL_W12_QA_BUNDLE="$NFL_TEAM_QA_BUNDLE/source/matchups"
export NFL_MATCHUP_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled'
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
export NFL_COMPARISON_QA_BUNDLE="$NFL_MATCHUP_QA_BUNDLE"
export PYTHONPATH=etl-pipeline/src
export PYTHONDONTWRITEBYTECODE=1
'/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -B -m pytest etl-pipeline > docs/plans/broadcast-final-audit-v1/checks/python-full-with-fixtures.log 2>&1
