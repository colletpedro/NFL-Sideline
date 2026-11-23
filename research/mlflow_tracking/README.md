# research/mlflow_tracking

Índice local (SQLite + arquivos) dos experimentos de ML, sem servidor. Plano: `docs/plans/mlflow-tracking-v1/`.

## Instalação

```bash
python3.11 -m venv research/mlflow_tracking/.venv
research/mlflow_tracking/.venv/bin/pip install -r research/mlflow_tracking/requirements.txt
```

`requirements.lock` é o `pip freeze` ordenado do ambiente testado. Os módulos são planos (`tracking.py`,
`integrity.py`, `cli.py`); o `conftest.py` da pasta põe-na no `sys.path`, então rode os testes assim:

```bash
research/mlflow_tracking/.venv/bin/python -m pytest research/mlflow_tracking -q
```

## Variáveis

- `NFL_MLFLOW_HOME`: home do MLflow (padrão `<checkout principal>/editorial/local-artifacts/mlflow`).
- `NFL_RESEARCH_STORES`: raiz dos stores científicos (padrão `<checkout principal>/editorial/local-artifacts`).

O checkout principal é resolvido por `git rev-parse --git-common-dir`, então funciona dentro de worktrees.

## Smoke

```bash
cd research/mlflow_tracking && .venv/bin/python cli.py smoke        # aceita --home
```

## Abrir a UI (somente 127.0.0.1)

```bash
.venv/bin/mlflow ui --host 127.0.0.1 --port 5055 --backend-store-uri sqlite:////<home>/mlflow.db
```

## Integridade dos stores

```bash
python integrity.py snapshot --root R --out antes.json [--hash]   # --out fora de R; exit 2 se R não é diretório
python integrity.py compare --before antes.json --after depois.json   # exit 1 se houver diferença, 2 se inválido
```

Manifesto formato 2: `{"format": 2, "root": ..., "entries": {rel: [tamanho, mtime_ns, ctime_ns, inode]}}`; com `--hash`
cada arquivo regular ganha o sha256 como quinto campo. `compare` usa todos os campos presentes nos dois e recusa
manifestos vazios, de formatos diferentes ou um com hash e o outro sem (exit 2). Erro ao percorrer um diretório
(permissão etc.) aborta o snapshot. Symlinks nunca são seguidos: a entrada registra o alvo (`os.readlink`) no sexto
campo (`[tam, mtime, ctime, ino, null, alvo]`), então trocar o alvo é uma mudança.

## Importar

```bash
.venv/bin/python cli.py import {v1,v2,xint,all} [--store PATH] [--home PATH] [--rebuild]
.venv/bin/python cli.py compare [--home PATH] [--format md|json] [--out PATH]   # exit 1 se a conferência falhar
```

`all` importa v1, depois v2, depois xint (`--store` só vale para um alvo). Erros de importação saem em stderr com
exit 2. Os stores são somente leitura e ficam em `<NFL_RESEARCH_STORES>/<store>` (v1: `qb-interception-risk-baseline-v1/20261104-v1`,
v2: `qb-risk-temporal-calibration-v2/20261104-v2`, xint: `qb-expected-interceptions-v1/20261105-v1`).

Antes de importar cada alvo confere a cadeia de hashes (a v1 também confere `design.json` e `RESEARCH-CONTRACT.md` da
worktree) e o `chosen_C` contra o argmin recalculado. Arquivo de referência ausente é erro (nunca pulado em silêncio):
v1 = `design.json` + `RESEARCH-CONTRACT.md`; v2 = todos os contratos de `freeze.contracts` (`protocol.json`,
`EXPERIMENT-PROTOCOL.md`, `RESERVED-EVALUATION.md`); xINT = `RESEARCH-CONTRACT.md` (`freeze.contract_sha256`) e
`development/selection.json == freeze.selection`. Qualquer exceção inesperada vira `ImporterError` com contexto, e o
CLI imprime `erro (<alvo>): ...` com exit 2, sem traceback. Estrutura criada: v1 = 1 pai + 16 `fold` + 2 `selection` +
2 `evaluation` + 2 `application`; v2 = 1 pai + 12 `candidate` + 1 `selection`; xint = 1 pai + 8 `fold` + 1 `selection` +
4 `evaluation` + 1 `final` + 1 `application`. Parquets nunca viram artefato (só entram, com hash, em `source_files.json`).
Toda execução leva as tags `importer_code_sha256` e `imported_at_utc`; `git_dirty` olha só `research/mlflow_tracking`.
Parâmetros acima de 6000 caracteres, tags acima de 8000 ou chaves fora do padrão do MLflow são erro (nunca truncados).

### Idempotência, interrupção e `--rebuild`

- A chave é o `source_freeze_sha256`. Um pai **FINISHED** com as contagens por role esperadas = já importado
  (`created=false`).
- Pai RUNNING/FAILED/KILLED (importação interrompida) é apagado, com as filhas e os diretórios de artefatos,
  e a importação refeita do zero. Falha no meio também desfaz tudo (execuções e diretórios `<run_id>`); erros de
  limpeza são anexados à exceção, e nada fora de `<home>/artifacts` é apagado.
- Pai FINISHED com contagens divergentes é erro com a sugestão `--rebuild`. O `--rebuild` importa a versão nova
  PRIMEIRO (rollback próprio se falhar) e só então apaga a antiga: o home nunca fica sem uma importação completa
  daquele freeze; outras importações (outros freezes) nunca são tocadas.
