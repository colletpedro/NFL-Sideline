# Fatos v1 — store da baseline QB interception risk (somente leitura)

Store (S): `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-interception-risk-baseline-v1/20261104-v1`
Worktree (W): `/Users/pedrocollet/Downloads/NFL Sideline/.claude/worktrees/mlflow-tracking-v1`
Leitura feita com `/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python -I` (pandas 2.3.3, pyarrow 25.0.1). O Python do sistema não tem pandas. Nada foi escrito em S, em W nem no repositório. Só este arquivo foi criado.
Script de leitura (scratchpad): `/private/tmp/claude-501/-Users-pedrocollet-Downloads-NFL-Sideline/2c205806-a206-4f1c-bd06-29a4e5995c2c/scratchpad/mlflow-scout/dump_v1.py`

---

## 0. Resumo dos achados que mudam a implementação

- **Diretórios canônicos confirmados:** `build-v2`, `development-v3`, `evaluation-v1`, `application-v1`, `figures-v4`. Confirmado por `verify_reproduction.py` (linhas 12–14), pelo `reproduction-check.json` (84 arquivos, `passed: true`) e pelo `HANDOFF.md`. **Divergência:** `docs/plans/qb-interception-risk-baseline-v1/README.md` linha 18 diz `figures-v3/`. Está desatualizado.
- **Hashes de código de `development-v3/environment.json` vs. worktree:** `acquire.py`, `model.py`, `evaluation.py` batem. `pipeline.py`, `dataset.py` e `plots.py` **não batem** com o arquivo atual da worktree.
- **Causa rastreada por commit:** os hashes de `pipeline.py`, `dataset.py`, `model.py`, `evaluation.py` e `acquire.py` de `environment.json` batem exatamente com o commit **`35ac931`** (freeze pré-teste). Esse commit não tem `plots.py`. O hash `011b1a9c…` de `plots.py` não aparece em nenhum commit (o arquivo era não rastreado na execução). `910dfae` (avaliação) alterou `pipeline.py` e `dataset.py` e adicionou `plots.py`, `verify_reproduction.py` etc. Os hashes atuais são `pipeline.py` = `431832e0…`, `dataset.py` = `9a6f86b2…`, `plots.py` = `c7965333…`.
- **Pergunta de SHA respondida:** `dataset.parquet` (S) = `10e90375…` = manifest = `frozen_config.dataset_sha256`. `design.json` (W) = `4f22d111…` = `frozen_config.design_sha256`. `frozen_config.json` (S) = `3add5c61…` = `evaluation_receipt.frozen_config_sha256` = `application_receipt.frozen_config_sha256`.
- **Implicação para o importador:** a proveniência de `development-v3` é o commit `35ac931`; `build-v2` é de `05c18ed`; `evaluation-v1` e `application-v1` são de `910dfae` (ou posterior, com `archive.py` em `d654bd6`, que não altera `pipeline/dataset/plots`). Gravar isso como tag de proveniência, não como "commit único".

---

## 1. Árvore do store (profundidade 2, tamanhos reais em disco)

Total: 224 MB (`du`). Tamanhos abaixo são do `du -h`/`ls`.

### 1.1 Canônicos (usar)

