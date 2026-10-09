# Matriz mecânica de razões E5b-3 — algoritmo 1.0.1 / resultado v2

Não há um booleano universal válido. Erro estrutural aborta; decisão de revisão,
evento, cobertura, completude e comparação têm dimensões distintas.

| Dimensão / razão | Condição / efeito |
|---|---|
| IDENTITY_CONFLICT | Mesmo revision/evidence/calculation/coverage ID com conteúdo divergente no pacote: aborta |
| schema/bytes/vínculo/somas inválidos | Campos fechados, referência inexistente, cycle, hash/receipt/soma/contagem/join inválidos: aborta sem destino final |
| AVAILABLE_AT_UNKNOWN / INGESTED_AT_UNKNOWN | Envelope/prova ausente: recurso não elegível PIT |
| {AVAILABLE_AT,INGESTED_AT}_DECLARATION_UNPROVEN | Origem/kind/subject/value não sustenta timestamp: recurso não elegível PIT |
| {AVAILABLE_AT,INGESTED_AT}_EVIDENCE_NOT_KNOWN_AT_CUTOFF | Receipt/registro igual ou posterior ao corte: recurso não elegível PIT |
| *_NOT_BEFORE_CUTOFF | Timestamp elegível igual/posterior ao corte (guard adicional): recurso não elegível PIT |
| EVIDENCE_NOT_KNOWN_AT_CUTOFF | Declaração de bound/estado/calendário/modelo/completude/causa recebida igual/depois: revisão não disputa PIT |
| EVIDENCE_DEPENDENCY_INELIGIBLE / *_EVIDENCE_DEPENDENCY_INELIGIBLE | Documento necessário não passou corte: revisão não disputa PIT |
| SUPERSEDED_ELIGIBLE_REVISION | Elegível, mas anterior na ordem disponibilidade/revision_id: rejeitada na seleção |
| RETROSPECTIVE_NOT_CHOSEN | Revisão não está no mapa nominal do pedido retrospectivo |
| mapa retrospectivo ausente/inexistente | Pedido inválido: aborta; null só é permitido para reconhecer lacuna de cálculo |
| INCOMPATIBLE_DEFINITION_OR_POPULATION | Versões de adapter/população/definição diferentes: candidato não selecionado |
| INCOMPATIBLE_EPA_MODELS_IN_SOURCE_SET | Modelos conhecidos diferentes em membros obrigatórios: revisão inteira excluída |
| CALCULATION_SOURCE_MODEL_CONFLICT | Modelo conhecido do lote contradiz modelo conhecido por arquivo: candidato excluído |
| TARGET_GAME_EXCLUDED | ID é targetGameId, independentemente de week/date/status/bound: evento fora de todas as janelas |
| STATE_UNKNOWN_OR_INELIGIBLE | Nenhuma revisão de estado elegível: evento incerto, expectedGames=null |
| EVENT_NOT_FINAL | Estado selecionado não é FINAL: evento fora, expectativa incerta |
| EVENT_TIME_UNKNOWN | FINAL sem bound aceito: evento fora, expectativa incerta |
| EVENT_NOT_BEFORE_CUTOFF | upper bound>=cutoff: não elegível, mas posição incerta; expectedGames=null, não prova evento futuro |
| EVENT_PROVEN_OUTSIDE_CUTOFF | EVENT_START_LOWER_BOUND aceito >=cutoff: fora comprovado, ID em outsideCutoffGameIds; não exige fechamento da sua semana para janelas por evento |
| EVENT_BOUNDS_CONFLICT | lower bound aceito > upper bound aceito: aborta; não escolhe prova conveniente |
| PBP_REVISION_UNAVAILABLE_AT_CUTOFF | Evento elegível mas nenhum cálculo candidato passou política: continua no denominador esperado |
| SOURCE_UNKNOWN | Sem observação/causa comprovada: lacuna, nunca zero nem causa inferida |
| PBP_ABSENT / SOURCE_DELAY / INGESTION_FAILED | Só origem/kind/valor/vínculo/tempo aceitos sustentam causa específica; mantém expectativa |
| PREGAME_TIME_UNVERIFIED | Kickoff ausente/sem prova elegível: exclusão do target não certifica pregame |
| PREGAME_CUTOFF_AFTER_KICKOFF | Cutoff>kickoff aceito: pedido pregame falha antes da publicação |
| CALENDAR_INELIGIBLE_OR_UNKNOWN | Calendário não selecionado: expectativa/percentual null |
| CALENDAR_COMPLETENESS_UNPROVEN | Calendário conhecido mas completude não aceita: expectativa/percentual null |
| PERIOD_NOT_CLOSED | WEEK_OBSERVATION/LAST_3_CALENDAR_WEEKS sem proof elegível das semanas pedidas: expectativa/percentual null. Em acumulada/histórica o denominador depende da classificação temporal de todos os eventos, sem promover semana aberta a fechada/bye |
| EVENT_EXPECTATION_UNCERTAIN | Eventos conhecidos cujo encerramento não pode ser situado: IDs incertos, expectativa null |
| CALENDAR_UNKNOWN / NOT_YET_CLOSED | Estados semanais conservadores; não substituem byes/lacunas |
| BYE | Calendário completo, período fechado e nenhum evento do time; não expande janela |
| PARTIAL | Fonte observada com PARTIAL/UNKNOWN: conteúdo auditável, separado de COMPLETE |
| NO_ELIGIBLE_PLAYS | Fonte COMPLETE observada, B vazio: fonte conta na cobertura; volume observado0, média null |
| NO_EPA_OBSERVATIONS | B presente mas E vazio: volume auditável, eficiência null |

`EVIDENCE_NOT_KNOWN_AT_CUTOFF` e limites *_NOT_BEFORE_CUTOFF podem ocorrer no mesmo
candidato via dependências distintas. Auditoria conserva subjectId da causa, não
um motivo genérico que apague qual partição/documento falhou.

Falhas de comparação de eficiência: SOURCE_SUBSET, EXPECTATION_UNKNOWN,
INCOMPLETE_SOURCE_COVERAGE, EPA_INCOMPLETE, UNKNOWN_FILTER_FLAGS,
NO_EPA_OBSERVATIONS, EPA_MODEL_UNKNOWN, INCOMPATIBLE_EPA_MODELS_SEPARATED.
Comparação entre dois resultados adiciona MISMATCH_<campo> para versão,
papel/fundamento/modelo/scope, season/phase/origin/window e mode/corte.
MISMATCH_REQUESTED_PERIOD identifica assinatura normalizada diferente (sem usar
actualWeeks/time/IDs). WEEK exige mesma semana; recentes mesmo intervalo;
acumulada/histórica usam season/phase/origin/mode/corte por evento.
Valores originais permanecem disponíveis. Nenhuma razão define confiança,
significância, favorito ou vencedor; incerteza estatística NOT_ESTIMATED.

Registros 1.0.0: [matriz histórica](historical-1.0.0/REASONS.md),
[verificação histórica](verification.json). Gate atual: [correção](correction-1.0.1/README.md).
