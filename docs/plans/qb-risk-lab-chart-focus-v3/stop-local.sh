#!/bin/sh
# Refuse another process, checkout or port. Never stop the approved18111 server.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
PID=$(lsof -t -a -iTCP:18124 -sTCP:LISTEN || true)
if [ -z "$PID" ]; then echo 'No listener on18124'; exit 0; fi
COMMAND=$(ps -p "$PID" -o command=)
CWD=$(lsof -a -p "$PID" -d cwd -Fn | sed -n 's/^n//p')
case "$COMMAND" in *'web-ui/scripts/risk-lab-dev.mjs') ;; *) echo 'Refused: listener is not the lab script' >&2; exit 2;; esac
if [ "$CWD" != "$ROOT" ]; then echo 'Refused: listener belongs to another checkout' >&2; exit 2; fi
kill -TERM "$PID"
echo "Stopped only lab PID $PID on18124"
