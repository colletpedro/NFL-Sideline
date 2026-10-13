# Proveniência prospectiva — somente desenho

Reutilizar FILE/SET/METADATA, envelopes, receipt e kinds aceitos E5b-3/4. Não há
migration, coletor ou registro operacional novo aqui. Proposta de envelope imutável
para quatro tipos; qualquer adaptação futura aos formatos aceitos requer teste
próprio, sem ampliar kinds congelados implicitamente.

Campos comuns: recordVersion, recordId (hash do conteúdo canônico), kind,
subject {resourceType, originalId, contentSha256, byteLength}, origin {system,
reference, authenticatedBy|null}, declarant {id,role,authorityBasis},
claim {population,revisionIds,value,basis}, times {eventAt|null,
observedOrDeclaredAt,persistedAt,demonstrableAvailableAt|null}, dependencies
[recordId/resourceId], supersedes [recordId], correctionReason|null.
Referência é identificador, não URL para aquisição automática. Hash comprova
igualdade/integridade local, **não autentica terceiros**; authenticatedBy depende
de prova específica ou é null. Origem/responsável não são inferidos pelo nome.

| Tipo / ligação aceita futura | Conteúdo / significado dos tempos | Prova / não prova |
|---|---|---|
| BYTE_RECEIPT → ARCHIVE_OBSERVATION | bytes/revisão, origem e coletor, canal/locator/hashes/len; eventAt pode ser publicação declarada upstream, não conhecida automaticamente; observedOrDeclaredAt é recebimento efetivo local; persistedAt é gravação do receipt; demonstrableAvailableAt no máximo conservador observável sob relógio/política aceitos | Esses bytes recebidos no instante documentado, disponibilidade conservadora então. Receipt atual não prova disponibilidade passada, ingestão, autenticidade, completude ou final |
| INGESTION → SYSTEM_INGESTION | revisão de bytes e receipt, run/stage/adapter/calculation/artifact, responsável; observedOrDeclaredAt é observação de ingestão finalizada; eventAt pode registrar a execução documentada, nunca inferred de SQL; persistedAt é append do registro | Ingestão da revisão exata segundo prova de execução. persisted_at existente não prova ingestão histórica; sucesso global não prova populações completas. Se prova observa ingestão só depois, limite de conhecimento é conservador posterior |
| GAME_FINAL → FINAL_OBSERVATION / EVENT_END_BOUND | gameId, revisão de estado e calendário; FINAL, basis e bound; eventAt é encerramento somente com semântica/prova própria, ou null; observedOrDeclaredAt é observação FINAL; bound conservador pode ser esse instante; persistedAt é registro | Estado final observado e bound aceito. Kickoff previsto não prova início/encerramento, placar não prova FINAL. FINAL_OBSERVED_AT não afirma instante exato. EVENT_END_EXACT continua proposta separada não implementada |
| COMPLETENESS_DECLARATION → PBP_COMPLETE / CALENDAR_COMPLETE / PERIOD_CLOSED | sujeito exato, definição/população, revisão/arquivos e inventário, regras de omissão, suporte, responsável/autoridade; eventAt pode descrever período da população, não conhecimento; observedOrDeclaredAt é emissão/recebimento demonstrado da declaração | Declaração sustentada/aceita sobre população específica. Não certifica suficiência estatística, modelo, evento final ou revisão diversa. Completude por jogo não prova calendário completo; lista de jogos não prova completude de jogadas |

Disponibilidade demonstrável é dos **bytes e da declaração usados**, para o
sistema e política especificados, não “existia na internet”. Se não há evidência,
null. observedOrDeclaredAt precisa indicar na basis se é emissão externa ou
observação local; emissão externa sozinha não sustenta recorded_at. No mapeamento
E5b, recorded_at é recebimento local confiado, que deve ser ≥ emissão conhecida.
Timestamps mantêm timezone/precisão original; comparações exatas UTC, sem truncar
frações. Registros com cronologia impossível são rejeitados; clocks/origens não
aceitos permanecem declaração não provada. Igualdade de tempos não dá semântica
igual: persistência, observação, evento e disponibilidade são conceitos distintos.

## Correção, conflito e corte

Correção é append de novo recordId com supersedes e motivo, mesmos sujeitos
explicitamente relacionados. Bytes corrigidos têm sourceRevisionId novo; não
alterar receipt, manifesto, cobertura ou tempos anteriores. Uma declaração
auxiliar nova não reescreve a completude original persistida nem certifica fonte
UNKNOWN por mudar rótulo; deve transportar a evidência e respeitar a fronteira
de vínculo/consistência E5b-4. Declarar revisão anterior inválida é novo documento.

Declarações simultâneas incompatíveis, de autoridades diferentes ou cadeia de
substituição ambígua => CONFLICT, ambas preservadas, sem latest-wins. Uma resolução
com autoridade explícita, conteúdo e evidências recebe novo ID e instante; não
apaga o conflito histórico nem vale em corte anterior. Desempate por revision_id
aceito E5b-3 só ordena revisões elegíveis sem conflito proprietário; não resolve
verdade por ordem lexical. Sem política de autoridade aceita, UNKNOWN/unproven.

PIT futuro precisa dos bytes e receipts íntegros, ingestão provada, calendário
completo/classificação temporal dos eventos, estados FINAL/bounds, documentos de
completude/modelo e todas as dependências. Todas disponibilidades/ingestões e
recebimentos das provas < corte exclusivo. event_upper_bound < corte; target
excluído e kickoff aceito ≥ corte para pregame. SET utiliza conjunto inteiro e
máximos dos membros/dependências; não escolhe só partições convenientes. Reusar
seleção E5b-3, não a reimplementar no coletor visual.

Uma declaração recebida hoje sobre jogo antigo **não fica elegível ontem**.
Correção após corte não disputa seleção congelada anterior; sua existência pode
mudar auditoria integral, mas não observationId da projeção escolhida. Receipt de
hoje com eventAt antigo prova recebimento hoje. Reconstrução retrospectiva nominal
pode estudar eventos anteriores se bound existe, mas continua sem garantia de
conhecimento histórico. Os relatórios resumidos E5b-6 não se tornam receipts,
provas de completude ou fontes auxiliares históricas nesta entrega.
