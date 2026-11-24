# Checkpoints do hub de modelos

## H0 — Plano (24/11/2026)

- Fatos levantados por dois `hub-scout` (Haiku): [facts/etl-data.md](facts/etl-data.md) e
  [facts/conventions.md](facts/conventions.md).
- Achado que mudou o plano: o raw da ETL tem PBP 2026 só até a semana 2 (última data 2026-09-21) e não tem
  temporadas antes de 2023 nem 2024 → aquisição própria (H-D3).
- Todas as colunas do EP existem no PBP (372 colunas), inclusive as 7 probabilidades do modelo do nflverse;
  não existe coluna `next_score*`, o alvo será derivado.

## H1 — Aquisição (24/11/2026)

- `acquire.py` + `cli.py acquire`; 16 temporadas (2011–2026) em 39,7 s; `acquisition_id`
  `2d6be326636857b500f62b79174471e3168d3ca801fd0cb24405931018844bd6`; `raw/` = 215 MB.
- 2026 com PBP nas semanas 1–11 (163 jogos), última `game_date` 2026-11-23.

## H2 — Feature store (24/11/2026)

- `build_id` `d1a6cb7857659ce01bd658a2da530e20c981f2394fc7d3b946121eab88788382` (2,0 s; reuso em 0,6 s).
- Linhas: plays 751.910 (633.230 `ep_eligible`), games 4.368, team_game 8.518, team_asof 8.736.
- Conferência do orquestrador: frequência real de cada `next_score_type` × probabilidade média do nflverse nas
  jogadas elegíveis: TD 0,3454/0,3442; FG 0,2655/0,2715; OPP_TD 0,1475/0,1469; OPP_FG 0,0990/0,0956;
  NO_SCORE 0,1365/0,1366; SAFETY 0,0034/0,0028; OPP_SAFETY 0,0026/0,0023. Pontos médios do alvo crescem de
  −0,71 (90+ jardas) a 5,04 (0–9 jardas), monotônico.

## H3 — Harness (24/11/2026)

- `metrics.py`, `hubtrack.py`, `backtest.py`, `register.py`, `card.py`, `model_code/json_linear_pyfunc.py`.
- Suíte completa: 91 testes, verde em duas execuções seguidas.
- Revisão adversarial H1–H3 em andamento.

## Revisão 1 (24/11/2026) — `hub-reviewer` (Sonnet)

- C1 crítico: siglas históricas (OAK/SD/STL) nos schedules × atuais no PBP → 323 linhas de `team_game` com time
  fora do jogo e 160 com placar invertido. Confirmado pelo orquestrador. Corrigido (H-D9).
- M1 safety em punt com recuo do retornador; M2/M3 cache sobrescrito e manifesto inconsistente (H-D10);
  M4 idempotência sem dados/código; M5 registro sem amarração ao selecionado (H-D11); B1–B5. Todos corrigidos
  com teste. Reconciliação de pontos × placar: 0 divergências em 4.259 jogos.
- Nova aquisição `f39993a2…` (migração para layout por sha), build `e03a2645…`.

## H4 — Expected Points v1 (24/11/2026)

- Backtest real (pai `2e7ac84a2a3b433aa817afc2f224aca0`, 100 s): logit_hinge 1,28304 log loss; nflverse
  (referência) 1,26825; melhor baseline 1,42683. Selecionado `logit_hinge`, `hub-ep` v2 @champion.
- 633.230 previsões em lote; cartão em [cards/ep.md](cards/ep.md).

## Revisão 2 (24/11/2026)

- Sem crítico/alto. Correções da revisão 1 confirmadas com prova; pyfunc × ajuste em memória: diferença 0,0;
  log loss recalculado do zero igual ao MLflow.
- Viés de +0,08 do EP explicado: deriva temporal (alvo médio 1,58 em 2011 → 2,10 em 2026, r = 0,90); sem erro
  de construção (viés em amostra −0,0001).
- M-1 (acquire por subconjunto troca a aquisição atual) e L-1..L-6 em correção.
- CI: job `model-hub` adicionado ao `research-ci.yml`; simulação local com home vazio: 133 passam, 7 `real_data` pulam.

## H5 — Fechamento (24/11/2026)

- M-1 e L-1..L-6 corrigidos. Build final `8631a979…`; pai final `455f23721b304e7980a8c24777333c88`;
  `hub-ep` v3 @champion (`params_sha256` `baed31a3…`); métricas pooled inalteradas (logit_hinge 1,28304;
  nflverse 1,26825; n = 350.829). 633.229 previsões, `in_sample: true` conferido por impressão digital.
- Verificação final do orquestrador: 151 testes verdes; simulação do CI com home vazio 144 passam / 7 pulam;
  nenhum diff em código congelado nem fora do escopo; nenhum pickle em `hub-ep`; raw da ETL intocado;
  home do hub = 467 MB (fora do Git).
