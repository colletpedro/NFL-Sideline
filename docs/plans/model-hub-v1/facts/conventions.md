# Fatos e convenções — hub de modelos (mlflow-scout)

Worktree: `/Users/pedrocollet/Downloads/NFL Sideline/.claude/worktrees/model-hub-v1` (branch `codex/model-hub-v1`).
Somente leitura: nenhum teste, build, rede ou `.env` foi tocado. Referências `arquivo:linha` são relativas à worktree.
Onde a linha não foi conferida isso está dito explicitamente.

---

## 1. Convenções dos pacotes `research/qb_*`

### 1.1 `research/qb_expected_interceptions` (principal)

**Arquivos** (`research/qb_expected_interceptions/`): `common.py`, `data.py`, `risk_model.py`, `evaluate.py`, `run.py`, `acquire.py`, `archive.py`, `update.py`, `isolation.py`, `reproduce.py`, `figures.py`, `write_docs.py`, `config.json`, `consumer-contract.json`, `requirements.lock`, `tests/{conftest.py,test_research.py}`. Não há `requirements.txt` nem `.gitignore` próprio.

**Dependência de outro pacote**: `common.py:16-18` faz `sys.path.insert(0, ROOT/'research/qb_interception_risk')` e importa `dataset` (FILTERS, KEY, unique) e `model` (features, RAW, NUM, CAT) de lá. Ou seja, o `expected_interceptions` reutiliza o `qb_interception_risk` (congelado).

**Caminhos fixos (hard-coded)** em `common.py`:
- `common.py:6-7`: `HERE`, `ROOT = HERE.parents[1]`.
- `common.py:8`: `DOC = ROOT/'docs/plans/qb-expected-interceptions-v1'`.
- `common.py:9`: `BASE = '5d7d7769ce71a6864edce4c7393a75913563595f'`.
- `common.py:10`: `MAIN = Path('/Users/pedrocollet/Downloads/NFL Sideline')` (absoluto, não via env).
- `common.py:11`: `APPROVED = Path('/Users/pedrocollet/.codex/worktrees/...')` (absoluto).
- `common.py:12`: `STORE = MAIN/'editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1'`.
- `common.py:13-15`: `V1`, `V2`, `LAB` (também absolutos sob MAIN).
- Observação: GUARDRAILS proíbe novos caminhos absolutos fixos; este pacote é congelado, então não se edita, mas não é modelo a copiar.
- `qb_risk_temporal_v2` não tem variável de ambiente (`NFL_RESEARCH_STORES`) — `grep` não achou nenhuma ocorrência de `NFL_RESEARCH_STORES`/`NFL_MLFLOW_HOME` em `research/qb_*` fora de `mlflow_tracking`.

**Como lê os dados** (de onde vêm PBP e schedules):
- Não lê `etl-pipeline/data/raw`. Lê o **store científico** em `MAIN/editorial/local-artifacts/...` por `--store` (padrão `common.py:12`, argumento em `run.py:164-175` `main()`, `--store default=str(STORE)`).
- `data.py:151-184` `build(store, out)`:
  - `data.py:152`: `verify_manifest(store)` (confere `sources.json`, `common.py:42-50`).
  - `data.py:154`: `lineage/historical-dataset.parquet` (população histórica, comparada por `assert_frame_equal` em `data.py:164-166`).
  - `data.py:156`: `base = store/'current'` se ano 2026, senão `store/'raw'`.
  - `data.py:157-158`: `pbp_{year}.parquet` / `ftn_{year}.parquet` (2022–2025 em `raw/`); 2026 usa `current/pbp.parquet` e `current/ftn.parquet`.
  - `data.py:161`: `current/schedule.csv` (só 2026), via `current_frames(p, f, schedule)` (`data.py:31-66`), que aplica o gate de jogos encerrados (272 jogos REG; `data.py:36`).
  - `data.py:173`: `rosters/{y}.parquet` para 2022–2026 (`identities`, `data.py:123`).
  - Saídas: `dataset.parquet`, `manifest.json` (`dataset_sha256`, `sources_sha256`), `audit/*`, `coverage.json`, `splits.csv`, `revision.json` (`data.py:175-184`).
- `data.py:68-102` `independent(p,f,d)`: reconciliação SQL independente com `sqlite3` (`data.py:2`) em memória.
- `data.py:13-20` `join(p,f)`: join PBP–FTN por `KEY` com `validate='one_to_one'`.
- `data.py:22-29` `validate_rows(d)`: faixas de contexto, GSIS `00-\d{7}`, placar pré-jogada.
- `qb_interception_risk/dataset.py:82-146` (pacote de origem, congelado): mesmo padrão `store/'raw/schedules.csv'`, `raw/pbp_{year}.parquet`, `raw/ftn_{year}.parquet` (`dataset.py:87-89`).

**Requirements/pins** (`requirements.lock`, pins exatos): cloudpickle 3.1.2, contourpy 1.3.3, cycler 0.12.1, fonttools 4.68.0, iniconfig 2.3.1, joblib 1.6.0, kiwisolver 1.5.1, matplotlib 3.10.7, numpy 2.3.4, packaging 26.3, pandas 2.3.3, pillow 13.0.0, pluggy 1.7.0, pyarrow 22.0.0, Pygments 2.21.0, pyparsing 3.3.3, pytest 8.4.2, python-dateutil 4.0.0, pytz 2026.6, scikit-learn 1.7.2, scipy 1.16.3, threadpoolctl 3.7.0, tzdata 2026.6. Python não fixado no lock (CI usa 3.11).
- O mesmo arquivo (md5 `94063bc7…`) é idêntico ao de `qb_interception_risk`, `qb_risk_temporal_v2` e `qb_risk_lab`. `mlflow_tracking/requirements.lock` é diferente (md5 `45bdafa8…`).

