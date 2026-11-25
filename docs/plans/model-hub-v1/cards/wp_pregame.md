# Cartão do modelo `wp-pregame`

## Objetivo

Estimar, antes do kickoff, a probabilidade de o MANDANTE vencer cada jogo da NFL (empates fora) a partir só do histórico de resultados (Elo em pontos de margem calculado ANTES de cada jogo), do calendário (campo neutro, descanso, jogo de divisão) e do `team_asof`. Serve de ponto de comparação 'modelo × mercado': o mercado (moneyline de fechamento) é referência, nunca feature (H-D12).

## Dados

- data_id: `8631a979c1a1abf07bb0d44326046eaaa78a433a608506d8ae131cc2ec970246`
- Alvo: `home_win`

## Tarefa

- Tipo: binary
- Métrica primária: `log_loss` (menor é melhor)
- Métricas: `log_loss`, `brier`, `ece`, `auc`

## Splits

Um split por semana (184 no total), de s2018w01 a s2026w11 (temporadas 2018-2026): cada split treina com todos os jogos desde 2011 anteriores à semana testada e testa nessa semana (H-D13). Os splits completos estão em `config.json` no pai do MLflow.

Execuções filhas registradas: 1472. Métricas agregadas são *pooled*: previsões de todos os splits concatenadas e a métrica calculada uma vez.

## Resultados (pooled)

| modelo | papel | n | log_loss | brier | ece | auc | accuracy |
|---|---|---|---|---|---|---|---|
| `coin` | baseline | 2381 | 0.69315 | 0.25000 | 0.04179 | 0.50000 | 0.50000 |
| `home_rate` | baseline | 2381 | 0.69072 | 0.24878 | 0.02281 | 0.49204 | 0.54200 |
| `market` | reference (fora da regra) | 2381 | 0.60888 | 0.21069 | 0.01803 | 0.72479 | 0.66401 |
| `elo_direct` | candidate | 2381 | 0.63574 | 0.22256 | 0.03049 | 0.69051 | 0.64133 |
| `logit_asof` | candidate | 2381 | 0.63497 | 0.22249 | 0.02999 | 0.69090 | 0.63629 |
| `logit_combo` **(selecionado)** | candidate | 2381 | 0.63344 | 0.22160 | 0.03531 | 0.69409 | 0.63419 |
| `logit_elo` | candidate | 2381 | 0.63652 | 0.22273 | 0.03372 | 0.69036 | 0.64049 |
| `logit_elo_ctx` | candidate | 2381 | 0.63610 | 0.22263 | 0.03414 | 0.69032 | 0.63797 |

## Regra de seleção e resultado

- Regra (fixada antes do backtest): min pooled log_loss entre candidatos; precisa ser melhor que o melhor baseline por mais de 0.
- Modelo selecionado: `logit_combo`
- Bate os baselines: sim

## Versões

- git_commit: `6825626816941f472ea753a80d56da23ed483103` (git_dirty: true)
- harness_version: `0.2.0`
- model_code_sha256: `8fd96278cebae7ddf4b0d0873f17e6b1d9c5c93250d4dead9495388c57a65fb8`
- config_sha256: `0a5a85ea612663f22d3645d752677678eb6cdf7eae9cc3d9f54672eaaa35e857`
- seed: 0
- Execução pai MLflow: `7143d28f49a24c4db0337840fd69b5c3`

## Hiperparâmetros fixos

