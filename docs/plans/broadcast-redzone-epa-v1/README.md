# EPA nas jogadas da red zone · W1–2

Entrega local sobre `e5c36cee30813cb882536114f401e5bc34d5c754`, branch `codex/broadcast-redzone-epa-v1`.

- [NE × SEA: EPA da red zone](http://127.0.0.1:18108/?view=matchup-w12&game=2026_01_NE_SEA#mr-redzone-epa)
- [NYJ × TEN: duas médias positivas](http://127.0.0.1:18108/?view=matchup-w12&game=2026_01_NYJ_TEN#mr-redzone-epa)
- [ATL × PIT: ATL sem média](http://127.0.0.1:18108/?view=matchup-w12&game=2026_01_ATL_PIT#mr-redzone-epa)
- [NYJ: agregado W1–2 e adversários](http://127.0.0.1:18108/?view=team-w12&team=NYJ&season=2026&returnWeek=1#team-redzone-epa)
- [Referência 18107](http://127.0.0.1:18107/?view=matchup-w12&game=2026_01_NE_SEA#mr-redzone)

## Operação

Na raiz desta worktree:

```sh
sh docs/plans/broadcast-redzone-epa-v1/run-local.sh
```

Host somente `127.0.0.1`, porta `18108`, `strictPort`, sem proxy/CORS. O script lê as configurações antigas de time/confronto e a nova `source-config.json`; não instala dependências. Node 24 e o ambiente Python existentes são reutilizados. O processo desta entrega está registrado em `/private/tmp/nfl-sideline-redzone-epa-18108.pid`; log em `/private/tmp/nfl-sideline-redzone-epa-18108.log`. Confirme o PID e o listener antes de encerrar; em foreground, use Ctrl+C.

Pacote durável, sem depender de um servidor ou checkout histórico:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-redzone-epa-v1/20261026-v1/bundle`

`verified-copy` é a cópia física conferida. `reproduced-from-copy` foi recalculado a partir dela, com bytes idênticos. O pacote tem 53 arquivos, incluindo fontes originais completas; não regrava o pacote do time/confronto.

Novo pin: `sha256:6e6bffd6d2e8fc1e70e9d47e395f250b8dcf2cbc084bedbf4e4a32fb2ccf8af6`.

```sh
export PYTHONPATH="$PWD/etl-pipeline/src"
export PYTHONDONTWRITEBYTECODE=1
export NFL_REDZONE_EPA_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-redzone-epa-v1/20261026-v1/bundle'
export NFL_TEAM_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle'
export NFL_W12_QA_BUNDLE="$NFL_TEAM_QA_BUNDLE/source/matchups"
export NFL_MATCHUP_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled'
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"

'/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -B -m pytest etl-pipeline/tests/test_redzone_epa.py etl-pipeline/tests/test_matchup_w12.py etl-pipeline/tests/test_team_w12.py -q
npm --prefix web-ui test
npm --prefix web-ui run lint
web-ui/node_modules/.bin/tsc -p web-ui/tsconfig.journey.json
web-ui/node_modules/.bin/tsc -p web-ui/tsconfig.redzone-epa.json
web-ui/node_modules/.bin/vite build --config web-ui/vite.redzone-epa.config.ts
npm --prefix web-ui run build
'/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -B docs/plans/broadcast-redzone-epa-v1/reconcile.py
python3 -B docs/plans/broadcast-redzone-epa-v1/check-http.py
python3 -B docs/plans/broadcast-redzone-epa-v1/verify-isolation.py
```

CLI nova: `python -B -m nfl_sideline_etl.redzone_epa generate --source CAMINHO_ABSOLUTO_PACOTE_CONFRONTOS --output DESTINO_NOVO`; `validate --bundle ... --expected-pin ...`; `reproduce --bundle ... --output DESTINO_NOVO`. Destinos existentes são recusados. A leitura verifica hashes, o pacote original pinado e recalcula a projeção inteira antes de servir.

Consulte [plano](PLAN.md), [relatório e limites](REPORT.md), [reconciliação](checks/reconciliation.json) e [verificação HTTP](checks/http.json). Nenhum estudo humano novo foi realizado.
