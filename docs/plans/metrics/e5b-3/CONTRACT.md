# Contrato interno E5b-3 — correção 1.0.1

Autoridade executável: `temporal_metrics.validation`, `evidence`, `times` e `core`.
Entrada **metrics-temporal-input-v2** (também aceita v1 fechado); saída **metrics-temporal-result-v2**;
algoritmo **metrics-temporal-1.0.1**; política **materialized-evidence-v1**.
É separado de metrics-offline-v1, contexto editorial e snapshot público.
O [desenho anterior ao código](DESIGN.md) registra a intenção; este documento
fecha os detalhes e ajustes de implementação.

## Estrutura de entrada

Campos são fechados: faltantes/inesperados falham antes de publicar. IDs são
strings não vazias. Contagens são inteiros não negativos, somas decimais finitas
são strings. Documentos auxiliares usam inteiros e strings decimais, não floats.
Os [pacotes completos](../../../../etl-pipeline/tests/fixtures/temporal_metrics/package.json)
são o exemplo de todos os tipos. Não se acessam caminhos ou URIs dessas fontes.

```text
inputVersion
policy: {policyVersion, trustedOrigins: [origens explicitamente confiadas]}
resources: [{revision_id, kind, dependencies: [revision_id],
             available_at: envelope|null, ingested_at: envelope|null, payload}]
evidence: [{evidence_id, kind, subject_id, origin, reference,
            recorded_at, value, dependencies: [revision_id], receipt?}]
calculations: [{revision_id, calculation_id, coverage_revision_id,
               calendar_revision_id, pbp_revision_id, metadata_revision_ids,
               game, versions, completeness, model, source_models,
               unknown_filter_flags_n, statistics, source_cause?}]
envelope: {value, evidence_id} | null
```

`revision_id` do candidato de cálculo é identidade **da revisão temporal do
pacote**, não substitui calculation_id, coverage_revision_id, source_revision_id,
source_set_id ou receipt_id. Pode incluir a associação do cálculo com documentos
auxiliares. Nomes de IDs não determinam cronologia. Réplicas idênticas deduplicam;
mesmo ID com conteúdo divergente falha no pacote. Não há catálogo persistente
para detectar conflitos entre invocações sem ambas as revisões materializadas.
IDs legados são preservados e não recalculados com um hash novo de falso formato.
O materializador deve ter validado semântica/bytes pelo adapter/writer aceitos;
aqui se validam somas, vínculos e invariantes, sem recalcular jogadas.

| kind | payload fechado | Semântica |
|---|---|---|
| FILE | source_revision_id, sha256, bytes_base64, origin | SHA conferido sobre bytes; revision_id=source_revision_id=sha256:hash |
| SET | source_set_id, source_kind (calendar/pbp) | revision_id=hash canônico E5b-1 da lista ordenada de IDs FILE; dependencies são membros inteiros, preservando multiplicidade |
| CALENDAR | season, phase, games, complete, closed_weeks | depende de SET calendar; cada game pertence à season/phase explícita |
| STATE | game_id, calendar_revision_id, status, event_upper_bound, kickoff, source_cause?, event_lower_bound? (v2) | depende do calendário indicado, game precisa existir nele |
| METADATA | origin, document | documento auxiliar explicitamente congelado, com dependências necessárias |

`game`: game_id, season, phase, round, week, home_team, away_team.
REG exige round REG; POST aceita WC/DIV/CON/SB ou null. Nenhum round por week.
`closed_weeks`: [{week, evidence_id}], com proof PERIOD_CLOSED sobre o calendário.
`complete`: envelope booleano. `status`: FINAL/SCHEDULED/POSTPONED/UNKNOWN.
`kickoff`: envelope de instante ou {gameday,gametime,evidence_id}; gametime null
fica ausente. America/New_York e DST são obrigatórios na segunda forma.
`source_cause`: envelope SOURCE_UNKNOWN/PBP_ABSENT/SOURCE_DELAY/INGESTION_FAILED,
aceito apenas como METADATA vinculado ao estado/cobertura correspondentes.

