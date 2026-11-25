# Cartão do modelo `ratings`

## Objetivo

Estimar a margem do mandante (pontos do mandante menos pontos do visitante) antes de cada jogo a partir só do histórico de resultados (e, em um candidato, do `team_asof`), e dar a cada time um rating em pontos: margem prevista = vantagem de casa × (1 - campo neutro) + rating(mandante) - rating(visitante). Os ratings alimentam o WP pré-jogo (H7) e o ranking de forças; o modelo não usa o mercado.

## Dados

- data_id: `8631a979c1a1abf07bb0d44326046eaaa78a433a608506d8ae131cc2ec970246`
- Alvo: `result`

## Tarefa

- Tipo: regression
- Métrica primária: `rmse` (menor é melhor)
- Métricas: `rmse`, `mae`

## Splits

Um split por semana (184 no total), de s2018w01 a s2026w11 (temporadas 2018-2026): cada split treina com todos os jogos desde 2011 anteriores à semana testada e testa nessa semana (H-D13). Os splits completos estão em `config.json` no pai do MLflow.

Execuções filhas registradas: 1288. Métricas agregadas são *pooled*: previsões de todos os splits concatenadas e a métrica calculada uma vez.

## Resultados (pooled)

| modelo | papel | n | rmse | mae | winner_acc |
|---|---|---|---|---|---|
| `hfa` | baseline | 2390 | 14.23218 | 11.01520 | 0.54200 |
| `zero` | baseline | 2390 | 14.30724 | 11.12720 | 0.50000 |
| `market` | reference (fora da regra) | 2390 | 12.69618 | 9.80105 | 0.66359 |
| `asof_linear` | candidate | 2390 | 13.11437 | 10.18591 | 0.63797 |
| `elo` **(selecionado)** | candidate | 2390 | 13.07725 | 10.17127 | 0.64133 |
| `ridge_decay_hl17` | candidate | 2390 | 13.11262 | 10.17557 | 0.63293 |
| `ridge_decay_hl34` | candidate | 2390 | 13.15913 | 10.24359 | 0.63335 |

## Regra de seleção e resultado

- Regra (fixada antes do backtest): min pooled rmse entre candidatos; precisa ser melhor que o melhor baseline por mais de 0.
- Modelo selecionado: `elo`
- Bate os baselines: sim

## Versões

- git_commit: `6825626816941f472ea753a80d56da23ed483103` (git_dirty: true)
- harness_version: `0.2.0`
- model_code_sha256: `09013919ecce20f104baf771f3ad4c0e973b272d739f37def37976a4b62c14a8`
- config_sha256: `625644f5b73ac14dab58574f1d35e22900e059ad149e376b1e7226e1ae10ad7a`
- seed: 0
- Execução pai MLflow: `bb7d2992cde94bd4a10aee913c86189d`

## Hiperparâmetros fixos

| modelo | papel | parâmetros |
|---|---|---|
| `hfa` | baseline | `{"estimate": "média de result nos jogos não neutros do treino", "neutral": 0.0}` |
| `zero` | baseline | `{"margin": 0.0}` |
| `asof_linear` | candidate | `{"features": ["ewm4_off_epa", "ewm4_def_epa", "ewm4_point_diff"], "intercept": false, "kind": "asof_linear", "nulls": "linhas de treino com asof nulo saem", "terms": "hfa*(1-neutro) + b . (x_mandante - x_visitante)"}` |
| `elo` | candidate | `{"cap": 28.0, "hfa": 2.0, "init": 0.0, "k": 0.07, "kind": "elo", "order": "kickoff_utc", "reversion": 0.3333333333333333}` |
| `ridge_decay_hl17` | candidate | `{"age_unit": "semanas de calendário até o último jogo do treino", "halflife_weeks": 17.0, "hfa": "estimado, sem penalidade", "kind": "ridge_decay", "lambda": 5.0}` |
| `ridge_decay_hl34` | candidate | `{"age_unit": "semanas de calendário até o último jogo do treino", "halflife_weeks": 34.0, "hfa": "estimado, sem penalidade", "kind": "ridge_decay", "lambda": 5.0}` |
| `market` | reference | `{"column": "spread_line", "sign": "positiva = mandante favorito = margem esperada do mandante"}` |

## RMSE e acerto por temporada de teste

