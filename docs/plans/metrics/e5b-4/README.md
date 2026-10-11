# E5b-4 — materialização isolada e leitor Java v2

**Candidata com caminho representável validado e aceite completo bloqueado.**
Base exata `8f583c4ec9ed83f86c2229b0f1656d32403bcc31`; worktree inicialmente limpa;
branch `codex/metrics-materialization-e5b4`. O [contrato](CONTRACT.md) foi registrado
antes da implementação. A [lacuna E5b-3](BLOCKER.md) impede preservar o mesmo
calculation_id de lote em vários candidatos por jogo. Não foi alterado o algoritmo
aceito nem fabricado um ID substituto.

## O que existe

`metrics_materialization` separa extração SQL, recuperação de archive, validação
semântica pelo adapter/writer aceitos, input-v2, publicação e seleção temporal.
Pacotes fechados offline conservam as onze relações originais, arquivos/receipts,
ordinais, réplicas, fontes completas, associações e estatísticas. O núcleo não
importa driver, .env ou rede. PostgreSQL só é ativado pelo modo nominal `postgres`,
com configuração local E5b-2 e transação REPEATABLE READ READ ONLY. Não consulta
games/teams para inventar calendário histórico e não prepara fixtures SQL.

Cada cálculo tem seleção explícita de artefato/archive e binding auxiliar.
Documentos recebidos têm origem, referência, recebimento, dependências e sujeito;
trustedOrigins é uma lista explícita. Receipts não provam ingestão, disponibilidade
anterior, modelo ou encerramento. persisted_at fica só na linhagem auditável.
FILE.ingested_at só recebe envelope SYSTEM_INGESTION explicitamente fornecido;
nenhum horário de materialização certifica PIT anterior.

O Java lê result-v2 por `metrics-temporal-read`, sem iniciar Spring ou datasource.
Tipos imutáveis conservam o documento inteiro e oferecem blocos, grupos, somas
BigDecimal/contagens BigInteger/razões exatas. Instantes usam strings validadas e
segundos decimais sem truncamento. Result-v1 e algoritmos desconhecidos falham.
Não há reexecução da seleção/janelas em Java. EPA defensivo continua produção
permitida ao adversário, reconciliada com o ataque correspondente, sem inversão.

## Garantias verificadas pelo Java

- Hash dos bytes de result.json e vínculos com COMPLETED, result_id/audit_id.
- Recomputação de result_id sobre sua projeção semântica armazenada e audit_id
  sobre o resultado sem o próprio audit_id, pelo serializador Python reproduzido.
  Três vetores Python provam UTF-8, controles, Unicode fora do BMP, bigint,
  listas/objetos e indentação. Não se recalcula o algoritmo que escolheu a projeção.
- Hash dos FILE usados, identidades dos SET inteiros e receipts; vínculos de
  evento/cálculo/cobertura/fontes/calendário/metadata; versões, modo, garantias e
  assinatura requestedPeriod em relação ao pedido.
- Partições de contagens/soma-null, general=pass+rush, off=def adversária;
  agregados reconciliados com as estatísticas originais selecionadas; volume,
  razões racionais e referências de cobertura por fundamento.

input_id é preservado e validado como hash, mas seu conteúdo completo não está no
result-v2: o leitor sozinho não reconstrói o input integral nem prova o vínculo
com SQL. A prova de integração confere input_id com temporalInputId materializado.
Identidades auxiliares arbitrárias não são autenticadas por comparar strings;
calculation/coverage IDs originais são conferidos pelo lado Python com E5b-2.
Hashes não autenticam origens, não provam histórico e não substituem recálculo do PBP.

## Reprodução offline em checkout novo

Use um runtime ETL já instalado (Python 3.11+, dependências de teste existentes).
Não copie archives históricos. Escolha destinos novos, fora de public/data.
`offline_demo.py` cria fontes/archives/receipts novos e relações **sintéticas**;
não é prova de PostgreSQL. Documentos são deliberadamente sintéticos e sua
confiança é explícita. Os golden Java não acessam os roots citados como dados.

