# Fatos: ETL nflverse e dados brutos locais (somente leitura)

Data da coleta: 2026-11-24. Worktree lido: `/Users/pedrocollet/Downloads/NFL Sideline/.claude/worktrees/model-hub-v1`. Dados reais lidos no checkout principal: `/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/data/raw/`. Sem rede, sem pipeline, sem `.env`.

Observação sobre o briefing: `docs/plans/mlflow-tracking-v1/GUARDRAILS.md` existe no worktree e foi lido. Suas regras (somente leitura, nada de commit, nada de pickle, FTN não sai da máquina) foram respeitadas. Nenhum FTN foi aberto.

---

## 1. Como a ETL baixa dados do nflverse

### Dependência
- `etl-pipeline/pyproject.toml` linha 9: `"nflreadpy==0.1.5"`, `"polars==1.44.1"`, `"pyarrow==25.0.1"`. `pandas==2.3.3` é só extra `test`.
- Não há `requirements*.txt` nem lock em `etl-pipeline/`. Só `pyproject.toml`.
- Instalado no venv: `nflreadpy 0.1.5` (confirmado por `importlib` e `pip list`).

### Chamadas ao nflreadpy (único ponto de rede da ETL de dados)
- `etl-pipeline/src/nfl_sideline_etl/extract.py`
  - linha 7: `import nflreadpy as nfl`
  - linhas 48-58: `download_pbp(season)` chama `nfl.load_pbp(seasons=[season])` (linha 51). Captura `ConnectionError`; se a cadeia de exceções tiver HTTP 404 (`_http_status_from_exception_chain`, linhas 22-45), levanta `SourceDataNotPublishedError` (linhas 10-11, 52-56). Outros erros são relançados.
  - linhas 60-62: `download_schedules(season)` chama `nfl.load_schedules(seasons=[season])`.
  - linhas 31-45: `to_polars()` converte retorno Polars ou Pandas para Polars (regra ADR-005).
- `etl-pipeline/seed_teams.py` linha 17 usa `nfl.load_teams()` (tabela `teams`, não é raw de jogos/jogadas; fora do escopo).
- URLs de download ficam dentro do nflreadpy; não há URL no código da ETL. Não verificado (sem rede).

### Escrita do raw
- `etl-pipeline/run_local.py`
  - linha 27: `DEFAULT_DATA_DIR = etl-pipeline/data`
  - linhas 62-77 `_write_nonempty_parquet`: vazio gera erro (PBP → `MissingPbpError`, schedules → `RuntimeError`). Caminho na linha 73: `data_dir/raw/{source}/season={season}/{source}.parquet`. Grava com `frame.write_parquet(path)` direto no caminho final (linha 75), sem arquivo temporário.
  - linhas 80-128 `acquire_season(...)`: schedules primeiro, depois PBP.
    - linhas 110-116: se `season > current_nfl_season()`, lança `MissingPbpError` antes de chamar o nflverse.
    - linhas 120-123: com `allow_missing_pbp`, captura `MissingPbpError` e `SourceDataNotPublishedError`, loga warning e não grava `pbp.parquet`. Fora disso, relança.
- Layout final: `etl-pipeline/data/raw/schedules/season=YYYY/schedules.parquet` e `etl-pipeline/data/raw/pbp/season=YYYY/pbp.parquet`.

### Modo "só adquirir para Parquet", sem banco: EXISTE
- `python etl-pipeline/run_local.py [--season YYYY ...] [--data-dir DIR] [--schedules-only | --pbp-only] [--allow-missing-pbp] [--upload-s3]`
- `run_local.py` linhas 12-23: imports só de `polars`, `extract`, `seasons`. Não importa `psycopg2` nem `load_*`.
- `run_local.py` linhas 131-149 `main()`: não abre conexão. Chama `acquire_season` por temporada com `upload_s3=args.upload_s3`.
- `--upload-s3` (linhas 54-58) é opt-in. S3 só é importado tardiamente (linha 103) quando a flag existe.
- `--schedules-only` e `--pbp-only` são mutuamente exclusivos (linhas 46-48). `--upload-s3` com `--pbp-only` dá erro (linhas 137-138).
- Sem `--season`, usa a temporada corrente (`seasons.py` linhas 16-19 e 33).
- Exceção não tratada em `run_local` sai com código 1 (linhas 153-157).
- Contraste: `run_pipeline.py` sempre abre o banco em `process_season` (linhas 112 `conn = factory()`), mesmo com `--skip-acquire`. Então ele NÃO é modo sem banco. `--skip-acquire` (run_pipeline linhas 257-261) só evita a chamada ao nflverse.