Cada cálculo contém os 12 grupos (2 times × off/def × 3 fundamentos), inclusive
vazios, no formato suficiente E5b-1. Valida eligible=epa+missing+nonfinite,
success<=epa, soma null iff epa_n=0, general=pass+rush e off=def adversária.
Rejeita grupos repetidos, times/season/phase/jogo incompatíveis. Versions tem
adapter=1.0.0, population=classified-scrimmage-v1, definition=1.0.0 para seleção.

`completeness`: envelope UNKNOWN/PARTIAL/COMPLETE, sujeito coverage_revision_id.
`model`: declaração de lote, sujeito calculation_id; `source_models`: mapa
**de todos os FILE IDs** do SET PBP para envelope de versão ou null, sujeito FILE.
Preserva o mapeamento por arquivo dos manifestos E5b-1/E5b-2. Declaração de lote
não promove fontes UNKNOWN. Modelos conhecidos diferentes dentro do SET excluem
a revisão inteira; modelo de lote contraditório também exclui. Entre jogos,
modelos diferentes ficam em grupos separados. UNKNOWN fica em grupo separado.
Alterar modelo pode criar calculation_id distinto com cobertura/somas iguais.

## Política e limites de prova

Origem confiada é premissa explícita do chamador. **Não é autenticação** obtida
por uma string origin, reference, hash ou envelope. `recorded_at` significa
recebimento/registro local confiável da evidência, segundo essa premissa;
nunca updated_at/gameday/kickoff/score/generatedAt. O núcleo não verifica
universalmente documentos externos nem procura prova na rede.

| Evidência | Valor aceito e vínculo | Garantia condicional |
|---|---|---|
| HASH_CHECK | não é aceito para tempo/completude | somente integridade; FILE ainda é rehashado pelo núcleo |
| ARCHIVE_OBSERVATION | sujeito FILE, receipt v1/hash/locator/SHA/observed_at coerentes; envelope.value=recorded_at | observação local e disponibilidade conservadora naquele instante |
| SYSTEM_INGESTION | sujeito recurso, envelope.value=recorded_at | ingestão daquele conteúdo pelo sistema; disponibilidade conservadora naquele mesmo instante |
| FINAL_OBSERVATION | sujeito STATE, bound=recorded_at | estado final observado e limite superior conservador, não horário exato anterior |
| EVENT_END_BOUND | sujeito STATE, bound=value, bound<=recorded_at | limite superior documentado pelo origin aceito |
| CALENDAR_COMPLETE | sujeito CALENDAR, value booleano | calendário completo declarado sob política |
| PERIOD_CLOSED | sujeito CALENDAR, value=week | período fechado declarado sob política |
| PBP_COMPLETE | sujeito coverage_revision_id, value=estado | completude de fonte da cobertura indicada |
| METADATA | sujeito do valor exato (kickoff normaliza offsets) | disponibilidade da declaração/modelo/causa; não autenticidade externa |

Archive conserva receipt_id original e demais campos, inclusive origem/root.
O núcleo verifica integridade/vínculo do receipt materializado, não acessa archive
ou seu root. Um administrador/chamador que falseie origin/relógio/documento está
fora da garantia. SYSTEM_INGESTION pode sustentar disponibilidade **no mesmo
instante**, pois o sistema recebeu esse conteúdo; não antecipa available_at.
Archive sozinho nunca sustenta ingestão, encerramento ou completude.

Qualificações: ACCEPTED_BY_POLICY; DECLARATION_UNPROVEN; UNKNOWN (envelope ausente);
EVIDENCE_NOT_KNOWN_AT_CUTOFF; EVIDENCE_DEPENDENCY_INELIGIBLE. Evidência não utilizada
fica NOT_USED_OR_BINDING_UNPROVEN. Capabilities são condicionais, não verificação
independente. Estado e completude aceitos continuam dimensões diferentes.