| temporada | n | `elo` rmse | `elo` acerto | `hfa` rmse | `hfa` acerto | `market` rmse | `market` acerto |
|---|---|---|---|---|---|---|---|
| 2018 | 267 | 13.228 | 0.645 | 14.153 | 0.600 | 12.994 | 0.657 |
| 2019 | 267 | 13.370 | 0.632 | 14.919 | 0.523 | 13.065 | 0.643 |
| 2020 | 269 | 12.988 | 0.664 | 14.245 | 0.504 | 12.697 | 0.672 |
| 2021 | 285 | 13.970 | 0.609 | 15.308 | 0.514 | 13.549 | 0.623 |
| 2022 | 284 | 11.749 | 0.642 | 12.377 | 0.573 | 11.487 | 0.663 |
| 2023 | 285 | 13.557 | 0.618 | 14.401 | 0.565 | 13.174 | 0.674 |
| 2024 | 285 | 13.175 | 0.674 | 14.486 | 0.535 | 12.721 | 0.705 |
| 2025 | 285 | 12.850 | 0.651 | 14.114 | 0.535 | 12.245 | 0.658 |
| 2026 | 163 | 12.428 | 0.636 | 13.711 | 0.522 | 11.911 | 0.685 |

## Ratings atuais (`hub-ratings@2`, elo, dados até 2026-11-24)

Vantagem de casa estimada/fixa: 2.00 pontos. Pontos acima de um time médio (0).

| posição | time | rating |
|---|---|---|
| 1 | BUF | +7.58 |
| 2 | JAX | +7.36 |
| 3 | SF | +6.20 |
| 4 | LA | +5.66 |
| 5 | SEA | +5.50 |
| … | … | … |
| 28 | LV | -5.07 |
| 29 | MIA | -5.15 |
| 30 | NYJ | -6.59 |
| 31 | ARI | -7.38 |
| 32 | TEN | -7.42 |

## Registro

- `hub-ratings@champion` = versão 2 (params_sha256 `de248fb1e6b29844921147ee550e2ff90ad13fb49e9a3532ef11ceaf64e115c8`)

## Limitações

- `market` (spread de fechamento) é REFERÊNCIA fora da regra: incorpora lesões, clima, informação privada e a própria decisão do mercado até o fechamento, que nenhum candidato tem. Bater o baseline não é bater o mercado; o RMSE do mercado é o teto realista de comparação.
- A linha de fechamento é conhecida antes do kickoff, mas só no fim da semana; um modelo com ela como feature viraria cópia dela (H-D12), por isso ela não entra nos candidatos.
- Backtest walk-forward SEMANAL (H-D13): cada split treina com todos os jogos anteriores à semana e testa nela, de 2018 até a última semana completa de 2026; a temporada corrente está incompleta. As métricas são pooled sobre todos os testes. Jogos da mesma semana não treinam uns aos outros (inclusive quinta antes de domingo).
- Hiperparâmetros fixos declarados no cartão; nada foi ajustado em 2018+ nem trocado depois de ver o teste. O piloto walk-forward 2013-2017 (`pilots/ratings_pilot.py`, só jogos até 2017) confirma só em parte: k=0,07 é o do ótimo; hfa=2,0 foi fixado a priori e o ótimo do piloto é 2,5 (a configuração usada fica em 9º de 180 no Elo, RMSE ~0,011 acima do ótimo; teto 40 e reversão 0,5 vencem a combinação 28 e 1/3 no ótimo global); no ridge o piloto prefere λ=5 com meia-vida 17, e a meia-vida 34 é a 2ª. Piloto e teste vêm da mesma liga: não é validação independente.
- Elo e ridge só conhecem placares: não sabem de quarterback lesionado, descanso, clima ou troca de elenco (a regressão de 1/3 entre temporadas e o decaimento temporal são o único tratamento da entressafra). A vantagem de casa do Elo é um valor fixo de 2,0 pontos, escolhido a priori (o ótimo do piloto 2013-2017 é 2,5).
- Campo neutro vem de `location == 'Neutral'` (83 jogos, incluindo Super Bowls); nele não há vantagem de casa. Jogos de pós-temporada entram no treino e no teste como os demais.
- O `asof_linear` usa o `team_asof` de cada jogo (estado ANTES dele, só jogos com kickoff estritamente anterior); as linhas de treino com `team_asof` nulo (o primeiro jogo de cada time em 2011) saem do ajuste.
- Acerto do vencedor: empates reais saem; previsão exatamente 0 conta 0,5. Time sem rating (fora do histórico) levanta erro em vez de receber um valor arbitrário.
- Os ratings do `asof_linear` são b·estado antes do PRÓXIMO jogo de cada time; só ele os tem com esse significado. O histórico `ratings_history.parquet` é walk-forward (nunca dentro da amostra), mas o `current_ratings.json` vem do champion ajustado com todos os jogos completos.