**Folds temporais** (expanding window):
- `risk_model.py:47-52` `blocks(d, year)`: treino = `season < year and season >= 2022` (janela expansiva ancorada em 2022); avaliação = `season == year`. Checa `check_train` (`risk_model.py:43-45`: `season < evaluation_year`, não vazio, alvo binário), disjunção de `game_id` (`:50`) e de datas (`:51`).
- `config.json`: `development_years: [2023, 2024]`, `evaluation_year: 2025`, `application_year: 2026`, `C_grid: [0.01, 0.1, 1.0]`, `seed: 20261105`, `bootstrap_replicates: 2000`, `selection` (texto da regra).
- `run.py:34-68` `develop(build,out)`: para cada ano de desenvolvimento, `blocks(d[d.season.le(2024)], year)` (`run.py:37-38`); seleciona C por log-loss agregado (`run.py:45-48`); promove C só com `useful` (`run.py:50-51`: calibração O/E em [0.8,1.25] e bootstrap upper95<0 vs B1 e B2); senão B1/B2 (`run.py:52-53`). Modelo de avaliação: `train = d[d.season.between(2022,2024)]` (`run.py:60`).
- `run.py:85-93` `evaluate`: `blocks(d,2025)` (`run.py:17`); guarda `train_years < 2025` (`run.py:19`).
- `run.py:94-106` `refit`: treino `season.between(2022,2025)` (`run.py:26`), ajuste nunca no `update`.
- `risk_model.py:30-41` `fit_reference(train, kind, evaluation_year)`: B0/B1/B2; B2 usa só `season == evaluation_year-1` (`risk_model.py:33`).
- Regra de taxa: `risk_model.py:24-28` `rate(y)` (suporte `(k+0.5)/(n+1)` quando `k∈{0,n}`).

**Gravação de stores** (`run.py`, `common.py`):
- `common.py:34-40` `new_dir(path)`: recusa destinos protegidos (APPROVED, V1, V2, LAB, `ROOT/web-ui`, `MAIN/web-ui`; `common.py:36-37`) e diretório existente (`:38`), cria com `mkdir(parents=True)`. Não sobrescreve.
- `common.py:20-24` `sha(path)` (SHA-256 em blocos de 1 MiB); `common.py:26-29` `write(path,value)` (JSON `sort_keys=True, indent=2, allow_nan=False`).
- Saídas de `develop` (`run.py:34-68`): `models/{B0,B1,B2}_{year}.json`, `models/C_{C}_{year}.json`, `selection.json`, `development/` (`metrics.csv`, `calibration.csv`, `paired_bootstrap.json`, `pass_predictions.parquet`, `players_*.csv`), `metrics_{year}.csv`, `evaluation_models/{k}.json`, `freeze.json` (format `xint-research-freeze-v1`, com `config_sha256`, `contract_sha256`, `code_sha256` por arquivo, `evaluation_model_hashes`), `environment.json`.
- `run.py:70-83` `verified_freeze(development)`: confere `config.json`, `RESEARCH-CONTRACT.md` e hashes de código; a única exceção é reparo de saída registrado em `DOC/'evidence/output-fix.json'` (`run.py:7-11`).
- `run.py:38-43` `load_fixed(final)`: confere `fixed.json` (`model_sha256`) e `code_sha256`.
- `run.py:114-143` `package(...)` grava `players.csv`, `pass_predictions.parquet`, `metrics.csv`, `calibration.csv`.
- `run.py:161-163` `apply`: aplica modelo fixo (sem fit), `train_years` < 2026.
- `run.py:166-177` `main()`: subcomandos `build|develop|evaluate|refit|apply`; chama `offline()` (`common.py:64-68`, bloqueia `socket.connect`).
- `archive.py`, `update.py`, `reproduce.py`, `isolation.py` existem; não foram lidos em detalhe (não verificado).

**Testes** (`tests/`):
- `tests/conftest.py:6-11`: fixture `prohibit_test_downloads` (autouse) bloqueia `socket.connect` e `create_connection`.
- `tests/test_research.py`:
  - `:10-24` fixture `current` (2026 sintético, 272 jogos, GSIS `00-0000001`).
  - `:26-38` fixture `passes`: `np.random.default_rng(71)`, 240 passes sintéticos (2022, semanas 1–2).
  - Testes principais: `:42` join/cardinalidade; `:52` elegibilidade parametrizada; `:60-69` alvo/identidade faltando sem imputação; `:75` blocos temporais; `:82` pré-processamento só treino e colunas proibidas; `:139-140` checagem de não importação de `web-ui/src`, `etl-pipeline/src`, `core-api/src`; `:145` jogo parcial; `:162` update aplica modelo fixo sem fit; `:182` hash de modelo fixo errado recusado.
- **Sem marcador `real_store`** neste pacote (grep em `research/` achou o marcador só em `mlflow_tracking`).

### 1.2 `research/qb_risk_temporal_v2` (principal)

**Arquivos**: `common.py`, `prepare.py`, `experiment.py`, `reserved.py`, `drift.py`, `identity.py`, `calibration_stats.py`, `figures.py`, `run.py`, `reproduce.py`, `isolation.py`, `archive.py`, `acquire_reserved.py`, `write_report.py`, `protocol.json`, `requirements.lock` (md5 igual ao do expected), `tests/{conftest.py,test_temporal.py}`, `.gitignore` (`.venv/`).

**Reuso do v1 congelado**: `common.py:4-6` insere `qb_interception_risk` no `sys.path` e importa `acquire.sha`, `dataset.{dump,verify_sources}`, `model.{fit,features,export_model,predict_json}`, `evaluation.{metrics,calibration,paired_game_bootstrap,groups}`, `pipeline.{load_dataset,destination}`. Diz explicitamente "reuse the immutable v1 implementation, never fork its model" (`common.py:1`).