| Diretório | Conteúdo | Tamanho |
|---|---|---|
| `build-v2/` | `dataset.parquet` (1,0 MB), `splits.csv` (4,4 MB), `build_manifest.json` (256 B), `audit.json` (28 KB), `audit/` (2,5 MB, 50+ CSV/parquet) | 7,9 MB |
| `development-v3/` | `development_{context,depth}_{2023,2024}.parquet` (4 × ~230 KB), `model_{context,depth}_2022_2024.json` (2,3 KB / 3,1 KB), `development_metrics.json` (16 KB), `frozen_config.json` (1,9 KB), `environment.json` (781 B) | 952 KB |
| `evaluation-v1/` | `test_predictions_{context,depth}.parquet` (236 KB cada), `metrics.json` (2,1 KB), `calibration_{context,depth}.json` (2,0 KB / 2,1 KB), `groups_{context,depth}.json` (10,3 KB cada), `coefficients_{context,depth}.csv`, `evaluation_receipt.json` (219 B) | 520 KB |
| `application-v1/` | `application_predictions_{context,depth}.parquet` (116 KB cada), `qb_{context,depth}.csv` (~10 KB), `qb_sensitivity.csv` (20 KB), `model_{context,depth}_2022_2025.json` (2,3 KB / 3,1 KB), `application_diagnostics_{context,depth}.json` (2,5 KB / 2,6 KB), `application_receipt.json` (271 B) | 296 KB |
| `figures-v4/` | 8 PNG/SVG (`calibration_2025`, `depth_sensitivity_2026`, `difference_per100_2026`, `observed_expected_2026`), `calibration_support.csv`, `plot_passers.csv` (10 arquivos) | 1,5 MB |
| `raw/` | `pbp_2022..2026.parquet` (19–20 MB cada, 2026 = 7,6 MB), `ftn_2022..2026.parquet` (256–556 KB), `schedules.csv` (2,1 MB) | 90 MB |
| `documentation/` | dicionários, licenças, loaders (`ftn_*`, `pbp_*`, `schedule.txt`) | 332 KB |
| `sources.json` | manifesto de fontes (20 registros) | 176 KB |
| `reproduction-check.json` | comparação byte a byte (84 registros, `passed: true`) | 28 KB |
| `reproduction-final/` | reprodução final: `build/`, `development/`, `evaluation/`, `application/`, `figures/` (11 MB) | 11 MB |
| `wheelhouse/`, `wheelhouse-manifest.json`, `requirements-final.lock`, `requirements-initial-numpy226.lock` | dependências offline (macOS arm64, cp311) | ~140 MB (wheelhouse) |
| `acquisition-progress.json`, `source-metadata-supplement.json` | metadados de aquisição | 168 KB / 83 KB |
| `isolation-final.json` (8 KB), `numerical_check.json` (4 KB) | verificações de isolamento e numérica | — |
| `*.log` finais: `reproduction-final.log`, `offline-install.log`, `offline-tests.log`, `tests-final.log`, `npm-ci.log`, `wheelhouse.log`, `legacy-tests.log` | logs | — |

### 1.2 Superados / tentativas (não usar como fonte)

| Caminho | Motivo |
|---|---|
| `build-v1/` (vazio, só `audit/`) | build abortado por colisão de nomes (CHECKPOINTS item 2; REPORT.md linha 185) |
| `development-v1/` (16 KB metrics, 952 KB total) | tentativa anterior; `model_*` tem intercepto ligeiramente diferente de v3 (`-2.977251151453414` vs `-2.9772511514532063`, diferença ~3e-10). Não é a versão congelada. |
| `development-v2-singlethread/` (vazio) e `development-v2.log` (6,9 KB) | tentativa abortada por NumPy 2.2.6/Accelerate (CHECKPOINTS item 3) |
| `development-v3.log` | log da execução congelada (120 bytes), não é output |
| `evaluation-v1.log`, `application-v1.log` | logs (não são outputs) |
| `figures-v1/`, `figures-v2/`, `figures-v3/` | figuras anteriores; `figures-v3` é citada no README desatualizado |
| `reproduction-v1/` (vazio, subpastas) e `reproduction-v1.log` | primeira tentativa de reprodução |
| `git-diff-check.log` (0 B) | log vazio |

Observação: `reproduction-final/` **não** é o canônico; é a reprodução (prova) de `build-v2`, `development-v3`, `evaluation-v1`, `application-v1` e `figures-v4` em destino novo (comparação do `verify_reproduction.py` contra o S canônico).

---

## 2. Arquivos (estrutura e valores reais)

### 2.1 `build-v2/build_manifest.json`
Chaves: `dataset_sha256`, `gate`, `independent_raw_reconciliation`, `rows`, `sources_sha256`.
- `dataset_sha256` = `10e90375f22a187f361007e7db84a6f5bf2c81451171be4be4e805d7cc67c296`
- `gate` = `"PASS"`
- `independent_raw_reconciliation` = `true`
- `rows` = `78460`
- `sources_sha256` = `9a8274510ef2231e8b12e5181b905326cce5abf3867eeb6d93da6f4876fdc729`

