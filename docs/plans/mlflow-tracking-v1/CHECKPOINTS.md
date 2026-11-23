# Checkpoints

Registro cronológico do andamento. Cada entrada: data, fase, o que foi feito, evidência e próximo passo.

## 23/11/2026 — Fase 0 concluída

- Relatório em [PHASE-0-REPORT.md](PHASE-0-REPORT.md); plano revisado em [PLAN.md](PLAN.md).
- Worktree `.claude/worktrees/mlflow-tracking-v1`, branch `codex/mlflow-tracking-v1` @ `ed2a008`.
- Agentes criados em `.claude/agents/` ([ORCHESTRATION.md](ORCHESTRATION.md)); proteções em [GUARDRAILS.md](GUARDRAILS.md).
- Rascunho do [ADR-011](../../adr/011-local-mlflow-tracking.md) com status "proposto".
- Fatos dos stores levantados por batedores Haiku e conferidos por amostragem: [v1](facts/v1-store.md),
  [v2](facts/v2-store.md), [xINT e laboratórios](facts/xint-and-labs.md). Diretórios canônicos: v1
  `build-v2`/`development-v3`/`evaluation-v1`/`application-v1`/`figures-v4`; v2 `experiment-verified`/
  `figures-reviewed`; xINT `development`/`evaluation`/`final`/`application-complete`/`figures-reviewed`.
- Proveniência da v1 vem de três commits (`05c18ed` build, `35ac931` freeze, `910dfae` avaliação/aplicação):
  gravar como tags por etapa, não como commit único.
- Avaliação reservada da v2: 72 jogos nas semanas 9–13; último kickoff 2026_13_DAL_SEA em 08/12/2026 01:15 UTC;
  o gate só abre a partir de **16/12/2026 01:15 UTC** (conferido pelo orquestrador a partir de
  `evidence/frozen/reserved_schedule.csv`). Fase 7 fica para depois dessa data.
- Próximo: Fase 1.

## 23/11/2026 — Fase 1 concluída

- `research/mlflow_tracking/`: venv com `mlflow==3.17.2` e as mesmas versões numéricas dos experimentos
  (`requirements.txt`, `requirements.lock` com 92 pacotes), `tracking.py`, `integrity.py`, `cli.py smoke`, README.
- Testes: `9 passed` (home com espaço no caminho, sem `mlruns` no cwd, idempotência, worktree → checkout principal).
- Execução smoke `dbde09e4b1114a9181685886b4466de5` no store real, consultada pela API REST de
  `mlflow ui --host 127.0.0.1 --port 5055`; UI encerrada.
- `.gitignore`: `/editorial/local-artifacts/mlflow/` e `/editorial/local-artifacts/qb-*/`.
- Linha de base de integridade dos 5 stores (`integrity.py snapshot`) guardada no scratchpad da sessão para
  comparar ao fim de cada fase.
- Implementado por `mlflow-implementer` (Sonnet); conferido pelo orquestrador (testes rodados de novo, código lido).

## 23/11/2026 — Fase 2: importador da v1

- `import_v1.py` + `cli.py import v1`: 23 execuções (pai 1, fold 16, selection 2, evaluation 2, application 2),
  cadeia de hashes conferida antes de criar qualquer execução, `source_files.json` com 87 arquivos.
- Verificador (Haiku): 22 testes incluindo `real_store`; tags completas; nenhum `.parquet`/`.pkl`; 5 stores
  intactos contra a linha de base; reimportação idempotente.
- Revisor (Sonnet): 354 métricas e 33 artefatos idênticos à origem; `pooled_selection` reproduz
  `pipeline.develop`. Achados: **alto** — pai RUNNING deixado por um kill era tratado como importação completa;
  médios — `integrity` aceitava raiz inexistente e não via conteúdo trocado com mtime restaurado; baixos —
  rollback deixava diretórios vazios, `git_dirty` olhava o repositório inteiro, experimento Default apontando
  para o cwd, erros da CLI como traceback, dois hashes do freeze sem conferência, risco de truncamento silencioso.
- Correções em andamento para os três importadores (ver Fase 3).

## 23/11/2026 — Fase 3 (em andamento)

- `import_v2.py` (pai 1, candidate 12, selection 1; 15 testes) e `import_xint.py` (pai 1, fold 8, selection 1,
  evaluation 4, final 1, application 1; 24 testes) prontos, com teste `real_store` cada.
- Uma falha intermitente foi vista com dois agentes rodando testes ao mesmo tempo; o orquestrador rodou a suíte
  completa 4 vezes seguidas sem falha (61/61). Isolamento de estado global entre testes incluído no endurecimento.
- Em paralelo: endurecimento dos importadores (achados da revisão) e `compare.py`.
- O home real será reconstruído do zero com os importadores endurecidos (o antigo é movido para o scratchpad,
  não apagado); o índice é reprodutível a partir dos stores.

## 23/11/2026 — Fase 3 concluída