**Leitura de dados**:
- Entrada = store (`--store`, `run.py`/`experiment.py:47`), não `etl-pipeline`.
- `prepare.py:19-33`: copia `raw`, `documentation`, `sources.json`, `development-v3` do v1 para `inputs/v1/` (cópia, nunca muta a original); verifica por `verify_sources`.
- `prepare.py:31-33`: copia `evaluation-v1/test_predictions_context.parquet` e `application-v1/application_predictions_context.parquet`.
- `prepare.py:52`: única aquisição nova = `inputs/roster_weekly_2026.parquet` (URL GitHub nflverse); `prepare.py:6-18` URLs de docs (`DOCS`). Não busca PBP/FTN novos (`prepare.py:54`, `no_new_pbp_or_ftn_acquired=True`).
- `experiment.py:48-53`: verifica `inputs/v1` e `additional-sources.json`; exige `reference-v1-check.json` com `passed` (`:53-54`); carrega `load_dataset(reference/'build')` (`:55`).
- `experiment.py:60-61`: lê predições preservadas do v1 (`development_context_2024.parquet`, `test_predictions_context.parquet`, `application_predictions_context.parquet`).
- `experiment.py:92`: `inputs/v1/raw/schedules.csv`.
- `experiment.py:96`: `inputs/roster_weekly_2026.parquet`.

**Folds temporais** (`common.py`, `experiment.py`):
- `common.py:15-19` `known_only(d)`: só 2022–2026 e 2026 apenas semanas 1–7; só REG (`:17-18`).
- `common.py:21-31` `blocks(d, train_years, cal_year, eval_year)`: `max(train_years) < cal_year < eval_year` quando há calibração (`:23`); treino = `season.isin(train_years)`; calibração = `season == cal_year`; avaliação = `season == eval_year`; bloqueia jogos compartilhados (`:27`) e sobreposição de datas (`:30`).
- `experiment.py:28-29` `candidate_blocks(year)`: para 2024 → treino `[2022]`, calibração 2023; para 2025/2026 → `[year-3, year-2]`, calibração `year-1` (**janela deslizante de 2 anos**, não expansiva, para M3).
- `experiment.py:58` `blocks(d,[previous],None,year)` com `previous = year-1` (M1, M2 = só ano anterior).
- `experiment.py:80`: papel temporal de M0 = `range(2022, year)` (expansiva), M1/M2 = `[previous]`, M3 = `years`.
- Anos avaliados: `protocol.json` `known_evaluation_years: [2024, 2025, 2026]`; seleção `selection_years: [2024, 2025]` (`experiment.py:31-45` `select`, guarda `known_only`).
- Reservado: `protocol.json` `reserved: {season 2026, weeks [9,13], maturity_days_after_latest_kickoff: 8}`. `reserved.py:21-38` `maturity(...)`: `not_before = latest_kickoff_utc + 8 dias` (fuso America/New_York, `:30`); recusa antes disso sem abrir PBP/FTN (`:33`). `reserved.py:40-50` `validate_bundle` confere `freeze.json` (hashes de arquivos e de código).

**Gravação de stores**:
- `experiment.py:47-48` `run(store, out, reference_dir=None)`: `out = destination(out)` (de `pipeline.py` do v1, não lido em detalhe).
- Saídas (`experiment.py:56-99`): `models/{M1,M2,M3}_{year}.json` (+ `M0` implícito), `predictions.parquet`, `splits.parquet`, `metrics.json`, `calibration_bins.json`, `groups.csv`, `selection.json`, `frozen/{M0.json,M1.json,<candidato>.json,reserved_schedule.csv,freeze.json}`, `drift/`, `environment.json` (`:97`).
- `experiment.py:88-95` `frozen/freeze.json`: `version: 2`, `selected`, `references: ['M0','M1']`, `reserved`, `contracts` (hash de `protocol.json` e dos documentos `docs/plans/qb-risk-temporal-calibration-v2/*`), `code_hashes` (inclui `V1_CODE/model.py` e `dataset.py`), `dataset_sha256`, `files` (sha de cada arquivo em `frozen/`), `status: 'awaiting_mature_reserved_window; no independent confirmation yet'`.
- Sem `.pkl`: modelos são JSON (`experiment.py:18` usa `export_model`, `predict_json`).
- Congelamento: hashes em `freeze.json`; qualquer mudança quebra `validate_bundle` (`reserved.py:40-50`).

**Testes** (`tests/`):
- `tests/conftest.py`: só ajusta `sys.path` (`:3`). Sem fixture de rede autouse.
- `tests/test_temporal.py`: fixture `data` (`:14-20`, `np.random.default_rng(83)`, 2022–2026 × 160 linhas sintéticas); `schedule()` (`:22-23`, 2026 semanas 9–13).
- Testes: `:25` blocos e jogos; `:32` `reserved` nunca seleção (parametrizado); `:41` prematuridade; `:53-62` guarda antes de ler parquet (monkeypatch que falha); `:99` sem avanço, sem promoção, 2026 excluído; `:110` reabertura de labels recusada; `:121` adulteração de manifesto; `:131` caminhos do v1 não modificados; `:137` aquisição futura recusa rede antes da maturidade.
- **Sem marcador `real_store`** (grep não encontrou). Não rodei.

### 1.3 Outros pacotes (resumo, sem leitura detalhada)
- `research/qb_interception_risk/`: pipeline do v1 (`dataset.py`, `model.py`, `evaluation.py`, `pipeline.py`, `plots.py`, `write_docs.py`, `design.json`, `requirements.lock`/`requirements.txt`, `tests/`). Caminhos de dados: `dataset.py:82-89`.
- `research/qb_risk_lab/`: `requirements.lock` (usado por `qb_risk_outcomes_lab`, `qb_progression_lab`, `qb_structure_production`) e `test_pipeline.py`.
- `research/qb_risk_outcomes_lab/`, `research/qb_progression_lab/`, `research/qb_structure_production/`: testes com caminhos absolutos para stores reais; CI os roda com `--deselect` (ver §3).