```bash
export PYTHONPATH=etl-pipeline/src
export PYTHONDONTWRITEBYTECODE=1
# Ajuste para seu runtime já instalado; este foi o runtime usado na entrega.
NFL_E5B4_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
NFL_E5B4_WORKSPACE=/private/tmp/nfl-e5b4-demo-new
"$NFL_E5B4_PYTHON" -B docs/plans/metrics/e5b-4/offline_demo.py --workspace "$NFL_E5B4_WORKSPACE"

"$NFL_E5B4_PYTHON" -B -m nfl_sideline_etl.metrics_materialization offline \
  --relations "$NFL_E5B4_WORKSPACE/relations.json" \
  --archives "$NFL_E5B4_WORKSPACE/archives.json" \
  --auxiliary "$NFL_E5B4_WORKSPACE/auxiliary.json" \
  --derived-at 2026-10-11T12:00:00.000000000001Z \
  --output /private/tmp/nfl-e5b4-materialized-new
"$NFL_E5B4_PYTHON" -B -m nfl_sideline_etl.metrics_materialization select \
  --materialized /private/tmp/nfl-e5b4-materialized-new \
  --request "$NFL_E5B4_WORKSPACE/request-reconstruction.json" \
  --output /private/tmp/nfl-e5b4-selected-new

export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
mvn -f core-api/pom.xml -o clean verify
"$JAVA_HOME/bin/java" -jar core-api/target/core-api-0.1.0.jar \
  metrics-temporal-read --artifact /private/tmp/nfl-e5b4-selected-new
"$NFL_E5B4_PYTHON" -B docs/plans/metrics/e5b-4/reproduce_gap.py \
  --output /private/tmp/nfl-e5b4-gap-new.json
"$NFL_E5B4_PYTHON" -B docs/plans/metrics/e5b-4/verify.py \
  --output /private/tmp/nfl-e5b4-gate-new.json
```

`select` não descobre mapa retrospectivo. A fixture gera nominalmente suas escolhas
como preparação de teste; consumidores precisam fornecer o próprio pedido.
O gate usa a **base atual desta entrega**, mantém current-state.md intacto e
congela E5a/E5b-1/2/3. Confere também a adição exata no dispatcher, preservando
os comandos anteriores e o comportamento padrão. Não altera o verificador
histórico E5b-3 para fazê-lo passar contra uma base diferente.

## Prova PostgreSQL real e comando explícito

Inspecione listeners/runtime primeiro. Não instale runtime, reutilize raiz antiga,
resete clusters históricos ou administre serviços globais. Este harness exige um
root NOVO; database_proof.py aceita apenas /private/tmp/nfl-e5b4-instance-* vazio.
Provisão e inserts pertencem ao harness/writer, não ao leitor. O login sem
privilégios administrativos herda SELECT já concedido a metric_persistence_writer;
a transação read-only impede INSERT mesmo com essa herança. Sem mudança de grants.

```bash
NFL_E5B4_PG_BIN=/private/tmp/nfl-e5b2-pg-runtime/bin  # runtime existente nesta máquina
NFL_E5B4_INSTANCE=/private/tmp/nfl-e5b4-instance-new
"$NFL_E5B4_PYTHON" -B docs/plans/metrics/e5b-2/instance.py start \
  --pg-bin "$NFL_E5B4_PG_BIN" --root "$NFL_E5B4_INSTANCE" --port 55484
"$NFL_E5B4_PYTHON" -B docs/plans/metrics/e5b-4/database_proof.py \
  --instance-root "$NFL_E5B4_INSTANCE" --workspace /private/tmp/nfl-e5b4-db-proof-new \
  --output /private/tmp/nfl-e5b4-db-report-new.json --java "$JAVA_HOME/bin/java"
"$NFL_E5B4_PYTHON" -B -m nfl_sideline_etl.metrics_materialization postgres \
  --config "$NFL_E5B4_INSTANCE/writer.json" \
  --selection /private/tmp/nfl-e5b4-db-proof-new/selection.json \
  --archives /private/tmp/nfl-e5b4-db-proof-new/archives.json \
  --auxiliary /private/tmp/nfl-e5b4-db-proof-new/auxiliary.json \
  --derived-at 2026-10-11T12:00:00.000000000001Z \
  --output /private/tmp/nfl-e5b4-db-cli-new
"$NFL_E5B4_PYTHON" -B docs/plans/metrics/e5b-2/instance.py stop \
  --pg-bin "$NFL_E5B4_PG_BIN" --root "$NFL_E5B4_INSTANCE"
```

