# Fatos do store v2 de calibração temporal (somente leitura)

Escopo: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-temporal-calibration-v2/20261104-v2` (doravante **STORE**). Worktree de código/docs: `/Users/pedrocollet/Downloads/NFL Sideline/.claude/worktrees/mlflow-tracking-v1` (doravante **W**). Python usado: `/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python3.11 -I -B` (pandas 2.3.3, pyarrow 25.0.1; o `python3.11` do sistema não tem pandas). Nenhum arquivo foi escrito dentro do STORE, W ou dos stores.

---

## 1. Estrutura do STORE e diretório canônico

### 1.1 Listagem (profundidade 2, tamanhos em bytes; diretórios = total recursivo)

```
STORE/
  acquisition-progress.json                      7202
  additional-sources.json                        7595
  experiment-final/                 total 3208868  32 arquivos
      calibration_bins.json 24999 | drift/ 78799 | environment.json 915 | frozen/ 24058
      groups.csv 54010 | metrics.json 23114 | models/ 17071 | passer_presentation.csv 8292
      position_by_week.csv 10192 | predictions.parquet 1389132 | selection.json 1909 | splits.parquet 1576377
  experiment-final.log                            150
  experiment-release/               total 3208954  32 arquivos
      (mesmos nomes; environment.json 1001; metrics.json 23114; demais iguais aos de final)
  experiment-release.log                          150
  experiment-v1/                    total 3207556  32 arquivos
      (environment.json 915; metrics.json 21802; demais tamanhos iguais)
  experiment-v1.log                               150
  experiment-verified/              total 3209130  32 arquivos
      calibration_bins.json 24999 | drift/ 78799 | environment.json 1177 | frozen/ 24058
      groups.csv 54010 | metrics.json 23114 | models/ 17071 | passer_presentation.csv 8292
      position_by_week.csv 10192 | predictions.parquet 1389132 | selection.json 1909 | splits.parquet 1576377
  experiment-verified.log                         150
  figures-final/                    total 898930   9 arquivos
  figures-reviewed/                 total 1019880  9 arquivos
  figures-verified/                 total 898930   9 arquivos
  inputs/                           total 97459821 45 arquivos (v1/ 96315520; provider/ 307497; roster_weekly_2026.parquet 836804)
  isolation-delivery.json                         5155
  isolation.json                                  1470
  legacy-tests.log 449 | npm-ci.log 577 | provider-revision-source.json 327
  reference-v1/                     total 11553948 85 arquivos
  reference-v1-check.json                        28299
  reference-v1.log                                2469
  reproduction-final/               total 17682356 147 arquivos
      experiment/ 3209130 | figures/ 898930 | figures-rechecked/ 898930 | figures-reviewed/ 1019880
      reference-v1/ 11553948 | reproduction-check.json 33778 | reproduction-check-3.json 33897 | reproduction-check-rechecked.json 33863
  reproduction-final.log                          3527
  requirements.lock                                379
  reserved-status.json                             806
  tests-delivery-final.log / tests-delivery.log / tests-final-v2.log / tests-final.log / tests-release.log / tests-v1.log   99 cada
  v1-lineage.json                                  246
  wheelhouse/                       total 99731010 23 arquivos