---

## 2. `research/mlflow_tracking/`

### 2.1 `tracking.py` (217 linhas)
Constantes:
- `tracking.py:17` `IMPORTER_VERSION = "0.1.0"`.
- `tracking.py:19-24` `EXPERIMENTS = {"v1": "qb-iw-baseline-v1", "v2": "qb-risk-temporal-v2", "xint": "xint-ftn-v1", "smoke": "mlflow-tracking-smoke"}`.
- `tracking.py:25` `MODELS = {"m3": "qb-iw-m3", "b2": "xint-ftn"}`.
- `tracking.py:27-39` `REQUIRED_TAGS` (11): `source_store, source_freeze_sha256, dataset_sha256, design_sha256, seed, git_commit, git_dirty, importer_version, importer_code_sha256, imported_at_utc, role`.
- `tracking.py:41-42` `MODULE_DIR`, `MODULE_PATHSPEC = ":/research/mlflow_tracking"`.

Funções públicas:
- `tracking.py:61` `mlflow_home() -> Path`: `NFL_MLFLOW_HOME` ou `main_checkout()/editorial/local-artifacts/mlflow`.
- `tracking.py:68` `stores_root() -> Path`: `NFL_RESEARCH_STORES` ou `main_checkout()/editorial/local-artifacts`.
- `tracking.py:80` `configure(home: Path | None = None) -> Path`: cria `home/artifacts`, aponta tracking e registry para o mesmo SQLite (`sqlite:///<home>/mlflow.db`, `tracking.py:75-77`), retira o experimento Default (`_retire_default_experiment`, `:98-110`).
- `tracking.py:113` `ensure_experiment(key_or_name: str, home: Path) -> str`: cria ou confere experimento com `artifact_location` em `home/artifacts/<name>`; restaura se deletado; `RuntimeError` se o location diverge (`:124-127`).
- `tracking.py:134` `git_info(path: Path) -> dict`: `commit`, `branch`, `dirty` (só o pathspec do módulo); fallback `"unknown"`.
- `tracking.py:164` `base_tags(source_store, source_freeze_sha256, dataset_sha256, design_sha256, seed, role, repo_path, importer_file=None, imported_at=None) -> dict`: monta as 11 tags (todas str) e chama `validate_tags`.
- Auxiliares: `_git` (`:45`), `main_checkout(start=None)` (`:52`, pai do `--git-common-dir`), `tracking_uri(home)` (`:75`), `_local_path` (`:92`), `importer_code_sha256(importer_file=None)` (`:147`, SHA de `tracking.py` + `importer_base.py` + importador), `validate_tags(tags)` (`:158`), `find_parents(experiment_id, source_freeze_sha256, client=None)` (`:194`, pais FINISHED com `role='parent'`, ordenados), `find_parent(...)` (`:212`, o mais recente ou None).

### 2.2 `registry.py` (495 linhas)
- Constantes: `ALIAS = "champion"` (`:31`); `CODE_DIR` (`:33`); `FROZEN_V1_MODEL_PY` (`:35`); `M3_JSON_SHA` (`:37`), `V1_MODEL_PY_SHA` (`:38`), `B2_JSON_SHA` (`:39`); `V2_STORE = "qb-risk-temporal-calibration-v2/20261104-v2"` (`:41`); `V1_STORE = "qb-interception-risk-baseline-v1/20261104-v1"` (`:42`); `XINT_STORE = "qb-expected-interceptions-v1/20261105-v1"` (`:43`); `M3_COLUMNS` (`:44`); `PINNED = ("numpy","pandas","scipy","scikit-learn")` (`:45`); `BAD_SUFFIXES = (".pkl",".pickle",".joblib")` (`:46`).
- `registry.py:49` `class RegistryError(RuntimeError)`.
- `registry.py:53` `sha256_file(path) -> str`; `:61` `_require(cond, msg)`; `:66` `pinned_requirements(lock=None) -> list[str]` (lê pins de numpy/pandas/scipy/scikit-learn do lock).
- `registry.py:79` `_specs(stores) -> dict` (`m3` e `b2`: `model_name`, `experiment`, `store`, `json_path`, `json_sha`, `freeze_path`, `code`, `code_paths`, `extra_tags`, `input_columns`).
  - m3: `json_path = V2/experiment-verified/frozen/M3.json`; `freeze_path = .../frozen/freeze.json`; `code = model_code/m3_pyfunc.py`; `code_paths=[FROZEN_V1_MODEL_PY]`.
  - b2: `json_path = XINT/final/model.json`; `freeze_path = XINT/development/freeze.json`; `code = model_code/b2_pyfunc.py`; `code_paths=[]`.
- `registry.py:99` `_signature(key)`; `:107` `_frame`; `:114` `_m3_2026`; `:125` `_b2_2026`; `:129` `_input_example`; `:141` `_find_version`; `:153` `_run_active`; `:163` `_version_source_is_live`; `:178` `discard_model_run(client, name, run_id, home)`; `:229` `_purge_orphans`; `:265` `_is_model_run`; `:272` `_set_alias`.
- **`registry.py:281` `register_one(key: str, home: Path | None = None, stores: Path | None = None) -> dict`**: confere sha do JSON e do código (`:287-290`), `tracking.ensure_experiment` (`:17` do fluxo), exige pai importado via `tracking.find_parent` (`:28-29`), cria `base_tags(..., "model", ...)` (`:31-33`), `mlflow.start_run`, `mlflow.pyfunc.log_model(name=..., python_model=<code>, artifacts={"model_json": ...}, code_paths, signature, input_example, pip_requirements=pinned_requirements(), registered_model_name=...)` (`:41-44`), seta alias `champion` (`:51`); em falha, `discard_model_run` (`:52-58`). Retorna `{"model","version","run_id","created"}` (`:59`).
- `registry.py:342` `register(which="all", home=None, stores=None) -> dict[str, dict]`; `:411` `verify_models(home=None, stores=None) -> list[str]` (recarrega `models:/<nome>@champion` e confere previsões/hashes).
- Observação: `registry.py:28-29` faz `import importer_base` e `import tracking` (módulos planos; exige `research/mlflow_tracking` no `sys.path`, feito pelo `conftest.py:9`).

