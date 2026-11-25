# Cartão do modelo `ep`

## Objetivo

Estimar, para cada jogada de ataque (1ª a 4ª descida), a probabilidade de cada um dos 7 desfechos do próximo placar da metade (TD, FG, safety do time com a posse; os três do adversário; nenhum) e o Expected Points (EP) = soma de probabilidade × pontos (+7, +3, +2, -7, -3, -2, 0). É a base de WP, 4º down e PROE no hub; não prevê o vencedor.

## Dados

- data_id: `8631a979c1a1abf07bb0d44326046eaaa78a433a608506d8ae131cc2ec970246`
- Alvo: `next_score_type`

## Tarefa

- Tipo: multiclass (classes: TD, FG, SAFETY, OPP_TD, OPP_FG, OPP_SAFETY, NO_SCORE)
- Métrica primária: `log_loss` (menor é melhor)
- Métricas: `log_loss`, `brier`

## Splits

| split | treino até (season, week) | teste |
|---|---|---|
| s2018 | (2017, 99), desde 2011 | [2018] (temporadas) |
| s2019 | (2018, 99), desde 2011 | [2019] (temporadas) |
| s2020 | (2019, 99), desde 2011 | [2020] (temporadas) |
| s2021 | (2020, 99), desde 2011 | [2021] (temporadas) |
| s2022 | (2021, 99), desde 2011 | [2022] (temporadas) |
| s2023 | (2022, 99), desde 2011 | [2023] (temporadas) |
| s2024 | (2023, 99), desde 2011 | [2024] (temporadas) |
| s2025 | (2024, 99), desde 2011 | [2025] (temporadas) |
| s2026 | (2025, 99), desde 2011 | [2026] (temporadas) |

Execuções filhas registradas: 72. Métricas agregadas são *pooled*: previsões de todos os splits concatenadas e a métrica calculada uma vez.

## Resultados (pooled)

| modelo | papel | n | log_loss | brier | ep_bias | ep_mae | ep_rmse |
|---|---|---|---|---|---|---|---|
| `freq` | baseline | 350829 | 1.52332 | 0.75518 | 0.19483 | 4.13513 | 4.87342 |
| `freq_field_down` | baseline | 350829 | 1.42683 | 0.71475 | 0.08825 | 3.73473 | 4.56800 |
| `nflverse` | reference (fora da regra) | 350829 | 1.26825 | 0.65590 | -0.01201 | 3.64735 | 4.53879 |
| `logit_basic` | candidate | 350829 | 1.43338 | 0.71774 | 0.07305 | 3.71315 | 4.56502 |
| `logit_hinge` | candidate | 350829 | 1.28304 | 0.66354 | 0.07899 | 3.66785 | 4.54830 |
| `logit_hinge_hl2` | candidate | 350829 | 1.28279 | 0.66312 | 0.03046 | 3.66141 | 4.54787 |
| `logit_hinge_hl4` **(selecionado)** | candidate | 350829 | 1.28267 | 0.66322 | 0.04854 | 3.66371 | 4.54781 |
| `logit_state` | candidate | 350829 | 1.30015 | 0.67136 | 0.07139 | 3.66351 | 4.55777 |

## Regra de seleção e resultado

- Regra (fixada antes do backtest): min pooled log_loss entre candidatos; precisa ser melhor que o melhor baseline por mais de 0.
- Modelo selecionado: `logit_hinge_hl4`
- Bate os baselines: sim

## Versões

- git_commit: `6825626816941f472ea753a80d56da23ed483103` (git_dirty: true)
- harness_version: `0.2.0`
- model_code_sha256: `d5234ce7974e3c1fb4e645316ed319798d23d0ad14499daec8676ddad32a7f6a`
- config_sha256: `5fa83ad4df606a8e4cec31938fa206ebc0787b41cf06a9b283fe39f4e7c08e07`
- seed: 0
- Execução pai MLflow: `af769b3303034ae997b4f3074b042643`

## Log-loss por temporada de teste

| split | `logit_hinge_hl4` | `freq_field_down` | `nflverse` |
|---|---|---|---|
| s2018 | 1.26685 | 1.42215 | 1.24126 |
| s2019 | 1.29464 | 1.44466 | 1.27189 |
| s2020 | 1.28567 | 1.43064 | 1.27365 |
| s2021 | 1.26551 | 1.41216 | 1.25438 |
| s2022 | 1.29713 | 1.42933 | 1.28531 |
| s2023 | 1.28457 | 1.43564 | 1.27464 |
| s2024 | 1.29770 | 1.42829 | 1.28651 |
| s2025 | 1.27619 | 1.42134 | 1.26584 |
| s2026 | 1.27037 | 1.41123 | 1.25357 |

