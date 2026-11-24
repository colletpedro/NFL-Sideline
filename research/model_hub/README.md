# Hub de modelos

<!-- BEGIN aquisicao-build (hub-implementer H1/H2) -->
## Aquisição e feature store

Todos os comandos rodam de `research/model_hub` com `.venv/bin/python cli.py ...`. O home do hub é
`NFL_HUB_HOME` (padrão: `<checkout principal>/editorial/local-artifacts/model-hub`); `--home` sobrescreve.

```bash
.venv/bin/python cli.py acquire [--season 2025 ...] [--refresh] [--no-refresh-current] [--allow-shrink]   # única etapa com rede (nflverse)
.venv/bin/python cli.py migrate                                                           # layout antigo de raw/ -> por sha256 (idempotente)
.venv/bin/python cli.py build [--acquisition ID] [--allow-partial]                         # offline
.venv/bin/python cli.py status
```

### Aquisição (`acquire.py`)
- Padrão: temporadas 2011..corrente (mar-dez = ano atual; jan/fev = ano anterior). **Cache bruto endereçado por conteúdo
  (H-D10)**: `HUB/raw/{pbp,schedules}/season=YYYY/<sha256>.parquet`, nunca sobrescrito; o manifesto aponta esses caminhos.
- Protocolo: limpa temporários órfãos (`.staging-PID-*`, `.x.tmp-PID` de processos mortos); baixa tudo para um diretório de
  staging validando colunas (`REQUIRED_*_COLUMNS`), contagens e encolhimento; só depois move cada arquivo para o nome
  definitivo (`os.replace`; se o sha já existe, reaproveita); grava o manifesto e, por último, `current.json`. Falha antes
  disso deixa manifesto, `current.json` e `raw/` exatamente como estavam. Um manifesto antigo continua reconstruível depois de
  um refresh que mude os dados (os arquivos antigos seguem lá; apague manualmente o que quiser reciclar).
- Temporada passada com arquivo presente não é rebaixada (a menos que `--refresh`); a corrente é rebaixada por padrão.
  O reaproveitamento olha a última entrada conhecida (manifestos de formato atual, o atual primeiro).
- PBP **ou schedules** vazio/404 da temporada corrente/futura não é fatal (mantém a entrada anterior, ou fica sem a
  tabela; ex.: março-maio, antes da publicação); para temporada passada é fatal, e qualquer outro erro também.
- **Subconjunto herda** (M-1): `acquire --season N` mantém no novo manifesto as entradas (mesmos arquivos/sha256) das
  temporadas não pedidas do manifesto atual; `build` recusa manifesto que não cubra 2011..corrente de forma contínua
  (schedules em todas, PBP em todas menos a última), salvo `--allow-partial`.
- **Encolhimento**: refresh que reduz as linhas de uma tabela/temporada em mais de 1% falha com erro claro, salvo
  `--allow-shrink`.
- Manifesto `HUB/acquisitions/<id>.json` (`format` 2: `path`, sha256, bytes, linhas, colunas, `max_game_date` e
  `weeks_with_pbp` do PBP, `fetched_at_utc` ou original preservado). `acquisition_id` = sha256 do conteúdo sem timestamps
  nem versões de biblioteca: mesmos arquivos, mesmo id.
- **Migração do layout antigo** (`raw/<tipo>/season=Y/<tipo>.parquet`, `format` 1): `cli.py migrate` (também executada por
  `acquire` e `build`) cria hardlinks no endereço do sha, regrava cada manifesto antigo no formato atual e remove o antigo e
  os arquivos antigos. **O `acquisition_id` muda** (`path`/`format` fazem parte do conteúdo); o id antigo fica em
  `migrated_from` e ainda resolve (`resolve_acquisition`). Manifesto antigo cujo arquivo foi alterado fica intacto e é
  listado como irrecuperável. O `build_id` muda junto (depende do id e do código).

