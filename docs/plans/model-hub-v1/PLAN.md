# Plano: hub de modelos de ML do NFL Sideline (v1, fundação)

Revisão 1 — 24/11/2026. Status: H0–H5 concluídas (ver CHECKPOINTS); próximo plano: publicação e novos modelos. Plano vivo: mudanças de rumo entram em [DECISIONS.md](DECISIONS.md) e a evidência de
cada fase em [CHECKPOINTS.md](CHECKPOINTS.md). Proteções em [GUARDRAILS.md](GUARDRAILS.md).
Decisão de arquitetura: [ADR-012](../../adr/012-model-hub-foundation.md).

## Objetivo

Transformar o NFL Sideline num **hub de modelos**: vários modelos de ML sobre os dados do nflverse, todos
construídos, avaliados, registrados e (mais tarde) publicados pelo mesmo caminho. É também um portfólio de
ML engineering, então o sistema importa tanto quanto cada modelo.

```
nflverse (nflreadpy) ──acquire──▶ cache bruto do hub (Parquet + manifesto com hashes)
   ──build──▶ feature store versionada (plays, games, team_game, team_asof)
   ──backtest──▶ execuções no MLflow (pai + uma filha por dobra, sempre contra baselines)
   ──register──▶ Model Registry (alias champion, pyfunc em código, sem pickle)
   ──predict──▶ previsões em lote  ──(fase futura)──▶ snapshot público + página de modelos
```

## Escopo desta revisão

Entra: aquisição própria, feature store, harness de backtest temporal, convenção de MLflow nativo, cartão de
modelo, primeiro modelo (Expected Points), CI sintético.

Fica para o próximo plano (registrado aqui para não se perder): publicação no site (snapshot `schemaVersion`
novo + página "Modelos"), win probability pré-jogo, ratings de times, WP ao vivo, 4º down, PROE, clusters de
estilo, família "over expected" de jogadores, monitoramento semanal.

## Convenções

- Pacote novo `research/model_hub/` (módulos planos, como `research/mlflow_tracking/`), venv próprio
  `research/model_hub/.venv`, Python 3.11.
- Dependências: as do lock do MLflow + `nflreadpy==0.1.5` e `polars==1.44.1` (mesmas da ETL). Nada de
  xgboost/lightgbm nesta revisão: scikit-learn basta e não exige `libomp`.
- Home dos dados do hub: `NFL_HUB_HOME`, padrão `<checkout principal>/editorial/local-artifacts/model-hub/`
  (fora do Git). MLflow: o mesmo home do plano MLflow (`NFL_MLFLOW_HOME`), experimentos com prefixo `hub-`.
- Toda saída é determinística a partir de (manifesto de aquisição, código, seed) e carrega hashes.
- CLI única: `research/model_hub/cli.py {acquire,build,backtest,register,predict,card,verify}`.

## Fases

| Fase | Entrega | Pronto quando |
|---|---|---|
| H0. Plano | Este plano, GUARDRAILS, DECISIONS, CHECKPOINTS, ADR-012, agentes `hub-*` | Documentos no branch `codex/model-hub-v1` |
| H1. Aquisição | `acquire.py`: baixa PBP e schedules de 2011 até a temporada corrente para `HUB/raw/{pbp,schedules}/season=YYYY/`, grava em arquivo temporário e troca atomicamente, escreve `HUB/acquisitions/<id>.json` (sha256, linhas, colunas, nflreadpy, data máxima de jogo) e `HUB/acquisitions/current.json` | Aquisição real concluída com 2026 até a última semana jogada; segunda execução sem `--refresh` não baixa nada; testes offline com nflreadpy simulado |
| H2. Feature store | `features.py`: a partir de um manifesto de aquisição constrói `HUB/features/<build_id>/` com `plays` (jogadas padronizadas + alvos), `games` (calendário, mercado, resultado), `team_game` (agregados por time e jogo), `team_asof` (features de cada time antes de cada jogo, só com jogos anteriores) e `manifest.json` | Build reprodutível byte a byte; teste de vazamento: alterar um jogo futuro não muda nenhuma linha `team_asof` anterior; alvo `next_score` conferido em jogadas reais |
| H3. Harness | `backtest.py`, `metrics.py`, `hubtrack.py`, `card.py`: especificação de modelo como interface (`fit`, `predict`, `params`), splits walk-forward declarados como dados, execução pai/filhas no MLflow com tags obrigatórias, comparação obrigatória contra baselines, cartão de modelo em Markdown gerado do MLflow | Backtest sintético roda de ponta a ponta; reexecução idêntica dá as mesmas métricas; split que vaza é recusado por teste |
| H4. Expected Points v1 | `models/ep.py`: alvo = próximo evento de pontuação na mesma metade, da perspectiva do time com a posse (7 classes); candidatos logísticos multinomiais com features de campo/tempo/descida; baselines = frequência por faixa de campo e o modelo do nflverse (referência, treinado com dados que incluem o teste); backtest por temporada 2018–2025 + 2026 até agora; registro `hub-ep` com alias `champion` | Backtest completo no MLflow; candidato escolhido por regra fixada antes; modelo carregável por pyfunc; cartão gerado |
| H5. Fechamento | Job `model-hub` no `research-ci.yml`, README, verificação e revisão adversarial | Testes sintéticos verdes, revisão sem achados abertos, CHECKPOINTS atualizado |

## Decisões de desenho (resumo; detalhes em DECISIONS.md)

- **Aquisição própria** em vez da ETL: o raw da ETL só tem 2023, 2025 e 2026 semanas 1–2, e a ETL está fora
  do escopo. O hub baixa do nflverse com o mesmo nflreadpy, mas para o seu próprio cache.
- **2011 em diante**: regra de kickoff atual desde 2011; temporadas antigas mudariam a distribuição.
- **Splits por tempo, sempre**: treino só com temporadas/semanas anteriores à de teste. Nada de k-fold aleatório.
- **Baseline obrigatório**: nenhum modelo vai para o registry sem bater, no backtest, um baseline simples
  registrado no mesmo experimento.
- **Sem pickle**: modelos persistem como parâmetros em JSON + pyfunc definido em código, como no plano MLflow.
  Modelos de árvore exigiriam outro formato; se um dia vencerem, a escolha vai para DECISIONS.
- **Regra de seleção fixada antes do backtest** e gravada como tag/parâmetro do pai.

## Riscos

- Volume: ~16 temporadas × ~48 mil jogadas. Cabe em memória (polars), mas testes usam dados sintéticos.
- O nflverse corrige dados retroativamente: por isso cada aquisição tem manifesto e o build referencia um.
- O modelo do nflverse como referência é otimista (viu os dados de teste); o cartão diz isso explicitamente.
