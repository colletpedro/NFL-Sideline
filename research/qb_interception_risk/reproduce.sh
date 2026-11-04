#!/bin/sh
set -eu
if [ "$#" -ne 3 ]; then
  echo 'Usage: reproduce.sh SOURCE_STORE PRETEST_DEVELOPMENT NEW_OUTPUT' >&2
  exit 2
fi
RESEARCH_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
QB_RESEARCH_PYTHON=${QB_RESEARCH_PYTHON:-"$RESEARCH_ROOT/.venv/bin/python"}
exec "$QB_RESEARCH_PYTHON" -W error::RuntimeWarning "$RESEARCH_ROOT/offline.py" reproduce --store "$1" --development "$2" --out "$3"