PIT exige todas as fontes **e todas as evidências usadas** antes do corte.
Cada recurso não-SET precisa de provas separadas de available_at/ingested_at.
SET usa máximos dos membros, nunca escolhe partes convenientes. Calendário,
estado e metadados incluem suas dependências. Para a revisão temporal composta,
a chave de disponibilidade é o máximo conservador das disponibilidades necessárias
e dos recorded_at das declarações aceitas necessárias. Os envelopes originais
permanecem intactos; esse máximo não retrodata bytes nem usa a hora da derivação.
Ordenação: `(disponibilidade elegível da revisão, revision_id)`. O máximo exato
em segundos racionais UTC está em selectionOrderAvailableAtEpochSeconds na auditoria.
Só depois se escolhe o maior candidato elegível. Disponibilidade do cálculo
reexecutado hoje é irrelevante; conhecimento das suas fontes/metadados é exigido.

Recursos CALENDAR/STATE com declaração temporal posterior elegível pela origem
são rejeitados **antes do desempate**, preservando uma versão anterior elegível.
Ausência de prova não é corrigida por score, data ou uma declaração mais recente.
EVENT_RECONSTRUCTION exige escolha nominal de calendário/estado/cálculo. Null no
mapa de cálculo reconhece uma lacuna deliberadamente. Não presume latest today.
Ainda exige FINAL e bound comprovado < corte, mas pode receber prova/revisão
posterior: postCutoffEvidenceIds e postCutoffResourceIds identificam isso.
Não representa conhecimento disponível na época.

## Pedido e janelas

```text
season, phase, team, targetGameId, targetWeek, mode, windows[], derivedAt
exatamente um: asOfInstant | asOfDate
week (obrigatório em WEEK_OBSERVATION)
historicalSeason + historicalPhase (obrigatórios em HISTORICAL_REFERENCE)
retrospective (obrigatório só em EVENT_RECONSTRUCTION):
  calendars: {"season/phase": revision_id}
  states: {"calendarRevision/gameId": revision_id}
  calculations: {"calendarRevision/gameId": revision_id|null}
```

Corte exige ISO com timezone/segundos inteiros e normaliza offsets para UTC Z.
asOfDate é YYYY-MM-DDT00:00:00Z; mapeamento fica no resultado. Evidências mantêm
strings/offsets/precisão originais, comparadas como frações exatas de segundo;
não há truncamento para microssegundos. Timestamp inválido/sem timezone falha.
Pregame exclui target por ID em todas as janelas. Kickoff aceito exige corte<=kickoff;
sem kickoff aceito registra PREGAME_TIME_UNVERIFIED, mesmo removendo target.
Eastern local ambíguo/inexistente falha; ausência de hora não é resolvida.

SEASON_TO_CUTOFF inclui eventos da season/phase que passam corte;
LAST_3_CALENDAR_WEEKS usa max(1,targetWeek-3)..targetWeek-1, sem extensão;
WEEK_OBSERVATION usa week explícita; HISTORICAL_REFERENCE usa temporada anterior
explicitamente pedida e bloco HISTORICAL_REFERENCE separado. Nunca há fallback.
LAST_3_GAMES não é implementado: bound observado não prova ordem real de eventos.
Reagendamento exige ID/estado/calendário congelados; week não resolve sozinho.

A expectativa parte dos jogos do calendário, filtrados por time/escopo. Fonte
faltante não tira evento temporalmente elegível do denominador. Calendário sem
completude, evento incerto ou semana solicitada aberta nas janelas semanais tornam expectedGames=null e
sourceRatio=null; IDs conhecidos/incertos continuam listados. Zero esperado tem
razão null. BYE exige calendário completo + período fechado + ausência de evento;
remover target não transforma a sua semana em bye. Sem fonte, causa específica
exige evidência; o default é SOURCE_UNKNOWN.

## Saída e auditoria

