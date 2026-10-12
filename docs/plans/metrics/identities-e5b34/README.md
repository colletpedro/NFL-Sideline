# Correção de identidades E5b-3/4 — candidata ao aceite

Base exata `f2d946593d1e6b2ed32ad1aa331c630f271c44db`, checkout inicial limpo,
branch `codex/metrics-identities-e5b34`. Worktree isolada gerenciada pelo Codex.
A revisão documental e380e80 foi lida no checkout de origem, sem cherry-pick.
E5b-4 e seus relatórios bloqueados são preservados integralmente como história.

## Resultado e matriz

A [matriz proprietária das quatro dimensões](CONTRACT.md) foi commitada antes
do código. `calculation_id` identifica o lote e conserva o manifesto
original; `coverage_revision_id` identifica conteúdo/proveniência do jogo;
`(calculation_id, coverage_revision_id)` identifica a projeção da associação;
`revision_id` identifica documentos/qualificações temporais dessa associação.

| Dimensão | Projeção imutável | Variação legítima |
|---|---|---|
| Lote | Manifesto completo original, versões, descritores/multiplicidade, metadata, declarações/modelos originais | Documentos qualificadores temporais não reescrevem o manifesto |
| Cobertura | Audit completo original, jogo, SETs, pbp_content_id/provenance, contagens/exclusões, escopo/completude, estatísticas/versões | Pode participar de cálculos diferentes, inclusive alteração somente de modelo no manifesto |
| Associação | Originais de lote/cobertura e game/PBP/versions/statistics/flags | Documento CALENDAR e metadata/envelopes explicitamente declarados podem variar em outra revisão |
| Revisão temporal | Todo candidato sob seu revision_id | Nova revisão pode mudar somente referências/qualificações permitidas; mesmo ID não pode divergir |

`original: {manifest, coverage}` separa campos persistidos dos envelopes. Arrays
originais conservam a ordem e os tipos; a normalização de conjuntos temporais
não reordena o manifesto. O documento CALENDAR depende do SET calendário original
sem ser seu alias. A validação por calculation_id continua presente, sobre o
manifesto global inteiro, além dos checks por cobertura/associação/revisão.

## Antes/depois e identidades

O [caso antes/depois](before-after.json) conserva exatamente:
`sha256:9344d1b8902207a39b5321f939da1bae8aaddbb848b33b1155152ac1a38eeca7`.
Antes: IDENTITY_CONFLICT, quatro associações, dois jogos observados, nenhuma saída.
Depois: mesmo calculation_id, todas as quatro associações, synthetic-1 observado
com volume3/EPA -1/3 e synthetic-6 COMPLETE vazio com doze grupos zero/null.
synthetic-3 é alvo excluído por ID; synthetic-5 permanece esperado sem PBP.
Denominador3, sourceRatio1/3; COMPLETE e AUDITABLE_SUBSET_UNKNOWN separados.

Novas identidades do exemplo corrigido (receipts/documentos sintéticos explícitos):

- input_id: `sha256:5991c83b5d276f7d6f46c0c7a207d133232d237adfc0b8610486491eef12dbcc`
- materialization_id: `sha256:f7d7f54649157116fc5c6fe124b8fb3a074e037723f2f0bfaba3cf6c42ffd755`
- result_id retrospectivo: `sha256:71d4f7daa6c8d4a68083525ed83c0789b29a0a5317c32992d168ef5791b42e69`
- audit_id retrospectivo: `sha256:7ea65041fe9e76be03e494454ef8f40214a299cc88860e38cd5d65d0cc85bff1`

São IDs próprios da derivação, sem substituir calculation/coverage/source/artifact/
receipt IDs. [Artefatos novos](examples/) e [gate](offline-verification.json)
contêm os hashes novos e antigos. Os 12 hashes E5a, seis arquivos E5b-1 e exemplos/
marcadores 1.0.0/1.0.1 permaneceram idênticos. O hash da contraprova bloqueada E5b-4
é registrado em preservedEvidenceHashes. Recursos/estatísticas originais continuam
consultáveis no resultado; o conjunto inteiro SQL/archive permanece na linhagem.

