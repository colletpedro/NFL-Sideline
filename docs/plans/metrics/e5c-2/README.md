# E5c-2 — projeção offline, candidata ao aceite

Base exata `35e3afcb52bf3aa99fbfda40401920b8c393bf24`; branch
`codex/metrics-observations-e5c2`, worktree isolada inicialmente limpa.
[Desenho anterior ao código](DESIGN.md), [relatório](REPORT.md),
[verificação](verification.json) e [prova real](real-proof.json).

Entrada: materialization-v2/input-v3 autocontida + solicitação nominal
metrics-observation-request-v1. Saída: metrics-observation-bundle-v1 contendo
metrics-auditable-observation-v1, manifesto/solicitação e cópia compartilhada dos
originais aceitos. Formatos/escopos/identidades estão no DESIGN. Exemplo nominal
completo: etl-pipeline/tests/fixtures/metrics_observations/request.json.

## CLI offline na raiz da worktree

Usar Python 3.11+ com as dependências ETL **já existentes**, sem instalar nada.
Nesta máquina, o ambiente está no checkout original e não foi modificado:

```bash
export PYTHONPATH=etl-pipeline/src
export PYTHONDONTWRITEBYTECODE=1
NFL_PY='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'

# Escolha um destino NOVO. Fixture totalmente sintética e fechada no Git.
"$NFL_PY" -B -m nfl_sideline_etl.metrics_observations generate \
  --materialized etl-pipeline/tests/fixtures/metrics_observations/materialized \
  --request etl-pipeline/tests/fixtures/metrics_observations/request.json \
  --output /private/tmp/nfl-e5c2-demo-new
"$NFL_PY" -B -m nfl_sideline_etl.metrics_observations validate \
  --bundle /private/tmp/nfl-e5c2-demo-new
"$NFL_PY" -B -m nfl_sideline_etl.metrics_observations inspect \
  --bundle /private/tmp/nfl-e5c2-demo-new
```

`generate` imprime bundleId. `validate` e `inspect` fazem a mesma validação
integral e imprimem resumo, IDs e ausência de garantia temporal/comparação.
Falhas retornam exit 2; saída existente é recusada. Nenhuma seleção latest,
PIT, EVENT_RECONSTRUCTION ou fallback é executada. Não aceitar result-v3 como
substituto do pacote de origem; pedidos PIT vazios continuam intactos.

Leitura Python operacional: `metrics_observations.publication.read(path)`.
`publication.publish(...)` também revalida os originais para chamadores Python.
O núcleo `core.project_verified` é puro e tem pré-condição explícita de validação
integral por `lineage.verify_source`; não é uma fronteira de aceitação de dados
não verificados. Não importa verify.py de fixtures E5c-1. Cada leitura pública
reconstrói a cadeia, sem cache de confiança em objetos mutáveis.

## Reprodução dos checks

```bash
"$NFL_PY" -B -m pytest -p no:cacheprovider \
  etl-pipeline/tests/test_metrics_observations.py \
  etl-pipeline/tests/test_metrics_materialization.py \
  etl-pipeline/tests/test_metrics_identities.py \
  etl-pipeline/tests/test_offline_metrics.py \
  etl-pipeline/tests/test_metrics_persistence.py \
  etl-pipeline/tests/test_temporal_metrics.py \
  etl-pipeline/tests/test_temporal_metrics_correction.py -q
# Python/jsonschema já existentes, usados só na verificação de schema:
python3 -B docs/plans/metrics/e5c-2/check_schema.py --observations \
  etl-pipeline/tests/fixtures/metrics_observations/observations.json \
  docs/plans/metrics/e5c-2/real-observations.json
python3 -B -m unittest discover \
  -s contracts/metrics/consumption-e5c1-v1 -p 'test_*.py'
git diff --check 35e3afcb52bf3aa99fbfda40401920b8c393bf24
```

O main histórico E5c-1 não é gate desta base: sua allowlist anterior intencionalmente
recusa o aceite documental. Nenhum gate antigo foi alterado. A suíte corrigida
(17 testes) e os 34 vetores aceitos são usados adequadamente.

## Prova real opcional

Não depende de banco ou harness, mas requer os originais locais aceitos E5b-6.
Os testes acima não dependem deles. O script verifica os quatro hashes de fonte,
IDs da materialização e reexecuta a verificação semântica aceita. Se os originais
faltarem, reportar prova real pendente; não adquirir nem criar receipts.

```bash
"$NFL_PY" -B docs/plans/metrics/e5c-2/real_proof.py \
  --materialized /private/tmp/nfl-e5b6-orchestrator-real-20261013/materialized \
  --accepted-summary docs/plans/metrics/e5b-6-review/real-proof-summary.json \
  --workspace /private/tmp/nfl-e5c2-real-reproduction-new
```

O script constrói a solicitação concreta BAL/DAL W1, W2, W1–2, NE POST2025 e
lacuna BAL W3, sem escolher por desempenho ou versão mais recente. Requer uma
única associação aceita por jogo nessa prova; caso contrário exige escolha
manual, não resolve alternativas. Armazena a escolha nominal antes da geração.
A origem CURRENT foi pedida explicitamente para 2026 e **não significa** dados
atualizados: o conteúdo continua arquivado W1–2.

O bundle local completo (cerca de 57 MB, com a duplicação inerente ao formato
materializado aceito entre input e lineage) compartilha fontes entre 48 documentos.
[real-observations.json](real-observations.json) é um extrato pequeno para revisão
visual, **não é autocontido nem validável como bundle sem a linhagem comum**.
O relatório declara essa dependência, hashes e caminho do bundle completo.
Não versionamos Parquets/archives inteiros nem configurações de conexão.
