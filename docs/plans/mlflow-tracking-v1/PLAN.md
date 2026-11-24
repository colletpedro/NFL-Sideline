# Plano: MLflow no NFL Sideline

Revisão 2 · 23/11/2026 · documento vivo. Mudanças de rumo entram em [DECISIONS.md](DECISIONS.md) e o andamento em
[CHECKPOINTS.md](CHECKPOINTS.md). Regras obrigatórias em [GUARDRAILS.md](GUARDRAILS.md).

O MLflow entra como **índice local de consulta** dos experimentos de ML do NFL Sideline (SQLite e arquivos, sem
servidor e sem custo). Ele fica por cima da proveniência que já existe — hashes SHA-256, freezes e reprodução
offline byte a byte — e é alimentado por um **importador separado que só lê os stores**. O site em produção
continua estático e o código científico congelado não muda.

## Por que importador, e não instrumentação

O código dos experimentos é congelado por hash (`verified_freeze`, `validate_bundle`, `frozen_config.json`) e a
reprodução compara todos os arquivos de saída byte a byte. Um `mlflow.start_run` dentro de `pipeline.py` ou
`experiment.py` quebraria as duas verificações. A Fase 0 ([relatório](PHASE-0-REPORT.md)) mostrou também:

| Premissa original | O que o repositório mostra | Consequência |
|---|---|---|
| Um laboratório de ML | Três experimentos com modelo (v1, v2, xINT) e dois modelos em uso (M3 no laboratório de risco, B2 no de desfechos) | Três experimentos MLflow, dois modelos registrados |
| Código no main | Só nos branches `codex/qb-*`, não incorporados | Branch `codex/mlflow-tracking-v1` a partir de `ed2a008` |
| `start_run`/`log_*` no código | Código congelado por hash; saídas comparadas byte a byte | Importador só leitura |
| Tags para reproduzir | Já existem `sources.json`, `dataset_sha256`, freezes, `reproduction-check.json` | Tags apontam para esses hashes |
| Escrever a regra de seleção antes | Já gravada e congelada (`design.json`, `protocol.json`, `config.json`, `selection.json`) | A Fase 3 confere, não seleciona |
| Janelas expansivas em tudo | Só v1 e xINT; a v2 usa janelas fixas | Filhas seguem a estrutura de cada experimento |
| Busca de hiperparâmetros | Só grade de C; na v2, C fixo | Filhas por C só em v1 e xINT |
| Modelo sklearn com `signature` | JSON próprio, regra sem pickle; B2 é tabela de taxas | pyfunc *models from code* lendo o JSON |
| Snapshot JSON versionado do laboratório | Pacotes locais fora do Git (`current.json`); métricas digitadas em `risk-outcomes/Lab.tsx:28` | Arquivo de proveniência versionado, chave = SHA do modelo |
| CI e clone limpo reproduzem | Sem CI de `research/`; dados reais ~1 GB locais; caminhos absolutos | CI só sintético; reprodução real = a offline existente |

## Objetivo e limites

**Vai fazer**
- Importar as execuções já feitas dos três experimentos: parâmetros; métricas por janela, ano, C e candidato;
  intervalos do bootstrap; calibração e figuras; tags que apontam para os hashes existentes.
- Registrar M3 e B2 como modelos que carregam pelo alias `champion`, sem pickle.
- Ligar cada número exibido no laboratório à execução de origem.
- Registrar a avaliação reservada da v2 (2026, semanas 9–13) quando o gate abrir.

**Não vai fazer**
- Rodar em produção ou hospedar servidor; a Vercel continua estática.
- Editar código congelado ou diretórios científicos (lista em [GUARDRAILS.md](GUARDRAILS.md)).
- Tocar ETL, Java, Supabase ou o snapshot público `web-ui/public/data`.
- Treinar de novo ou refazer seleção para alimentar o MLflow.

O desenho hospedado foi descartado por decisão do dono do projeto (custo recorrente e exposição de credenciais);
o repositório não registrava esse motivo, por isso ele entra no [ADR-011](../../adr/011-local-mlflow-tracking.md).

## Como encaixa

```
stores M/editorial/local-artifacts/qb-*   (fonte de verdade, imutáveis)
  -> research/mlflow_tracking/  importador, só leitura
  -> M/editorial/local-artifacts/mlflow/  mlflow.db + artifacts/  (fora do Git)
  -> compare.py / registry.py: tabela de comparação, alias champion
  -> web-ui/broadcast-journey/risk-outcomes/provenance.json  (versionado; chave = SHA-256 do modelo; D8a)
  -> laboratório local: pacotes já trazem o SHA do modelo; o Lab lê a proveniência por essa chave
```

## Convenções

| Item | Valor |
|---|---|
| Versão | `mlflow==3.17.2` (publicada em 21/10/2026), venv próprio `research/mlflow_tracking/.venv`, Python 3.11 |
| Tracking URI | `sqlite:///<NFL_MLFLOW_HOME>/mlflow.db`; artefatos em `<NFL_MLFLOW_HOME>/artifacts/<experimento>` (sempre explícito; nunca `./mlruns`) |
| Experimentos | `qb-iw-baseline-v1`, `qb-risk-temporal-v2`, `xint-ftn-v1` |
| Modelos registrados | `qb-iw-m3` (M3 congelado da v2), `xint-ftn` (B2 do xINT); alias `champion` |
| Tags obrigatórias | `source_store`, `source_freeze_sha256`, `dataset_sha256`, `design_sha256` (ou protocolo/config), `seed`, `git_commit`, `git_dirty`, `importer_version`, `role` (`parent`/`fold`/`evaluation`/`application`/`reserved`) |
| Idempotência | Antes de criar uma execução-pai, busca `tags.source_freeze_sha256`; se existir, não reimporta |