### Como `--allow-missing-pbp` funciona
- `run_local.py` linhas 50-53 (flag) e 120-123 (comportamento). Tolera apenas:
  1. `MissingPbpError`: PBP vazio do nflverse, ou temporada futura além de `current_nfl_season()`.
  2. `SourceDataNotPublishedError`: HTTP 404 do nflverse.
- Nesses casos loga warning, não grava `pbp.parquet` e `rows_pbp = 0`. Schedules continuam gravados.
- Erros de rede, auth, 5xx e schema continuam fatais (a exceção não é capturada, linha 120 só pega as duas classes acima).
- `run_pipeline.py` linhas 60-79 `_validate_local_inputs` (usado com `--skip-acquire`): se `load_metrics.load_pbp` levanta `PbpUnavailable` e a flag está ligada, só loga warning. Se o arquivo local existe com linhas, ele é usado.
- `run_pipeline.py` linhas 252-256 (flag) e 157 (`allow_empty=allow_missing_pbp` repassado a `load_metrics`).
- Testes: `etl-pipeline/tests/test_etl.py` linhas ~185-200 verificam 404 → `SourceDataNotPublishedError` e tolerância só com a flag.

---

## 2. Arquivos raw por temporada (lidos com pyarrow/polars via `etl-pipeline/.venv/bin/python -I`)

Versões no venv: polars 1.44.1, pyarrow 25.0.1, pandas 2.3.3, nflreadpy 0.1.5, Python 3.11.13.

| Arquivo | Tamanho (bytes) | Linhas | Colunas | Escrito por |
|---|---|---|---|---|
| `raw/schedules/season=2023/schedules.parquet` | 31.603 | 285 | 46 | Polars |
| `raw/schedules/season=2025/schedules.parquet` | 33.592 | 285 | 46 | Polars |
| `raw/schedules/season=2026/schedules.parquet` | 26.877 | 272 | 46 | Polars |
| `raw/pbp/season=2023/pbp.parquet` | 13.384.561 | 49.665 | 372 | Polars |
| `raw/pbp/season=2025/pbp.parquet` | 13.266.724 | 48.771 | 372 | Polars |
| `raw/pbp/season=2026/pbp.parquet` | 1.668.541 | 5.489 | 372 | Polars |

Todos com 1 row group. Caminho base: `/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/data/raw/`.

### Schedules
- `week`: 2023 = 1..22; 2025 = 1..22; 2026 = 1..18.
- `game_type` (contagem):
  - 2023: REG 272, WC 6, DIV 4, CON 2, SB 1.
  - 2025: REG 272, WC 6, DIV 4, CON 2, SB 1.
  - 2026: REG 272 (sem jogos de pós-temporada).
- `gameday` (String): 2026 vai de `2026-09-09` a `2027-01-10`. Ou seja, o arquivo 2026 contém jogos futuros em relação à data atual (2026-11-24), com placar preenchido só em parte (ver abaixo).
- Jogos com placar (`home_score` não nulo): 2023 = 285 de 285; 2025 = 285 de 285; 2026 = 32 de 272.
- Por semana de 2026, jogos com placar: semana 1 = 16, semana 2 = 16. Demais semanas não têm placar.
- Contagem de jogos por semana de 2026: 16, 16, 16, 16, 15, 14, 14, 14, 15, 14, 13, 16, 14, 15, 16, 16, 16, 16.

### PBP
- `week`: 2023 = 1..22; 2025 = 1..22; 2026 = 1..2.
- `season_type`:
  - 2023: REG 47.399, POST 2.266.
  - 2025: REG 46.452, POST 2.319.
  - 2026: REG 5.489.
- `game_date` (String): 2023 = 2023-09-07 a 2024-02-11; 2025 = 2025-09-04 a 2026-02-08; 2026 = 2026-09-09 a 2026-09-21.
- Data mais recente de jogo com PBP: 2026-09-21 (jogo LA x NYG, semana 2). Não há PBP posterior.

### 2026: semanas com PBP
- Apenas semanas 1 e 2. Total de 32 jogos e 5.489 jogadas (ver linha de contagem por semana).
  - Semana 1: 16 jogos, 2.756 jogadas.
  - Semana 2: 16 jogos, 2.733 jogadas.
- Semanas 3 a 18: sem PBP no raw.
- Todos os `game_id` de PBP 2026 existem em `schedules` 2026.
- Exemplo de jogo: `2026_01_NE_SEA`, 2026-09-09, 166 jogadas.
- Mtime dos arquivos 2026: 2026-09-22 01:43 (PBP e schedules). Não verifiquei se há atualização posterior.