- Endurecimento (`importer_base.py` compartilhado): só pai FINISHED conta; pais RUNNING/FAILED/KILLED do mesmo
  freeze são limpos antes de importar; contagens por role conferidas; `--rebuild`; rollback remove o diretório
  inteiro da execução e só dentro do home; `integrity` formato 2 com ctime/inode e `--hash`; `git_dirty` só sobre
  `research/mlflow_tracking`; tags `importer_code_sha256` e `imported_at_utc`; Default do SQLite desativado;
  limites de tamanho de params/tags com erro; v1 confere design e contrato; fixture que isola o estado do MLflow
  por teste. Crash simulado com `os._exit(9)` no meio da importação: a chamada seguinte limpa e reimporta completo.
- `compare.py` reaplica as três regras de seleção só com números do MLflow: **31 PASS, 0 FAIL** no home real
  (v1 C=0.1/0.1; v2 M3; xINT B2 com C=0.1 e `context_useful=false`).
- Suíte: 98 testes, 3 rodadas seguidas verdes.
- Home real reconstruído do zero (antigo movido para o scratchpad): `qb-iw-baseline-v1` pai
  `6b000d8bf68548e39d3d6244c16ef376` (1/16/2/2/2), `qb-risk-temporal-v2` pai `6e4dd3c93a914cc6910fea1358cb84e1`
  (1/12/1), `xint-ftn-v1` pai `640e7dcfd9f94e918a21c99e22b0d9fe` (1/8/1/4/1/1). Reimportação: `created=false` nos três.
- Stores conferidos com hash completo (linha de base formato 2) antes e depois: sem diferença.
- Conferido pelo orquestrador: `compare` 31/0, `import all` idempotente, nenhum diff em código congelado.

## 23/11/2026 — Fase 4 concluída

- `registry.py` + `model_code/m3_pyfunc.py` e `model_code/b2_pyfunc.py` (pyfunc *models from code*,
  `loader_module: mlflow.pyfunc.loaders.code_model`); artefato = JSON congelado; `model.py` congelado da v1 vai
  em `code_paths` e é carregado por caminho com nome único, conferindo o sha256.
- Home real: `qb-iw-m3` v1 (execução `f83dc9a9722049668e4399665b0686c4`) e `xint-ftn` v1 (execução
  `64f9250a07b64c93a12ffbd48b16f1d0`), alias `champion`; registro idempotente; execuções role=model fora da
  hierarquia importada (sem `mlflow.parentRunId`), então `import all` e `compare` continuam iguais.
- `verify-models` (exit 0): M3 pelo alias == `predictions.parquet` 2026 (diferença 0,0 em 7106 linhas) e ==
  pacote ativo do laboratório (4,2e-17 em 7970 jogadas); B2 == `pass_predictions.parquet` (0,0) e == pacote de
  desfechos (2,2e-16); log loss recalculado == métrica registrada (diferença relativa 0,0) nos dois; B2
  reimplementado == `risk_model.predict` original bit a bit; nenhum `.pkl` no home (conferido pelo orquestrador).
- Limite conhecido: o `MLmodel` guarda caminhos absolutos desta máquina; mover o home exige reregistrar.
- Suíte: 108 testes.

## 23/11/2026 — Fase 5 concluída

- `provenance.py` + `cli.py provenance [--check]` geram `web-ui/broadcast-journey/risk-outcomes/provenance.json`
  (D8a) só a partir do MLflow: para cada modelo `champion`, versão, execução role=model, pai de origem, freeze,
  commit do importador e cada número exibido com `runId` e chave de métrica. Determinístico (`changed=false` e
  mtime intacto na segunda geração).
- Números do B2/B1/C e réplicas conferidos contra `evaluation/metrics.csv` e `paired_bootstrap.json`;
  M3 2025/2026 contra `experiment-verified/metrics.json` (igualdade exata).
- `Lab.tsx` do laboratório de desfechos: os números digitados da linha 28 saíram; o componente `Evaluation` lê a
  proveniência validada (sha do B2 == `B2_SHA` e == modelo do pacote ativo) e renderiza o mesmo texto de antes,
  caractere a caractere (teste), mais "Fonte: execução MLflow … · modelo xint-ftn v1". Proveniência inválida →
  texto neutro sem números. Teste falha se voltar a haver literais de métrica no código-fonte.
- Web-ui: `npm ci` (Node 24) sem mudar o lockfile; 23 testes do laboratório; lint sem erro novo. No `npm test`
  inteiro, `artifact.test.tsx` exige `NFL_RISK_OUTCOMES_QA_STORE` (não alterado; passa com a variável).

## 23/11/2026 — Fase 6 (em andamento)

- `.github/workflows/research-ci.yml`: job do módulo MLflow (testes `real_store` se pulam sem stores) e matriz
  dos 7 pacotes de pesquisa; `fetch-depth: 0` para o teste da v2 que faz `git diff d654bd6`. Seis testes que
  leem stores reais por caminho absoluto fixo em código congelado (`qb_risk_outcomes_lab` 4,
  `qb_progression_lab` 2) estão desselecionados por id, com comentário.