### 2.2 `development-v3/development_metrics.json`
- Tipo: lista, **16 registros** = 2 variantes × 4 valores de C × 2 folds.
- Chaves de cada registro: `C`, `constant`, `model`, `train_years`, `validation`, `variant`.
- `model` e `constant` têm as mesmas 9 chaves: `brier`, `expected`, `log_loss`, `mean_probability`, `n`, `positives`, `pr_auc_average_precision`, `prevalence`, `roc_auc`.
- Combinações distintas `(variant, C, validation)`: todas as 16 aparecem uma vez. Variantes: `context`, `depth`. C: `0.01`, `0.1`, `1.0`, `10.0`. Validação: `2023` (train_years `[2022]`) e `2024` (train_years `[2022, 2023]`).
- Exemplo (primeiro registro, `context`, C=0.01, validação 2023): `n=18248`, `positives=738`, `constant.log_loss=0.17087086787939768`, `model.log_loss=0.1693086761130206`.
- Tamanho `n` por fold: 2023 = 18248; 2024 = 17740 (coerente com os parquets de desenvolvimento).

### 2.3 `development-v3/frozen_config.json`
Chaves de topo (9): `chosen_C`, `constant_prevalence`, `contract_sha256`, `dataset_sha256`, `design`, `design_sha256`, `models`, `notice`, `version`.
- `version` = `1` (inteiro, topo); `design.version` = `"qb-iw-research-v1"`.
- `chosen_C` = `{"context": 0.1, "depth": 0.1}`
- `constant_prevalence` = `0.04204015112230536`
- `contract_sha256` = `644bdde4bc9f753af85f64514b2d845433d4572075bae923737234ace4f8eb65` (confere com o `RESEARCH-CONTRACT.md` da worktree)
- `dataset_sha256` = `10e90375f22a187f361007e7db84a6f5bf2c81451171be4be4e805d7cc67c296`
- `design_sha256` = `4f22d1114408ccb112edcc27f64589d8bb1d232452fc4821f66a375157f48791`
- `models` = `{"context": "5dd05c66b8658e8d62253a9e4c2acf7348eb14a903cdd8d14c228d306da1fe5a", "depth": "933ab576c0df8292a2bc54952de1e98d759d4243177108fbaf98bc7b204b49ed"}`
- `notice` = "Created before first final temporal evaluation. No adjustment to 2025 performance permitted."
- `design` (chaves de 17): `C_grid` [0.01, 0.1, 1.0, 10.0]; `application` {season: 2026, weeks: [1, 7]}; `application_train` [2022, 2023, 2024, 2025]; `bootstrap_replicates` 2000; `calibration_edges` [0, 0.02, 0.03, 0.04, 0.05, 0.075, 0.1, 0.15, 0.25, 1] (9 bins); `environment` (texto: wind/temp/roof excluídos); `final_test` 2025; `final_train` [2022, 2023, 2024]; `folds` [{train: [2022], validation: 2023}, {train: [2022, 2023], validation: 2024}]; `max_iter` 2000; `posthoc_calibration` false; `seed` 20261104; `selection` (texto: log loss agregado ponderado por passe em 2023/2024, empate prefere menor C); `solver` "lbfgs"; `tol` 1e-9; `variants` ["context", "depth"]; `version` "qb-iw-research-v1".

### 2.4 `development-v3/environment.json`
Chaves: `code_hashes`, `packages`, `platform`, `python`.
- `python` = `"3.11.13"`; `platform` = `"macOS-26.6.2-arm64-arm-64bit"`
- `packages` = matplotlib 3.10.7, numpy 2.3.4, pandas 2.3.3, pyarrow 22.0.0, scikit-learn 1.7.2, scipy 1.16.3.
- `code_hashes` (6 arquivos, SHA-256 de `*.py` do diretório no momento da execução): `acquire.py` a74f23d3…, `dataset.py` 37b4fd79…, `evaluation.py` 2d9b16ee…, `model.py` 39a18d8f…, `pipeline.py` cd82d3b6…, `plots.py` 011b1a9c… (ver seção 4).

### 2.5 `development-v3/model_context_2022_2024.json` e `model_depth_2022_2024.json`
Chaves (ambos, 17): `C`, `categorical_columns`, `categories`, `category_imputation`, `coefficients`, `feature_names`, `format`, `intercept`, `iterations`, `mean`, `median`, `missing_indicators`, `numeric_columns`, `raw_features`, `scale`, `train_years`, `variant`.
- `format` = `"qb-iw-json-logistic-v1"`; `C` = `0.1`; `train_years` = `[2022, 2023, 2024]`.
- **context**: `intercept` = `-2.9772511514532063`; `coefficients` 18; `feature_names` 18 (`num__ydstogo` … `cat__qtr_5.0`); `numeric_columns` 9; `raw_features` 6; `categorical_columns` = `["down", "qtr"]`; `categories` = [[1,2,3,4],[1,2,3,4,5]]; `category_imputation` = [1.0, 2.0]; `missing_indicators` = []; `iterations` = 77.
- **depth**: `intercept` = `-3.2395464765184907`; `coefficients` 24; `feature_names` 24; `numeric_columns` 12; `raw_features` 7; `mean`/`scale` com 15 valores; `median` 12; `missing_indicators` 3 inteiros; `iterations` = 116.
- Hashes que batem com `frozen_config.models`: context `5dd05c66…` (igual), depth `933ab576…` (igual).