### 2.3 `model_code/b2_pyfunc.py` (40 linhas)
- Padrão "models from code" (MLflow `set_model`), sem pickle.
- `b2_pyfunc.py:17` `INPUT_COLUMNS = ["is_interception_worthy"]`.
- `b2_pyfunc.py:20` `class B2Model(PythonModel)`.
- `b2_pyfunc.py:21-31` `load_context(self, context)`: lê `context.artifacts["model_json"]` (`:22`); valida `format="xint-ftn-reference-v1"`, `kind="B2"`, `target="interception"`, `risk_input="is_interception_worthy"` (`:23-27`); exige grupos `'0'` e `'1'` (`:29-30`); guarda `self.prob`.
- `b2_pyfunc.py:33-37` `predict(self, context, model_input: TypeFromExample, params=None)`: exige valores binários (`:35-36`) e devolve `np.array` de probabilidades por grupo FTN.
- `b2_pyfunc.py:40` `set_model(B2Model())`.
- Artefato: `model_json` (= `xint/final/model.json`, sha `ebc588e7…` em `registry.py:39`).

### 2.4 `model_code/m3_pyfunc.py` (68 linhas, lido só por grep)
- `m3_pyfunc.py:27` `_sha256`; `:31` `_find_frozen_model_py(model_json_path)` (procura `<modelo>/code/model.py` pelo hash congelado `FROZEN_MODEL_PY_SHA256`, `:31-38`); `:41` `_load_frozen_module(path)` (carrega o `model.py` congelado do v1 por `spec_from_file_location`); `:52` `class M3Model(PythonModel)`; `:55` `load_context` (lê `model_json`, carrega módulo congelado, `:55-61`); `:62` `predict`.
- Não li o corpo completo de `predict`.

### 2.5 Demais módulos e testes (existência)
- Módulos: `cli.py` (176), `compare.py` (649), `import_v1.py` (331), `import_v2.py` (336), `import_xint.py` (388), `importer_base.py` (335), `integrity.py` (119), `provenance.py` (184), `conftest.py` (44).
- Testes em `tests/`: `test_registry.py`, `test_provenance.py`, `test_hardening.py`, `test_import_v1.py`, `test_import_v2.py`, `test_import_xint.py`, `test_tracking.py`, `test_compare.py`, `rebuild_helper.py`.
- Marcador `real_store` definido em `conftest.py:14` e usado em: `test_registry.py:376`, `test_provenance.py:191`, `test_compare.py:540`, `test_import_v1.py:314`, `test_import_v2.py:399`, `test_import_xint.py:484`. Skip: `test_import_v1.py:315` (`skipif` por `reproduction-check.json`), `test_import_v2.py:400` (`skipif` por `v1-lineage.json`), `test_import_xint.py:485` (`skipif` por `output-fix.json`), `test_registry.py:380` (`pytest.skip("stores reais ausentes")` no corpo). Os demais skips não verificados.
- `conftest.py:21-44` `isolated_mlflow` (autouse): `NFL_MLFLOW_HOME` em `tmp_path`, `chdir` para cwd vazio, `tracking.configure(home)`, limpa URIs ao final.
- `README.md`: `python3.11 -m venv research/mlflow_tracking/.venv`; `pip install -r requirements.txt`; `cli.py smoke`.
- `requirements.txt` (pins): mlflow 3.17.2, numpy 2.3.4, pandas 2.3.3, pyarrow 22.0.0, scikit-learn 1.7.2, scipy 1.16.3, matplotlib 3.10.7, pytest 8.4.2.
- `requirements.lock` (`pip freeze`, ~110 pins): inclui mlflow 3.17.2, mlflow-skinny/tracing 3.17.2, SQLAlchemy 2.1.9, alembic 1.20.1, fastapi 0.165.0, uvicorn 0.54.0, skops 0.16.0, pydantic 2.14.4, protobuf 7.36.2, opentelemetry 1.45.2, cloudpickle 3.1.3 (difere de 3.1.2 dos pacotes qb_*), python-dateutil 2.9.0.post0 (difere de 4.0.0 dos qb_*).

---

## 3. `.github/workflows/research-ci.yml` (resumo)

- Nome: "Research CI". Gatilhos: `push` e `pull_request` com paths `research/**` e o próprio workflow; `workflow_dispatch`. `permissions: contents: read`.
- **Job `mlflow-tracking`** ("mlflow_tracking (sintético)"), `ubuntu-latest`, timeout 20 min, `MLFLOW_DISABLE_AGENT_HINT=1`:
  1. `actions/checkout@v4`.
  2. `actions/setup-python@v5` Python 3.11, cache pip com `cache-dependency-path: research/mlflow_tracking/requirements.lock`.
  3. `pip install -r research/mlflow_tracking/requirements.lock`.
  4. Teste: env `NFL_RESEARCH_STORES=${{ runner.temp }}/no-stores` e `NFL_MLFLOW_HOME=${{ runner.temp }}/mlflow-home`; `python -m pytest research/mlflow_tracking -q -rs` (sem deselect; `real_store` pula sozinho).
