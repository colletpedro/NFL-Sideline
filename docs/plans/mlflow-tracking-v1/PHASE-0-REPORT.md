# Fase 0 — reconhecimento (23/11/2026)

Somente leitura: sem edição, stage, treino, teste, build ou rede. `.env` existe e não foi aberto. Branch lido:
ponta da cadeia `codex/qb-progression-improvisation-lab-v1` @ `ed2a008` (worktree limpa). Caminhos relativos à
raiz do repositório; **S** = `editorial/local-artifacts/` do checkout principal.

## Onde está o código

O laboratório de ML não está no `main` nem em `codex/metrics-integration-e5c3r` (`98cca81`). Vive em 9 branches
`codex/qb-*`, em cadeia linear sobre `98cca81`, nenhum incorporado:
`qb-interception-risk-baseline-v1` (`d654bd6`) → `qb-risk-temporal-calibration-v2` (`a6d3672`) →
`qb-risk-lab-v1` → `qb-risk-lab-communication-v2` → `qb-risk-lab-chart-focus-v3` →
`qb-expected-interceptions-v1` (`a246663`) → `qb-risk-outcomes-lab-v1` → `qb-structure-production-v1` →
`qb-progression-improvisation-lab-v1` (`ed2a008`).

## 1. Experimentos

Scripts Python com `argparse`; nenhum notebook.

| Experimento | Pasta | Entrada | Alvo / modelos |
|---|---|---|---|
| Baseline v1 | `research/qb_interception_risk/` | `pipeline.py {build,develop,evaluate,apply,reproduce}`; `offline.py` (rede bloqueada); `reproduce.sh`; `acquire.py` (rede) | `is_interception_worthy` (FTN); variantes `context`/`depth` |
| Calibração temporal v2 | `research/qb_risk_temporal_v2/` | `prepare.py` (rede); `run.py` → `experiment.run`; `reserved.py {preflight,evaluate}`; `reproduce.py` | M0–M3; M3 promovido |
| Interceptações esperadas v1 | `research/qb_expected_interceptions/` | `run.py {build,develop,evaluate,refit,apply}`; `update.py`; `reproduce.py` | INT observada dado FTN; B0/B1/B2 e logística C; B2 escolhido |

Baselines: v1 prevalência constante (`p0`); v2 M1 (constante do ano anterior); xINT B0 (taxa global), B1 (taxa
por grupo FTN), B2 (grupo FTN, só a temporada anterior). Aplicação/empacotamento sem treino:
`research/qb_risk_lab/pipeline.py` (M3), `qb_risk_outcomes_lab/package.py` (B2), `qb_progression_lab/`;
`qb_structure_production/` é descritivo (sem sklearn).

## 2. Método

| Peça | Onde | Bibliotecas |
|---|---|---|
| Janelas expansivas | v1 `design.json` `folds` + `pipeline.temporal`; xINT `risk_model.blocks`. v2 usa janelas fixas (`experiment.candidate_blocks`, `common.blocks`) | pandas |
| Hiperparâmetros | Só C da L2: v1 `[0.01, 0.1, 1, 10]`, xINT `[0.01, 0.1, 1]`; v2 `C: 0.1` fixo | scikit-learn `LogisticRegression` (lbfgs, tol 1e-9) |
| Calibração de intercepto | `qb_risk_temporal_v2/calibration_stats.py`: `intercept_shift` (brentq no logit); `diagnostic_calibration` só diagnóstico | numpy, scipy |
| Bootstrap por jogo | v1 `evaluation.paired_game_bootstrap`/`qb_aggregate`; v2 `stratified_paired`/`diagnostic_calibration`; xINT `evaluate.paired`; 2.000 réplicas | numpy `default_rng` |
| Métricas | `evaluation.metrics` (v1), `calibration_stats.scores` (v2), `evaluate.metrics` (xINT) | `sklearn.metrics` |

## 3. Saídas atuais

Arquivos em diretórios novos por etapa (recusa sobrescrever). v1: `development-v3/` (`development_metrics.json`,
`frozen_config.json`, `model_*.json`, `environment.json`), `evaluation-v1/` (`metrics.json` com bootstrap,
`calibration_{v}.json`, `groups_{v}.json`, `coefficients_{v}.csv`, `test_predictions_*.parquet`),
`application-v1/`, `figures-v4/`. v2: `metrics.json`, `calibration_bins.json`, `groups.csv`, `selection.json`,
`predictions.parquet`, `splits.parquet`, `frozen/freeze.json`. xINT: `metrics.csv`, `calibration.csv`,
`paired_bootstrap.json`, `selection.json`, `freeze.json`, `pass_predictions.parquet`. O terminal só imprime
resumos (capturados em `*.log`). Modelos em JSON próprio, sem pickle; `predict_json` reimplementa a inferência e é
conferido contra o sklearn. Cópias pequenas versionadas em `docs/plans/<experimento>/evidence/` e `figures/`.