## Fases

Estado em 23/11/2026: Fases 0–5 concluídas e verificadas; Fase 6 concluída (capturas em [README.md](README.md)), exceto a
primeira execução real do CI no GitHub, que depende de commit/push do dono; Fase 7 aguarda o
gate de 16/12/2026. Detalhes e evidências em [CHECKPOINTS.md](CHECKPOINTS.md).

| Fase | Entrega | Pronto quando |
|---|---|---|
| 0. Reconhecimento | [Relatório](PHASE-0-REPORT.md) e rascunho do ADR-011 | ✅ concluída |
| 1. Instalação isolada | Venv com `mlflow` fixo e lock próprio; `tracking.py` (resolução de caminhos, URI, criação de experimentos com `artifact_location`, convenção de tags, git); `.gitignore` com o store do MLflow e os stores `qb-*`; utilitário de integridade dos stores (manifesto caminho/tamanho/mtime) | `mlflow ui --host 127.0.0.1` mostra uma execução de teste com as tags; `git status` não lista nada do MLflow; testes passam |
| 2. Importador da v1 | Pai por freeze (`development-v3` + `evaluation-v1`); filhas por variante × C × fold (`development_metrics.json`); filha de avaliação 2025 por variante (métricas, bootstrap, calibração); filha de aplicação 2026 W1–7 (métricas descritivas); figuras, coeficientes e JSONs como artefatos | Teste prova que cada métrica no MLflow é igual à do arquivo; stores intactos (manifesto antes/depois); código congelado sem diff |
| 3. v2, xINT e comparação | v2: filhas ano (2024, 2025, 2026 W1–7) × candidato M0–M3 com bootstrap vs M1 e calibração diagnóstica; xINT: filhas por ano de desenvolvimento × C e B0–B2, avaliação 2025 por modelo e grupo FTN; tag `selection_rule` com o texto congelado; `compare.py` monta a tabela a partir do MLflow | A tabela sai do script e o vencedor confere com `selection.json` (M3 na v2, B2 no xINT; C escolhido na v1) |
| 4. Registro dos modelos | `qb-iw-m3` e `xint-ftn` como pyfunc *models from code* com o JSON congelado como artefato; `signature` e `input_example`; alias `champion` | `models:/…@champion` reproduz as previsões salvas (atol 1e-12) e a métrica registrada; SHA do JSON registrado = SHA congelado; nenhum `.pkl` no diretório do modelo |
| 5. Ligação com o laboratório | `web-ui/broadcast-journey/risk-outcomes/provenance.json` determinístico (D8a) (SHA do modelo → `run_id`, experimento, commit, parâmetros, métricas); `Lab.tsx` de desfechos lê os números dele pela fronteira local, sem números digitados | Regenerar sem mudar o champion dá os mesmos bytes; nenhum número de métrica digitado no TSX; testes do `web-ui` passam; pacotes e snapshot público intactos |
| 6. Reprodutibilidade e vitrine | Workflow `research-ci.yml` (pytest de `research/*` com dados sintéticos + teste de fumaça do importador); README do módulo com capturas da UI; ADR-011 aceito; linha na §11 do `Spec.md` | CI verde; clone limpo roda o teste de fumaça; reprodução real documentada |
| 7. Avaliação reservada | Quando `reserved.py` liberar (não antes de 16/12/2026 01:15 UTC, pelo calendário congelado; ver [CHECKPOINTS.md](CHECKPOINTS.md)), o resultado entra no experimento da v2 pelo importador | Execução no MLflow com `opening_receipt` e métricas |

## Decisões de design

| Decisão | Escolha | Por quê |
|---|---|---|
| Papel do MLflow | Índice; se divergir, valem os arquivos e hashes | A proveniência atual é mais rigorosa que a do MLflow |
| Como registrar | Importador pós-execução | Código congelado por hash; saídas comparadas byte a byte |
| Onde ficam os dados | SQLite + artefatos em `M/editorial/local-artifacts/mlflow/`, ignorados pelo Git | Convenção dos stores; caminho resolvido pelo Git ou por `NFL_MLFLOW_HOME` |
| Hierarquia | Pai por freeze; filhas por janela, ano, C ou candidato | Respeita a estrutura de cada experimento |
| Formato do modelo | pyfunc a partir de código, artefato = JSON congelado | Mantém a regra sem pickle |
| Seleção | Já congelada; o MLflow registra e confere | Evita escolher no teste |
| Ligação com o laboratório | Proveniência versionada por SHA do modelo | Pacotes e snapshot público intactos |
| Ambiente | Venv separado com as mesmas versões numéricas dos experimentos | Locks dos experimentos intactos; previsões idênticas |

## Riscos e cuidados

- **Divergência MLflow × arquivos:** importador idempotente e teste de igualdade por métrica.
- **Quebrar a reprodução:** nunca escrever nos stores nem em código congelado; verificação a cada fase.
- **Pickle escondido:** pyfunc com classe Python serializa com cloudpickle; usar *models from code* e checar `.pkl`.
- **~1 GB fora do `.gitignore`:** os stores `qb-*` aparecem como `??`; entradas novas na Fase 1.
- **Branch não incorporado:** a cadeia `qb-*` pode mudar antes do merge; o branch do MLflow exigiria rebase.
- **Licença FTN (CC BY-SA 4.0):** artefatos com linhas reais não saem da máquina; CI só sintético.
- **Exposição:** UI só em 127.0.0.1; versão fixa.

## No currículo

Só depois das Fases 1 a 3: "Indexei no MLflow os experimentos de validação temporal (parâmetros, métricas por
janela e modelos congelados) e liguei cada número exibido no laboratório à execução de origem, sem quebrar a
reprodução byte a byte."