### 2.6 `development-v3/development_*.parquet` (4 arquivos)
Colunas idênticas nos 4 (6 colunas):
| coluna | dtype |
|---|---|
| `game_id` | string |
| `play_id` | double |
| `season` | int32 |
| `is_interception_worthy` | int64 |
| `probability` | double |
| `constant_probability` | double |

Linhas: `development_context_2023` = 18248; `development_context_2024` = 17740; `development_depth_2023` = 18248; `development_depth_2024` = 17740.

### 2.7 `evaluation-v1/metrics.json`
Estrutura: `{context|depth: {constant: {...}, model: {...}, paired_game_bootstrap: {brier: {delta, low, high}, log_loss: {delta, low, high}}}}`. Cada `constant`/`model` tem 9 chaves numéricas: `brier`, `expected`, `log_loss`, `mean_probability`, `n`, `positives`, `pr_auc_average_precision`, `prevalence`, `roc_auc`.

Valores reais (n = 17358, positives = 553, prevalence = 0.031858509044820835 em todos):

**context**
- constant: brier 0.03094721028165591; expected 729.7329431809765; log_loss 0.14254487019270104; mean_probability 0.04204015112230536; pr_auc 0.031858509044820835; roc_auc 0.5.
- model: brier 0.030873765589395377; expected 734.47074835571; log_loss 0.14120157433717448; mean_probability 0.042313097612381036; pr_auc 0.04476199597735799; roc_auc 0.5842720967506765.
- bootstrap (jogos pareados): brier delta -7.344469226052486e-05 [low -0.00018132020162608172, high 2.1316158774853603e-05]; log_loss delta -0.001343295855526507 [low -0.002376546117110872, high -0.0003814957790638184].

**depth**
- constant: idêntico ao constant do context.
- model: brier 0.03040904732062562; expected 736.8542942396208; log_loss 0.13438312216507275; mean_probability 0.042450414462473836; pr_auc 0.0774155937724455; roc_auc 0.702882172004909.
- bootstrap: brier delta -0.000538162961030278 [low -0.0008202011859857088, high -0.0002711232483639251]; log_loss delta -0.008161748027628231 [low -0.010355627453227587, high -0.0061380563336603765].

### 2.8 `evaluation-v1/calibration_context.json` (e `calibration_depth.json`)
- Tipo: lista de **9 bins** (edges de `design.calibration_edges`). Ambos têm 9.
- Chaves de cada bin: `bin`, `mean_probability`, `n`, `observed_rate`, `positives`, `wilson_high`, `wilson_low`.
- Exemplo (context, bin 2): `{"bin": "[0.02, 0.03)", "mean_probability": 0.027390179540959854, "n": 2283, "observed_rate": 0.02058694699956198, "positives": 47, "wilson_high": 0.027267675943381385, "wilson_low": 0.015516922692571362}`.
- Rótulos de bin: `"[0.0, 0.02)"`, `"[0.02, 0.03)"`, … (intervalo fechado à esquerda, aberto à direita).

### 2.9 `evaluation-v1/groups_context.json` (e `groups_depth.json`)
- Tipo: lista de **21 registros** (cada um de um grupo × valor).
- Chaves: `brier`, `constant_brier`, `constant_log_loss`, `expected`, `group`, `log_loss`, `mean_probability`, `n`, `positives`, `pr_auc_average_precision`, `prevalence`, `roc_auc`, `support_sufficient`, `value`.
- Grupos: `down` (4 valores: "1.0", "2.0", "3.0", "4.0"), `qtr` (5: "1.0"…"5.0"), `distance_group` (4: "1-3", "4-7", "8-10", "11+"), `score_group` (5), `roof` (3: "closed", "dome", "outdoors").
- `support_sufficient`: 20 `true`; **1 `false`** = `qtr` / `"5.0"` (n=101, positives=3).
- Exemplo (depth, down=1.0): `n` 6371, `positives` 148 (mesmo n em context e depth).