## 4. Laboratório

Não há snapshot do laboratório no Git. `research/qb_risk_lab/pipeline.py update` gera pacotes endereçados por
conteúdo em `S/qb-risk-lab-v1/packages/<id24>/` com ponteiro `current.json`. `index.json` tem `schemaVersion`,
`pipelineVersion`, `season`, `phase`, `model{id, sha256, structureYears, calibrationYear, offset}`, `coverage`,
`summary`, `players`, `attribution`, `interpretation`, `packageId`, `acquiredAt` — sem log loss/Brier/PR-AUC. O
frontend lê por GET `/__risk-lab/…` (middleware em `web-ui/build/risk-lab.ts`; congelado na build por
`risk-lab-export.ts`; config `web-ui/vite.risk-lab.config.ts`). Métricas do xINT estão digitadas à mão em
`web-ui/broadcast-journey/risk-outcomes/Lab.tsx:28`. O snapshot público `web-ui/public/data` é separado.

## 5. Dados, versões e sementes

Parquet/CSV locais do nflverse (PBP e FTN 2022–2026, schedules, rosters) via `urllib`; sem PostgreSQL. Hashes
extensos (`sources.json`, `build_manifest.json`, freezes). Sementes: v1/v2 `20261104`, xINT `20261105`.
Reprodução offline byte a byte já comprovada. Dataset v1: 78.460 linhas.

## 6. Dependências

`requirements.txt`/`requirements.lock` por pasta (pip): numpy 2.3.4, pandas 2.3.3, pyarrow 22.0.0,
scikit-learn 1.7.2, scipy 1.16.3, matplotlib 3.10.7, pytest 8.4.2. Python 3.11.13, macOS arm64; venv por pasta;
wheelhouse offline no store. v2 e xINT importam a v1 via `sys.path.insert`.

## 7. Testes e CI

pytest: v1 23 testes em 1,34 s; v2 43 em 2,03 s; também xINT, `qb_risk_lab`, `qb_risk_outcomes_lab`. Fixtures
sintéticas pequenas. Sem CI para `research/` (só `ci-java.yml` e `weekly_etl.yml`). Duração de um experimento
completo: não registrada.

## 8. Spec e ADRs

O `Spec.md` não menciona o laboratório nem MLflow; diz que o produto não tem modelo quantitativo próprio
(linhas 20 e 36); roadmap §10 item 5 prevê backtest e modelo. Reprodutibilidade só do ETL (§9.1). ADRs: só o
arquivo `docs/adr/010-…`; 001–009 existem só na tabela §11 do Spec. Formato `# ADR-NNN: título`, `Status:`,
seções `##`, em português. Próximo: **ADR-011**.

## 9. `.gitignore`

Os `.gitignore` locais ignoram `.venv/` (e `artifacts/` na v1). A raiz não ignora os stores `S/qb-*` (~1 GB):
`git status` mostra `?? editorial/local-artifacts/`. Nenhum `mlruns`/`mlflow.db` no repositório.

## 10. Obstáculos

Caminhos absolutos fixos (`acquire.APPROVED`, `qb_expected_interceptions/common.py`, `qb_risk_outcomes_lab/package.py`,
`vite.*.config.ts`, scripts em `docs/plans/qb-risk-lab-v1/`); `sys.path.insert`; bloqueio de rede por troca de
`socket.socket.connect`; integridade por hash do código congelado; reprodução compara todos os arquivos de saída;
modelos JSON sem pickle (conflita com `mlflow.sklearn`); código denso, mas modular por etapa.

## Não consegui verificar

Duração de um experimento completo; documento sobre o abandono do desenho hospedado por custo/credenciais
(só o ADR-009, substituído pelo ADR-010); uso de autolog/Optuna (não há); CI para `research/` (não há); arquivos
dos ADRs 001–009 (nunca existiram); estado atual da avaliação reservada da v2; detalhes dos branches `codex/broadcast-*`.
