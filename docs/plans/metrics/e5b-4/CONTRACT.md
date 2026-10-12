# E5b-4 — contrato antes da implementação

Base exata 8f583c4ec9ed83f86c2229b0f1656d32403bcc31; branch
codex/metrics-materialization-e5b4; checkout inicial limpo. E5a, E5b-1/2 e
metrics-temporal-1.0.1 são fronteiras congeladas. Candidata interna, sem produto.

## Camadas e seleção

1. `extract` lê PostgreSQL em REPEATABLE READ READ ONLY. Configuração local E5b-2
   explícita; nenhuma .env/PG*/DSN/remoto. Seleção nominal de pares calculation_id,
   artifact_id e archive_id. Recupera todas as coberturas/somas e membros de cada
   conjunto, inclusive ordinal e multiplicidade. Sem seleção de último/melhor.
2. `recovery` abre somente roots fornecidos explicitamente; não cria archive nem
   receipts. Confere UUID, root literal resolvido, locator canônico, receipt no
   disco versus SQL, hash do receipt, bytes/SHA/tamanho e arquivos originais.
   Não segue symlinks nem origin/reference. Outra root é outra observação: não
   copiar archive para reproduzir um receipt. Memória recebe um pacote fechado
   de bytes/receipts; a validação offline não importa driver.
3. `core` confronta todas as relações com o artefato original e recalcula pelo
   prepare E5b-2/adapter E5b-1. Hashes não substituem estatísticas/associações.
   Documentos auxiliares explícitos produzem input-v2; linhagem separada conserva
   todas as identidades e relações originais. Ausência de PBP não gera grupos.
4. `select` chama o núcleo aceito sem modificações. PIT conserva UNKNOWN quando
   faltam evidências; retrospectivo exige mapa nominal fornecido pelo usuário.
5. Leitor Java puro lê result-v2 e marcador. Não seleciona revisões nem calcula
   janelas. Não inicia Spring/DB/Gemini/Python. result-v1 recusado.

Pacote de relações `metrics-relations-v1`: {relationsVersion, selection,
relations}. selection é lista não vazia de {calculation_id,artifact_id,archive_id}.
relations contém exatamente as onze relações abaixo, com colunas SQL originais.
Representação de numeric = string decimal finita; bigint = inteiro JSON;
timestamptz = string com offset/precisão preservados. persisted_at é auditoria:
**nenhum timestamp SQL é promovido a disponibilidade ou ingestão** nesta versão.
Login pode herdar metric_persistence_writer (SELECT já concedido), mas a extração
abre transação read-only; não propõe nova migration ou amplia privilégios.

| Relação E5b-2 | Verificação e projeção |
|---|---|
| metric_archive_blob | SHA, comprimento e persisted_at auditável; bytes fechados |
| metric_source_revision | revision_id=sha256:SHA original; recurso FILE |
| metric_source_set | revision_id/kind e members_json integral; recurso SET |
| metric_source_member | set/kind/ordinal contínuo, descritor/raw_rows/source_id; dependências preservam réplicas |
| metric_calculation | manifesto, versões e conjuntos; calculation_id de lote intacto |
| game_metric_coverage_revision | audit completo e todas as colunas congeladas, inclusive sem PBP |
| metric_calculation_coverage | associação integral por calculation/game/coverage |
| team_game_metric_sums | numeric e record_json reconciliados, 12 grupos só quando observados |
| metric_artifact | artifact_id original do mapa dos seis hashes e vínculo cálculo |
| metric_artifact_file | seis arquivos originais, manifesto e COMPLETED incluídos |
| metric_archive_receipt | receipt original, vínculo blob/archive/root/locator e instante prospectivo |

## Documentos auxiliares e confiança

`metrics-auxiliary-v1`: {auxiliaryVersion,policy,archiveOrigin,resources,evidence,
bindings,file_ingestion?}. policy é a política temporal aceita com trustedOrigins nominal,
nunca inferida das origens presentes. archiveOrigin identifica explicitamente
quem assume a observação local. Receipt fornece available_at conservador do FILE;
ingested_at continua null salvo file_ingestion[source_revision_id] com envelope
SYSTEM_INGESTION de documento explícito. Esse mapa nunca é preenchido por SQL. Receipt
não prova disponibilidade anterior, encerramento, completude nem modelo.