### Exemplo de 2 linhas de schedules 2026 (valores reais)
1. `game_id=2026_01_NE_SEA`, season 2026, game_type REG, week 1, gameday 2026-09-09 (Wednesday, 20:20), away NE 10 @ home SEA 13, result 3, total 23, overtime 0, roof outdoors, surface fieldturf, temp 74, wind 6, spread_line 3.0, total_line 44.5, away_moneyline 140, home_moneyline -166, away_qb_name Drake Maye, home_qb_name Sam Darnold, referee Adrian Hill, stadium Lumen Field.
2. `game_id=2026_01_SF_LA`, season 2026, game_type REG, week 1, gameday 2026-09-10 (Thursday, 20:35), away SF 27 @ home LA 7, result -20, total 34, overtime 0, roof dome, surface grass, temp 57, wind 4, spread_line 3.5, total_line 47.5, away_moneyline 180, home_moneyline -218, away_qb_name Brock Purdy, home_qb_name Matthew Stafford, stadium Melbourne Cricket Ground (`stadium_id MEL00`, local neutro).

### Schema de schedules (46 colunas; igual em 2025 e 2026)
`game_id` String; `season` Int32; `game_type` String; `week` Int32; `gameday` String; `weekday` String; `gametime` String; `away_team` String; `away_score` Int32; `home_team` String; `home_score` Int32; `location` String; `result` Int32; `total` Int32; `overtime` Int32; `old_game_id` String; `gsis` Int32; `nfl_detail_id` String; `pfr` String; `pff` Int32; `espn` String; `ftn` Int32; `away_rest` Int32; `home_rest` Int32; `away_moneyline` Int32; `home_moneyline` Int32; `spread_line` Float64; `away_spread_odds` Int32; `home_spread_odds` Int32; `total_line` Float64; `under_odds` Int32; `over_odds` Int32; `div_game` Int32; `roof` String; `surface` String; `temp` Int32; `wind` Int32; `away_qb_id` String; `home_qb_id` String; `away_qb_name` String; `home_qb_name` String; `away_coach` String; `home_coach` String; `referee` String; `stadium_id` String; `stadium` String.

Contrato de colunas usado por `load_games.py` (`SCHEDULE_COLUMNS = tuple(GAMES_COLUMNS)`, linha 54): verificado em `load_schedules` (linhas 174-188), que exige as colunas do contrato.

---

## 3. Schema do PBP (372 colunas, dtypes de `season=2025/pbp.parquet`)

Checagem das colunas pedidas:
- **Presentes**: ep, epa, wp, def_wp, home_wp, vegas_wp, wpa, down, ydstogo, yardline_100, half_seconds_remaining, game_seconds_remaining, quarter_seconds_remaining, qtr, score_differential, posteam_timeouts_remaining, defteam_timeouts_remaining, posteam, defteam, home_team, away_team, play_type, pass, rush, roof, surface, temp, wind, spread_line, total_line, result, success, cpoe, xpass, pass_oe, air_yards, yards_after_catch, xyac_epa, fourth_down_converted, field_goal_result, drive, fixed_drive_result, drive_end_transition, passer_player_id, receiver_player_id, rusher_player_id, game_id, play_id, old_game_id, season, week, season_type, game_date.
- **Ausentes**: `punt` (existem `punt_attempt`, `punt_blocked`, `punt_inside_twenty`, `punt_in_endzone`, `punt_out_of_bounds`, `punt_downed`, `punt_fair_catch`, `punt_returner_*`, `punter_player_id`); `next_score_half` (não existe nenhuma coluna `next_score*`).
- **Fim de drive, equivalentes disponíveis**: `fixed_drive_result` (String), `drive_end_transition` (String), `drive_ended_with_score` (Float64), `drive_end_yard_line` (String), `drive_play_id_ended` (Float64), `end_clock_time` (String), `end_yard_line` (String).
- Observações de dtype: `pass`, `rush`, `success`, `wp`, `ep`, `epa` são Float64 (não Boolean). `game_date` é String. `season` e `week` são Int32. `play_id` é Float64. `spread_line`, `total_line` estão no PBP também.

A lista completa de todas as 372 colunas com dtype está abaixo (seção "Anexo A").

---

## 4. Outras fontes locais (somente listagem; nenhum FTN aberto)