- **Job `experiments`** (nome `${{ matrix.name }}`), `ubuntu-latest`, timeout 30 min, `fail-fast: false`, `MLFLOW_DISABLE_AGENT_HINT=1`. Matrix (7 itens):
  1. `qb_interception_risk` → lock `research/qb_interception_risk/requirements.lock`, tests `research/qb_interception_risk/tests`.
  2. `qb_risk_temporal_v2` → lock próprio, tests `research/qb_risk_temporal_v2/tests`.
  3. `qb_expected_interceptions` → lock próprio, tests `research/qb_expected_interceptions/tests`.
  4. `qb_risk_lab` → lock `research/qb_risk_lab/requirements.lock`, tests `research/qb_risk_lab/test_pipeline.py`.
  5. `qb_risk_outcomes_lab` → lock do `qb_risk_lab`, tests `research/qb_risk_outcomes_lab/test_package.py`, **deselect de 4 testes**: `test_scientific_keys_and_probabilities_preserved`, `test_publication_determinism_and_m3_pointer_untouched`, `test_failure_before_atomic_commit_preserves_valid_pointer_and_old_version`, `test_missing_charting_never_imputed_and_manifest_tampering_fails` (motivo no YAML: `baseline` lê store real por caminho absoluto).
  6. `qb_progression_lab` → lock do `qb_risk_lab`, tests `research/qb_progression_lab/test_package.py`, **deselect de 2 testes**: `test_all_categories_preserved_and_main_exact`, `test_replay_failure_keeps_pointer_and_recovers`.
  7. `qb_structure_production` → lock do `qb_risk_lab`, tests `research/qb_structure_production/test_structure.py`, sem deselect.
- Passos do job `experiments`: `actions/checkout@v4` com **`fetch-depth: 0`** (comentário: `qb_risk_temporal_v2` compara com commit-base `d654bd6` via `git diff`); setup Python 3.11 com cache pip no lock do matrix; `pip install -r ${{matrix.lock}}`; teste com as mesmas env vars (`NFL_RESEARCH_STORES`, `NFL_MLFLOW_HOME`) e `python -m pytest ${{matrix.tests}} ${{matrix.deselect}} -q -rs`.
- Versões de Python: 3.11 em todos os jobs. Nenhuma matriz de versões de Python.
- Observação verificada: `qb_*` não lê `NFL_RESEARCH_STORES` (grep vazio); os caminhos são absolutos (`common.py:10-15`), então as env vars do CI não afetam os pacotes `qb_*`.

---

## 4. Contrato público: `docs/static-snapshot-contract.md` (97 linhas)

- Frase de escopo: `schemaVersion: 1` atual; "mudanças incompatíveis exigem nova versão e suporte explícito no cliente" (linha 3). O frontend de Production lê só `web-ui/public/data` (linha 3).
- Publicação (linha 7): rollout estático concluído em 2026-09-14; URLs canônicas Vercel; sem backend público, Cloud Run, `/api/v1`, Supabase ou Gemini.
- Conteúdo publicado (linha 9): temporada 2026, 272 jogos, semanas 1–18, 32 times, 112 mercados válidos, 160 sem mercado, 8 análises públicas.

**`/data/manifest.json`** (seção "Manifesto", linhas 11–18). Campos de topo:
- `schemaVersion` (inteiro, `1`);
- `generatedAt` (timestamp ISO-8601 UTC);
- `defaultSeason` (temporada aberta por default);
- `seasons` (inteiros, únicos, crescentes).
Tabela (linha 58): `Manifest: schemaVersion: integer, generatedAt: timestamp, defaultSeason: integer, seasons: integer[]`.

**`/data/seasons/{season}.json`** (linhas 20–36). Campos de topo:
- `schemaVersion`, `season`, `generatedAt`;
- `teams` (ordem de `teamAbbr`);
- `games` (ordem de semana, data, `gameId`);
- `metricsByTeam` (mapa ordenado por abreviação; séries ordenadas por semana);
- `analysesByGame` (mapa por `gameId`, no máximo uma análise `matchup` válida, a mais recente).
Tabela (linhas 59–65): `SeasonSnapshot`, `Team`, `Game` (~27 campos, incluindo `market: Market?`), `Market` (`homeImpliedRaw`, `awayImpliedRaw`, `homeImpliedFair`, `awayImpliedFair`, `vigPct`, `computedAt`), `Metric` (`season`, `week`, `teamAbbr`, `offEpaPlay`, `offEpaPass`, `offEpaRush`, `defEpaPass`, `defEpaRush`, `dropbackRate`, `playsOffense`), `Analysis` (`gameId`, `analysisType: "matchup"`, `createdAt`, `fatorChave`, `vantagemTatica`, `alertaVermelho`, `veredito`).
- Campos opcionais aparecem como `null` (linha 66); `result` = `homeScore - awayScore` (linha 66).

**Regras de compatibilidade/garantias** (linhas 30–50, 68–72):
- Calendário independe de mercado (`market: null` é publicável, linha 32).
- Par de moneylines atômico; ausência preserva a última cotação completa (linha 32).
- Análise só entra se `analysisCacheId` aprovado em `editorial/analysis-selections.json` e hashes conferem (linhas 38–43).
- Manifesto raiz inválido aborta antes do writer; `selections: []` é válido; o manifesto nunca é copiado para `web-ui/public` (linhas 48–50).
- Exportador: 3 consultas por temporada; nunca serializa entidades JPA (linha 70); escrita em diretório temporário irmão e troca atômica com restauração (linha 72); preserva arquivos quando só `generatedAt` mudaria (linha 72).

**Proibido expor** (linha 36): `context_json`, `prompt_hash`, nome do modelo, prompts, credenciais e configurações internas. Também evidências, claims e códigos internos (linha 36). Análise pública expõe só `gameId`, `analysisType`, `createdAt`, `fatorChave`, `vantagemTatica`, `alertaVermelho`, `veredito` (linha 36).