resources/evidence têm o formato fechado E5b-3 (CALENDAR, STATE, METADATA), com
origem, recebimento recorded_at, dependências e IDs explícitos. Provas auxiliares
precisam depender de METADATA congelado que contém o documento recebido; não se
acessa reference. METADATA.document exige {documentVersion:
metrics-auxiliary-document-v1,origin,received_at,reference,content}; a origem deve
coincidir com payload.origin e recorded_at da prova não pode preceder received_at.
Isso valida vínculo e cronologia declarada, não autentica o documento. Recursos FILE/SET são exclusivos da recuperação. CALENDAR deve
conter exatamente o inventário congelado daquela temporada/fase do cálculo e
vincular o SET calendar. Calendar mutável games não é consultado. CALENDAR sem
prova de completude e STATE UNKNOWN são gerados quando os documentos faltam.

bindings: lista de {calculation_id,calendars,metadata_revision_ids,
completeness,model,source_models}. completeness é mapa coverage_id→envelope;
source_models é mapa source_revision_id→envelope (todos os membros únicos).
calendars é mapa season/phase→ID de CALENDAR, com todas as fases do lote.
Bindings ligam explicitamente declarações aos registros; completude efetiva
persistida não é promovida por declaração divergente. Modelo conhecido no
manifesto deve coincidir; UNKNOWN pode receber documento separado declarado.
Envelopes ausentes são null. Evidência não confiada conserva declaração sem
qualificação. kickoff previsto não vira bound, score não vira FINAL.

revision_id temporal identifica associação cálculo/cobertura/documentos; preserva
calculation_id e coverage_id originais em campos separados. calendar_revision_id
no cálculo temporal identifica documento CALENDAR, distinto do SET persistido;
ambos são conservados na linhagem. artifact/receipt/source_set IDs nunca viram
aliases. Materialization identity é hash próprio da derivação, separado desses IDs.

## Ausência, integridade e publicação

Corrupção, relação extra/faltante, associação/soma divergente ou conflito falha
sem destino final. Ausência de fonte estatística permanece NO_SOURCE_OBSERVATION
na linhagem; não há candidato de cálculo com grupos inventados. COMPLETE vazio
mantém doze grupos zero com epa_sum null. Calendário/estado/modelo/completude não
comprovados permanecem UNKNOWN, com diagnósticos. Não preencher PIT.

Saída `metrics-materialization-v1`: input.json v2, lineage.json, COMPLETED.json
com hashes/identidade própria. derivedAt é explícito; não é conhecimento histórico.
Destino novo, publicação exclusiva atômica, nenhum web-ui/public/data. Seleção
publica artefato result-v2 pelo publicador aceito, verificando primeiro pacote.
Entradas e metadados idênticos produzem bytes idênticos.

## Leitor Java e garantias

Árvore JSON imutável tipada (objetos/mapas, listas, strings, BigInteger, boolean,
null), com acesso a BigDecimal para somas e razões e instantes decimais exatos.
Preserva todos os campos de request, requestedPeriod, garantias, UNKNOWN, gaps,
subsets, modelos separados e EPA permitido da defesa. Nenhum double/float.
Valida versão/estrutura, hashes de bytes e vínculos de IDs com marcador; verifica
identidades semânticas result_id/audit_id reproduzindo JSON canônico Python com
vetores de paridade; valida partições das contagens, soma/null, razões racionais,
grupo de doze estatísticas e vínculos selecionados. Não autentica evidências,
reexecuta seleção temporal nem comprova conhecimento histórico por conta própria.
Hash canônico não equivale a autenticação ou recálculo de PBP.

## Lacuna de contrato sob investigação

validation.py E5b-3 parece exigir que calculation_id tenha projeção por jogo
única; E5b-2 conserva calculation_id de lote em várias associações. Caso confirmado,
materialização recusará lote com múltiplos jogos observados antes de publicar.
A reprodução e proposta mínima serão registradas separadamente; não contornar
com IDs novos nem escolher apenas um jogo. E5b-4 não será anunciada completa
com esse bloqueio. EVENT_END_EXACT permanece proposta, sem implementação.