## Calibração do EP por decis (`logit_hinge_hl4`, pooled)

| decil | n | EP previsto (média) | pontos reais (média) | diferença |
|---|---|---|---|---|
| 1 | 35083 | -0.914 | -0.790 | +0.125 |
| 2 | 35083 | 0.219 | 0.192 | -0.027 |
| 3 | 35083 | 0.708 | 0.768 | +0.060 |
| 4 | 35083 | 1.121 | 1.219 | +0.098 |
| 5 | 35082 | 1.546 | 1.541 | -0.005 |
| 6 | 35083 | 2.030 | 2.073 | +0.044 |
| 7 | 35083 | 2.570 | 2.642 | +0.071 |
| 8 | 35083 | 3.181 | 3.206 | +0.025 |
| 9 | 35083 | 3.967 | 4.042 | +0.074 |
| 10 | 35083 | 5.154 | 5.174 | +0.020 |

## Viés do EP (média real - previsto; mais perto de zero é melhor)

| modelo | log_loss pooled | brier pooled | ep_mae pooled | ep_bias pooled |
|---|---|---|---|---|
| `logit_hinge` | 1.28304 | 0.66354 | 3.66785 | +0.0790 |
| `logit_hinge_hl2` | 1.28279 | 0.66312 | 3.66141 | +0.0305 |
| `logit_hinge_hl4` | 1.28267 | 0.66322 | 3.66371 | +0.0485 |

## Viés do EP por temporada de teste

| split | `logit_hinge` | `logit_hinge_hl2` | `logit_hinge_hl4` |
|---|---|---|---|
| s2018 | +0.0867 | +0.0570 | +0.0700 |
| s2019 | +0.0214 | -0.0150 | +0.0017 |
| s2020 | +0.1857 | +0.1533 | +0.1659 |
| s2021 | +0.0962 | +0.0365 | +0.0631 |
| s2022 | +0.1085 | +0.0474 | +0.0716 |
| s2023 | +0.0241 | -0.0435 | -0.0179 |
| s2024 | +0.0369 | -0.0161 | +0.0008 |
| s2025 | +0.0624 | +0.0153 | +0.0272 |
| s2026 | +0.1002 | +0.0537 | +0.0653 |

## Registro

- `hub-ep@champion` = versão 4 (params_sha256 `48ca751d1b6a8936475ee01fa42786bdee9e3605001c7741e854293e0d0e2d33`)

## Limitações

- A referência `nflverse` foi treinada com dados que incluem as temporadas de teste (inclusive jogadas futuras ao split), portanto é OTIMISTA: serve de teto de comparação, não de adversário justo. Ela está fora da regra de seleção.
- O backtest é walk-forward por temporada (treino 2011..s-1, teste s, de 2018 até a última temporada); 2026 está incompleta (até a última semana adquirida). As métricas são pooled sobre todos os testes.
- O alvo é o próximo evento de pontuação na MESMA metade (prorrogação = metade 3); PAT e conversão de 2 pts não são eventos. Fim de metade sem pontuação = NO_SCORE.
- Entram só jogadas `ep_eligible` (down 1-4, sem kickoff, PAT nem 2 pts). Linhas inválidas são excluídas, não imputadas, para TODOS os modelos: 1 de 633230 (nulo em coluna bruta: 0; sem alvo: 0; probabilidades do nflverse nulas ou zero: 1).
- Os modelos usam só situação de jogo (campo, descida, distância, tempo, timeouts, mando, prorrogação, teto fechado); não conhecem placar, força dos times nem clima. EP condicional ao placar fica para o WP.
- As previsões em lote (`predict ep`) usam o champion ajustado com TODAS as jogadas: são dentro da amostra. Para avaliação use o backtest.
- Baselines com suavização de Laplace (+1 por classe) para evitar probabilidade zero no log-loss.
- Deriva temporal: a pontuação média por jogada subiu de ~1,58 (2011) para ~2,10 (2026). O `logit_hinge` sem pesos tem viés pooled +0.079 (o EP fica abaixo do real); o selecionado (`logit_hinge_hl4`) tem +0.049, com candidatos de ponderação por recência (meia-vida 2 e 4 temporadas) na disputa. O viés é métrica reportada, fora da regra de seleção.
- A referência `nflverse` pode incluir as temporadas de teste no seu treino (a versão do modelo nflverse não está fixada), então pode haver vazamento a favor dela, em grau desconhecido.
- Há uma descontinuidade de cerca de 0,3 ponto no EP na fronteira goal-to-go (1ª&gol na 10 vs 1ª&10 na 11), efeito da variável `goal_to_go` e do encaixe linear por partes; não é suavizada.
