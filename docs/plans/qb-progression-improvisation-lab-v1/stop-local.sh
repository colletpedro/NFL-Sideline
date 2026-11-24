#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
PID=$(lsof -tiTCP:18127 -sTCP:LISTEN || true)
if [ -z "$PID" ]; then echo 'Nenhum servidor na porta 18127.'; exit 0; fi
for p in $PID; do
 CMD=$(ps -p "$p" -o command=)
 CWD=$(lsof -a -p "$p" -d cwd -Fn | sed -n 's/^n//p')
 case "$CMD" in *web-ui/scripts/progression-dev.mjs*) ;; *) echo 'Comando diferente; preservado.'; exit 1;; esac
 if [ "$CWD" != "$ROOT" ]; then echo 'Worktree diferente; preservada.'; exit 1; fi
 kill -TERM "$p"
done
