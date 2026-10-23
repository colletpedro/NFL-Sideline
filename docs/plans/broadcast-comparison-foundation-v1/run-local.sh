#!/bin/sh
set -eu
cd "$(dirname "$0")/../../.."
export PYTHONPATH="$PWD/etl-pipeline/src"
export PYTHONDONTWRITEBYTECODE=1
exec '/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -B -m nfl_sideline_etl.comparison_foundation serve --config "$PWD/docs/plans/broadcast-comparison-foundation-v1/config.json"
