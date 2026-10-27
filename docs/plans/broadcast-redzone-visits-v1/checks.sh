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
CHECKS=docs/plans/broadcast-redzone-visits-v1/checks
npm --prefix web-ui test > "$CHECKS/frontend-full.log" 2>&1
node web-ui/node_modules/typescript/bin/tsc -p web-ui/tsconfig.season.json > "$CHECKS/typescript.log" 2>&1
node web-ui/node_modules/typescript/bin/tsc -p web-ui/tsconfig.node.json >> "$CHECKS/typescript.log" 2>&1
npm --prefix web-ui run lint > "$CHECKS/lint.log" 2>&1
for entry in curve story season ranking-redzone redzone-epa w12 hub-team reading-polish matchup
 do node web-ui/node_modules/vite/bin/vite.js build --config "web-ui/vite.$entry.config.ts" > "$CHECKS/build-$entry.log" 2>&1
 done
npm --prefix web-ui run build > "$CHECKS/build-public.log" 2>&1
VITE_API_BASE_URL=https://invalid.example VITE_DATA_MODE=api npm --prefix web-ui run build > "$CHECKS/build-public-adverse.log" 2>&1
