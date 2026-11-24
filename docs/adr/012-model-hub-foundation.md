# ADR-012: fundação do hub de modelos de ML

Status: proposto (24/11/2026). Plano: [docs/plans/model-hub-v1](../plans/model-hub-v1/PLAN.md). Depende do
[ADR-011](011-local-mlflow-tracking.md).

## Contexto

O laboratório de ML tem três experimentos congelados sobre risco de passes de QB, todos indexados no MLflow
local. O objetivo passou a ser um hub com vários modelos sobre times e jogadores, servindo também de portfólio
de ML engineering. O raw da ETL é incompleto para isso (poucas temporadas, 2026 desatualizado) e a ETL alimenta
produção, então não deve ser alterada para pesquisa.

## Decisão

- Pacote `research/model_hub/` com aquisição própria do nflverse para um cache local versionado por manifesto.
- Feature store local derivada de um manifesto, com teste de vazamento temporal.
- Harness único de backtest walk-forward que registra no MLflow de forma nativa (experimentos `hub-*`), sempre
  contra baselines e com regra de seleção fixada antes.
- Modelos registrados como pyfunc definido em código com parâmetros em JSON, sem pickle.
- Publicação no site fica para um ADR próprio (novo `schemaVersion`).

## Consequências

- Produção, ETL, core-api e banco não mudam.
- O cache e a feature store não estão no Git; são reconstruídos por `acquire` + `build`.
- Modelos de árvore ficam de fora até haver um formato de serialização sem pickle aceito.