Local: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/`

- Total de `*.parquet`: 657 arquivos, cerca de 1,8 GB (1.798.973.267 bytes).
- Por diretório de primeiro nível:
  - `backups/`: 226
  - `qb-structure-production-v1/`: 112
  - `real-recovery/`: 72
  - `qb-interception-risk-baseline-v1/`: 71
  - `qb-risk-temporal-calibration-v2/`: 65
  - `qb-expected-interceptions-v1/`: 42
  - `qb-risk-lab-v1/`: 24
  - `broadcast-w1-7-v1/`: 8
  - `broadcast-matchup-w12-v1/`: 7
  - `broadcast-season-timeline-v1/`: 6
  - `broadcast-score-curve-v2/`: 6
  - `qb-progression-improvisation-lab-v1/`: 4
  - `broadcast-comparison-foundation-v1/`: 4
  - `broadcast-situational-w12-v1/`: 3
  - `broadcast-redzone-epa-v1/`: 3
  - `broadcast-hub-team-w12-v1/`: 3
  - `qb-risk-outcomes-lab-v1/`: 1

Exemplos de caminhos (relativos a `local-artifacts/`, sem `backups/`; até 40):
- `broadcast-w1-7-v1/20261027-v1/source/pbp.parquet`
- `broadcast-w1-7-v1/20261027-v1/source/schedules.parquet`
- `broadcast-w1-7-v1/20261027-v1/verified-copy/source/pbp.parquet`
- `broadcast-w1-7-v1/20261027-v1/verified-copy/source/schedules.parquet`
- `broadcast-situational-w12-v1/20261023-v1/bundle/pbp.parquet`
- `broadcast-situational-w12-v1/20261023-v1/verified-copy/pbp.parquet`
- `broadcast-situational-w12-v1/20261023-v1/bundle-reconciled/pbp.parquet`
- `broadcast-season-timeline-v1/20261027-v1/bundle/source/source/pbp.parquet`
- `broadcast-season-timeline-v1/20261027-v1/bundle/source/source/schedules.parquet`
- `broadcast-score-curve-v2/20261027-v1/bundle/source/source/source/pbp.parquet`
- `broadcast-score-curve-v2/20261027-v1/bundle/source/source/source/schedules.parquet`
- `broadcast-redzone-epa-v1/20261026-v1/bundle/source/sources/situational/pbp.parquet`
- `broadcast-matchup-w12-v1/20261024-v1/bundle-final/sources/situational/pbp.parquet`
- `broadcast-hub-team-w12-v1/20261024-v1/bundle/source/matchups/sources/situational/pbp.parquet`
- `broadcast-comparison-foundation-v1/20261023-v1/bundle/sources/situational/pbp.parquet`
- `qb-progression-improvisation-lab-v1/packages/5b780052143352a5abf8ffec/plays.parquet`
- `qb-risk-lab-v1/runs/20261104T150413769562Z/pbp.parquet`
- `qb-risk-lab-v1/runs/20261104T150413769562Z/ftn.parquet` (FTN: não aberto)
- `qb-risk-temporal-calibration-v2/20261104-v2/inputs/roster_weekly_2026.parquet`
- `qb-risk-temporal-calibration-v2/20261104-v2/experiment-final/splits.parquet`
- `qb-risk-temporal-calibration-v2/20261104-v2/experiment-final/predictions.parquet`
- `qb-interception-risk-baseline-v1/20261104-v1/build-v2/dataset.parquet`
- `qb-interception-risk-baseline-v1/20261104-v1/application-v1/application_predictions_context.parquet`
- `qb-interception-risk-baseline-v1/20261104-v1/development-v1/development_context_2023.parquet`
- `qb-interception-risk-baseline-v1/20261104-v1/evaluation-v1/test_predictions_context.parquet`
- `qb-interception-risk-baseline-v1/20261104-v1/raw/pbp_2022.parquet`
- `qb-interception-risk-baseline-v1/20261104-v1/raw/pbp_2026.parquet`
- `qb-interception-risk-baseline-v1/20261104-v1/raw/ftn_2025.parquet` (FTN: não aberto)
- `qb-expected-interceptions-v1/20261105-v1/current/pbp.parquet`
- `qb-expected-interceptions-v1/20261105-v1/current/ftn.parquet` (FTN: não aberto)
- `qb-expected-interceptions-v1/20261105-v1/build/dataset.parquet`
- `qb-expected-interceptions-v1/20261105-v1/lineage/historical-dataset.parquet`
- `qb-expected-interceptions-v1/20261105-v1/application/pass_predictions.parquet`
- `qb-expected-interceptions-v1/20261105-v1/raw/ftn_2022.parquet` (FTN: não aberto)

Observação: 57 caminhos contêm `ftn` no nome (FTN, CC BY-SA 4.0, não devem sair da máquina conforme GUARDRAILS). Há também cópias de `pbp.parquet` e `schedules.parquet` em vários bundles e em `backups/`.

Não encontrado: nenhum `*.parquet` fora de `local-artifacts/` nem dentro do repositório além de `etl-pipeline/data/raw/`.

---

## 5. Pacotes no `etl-pipeline/.venv` (Python 3.11.13)

Disponíveis:
- `polars 1.44.1` (+ `polars-runtime-32 1.44.1`)
- `pyarrow 25.0.1`
- `pandas 2.3.3`
- `nflreadpy 0.1.5`
- `numpy 2.4.6`
- `boto3 1.43.88`, `botocore 1.43.88`
- `psycopg2-binary 2.9.12`
- `pydantic 2.13.5`, `pydantic-settings 2.15.0`, `python-dotenv 1.2.3`
- `requests 2.34.2`
- `pytest 9.0.2`

Não encontrado: `scikit-learn` (sklearn), `mlflow`, `duckdb`, `statsmodels`, `xgboost`, `lightgbm`. Não instalado no venv.

---

## Anexo A: colunas do PBP 2025 (372), índice, nome, dtype

Fonte: `/private/tmp/claude-501/-Users-pedrocollet-Downloads-NFL-Sideline/4a6545df-3bfd-4df3-aa1e-97d86449d2b6/scratchpad/pbp2025_schema.txt`

| # | coluna | dtype |
|---|---|---|
| 0 | play_id | Float64 |
| 1 | game_id | String |
| 2 | old_game_id | String |
| 3 | home_team | String |
| 4 | away_team | String |
| 5 | season_type | String |
| 6 | week | Int32 |
| 7 | posteam | String |
| 8 | posteam_type | String |
| 9 | defteam | String |
| 10 | side_of_field | String |
| 11 | yardline_100 | Float64 |
| 12 | game_date | String |
| 13 | quarter_seconds_remaining | Float64 |
| 14 | half_seconds_remaining | Float64 |
| 15 | game_seconds_remaining | Float64 |
| 16 | game_half | String |
| 17 | quarter_end | Float64 |
| 18 | drive | Float64 |
| 19 | sp | Float64 |
| 20 | qtr | Float64 |
| 21 | down | Float64 |
| 22 | goal_to_go | Float64 |
| 23 | time | String |
| 24 | yrdln | String |
| 25 | ydstogo | Float64 |
| 26 | ydsnet | Float64 |
| 27 | desc | String |
| 28 | play_type | String |
| 29 | yards_gained | Float64 |
| 30 | shotgun | Float64 |
| 31 | no_huddle | Float64 |
| 32 | qb_dropback | Float64 |
| 33 | qb_kneel | Float64 |
| 34 | qb_spike | Float64 |
| 35 | qb_scramble | Float64 |
| 36 | pass_length | String |
| 37 | pass_location | String |
| 38 | air_yards | Float64 |
| 39 | yards_after_catch | Float64 |
| 40 | run_location | String |
| 41 | run_gap | String |
| 42 | field_goal_result | String |
| 43 | kick_distance | Float64 |
| 44 | extra_point_result | String |
| 45 | two_point_conv_result | String |
| 46 | home_timeouts_remaining | Float64 |
| 47 | away_timeouts_remaining | Float64 |
| 48 | timeout | Float64 |
| 49 | timeout_team | String |
| 50 | td_team | String |
| 51 | td_player_name | String |
| 52 | td_player_id | String |
| 53 | posteam_timeouts_remaining | Float64 |
| 54 | defteam_timeouts_remaining | Float64 |
| 55 | total_home_score | Float64 |
| 56 | total_away_score | Float64 |
| 57 | posteam_score | Float64 |
| 58 | defteam_score | Float64 |
| 59 | score_differential | Float64 |
| 60 | posteam_score_post | Float64 |
| 61 | defteam_score_post | Float64 |
| 62 | score_differential_post | Float64 |
| 63 | no_score_prob | Float64 |
| 64 | opp_fg_prob | Float64 |
| 65 | opp_safety_prob | Float64 |
| 66 | opp_td_prob | Float64 |
| 67 | fg_prob | Float64 |
| 68 | safety_prob | Float64 |
| 69 | td_prob | Float64 |
| 70 | extra_point_prob | Float64 |
| 71 | two_point_conversion_prob | Float64 |
| 72 | ep | Float64 |
| 73 | epa | Float64 |
| 74 | total_home_epa | Float64 |
| 75 | total_away_epa | Float64 |
| 76 | total_home_rush_epa | Float64 |
| 77 | total_away_rush_epa | Float64 |
| 78 | total_home_pass_epa | Float64 |
| 79 | total_away_pass_epa | Float64 |
| 80 | air_epa | Float64 |
| 81 | yac_epa | Float64 |
| 82 | comp_air_epa | Float64 |
| 83 | comp_yac_epa | Float64 |
| 84 | total_home_comp_air_epa | Float64 |
| 85 | total_away_comp_air_epa | Float64 |
| 86 | total_home_comp_yac_epa | Float64 |
| 87 | total_away_comp_yac_epa | Float64 |
| 88 | total_home_raw_air_epa | Float64 |
| 89 | total_away_raw_air_epa | Float64 |
| 90 | total_home_raw_yac_epa | Float64 |
| 91 | total_away_raw_yac_epa | Float64 |
| 92 | wp | Float64 |
| 93 | def_wp | Float64 |
| 94 | home_wp | Float64 |
| 95 | away_wp | Float64 |
| 96 | wpa | Float64 |
| 97 | vegas_wpa | Float64 |
| 98 | vegas_home_wpa | Float64 |
| 99 | home_wp_post | Float64 |
| 100 | away_wp_post | Float64 |
| 101 | vegas_wp | Float64 |
| 102 | vegas_home_wp | Float64 |
| 103 | total_home_rush_wpa | Float64 |
| 104 | total_away_rush_wpa | Float64 |
| 105 | total_home_pass_wpa | Float64 |
| 106 | total_away_pass_wpa | Float64 |
| 107 | air_wpa | Float64 |
| 108 | yac_wpa | Float64 |
| 109 | comp_air_wpa | Float64 |
| 110 | comp_yac_wpa | Float64 |
| 111 | total_home_comp_air_wpa | Float64 |
| 112 | total_away_comp_air_wpa | Float64 |
| 113 | total_home_comp_yac_wpa | Float64 |
| 114 | total_away_comp_yac_wpa | Float64 |
| 115 | total_home_raw_air_wpa | Float64 |
| 116 | total_away_raw_air_wpa | Float64 |
| 117 | total_home_raw_yac_wpa | Float64 |
| 118 | total_away_raw_yac_wpa | Float64 |
| 119 | punt_blocked | Float64 |
| 120 | first_down_rush | Float64 |
| 121 | first_down_pass | Float64 |
| 122 | first_down_penalty | Float64 |
| 123 | third_down_converted | Float64 |
| 124 | third_down_failed | Float64 |
| 125 | fourth_down_converted | Float64 |
| 126 | fourth_down_failed | Float64 |
| 127 | incomplete_pass | Float64 |
| 128 | touchback | Float64 |
| 129 | interception | Float64 |
| 130 | punt_inside_twenty | Float64 |
| 131 | punt_in_endzone | Float64 |
| 132 | punt_out_of_bounds | Float64 |
| 133 | punt_downed | Float64 |
| 134 | punt_fair_catch | Float64 |
| 135 | kickoff_inside_twenty | Float64 |
| 136 | kickoff_in_endzone | Float64 |
| 137 | kickoff_out_of_bounds | Float64 |
| 138 | kickoff_downed | Float64 |
| 139 | kickoff_fair_catch | Float64 |
| 140 | fumble_forced | Float64 |
| 141 | fumble_not_forced | Float64 |
| 142 | fumble_out_of_bounds | Float64 |
| 143 | solo_tackle | Float64 |
| 144 | safety | Float64 |
| 145 | penalty | Float64 |
| 146 | tackled_for_loss | Float64 |
| 147 | fumble_lost | Float64 |
| 148 | own_kickoff_recovery | Float64 |
| 149 | own_kickoff_recovery_td | Float64 |
| 150 | qb_hit | Float64 |
| 151 | rush_attempt | Float64 |
| 152 | pass_attempt | Float64 |
| 153 | sack | Float64 |
| 154 | touchdown | Float64 |
| 155 | pass_touchdown | Float64 |
| 156 | rush_touchdown | Float64 |
| 157 | return_touchdown | Float64 |
| 158 | extra_point_attempt | Float64 |
| 159 | two_point_attempt | Float64 |
| 160 | field_goal_attempt | Float64 |
| 161 | kickoff_attempt | Float64 |
| 162 | punt_attempt | Float64 |
| 163 | fumble | Float64 |
| 164 | complete_pass | Float64 |
| 165 | assist_tackle | Float64 |
| 166 | lateral_reception | Float64 |
| 167 | lateral_rush | Float64 |
| 168 | lateral_return | Float64 |
| 169 | lateral_recovery | Float64 |
| 170 | passer_player_id | String |
| 171 | passer_player_name | String |
| 172 | passing_yards | Float64 |
| 173 | receiver_player_id | String |
| 174 | receiver_player_name | String |
| 175 | receiving_yards | Float64 |
| 176 | rusher_player_id | String |
| 177 | rusher_player_name | String |
| 178 | rushing_yards | Float64 |
| 179 | lateral_receiver_player_id | String |
| 180 | lateral_receiver_player_name | String |
| 181 | lateral_receiving_yards | Float64 |
| 182 | lateral_rusher_player_id | String |
| 183 | lateral_rusher_player_name | String |
| 184 | lateral_rushing_yards | Float64 |
| 185 | lateral_sack_player_id | String |
| 186 | lateral_sack_player_name | String |
| 187 | interception_player_id | String |
| 188 | interception_player_name | String |
| 189 | lateral_interception_player_id | String |
| 190 | lateral_interception_player_name | String |
| 191 | punt_returner_player_id | String |
| 192 | punt_returner_player_name | String |
| 193 | lateral_punt_returner_player_id | String |
| 194 | lateral_punt_returner_player_name | String |
| 195 | kickoff_returner_player_name | String |
| 196 | kickoff_returner_player_id | String |
| 197 | lateral_kickoff_returner_player_id | String |
| 198 | lateral_kickoff_returner_player_name | String |
| 199 | punter_player_id | String |
| 200 | punter_player_name | String |
| 201 | kicker_player_name | String |
| 202 | kicker_player_id | String |
| 203 | own_kickoff_recovery_player_id | String |
| 204 | own_kickoff_recovery_player_name | String |
| 205 | blocked_player_id | String |
| 206 | blocked_player_name | String |
| 207 | tackle_for_loss_1_player_id | String |
| 208 | tackle_for_loss_1_player_name | String |
| 209 | tackle_for_loss_2_player_id | String |
| 210 | tackle_for_loss_2_player_name | String |
| 211 | qb_hit_1_player_id | String |
| 212 | qb_hit_1_player_name | String |
| 213 | qb_hit_2_player_id | String |
| 214 | qb_hit_2_player_name | String |
| 215 | forced_fumble_player_1_team | String |
| 216 | forced_fumble_player_1_player_id | String |
| 217 | forced_fumble_player_1_player_name | String |
| 218 | forced_fumble_player_2_team | String |
| 219 | forced_fumble_player_2_player_id | String |
| 220 | forced_fumble_player_2_player_name | String |
| 221 | solo_tackle_1_team | String |
| 222 | solo_tackle_2_team | String |
| 223 | solo_tackle_1_player_id | String |
| 224 | solo_tackle_2_player_id | String |
| 225 | solo_tackle_1_player_name | String |
| 226 | solo_tackle_2_player_name | String |
| 227 | assist_tackle_1_player_id | String |
| 228 | assist_tackle_1_player_name | String |
| 229 | assist_tackle_1_team | String |
| 230 | assist_tackle_2_player_id | String |
| 231 | assist_tackle_2_player_name | String |
| 232 | assist_tackle_2_team | String |
| 233 | assist_tackle_3_player_id | String |
| 234 | assist_tackle_3_player_name | String |
| 235 | assist_tackle_3_team | String |
| 236 | assist_tackle_4_player_id | String |
| 237 | assist_tackle_4_player_name | String |
| 238 | assist_tackle_4_team | String |
| 239 | tackle_with_assist | Float64 |
| 240 | tackle_with_assist_1_player_id | String |
| 241 | tackle_with_assist_1_player_name | String |
| 242 | tackle_with_assist_1_team | String |
| 243 | tackle_with_assist_2_player_id | String |
| 244 | tackle_with_assist_2_player_name | String |
| 245 | tackle_with_assist_2_team | String |
| 246 | pass_defense_1_player_id | String |
| 247 | pass_defense_1_player_name | String |
| 248 | pass_defense_2_player_id | String |
| 249 | pass_defense_2_player_name | String |
| 250 | fumbled_1_team | String |
| 251 | fumbled_1_player_id | String |
| 252 | fumbled_1_player_name | String |
| 253 | fumbled_2_player_id | String |
| 254 | fumbled_2_player_name | String |
| 255 | fumbled_2_team | String |
| 256 | fumble_recovery_1_team | String |
| 257 | fumble_recovery_1_yards | Float64 |
| 258 | fumble_recovery_1_player_id | String |
| 259 | fumble_recovery_1_player_name | String |
| 260 | fumble_recovery_2_team | String |
| 261 | fumble_recovery_2_yards | Float64 |
| 262 | fumble_recovery_2_player_id | String |
| 263 | fumble_recovery_2_player_name | String |
| 264 | sack_player_id | String |
| 265 | sack_player_name | String |
| 266 | half_sack_1_player_id | String |
| 267 | half_sack_1_player_name | String |
| 268 | half_sack_2_player_id | String |
| 269 | half_sack_2_player_name | String |
| 270 | return_team | String |
| 271 | return_yards | Float64 |
| 272 | penalty_team | String |
| 273 | penalty_player_id | String |
| 274 | penalty_player_name | String |
| 275 | penalty_yards | Float64 |
| 276 | replay_or_challenge | Float64 |
| 277 | replay_or_challenge_result | String |
| 278 | penalty_type | String |
| 279 | defensive_two_point_attempt | Float64 |
| 280 | defensive_two_point_conv | Float64 |
| 281 | defensive_extra_point_attempt | Float64 |
| 282 | defensive_extra_point_conv | Float64 |
| 283 | safety_player_name | String |
| 284 | safety_player_id | String |
| 285 | season | Int32 |
| 286 | cp | Float64 |
| 287 | cpoe | Float64 |
| 288 | series | Float64 |
| 289 | series_success | Float64 |
| 290 | series_result | String |
| 291 | order_sequence | Float64 |
| 292 | start_time | String |
| 293 | time_of_day | String |
| 294 | stadium | String |
| 295 | weather | String |
| 296 | nfl_api_id | String |
| 297 | play_clock | String |
| 298 | play_deleted | Float64 |
| 299 | play_type_nfl | String |
| 300 | special_teams_play | Float64 |
| 301 | st_play_type | String |
| 302 | end_clock_time | String |
| 303 | end_yard_line | String |
| 304 | fixed_drive | Float64 |
| 305 | fixed_drive_result | String |
| 306 | drive_real_start_time | String |
| 307 | drive_play_count | Float64 |
| 308 | drive_time_of_possession | String |
| 309 | drive_first_downs | Float64 |
| 310 | drive_inside20 | Float64 |
| 311 | drive_ended_with_score | Float64 |
| 312 | drive_quarter_start | Float64 |
| 313 | drive_quarter_end | Float64 |
| 314 | drive_yards_penalized | Float64 |
| 315 | drive_start_transition | String |
| 316 | drive_end_transition | String |
| 317 | drive_game_clock_start | String |
| 318 | drive_game_clock_end | String |
| 319 | drive_start_yard_line | String |
| 320 | drive_end_yard_line | String |
| 321 | drive_play_id_started | Float64 |
| 322 | drive_play_id_ended | Float64 |
| 323 | away_score | Int32 |
| 324 | home_score | Int32 |
| 325 | location | String |
| 326 | result | Int32 |
| 327 | total | Int32 |
| 328 | spread_line | Float64 |
| 329 | total_line | Float64 |
| 330 | div_game | Int32 |
| 331 | roof | String |
| 332 | surface | String |
| 333 | temp | Int32 |
| 334 | wind | Int32 |
| 335 | home_coach | String |
| 336 | away_coach | String |
| 337 | stadium_id | String |
| 338 | game_stadium | String |
| 339 | aborted_play | Float64 |
| 340 | success | Float64 |
| 341 | passer | String |
| 342 | passer_jersey_number | Int32 |
| 343 | rusher | String |
| 344 | rusher_jersey_number | Int32 |
| 345 | receiver | String |
| 346 | receiver_jersey_number | Int32 |
| 347 | pass | Float64 |
| 348 | rush | Float64 |
| 349 | first_down | Float64 |
| 350 | special | Float64 |
| 351 | play | Float64 |
| 352 | passer_id | String |
| 353 | rusher_id | String |
| 354 | receiver_id | String |
| 355 | name | String |
| 356 | jersey_number | Int32 |
| 357 | id | String |
| 358 | fantasy_player_name | String |
| 359 | fantasy_player_id | String |
| 360 | fantasy | String |
| 361 | fantasy_id | String |
| 362 | out_of_bounds | Float64 |
| 363 | home_opening_kickoff | Float64 |
| 364 | qb_epa | Float64 |
| 365 | xyac_epa | Float64 |
| 366 | xyac_mean_yardage | Float64 |
| 367 | xyac_median_yardage | Int32 |
| 368 | xyac_success | Float64 |
| 369 | xyac_fd | Float64 |
| 370 | xpass | Float64 |
| 371 | pass_oe | Float64 |