```

Arquivos de `experiment-verified/` (32, incluindo `frozen/` e `models/`):
`calibration_bins.json`, `drift/` (9 arquivos), `environment.json`, `frozen/` (5), `groups.csv`, `metrics.json`, `models/` (9), `passer_presentation.csv`, `position_by_week.csv`, `predictions.parquet`, `selection.json`, `splits.parquet`.

`drift/` (em `experiment-verified/drift/`): `composition.csv` 14584; `integrity_v1_reconciled.json` 26791; `population.csv` 278; `schema_comparison.json` 2855; `standardization.csv` 1834; `standardization_cells_coarse.csv` 3013; `standardization_cells_primary.csv` 23985; `standardization_contract.json` 2270; `standardization_differences.json` 3189.

`frozen/` (em `experiment-verified/frozen/`): `M0.json` 2680; `M1.json` 97; `M3.json` 2816; `freeze.json` 1769; `reserved_schedule.csv` 16696.

`models/`: `M1_2024/2025/2026.json` (97/96/97 bytes); `M2_2024/2025/2026.json` (2782/2782/2789); `M3_2024/2025/2026.json` (2800/2812/2816).

### 1.2 Qual é o diretório canônico

**Canônico: `experiment-verified/` e `figures-reviewed/`.** Evidências:

- `docs/plans/qb-risk-temporal-calibration-v2/README.md` (W), linhas 17–18: "`experiment-verified/`: dataset lido da referência, diagnósticos, modelos, previsões por passe, splits por chave/candidato/ano, CIs, classificação de posição e decisão. `models/` preserva M1/M2/M3 por ano… `frozen/` contém apenas M0/M1 e o M3 escolhido para reserva." e "`figures-reviewed/`: PNG/SVG e tabela de suporte das curvas."
- README, linha 81: `FREEZE="$STORE/experiment-verified/frozen"` (comando oficial de preflight/avaliação reservada).
- `HANDOFF.md` (W), linha 7: "Configuração científica em `experiment-verified/frozen` no store".
- `research/qb_risk_temporal_v2/reproduce.py` (W), linha 33: `compare()` compara `store/'experiment-verified'` com a saída e `store/'figures-reviewed'` com a figura.
- `docs/plans/.../evidence/reproduction-check.json`: `"figures_directory": "figures-reviewed"`.
- `CHECKPOINTS.md` (W), item 13: a revisão visual "revelou recorte de taxas extremas com baixo n: painéis próprios passaram a mostrar todas as faixas" — a versão corrigida é a revisada.

Não canônicos (evidência):

| Diretório | Situação |
|---|---|
| `experiment-v1/` | Execução anterior. `metrics.json` difere do canônico só pela ausência de `same_structure_before_offset_diagnostic` nas 3 linhas M3 (verificado; as demais 9 entradas são idênticas). `environment.json` lista `calibration_stats.py`, `experiment.py`, `reserved.py` com hashes diferentes e não tem `figures.py`/`reproduce.py`/`isolation.py`. `freeze.json` difere no `code_hashes` (`reserved.py`, `calibration_stats.py`, `experiment.py`). |
| `experiment-final/` | Execução posterior. Mesmos `metrics.json`, `groups.csv`, `predictions.parquet`, `splits.parquet`, `calibration_bins.json` do canônico. Diferença só em `environment.json` e `freeze.json.code_hashes` (`experiment.py` = `d2f7d92f…`, `reserved.py` = `7aff9cdb…`, não batem com o código atual de W). |
| `experiment-release/` | Igual a `experiment-final` no conteúdo científico; `freeze.json.code_hashes` difere só em `experiment.py` (`d2f7d92f…`). |
| `figures-final/`, `figures-verified/` | Idênticos entre si; diferem de `figures-reviewed/` só em `calibration_known_periods.png/.svg` (versão pré-correção do recorte de taxas extremas). |

Os logs `experiment-*.log` contêm as mesmas 4 linhas em todos: `Retrospective year complete 2024/2025/2026` e `Decision candidate_for_reserved_evaluation_only M3`.

`reproduction-final/experiment/` tem o mesmo tamanho total de `experiment-verified/` (3209130 bytes); é a réplica offline.

---

## 2. Experimento canônico (`experiment-verified/`)

### 2.1 `metrics.json`

- Tipo: **lista** de **12** registros. Ordem: ano 2024 (M0, M1, M2, M3), 2025 (M0..M3), 2026 (M0..M3).
- Pares `(year, candidate)` distintos: **12/12**. Anos: 2024, 2025, 2026. Candidatos: M0, M1, M2, M3.
- Chaves por registro: `M1`, `calibration_diagnostic`, `candidate`, `difference_vs_M1`, `model`, `period_status`, `year`. Chave `same_structure_before_offset_diagnostic` existe **só em 3 registros** (2024/M3, 2025/M3, 2026/M3).
- `period_status` = `"known_retrospective_diagnostic"` em todos.
- Subchaves:
  - `model` e `M1`: `brier`, `expected`, `log_loss`, `mean_probability`, `n` (int), `observed_expected`, `positives` (int), `pr_auc_average_precision`, `prevalence`, `roc_auc`. `M1` do registro é idêntico ao `model` do registro M1 do mesmo ano (verificado nos 3 anos).
  - `difference_vs_M1`: `brier` e `log_loss`, cada um `{delta, high, low}`.
  - `calibration_diagnostic`: `bootstrap_requested` (int), `bootstrap_valid_joint` (int), `bootstrap_valid_offset` (int), `joint_intercept`, `joint_intercept_ci` [lista 2], `method` (`"game bootstrap; diagnostic MLE, not applied to predictions"`), `offset_intercept`, `offset_intercept_ci` [2], `slope`, `slope_ci` [2], `status` (`"diagnostic_only"` ou `"constant_slope_unidentifiable"`).
  - `same_structure_before_offset_diagnostic` (só M3): mesmas 10 subchaves de `model`.
- Código: `research/qb_risk_temporal_v2/experiment.py` linhas 70–75 (`record=dict(year, candidate, model=m, M1=base, difference_vs_M1=diff, calibration_diagnostic=…, period_status=…)`; para M3, `record['same_structure_before_offset_diagnostic']=raw`, com guarda `ValueError` se AP ou AUC mudarem por deslocamento de offset).

**Tabela `model` (valores completos, `repr` do Python):**

| year | cand | log_loss | brier | pr_auc_average_precision | roc_auc | observed_expected | n | positives | expected | mean_probability | prevalence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | M0 | 0.14680295113185876 | 0.03227238927603301 | 0.05776977158210094 | 0.5737132857342024 | 0.7206239509413567 | 17740 | 591 | 820.1226162799226 | 0.046230136205181654 | 0.03331454340473506 |
| 2024 | M1 | 0.14677662549388334 | 0.032255496477054064 | 0.03331454340473506 | 0.5 | 0.8237449702569182 | 17740 | 591 | 717.4550635686101 | 0.0404427882507672 | 0.03331454340473506 |
| 2024 | M2 | 0.1456372582204236 | 0.03217295702573713 | 0.048772758118638015 | 0.5700497648805004 | 0.8263108152277442 | 17740 | 591 | 715.2272354526924 | 0.040317206057085254 | 0.03331454340473506 |
| 2024 | M3 | 0.1453941792780007 | 0.03214284874455856 | 0.05456064375073514 | 0.5722705708965286 | 0.8254782640022431 | 17740 | 591 | 715.9485909836071 | 0.04035786871384482 | 0.03331454340473506 |
| 2025 | M0 | 0.14120157433717448 | 0.030873765589395377 | 0.04476199597735799 | 0.5842720967506765 | 0.7529231099237429 | 17358 | 553 | 734.47074835571 | 0.042313097612381036 | 0.031858509044820835 |
| 2025 | M1 | 0.14117772155557853 | 0.03084566448231916 | 0.031858509044820835 | 0.5 | 0.9562943324113731 | 17358 | 553 | 578.2738444193913 | 0.03331454340473507 | 0.031858509044820835 |
| 2025 | M2 | 0.1402653990784605 | 0.030785368072607747 | 0.042402218624973204 | 0.5709514465739067 | 0.948820500971766 | 17358 | 553 | 582.8288906422518 | 0.03357696109242147 | 0.031858509044820835 |
| 2025 | M3 | 0.13966077421760636 | 0.03074277899215753 | 0.045524074639917936 | 0.5859075998327803 | 0.9480987330447663 | 17358 | 553 | 583.2725862042566 | 0.03360252253740389 | 0.031858509044820835 |
| 2026 | M0 | 0.13734305368853172 | 0.02984316969838219 | 0.05282409165714033 | 0.5780969770986697 | 0.7760750234252997 | 7106 | 219 | 282.18921288487985 | 0.03971140063113986 | 0.030819026175063328 |
| 2026 | M1 | 0.1375954619596301 | 0.029870294325320602 | 0.030819026175063328 | 0.5 | 0.9673718921279366 | 7106 | 219 | 226.38656527249694 | 0.03185850904482085 | 0.030819026175063328 |
| 2026 | M2 | 0.1370647418112149 | 0.02984046806233492 | 0.04022918996141585 | 0.5595868199831195 | 0.9689333364445646 | 7106 | 219 | 226.02174139616838 | 0.031807168786401406 | 0.030819026175063328 |
| 2026 | M3 | 0.13632541358974393 | 0.029770426986323484 | 0.05107774897845832 | 0.5742720220016139 | 0.9685173517984116 | 7106 | 219 | 226.11881923782295 | 0.031820830177008576 | 0.030819026175063328 |

**Diferença vs M1 e diagnóstico de calibração (resumo; M1 omitido porque é a referência; em algumas linhas o IC do Brier foi omitido na tabela, valores completos em `metrics.json`):**

| year | cand | ΔLL [low, high] | ΔBrier [low, high] | status | offset_intercept [CI] | slope | joint_intercept | boot válidos offset/joint/req |
|---|---|---|---|---|---|---|---|---|
| 2024 | M0 | 2.632563797540078e-05 [-0.0010389247335985021, 0.0009902623879918136] | 1.68927989789445e-05 [-0.00011726435984459422, 0.00013301433471390978] | diagnostic_only | -0.3425959741132276 [-0.4262301070739633, -0.25830255229738547] | 0.9246402403503359 | -0.5673598666879434 | 2000/2000/2000 |
| 2024 | M2 | -0.0011393672734598046 [-0.0020501399528215815, -0.0002841650538894585] | -8.253945131693963e-05 [-0.00017030312112102997, -4.432389776077528e-06] | diagnostic_only | -0.19879595050698484 | 0.8603702789216394 | -0.6359151494265427 | 2000/2000/2000 |
| 2024 | M3 | -0.0013824462158826816 [-0.0024191410038316864, -0.0004535818848115408] | -0.00011264773249550073 [-0.00023148878329503863, -8.8917544288491e-06] | diagnostic_only | -0.19997234621425172 | 0.913710836849978 | -0.46960990899529637 | 2000/2000/2000 |
| 2025 | M0 | 2.3852781595921154e-05 [-0.001298828656719489, 0.001199169927797457] | 2.8101107076223733e-05 | diagnostic_only | -0.2959159181900021 | 0.9435094538177743 | -0.4695177140141418 | 2000/2000/2000 |
| 2025 | M2 | -0.0009123224771180841 [-0.001812318071806592, -2.7231887738660862e-05] | -6.029640971140906e-05 | diagnostic_only | -0.05447333849711745 | 0.8552594474276315 | -0.5358711017903051 | 2000/2000/2000 |
| 2025 | M3 | -0.0015169473379722008 [-0.002592064866186194, -0.000541877743789119] | -0.00010288549016162002 [-0.00019062212522711263, -2.3672476352377607e-05] | diagnostic_only | -0.05531758753927164 | 0.9632378123916329 | -0.1770497177436158 | 2000/2000/2000 |
| 2026 | M0 | -0.0002524082710983739 [-0.0020010102040229198, 0.00141493704337648] | -2.7124626938415035e-05 | diagnostic_only | -0.2637220824793385 | 0.973543999026948 | -0.3468362318408708 | 2000/2000/2000 |
| 2026 | M2 | -0.0005307201484152203 [-0.0016920836096881158, 0.0005666492041994903] | -2.9826262985687398e-05 | diagnostic_only | -0.03270400788388241 | 0.6742262957083789 | -1.1346154694318915 | 2000/2000/2000 |
| 2026 | M3 | -0.0012700483698861954 [-0.002429235862903927, -0.00015240731531538892] | -9.986733899712703e-05 | diagnostic_only | -0.03312518420857966 | 0.9711174533896342 | -0.13059549206673512 | 2000/2000/2000 |

Os registros M1 têm `difference_vs_M1` = 0.0 com IC [0,0], `status = constant_slope_unidentifiable`, `slope/joint_intercept = None` e `bootstrap_valid_joint = 0`.

**`same_structure_before_offset_diagnostic` (só M3; mesma estrutura, sem offset):**

| year | log_loss | brier | roc_auc | pr_auc_AP | observed_expected | expected | mean_probability |
|---|---|---|---|---|---|---|---|
| 2024 | 0.14880626941769284 | 0.032479240843070814 | 0.5722705708965286 | 0.05456064375073514 | 0.6394265609523115 | 924.2656406387173 | 0.05210065618031101 |
| 2025 | 0.14237217592419274 | 0.030983617362756496 | 0.5859075998327803 | 0.045524074639917936 | 0.6833693195317003 | 809.2256766501606 | 0.046619753234828934 |
| 2026 | 0.1368948591968338 | 0.02981104065960865 | 0.5742720220016139 | 0.05107774897845832 | 0.830829259682006 | 263.5920647327956 | 0.037094295628032035 |

(n e positives iguais aos do `model`.) AP e AUC batem com o `model` do mesmo ano (guarda do código).

### 2.2 `selection.json` (completo)

```json
{
  "decision": "candidate_for_reserved_evaluation_only",
  "reference_if_none": "M1",
  "results": {
    "M2": {
      "difference_vs_M1": {
        "brier": {"delta": -7.15389750451065e-05, "high": -2.1468545859129183e-05, "low": -0.00012484992845438503},
        "ll": {"delta": -0.0010270804316198257, "high": -0.0004166899051765632, "low": -0.0016526267328082578}
      },
      "eligible": true,
      "per_year_conditions_pass": true,
      "pooled": {"brier": 0.031486713677158294, "expected": 1298.0561260949444, "log_loss": 0.14298056179936838, "mean_probability": 0.03698376335104406, "n": 35098, "observed_expected": 0.8813178236303195, "positives": 1144, "pr_auc_average_precision": 0.045095708079749816, "prevalence": 0.032594449826200925, "roc_auc": 0.5690781614862724}
    },
    "M3": {
      "difference_vs_M1": {
        "brier": {"delta": -0.00010781973652902111, "high": -4.2939230511026794e-05, "low": -0.000175796385536743},
        "ll": {"delta": -0.0014489648345284696, "high": -0.0007721888243106852, "low": -0.0021515498804693858}
      },
      "eligible": true,
      "per_year_conditions_pass": true,
      "pooled": {"brier": 0.03145043291567438, "expected": 1299.2211771878638, "log_loss": 0.14255867739645972, "mean_probability": 0.0370169575812828, "n": 35098, "observed_expected": 0.8805275191681861, "positives": 1144, "pr_auc_average_precision": 0.049956187047367574, "prevalence": 0.032594449826200925, "roc_auc": 0.5776336485273577}
    }
  },
  "selected_contextual_candidate": "M3",
  "selection_years": [2024, 2025]
}
```

### 2.3 `calibration_bins.json`

- Tipo: dict com **12 chaves**: `2024_M0, 2024_M1, 2024_M2, 2024_M3, 2025_M0, …, 2026_M3` (formato `"{ano}_{candidato}"`).
- Cada chave: lista de **9 registros** (um por faixa). Faixas: `[0.0, 0.02)`, `[0.02, 0.03)`, `[0.03, 0.04)`, `[0.04, 0.05)`, `[0.05, 0.075)`, `[0.075, 0.1)`, `[0.1, 0.15)`, `[0.15, 0.25)`, `[0.25, 1.0)`.
- Chaves de cada registro: `bin`, `mean_probability`, `n`, `observed_rate`, `positives`, `wilson_high`, `wilson_low`. `M1` tem `n=0` e `mean_probability/observed_rate/wilson_*` = `null` na faixa 1 (nulls onde n=0).
- Exemplo (2025_M3, faixa 1): `{"bin": "[0.0, 0.02)", "mean_probability": 0.01895833067700178, "n": 455, "observed_rate": 0.013186813186813187, "positives": 6, "wilson_high": 0.02846801529743591, "wilson_low": 0.006057189043234164}`.
- Nota: `wilson_low` pode ser `-1.3877787807814457e-17` (erro de ponto flutuante) quando positives=0.

### 2.4 `groups.csv`

- Colunas (16): `year, candidate, group, value, support_sufficient, n, positives, prevalence, expected, mean_probability, log_loss, brier, pr_auc_average_precision, roc_auc, constant_log_loss, constant_brier`.
- Dtypes: `year` int64; `candidate`, `group`, `value` object (lidos como string; `value` ex. `"1.0"`, `"1-3"`, `"closed"`); `support_sufficient` bool; `n`, `positives` int64; demais float64.
- **256 linhas**. Por (ano, candidato): 2024 = 21, 2025 = 21, 2026 = 22 (× 4 candidatos).
- `group` (valores): `down` ∈ {1.0,2.0,3.0,4.0}; `qtr` ∈ {1.0..5.0}; `distance_group` ∈ {1-3, 4-7, 8-10, 11+}; `roof` ∈ {closed, dome, open, outdoors}; `score_group` (leading/tied/trailing…).
- `support_sufficient = False` em 16 linhas.
- Primeira linha: `2024, M0, down, 1.0, True, 6561, 195, 0.0297210791037951, 260.62883096305353, 0.0397239492399106, 0.134598890810536, 0.0289003428509812, 0.0441555568061394, 0.55304542561847, 0.1353976203689, 0.0289526916077333`.

### 2.5 `predictions.parquet`

- Schema (pyarrow):

| coluna | tipo |
|---|---|
| game_id | string (object) |
| play_id | double (float64) |
| season | int32 |
| season_type | string (object) |
| week | int32 |
| passer_player_id | string (object) |
| is_interception_worthy | int64 |
| M0, M1, M2, M3 | double (float64) |

- Metadados: pandas metadata presente. **42204 linhas**, 1 row group. Sem nulos.
- Linhas por temporada: **2024: 17740** (semanas 1–18); **2025: 17358** (semanas 1–18); **2026: 7106** (semanas 1–7). Todas `season_type = REG`.
- Valores: 651 `game_id` distintos; 148 passadores; `is_interception_worthy`: 0 = 40841, 1 = 1363. Sem duplicatas em (game_id, play_id, passer_player_id).
- Exemplo (2 primeiras linhas): `game_id=2024_01_ARI_BUF, play_id=83.0, season=2024, season_type=REG, week=1, passer_player_id=00-0035228, is_interception_worthy=0, M0=0.030917, M1=0.040443, M2=0.02302, M3=0.030599`.
- Faixas de M0 e M3 (todos os dados): M0 [0.01704631235357113, 0.15463931623557106]; M3 [0.01335934536400487, 0.14707457355629516].

Nota de consistência: `n` de `metrics.json` por ano = linhas de `predictions.parquet` do mesmo ano (17740 / 17358 / 7106).

### 2.6 `splits.parquet`

- Schema: `game_id` string; `play_id` double; `season` int32; `week` int32; `evaluation_year` int64; `candidate` string; `role` string.
- **941520 linhas**, 1 row group.
- Valores: `season` ∈ {2022, 2023, 2024, 2025, 2026}; `evaluation_year` ∈ {2024, 2025, 2026}; `candidate` ∈ {M0..M3}; `role` ∈ {`structure_train`, `constant_train`, `calibration`, `evaluation_known`, `unused`}.
- Contagens por (evaluation_year, candidate, role):

| ano | cand | calibration | constant_train | evaluation_known | structure_train | unused |
|---|---|---|---|---|---|---|
| 2024 | M0 | 0 | 0 | 17740 | 36256 | 24464 |
| 2024 | M1 | 0 | 18248 | 17740 | 0 | 42472 |
| 2024 | M2 | 0 | 0 | 17740 | 18248 | 42472 |
| 2024 | M3 | 18248 | 0 | 17740 | 18008 | 24464 |
| 2025 | M0 | 0 | 0 | 17358 | 53996 | 7106 |
| 2025 | M1 | 0 | 17740 | 17358 | 0 | 43362 |
| 2025 | M2 | 0 | 0 | 17358 | 17740 | 43362 |
| 2025 | M3 | 17740 | 0 | 17358 | 36256 | 7106 |
| 2026 | M0 | 0 | 0 | 7106 | 71354 | 0 |
| 2026 | M1 | 0 | 17358 | 7106 | 0 | 53996 |
| 2026 | M2 | 0 | 0 | 7106 | 17358 | 53996 |
| 2026 | M3 | 17358 | 0 | 7106 | 35988 | 18008 |

- Linhas por temporada (`season`): 2022: 216096; 2023: 218976; 2024: 212880; 2025: 208296; 2026: 85272.

### 2.7 `models/`

Arquivos (9): `M1_2024.json, M1_2025.json, M1_2026.json, M2_2024.json, M2_2025.json, M2_2026.json, M3_2024.json, M3_2025.json, M3_2026.json`. O sufixo é o **ano de avaliação**.

| arquivo | kind | offset | calibration_year | calibration_n | calibration_positive | structure_sha256 | outras chaves |
|---|---|---|---|---|---|---|---|
| M1_2024 | constant | — | — | — | — | — | `probability` 0.040442788250767206, `train_years` [2023] |
| M1_2025 | constant | — | — | — | — | — | `probability` 0.03331454340473506, `train_years` [2024] |
| M1_2026 | constant | — | — | — | — | — | `probability` 0.031858509044820835, `train_years` [2025] |
| M2_2024 | context | 0.0 | None | 0 | 0 | c0d44267e085940ab944cecb80491651f30b40a00e77a11feab9947c7cd703b5 | `structure` |
| M2_2025 | context | 0.0 | None | 0 | 0 | bdb10fea237a0180e2565daf887256f948f9d54f3f528eaf9c805236a8718767 | `structure` |
| M2_2026 | context | 0.0 | None | 0 | 0 | 6a96fca92d604c30cb4bcd636f70257093828250b03384a07bbe97fabb1b7436 | `structure` |
| M3_2024 | context | -0.26912885047460955 | 2023 | 18248 | 738 | 2ae931e7e578656096a20d1710dc1ff6550f2f80b36b30402581f80adffcde7c | `structure` |
| M3_2025 | context | -0.3425959741132276 | 2024 | 17740 | 591 | 3b000e91f9b3d09b423c6485f87e1028792623e9efd86f9abb32fdd28c70bceb | `structure` |
| M3_2026 | context | -0.1593395890254225 | 2025 | 17358 | 553 | 316db691f25860fd0a81972700c08504b9317ba42b1bd5aa472a8bf0942cdd8b | `structure` |

Chaves de `M3_*.json` (top-level): `calibration_n`, `calibration_positive`, `calibration_year`, `kind`, `offset`, `structure`, `structure_sha256`.

Chaves de `structure` (17): `C`, `categorical_columns`, `categories`, `category_imputation`, `coefficients`, `feature_names`, `format`, `intercept`, `iterations`, `mean`, `median`, `missing_indicators`, `numeric_columns`, `raw_features`, `scale`, `train_years`, `variant`.

Valores de `M3_2025.structure` (exemplos): `C=0.1`; `categorical_columns` começa em `down`; `categories`=[[1.0,2.0,3.0,4.0],[1.0,2.0,3.0,4.0,5.0]] (no M3_2026); `coefficients` len 18; `feature_names` len 18 (ex.: `num__ydstogo`, `cat__down_1.0`…); `format`=`"qb-iw-json-logistic-v1"`; `intercept`=-2.8734611274420714; `iterations`=93; `numeric_columns` len 9 (começa em `ydstogo`); `raw_features` len 6; `variant`=`"context"`. (`train_years` de `M3_2025` começa em 2022 e tem 2 elementos; o valor completo não foi conferido.)

Para `M3_2026` (o congelado): `train_years` = **[2023, 2024]**, `variant` = `"context"`, `C` = 0.1, 18 coeficientes.

Hash `structure_sha256`: reproduz-se com `sha256(json.dumps(structure, sort_keys=True).encode())` (separadores padrão); verificado para M3_2026 = `316db691…cdd8b`. (Esta é a hash da estrutura, não do arquivo.)

Código de geração: `research/qb_risk_temporal_v2/experiment.py` linha 22 (`return dict(kind='context', structure=m, offset=delta, calibration_year=cal_year, structure_sha256=…)`).

### 2.8 `frozen/freeze.json` (completo; hashes longos abreviados onde indicado)

```json
{
  "code_hashes": {
    "research/qb_interception_risk/dataset.py": "9a6f86b2259e97255d03ab8d500b15511b6d47a5d5312c8a8997f997c308d330",
    "research/qb_interception_risk/model.py": "39a18d8ffe504f9bab87ccbb0dc87d3407d0f85bba3fb5dbd7c1308533fc5d80",
    "research/qb_risk_temporal_v2/calibration_stats.py": "08e7eee55fb4f491cad6e432d40c7cb6e311b16aa59ef5fdb6448ad3c7747799",
    "research/qb_risk_temporal_v2/common.py": "c2e2ea1aaf5071b54a49b22dd096eee26122d3d3ffbdc72b57e722e26735fdc7",
    "research/qb_risk_temporal_v2/experiment.py": "5ae8f62a105bed2480b24ed7d3d3f34c8fe83c1be5d7061bce43213cf1f0c651",
    "research/qb_risk_temporal_v2/reserved.py": "cba1ae9333362a608caf1d51fe5c619937e61cd6c36344051b90a24b6da72677"
  },
  "contracts": {
    "EXPERIMENT-PROTOCOL.md": "662f8694d1bf37bb8e6462ec4f3b8c0068eb6a42121c4bf0e856a70cabd5b8f1",
    "RESERVED-EVALUATION.md": "cadf7175e6b39b1cd0057d08ea810f87a3b6dd697b9e8c46e74c7c32f5792e1c",
    "protocol.json": "342d0d8a9a4df65df9b303467d76be086ca9dded0697fb4dc62723962070b34a"
  },
  "dataset_sha256": "10e90375f22a187f361007e7db84a6f5bf2c81451171be4be4e805d7cc67c296",
  "files": {
    "M0.json": "d75eaa1f09ea552a2bf47f6bfc6c5ed4dbeee867f2bb7f94409a2373b46a18bb",
    "M1.json": "23d917f4def21a1b3e521a1565bb6d42caa0529686b844adf73fbfea32fcfed5",
    "M3.json": "38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6",
    "reserved_schedule.csv": "e423fd962b90907befde984260c5ccc061483678738e8aa196e446afa9660e52"
  },
  "references": ["M0", "M1"],
  "reserved": {"maturity_days_after_latest_kickoff": 8, "season": 2026, "weeks": [9, 13]},
  "selected": "M3",
  "status": "awaiting_mature_reserved_window; no independent confirmation yet",
  "version": 2
}
```

Chaves: `code_hashes` (6), `contracts` (3), `dataset_sha256`, `files` (4), `references`, `reserved`, `selected`, `status`, `version`. Não há hash de `predictions`/`splits`.

Sha256 do próprio `freeze.json` = `3af75413a0f8bdb9a5fa788cc3b769272deaa66f523b734aa5fe739a90b723ca` (é o `freeze_sha256` de `reserved-status.json`).

Frozen M0/M1 (`frozen/M0.json`, `frozen/M1.json`): `M0` tem chaves `calibration_year, kind, offset, structure` (contexto); `M1` = `{"kind": "constant", "probability": 0.031858509044820835, "train_years": [2025]}`.

### 2.9 `environment.json` (canônico, completo)

```json
{
  "code_hashes": {
    "calibration_stats.py": "08e7eee55fb4f491cad6e432d40c7cb6e311b16aa59ef5fdb6448ad3c7747799",
    "common.py": "c2e2ea1aaf5071b54a49b22dd096eee26122d3d3ffbdc72b57e722e26735fdc7",
    "drift.py": "a9003536259289593c5c411efccfa9ba928da4db042e0c5e4e297fab22429ebf",
    "experiment.py": "5ae8f62a105bed2480b24ed7d3d3f34c8fe83c1be5d7061bce43213cf1f0c651",
    "figures.py": "64ff53d81bc5f29062345ebc3cafea29d070cdf11111cc05f5701072ee7f3760",
    "identity.py": "b4187d336702642ca0cf278fa8b1d6927b7089aa14b50410e69b45c6c2a33d3c",
    "isolation.py": "6f4f23edbcb5448fb4caecb5a31e023b513e8da2ef30550fd97ba8e812b1ca0b",
    "prepare.py": "b3c0f8d66fcd1d0dda1e803be3aea96ca9e170fd8578dd691d083bd61931f1fd",
    "reproduce.py": "714575e777d0e091f57c752b659c756ae3813dc6438a3e4d1d19b513e674d37a",
    "reserved.py": "cba1ae9333362a608caf1d51fe5c619937e61cd6c36344051b90a24b6da72677",
    "run.py": "f5ee105f8801d7953f07ebe039c8a49de4ab68a797527092bb689f99fe3c591c"
  },
  "packages": {"matplotlib": "3.10.7", "numpy": "2.3.4", "pandas": "2.3.3", "pyarrow": "22.0.0", "scikit-learn": "1.7.2", "scipy": "1.16.3"},
  "python": "3.11.13"
}
```

### 2.10 `drift/`

Ver listagem em 2.0 (seção 1.1). Arquivos: `composition.csv`, `integrity_v1_reconciled.json`, `population.csv`, `schema_comparison.json`, `standardization.csv`, `standardization_cells_coarse.csv`, `standardization_cells_primary.csv`, `standardization_contract.json`, `standardization_differences.json`. Não foram detalhados (fora do pedido de esquema principal).

### 2.11 Outros arquivos do canônico (apenas nomes)

`passer_presentation.csv` (8292 bytes), `position_by_week.csv` (10192 bytes; colunas: `passer_player_id, season, week, team, positions, position_class, passes`; 243 linhas).

---

## 3. Comparação do M3 congelado

| Item | SHA-256 |
|---|---|
| `STORE/experiment-verified/frozen/M3.json` | `38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6` |
| `W/docs/plans/qb-risk-temporal-calibration-v2/evidence/frozen/M3.json` | `38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6` |
| `MODEL_SHA` em `W/research/qb_risk_lab/pipeline.py` (linha 12) | `38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6` |

**Igualdade: as três são idênticas.** Os conteúdos JSON também são iguais (`json.load` do arquivo de evidência == arquivo do STORE). O `pipeline.py` usa `MODEL=ROOT/'docs/plans/qb-risk-temporal-calibration-v2/evidence/frozen/M3.json'` (linha 11) e aborta se a hash divergir (linha 23).

Conteúdo do M3 congelado: `calibration_n` 17358, `calibration_positive` 553, `calibration_year` 2025, `kind` "context", `offset` -0.1593395890254225, `structure_sha256` `316db691f25860fd0a81972700c08504b9317ba42b1bd5aa472a8bf0942cdd8b` (igual a `models/M3_2026.json`). Atenção: `structure_sha256` (hash da estrutura) ≠ SHA do arquivo (38b9…).

---

## 4. Estado da janela reservada

### 4.1 `evidence/reserved-status.json` (W) — idêntico ao do STORE (`cmp` OK)

```json
{
  "checks": [
    {"returncode": 3, "script": "reserved.py", "stderr": "", "stdout": "PREMATURE: not before 2026-12-16T01:15:00+00:00 UTC; no PBP/FTN opened"},
    {"returncode": 3, "script": "acquire_reserved.py", "stderr": "", "stdout": "PREMATURE: no acquisition before 2026-12-16T01:15:00+00:00; no network or label files opened"}
  ],
  "freeze_sha256": "3af75413a0f8bdb9a5fa788cc3b769272deaa66f523b734aa5fe739a90b723ca",
  "no_future_network_acquisition": true,
  "no_reserved_label_files_opened": true,
  "not_before_fortaleza": "2026-12-15 22:15 -03:00",
  "not_before_utc": "2026-12-16T01:15:00+00:00",
  "not_independent_confirmation": true,
  "reserved_season": 2026,
  "weeks": [9, 13],
  "state": "PENDING_PREMATURE"
}
```

### 4.2 `OPENED.json`

**Não encontrado.** `find STORE -iname "*opened*"` não retornou nada. Também não há `OPENED.json` em W.

### 4.3 Regra de maturidade (`W/research/qb_risk_temporal_v2/reserved.py`)

- `maturity()`, linhas 21–33: para cada jogo do calendário fixado e do atualizado, `gameday + gametime` é interpretado em **America/New_York** e convertido para UTC (`last()`, linha 30). `latest = max(...)`; `not_before = latest + timedelta(days=8)` (linha 32). Se `now < not_before` → `GateError("PREMATURE: not before …; no PBP/FTN opened")` (linha 33), antes de ler PBP/FTN.
- Linhas 15–19 (`schedule_window`): janela = season 2026, REG, semanas 9–13; exige conjunto de semanas {9,10,11,12,13}, `game_id` sem duplicata e `gameday`/`gametime` não nulos.
- Linhas 86–96 (`evaluate`): recusa se `OPENED.json` existir; cria `OPENED.json` com modo `'x'` (criação exclusiva) antes de abrir labels.
- Linha 110: `preflight` chama `maturity(pinned_schedule)` sem calendário atualizado.

### 4.4 Calendário reservado (`STORE/experiment-verified/frozen/reserved_schedule.csv`, idêntico a `evidence/frozen/reserved_schedule.csv`)

- Colunas (46): `game_id, season, game_type, week, gameday, weekday, gametime, away_team, away_score, home_team, home_score, location, result, total, overtime, old_game_id, gsis, nfl_detail_id, pfr, pff, espn, ftn, away_rest, home_rest, away_moneyline, home_moneyline, spread_line, away_spread_odds, home_spread_odds, total_line, under_odds, over_odds, div_game, roof, surface, temp, wind, away_qb_id, home_qb_id, away_qb_name, home_qb_name, away_coach, home_coach, referee, stadium_id, stadium`.
- 72 linhas de jogos (semanas 9–13): W9 = 15, W10 = 14, W11 = 13, W12 = 16, W13 = 14. Sem `gameday`/`gametime` vazios. `home_score/away_score` vazios (sem placares).
- Jogo mais cedo: `2026_09_JAX_BAL`, 2026-11-05 Thursday 20:15 ET.
- **Jogo mais tarde (kickoff): `2026_13_DAL_SEA`, gameday 2026-12-07 (Monday), gametime 20:15 America/New_York = 2026-12-08T01:15:00Z.**
- `not_before = 2026-12-08T01:15Z + 8 dias = 2026-12-16T01:15:00Z`.
- Equivalente local: 2026-12-15 22:15 Fortaleza (-03) = 2026-12-15 20:15 New York (-05).
- Hoje é 2026-11-23: a reserva **ainda está prematura** (faltam ~23 dias).

---

## 5. Hashes de código (worktree W vs `freeze.json.code_hashes`)

| Arquivo | SHA-256 em W (`research/qb_risk_temporal_v2/`) | `freeze.json` | Igual? |
|---|---|---|---|
| experiment.py | `5ae8f62a105bed2480b24ed7d3d3f34c8fe83c1be5d7061bce43213cf1f0c651` | `5ae8f62a…` | **Sim** |
| common.py | `c2e2ea1aaf5071b54a49b22dd096eee26122d3d3ffbdc72b57e722e26735fdc7` | `c2e2ea1a…` | **Sim** |
| calibration_stats.py | `08e7eee55fb4f491cad6e432d40c7cb6e311b16aa59ef5fdb6448ad3c7747799` | `08e7eee5…` | **Sim** |
| reserved.py | `cba1ae9333362a608caf1d51fe5c619937e61cd6c36344051b90a24b6da72677` | `cba1ae93…` | **Sim** |

Bônus: `research/qb_interception_risk/dataset.py` e `model.py` estão listados no `freeze.json` (`9a6f86b2…`, `39a18d8f…`); não foram recalculados.

Nota: `experiment-final/` e `experiment-release/` têm `experiment.py` = `d2f7d92f…` e `experiment-final/` tem `reserved.py` = `7aff9cdb…`; ambos diferem do código atual de W. `experiment-v1/` tem `experiment.py` = `8dc55de6…`, `reserved.py` = `e83f8ac6…`, `calibration_stats.py` = `d39fa0f8…`.

---

## Não encontrado

- `same_structure_before_offset_diagnostic` em `metrics.json` do canônico: presente só em 3 de 12 registros (M3 de 2024/2025/2026); não existe em M0/M1/M2.
- `OPENED.json` em qualquer ponto do STORE e de W: não encontrado.
- Relatório de `DRIFT-AUDIT`/`drift/*` em detalhe: não lido (fora do pedido de esquema principal).
- Manifesto do próprio STORE (lista de hashes de todos os arquivos): não há; o único conjunto de hashes é `freeze.json` (code/contracts/files) e `environment.json`.
- Versão de `train_years` do M3_2025: o valor exato não foi coletado (o M3_2026/congelado tem [2023, 2024]).