### 2.10 `evaluation-v1/coefficients_context.csv` e `coefficients_depth.csv`
- Colunas: `feature`, `coefficient_per_standardized_unit_or_category` (dtypes: object, float64).
- Linhas: context = **18**; depth = **24**. Mesmas linhas do `feature_names` do modelo JSON correspondente.

### 2.11 `evaluation-v1/test_predictions_context.parquet` e `_depth.parquet`
Colunas (8): `game_id` string; `play_id` double; `season` int32; `week` int32; `passer_player_id` string; `is_interception_worthy` int64; `probability` double; `constant_probability` double.
Linhas: **17358** cada.

### 2.12 `evaluation-v1/evaluation_receipt.json`
Chaves: `frozen_config_sha256` = `3add5c6113c91f720ae7dfde759617f114daf66f700b4ce7229c2efa21f3e90a`; `protocol` = "2025 single final temporal evaluation; later identical reruns are reproduction only"; `test_year` = `2025`.
(O hash confere com `sha256(S/development-v3/frozen_config.json)`.)

### 2.13 `application-v1/application_receipt.json`
Chaves: `expected_sum` = 282.18921288487985; `frozen_config_sha256` = `3add5c6113…`; `games` = 107; `observed` = 219; `passers` = 62; `passes` = 7106; `weeks` = [1,2,3,4,5,6,7].

### 2.14 `application-v1/application_diagnostics_context.json` (e `_depth.json`)
Chaves de topo: `calibration` (lista de 9 bins, mesmo formato de 2.8, por exemplo o bin `[0.0, 0.02)` com `n` 4) e `metrics_descriptive_only` (dict com as 9 chaves de métricas, mesmas de `metrics.json`).

### 2.15 `application-v1/model_context_2022_2025.json` e `model_depth_2022_2025.json`
Mesmas 17 chaves de 2.5. `C` = 0.1; `train_years` = `[2022, 2023, 2024, 2025]`.
- context `intercept` = `-3.0395405143059664`
- depth `intercept` = `-3.302425362175234`

### 2.16 `application-v1/qb_context.csv` (e `qb_depth.csv`)
- Colunas (16): `passer_player_id`, `names`, `teams`, `passes`, `games`, `observed`, `expected`, `observed_rate`, `expected_rate`, `difference_count`, `difference_per100`, `interceptions`, `ci_low_per100`, `ci_high_per100`, `ci_games`, `plot_convention_n100`.
- Linhas: **62** passers. Somas: `passes` = 7106; `observed` = 219; `expected` = 282.1892.
- Exemplo (primeira linha): `passer_player_id` `00-0023459`, `names` `A.Rodgers`, `teams` `PIT`, `passes` 260, `games` 7, `observed` 5, `expected` 9.9187, `plot_convention_n100` = `True`.
- `plot_convention_n100` = True em 32 de 62.

### 2.17 `application-v1/qb_sensitivity.csv`
- Linhas: 62. Colunas (32): `passer_player_id` + 15 colunas com sufixo `_context` + 15 com sufixo `_depth` + `adjustment_change_per100`. Gerado por merge `one_to_one` de `qb_context` e `qb_depth` (`pipeline.py` linhas 85).

### 2.18 `application-v1/application_predictions_context.parquet` e `_depth.parquet`
Colunas (10): `game_id` string; `play_id` double; `season` int32; `week` int32; `passer_player_id` string; `passer_player_name` string; `posteam` string; `is_interception_worthy` int64; `interception` double; `probability` double.
Linhas: **7106** cada.

### 2.19 `figures-v4/` (10 arquivos)
`calibration_2025.png` (250.457 B), `calibration_2025.svg` (163.619 B), `calibration_support.csv` (1.824 B), `depth_sensitivity_2026.png` (192.720 B), `depth_sensitivity_2026.svg` (141.360 B), `difference_per100_2026.png` (209.429 B), `difference_per100_2026.svg` (156.547 B), `observed_expected_2026.png` (289.536 B), `observed_expected_2026.svg` (187.583 B), `plot_passers.csv` (1.093 B).