**Comando** (linhas 74–95): `java -jar core-api/target/core-api-0.1.0.jar snapshot-export --season 2026 --as-of 2026-09-15 --output web-ui/public/data`; `--as-of` obrigatório (corte editorial); `--allow-empty` explícito; códigos de falha fixos (`INVALID_OPTIONS`, `STARTUP_FAILED`, `DATABASE_READ_FAILED`, `OUTPUT_WRITE_FAILED`, `EMPTY_SEASON`, `EDITORIAL_MANIFEST_INVALID`, `EXPORT_FAILED`).

**Onde o web-ui lê** (`web-ui/src/services/`):
- `types.ts`: `SnapshotManifest` (`types.ts:68-73`: `schemaVersion: number; generatedAt: string; defaultSeason: number; seasons: number[]`); `SnapshotGame` (`:75`); `SnapshotAnalysis` (`:101`); `SnapshotMetric` (`:111`); `SnapshotSeason` (`:124-132`: `schemaVersion, season, generatedAt, teams: Team[], games: SnapshotGame[], metricsByTeam: Record<string, SnapshotMetric[]>, analysesByGame: Record<string, SnapshotAnalysis>`). Outros tipos: `Team` (`:1`), `Game` (`:9`), `MarketImplied` (`:35`), `TeamWeekMetrics` (`:44`), `GameDetail` (`:55`), `AnalysisResponse` (`:62`).
- `staticDataClient.ts`: `class StaticNflDataClient implements NflDataClient` (`:16`); `fetchJson("/data/manifest.json")` (`:60`); `fetchJson(\`/data/seasons/${season}.json\`)` (`:75`); `private async fetchJson(path)` (`:99`); `validateManifest(value)` (`:106`, confere `schemaVersion !== SCHEMA_VERSION`, `:108`); `validateSeason(value, expectedSeason)` (`:121`, `:123`); `export const testing = {...}` (`:224`).
- `dataClient.ts`: `interface NflDataClient` (`:3`: `getPublicationContext()`, `listGames(season)`); `interface PublicationContext` (`:11`).
- `runtimeClient.production.ts`: `export const dataClient = new StaticNflDataClient(window.fetch.bind(window))` (linha 3).
- Dados publicados atuais: `web-ui/public/data/manifest.json` (`schemaVersion: 1`, `generatedAt: "2026-09-22T05:13:34.372884Z"`, `defaultSeason: 2026`, `seasons: [2026]`) e `web-ui/public/data/seasons/2026.json` (único arquivo em `seasons/`).

---

## 5. Páginas do web-ui e build de produção

**Rotas** (`web-ui/src/App.tsx:10-12`, `BrowserRouter` + `Routes`):
- `/` → `Home` (`src/pages/Home.tsx`);
- `/game/:id` → `MatchupDashboard` (`src/pages/MatchupDashboard.tsx`).
Não há rota de "modelos", "hub" ou "lab" em `web-ui/src` (grep `hub|/models|modelo` em `App.tsx`/`main.tsx` vazio; `grep` de `broadcast-journey|risk-lab|risk-outcomes|progression` em `web-ui/src` vazio). `src/components` e `src/features` não têm rotas.

**Entrada de produção**:
- `web-ui/index.html` → `/src/main.tsx` (uma única entrada HTML).
- `web-ui/vite.config.ts` (16 linhas): só `react()` e alias `#runtime-client`; sem `rollupOptions.input`. (grep de `rollupOptions|input:` em `web-ui/vite*.ts` vazio.)
- `web-ui/package.json:8` `"build": "tsc -b && vite build"`; `:7` dev; `:12-18` scripts de `editorial`, `experience`, `real`, `journey` (`journey:build` usa `tsconfig.journey.json` e `vite.journey.config.ts`).
- `web-ui/vercel.json`: `framework: vite`, `buildCommand: npm run build`, `outputDirectory: dist`, rewrite `/(.*)` → `/index.html`. Build de produção = `web-ui/src` apenas.

**Labs e journey (fora do build de produção)**:
- `web-ui/broadcast-journey/` é um app separado: `index.html`, `logos.html`, `main.tsx` (`:8`: pilot `?view=matchup-reading`), `App.tsx` (`:49-50`: `?view=explorer`, `?view=media`; `:48`: `observation`/`entry`). Contém subpastas `risk-lab/`, `risk-outcomes/`, `progression/`, `explorer/`, `media/`, `matchup/`, `hub-team/`, `season/`, `score-curve/`, `situational/`, `w12/`, `ranking-redzone/`, `redzone-epa/`, `reading-polish/`, `game-story/`.
- Configs de build dos labs (`web-ui/vite.*.config.ts`) apontam `outDir` para diretórios fora de `dist`: `../risk-lab-dist`, `../risk-outcomes-dist`, `../journey-dist`, `../hub-team-dist`, `../matchup-dist`, `../w12-dist`, `../real-dist`, `../season-dist`, `../story-dist`, `../curve-dist`, `../redzone-epa-dist`, `../ranking-redzone-dist`, `../reading-polish-dist`, `../experience-dist`.
- `vite.risk-lab.config.ts`: `root` = `broadcast-journey`; `transformIndexHtml` troca `src="/main.tsx"` por `/risk-lab/main.tsx`; `port 18124` fixo; store default com caminho absoluto (`/Users/pedrocollet/...`, linha 5); em build chama `labExport(store)`.
- `vite.progression.config.ts`: `command !== 'serve'` lança erro ("Progression is a local research server, not ..."); `base` absoluto em `/Users/pedrocollet/...` (linha 9); porta 18127.
- `.gitignore` marca `web-ui/risk-lab-dist/` e `web-ui/risk-outcomes-dist/` como "isolated laboratory build; never part of the approved public build" (linhas em `.gitignore`).

**Conclusão**: o que entra no build de produção (Vercel) é só `web-ui/src` a partir de `index.html`: `Home`, `MatchupDashboard`, serviços estáticos. Labs, journey e `broadcast-*` são locais (dev servers em `scripts/*-dev.mjs` e saídas em `*-dist/` ignoradas pelo git). Não encontrei página publicada de "modelos" ou "lab".