| modelo | papel | parâmetros |
|---|---|---|
| `coin` | baseline | `{"p": 0.5}` |
| `home_rate` | baseline | `{"estimate": "média de home_win nos jogos não neutros do treino", "neutral": 0.5}` |
| `elo_direct` | candidate | `{"elo": {"cap": 28.0, "hfa": 2.0, "k": 0.07, "reversion": 0.3333333333333333}, "hfa": 2.0, "kind": "elo_direct", "sigma": 13.5}` |
| `logit_asof` | candidate | `{"C": 1.0, "elo": {"cap": 28.0, "hfa": 2.0, "k": 0.07, "reversion": 0.3333333333333333}, "features": ["home_field", "asof_off_epa_diff", "asof_def_epa_diff", "asof_point_diff_diff"], "fit_intercept": false, "kind": "logit", "nulls": "linhas de treino com feature nula saem; jogo a prever com feature nula levanta erro", "rest_clip": 7.0, "scaling": "divide pelo desvio-padrão do treino, sem centralizar"}` |
| `logit_combo` | candidate | `{"C": 1.0, "elo": {"cap": 28.0, "hfa": 2.0, "k": 0.07, "reversion": 0.3333333333333333}, "features": ["elo_diff", "home_field", "rest_diff", "div_game", "asof_off_epa_diff", "asof_def_epa_diff", "asof_point_diff_diff"], "fit_intercept": false, "kind": "logit", "nulls": "linhas de treino com feature nula saem; jogo a prever com feature nula levanta erro", "rest_clip": 7.0, "scaling": "divide pelo desvio-padrão do treino, sem centralizar"}` |
| `logit_elo` | candidate | `{"C": 1.0, "elo": {"cap": 28.0, "hfa": 2.0, "k": 0.07, "reversion": 0.3333333333333333}, "features": ["elo_diff", "home_field"], "fit_intercept": false, "kind": "logit", "nulls": "linhas de treino com feature nula saem; jogo a prever com feature nula levanta erro", "rest_clip": 7.0, "scaling": "divide pelo desvio-padrão do treino, sem centralizar"}` |
| `logit_elo_ctx` | candidate | `{"C": 1.0, "elo": {"cap": 28.0, "hfa": 2.0, "k": 0.07, "reversion": 0.3333333333333333}, "features": ["elo_diff", "home_field", "rest_diff", "div_game"], "fit_intercept": false, "kind": "logit", "nulls": "linhas de treino com feature nula saem; jogo a prever com feature nula levanta erro", "rest_clip": 7.0, "scaling": "divide pelo desvio-padrão do treino, sem centralizar"}` |
| `market` | reference | `{"formula": "p = imp(home)/(imp(home)+imp(away)); imp(ml)=100/(ml+100) se ml>0, -ml/(-ml+100) se ml<0", "source": "home_moneyline/away_moneyline de fechamento"}` |

## Log loss, Brier e acerto por temporada de teste

| temporada | n | `logit_combo` log loss | `logit_combo` brier | `logit_combo` acerto | `home_rate` log loss | `home_rate` brier | `home_rate` acerto | `market` log loss | `market` brier | `market` acerto |
|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 265 | 0.6137 | 0.2135 | 0.642 | 0.6739 | 0.2404 | 0.600 | 0.6135 | 0.2124 | 0.660 |
| 2019 | 266 | 0.6424 | 0.2255 | 0.635 | 0.6981 | 0.2524 | 0.523 | 0.6163 | 0.2141 | 0.643 |
| 2020 | 268 | 0.6264 | 0.2175 | 0.657 | 0.7021 | 0.2544 | 0.504 | 0.5900 | 0.2019 | 0.675 |
| 2021 | 284 | 0.6598 | 0.2327 | 0.602 | 0.6978 | 0.2523 | 0.514 | 0.6232 | 0.2177 | 0.623 |
| 2022 | 282 | 0.6299 | 0.2200 | 0.652 | 0.6826 | 0.2448 | 0.573 | 0.6050 | 0.2093 | 0.658 |
| 2023 | 285 | 0.6502 | 0.2293 | 0.614 | 0.6847 | 0.2458 | 0.565 | 0.6270 | 0.2186 | 0.674 |
| 2024 | 285 | 0.6188 | 0.2147 | 0.667 | 0.6922 | 0.2495 | 0.535 | 0.5892 | 0.2010 | 0.707 |
| 2025 | 284 | 0.6348 | 0.2227 | 0.606 | 0.6919 | 0.2494 | 0.535 | 0.6070 | 0.2109 | 0.660 |
| 2026 | 162 | 0.6163 | 0.2150 | 0.636 | 0.6948 | 0.2508 | 0.522 | 0.6082 | 0.2099 | 0.682 |