`result.json` separa structuralValidation, temporalEligibility, revisionDecisions,
resourceDecisions, evidenceQualifications, completeness por evento e guarantees.
`blocks` conservam origin/season/phase/window, semanas pedidas/observadas,
calendário, eventos/estados/cálculos/coverage/source IDs, lacunas e coverage.
`calculationsUsed` conserva estatísticas suficientes e vínculos originais por jogo
para auditoria autossuficiente, sem depender só de IDs externos.
Cada fundamento tem sums, source games, EPA observed games, casos sem jogadas/sem
EPA, eligibleN e epaN. Conjunto sem fonte não recebe estatísticas zero.

Agregados separam COMPLETE, AUDITABLE_SUBSET_UNKNOWN e AUDITABLE_SUBSET_PARTIAL,
modelo, off/def e fundamento. General conserva somas próprias reconciliadas.
EPA=soma/epa_n; SR=success_n/epa_n; volume=eligible_n; frequência usa eligible_n
geral **do mesmo grupo/jogos**, sem condicionar EPA. Razões incluem numerador,
denominador e fração racional exata; nenhum arredondamento intermediário ou
apresentação numérica aproximada é necessária nesta entrega. Defesa é permitida.

comparisonEligible é elegibilidade conservadora para **eficiência descritiva**,
por fundamento: cobertura esperada completa conhecida, COMPLETE, EPA>=1, sem
missing/nonfinite/flags desconhecidas, modelo conhecido compatível. Não é amostra
mínima estatística. Valores permanecem separados quando false. `comparison()`
também exige mesmas versões/papel/fundamento/modelo, season/phase/origin/window,
mode/corte e assinatura normalizada do período solicitado entre resultados, devolvendo os valores originais com razões de falha.
Volume observado, inclusive zero, continua auditável independentemente disso.
StatisticalUncertainty é sempre NOT_ESTIMATED; sem threshold/confidence/edge.

result_id é SHA da projeção semântica selecionada: pedido normalizado (sem momento
de execução/mapa de alternativas), versões, política, blocos e fontes/evidências
usadas. input_id inclui pacote integral; audit_id inclui decisões/alternativas e
derivedAt. Acrescentar alternativa/jogo em uma revisão de calendário futuro inelegível conserva
result_id; muda audit_id. Permutar coleções não muda resultado. Duplicata idêntica
não aumenta amostra; presença da réplica fica auditável no input_id. derivedAt é
instante explícito de derivação, sem sustentar conhecimento histórico.

CLI JSON valida antes de criar destino final. `COMPLETED.json` conserva hashes e
IDs. Publicação em diretório novo por rename exclusivo, limpeza de staging em erro,
recusa de sobrescrita/symlink existente/public/data, inclusive via caminho resolvido.
Não há leitura de .env, DB, rede, SQL, aquisição ou writer na execução temporal.

## Política corrigida antes da implementação (1.0.1)

SEASON_TO_CUTOFF e HISTORICAL_REFERENCE usam todos os eventos do time no
calendário completo da temporada/fase explícita e classificam cada ID:
1. targetGameId excluído, independentemente de semana/estado;
2. fora do corte se há limite inferior aceito do início efetivo >= corte;
3. elegível se FINAL com limite superior aceito de encerramento < corte;
4. incerto em todos os demais casos (inclusive upper bound >= corte).
Jogo elegível sem PBP continua esperado. Completude do calendário é necessária
para afirmar que não há IDs omitidos; calendário incompleto dá UNKNOWN mesmo
com todos os IDs conhecidos classificados. IDs incertos e motivos são auditáveis.

Fechamento semanal não define o denominador destas duas janelas por evento.
Uma semana aberta pode conter eventos já encerrados, alvo e eventos fora do corte.
Não se declara a semana fechada nem bye por isso. PERIOD_NOT_CLOSED continua
obrigatório para WEEK_OBSERVATION e LAST_3_CALENDAR_WEEKS; suas semanas não são
estendidas/substituídas. requestedWeeks acumuladas é apenas inventário de semanas
do calendário; não define o período solicitado nem sua assinatura.

