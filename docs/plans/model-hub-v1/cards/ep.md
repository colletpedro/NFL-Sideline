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

Execuções filhas registradas: 54. Métricas agregadas são *pooled*: previsões de todos os splits concatenadas e a métrica calculada uma vez.

## Resultados (pooled)

| modelo | papel | n | log_loss | brier | ep_mae | ep_rmse |
|---|---|---|---|---|---|---|
| `freq` | baseline | 350829 | 1.52332 | 0.75518 | 4.13513 | 4.87342 |
| `freq_field_down` | baseline | 350829 | 1.42683 | 0.71475 | 3.73473 | 4.56800 |
| `nflverse` | reference (fora da regra) | 350829 | 1.26825 | 0.65590 | 3.64735 | 4.53879 |
| `logit_basic` | candidate | 350829 | 1.43338 | 0.71774 | 3.71315 | 4.56502 |
| `logit_hinge` **(selecionado)** | candidate | 350829 | 1.28304 | 0.66354 | 3.66785 | 4.54830 |
| `logit_state` | candidate | 350829 | 1.30015 | 0.67136 | 3.66351 | 4.55777 |

## Regra de seleção e resultado

- Regra (fixada antes do backtest): min pooled log_loss entre candidatos; precisa ser melhor que o melhor baseline por mais de 0.
- Modelo selecionado: `logit_hinge`
- Bate os baselines: sim

## Versões

- git_commit: `a97c1a89d03120c7ff9287c705078098e3e99486` (git_dirty: true)
- harness_version: `0.2.0`
- model_code_sha256: `487cfbbe45f096ee1b6d9f5d91d9742adbe6ee61d0f8c005a6e4a8631bf731cc`
- config_sha256: `4bf058fb6add2a27506cf28600c27526d7c0199bc6e774d31a53b7bcae996282`
- seed: 0
- Execução pai MLflow: `455f23721b304e7980a8c24777333c88`

## Log-loss por temporada de teste

| split | `logit_hinge` | `freq_field_down` | `nflverse` |
|---|---|---|---|
| s2018 | 1.26699 | 1.42215 | 1.24126 |
| s2019 | 1.29498 | 1.44466 | 1.27189 |
| s2020 | 1.28585 | 1.43064 | 1.27365 |
| s2021 | 1.26721 | 1.41216 | 1.25438 |
| s2022 | 1.29604 | 1.42933 | 1.28531 |
| s2023 | 1.28428 | 1.43564 | 1.27464 |
| s2024 | 1.29827 | 1.42829 | 1.28651 |
| s2025 | 1.27682 | 1.42134 | 1.26584 |
| s2026 | 1.27208 | 1.41123 | 1.25357 |

## Calibração do EP por decis (`logit_hinge`, pooled)

| decil | n | EP previsto (média) | pontos reais (média) | diferença |
|---|---|---|---|---|
| 1 | 35083 | -0.929 | -0.796 | +0.133 |
| 2 | 35082 | 0.190 | 0.207 | +0.017 |
| 3 | 35084 | 0.672 | 0.767 | +0.096 |
| 4 | 35078 | 1.085 | 1.203 | +0.118 |
| 5 | 35087 | 1.509 | 1.559 | +0.050 |
| 6 | 35083 | 1.990 | 2.061 | +0.071 |
| 7 | 35083 | 2.534 | 2.642 | +0.108 |
| 8 | 35083 | 3.153 | 3.210 | +0.056 |
| 9 | 35083 | 3.951 | 4.040 | +0.089 |
| 10 | 35083 | 5.121 | 5.173 | +0.052 |

## Registro

- `hub-ep@champion` = versão 3 (params_sha256 `baed31a30fbc7bf8b2933e35b7e50e9a711b9ee3fa6555b51684de578f4f4d63`)

## Limitações

- A referência `nflverse` foi treinada com dados que incluem as temporadas de teste (inclusive jogadas futuras ao split), portanto é OTIMISTA: serve de teto de comparação, não de adversário justo. Ela está fora da regra de seleção.
- O backtest é walk-forward por temporada (treino 2011..s-1, teste s, de 2018 até a última temporada); 2026 está incompleta (até a última semana adquirida). As métricas são pooled sobre todos os testes.
- O alvo é o próximo evento de pontuação na MESMA metade (prorrogação = metade 3); PAT e conversão de 2 pts não são eventos. Fim de metade sem pontuação = NO_SCORE.
- Entram só jogadas `ep_eligible` (down 1-4, sem kickoff, PAT nem 2 pts). Linhas inválidas são excluídas, não imputadas, para TODOS os modelos: 1 de 633230 (nulo em coluna bruta: 0; sem alvo: 0; probabilidades do nflverse nulas ou zero: 1).
- Os modelos usam só situação de jogo (campo, descida, distância, tempo, timeouts, mando, prorrogação, teto fechado); não conhecem placar, força dos times nem clima. EP condicional ao placar fica para o WP.
- As previsões em lote (`predict ep`) usam o champion ajustado com TODAS as jogadas: são dentro da amostra. Para avaliação use o backtest.
- Baselines com suavização de Laplace (+1 por classe) para evitar probabilidade zero no log-loss.
- Deriva temporal: o EP walk-forward fica cerca de 0,08 ponto ABAIXO do real, porque a pontuação média por jogada subiu de ~1,58 (2011) para ~2,10 (2026) e o treino mistura épocas; a próxima versão deve testar ponderação por recência.
- A referência `nflverse` pode incluir as temporadas de teste no seu treino (a versão do modelo nflverse não está fixada), então pode haver vazamento a favor dela, em grau desconhecido.
- Há uma descontinuidade de cerca de 0,3 ponto no EP na fronteira goal-to-go (1ª&gol na 10 vs 1ª&10 na 11), efeito da variável `goal_to_go` e do encaixe linear por partes; não é suavizada.