## Calibração por decis de probabilidade prevista: `logit_combo` (pooled, 2018+)

| decil | n | previsto médio | observado (mandante vence) | observado − previsto |
|---|---|---|---|---|
| 1 | 238 | 0.256 | 0.290 | +0.034 |
| 2 | 238 | 0.374 | 0.332 | -0.042 |
| 3 | 238 | 0.443 | 0.420 | -0.023 |
| 4 | 238 | 0.499 | 0.458 | -0.041 |
| 5 | 238 | 0.554 | 0.492 | -0.063 |
| 6 | 238 | 0.599 | 0.550 | -0.049 |
| 7 | 238 | 0.646 | 0.630 | -0.016 |
| 8 | 238 | 0.698 | 0.676 | -0.021 |
| 9 | 238 | 0.755 | 0.735 | -0.019 |
| 10 | 239 | 0.840 | 0.833 | -0.007 |

## Calibração por decis de probabilidade prevista: `market` (pooled, 2018+)

| decil | n | previsto médio | observado (mandante vence) | observado − previsto |
|---|---|---|---|---|
| 1 | 237 | 0.228 | 0.207 | -0.021 |
| 2 | 238 | 0.337 | 0.307 | -0.030 |
| 3 | 239 | 0.406 | 0.372 | -0.033 |
| 4 | 237 | 0.473 | 0.485 | +0.012 |
| 5 | 239 | 0.548 | 0.540 | -0.008 |
| 6 | 237 | 0.598 | 0.570 | -0.028 |
| 7 | 240 | 0.644 | 0.625 | -0.019 |
| 8 | 236 | 0.700 | 0.699 | -0.000 |
| 9 | 238 | 0.757 | 0.752 | -0.005 |
| 10 | 240 | 0.836 | 0.858 | +0.022 |

## Coeficientes do selecionado (`hub-wp-pregame@5`, ajustado em todos os jogos completos)

Log-odds de o mandante vencer, sem intercepto. `por unidade` está na unidade original da feature (pontos de Elo, dias, 0/1, EPA); `padronizado` = por desvio-padrão do treino.

| feature | por unidade | desvio-padrão | padronizado |
|---|---|---|---|
| `elo_diff` | +0.0978 | 5.3241 | +0.5205 |
| `home_field` | +0.2759 | 0.1379 | +0.0380 |
| `rest_diff` | +0.0286 | 2.5147 | +0.0720 |
| `div_game` | -0.0737 | 0.4783 | -0.0353 |
| `asof_off_epa_diff` | +1.7566 | 0.1141 | +0.2005 |
| `asof_def_epa_diff` | -0.2480 | 0.0955 | -0.0237 |
| `asof_point_diff_diff` | +0.0093 | 8.6880 | +0.0806 |

Jogos no ajuste: 4229 (descartados por feature nula: 16).

## Registro

- `hub-wp-pregame@champion` = versão 5 (params_sha256 `8acd74b5017daaa8496e623d9ab10ad5892ad00219f2c91f22f236068bf50db5`)

## Próxima semana

Modelo `hub-wp-pregame@5` (probabilidade de o MANDANTE vencer, só com informação anterior ao jogo, sem lesões) × mercado (probabilidade justa do moneyline de fechamento; "—" quando o moneyline ainda não saiu). A diferença é modelo − mercado em pontos percentuais.