### 2.20 `sources.json`
- Chaves de topo: `version` (1), `python` ("3.11.13"), `files` (lista de **20**), `notice` (texto: 2026 PBP é fonte local congelada aprovada, não download remoto; FTN pode ir além da W7 e a aplicação filtra).
- Chaves de cada registro em `files`: `path`, `url`, `acquired_at_utc`, `bytes`, `sha256`, `season`, `kind`, `headers`, `rows`, `games`, `weeks`, `schema`, `parquet_metadata`, `license`, `attribution`.

### 2.21 `reproduction-check.json`
- Chaves de topo: `comparison` ("byte SHA-256, same pinned Python dependencies and platform"), `files` (84), `network`, `passed` (**true**), `records` (84).
- Chaves de cada registro: `identical`, `original`, `reproduced_sha256`, `reproduction`, `sha256`.
- Comparados (`verify_reproduction.py` linhas 12–14): `build-v2` (todos os arquivos), `development-v3`, `evaluation-v1`, `application-v1`, `figures-v4`.

### 2.22 Outros arquivos de build (referência)
`build-v2/audit.json` (28 KB), `build-v2/splits.csv` (4,4 MB), `build-v2/audit/` (lista em `ls`: `aborted_{2022..2026}.csv`, `counts_by_{game,qb,season,week}.csv`, `distribution_{down,penalty_type,qtr,roof}.csv`, `eligible_{2022..2026}.parquet`, `environment_by_stadium.csv`, `feature_distributions.csv`, `identities.csv`, `name_collisions.json`, `no_play_worthy_{2022..2026}.csv`, `outside_eligible_{2022..2026}.parquet`, `penalty_{2022..2026}.csv`, `unknown_receiver_{2022..2026}.csv`).

---

## 3. SHA-256 (verificações pedidas)

| Arquivo | Hash calculado | Referência | Resultado |
|---|---|---|---|
| `S/build-v2/dataset.parquet` | `10e90375f22a187f361007e7db84a6f5bf2c81451171be4be4e805d7cc67c296` | `build_manifest.dataset_sha256` = `10e90375…`; `frozen_config.dataset_sha256` = `10e90375…` | **IGUAIS** (3 de 3) |
| `S/development-v3/frozen_config.json` | `3add5c6113c91f720ae7dfde759617f114daf66f700b4ce7229c2efa21f3e90a` | `evaluation_receipt.frozen_config_sha256` e `application_receipt.frozen_config_sha256` = `3add5c61…` | **IGUAIS** |
| `W/research/qb_interception_risk/design.json` | `4f22d1114408ccb112edcc27f64589d8bb1d232452fc4821f66a375157f48791` | `frozen_config.design_sha256` = `4f22d111…` | **IGUAL** |
| `W/docs/plans/qb-interception-risk-baseline-v1/RESEARCH-CONTRACT.md` | `644bdde4bc9f753af85f64514b2d845433d4572075bae923737234ace4f8eb65` | `frozen_config.contract_sha256` = `644bdde4…` | **IGUAL** |
| `S/development-v3/model_context_2022_2024.json` | `5dd05c66…` | `frozen_config.models.context` = `5dd05c66…` | **IGUAL** |
| `S/development-v3/model_depth_2022_2024.json` | `933ab576…` | `frozen_config.models.depth` = `933ab576…` | **IGUAL** |

---

## 4. Proveniência por commit e código

### 4.1 Commits que produziram os outputs (registrados em CHECKPOINTS.md)
- `3fd44b7` — fontes e população (contrato)
- `05c18ed` — reconciliação independente: `build-v2` (dataset sha `10e90375…`). `dataset.py` = `37b4fd79…`.
- `35ac931` — **freeze pré-teste**: `development-v3` (C=0.1, `frozen_config`). Este é o commit cujos hashes batem com `environment.json`.
- `910dfae` — avaliação 2025, aplicação 2026 e relatório. `evaluation-v1`, `application-v1`.
- `d654bd6` — HEAD atual da worktree da baseline (`codex/qb-interception-risk-baseline-v1`). Mudança em relação a `910dfae`: só adiciona `archive.py` (22 linhas). `pipeline.py`, `dataset.py`, `plots.py` iguais a `910dfae`.
- Commit de `figures-v4`: não encontrado nos docs nem no git.
- Nenhum dos docs (README/HANDOFF/CHECKPOINTS) grava o hash de commit em `environment.json`. Os commits foram lidos só via `git log`.

### 4.2 `code_hashes` de `development-v3/environment.json` vs. arquivos