## Versões, conflitos e limites

| Entrada / pacote | Algoritmo | Resultado / leitura |
|---|---|---|
| input-v1/v2 histórico | 1.0.1 e checks históricos, incluindo a limitação de lote | result-v2; Java mantém suporte separado |
| input-v3 com original explícito, materialization-v2 | 1.1.0 | result-v3; Java aceita explicitamente esse par |

Versions cruzadas/desconhecidas falham. Pacotes materialization-v1 não são
promovidos por publish/read v2. Relations-v1, auxiliary-v1 e política de confiança
permanecem. Formatos novos são internos; nenhum consumidor principal conectado.

Abortam conflitos de revision_id, manifesto global, cobertura/estatísticas,
jogo/fontes/versões, associação, proveniência original versus manifesto, documentos
mal vinculados, completude reescrita ou declaração conhecida de modelo contraditória.
Mantidos 12 grupos, reconciliação general=pass+rush/off=def, contagens/decimais/razões
exatos, limites exclusivos e offsets/precisão fracionária. UNKNOWN não vira COMPLETE.

Os testes provam revisões legítimas com calendário auxiliar diferente, modelo
qualificado por novos documentos sem trocar o cálculo original, lotes compartilhando
cobertura após declaração de modelo, réplicas/permutação/alternativas sem duplicar
amostra, PIT escolhendo anterior e mantendo result_id ao adicionar futuro inelegível,
retrospectivo escolhendo posterior nominalmente e comparação recusando recortes
incompatíveis, conservando os valores originais.

O núcleo confere o pacote materializado; o calculation_id do lote completo continua
validado pelo adapter/prepare E5b-2, confrontando artefatos, fontes e relações. Java
confere estrutura, marcador/hashes, identidade semântica pelo serializador Python,
originais e agregados; não reimplementa seleção temporal nem recalcula PBP.
Hashes/origin/documentos não autenticam terceiros. Receipts atuais, persisted_at e
derivedAt não certificam histórico. As fixtures de história são declarações sintéticas
sob política explícita, sem certificação de um dataset histórico real.

## Gates e prova real

- 434 testes ETL offline, sem falhas/skips, incluindo 24 regressões novas de identidade.
- E5a: 26 exemplos, 23 testes e 12 hashes congelados.
- E5b-1 CLI: seis arquivos byte a byte. E5b-2: dry-run sem banco/archive.
- Regressões 1.0.1, exemplos/marcadores e três contraprovas de período/cobertura preservados.
- Java 21: `mvn -f core-api/pom.xml -o clean verify`: 170 testes, zero falhas/erros/skips;
  inclui 16 testes novos de versões/originais, além dos vetores de paridade existentes.
- [PostgreSQL real final](database-verification.json): writer/archive aceitos → extração
  REPEATABLE READ READ ONLY → materialização integral → seleção → seis leituras Java.
  Três fluxos: lote antes bloqueado, dois cálculos com cobertura compartilhada e
  mudança somente de modelo, dois jogos com PBP + COMPLETE vazio + jogo sem PBP.
- [CLI real](cli-verification.json): bytes integralmente iguais aos da prova direta,
  com dois outros cálculos presentes e não selecionados. Leitor Java sobre a saída CLI.
- Todos os onze conjuntos de linhas, persisted_at, blobs, receipts e marcador de
  archive idênticos antes/depois de cada leitura/materialização. IDs/somas/contagens/
  razões/modelos/modos/garantias reconciliados. PostgreSQL recusou INSERT em read-only.
- `git diff --check` aprovado. Gate próprio congela E5a/adapter/writer/schema/produto,
  testes temporais anteriores, scripts/evidência histórica e dispatcher contra a
  base desta tarefa. Não modifica gates antigos para fazer a base passar.

A prova final usa UUID `febe7630-6d21-4377-9055-6d589c2666c1`, porta55485, diretório novo
`/private/tmp/nfl-e5b4-instance-identities-final-20261012-7c89d3` e PostgreSQL17.6
já existente. Nenhum runtime baixado. A primeira instância própria também foi
encerrada e preservada; a repetição final conferiu a preservação integral dos
campos originais após os últimos ajustes. [Encerramento inicial](shutdown-first.json)
e [final](shutdown-final.json): pg_ctl stop somente do próprio cluster,
listener ausente e probe de bind aprovado na porta55485. Clusters históricos,
serviços globais, .env e banco remoto não foram usados.

