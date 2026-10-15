# E5c-2 — fronteiras congeladas antes do código

Candidata. Base exata 35e3afcb52bf3aa99fbfda40401920b8c393bf24; worktree
isolada inicialmente limpa, branch codex/metrics-observations-e5c2. Checkout
original e 36 arquivos históricos inventariados sem alterações. Sem publicação.

## Entrada nominal v1

`metrics-observation-request-v1`: objeto fechado com requestVersion,
source {materializationId, temporalInputId}, derivedAt (UTC Z segundos),
presentation {epaDecimals, ratePercentDecimals, rounding: HALF_UP} e requests.
Cada pedido contém season, phase REG/POST, weeks (inteiros positivos), origin
CURRENT/HISTORICAL_REFERENCE explícito, teams, roles off/def, foundations
(general/classified_pass/classified_rush), calendarSourceSetId,
calendarRevisionId e associations. Cada associação contém gameId, calculationId,
coverageRevisionId, artifactId, archiveId e temporalRevisionId (null apenas se
não houver candidato observado). São identidades literais do pacote escolhido.

Uma associação por jogo do inventário nominal das semanas/times, incluindo
jogos sem observação. Réplicas idênticas de pedidos/associações/conjuntos são
normalizadas; divergência para o mesmo gameId recusa, não escolhe latest. Cada
pedido produz um documento por time/papel/fundamento; pedidos [1], [2], [1,2]
produzem semanas e acumulada declaradas. Nenhum corte, target, mode ou seletor
PIT é entrada desta versão. Períodos/origens nunca são inferidos do relógio.

## Bundle físico e leitura

Consumir somente materialization-v2/input-v3 aceito: input.json, lineage.json,
COMPLETED.json. O reader aceito verifica versões, bytes, hashes, marcadores e
identidades; depois `materialize(relations, recoveredArchives, auxiliary,
derivedAt)` deve reproduzir integralmente input e linhagem. Esse caminho chama
prepare/adapter aceitos nos bytes embutidos e confronta onze relações, manifesto
completo, fontes, estatísticas/coberturas, receipts e qualificações. Nenhum banco,
rede, .env ou archive original é acessado. Não implementar outro adapter.

Saída `metrics-observation-bundle-v1`: manifest.json, request.json,
observations.json, shared-source/{input.json,lineage.json,COMPLETED.json} e
COMPLETED.json raiz. Uma cópia comum da materialização, não Parquets por grupo.
Referências físicas fixas, relativas, sem symlinks, extras ou resolução de URLs.
Receipts e originais contêm roots históricos participantes das identidades;
essas strings são evidência imutável necessária, nunca locators usados na leitura.
Nenhuma configuração de conexão é exportada. Manifesto declara autocontido e
sem dependências externas. Copiar todo o diretório basta para validar novamente.
O source materializationId original não é reescrito para remover caminhos.

Manifesto contém implementationVersion, observationIds, mapeamento por
observationId/membro para a associação original, fieldScopes, source identities,
requestSemanticId e bundleId. BundleId cobre manifesto sem bundleId; inclui IDs
semânticos das observações e pedido sem apresentação/derivedAt, mas não hashes
físicos dependentes de formatação. COMPLETED cobre hashes dos seis arquivos e
manifesto e identidade. Reader refaz toda a projeção e confronta a saída exata,
além dos hashes. Originais rehasheados mas semanticamente adulterados recusam.
Staging irmão, rename exclusivo aceito e recusa de sobrescrita/public/data.

## Nova projeção pura

Após validação integral, núcleo só lê árvores JSON em memória e o pedido validado.
Confere escopos/participantes/versões/IDs/associação e universo nominal por calendário.
Estatísticas do grupo e general vêm dos mesmos originais; soma exata E5a,
contagens e denominadores próprios, nenhum sinal defensivo invertido. Um jogo
conta uma vez; cobertura compartilhada/alternativas não ampliam a amostra.

O schema E5c-1 permanece congelado, inclusive derivationVersion de formato
metrics-observation-projection-candidate-1; implementationVersion separado
identifica a implementação E5c-2. Não importar verify.py de fixtures. Validar
estrutura e consistência operacional e usar schema/fixtures somente nos testes.
Geração/leitura se comparam por derivação operacional, não por premissas sintéticas.

Qualificação de conteúdo reutiliza Policy.proof aceito no regime sem corte
(usado pelo caminho retrospectivo), apenas para envelopes de completude/modelo/
calendário. Não chama select, não seleciona eventos, não emite retrospectivo ou
PIT. Origem confiada continua premissa explícita preservada da materialização.
Completude/modelo UNKNOWN não recebem garantia por recibo atual ou cálculo válido.
Cobertura esperada só conhecida com CALENDAR_COMPLETE e PERIOD_CLOSED para todas
as semanas declaradas; caso contrário expected/count/ratio null. Temporal é
sempre UNKNOWN e cutoff/target/kickoff null, inclusive com documentos temporais
na origem. Comparação/ranking/tese/elegibilidade pregame não são saídas.

Modelos conhecidos distintos ou mistura conhecido/UNKNOWN no conjunto solicitado
recusam o documento inteiro com IDs/motivo, pedindo separar pedidos/fontes;
não apagar EPA reconciliado só por todos os modelos serem UNKNOWN. Modelo do lote
não qualifica FILEs automaticamente. Fonte faltante fica membro ABSENT/statistics
null; associação original completa continua no manifesto mesmo quando campos
calculationId/artifactId do membro são null conforme schema E5c-1.

## Escopo de campos e incompatibilidade mínima

eligibleN/epaN/successN/epaMissingN/epaNonfiniteN/epaSum são mapeamentos literais
por time/papel/fundamento E5b-1. generalEligibleN vem do general do mesmo
jogo/time/papel. unknownFilterFlagsN é **contexto do jogo inteiro**, de
original.coverage.unknown_filter_flags_n, não contagem atribuída ao fundamento
ou time. fieldScopes vincula esse aviso a cada observação; totais somam apenas
jogos distintos dentro dela. Não somar esse campo entre grupos/times. Limitação
UNKNOWN_FILTER_FLAGS_GAME_SCOPE acompanha os dados, inclusive quando count=0;
zero significa nenhuma exclusão desse tipo na auditoria do jogo, não nova medição.

Contraprova mínima de fronteira aceita: PBP com zero linhas, metadata ausente,
calendário com um jogo => audit.scope=NO_SOURCE_OBSERVATION, nenhum grupo. E5c-1
permite fonte presente vazia UNKNOWN como volume0, mas não há vínculo de observação
por jogo que sustente esse zero neste caminho. E5c-2 conserva null/ABSENT e registra
EMPTY_SOURCE_SET_WITHOUT_GAME_OBSERVATION se todos FILEs PBP têm raw_rows=0.
Não promove arquivo vazio do lote a observação vazia por jogo. Já fonte com
jogada excluída e B vazio produz grupo observado UNKNOWN com volume0; COMPLETE
vazio só com prova/declaração aceita vinculada. Teste/relatório guardarão a
contraprova. Proposta futura, se necessário: evidência explícita de observação
vazia por jogo e versão de adapter/materializador que a represente; não alterar
silenciosamente os formatos aceitos agora.
