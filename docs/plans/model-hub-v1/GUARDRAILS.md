# Proteções do hub de modelos

Regras obrigatórias para pessoas e agentes. Se uma tarefa parecer exigir quebrar uma delas, pare e registre em
[DECISIONS.md](DECISIONS.md).

## Caminhos

| Nome | Caminho |
|---|---|
| Worktree (W) | `/Users/pedrocollet/Downloads/NFL Sideline/.claude/worktrees/model-hub-v1`, branch `codex/model-hub-v1`, base `a97c1a8` |
| Checkout principal (M) | `/Users/pedrocollet/Downloads/NFL Sideline` (branch de outro trabalho; não trocar) |
| Home do hub (HUB) | `NFL_HUB_HOME`, padrão `M/editorial/local-artifacts/model-hub/` |
| MLflow | `NFL_MLFLOW_HOME`, padrão `M/editorial/local-artifacts/mlflow/` |

M é resolvido por `git rev-parse --git-common-dir`. Nenhum caminho absoluto fica fixo no código.

## Somente leitura

- `M/etl-pipeline/data/`, todos os stores `M/editorial/local-artifacts/qb-*` e qualquer outro diretório de
  `local-artifacts` que não seja `model-hub/` ou `mlflow/`.
- Código congelado: `research/qb_*`, `docs/plans/qb-*`. Também não alterar `research/mlflow_tracking/` nem
  `docs/plans/mlflow-tracking-v1/` (outro plano, já commitado); importar `tracking.py` é permitido.
- Fora do escopo: `etl-pipeline/`, `core-api/`, `supabase/`, `web-ui/`.
- No MLflow, não apagar nem alterar experimentos que não comecem com `hub-`.

## Escrita permitida

`research/model_hub/**`, `docs/plans/model-hub-v1/**`, `docs/adr/012-*.md`, `.claude/agents/hub-*.md`,
`.gitignore` (entradas novas), `.github/workflows/research-ci.yml` (job novo, H5), linha nova na §11 do `Spec.md`,
`HUB/**`, experimentos `hub-*` e modelos `hub-*` no MLflow. Testes escrevem só em `tmp_path`.

## Outras regras

- Rede: `pip install` no `research/model_hub/.venv` e o comando `cli.py acquire` (só nflverse via nflreadpy).
  Todo o resto (build, backtest, testes) roda offline; testes bloqueiam socket.
- Vazamento temporal é defeito crítico. Features de uma jogada ou jogo só usam informação anterior ao instante
  da previsão; splits treinam só com o passado do teste.
- Sem pickle/cloudpickle/joblib em modelos registrados ou artefatos.
- `mlflow ui` só em `127.0.0.1`.
- Agentes não rodam `git commit/push/checkout/reset/stash/rebase`. Commits só pelo orquestrador a pedido do dono.
- Não abrir `.env`. Dados FTN não são usados nesta revisão.