| Arquivo | `environment.json` | Commit que bate | Worktree atual (W, mlflow-tracking-v1) | Igual? |
|---|---|---|---|---|
| `pipeline.py` | `cd82d3b60f59fe661706094af5495385057b96a036df0f837b6fe038cf2543d3` | `35ac931` (`cd82d3b6…`) | `431832e03d16d093dc357acfaff3425d26a3d54a4a41c0dbdda7860f9e1025eb` (= `910dfae`, `d654bd6`) | **NÃO** |
| `dataset.py` | `37b4fd793ccacc11406f7823f3545fffaa90e7aabe34aeaaa3f1f5bac15a8023` | `35ac931` e `05c18ed` (`37b4fd79…`) | `9a6f86b2259e97255d03ab8d500b15511b6d47a5d5312c8a8997f997c308d330` (= `910dfae`) | **NÃO** |
| `model.py` | `39a18d8ffe504f9bab87ccbb0dc87d3407d0f85bba3fb5dbd7c1308533fc5d80` | `35ac931`, `910dfae` | `39a18d8ffe504f9bab87ccbb0dc87d3407d0f85bba3fb5dbd7c1308533fc5d80` | **IGUAL** |
| `evaluation.py` | `2d9b16ee13ce4b98d28c90fab69e13d39eca76b15ab023577a7682ee3e8afe6c` | `35ac931`, `910dfae` | `2d9b16ee13ce4b98d28c90fab69e13d39eca76b15ab023577a7682ee3e8afe6c` | **IGUAL** |
| `acquire.py` | `a74f23d3bff0c87aaf1a6d8fa582c18e034df7ccc799c477e905286023f771bc` | `35ac931`, `910dfae` | `a74f23d3bff0c87aaf1a6d8fa582c18e034df7ccc799c477e905286023f771bc` | **IGUAL** |
| `plots.py` | `011b1a9c501a9edfe9c69b468883fcd75ad7c5d8f5a6bf5b08caedb2fa69ba1c` | **nenhum commit** (`35ac931` não tem `plots.py`) | `c7965333cf5ec7bd…` (= `910dfae`) | **NÃO** |

Leitura: `environment.json` foi escrito na execução do freeze (commit `35ac931`), quando `plots.py` existia só como arquivo não rastreado. A worktree atual tem a versão alterada em `910dfae`, que muda `pipeline.py` (o modo `reproduce` passou a chamar `develop` e checar o freeze, e `plots` foi chamado) e `dataset.py` (adicionou auditorias de distribuição e no_play). A mudança em `dataset.py` mexe na construção de `dataset.parquet`, mas o hash `dataset_sha256` continua igual ao do freeze, o que indica que a mudança não alterou o conteúdo do dataset (não verificado diretamente; é inferência a partir do hash). `model.py` e `evaluation.py` não mudaram desde `35ac931`.

### 4.3 Versão do código vs. saída
- `build-v2` → código de `05c18ed` (dataset sha `10e90375…`).
- `development-v3` → código de `35ac931` (`pipeline.py`, `dataset.py`, `model.py`, `evaluation.py`, `acquire.py` exatos) + `plots.py` não rastreado.
- `evaluation-v1`, `application-v1`, `figures-v4` → código de `910dfae` (e `d654bd6`, sem alteração nesses arquivos). Nenhum `environment.json` foi gravado em `evaluation-v1`.

---

## 5. Não encontrado

- Hash de commit gravado dentro de qualquer arquivo do store: **não encontrado** (só nos docs e via `git log`).
- `environment.json` em `evaluation-v1`, `application-v1`, `build-v2`: **não encontrado**.
- Hash do `plots.py` que gerou `figures-v4`: **não encontrado** (nenhum commit tem `011b1a9c…`).
- Commit de `figures-v4`: **não encontrado**.
- Parquets com hashes de linha/conteúdo por arquivo em `build-v2/dataset.parquet` (colunas e dtypes não lidos nesta rodada; só o SHA foi pedido).
- Documentação que confirme `figures-v4` como canônica: **não encontrado** em README/HANDOFF/CHECKPOINTS (o README diz `figures-v3`; o `verify_reproduction.py` e o `reproduction-check.json` usam `figures-v4`).
- Não foram lidos `REPORT.md`, `MODEL-CARD.md`, `DATA-AUDIT.md` nem o conteúdo de `evidence/` (fora do escopo pedido).
