# Identidades E5b-3/4 — contrato anterior à correção

Base exata: f2d946593d1e6b2ed32ad1aa331c630f271c44db. Branch:
`codex/metrics-identities-e5b34`. Nenhum cherry-pick documental do orquestrador.

## Matriz das quatro dimensões

| Dimensão proprietária | Campos imutáveis | Referências auxiliares / variações legítimas | Conflitos que abortam |
|---|---|---|---|
| Lote `calculation_id` | `original.manifest` completo: artifactVersion, versions, mode, inputs (descritores e multiplicidade), metadata original, source_model_versions, replica_projection, requested_seasons, limitations, calculation_id | Qualificação temporal `model` e `source_models` pode usar documentos distintos; declaração original conhecida deve continuar igual | Mesmo ID com qualquer divergência no manifesto global; fontes/versões incompatíveis com a projeção |
| Cobertura `coverage_revision_id` | `original.coverage` completo: jogo, SET calendário/PBP originais, pbp_content_id, auditoria de população, contagens, exclusões, completude/escopo/status e provenance originais; statistics e versions | Pode ser compartilhada por lotes diferentes, inclusive com nova declaração de modelo de fonte no manifesto | Mesmo ID com jogo, fontes, estatísticas, flags, proveniência ou versões divergentes; identidade original inconsistente |
| Associação `(calculation_id, coverage_revision_id)` | Originais acima, game, pbp_revision_id, versions, statistics, unknown_filter_flags_n; referência do lote para cobertura | `calendar_revision_id` aponta ao documento CALENDAR usado nesta revisão, que depende do SET calendário original; não é alias desse SET | Associação desvinculada do lote/fontes/jogo; calendário auxiliar sem vínculo original; alterações nos campos imutáveis |
| Revisão temporal `revision_id` | Todo candidato, incluindo referências aos documentos e envelopes de qualificação | Entre IDs distintos: calendar_revision_id, metadata_revision_ids, completeness, model, source_models, source_cause podem variar explicitamente; jamais substituem campos persistidos | Mesmo revision_id com qualquer conteúdo diferente; envelopes vinculados ao sujeito/kind/valor errado; completude divergente do conteúdo original; modelo conhecido contraditório |

## Formato explícito e versões

Entrada `metrics-temporal-input-v3`: mesmos campos de v2, com campo obrigatório
`original: {manifest, coverage}` em cada candidato observado. Esses objetos são
cópias dos documentos originais E5b-1, sem envelopes temporais adicionados.
Coberturas sem PBP continuam na linhagem integral; não recebem candidato nem
estatísticas fabricadas. COMPLETE vazio conserva os doze grupos zero/null.

Algoritmo novo `metrics-temporal-1.1.0`, resultado `metrics-temporal-result-v3`:
mesma seleção/aritmética de 1.0.1, com validação das quatro dimensões e originais
em calculationsUsed. Materializador `metrics-materialization-v2` emite somente
input-v3. Relations-v1, auxiliary-v1 e a política de confiança não mudam.

Entradas v1/v2 continuam usando explicitamente algoritmo 1.0.1/result-v2 e seus
checks históricos, inclusive a limitação de lote. Não são reinterpretadas como
v3. Leitor Java permite apenas os pares result-v2/1.0.1 e result-v3/1.1.0;
recusa versões cruzadas/desconhecidas. Materializações v1 não são promovidas por
read/select v2; seus arquivos e golden Java continuam registros históricos.

## Limite de validação

O núcleo temporal confere o pacote materializado, vínculos e invariantes; não
recalcula PBP nem autentica documentos. O calculation_id cobre os cinco documentos
completos e continua validado pelo adapter/prepare/writer/materializador aceitos,
a partir de todas as fontes e bytes arquivados. Um manifesto copiado no candidato
não substitui essa validação integral. A cobertura é confrontada com seu hash
original e suas estatísticas reconciliadas; repetição de ID no pacote exige
igualdade da projeção proprietária, independentemente de revision_id.

Documentos auxiliares mantêm origem/recebimento/dependências/sujeito/confiança
explícitos. Receipts e persisted_at não certificam disponibilidade histórica.
Corte exclusivo, frações/offsets exatos, PIT/retrospectivo nominal, denominadores,
fontes compostas inteiras, UNKNOWN, assinatura do período, modelos e subsets
separados continuam iguais. Um jogo contribui com uma única revisão selecionada;
alternativas/réplicas não aumentam amostra. EVENT_END_EXACT não implementado.

Artefatos corrigidos e gate próprio ficam neste diretório. Exemplos/hashes
1.0.0/1.0.1 e evidência bloqueada E5b-4 ficam intactos. E5a, adapter, writer,
archive, schema, produto e publicação permanecem fora do escopo.