- Clone limpo simulado no scratchpad com `sandbox-exec` negando acesso aos stores reais: tudo verde
  (mlflow_tracking 112 passed/7 skipped; experimentos 23/24/33/12/2/13/42 passed). Locks sem pacotes
  exclusivos de macOS; a primeira execução no GitHub confirmará a instalação no Linux.
- Linha do ADR-011 (proposto) na §11 do `Spec.md`.

## 23/11/2026 — Segunda rodada de revisão e correções

- Revisor (Sonnet) das Fases 2–3: nenhum achado alto; 500 métricas da v2 e 633 do xINT idênticas à origem;
  regras do `compare` fiéis aos originais em 40.000 casos aleatórios de fronteira. Médios corrigidos:
  `--rebuild` passou a importar a nova antes de apagar a antiga (falha no meio mantém a antiga intacta);
  teste de hash do `integrity` agora prova o hash; cadeia de hashes completa (contratos do xINT e da v2,
  `selection.json == freeze.selection`, referências ausentes viram erro). Baixos corrigidos: `integrity` com
  `onerror` e symlinks registrados sem seguir; aviso quando o código do importador mudou; erros da CLI sem
  traceback; experimento deletado restaurado; bootstrap pareado de desenvolvimento ftn_0/ftn_1 do xINT
  importado; registro cria nova versão quando a origem foi reconstruída; warnings próprios eliminados.
- Os modelos passaram à versão 2 (anotação de tipo no código do modelo); previsões e métricas idênticas.
- Home real reconstruído com `--rebuild` (backup no scratchpad); `provenance.json` regenerado: só mudaram
  `runId`, `sourceParentRunId` e `version`.
- Suíte: 162 testes, duas rodadas verdes, sem warnings próprios.

## 23/11/2026 — Verificação final

- Verificador (Haiku): 162 passed; `import all` e `register all` idempotentes sem aviso; `verify-models` exit 0;
  `compare` 31 PASS / 0 FAIL; `provenance --check` exit 0; contagens ativas corretas, sem pai duplicado nem
  RUNNING; aliases `champion` → v2 com origem ativa; nenhum `.pkl/.pickle/.joblib/.parquet` no home; 5 stores
  idênticos por hash à linha de base; nenhum diff em código congelado; nenhum caminho absoluto fixo no módulo.
- Orquestrador: laboratório de desfechos rodado localmente (`run-local.sh`) e lido no navegador: parágrafo de
  avaliação igual ao anterior, com "Fonte: execução MLflow fcfc4dae · modelo xint-ftn v2"; essa execução existe,
  está FINISHED e tem `all.log_loss = 0.04985274183852961`; console sem erros. Vitest do laboratório 23/23 com
  `NFL_RISK_OUTCOMES_QA_STORE`; lint sem erro novo; `tsc -p tsconfig.journey.json` ok.
- Revisor final (Sonnet): nenhum erro de número, pickle ou reprodução; modelo pelo alias em processo Python
  limpo reproduz o laboratório (2e-16). Achados restantes (1 médio: kill na janela entre "nova pronta" e "antiga
  apagada" deixava duas importações silenciosas; 4 baixos) em correção.
- Capturas da interface (`mlflow ui` em 127.0.0.1) salvas em `captures/` e exibidas no README do plano.

## 23/11/2026 — Terceira rodada de correções e fechamento

- Corrigidos os achados da revisão final: dois pais FINISHED do mesmo freeze (kill na janela do rebuild)
  agora fazem `import` falhar pedindo `--rebuild` e o `compare` reprovar; `find_parent` determinístico;
  `verify-models`/`provenance` mandam rodar `register` quando a origem do champion foi reconstruída; aviso
  (não falha) quando o pai v2 aponta para um pai v1 inativo; `register` limpa versões/execuções órfãs de um
  kill e não deixa resíduo em falha; testes de fronteira do `compare` chamam `experiment.select` e
  `run.develop` originais.
- Home real reconstruído pelo orquestrador (`import all --rebuild`; backup no scratchpad), `register all`
  (modelos v3, origem ativa; segunda chamada `created=false`), `verify-models` exit 0, `compare`
  **34 PASS / 0 FAIL, nenhum aviso**, `provenance.json` regenerado (só `runId`/`version`) e `--check` ok.
- Conferido pelo orquestrador: suíte Python **173 passed**; vitest do laboratório 23/23; 5 stores idênticos
  por hash à linha de base; nenhum diff em código congelado; nenhum `__pycache__` em diretórios congelados.
- Pendências: primeira execução do CI no GitHub; Fase 7 (gate em
  16/12/2026); decisões D3 (alteração do laboratório) e aceitação do ADR-011 pelo dono.
