# Base comparável · NYJ × TEN W1

Entrega técnica privada, sem interface nova. [Plano prévio](PLAN.md), [pedido nominal](request.json), [política e matriz](POLICY.md), [permissões concretas](permissions.json), [contrato](CONTRACT.md), [decisões para a página](PILOT-DECISIONS.md), [relatório](REPORT.md) e [reconciliação independente](reconciliation.json).

Base confirmada limpa em `d7e8aa35c7ea6605fd443992668b2b1d2c8fe7d2`. Worktree gerenciada `/Users/pedrocollet/.codex/worktrees/broadcast-comparison-foundation-v1/NFL Sideline`, branch `codex/broadcast-comparison-foundation-v1`. Plano/pedido/política commitados em `312d891`, definições completas em `8811467`, antes da geração final. HEAD final é informado no chat e verificável por git.

## Artefatos duráveis

Raiz física nova fora das worktrees:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/`

- Operacional: `bundle-reconciled/`.
- Recuperação física verificada: `verified-copy/`.
- Reprodução integral verificada: `reproduced-bundle/`.
- `bundle/` conserva a primeira geração interna, sem config operacional; não é fallback nem substitui o pacote final.

Os três pacotes finais têm os mesmos 18 arquivos físicos (17 entradas no manifest, mais COMPLETED.json) e os mesmos bytes. Pin:

`sha256:b10a2028f26d6acc229f80bbd27269016dd2e6b2e4b432a6d8a9109f643e5ee4`

As cópias completas de situational-v1 e das 588 observações estão em `sources/` dentro de cada pacote. A configuração nova não depende da localização antiga do bundle de 588 observações em worktree. O reader da recuperação passou em processo novo com principal, recuperações originais e bundles antigos bloqueados. [Prova](checks/copy.json), [reprodução](checks/reproduction.log) e [verificação das fontes](source-verification.json). Duas cópias no mesmo disco não demonstram proteção contra perda do disco. Nenhuma raiz anterior foi movida, alterada ou renomeada.

## HTTP próprio

Servidor **PID 95101**, somente **127.0.0.1:18101**, strictPort. Endpoint separado `GET /__comparison/`, exige `X-Local-Comparison: 1`. [Config explícita](config.json). O corpo corresponde byte a byte a `bundle-reconciled/comparison.json`, sem envelope ou seleção por URL. Não há página nova nesta porta.

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-comparison-foundation-v1/NFL Sideline'
# Instância já ativa: não iniciar outra na mesma porta.
./docs/plans/broadcast-comparison-foundation-v1/run-local.sh
# O script exec usa Python existente, não instala nem carrega .env.
curl --fail --header 'X-Local-Comparison: 1' http://127.0.0.1:18101/__comparison/
# Encerramento direcionado: conferir o listener antes de TERM.
lsof -nP -a -p 95101 -iTCP:18101 -sTCP:LISTEN && kill -TERM 95101
```

Ctrl+C encerra uma instância iniciada no terminal. Nenhum processo foi encerrado para liberar porta. Explorador **18100/PID74464**, referência **18099/PID64333** e situacional **18098/PID49375** permanecem preservados. Log próprio: `server.log` na raiz durável, fora do pacote imutável. Outra fonte exige config nova explícita com caminho e pin; não há fallback silencioso.

## Leitura, reprodução e recuperação

```sh
export NFL_COMPARISON_PY='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export PYTHONPATH="$PWD/etl-pipeline/src"
export PYTHONDONTWRITEBYTECODE=1
export NFL_COMPARISON_ART='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1'
"$NFL_COMPARISON_PY" -B -m nfl_sideline_etl.comparison_foundation validate --bundle "$NFL_COMPARISON_ART/bundle-reconciled" --expected-pin 'sha256:b10a2028f26d6acc229f80bbd27269016dd2e6b2e4b432a6d8a9109f643e5ee4'
"$NFL_COMPARISON_PY" -B -m nfl_sideline_etl.comparison_foundation validate --bundle "$NFL_COMPARISON_ART/verified-copy"
# Escolher destino ainda inexistente; nunca sobrescreve.
"$NFL_COMPARISON_PY" -B -m nfl_sideline_etl.comparison_foundation reproduce --bundle "$NFL_COMPARISON_ART/verified-copy" --output "$NFL_COMPARISON_ART/reproduction-review-new"
"$NFL_COMPARISON_PY" -B docs/plans/broadcast-comparison-foundation-v1/reconcile.py --bundle "$NFL_COMPARISON_ART/verified-copy" --output /private/tmp/comparison-reconciliation-review.json
```

Para gerar novamente desde as fontes históricas, em destino novo:

```sh
"$NFL_COMPARISON_PY" -B -m nfl_sideline_etl.comparison_foundation generate \
  --situational '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled' \
  --observations '/Users/pedrocollet/.codex/worktrees/broadcast-w12-expansion-v1/NFL Sideline/editorial/local-artifacts/broadcast-w12-expansion-v1/20261022-v1/bundle' \
  --recovery '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery/20261019T024130Z-50e03b27' \
  --backup '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/20261019T024130Z-50e03b27' \
  --request docs/plans/broadcast-comparison-foundation-v1/request.json \
  --policy docs/plans/broadcast-comparison-foundation-v1/POLICY.md \
  --definitions docs/plans/broadcast-comparison-foundation-v1/DEFINITIONS.md \
  --output "$NFL_COMPARISON_ART/regeneration-review-new"
```

Esse caminho executa novamente os readers integrais das duas recuperações, a comparação de seus 162 arquivos e os readers dos dois bundles. Para a próxima sessão, `reproduce` é suficiente e usa apenas o pacote durável; nenhum acesso à worktree antiga é necessário. Request e política são nominais, sem latest ou escolha incidental.

## Reproduzir checks

```sh
export NFL_COMPARISON_QA_BUNDLE="$NFL_COMPARISON_ART/bundle-reconciled"
"$NFL_COMPARISON_PY" -B -m pytest -p no:cacheprovider -q etl-pipeline
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
"$NFL_COMPARISON_PY" -B docs/plans/broadcast-comparison-foundation-v1/verify_http.py docs/plans/broadcast-comparison-foundation-v1/config.json /private/tmp/comparison-http-review.json
"$NFL_COMPARISON_PY" -B docs/plans/broadcast-comparison-foundation-v1/verify_isolation.py
git diff --check d7e8aa35c7ea6605fd443992668b2b1d2c8fe7d2
git log --oneline d7e8aa35c7ea6605fd443992668b2b1d2c8fe7d2..HEAD
git rev-parse HEAD
git status --short
```

608 testes Python completos passaram; depois dos ajustes finais de definição/validação, os 26 testes pertinentes passaram novamente com o pacote final. 281 frontend, cinco `it.fails` legados preservados, lint e quatro builds passaram. Sem a variável QA os três ensaios reais novos ficam explicitamente skipped; a entrega os executou habilitados. Não há inspeção visual exigida para interface inalterada. Não foram executados testes Java/banco sem alteração correspondente.

Somente descrição dos registros observados; completude/cobertura/modelo EPA/disponibilidade histórica UNKNOWN. Sem novos dados/semanas, modelos, dependências, motor editorial, Gemini, Spring, Supabase, ETL semanal, snapshots públicos, merge, push, deploy ou promoção de interface.