Confirme bind/listener livre após stop. Se runtime/bind indisponível, apenas gates
offline e pendência explícita do teste real; nunca baixar runtime automaticamente.
Nesta entrega o runtime PostgreSQL 17.6 já existia e o teste real foi executado.

## Evidências e resultados

[Relatório de versões/hashes](validation.json), [gate offline](offline-verification.json),
[prova real final](database-verification.json), [CLI real](cli-database-verification.json).

- 410 testes ETL offline (350 anteriores +60 novos), sem falhas/skips.
- 26 exemplos/23 testes E5a e 12 hashes; seis arquivos E5b-1 byte a byte;
  E5b-2 dry-run sem DB/criação de archive; regressões 1.0.1 e três contraprovas;
  exemplos corrigidos/marcadores byte a byte e evidências históricas preservadas.
- Java 21.0.12.1 `mvn -o clean verify`: 154 testes, incluindo 27 do leitor,
  zero falhas/erros/skips. Nenhum serviço externo/modelo foi chamado na prova.
- Prova real reconciliou fontes/IDs/somas/contagens em dois cálculos representáveis.
  EPA geral -1/3, volume3, subset UNKNOWN; COMPLETE vazio separado; sourceRatio1/3
  sobre três jogos esperados, com synthetic-5 sem PBP no denominador.
- PIT anterior aos receipts/documentos atuais: expectedGames null, nenhuma
  certificação fabricada. Retrospectivo: NOT_DEMONSTRATED para conhecimento histórico.
- Todas as onze relações, persisted_at, blobs e receipts permaneceram idênticos
  antes/depois. CLI real produziu materialização idêntica e ignorou lote posterior
  não selecionado. PostgreSQL recusou INSERT na transação read-only.
- `git diff --check` passou. Primeiro erro Java foi inferência genérica do parser;
  três expectativas de teste foram corrigidas (nome status, linha já null e
  incompatibilidade de modelos por janela). Gates finais não têm falhas/skips.

Foram usadas duas instâncias próprias novas para revalidar os checks finais;
ambas encerradas. [Primeiro encerramento](shutdown-first.json) e
[encerramento final](shutdown-final.json) registram UUID/root e porta55484 liberada,
com probe de bind aprovado e evidência preservada. Nenhum cluster anterior tocado.
Runtime/cluster/archives não são necessários para os testes offline/golden Java.

## Limites e próximo aceite

Lotes com várias coberturas observadas falham pela lacuna documentada E5b-3;
a entrega geral não é declarada concluída. A correção exige revisão/versionamento
separados, preservando os IDs originais. Calendário, estado/bounds, completude,
modelo e ingestão sem documentos/prova continuam UNKNOWN ou declaração não
comprovada. Fonte COMPLETE não certifica qualidade/amostra/confiança.

Não conectada ao pipeline semanal, JPA/editorial, AnalysisContextBuilder, regras,
frontend, API principal ou snapshots. Sem .env, banco remoto, aquisição/backfill,
Gemini/modelos, push, deploy ou merge. EVENT_END_EXACT continua proposta.
Supabase completo/advisors permanece pendência independente; teste PostgreSQL
nativo não a resolve. Frontend/inspeção visual não executados porque inalterados.
E5b-5 e integrações posteriores continuam fora desta candidata.