### Feature store (`features.py`)
**Siglas (H-D9)**: o PBP traz sempre as siglas atuais (LV, LAC, LA) e o schedule as históricas (OAK 2011-2019, SD 2011-2016,
STL 2011-2015); sem tratamento, 160 linhas de `team_game` ficavam invertidas. `FRANCHISE_ALIASES = {OAK: LV, SD: LAC,
STL: LA}` (único lugar) é aplicado a `posteam`, `defteam`, `home_team`, `away_team` e `td_team` de `plays` e a
`home_team`/`away_team` de `games`; a sigla do schedule fica em `games.home_team_raw`/`away_team_raw`. O `game_id` não muda
(`2011_01_PHI_STL`). Conferido nos Parquets reais: não há outra sigla histórica (JAX é a única forma de Jacksonville; LAR
não ocorre). `team_game` e `team_asof` usam a franquia atual, então o histórico (EWM) atravessa a mudança de cidade, e
`build_team_game` falha se alguma linha tiver time fora do jogo.

`build` lê só os arquivos do manifesto (sha256 conferido), escreve em diretório temporário e renomeia para
`HUB/features/<build_id>/` (`plays`, `games`, `team_game`, `team_asof` `.parquet` + `manifest.json`). `build_id` =
sha256(acquisition_id, sha256 de features.py, parâmetros). Build idêntico e íntegro é reutilizado; o build é
byte-reprodutível (linhas em ordem determinística, sem timestamps).

**Alvo `next_score` (`plays`)** — evento de pontuação: `touchdown==1` (time = `td_team`, 7), `field_goal_result=='made'`
(time = `posteam`, 3), `safety==1` (time = `defteam`, 2, exceto quando o placar do `posteam` sobe 2 na jogada
(`posteam_score_post - posteam_score == 2`): punt com recuo do retornador no próprio end zone, 5 casos reais, em que o
chutador pontua; sem variação observável vale o `defteam`). PAT e conversão de 2 pontos não são eventos. Para cada jogada,
o primeiro evento na mesma (`game_id`, `half`) a partir da jogada atual, inclusive, na perspectiva do `posteam` da
jogada: `TD/FG/SAFETY` (+7/+3/+2) se pontua o `posteam`, `OPP_*` (-7/-3/-2) caso contrário, `NO_SCORE` (0) se a metade
acaba sem evento. `half`: 1 = qtr 1-2, 2 = qtr 3-4, 3 = prorrogação. Sem `posteam`/`qtr`: nulo.
`ep_eligible`: `posteam` e `yardline_100` não nulos, `down` 1..4, `play_type` não nulo e fora de {kickoff, extra_point},
sem `two_point_attempt`.

**`team_game`** — jogadas com `play_type` in {pass, run}, `epa` não nulo, `posteam`/`defteam` não nulos. `off_*` por
`posteam`, `def_*` por `defteam` (o que a defesa sofreu); médias por jogada; `off_pass_rate` = pass/(pass+run);
pontos vêm do schedule. Conversões de 2 pontos (`two_point_attempt == 1`) ficam de fora.

**`team_asof`** — uma linha por (jogo, time) de todos os jogos de `games`, inclusive futuros, usando só `team_game`
do mesmo time com `kickoff_utc` estritamente anterior. Por métrica (`off_epa`, `def_epa`, `off_success`,
`def_success`, `pass_rate`, `point_diff`): `season_*` (média da temporada até ali), `last3_*` (3 jogos mais recentes,
atravessa temporadas) e `ewm4_*` (média exponencial, meia-vida de 4 jogos, atravessa temporadas). Sem jogo anterior:
nulo, nunca zero. Teste de vazamento em `tests/test_features.py`.

**Qualidade** — o build confere (testes `real_data`) que, em todos os jogos completos, os pontos por time reconstruídos
das jogadas (TD 6, FG 3, safety 2, PAT 1, conversão de 2) batem com o placar do schedule. `half` sai do `qtr` de cada
jogada e é idêntico ao `game_half` do nflverse (0 divergências nos dados reais). O nflverse numera algumas jogadas fora de
ordem cronológica (em 131 jogos o `qtr` diminui ao percorrer por `play_id`); isso não altera nenhum rótulo, e a contagem
fica em `features/<build_id>/manifest.json` (`qa.games_qtr_out_of_order`).

Testes: `.venv/bin/python -m pytest research/model_hub -q` (offline, sintéticos). Os `@pytest.mark.real_data` usam o
cache real do hub e são pulados se faltar.
<!-- END aquisicao-build -->

<!-- BEGIN ep (hub-implementer H4) -->
## Expected Points v1 (`hub-ep`)

