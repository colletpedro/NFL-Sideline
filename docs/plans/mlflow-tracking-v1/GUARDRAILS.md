# Proteções do plano MLflow

Regras obrigatórias para qualquer pessoa ou agente que trabalhe no plano. Se uma tarefa parecer exigir quebrar
uma delas, pare e registre a dúvida em [DECISIONS.md](DECISIONS.md) em vez de contornar.

## Caminhos

| Nome | Caminho |
|---|---|
| Worktree (W) | `/Users/pedrocollet/Downloads/NFL Sideline/.claude/worktrees/mlflow-tracking-v1`, branch `codex/mlflow-tracking-v1`, base `ed2a008` |
| Checkout principal (M) | `/Users/pedrocollet/Downloads/NFL Sideline` (branch de outro trabalho; não trocar) |
| Stores científicos (S) | `M/editorial/local-artifacts/qb-*` |
| Store do MLflow | `NFL_MLFLOW_HOME`, padrão `M/editorial/local-artifacts/mlflow/` (resolvido pelo diretório comum do Git, nunca fixo no código) |

O código resolve M a partir de `git rev-parse --git-common-dir` (pai do `.git` comum) e aceita variável de
ambiente ou argumento de CLI para todo caminho. Nenhum caminho absoluto novo fica fixo no código.

## Somente leitura

- Todos os stores `S/qb-*`: o importador só lê. Nunca criar, renomear ou apagar nada lá dentro; nem arquivo
  temporário, nem lock, nem `__pycache__`.
- Código e documentos congelados por hash (qualquer edição quebra `verified_freeze`, `validate_bundle` ou a
  reprodução byte a byte):
  `research/qb_interception_risk/`, `research/qb_risk_temporal_v2/`, `research/qb_expected_interceptions/`,
  `research/qb_risk_lab/`, `research/qb_risk_outcomes_lab/`, `research/qb_progression_lab/`,
  `research/qb_structure_production/`, `docs/plans/qb-*/`.
- Fora do escopo: `etl-pipeline/`, `core-api/`, `supabase/`, `web-ui/public/data/` (snapshot público).

Importar módulos congelados é permitido (o `__pycache__` gerado na worktree é ignorado pelo Git e não muda os
hashes dos `.py`). Copiar lógica deles só quando o import for inviável, com teste de igualdade contra o original.

## Escrita permitida

| Fase | Caminhos |
|---|---|
| Todas | `research/mlflow_tracking/**`, `docs/plans/mlflow-tracking-v1/**`, `.claude/agents/**`, `docs/adr/011-*.md` |
| 1 | `.gitignore` (entradas novas apenas) |
| 5 | `web-ui/broadcast-journey/risk-outcomes/**` (inclui `provenance.json` gerado), `web-ui/build/risk-outcomes*.ts` e os testes correspondentes, somente o necessário para ler a proveniência |
| 6 | `.github/workflows/research-ci.yml` (novo), linha nova na §11 do `Spec.md` |

Testes escrevem só em `tmp_path`. Saídas de verificação vão para o scratchpad da sessão, nunca para o repositório.

## Outras regras

- Sem pickle: nenhum modelo registrado pode conter `.pkl`/cloudpickle. Usar pyfunc *models from code*.
- Rede: só `pip install` do PyPI para `research/mlflow_tracking/.venv` e, a partir da Fase 5, `npm ci` (lockfile
  existente, sem atualizar dependências) em `W/web-ui` com Node 24 (`/opt/homebrew/opt/node@24/bin`, o mesmo dos
  scripts do laboratório). Nenhuma outra chamada de rede; o importador e os testes rodam offline.
- `mlflow ui`/`mlflow server` só em `127.0.0.1`. Nunca publicar o servidor nem o store.
- Nada de `git commit`, `push`, `checkout`, `reset`, `stash`, `rebase` por agentes. Commits só pelo dono do projeto.
- Não abrir `.env` nem imprimir segredos.
- Dados FTN (CC BY-SA 4.0): o CI usa só dados sintéticos e os stores não são publicados. Evidências já versionadas
  podem ir ao GitHub com a atribuição "FTN Data via nflverse, CC BY-SA 4.0" (D13).
- Arquivos e hashes dos stores são a fonte de verdade. Se o MLflow divergir de um arquivo, o MLflow está errado.