---

## 6. `Spec.md` e ADRs

**Seções** (`grep ^## ` / `^### `):
- `## 1. Produto e posicionamento` (linha 16): `1.1 Escopo implementado` (24), `1.2 Não implementado ou não comprovado` (34).
- `## 2. Arquitetura implementada` (43): `2.1 Responsabilidades` (69), `2.2 Estrutura real do monorepo` (81). Linha 61: "Production publicada".
- `## 3. Configuração e variáveis de ambiente` (119): `3.1 Política compartilhada de temporadas` (138).
- `## 4. Pipeline de dados` (148): `4.1 Ordem de preparação` (150), `4.2 Schedules e mercado` (168), `4.3 Métricas semanais` (196), `4.4 Contrato de ingestion_runs` (235).
- `## 5. Schema PostgreSQL/Supabase` (248): `5.1 RLS e Data API` (267).
- `## 6. API REST implementada` (275).
- `## 7. Análise Gemini e contrato JSON` (291): `7.1 Janelas temporais` (322), `7.2 Garantias e limite da validação` (332), `7.3 Motor descritivo local por regras` (342).
- `## 8. Frontend` (373). Texto: rotas `/` e `/game/:id` (linha 375).
- `## 9. Infraestrutura e operação` (385): `9.1 Reprodutibilidade e validação do ETL` (399).
- `## 10. Roadmap` (405).
- `## 11. ADR log` (415).
- `## 12. Riscos e pendências` (431).
- `## 13. Glossário mínimo` (441). Subseções finais sem número (451, 458, 476, 488): "Revisão histórica de clareza e avaliação local", "Integração local restrita do motor por regras", "Interface editorial local de desenvolvimento", "Contrato visual e laboratório local — E0 a E3".

**ADRs em `Spec.md` §11** (tabela, linhas 419–429):
- ADR-001 Monorepo único
- ADR-002 Produto tactical-first
- ADR-003 Previsão como saída secundária
- ADR-004 Mercado como contexto complementar
- ADR-005 nflverse/nflreadpy, Polars e Parquet local
- ADR-006 Carga direta no Supabase
- ADR-007 Gemini escolhe claims táticas estruturadas
- ADR-008 Supabase migrations como fonte versionada do schema
- ADR-009 Substituído pelo ADR-010 (proxy hospedado)
- ADR-010 Java exporta snapshots públicos; Production é estática
- ADR-011 Proposto: MLflow local (SQLite) como índice dos experimentos de ML, alimentado por importador só leitura

**`docs/adr/`**: `010-static-publication-and-editorial-roadmap.md`, `011-local-mlflow-tracking.md`. **Maior número: 011** (ADR-011 = "local-mlflow-tracking", status proposto na tabela).
- Próximo número livre: **012**.

---

## 7. `.gitignore` (relacionado)

- `.venv/` (linha 2): ignora qualquer `.venv` em qualquer nível (cobre `etl-pipeline/.venv`, `research/mlflow_tracking/.venv`).
- `etl-pipeline/data/` (linha após "Dados locais gerados pela extração (Fase 1)"): ignora `etl-pipeline/data/` (raw/pbp e schedules locais).
- `/editorial/local-artifacts/mlflow/` (com comentário "MLflow local: índice dos experimentos ... nunca versionado").
- `/editorial/local-artifacts/qb-*/` (com comentário "Stores científicos completos dos experimentos QB; evidências pequenas ficam em docs/plans/qb-*").
- `/editorial/local-artifacts/real-recovery/`, `/backups/`, `/operations/`, `/editorial/local-artifacts/broadcast-*/` e outros.
- **Não há entrada genérica `editorial/local-artifacts`**: só caminhos específicos. Entradas `editorial/...` sem o prefixo `local-artifacts` (ex.: `editorial/local-integration-v1/baseline/`, `editorial/**/java21-clean-verify*.log`) são específicas.
- `research/mlflow_tracking/.gitignore`: `.venv/`, `__pycache__/`, `.pytest_cache/`.
- `research/qb_risk_temporal_v2/.gitignore`: `.venv/`.
- Não encontrado: entrada que ignore `research/*/__pycache__` no `.gitignore` raiz (há `__pycache__/` global, linha "Cache do Python", então coberto). Não encontrado: entrada para `research/qb_expected_interceptions/.venv` (coberta por `.venv/` global).

---

## Não encontrado (o que procurei e não achei)
- `real_store` em `research/qb_*`: não encontrado (só `research/mlflow_tracking`).
- Leitura de `NFL_RESEARCH_STORES` / `NFL_MLFLOW_HOME` em `research/qb_*`: não encontrado.
- Referências a `etl-pipeline/data/raw` ou `etl-pipeline` como fonte de dados em `research/qb_*`: não encontrado (só listas de proteção/isolamento).
- `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini` na raiz da worktree: não encontrado.
- Rotas de "modelos", "hub de modelos", "lab" em `web-ui/src` (App/main/pages): não encontrado.
- `rollupOptions`/`build.rollupOptions.input` em `web-ui/vite*.ts`: não encontrado.
- Entrada de `progression-dist` no `.gitignore`: não encontrado (há `risk-lab-dist` e `risk-outcomes-dist`).
- Leitura completa de: `qb_interception_risk/*.py` (exceto `dataset.py:82-89`), `qb_expected_interceptions/update.py`, `archive.py`, `isolation.py`, `reproduce.py`, `figures.py`, `write_docs.py`; `qb_risk_temporal_v2/write_report.py`, `reserved.py` além das linhas 1–50, `drift.py`, `identity.py`, `calibration_stats.py`; `m3_pyfunc.py` predict; corpo dos testes real_store de `test_registry.py`, `test_provenance.py`, `test_compare.py`.
- Execução de testes ou builds: não feita (conforme instrução).