Novo campo opcional STATE.event_lower_bound (somente input-v2): envelope de
instante com EVENT_START_LOWER_BOUND, sujeito STATE. Seu value é uma prova
materializada de que o início efetivo não ocorreu antes desse limite, inclusive
uma observação documentada de não início até aquele instante; não é kickoff
previsto. A política exige valor/offset semanticamente igual, origem confiada,
dependências e recorded_at >= bound. PIT exige conhecimento/bytes antes do corte.
Assim um documento recebido antes do corte que apenas prevê kickoff futuro NÃO
prova este bound: prova de não início até/depois do corte normalmente só existe
retrospectivamente. Isso mantém UNKNOWN em PIT sem prova suficiente. SCHEDULED
sozinho é incerto. Bound inferior aceito > bound superior aceito aborta como
EVENT_BOUNDS_CONFLICT. Kickoff permanece prova separada de pregame.

Reagendamento conserva calendário e estado congelados e vínculo exato por ID;
uma revisão posterior não disputa PIT. EVENT_RECONSTRUCTION exige mapa nominal
inclusive para eventos futuros/incertos e relata provas posteriores. Sem prova
nova suficiente, reagendamento é incerto; week/data/placar/duração não resolvem.
Nenhuma alteração do adapter/schema/archive/writer E5b-1/2 é necessária. Lacuna
para futuro materializador: recuperar documento de limite inferior com origem,
recebimento, dependências e vínculo STATE; não derivar do calendário mutável.

Cada bloco v2 publica requestedPeriod: window, season, phase, origin, mode,
cutoff UTC e selection. WEEK usa {week}; LAST_3 usa {weeks: lista ordenada única}
(inclusive vazio); acumulada/histórica usa {eventEndBefore: cutoff}. Histórico
conserva season/phase históricos e origin próprio, sem fallback. Não entram
team, targetWeek fora das janelas recentes, gameIds, actualWeeks ou result_id.
comparison recalcula a assinatura normalizada a partir do pedido e escopo,
rejeitando MISMATCH_REQUESTED_PERIOD; preserva checks antigos e valores originais.
Offsets equivalentes e listas de semanas semanticamente equivalentes são iguais.

Versionamento: input-v1 mantém exatamente os campos/kinds anteriores; v2 aceita
opcional lower bound. Inputs v1 ainda podem ser lidos, com futuro sem prova dando
UNKNOWN. Resultado v2 é deliberadamente uma nova estrutura (requestedPeriod,
outsideCutoffGameIds e auditoria de lower bound); NÃO se anuncia compatibilidade
para consumidores result-v1. Mesmo inputs v1 geram result-v2. Política de confiança
materialized-evidence-v1 permanece; algoritmo 1.0.1 muda seleção/expectativa e
comparação. Exemplos/verification 1.0.0 e docs historical-1.0.0 são históricos,
não gate atual. Versões e blocos alteram result_id; audit_id deriva do resultado,
decisões, pacote e derivedAt, e muda também. IDs E5b-1/2 não são recalculados.

### Lacuna de exatidão no exemplo E5a

O ledger congelado exclusive_cut_boundary declara event_time_basis=OFFICIAL_END.
A antiga regressão E5b-3 descartava essa informação ao materializar apenas
EVENT_END_BOUND. Na semântica de limite superior, bound igual ao corte não prova
encerramento igual ao corte: o evento pode ter terminado antes. O teste temporal
agora documenta UNKNOWN nessa materialização com perda de informação. Os 26
exemplos/23 testes e 12 hashes E5a permanecem idênticos. Proposta mínima futura,
se for necessário recuperar essa distinção: evidência separada EVENT_END_EXACT
com igualdade documentada e validação de vínculo/tempo; não alterar ou promover
silenciosamente EVENT_END_BOUND. Não implementada nesta correção.