- Um `--rebuild` interrompido (kill) entre "nova importação pronta" e "antiga apagada" deixa dois pais FINISHED do
  mesmo freeze. `import` sem `--rebuild` então falha com erro claro pedindo `--rebuild` (nunca responde `created=false`
  em silêncio); `compare` reprova o experimento ("um só pai FINISHED por freeze"); `import <alvo> --rebuild` recupera e
  mantém só uma importação completa. `tracking.find_parent` escolhe de forma determinística o pai mais recente
  (`imported_at_utc`, `start_time`, `run_id`).
- Depois de `import v1 --rebuild`, o pai v2 pode ficar com a tag `upstream_v1_parent_run_id` apontando para o pai v1
  antigo (agora inativo). `compare` não reprova: mostra um AVISO (seção "Avisos" do markdown e lista `warnings` no JSON).
  Para refazer o elo: `cli.py import v2 --rebuild` e depois `cli.py register m3` (o M3 nasce no experimento v2 e sua
  versão guarda o pai v2).
- Se o pai FINISHED existente foi importado com outro `importer_code_sha256` (código do importador mudou), sai um
  aviso em stderr sugerindo `--rebuild` (não falha). O índice SQLite não é fonte de verdade: adulteração direta nele
  (métricas/tags alteradas à mão) não é detectada pela idempotência; use `compare`/`verify-models` ou `--rebuild`.
- Experimento deletado com o mesmo `artifact_location` é restaurado; com outro, erro claro.
- O experimento Default do SQLite (que apontaria para `<cwd>/mlruns`) é marcado como deletado: `start_run` sem
  experimento falha em vez de escrever no cwd.
- **Concorrência:** não rode duas importações ao mesmo tempo no mesmo home; a limpeza de execuções RUNNING apagaria a
  importação da outra.

Testes contra os stores reais: `pytest -m real_store`.

## Registrar os modelos (Fase 4)

```bash
.venv/bin/python cli.py register {m3,b2,all} [--home PATH]   # idempotente; cria a versão e o alias champion
.venv/bin/python cli.py verify-models [--home PATH]          # exit 1 se qualquer conferência falhar
```

`qb-iw-m3` (M3 congelado da v2, experimento `qb-risk-temporal-v2`) e `xint-ftn` (B2 do xINT, experimento `xint-ftn-v1`)
são pyfunc *models from code* (`model_code/m3_pyfunc.py`, `model_code/b2_pyfunc.py`): nada de pickle. O artefato é o
JSON congelado do store (`M3.json`, `final/model.json`); o M3 empacota em `code/` o `qb_interception_risk/model.py`
congelado, carregado por caminho sob o nome `qb_iw_frozen_model` (o nome genérico `model` pode colidir). Cada registro
cria uma execução `role=model` (sem `mlflow.parentRunId`; guarda `source_parent_run_id`) e a versão leva as tags
`model_sha256`, `model_code_sha256`, `source_store`, `source_run_id` (+ `v1_model_py_sha256` no M3). Rodar de novo
com os mesmos hashes só garante o alias, desde que a execução do modelo e o pai de origem (`source_parent_run_id`, também
tag da versão) ainda existam e estejam ativos; depois de um `import --rebuild` o pai muda e `register` cria nova
execução e nova versão e move o alias `champion`. `verify-models` e `provenance` acusam um `champion` cuja execução de
origem não está mais ativa e mandam rodar `cli.py register <alvo>`. Um `register` interrompido entre `log_model` e as
tags da versão deixa uma versão sem `model_sha256`, com execução `role=model` e diretório de modelo órfãos: o próximo
`register` apaga de verdade (versão, modelo logado, execução e diretórios dentro do home) o que sobrou, exceto o champion;
uma falha depois de `log_model` também apaga tudo o que criou. `verify-models` recarrega `models:/<nome>@champion` e confere previsões
(atol 1e-12) contra `predictions.parquet`/`pass_predictions.parquet` e contra os pacotes ativos dos laboratórios,
o log loss contra a métrica no MLflow (rtol 1e-12), o SHA do JSON e a ausência de `.pkl`.

## Proveniência do laboratório de desfechos (Fase 5)

```bash
.venv/bin/python cli.py provenance [--home PATH] [--out PATH]            # gera; só reescreve se o conteúdo mudar
.venv/bin/python cli.py provenance [--home PATH] [--out PATH] --check    # exit 1 se o arquivo versionado diferir
```

Gera `web-ui/broadcast-journey/risk-outcomes/provenance.json` só a partir do MLflow (aliases `champion` de `xint-ftn`
e `qb-iw-m3`): `schemaVersion: 1` e, por modelo (chave = sha256 do JSON do modelo), nome, versão, `run_id` da execução
`role=model`, `source_parent_run_id`, experimento, `source_freeze_sha256`, `source_store` e `git_commit` do importador.
Os números do laboratório ficam em `numbers`, cada um com `value`, `runId` e a chave de origem (`metricKey`, ou
`paramKey` para as 2.000 réplicas do bootstrap pareado, `paired.all.B2-B1.log_loss.reps`): avaliação 2025 do B2
(grupos `all`, `ftn_0`, `ftn_1`), log loss de B1 e C, e as métricas das candidatas 2026·M3 e 2025·M3. O conteúdo é
determinístico (chaves ordenadas, sem horário de importação). Falta de alias, execução, métrica ou parâmetro é erro
claro (exit 2). O `run_id` muda quando o home é reconstruído (`import --rebuild`), então regenere o arquivo e revise o
diff antes de commitar. O laboratório valida o arquivo (sha do B2 igual ao do pacote ativo, números finitos) e, se
algo não bater, mostra texto neutro em vez de números.