## Reprodução em checkout novo

Runtime ETL/Java/PostgreSQL deve já existir. Execute na raiz desta worktree:

```bash
export PYTHONPATH=etl-pipeline/src
export PYTHONDONTWRITEBYTECODE=1
NFL_IDENTITIES_PY='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
"$NFL_IDENTITIES_PY" -B docs/plans/metrics/identities-e5b34/verify.py --output /private/tmp/identities-gate-new.json
mvn -f core-api/pom.xml -o clean verify
"$NFL_IDENTITIES_PY" -B docs/plans/metrics/identities-e5b34/reproduce.py \
  --output /private/tmp/identities-before-after-new.json --artifacts /private/tmp/identities-artifacts-new
"$JAVA_HOME/bin/java" -jar core-api/target/core-api-0.1.0.jar metrics-temporal-read \
  --artifact /private/tmp/identities-artifacts-new/reconstruction

# Verifique runtime/listeners; escolha porta livre e roots NOVOS.
NFL_IDENTITIES_INSTANCE=/private/tmp/nfl-e5b4-instance-identities-reproduction-new
NFL_IDENTITIES_WORKSPACE=/private/tmp/identities-db-reproduction-new
NFL_IDENTITIES_PG=/private/tmp/nfl-e5b2-pg-runtime/bin
"$NFL_IDENTITIES_PY" -B docs/plans/metrics/e5b-2/instance.py start \
  --pg-bin "$NFL_IDENTITIES_PG" --root "$NFL_IDENTITIES_INSTANCE" --port 55485
"$NFL_IDENTITIES_PY" -B docs/plans/metrics/identities-e5b34/database_proof.py \
  --instance-root "$NFL_IDENTITIES_INSTANCE" --workspace "$NFL_IDENTITIES_WORKSPACE" \
  --output /private/tmp/identities-db-report-new.json --java "$JAVA_HOME/bin/java"
"$NFL_IDENTITIES_PY" -B docs/plans/metrics/identities-e5b34/cli_proof.py \
  --instance-root "$NFL_IDENTITIES_INSTANCE" --proof-workspace "$NFL_IDENTITIES_WORKSPACE" \
  --output-root /private/tmp/identities-cli-new --report /private/tmp/identities-cli-report-new.json \
  --java "$JAVA_HOME/bin/java"
"$NFL_IDENTITIES_PY" -B docs/plans/metrics/e5b-2/instance.py stop \
  --pg-bin "$NFL_IDENTITIES_PG" --root "$NFL_IDENTITIES_INSTANCE"
# Confirme listener ausente e bind livre; preserve os dados/evidências locais.
git diff --check
```

O harness real recusa raiz usada e banco não vazio. Em falha, encerre apenas a
instância identificada criada para sua reprodução; não resete clusters. Transporte
SQL-shaped offline nunca é anunciado como PostgreSQL real. Se bind/runtime não
estiver disponível, reporte essa prova como pendente e execute o gate offline.

## Pendências e entrega

Candidata à revisão/aceite do orquestrador. EVENT_END_EXACT e E5b-5 não iniciados;
Supabase completo/advisors permanecem pendência independente. Sem ETL semanal,
aquisição/backfill, Gemini/modelos, frontend/snapshots/análises, JPA/editorial,
AnalysisContextBuilder, API principal/laboratório/BASIC/FULL, publicação/push/deploy/
merge em main. Alterações limitadas ao contrato temporal, materializador/leitor,
regressões e documentação da transição.

Os commits focados de especificação, núcleo temporal, adaptação Python/Java e
regressões/evidências são entregues na branch informada. HEAD e estado final
limpo são apresentados na resposta de entrega (o próprio commit não pode incluir
seu hash em arquivo sem alterar esse hash). [Versões e hashes](validation.json),
[Java](java-verification.json), [gate offline](offline-verification.json).