| kickoff (UTC) | visitante | mandante | modelo | mercado | diferença |
|---|---|---|---|---|---|
| 2026-11-26 01:00 | GB | LA | 73.0% | 54.9% | +18.1 |
| 2026-11-26 18:00 | CHI | DET | 63.6% | 43.3% | +20.3 |
| 2026-11-26 21:30 | PHI | DAL | 73.5% | 79.1% | -5.6 |
| 2026-11-27 01:20 | KC | BUF | 63.4% | 57.5% | +5.9 |
| 2026-11-27 20:00 | DEN | PIT | 46.2% | 41.6% | +4.6 |
| 2026-11-29 18:00 | ATL | MIN | 65.7% | 74.5% | -8.7 |
| 2026-11-29 18:00 | BAL | HOU | 78.0% | 72.6% | +5.4 |
| 2026-11-29 18:00 | NO | CIN | 81.2% | 82.7% | -1.5 |
| 2026-11-29 18:00 | NYG | IND | 40.8% | 26.7% | +14.1 |
| 2026-11-29 18:00 | NYJ | MIA | 55.3% | 34.5% | +20.7 |
| 2026-11-29 18:00 | TEN | JAX | 89.8% | 88.8% | +1.0 |
| 2026-11-29 21:05 | NE | LAC | 34.4% | 51.4% | -17.0 |
| 2026-11-29 21:25 | SEA | SF | 60.0% | 61.3% | -1.3 |
| 2026-11-29 21:25 | WAS | ARI | 34.9% | 22.9% | +12.0 |
| 2026-11-30 01:20 | LV | CLE | 67.1% | 66.2% | +0.9 |
| 2026-12-01 01:15 | CAR | TB | 62.1% | 58.4% | +3.7 |

## Limitações

- `market` (probabilidade justa do moneyline de FECHAMENTO) é REFERÊNCIA fora da regra: incorpora lesões, clima, escalações e informação que só existe perto do kickoff e que o modelo não vê. O modelo não usa o mercado como feature (H-D12); bater os baselines não é bater o mercado.
- O modelo NÃO vê lesões, quarterback titular, clima, viagem nem troca de elenco: só placares, descanso, divisão e o estado `team_asof` (EPA e saldo de pontos). Por isso diferenças modelo − mercado grandes são, muitas vezes, informação que o mercado tem e o modelo não, não 'valor'.
- Elo calculado online em ordem de kickoff: o rating de cada jogo, inclusive de treino, usa só jogos de kickoff anterior. Jogos da mesma semana já disputados antes (quinta antes de domingo) entram no Elo dos seguintes, como na prática; o ajuste logístico, porém, só usa jogos de semanas anteriores (H-D13). O rating inicial de 2011 é 0 para todos (burn-in nas primeiras temporadas de treino).
- Hiperparâmetros fixos: os do Elo do `hub-ratings` (piloto 2013-2017), C da logística 1,0, σ de 13,5 do `elo_direct`, descanso limitado a ±7 dias. Nada foi ajustado em 2018+; ainda assim piloto e teste vêm da mesma liga.
- Empates fora do alvo (14 de 4259 jogos completos), mas entram no Elo (margem 0). Jogos em campo neutro (82 sem empate, incluindo Super Bowls) sem vantagem de casa; a taxa `home_rate` neles é 0,5.
- A vantagem de casa estimada vem de 2011 em diante e a taxa de vitória do mandante caiu depois de 2018: a tabela de calibração mostra o previsto acima do observado em 9 de 10 decis (taxa real do mandante 54,2% em 2018+ contra previsão média de 56,6%, cerca de +2,5 pp), ou seja, o modelo superestima o mandante de forma global. Os hiperparâmetros e o ajuste não foram corrigidos para isso (nada foi ajustado em 2018+).
- A previsão do modelo para um jogo `out_of_sample` é a da dobra semanal do backtest (treinada só com semanas anteriores). Os demais jogos completos levam o champion ajustado com TODOS os jogos: são DENTRO da amostra e não servem para avaliar. Jogos futuros usam o champion e o Elo atual.
- Calibração e acerto são pooled sobre 2018+ (poucos jogos por temporada: o erro de amostragem do log loss de uma temporada é grande, diferenças de ~0,005 entre modelos não são distinguíveis). Jogos futuros sem moneyline publicado ficam sem `market` e sem diferença.
- A seleção não é estatisticamente significativa: os 5 candidatos ficam a ~0,003 de log loss entre si e, num bootstrap por semana (revisão 4), a vantagem do selecionado sobre `elo_direct` (Elo convertido em probabilidade sem nenhum ajuste) e `logit_asof` tem IC 95% que inclui zero. Na prática, o Elo puro é equivalente.
- `model_code_sha256` deste cartão é o hash do conjunto de códigos do backtest; o do registro do modelo é o hash do arquivo do pyfunc. São grandezas diferentes.