```bash
.venv/bin/python cli.py backtest ep [--force]                  # ~100 s; MLflow experimento hub-ep
.venv/bin/python cli.py register ep                            # ajusta o selecionado em TODAS as jogadas -> hub-ep@champion
.venv/bin/python cli.py predict ep                             # HUB/predictions/ep/<build_id>/plays_ep.parquet
.venv/bin/python cli.py card ep --out docs/plans/model-hub-v1/cards/ep.md
```

- **Tarefa**: próximo evento de pontuação na mesma metade, 7 classes (`TD, FG, SAFETY, OPP_TD, OPP_FG, OPP_SAFETY,
  NO_SCORE`), na ótica do time com a posse; `EP = Σ p·pontos` (7, 3, 2, -7, -3, -2, 0). Jogadas `ep_eligible`
  (REG+POST) sem nulos nas colunas brutas, com alvo e com as 7 probabilidades do nflverse utilizáveis (não nulas, soma > 0): as
  demais saem para TODOS os modelos (comparação sobre as mesmas jogadas) e são contadas por motivo (`dropped_invalid_rows`,
  `dropped_by_reason`).
- **Splits**: walk-forward por temporada, treino 2011..s-1, teste 2018..última temporada (2026 parcial).
- **Regra fixada antes**: menor `log_loss` pooled entre os candidatos, precisando bater o melhor baseline
  (`min_improvement=0`).
- **Baselines (entram na regra)**: `freq` e `freq_field_down` (faixa de 10 jardas × down; célula com < 200 jogadas usa a
  faixa; faixa com < 200, a global; suavização de Laplace +1 por classe). **Referência (fora da regra)**: `nflverse` =
  as 7 probabilidades do PBP renormalizadas; foi treinada com dados que incluem os anos de teste, portanto é otimista.
- **Candidatos** (`models/ep.py`): `logit_basic`, `logit_state`, `logit_hinge` (logística multinomial sklearn, lbfgs,
  `max_iter=2000`, erro se não convergir, padronização com média/desvio do treino).
- **Receita única de features**: `model_code/ep_pyfunc.py` (importada pelo treino e copiada para o modelo
  registrado). O pyfunc recebe as colunas brutas (`RAW_COLUMNS`), devolve `p_<classe>` ×7 + `ep`; passe a entrada por
  `ep_pyfunc.raw_frame(df)` (schema `double`). Nulos levantam erro, nunca são imputados.
  Limite do MLflow: a validação de schema roda ANTES do pyfunc e recusa int64/bool (só aceita `double`), então não dá
  para converter dentro do modelo; sempre passe a entrada por `raw_frame`:

  ```python
  import sys; sys.path.insert(0, "research/model_hub/model_code")
  import ep_pyfunc, mlflow
  model = mlflow.pyfunc.load_model("models:/hub-ep@champion")
  probs = model.predict(ep_pyfunc.raw_frame(plays))   # plays: DataFrame com ep_pyfunc.RAW_COLUMNS (int/bool/float)
  ```
- **Métricas extras** (via hook `extra_metrics`/`extra_artifacts` do `run_backtest`): `ep_mae`, `ep_rmse` e calibração do EP por
  decis (artefato `extras/<modelo>/ep_calibration.json` no pai). `references=` do `run_backtest` guarda o papel
  `reference`.
- **Idempotência**: `config_sha256` cobre config, `data_sha256` (impressão digital das linhas usadas pelos splits e das
  colunas declaradas por `columns()` de cada modelo, independente da ordem das linhas; `data_id` é só rótulo) e o hash do
  código (arquivo da classe de cada modelo + `ep_pyfunc.py` + `ep.py`). Mudar dados usados, `fit` ou receita reexecuta.
  Splits de teste não podem se sobrepor; métrica indefinida num split (AUC com classe única) é omitida com aviso.
- **Registro**: `register ep` só aceita o `selected_model` do pai, com hiperparâmetros idênticos aos do `config.json`; o
  run final grava `selected_model`, `hyperparams_sha256`, `train_data_sha256` e o pai. Os parâmetros do modelo final
  NÃO são comparados com os `fitted.json` das dobras (reajuste com todos os dados).
- **Atenção**: `predict ep` grava em `meta.json` `in_sample` (verdadeiro só se os dados previstos têm a mesma impressão
  digital dos do ajuste do champion), `champion_version`, `source_run_id` e `build_id`; para avaliação use o backtest.
  `card ep` exige que o pai do backtest seja do build atual (ou `--run-id`).
<!-- END ep -->
