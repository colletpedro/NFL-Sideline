# E5b-2 — desenho anterior ao DDL

Base confirmada: `882c9013ec1a1cd08f2d0b7049fb74ff1cdb8491`.
A adaptação aceita `metrics-offline-v1` é a autoridade executável. E5B.md propõe
nomes/grão, mas não permite confundir as identidades implementadas.

| Identidade | Significado e persistência |
|---|---|
| source_revision_id / SHA-256 | Bytes de **um** arquivo; `metric_source_revision` referencia blob imutável. Sem modelo/instantes mutáveis na linha de bytes. |
| calendar_revision_id / pbp_revision_id | Hash da lista ordenada de IDs recebidos, inclusive multiplicidade. `metric_source_set` + `metric_source_member` preservam partições, ordem canônica e descritor de cada ocorrência. Não é hash de arquivo. |
| pbp_content_id | Hash da projeção normalizada/deduplicada de um jogo, antes da população. Fica na cobertura; bytes originais permanecem no archive. |
| coverage_revision_id | Hash do jogo congelado, revisões compostas, conteúdo, proveniência **do jogo** e versões E5b-1. Não identifica o manifesto inteiro. `game_metric_coverage_revision` preserva o audit completo. |
| calculation_id | Hash canônico original dos cinco documentos, retirando somente o próprio calculation_id. `metric_calculation` conserva manifesto completo, modelos EPA, evidências e versões. Associação `metric_calculation_coverage` admite cálculos distintos com mesma cobertura. |
| artifact_id | Hash adicional do mapa de hashes dos seis arquivos originais; `metric_artifact` + `metric_artifact_file` preservam bytes e formatação, inclusive COMPLETED.json, para recuperação. Não substitui calculation_id. |
| receipt_id | Hash de uma observação prospectiva local: blob, archive_id, instante UTC, origem. `metric_archive_receipt` conserva o primeiro receipt por blob/archive; reexecução reutiliza-o. Outro archive é outra observação. |

Relação auxiliar `metric_archive_blob` deduplica bytes compartilhados por fontes,
artefatos e receipts. Estas relações auxiliares são necessárias para não embutir
uma coleção em uma falsa revisão de arquivo, não perder evidências de modelo,
preservar artefatos originais e distinguir observação de persistência SQL.
Declarações recebidas ficam no manifesto/audit com origem; receipt não autentica
referências nem prova encerramento ou disponibilidade histórica. Nenhum ponteiro
"atual", "último" ou seleção por corte é criado.

## Invariantes e acesso

SQL: FKs de jogos/times/fontes/cobertura; unicidade contratual; bigint não negativo;
partição EPA, success <= epa, soma null somente sem EPA e soma numeric finita
(inclusive negativa/zero); fase/round, papel/fundamento, estado/escopo válidos.
Estado/escopo das somas referencia a cobertura. JSON preserva auditoria detalhada.
Writer: recalcular com o adapter aceito a partir das fontes verificadas e comparar
o conjunto completo; assim valida joins, contagens brutas, exclusões, 12 grupos
quando há observação, general=pass+rush e off=def adversária antes do commit.
Hashes sozinhos nunca aprovam semântica. Entidades de domínio só por FK; não são
criadas/corrigidas pelo writer, nem exigem SELECT/grants sobre tabelas legadas.

Schema privado `metrics_private`; RLS em todas as tabelas, policies SELECT/INSERT
somente `metric_persistence_writer` NOLOGIN/NOBYPASSRLS. Sem UPDATE/DELETE/TRUNCATE,
sem policies/grants para PUBLIC/anon/authenticated/service_role. Login de teste e
marcador de instância pertencem apenas ao provisionamento descartável.

## Ordem de operações e falhas

1. Sem banco: ler marcador COMPLETED, conferir hashes/canonicalização e recalcular
   a semântica usando arquivos explicitamente fornecidos. Dry-run encerra aqui.
2. Validar configuração explícita loopback + identificação E5b-2; conectar com
   parâmetros fechados (sem DSN/service/.env), verificar database/marcador/role.
3. Arquivar bytes antes da transação lógica; publicar sem sobrescrita, verificar
   na recuperação; publicar receipt UTC por blob/archive sem deslocar o primeiro.
4. Uma transação para blobs, fontes/partições, cálculo, cobertura de **todos** os
   jogos, somas, artefatos e receipts. INSERT ON CONFLICT DO NOTHING + comparação
   de todos os campos imutáveis, nunca UPDATE. Lock transacional E5b-2 serializa
   writers concorrentes e mantém recuperação simples.

Falha SQL reverte todo o conjunto lógico; arquivos já publicados podem permanecer
sem referência SQL. Nunca apagar conteúdo compartilhado para desfazer tentativa.
Reexecução valida/reutiliza blobs e receipts e refaz a transação. Não há atomicidade
distribuída nem certificação contra adulteração por administrador/queda de energia.
Observação local e persisted_at SQL são instantes distintos; available_at,
event_upper_bound e ingested_at declarados são preservados, nunca inferidos.
