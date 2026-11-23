# Fatos para o plano MLflow: store xINT e stores de laboratório

Somente leitura. Nenhum arquivo do repositório ou dos stores foi alterado. Os valores abaixo vêm de leitura direta dos arquivos (JSON, CSV, Parquet via `python3.11 -I`) e de `grep`/`cat` nos códigos da worktree `mlflow-tracking-v1`.

Caminhos base usados:
- Store xINT: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1`
- Worktree: `/Users/pedrocollet/Downloads/NFL Sideline/.claude/worktrees/mlflow-tracking-v1`

---

## Tarefa A: store xINT

### A1. Estrutura e diretórios canônicos

Listagem (tamanhos aproximados, profundidade 2). O diretório raiz tem 289 MB. O único diretório dentro de `qb-expected-interceptions-v1/` é `20261105-v1/`.

| Caminho (relativo ao store) | Tamanho | Observação |
|---|---|---|
| `RESEARCH-CONTRACT.md`, `config.json`, `consumer-contract.json`, `sources.json`, `package-manifest.json`, `acquisition-progress.json`, `output-fix.json`, `requirements.lock` | 6 a 38 KB cada | arquivos de raiz |
| `development/` | 2,3 MB | ver A2 |
| `evaluation/` | 1,1 MB | métricas 2025 fora do ajuste |
| `final/` | 12 KB | modelo fixo B2 |
| `application/` | 8,3 MB | primeira tentativa, sem `cases/` |
| `application-complete/` | 8,6 MB | pacote completo, com `cases/` (340 KB) e `consumer/` (7,8 MB) |
| `figures/` | 2,8 MB | primeira revisão de layout |
| `figures-reviewed/` | 2,7 MB | figuras revisadas |
| `build/` | 9,9 MB | `dataset.parquet`, `splits.csv`, `manifest.json`, `coverage.json`, `audit/` |
| `current/` | 11 MB | dados brutos de 2026 (`pbp.parquet`, `ftn.parquet`, `schedule.csv`). Não é ponteiro. |
| `raw/` | 82 MB | PBP e FTN 2022 a 2025 |
| `previous-lab/` | 12 MB | cópia das fontes do laboratório |
| `lineage/` | 1,2 MB | dataset histórico e fontes v1 |
| `rosters/` | 4 MB | roster semanal 2022 a 2026 |
| `documentation/` | 84 KB | dicionários e licença |
| `reproduction-offline/` | 25 MB | reconstrução offline completa em destino novo |
| `update-replay/`, `update-replay-sources/` | 8,6 MB e 12 MB | prova de atualização só por aplicação |
| `wheelhouse/` | 97 MB | wheels para ambiente offline |

Diretórios canônicos, com evidência:

- **`application-complete/` é canônico. `application/` não é.**
  - `docs/plans/qb-expected-interceptions-v1/README.md`, linha 25: "`application-complete/` | Aplicação atual completa, tabela por jogador, previsões, casos e `consumer/`".
  - README, linha 31: "`application/` conserva a primeira tentativa, interrompida ao gravar casos por ausência do diretório; não é o pacote completo. `figures/` conserva a primeira revisão de layout. Usar somente `application-complete/` e `figures-reviewed/`."
  - `docs/plans/qb-expected-interceptions-v1/HANDOFF.md`, linha 29: "A saída `application/` foi interrompida somente ao gravar casos sem diretório; foi preservada, e `application-complete/` é a entrega válida."
  - `evidence/output-fix.json`: "Application failed only when saving case CSVs because cases/ parent was absent." Nele o `before` é `9573d498...` e o `after` é `9daee27b...`. Também registra o `original_freeze_sha256` `db3274be...`.
  - No store, `application/` não tem `cases/`. `application-complete/` tem.
  - `research/qb_expected_interceptions/run.py`, linha 145: `(out/'cases').mkdir(exist_ok=True)`. É a correção de I/O.
- **`figures-reviewed/` é canônico. `figures/` não é.**
  - README, linha 26 (`figures-reviewed/`: "PNG/SVG revisados e tabelas de suporte") e linha 31 (ver acima).
  - `reproduce.py`, linha 45: `figures(...); checks['figures']=compare(store/'figures-reviewed',out/'figures')`.
- **`reproduce.py`, linha 44**: `apply(...,out/'application'); checks['application']=compare(store/'application-complete', out/'application')`. A reprodução compara a aplicação com `application-complete/`.
- **`development/` e o diretório aninhado `development/development/`.** Não há cópia duplicada. Os arquivos de métricas e bootstrap de desenvolvimento ficam em `development/development/`. Os modelos, `selection.json`, `freeze.json` e `metrics_2023/2024.csv` ficam no nível de `development/`. README, linha 22: "`development/` | Pequena busca temporal, referências, modelos por fold, decisão e freeze original pré-2025".
- **`reproduction-offline/`**: reconstrução offline completa. README, tabela de diretórios: "Reconstrução offline completa em destino novo; recibo 156 arquivos científicos idênticos".

### A2. development/

**`development/selection.json` (completo):**

```json
{
  "C_grid_scores": [
    {"C": 0.01, "pooled_log_loss": 0.04733184184795346},
    {"C": 0.1,  "pooled_log_loss": 0.04702175615377407},
    {"C": 1.0,  "pooled_log_loss": 0.047043919591350264}
  ],
  "chosen_C": 0.1,
  "context_calibration_gate": false,
  "context_useful": false,
  "decision_data_years": [2023, 2024],
  "no_2025_or_2026_selection": true,
  "paired": {
    "B1-B0": {
      "brier":    {"delta": -0.009539585739048404, "games": 544, "high": -0.008617215918034679, "low": -0.010475062702061121, "reps": 2000, "seed": 20261105},
      "log_loss": {"delta": -0.06146061193575985,  "games": 544, "high": -0.056963674971637825, "low": -0.06606681480177314,  "reps": 2000, "seed": 20261105}
    },
    "B2-B1": {
      "brier":    {"delta": -0.0001713893217167199, "games": 544, "high": -8.445739833121175e-05, "low": -0.0002619751859861443, "reps": 2000, "seed": 20261105},
      "log_loss": {"delta": -0.0003536603283691718, "games": 544, "high": -0.0001784899453830356, "low": -0.0005405858705615894, "reps": 2000, "seed": 20261105}
    },
    "C-B0": {
      "brier":    {"delta": -0.009499561969786836, "games": 544, "high": -0.008563363367998103, "low": -0.010444502489490286, "reps": 2000, "seed": 20261105},
      "log_loss": {"delta": -0.06136603719601083,  "games": 544, "high": -0.05683871520754716,  "low": -0.06596881460397963,  "reps": 2000, "seed": 20261105}
    },
    "C-B1": {
      "brier":    {"delta": 4.002376926156791e-05, "games": 544, "high": 0.000127176426115526,  "low": -5.15506266214928e-05,   "reps": 2000, "seed": 20261105},
      "log_loss": {"delta": 9.457473974901173e-05, "games": 544, "high": 0.000317720434748721,  "low": -0.00012594789553850772, "reps": 2000, "seed": 20261105}
    },
    "C-B2": {
      "brier":    {"delta": 0.0002114130909782878, "games": 544, "high": 0.0003395184004942328, "low": 8.741382446096243e-05,  "reps": 2000, "seed": 20261105},
      "log_loss": {"delta": 0.0004482350681181835, "games": 544, "high": 0.00075288114106456,   "low": 0.00016492675650043586, "reps": 2000, "seed": 20261105}
    }
  },
  "rule": "C minimum pooled development log loss; promote only if paired game-bootstrap log-loss upper95<0 versus BOTH B1 and B2, Brier delta<=0.0001 versus both, and pooled development O/E in [0.8,1.25] in EACH FTN group. Otherwise choose B1 or B2 with lowest pooled development log loss; tie prefers B1. Never select using 2025/2026.",
  "selected": "B2"
}
```

**`development/freeze.json`** (chaves de topo, `format: xint-research-freeze-v1`):
- `code_sha256` (5 entradas): `common.py` 230b04fa..., `data.py` 30d2089f..., `evaluate.py` f3a31caa..., `risk_model.py` 21616191..., `run.py` 9573d498... (este é o `before` do output-fix; ver A1).
- `config` (dict, 18 chaves); `config_sha256` 77e200f1...; `contract_sha256` 4c5532ed...
- `evaluation_model_hashes`: B0 `9c4710c3...`, B1 `e4fbc89b...`, B2 `008f820e...`, C `4ba9e280...` (valores completos no arquivo).
- `selection`: objeto idêntico ao `selection.json` acima (9 chaves).
- `target`: `"interception"`; `not_M3`: `true`; `retrospective_temporal`: `true`.

**`development/models/` (12 arquivos, `train_years` lido de cada um):**

| Arquivo | train_years |
|---|---|
| `B0_2023.json` | [2022] |
| `B0_2024.json` | [2022, 2023] |
| `B1_2023.json` | [2022] |
| `B1_2024.json` | [2022, 2023] |
| `B2_2023.json` | [2022] |
| `B2_2024.json` | [2023] |
| `C_0.01_2023.json` | [2022] |
| `C_0.01_2024.json` | [2022, 2023] |
| `C_0.1_2023.json` | [2022] |
| `C_0.1_2024.json` | [2022, 2023] |
| `C_1.0_2023.json` | [2022] |
| `C_1.0_2024.json` | [2022, 2023] |

Os modelos C têm valores de C em {0.01, 0.1, 1.0} e anos de fold em {2023, 2024}, ou seja, 6 arquivos. `B2_2024` usa só 2023 (`[2023]`), diferente de B0 e B1, que usam 2022 e 2023. É a regra de B2, uma taxa da temporada anterior. Os arquivos B* têm formato `xint-ftn-reference-v1` (chaves: `format, global_rate, groups, kind, risk_input, target, train_years`). Os C têm chaves: `C, categorical_columns, categories, category_imputation, coefficients, feature_names, format, intercept, iterations, kind, mean, median`.

**`development/evaluation_models/`** (4 arquivos): `B0.json` [2022, 2023, 2024], `B1.json` [2022, 2023, 2024], `B2.json` [2024], `C.json` [2022, 2023, 2024].

**`development/metrics_2023.csv`** (colunas: `model,group,n,observed_interceptions,expected_interceptions,observed_expected_ratio,prevalence,mean_prediction,log_loss,brier,average_precision,roc_auc`; 12 linhas):

```csv
B0,all,18248,430,423.57085739671265,1.0151784347081882,0.023564226216571678,0.023211905819635722,0.11160642901974646,0.023009077589048018,0.023564226216571678,0.5
B1,all,18248,430,337.97646519963496,1.2722779372995952,0.023564226216571678,0.01852128809730573,0.04946218310386399,0.013589616307971283,0.4461507277435264,0.9258601831959842
B2,all,18248,430,337.97646519963496,1.2722779372995952,0.023564226216571678,0.01852128809730573,0.04946218310386399,0.013589616307971283,0.4461507277435264,0.9258601831959842
C,all,18248,430,338.86248578902905,1.2689513240120414,0.023564226216571678,0.01856984249172671,0.04953301823290259,0.013632024937379271,0.4697256933319437,0.9272049168987724
B0,ftn_1,738,375,17.130386494891162,21.8909246508733,0.508130081300813,0.023211905819635722,1.9236910353055978,0.485079538690036,0.508130081300813,0.5
B1,ftn_1,738,375,294.8862911795961,1.2716766130427264,0.508130081300813,0.3995749202975557,0.7170465688843385,0.26171812475848527,0.508130081300813,0.5
B2,ftn_1,738,375,294.8862911795961,1.2716766130427264,0.508130081300813,0.3995749202975557,0.7170465688843385,0.26171812475848527,0.508130081300813,0.5
C,ftn_1,738,375,293.07283295755224,1.2795454161195277,0.508130081300813,0.39711765983408165,0.7196475717998986,0.26277361674604016,0.5255548992221054,0.5180606060606061
B0,ftn_0,17510,55,406.44047090182147,0.13532116985782558,0.0031410622501427754,0.023211905819635722,0.03523187508262717,0.0035340347396745605,0.0031410622501427754,0.5
B1,ftn_0,17510,55,43.090174020038674,1.2763930815044464,0.0031410622501427754,0.002460889435753208,0.02132527409723977,0.0031316586131409385,0.0031410622501427754,0.5
B2,ftn_0,17510,55,43.090174020038674,1.2763930815044464,0.0031410622501427754,0.002460889435753208,0.02132527409723977,0.0031316586131409385,0.0031410622501427754,0.5
C,ftn_0,17510,55,45.78965283147684,1.2011447259148416,0.0031410622501427754,0.0026150572719290032,0.02128946937325421,0.003131368469372892,0.0042663904064544015,0.5081711413765266
```

**`development/metrics_2024.csv`** (mesmas colunas; 12 linhas):

```csv
B0,all,17740,387,414.92497793468664,0.9326987300844484,0.02181510710259301,0.023389232127096204,0.1050769893077636,0.02134168607428818,0.02181510710259301,0.5
B1,all,17740,387,312.4570777226055,1.2385701192007323,0.02181510710259301,0.017613138541296817,0.04431958779304527,0.011678536011166089,0.48787456694549225,0.92279868503402
B2,all,17740,387,354.17095457647895,1.0926926530798617,0.02181510710259301,0.01996454084422091,0.04360213977177413,0.011330849488621484,0.48787456694549225,0.92279868503402
C,all,17740,387,313.38691981317027,1.2348951903631304,0.02181510710259301,0.017665553540764954,0.04443858194746419,0.011716106627780987,0.5139853848240309,0.9250235012123247
B0,ftn_1,591,333,13.823036187113857,24.09022124317594,0.5634517766497462,0.023389232127096204,2.126363443371323,0.53764142403627,0.5634517766497462,0.5
B1,ftn_1,591,333,264.3484216795712,1.2597011091809904,0.5634517766497462,0.44729005360333535,0.7121630156286464,0.2594674179411018,0.5634517766497462,0.5
B2,ftn_1,591,333,300.30487804878044,1.1088730964467006,0.5634517766497462,0.5081300813008129,0.6912157401868038,0.24903436201627094,0.5634517766497462,0.5
C,ftn_1,591,333,263.799558523699,1.2623220518774456,0.5634517766497462,0.4463613511399306,0.7146806136463505,0.26059408504695364,0.5830035617760417,0.5109411737318714
B0,ftn_0,17149,54,401.1019417475728,0.1346291163905261,0.0031488716543238674,0.023389232127096204,0.03541809990595802,0.003548628453696229,0.0031488716543238674,0.5
B1,ftn_0,17149,54,48.10865604303439,1.122459125686148,0.0031488716543238674,0.002805333024843104,0.021303932894751472,0.003139074280418409,0.0031488716543238674,0.5
B2,ftn_0,17149,54,53.86607652769845,1.0024862303129258,0.0031488716543238674,0.0031410622501427754,0.021283658353307616,0.0031389563226152557,0.0031488716543238674,0.5
C,ftn_0,17149,54,49.58736128947129,1.0889871651925473,0.0031488716543238674,0.002891559932909866,0.02134026480162234,0.0031391117449463615,0.005500310179610431,0.5151668779045205
```

**`development/development/metrics.csv`** (desenvolvimento, pooled 2023 a 2024; mesmas colunas; 12 linhas):

```csv
B0,all,35988,817,838.4958353313993,0.9743638138370675,0.022702011781705014,0.02329931742056795,0.1083877933497849,0.02218715012789876,0.022281899038967753,0.4901473851812722
B1,all,35988,817,650.4335429222403,1.2560852817175094,0.022702011781705014,0.01807362295549184,0.04692718141402504,0.01264756438885035,0.4784322925548465,0.9249249000520521
B2,all,35988,817,692.147419776114,1.180384375721969,0.022702011781705014,0.019232728125378292,0.046573521085655864,0.01247617506713363,0.4784322925548465,0.9249249000520521
C,all,35988,817,652.2494056021993,1.252588339648531,0.022702011781705014,0.018124080404640416,0.04702175615377407,0.012687588158111919,0.4966168766377297,0.9261271047587156
B0,ftn_1,1329,708,30.95342268200502,22.873076340329902,0.5327313769751693,0.02329076198796465,2.013818494422862,0.5084535599388128,0.5471803785170253,0.5274400229263899
B1,ftn_1,1329,708,559.2347128591674,1.2660158314927354,0.5327313769751693,0.42079361388951647,0.7148748759015588,0.2607172461060596,0.5471803785170253,0.5274400229263899
B2,ftn_1,1329,708,595.1911692283768,1.1895337777236714,0.5327313769751693,0.44784888580013305,0.7055597218111683,0.2560777155932116,0.5471803785170253,0.5274400229263899
C,ftn_1,1329,708,556.8723914812513,1.2713864268198989,0.5327313769751693,0.4190160959226872,0.7174387890544157,0.26180438933132216,0.559482117767796,0.5273115168718214
B0,ftn_0,34659,109,807.5424126493944,0.13497743064960707,0.003144926281773854,0.023299645478790338,0.03532401765729178,0.00354125559433735,0.00314688087000964,0.5003113424235586
B1,ftn_0,34659,109,91.19883006307307,1.1951907708094023,0.003144926281773854,0.002631317408554,0.021314714638470855,0.003135327826855741,0.00314688087000964,0.5003113424235586
B2,ftn_0,34659,109,96.95625054773713,1.1242183911220147,0.003144926281773854,0.002797433582842469,0.021304682955178764,0.0031352694622645448,0.00314688087000964,0.5003113424235586
C,ftn_0,34659,109,95.37701412094813,1.1428330086091443,0.003144926281773854,0.0027518686090466584,0.021314602550815163,0.003135199781090178,0.004172548831374701,0.5094993295184481
```

**`development/development/paired_bootstrap.json`**: chaves de topo `all`, `ftn_0`, `ftn_1`. Cada uma tem `B1-B0`, `B2-B1`, `C-B0`, `C-B1`, `C-B2`. Cada comparação tem `brier` e `log_loss`, com `delta`, `games`, `high`, `low`, `reps`, `seed`. Em `all`: `games` = 544, `reps` = 2000, `seed` = 20261105. Em `ftn_1`: `games` = 482.

Valores de `all` (delta, IC 2,5% a 97,5%, com `low` e `high`):
- B1-B0 log_loss: -0.06146061 [-0.06606681, -0.05696367]
- B2-B1 log_loss: -0.00035366 [-0.00054059, -0.00017849]
- C-B1 log_loss: +0.00009457 [-0.00012595, +0.00031772]
- C-B2 log_loss: +0.00044824 [+0.00016493, +0.00075288]

### A3. evaluation/ (2025, fora do ajuste)

**`evaluation/metrics.csv`** (mesmas colunas; 12 linhas):

```csv
B0,all,17358,380,397.0132972812802,0.957146782241839,0.02189192303260744,0.02287206459737759,0.10533532044258173,0.021413627416028834,0.02189192303260744,0.5
B1,all,17358,380,313.1334015170755,1.213540293558489,0.02189192303260744,0.018039716644606265,0.05029813324690858,0.012358283073316162,0.4470018440457666,0.8940122201486754
B2,all,17358,380,364.50562063822224,1.0425079298767692,0.02189192303260744,0.020999286820959917,0.04985274183852961,0.012187694142121633,0.4470018440457666,0.8940122201486754
C,all,17358,380,312.3135978211461,1.2167257610653768,0.02189192303260744,0.017992487488255913,0.050521123265684885,0.012512307817632162,0.4447115779725071,0.9017488576547978
B0,ftn_1,553,305,12.648251722349805,24.114004583025235,0.5515370705244123,0.022872064597377586,2.093994650276198,0.5268306188535935,0.5515370705244123,0.5
B1,ftn_1,553,305,264.07577092511013,1.1549715406738155,0.5515370705244123,0.4775330396475771,0.6987923758639154,0.25282052694778134,0.5515370705244123,0.5
B2,ftn_1,553,305,311.58883248730956,0.9788540801199032,0.5515370705244123,0.563451776649746,0.6881136005804266,0.24748589058381482,0.5515370705244123,0.5
C,ftn_1,553,305,262.2780291820047,1.1628881037090184,0.5515370705244123,0.4742821504195383,0.7087469110215505,0.2576753405345174,0.5345885611021075,0.46401374933897405
B0,ftn_0,16805,75,384.3650455589303,0.19512700456655105,0.0044629574531389465,0.022872064597377586,0.0398947605260099,0.004781934689758478,0.0044629574531389465,0.5
B1,ftn_0,16805,75,49.05763059196535,1.5288141537818887,0.0044629574531389465,0.0029192282411166525,0.0289582155934004,0.004445422563790469,0.0044629574531389465,0.5
B2,ftn_0,16805,75,52.916788150912595,1.4173195808125887,0.0044629574531389465,0.003148871654323868,0.028849572848094095,0.004444766285397067,0.0044629574531389465,0.5
C,ftn_0,16805,75,50.03556863914145,1.4989336993630078,0.0044629574531389465,0.0029774215197346894,0.02886097089264152,0.004444759046883129,0.005695522287026698,0.5419493923092249
```

**`evaluation/calibration.csv`**: colunas `model,group,bin,n,observed_interceptions,expected_interceptions,mean_prediction,observed_rate,support_sufficient`. 132 linhas de dados, que são 4 modelos (B0, B1, B2, C) x 3 grupos (`all`, `ftn_0`, `ftn_1`) x 11 faixas de probabilidade.

**`evaluation/paired_bootstrap.json`**: chaves de topo `all`, `ftn_0`, `ftn_1`. Cada uma tem as comparações `B1-B0`, `B2-B1`, `C-B0`, `C-B1`, `C-B2`, com `brier` e `log_loss` (cada um com `delta`, `games`, `high`, `low`, `reps`, `seed`). Em `all`, `games` = 272, `reps` = 2000, `seed` = 20261105. Em `ftn_1`, `games` = 237.

Valores de `all` (delta; `low`, `high`):
- B1-B0 brier: -0.009055344342712667 [-0.010291251230269196, -0.007875428017182181]
- B1-B0 log_loss: -0.05503718719567322 [-0.060787846990993974, -0.04958355398716963]
- B2-B1 brier: -0.0001705889311945283 [-0.0003756855612259178, 4.4071373451959676e-05]
- B2-B1 log_loss: -0.000445391408378936 [-0.0008590216701725318, -5.874732661114768e-06]
- C-B0 brier: -0.008901319598396663 [-0.01014168060069969, -0.007708419944343027]
- C-B0 log_loss: -0.05481419717689688 [-0.06064766459902502, -0.04936522296369118]
- C-B1 brier: 0.00015402474431600266 [4.950274488813389e-05, 0.0002636627256199455]
- C-B1 log_loss: 0.0002229900187763447 [-4.286936170998793e-05, 0.0004811470121352986]
- C-B2 brier: 0.00032461367551053094 [9.081685060128806e-05, 0.0005632256100272463]
- C-B2 log_loss: 0.0006683814271552808 [0.00018191569249830726, 0.001159892314874447]

**`evaluation/receipt.json`** (completo):

```json
{
  "description": "Retrospective temporal out-of-fit evaluation; previously examined season",
  "evaluation_year": 2025,
  "freeze_sha256": "db3274be82a6eeaf292875097dbc0cefbf6e7fc0599515c8dcc67048776b5856",
  "no_test_correction": true,
  "selected": "B2"
}
```

O `freeze_sha256` é o mesmo `original_freeze_sha256` registrado em `evidence/output-fix.json`.

**`evaluation/players_B0.csv`, `players_B1.csv`, `players_B2.csv`, `players_C.csv`**: 96 linhas físicas cada (cabeçalho e 95 jogadores, por `wc -l`). Colunas (26):

`model_id,season,gsis_id,name,pbp_names,teams,position,position_class,period_start,period_end,weeks,eligible_passes,games,ftn_interception_worthy_passes,observed_interceptions,expected_interceptions,expected_from_ftn_1,expected_from_ftn_0,observed_in_ftn_1,observed_in_ftn_0,observed_minus_expected,difference_per_100_passes,observed_per_100_passes,expected_per_100_passes,small_support,coverage,player_interval_status`

Exemplo de linha em `players_B2.csv`: `XINT-FTN-B2-v1-evaluation2025,2025,00-0023459,Aaron Rodgers,A.Rodgers,PIT,QB,qb,...,495,16,11,7,7.7220234238399605,...`. `player_interval_status` é `not_estimated` nessa linha.

### A4. final/

**`final/fixed.json`** (completo):

```json
{
  "code_sha256": {
    "common.py": "230b04fad28052eb96cdf9dac3ef8749f0d37e1658672d97171d18918b883588",
    "risk_model.py": "2161619135fea8654aa79e9fc337adc1b333d5686a2d4e3a66f77a7539e0fec0"
  },
  "development_freeze_sha256": "db3274be82a6eeaf292875097dbc0cefbf6e7fc0599515c8dcc67048776b5856",
  "fit_years": [2025],
  "interpretation": "Retrospective conditional probability. FTN charting may know the outcome; not pre-snap prediction or responsibility.",
  "model_id": "XINT-FTN-B2-v1-fit2025",
  "model_sha256": "ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8",
  "risk_input": "is_interception_worthy",
  "selected": "B2",
  "target": "interception",
  "update_policy": "Apply only. Never fit during data update."
}
```

**`final/model.json`** (completo; 719 bytes):

```json
{
  "format": "xint-ftn-reference-v1",
  "global_rate": {"boundary_adjusted": false, "events": 380, "n": 17358, "probability": 0.02189192303260744},
  "groups": {
    "0": {"boundary_adjusted": false, "events": 75,  "fallback_global": false, "group_n": 16805, "n": 16805, "probability": 0.0044629574531389465},
    "1": {"boundary_adjusted": false, "events": 305, "fallback_global": false, "group_n": 553,   "n": 553,   "probability": 0.5515370705244123}
  },
  "kind": "B2",
  "model_id": "XINT-FTN-B2-v1-fit2025",
  "risk_input": "is_interception_worthy",
  "target": "interception",
  "train_years": [2025]
}
```

`final/` também tem `environment.json` (inventário de ambiente, fora da identidade científica). Não há pickle nem joblib.

### A5. build/

**`build/manifest.json`**: chaves de topo `coverage` (dict, 9 chaves), `dataset_sha256` = `1859ebfa9f8b317d622cad567b5c41b163a9bf41809b456bf3e9d03f6a7e5b37`, `historical_population_exact` = true, `independent_reconciliation` = true, `rows` = 79324, `sources_sha256` = `6a748c78633ae87ffa6f46c152190e6b3017092ea4b64605740f2e63bf2db95a`.

**`build/coverage.json`**: chaves `completed_games`, `completed_through`, `ftn_weeks`, `included`, `included_games`, `pbp_weeks`, `pending_games`, `scheduled_games`, `weeks`. As 9 chaves de `coverage` em `manifest.json` são as mesmas.

### A6. Hash de final/model.json

- `sha256(final/model.json)` = `ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8`.
- `research/qb_risk_outcomes_lab/package.py`, linha 5: `MODEL_SHA='ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8'`. Confere.
- O mesmo valor aparece em `web-ui/broadcast-journey/risk-outcomes/model.ts`, linha 2 (`B2_SHA`), e em `final/fixed.json`.

---

## Tarefa B: stores de laboratório

### B4. qb-risk-lab-v1 (M3)

**`qb-risk-lab-v1/current.json`** (arquivo completo):

```json
{"checkedAt":"2026-11-04T14:47:13.940173+00:00","indexSha256":"05ae0b8771a4705bc3ca6b448e7f8f7b8ea13d7e0446b8256fb2ac67f1dc8f24","packageId":"d3739e3d9103c48fda1c417a"}
```

- `packages/` tem dois diretórios: `4f8b62cecd9870e3bdb24911` (anterior) e `d3739e3d9103c48fda1c417a` (ativo, apontado por `current.json`).
- Arquivos do pacote ativo: `funnel.json` (71753 bytes), `index.json` (171912), `integrity.json` (6393), `players/` (66 arquivos `00-NNNNNNN.json`), `sources.json` (1563).

**`index.json` do pacote ativo**: chaves de topo `acquiredAt, attribution, coverage, interpretation, model, packageId, phase, pipelineVersion, players, schemaVersion, season, summary`. `players` é lista com 66 entradas. `schemaVersion` = 1, `season` = 2026, `phase` = `REG`.

**`model`**:

```json
{"calibrationYear": 2025, "id": "M3-2026-frozen-v2", "offset": -0.1593395890254225, "sha256": "38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6", "structureYears": [2023, 2024]}
```

Resumo (`summary`): `passes` 7970, `games` 121, `observed` 242, `interceptions` 170, `expected` 253.21627774175468, `expectedRate` 0.031771176630082144, `observedRate` 0.030363864491844417, `difference` -11.21627774175468, `per100` -0.14073121382377263. O rótulo `observed` = 242 coincide numericamente com os 242 passes classificados como interceptáveis do B2, mas a semântica desse campo não foi verificada no código.

**`players/00-0023459.json`** (um jogador, Aaron Rodgers): chaves de topo `packageId`, `player`, `plays` (lista com 284 registros).
- `player` tem as chaves `byGame, difference, expected, expectedRate, games, id, interceptions, name, observed, observedRate, passes, per100, positionClass, positions, teams`.
- Registro de jogada (`plays[i]`) tem as chaves `clock, date, description, distance, down, evidence, fieldPosition, gameId, id, interception, name, opponent, passerId, playId, position, positionClass, probability, quarter, scoreDifferential, team, week, worthy`.
- Exemplo de registro: `id` = `2026_01_ATL_PIT:68`, `clock` = `14:54`, `down` = 1, `distance` = 10.0, `description` = `(14:54) (Shotgun) 8-A.Rodgers pass incomplete short right.`, `interception` = false, `worthy` presente.

### B5. qb-risk-outcomes-lab-v1 (B2)

**`qb-risk-outcomes-lab-v1/current.json`** (arquivo completo):

```json
{"checkedAt":"2026-11-05T18:52:52.054734+00:00","indexSha256":"cf35c2098bc43425e2f14760ce9ae3d7ec97f37cac865c607a0fac9d32e2b1a4","packageId":"404d23007ba98d989940f117"}
```

- `packages/` tem um único pacote: `404d23007ba98d989940f117`.
- Arquivos do pacote ativo: `index.json`, `integrity.json`, `sources.json`, `players/` (66 arquivos). Não há `funnel.json`.

**`index.json` do pacote ativo**: chaves de topo `acquiredAt, attribution, comparison, coverage, interpretation, model, packageId, phase, players, presentationVersion, schemaVersion, scientific, season, summary, target`.
- `phase` = `REG`, `schemaVersion` = 1, `presentationVersion` = `1.0.0`, `target` = `observed_interception`, `season` = 2026.
- `comparison`: `m3PackageId` = `d3739e3d9103c48fda1c417a`, `onlyB2` = 0, `onlyM3` = 0, `revisedKeys` = [], `revisedPasses` = 0, `sameEligiblePasses` = true, `sharedPasses` = 7970.
- `coverage` tem chaves `completedGames, ftnWeeks, games, included, pbpWeeks, pendingGames, scheduled, scheduledGames, weeks`.
- `scientific`: `consumerIndexSha256` `83cc9429...`, `integritySha256` `1c6f3bda...`, `sourceManifestSha256` `6a748c78...`.

**`model`**:

```json
{"id": "XINT-FTN-B2-v1-fit2025", "rateClassified": 0.5515370705244123, "rateNotClassified": 0.0044629574531389465, "referenceClassified": {"events": 305, "passes": 553}, "referenceNotClassified": {"events": 75, "passes": 16805}, "referenceSeason": 2025, "sha256": "ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8"}
```

Resumo (`summary`): `eligiblePasses` 7970, `games` 121, `interceptionWorthyPasses` 242, `observedInterceptions` 170, `expectedInterceptions` 167.9617062647659, `expectedFromClassified` 133.4719710669077, `expectedFromNotClassified` 34.489735197858195, `differenceInterceptions` 2.038293735234106, `differencePer100` 0.02557457635174537.

**`players/00-0023459.json`**: chaves de topo `packageId`, `player`, `plays` (284 registros).
- `player` tem as chaves `byGame, differenceInterceptions, differencePer100, eligiblePasses, expectedFromClassified, expectedFromNotClassified, expectedInterceptions, games, id, interceptionWorthyPasses, name, observedInterceptions, positionClass, positions, teams`.
- Registro de jogada tem as chaves `clock, date, description, distance, down, evidence, fieldPosition, ftnInterceptionWorthy, gameId, id, name, observedInterception, opponent, pInterceptionGivenFtn, passerId, playId, position, positionClass, quarter, scoreDifferential, team, week`.

Diferença de nomes entre os dois stores: M3 usa `worthy`, `interception`, `probability`. B2 usa `ftnInterceptionWorthy`, `observedInterception`, `pInterceptionGivenFtn`.

### B6. Web-ui (worktree mlflow-tracking-v1)

**`web-ui/build/risk-outcomes.ts`** (40 linhas)

Rotas GET (dev server, via `outcomesBoundary`, linhas 23 a 40):
- `GET /__risk-outcomes/index.json` (linha 31). Responde o `index.json` com `checkedAt` do `current.json`.
- `GET /__risk-outcomes/packages/<24 hex>/players/00-NNNNNNN.json` (linha 35). Responde o arquivo do jogador.
- Qualquer outra URL com esse prefixo responde 404 `ABSENT` (linha 36). Jogador ausente responde 404 `PLAYER_ABSENT` (linha 37). Erro responde 503 `PACKAGE_UNAVAILABLE` (linha 38).
- Restrição de método e cabeçalhos: `allowedLabRequest` de `build/risk-lab.ts`, linha 6. Exige método `GET`, host `127.0.0.1:<porta>`, `x-risk-lab: 1`, sem `expect` nem `transfer-encoding`. Recusa com 403 `REQUEST_REFUSED` (linha 30).

Validação dos arquivos (`outcomeFiles`, linhas 8 a 18, e `activeOutcome`, linhas 19 a 22):
1. O id precisa casar com `^[a-f0-9]{24}$` (linha 9).
2. Lê `integrity.json` e, para cada arquivo listado, exige o caminho da allowlist `^(index|sources)\.json$|^players/00-\d{7}\.json$` (linha 12). Não existe `funnel.json` nessa allowlist. Compara o SHA-256 de cada arquivo com o digest do manifest (linha 13).
3. `index.json` passa por `validateOutcomeIndex`. Exige `index.packageId === id` (linha 15).
4. Cada jogador passa por `validateOutcomeDetail` (linha 16).
5. `activeOutcome` confere que o SHA-256 de `index.json` é igual a `current.indexSha256` (linha 21).

Origem do caminho da store: não vem do próprio módulo. Ele recebe `store` como parâmetro. O chamador é `web-ui/vite.risk-outcomes.config.ts`:
- linha 11: `const b2=process.env.NFL_RISK_OUTCOMES_STORE ?? '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-outcomes-lab-v1'`. Este é um caminho absoluto fixo como fallback.
- linha 10: mesmo padrão para o store do M3, `NFL_RISK_LAB_STORE`, também com fallback absoluto fixo.
- `web-ui/vite.risk-lab.config.ts`, linha 9: mesmo padrão para `NFL_RISK_LAB_STORE`.
- Na linha 13 de `vite.risk-outcomes.config.ts`, no modo `serve` é usado `outcomesBoundary(b2,port)`. No modo de build é usado `outcomesExport(m3,b2)`.

**`web-ui/build/risk-outcomes-export.ts`** (27 linhas)

`outcomesExport(store, outcomeStore)` roda em `closeBundle` (linha 16). Escreve em `web-ui/risk-outcomes-dist/local-data/<sha24>.json` (linha 17). Gera `local-routes.json` com `schemaVersion: 1`, `packageId`, `outcomePackageId` e o mapa `routes` (linha 25).

Rotas GET congeladas:
- Do M3 (linha 20): `/__risk-lab/index.json`, e `/__risk-lab/packages/<id>/players/...json`. Aceita `index|sources|funnel` e `players/00-NNNNNNN.json`. Confere SHA-256 e `active.indexSha256`.
- Do B2 (linha 21): `/__risk-outcomes/index.json`, e `/__risk-outcomes/packages/<id>/players/...json`. Usa `activeOutcome(outcomeStore)`, que já valida o pacote.
- Temporadas, histórias e curvas (linhas 22 a 24): `prepareSeason`, `prepareStory` e `prepareCurve`. As rotas `/__game-story/` e `/__curve-events/` são fixas. As rotas de temporada vêm de `freezeSeason`, e os cabeçalhos usam `X-Season-Collection` e `X-Season-Document`.
- Sem `index.json` de outra coisa. Ao final, o console imprime "frozen GET documents; public snapshots excluded" (linha 26).

**`web-ui/broadcast-journey/risk-outcomes/Lab.tsx`** (68 linhas)

Linhas com números de métrica literais no texto:

Todas estão na linha 28 (`Method`, seção "Calibração e avaliação retrospectiva"). Nenhuma outra linha do arquivo tem literal de métrica. Os números computados (`percent`, `interceptionNumber`, `index.model.*`) não são literais.

| Linha | Texto no código | Valor de origem | Arquivo e linha de origem |
|---|---|---|---|
| 28 | "380 interceptações observadas" | 380 | `evaluation/metrics.csv`, B2, all, `observed_interceptions` |
| 28 | "364,51 esperadas no total" | 364.50562063822224 (arredondado) | `evaluation/metrics.csv`, B2, all, `expected_interceptions` |
| 28 | "75 observadas" (grupo não classificado) | 75 | `evaluation/metrics.csv`, B2, ftn_0, `observed_interceptions`; também `final/model.json`, `groups.0.events` |
| 28 | "aproximadamente 52,92 esperadas" | 52.916788150912595 (arredondado) | `evaluation/metrics.csv`, B2, ftn_0, `expected_interceptions` |
| 28 | "305 observadas" (classificado) | 305 | `evaluation/metrics.csv`, B2, ftn_1, `observed_interceptions`; também `final/model.json`, `groups.1.events` |
| 28 | "311,59 esperadas" | 311.58883248730956 (arredondado) | `evaluation/metrics.csv`, B2, ftn_1, `expected_interceptions` |
| 28 | "Log loss de B2: 0,049853" | 0.04985274183852961 | `evaluation/metrics.csv`, B2, all, `log_loss` |
| 28 | "Brier: 0,012188" | 0.012187694142121633 | `evaluation/metrics.csv`, B2, all, `brier` |
| 28 | "average precision: 0,447002" | 0.4470018440457666 | `evaluation/metrics.csv`, B2, all, `average_precision` |
| 28 | "ROC-AUC: 0,894012" | 0.8940122201486754 | `evaluation/metrics.csv`, B2, all, `roc_auc` |
| 28 | "B1 teve log loss 0,050298" | 0.05029813324690858 | `evaluation/metrics.csv`, B1, all, `log_loss` |
| 28 | "a regressão contextual, 0,050521" | 0.050521123265684885 | `evaluation/metrics.csv`, C, all, `log_loss` |
| 28 | "2.000 réplicas" | `reps` = 2000 | `evaluation/paired_bootstrap.json`, todas as comparações (também `development/development/paired_bootstrap.json`) |

Os arredondamentos batem com 2 casas para as contagens esperadas e com 6 casas decimais para as métricas. Não encontrei divergência entre o texto e os CSVs.

**Testes em `web-ui/broadcast-journey/risk-outcomes/*.test.tsx`** (3 arquivos):

- `Entry.test.tsx`: 8 testes. Títulos: "two readings, history and pinned asynchronous versions" (describe), e os its "keeps old URLs on M3 ...", "restores a direct new URL ...", "never paints a late source response ...", "never paints a late player response ...", "explains source-absent player and period ...", "recovers from load failure ...", "keeps supported totals and rates distinct ...", "keeps direct pass links, exact source identifier and reference rate naming".
- `model.test.tsx`: 6 testes (`explicit outcome contract`, `rejects missing labels`, `retains unsupported periods`, `normalizes both axes`, `renders artifact-derived decomposition`, `strictly parses active reading`).
- `artifact.test.tsx`: 1 teste, "reconciles all scientific pass probabilities, periods, two contributions, DOM numbers and chart units". Lê o store de `NFL_RISK_OUTCOMES_QA_STORE` e falha se a variável não estiver definida. Confere `model.sha256 === B2_SHA`, 66 jogadores e `sameEligiblePasses === true`.

Textos de `Lab.tsx` que os testes checam (não são métricas):
- `model.test.tsx:14`: "Referência de 2025" (texto de `Calculation`, linha 19 de Lab.tsx).
- `Entry.test.tsx:18`: "Quem lançou", "Quem sofreu", e o valor `0` de `data-metric=observed-interceptions`.
- `Entry.test.tsx:19`: "Nenhuma jogada corresponde", "A jogada da URL não pertence".
- `Entry.test.tsx:21`: "Conferindo as jogadas de Beta", "Pacote de interceptações incompatível".
- `Entry.test.tsx:22`: "O lançador 00-9999999 não está neste pacote", "A semana 7 não tem cobertura", "coberturas ou revisões diferem".
- `Entry.test.tsx:23`: "não pôde ser carregada", "referência de 2025".
- `Entry.test.tsx:25`: "Taxa de referência para passes desta classificação", "não terminaram em interceptação".

Nenhum teste checa os literais numéricos de Lab.tsx linha 28. Fiz busca fixa (`grep -F`) em todos os `*.test.tsx`, `test-fixture.ts`, `model.ts`, `communication.ts` e `Metrics.tsx` por: `0,049853`, `0,012188`, `0,447002`, `0,894012`, `0,050298`, `0,050521`, `364,5`, `52,92`, `311,59`, `380`, `réplicas`, `2.000`, `Log loss`, `Brier`, `average precision`, `ROC`, `observadas`, `Como chegamos`, `Entender o cálculo`, `Como ler esta comparação`. Nenhuma ocorrência, exceto `Referência de 2025` (`model.test.tsx:14`).

---

## Não encontrado

- Nenhum teste em `web-ui/broadcast-journey/risk-outcomes/*.test.tsx` checa os valores numéricos de Lab.tsx linha 28.
- Não verifiquei o SHA-256 de `evaluation_model_hashes` contra os arquivos em `development/evaluation_models/`. Não foi pedido.
- Não confirmei a semântica do campo `observed` (= 242) no `summary` do M3. Só comparei o valor numérico.
- Não li os 66 arquivos de jogadores de cada pacote nem os parquets (`pass_predictions`, `build/dataset.parquet`, `build/splits.csv`). Só a estrutura e os valores pedidos.
