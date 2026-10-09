# E5b-3 — contrato anterior ao código

Base confirmada: `8176e08668a6db4c837fb4de60f52d9b9011217e`.
Contrato interno `metrics-temporal-input-v1` / `metrics-temporal-result-v1`,
algoritmo `metrics-temporal-1.0.0`, política `materialized-evidence-v1`.
Detalhes finais e ajustes de política estão em [CONTRACT.md](CONTRACT.md).
Nenhuma compatibilidade implícita com editorial, FrozenContext ou snapshot.

## Entrada materializada

Um pacote JSON contém `inputVersion`, `policy`, `resources`, `evidence` e
`calculations`. Recursos imutáveis têm `revision_id`, `kind`, `dependencies`,
`available_at`, `ingested_at`, `payload`. IDs iguais e conteúdo divergente falham;
réplicas idênticas deduplicam. FILE preserva source_revision_id/SHA, bytes base64
(integridade conferida) e origem. SET preserva source_set_id e membros inteiros,
inclusive multiplicidade. CALENDAR depende de um SET de calendário e congela
season/phase, jogos, completude e períodos fechados. STATE congela estado e bound
por game_id e calendar_revision_id. METADATA materializa documentos necessários.
Cada cálculo preserva calculation_id, coverage_revision_id, calendar_revision_id,
pbp_revision_id (SET), metadata_revision_ids, jogo congelado, completeness,
model, source_models por FILE, versões, unknown_filter_flags_n e os 12 grupos de somas E5b-1.
Esses IDs não são aliases. O instante de derivação é separado, explícito no pedido;
não exige existência passada do cálculo determinístico sobre fontes conhecidas.

Envelopes são `{value, evidence_id}` ou null. Evidências têm evidence_id, kind,
subject_id, origin, reference, recorded_at, value e dependencies (recursos).
`recorded_at` significa recebimento/registro comprovado segundo a política local,
não updated_at genérico. Todas as referências são resolvidas no pacote. O núcleo
não acessa URIs nem autentica documentos externos. A política contém origins
explicitamente confiadas pelo chamador; essas premissas entram na saída.

## Qualificação mecânica

| kind | Permissão sob origem aceita e vínculo exato | Não comprova |
|---|---|---|
| HASH_CHECK | nenhuma temporal; bytes FILE são rehashados | autenticidade, tempo, completude |
| ARCHIVE_OBSERVATION | available_at conservador = recorded_at; observação local | disponibilidade anterior, ingestão, fim, completude |
| SYSTEM_INGESTION | ingested_at e disponibilidade conservadora = recorded_at | disponibilidade anterior ou estado do jogo |
| FINAL_OBSERVATION | FINAL e bound = recorded_at | encerramento exato anterior à observação |
| EVENT_END_BOUND | bound explicitamente documentado em value | disponibilidade do documento antes de recorded_at |
| CALENDAR_COMPLETE | completude do calendário indicado, value=true | período fechado |
| PERIOD_CLOSED | fechamento da semana indicada no calendário | ausência de evento sem calendário completo |
| PBP_COMPLETE | completeness COMPLETE/PARTIAL da cobertura indicada | completude do EPA/flags |
| METADATA | valor declarado (modelo/kickoff/causa específica) | certificação independente universal |

Origem não aceita => DECLARATION_UNPROVEN; envelope ausente => UNKNOWN.
Mesmo origem aceita exige kind/subject/value coerentes. PIT exige recorded_at
< corte e dependências elegíveis para TODA evidência usada. Instantes das fontes
exigem provas separadas de disponibilidade e ingestão. SET herda o máximo dos
membros e preserva todos; CALENDAR/STATE/METADATA exigem seus próprios instantes
mais as dependências. Declarações aceitas necessárias entram no máximo de
disponibilidade composto pelo recorded_at conservador e precisam anteceder o corte
antes de disputar a seleção. SYSTEM_INGESTION também prova disponibilidade no mesmo
instante, nunca anterior; FILE/SET e payloads originais permanecem preservados. Evidência posterior nunca retrodata uma declaração.

## Seleção, janelas e saída

PIT: validar tudo, selecionar calendário elegível por (available_at, revision_id),
selecionar estados por jogo na mesma ordem, filtrar FINAL/bound < corte, selecionar
cálculos sobre o calendário escolhido e fontes inteiras elegíveis por
(max disponibilidade das dependências/evidências necessárias, revision_id). Para o cálculo,
revision_id apenas desempata a revisão temporal do pacote; source_set_id identifica
os bytes compostos usados. Nenhum recálculo cria disponibilidade retroativa.
EVENT_RECONSTRUCTION exige mapa explícito de calendário/estados/cálculos; nunca
escolhe revisão atual silenciosamente. Bound ainda precisa passar corte, mas
recebimento posterior é permitido e relatado. Em ambos excluir target por ID.
Kickoff aceito exige corte <= kickoff; sem prova PREGAME_TIME_UNVERIFIED.

Corte aceita instante com offset, normaliza UTC e exige segundos inteiros.
asOfDate mapeia exclusivamente para meia-noite UTC e registra o mapeamento.
Evidências preservam string/offset/precisão original; comparação usa fração exata
(inclusive mais de seis casas). Calendário local usa America/New_York, rejeita
horários DST ambíguos/inexistentes; ausência permanece null. Kickoff não é bound.

SEASON_TO_CUTOFF: season/phase pedidas; LAST_3_CALENDAR_WEEKS:
max(1,targetWeek-3)..targetWeek-1; WEEK_OBSERVATION: week explícita;
HISTORICAL_REFERENCE: season anterior explícita, origin próprio, sem fallback.
LAST_3_GAMES não implementado: bounds conservadores não provam ordem real.
Semanas vazias não ampliam recorte. Dois jogos na semana permanecem dois IDs.
REG/POST/round nunca são deduzidos de week.

Expectativa parte do calendário selecionado. Evento elegível sem PBP permanece
no denominador. Completude do calendário desconhecida, período não fechado ou
encerramento incerto => expectedGames=null, IDs certos/incertos preservados.
BYE exige calendário completo e período fechado, sem evento do time.
Ausência sem causa comprovada é SOURCE_UNKNOWN. COMPLETE exige prova aceita;
subset UNKNOWN/PARTIAL tem agregado separado. Não se trata falta como zero.

Somas exatas: EPA=sum/epa_n, SR=success_n/epa_n, volume=eligible_n,
frequência=eligible_n(f)/eligible_n(general). Razões guardam numerador/denominador
sem arredondamento. Modelos conhecidos diferentes não agrupam; UNKNOWN é grupo
separado com limitação, não igualdade presumida. População/definição divergente
é rejeitada. comparisonEligible é por fundamento/grupo e exige fonte completa
esperada, EPA sem missing/nonfinite, flags conhecidas, modelo conhecido e amostra
EPA>=1 (eficiência). Incerteza estatística NOT_ESTIMATED. Comparação entre dois
resultados exige também scope/mode/corte/versões/roles iguais.

Saída: validação estrutural, seleção/rejeição de revisões e razões, jogos e
lacunas, cobertura/fundamentos, agregados completos/subsets separados,
evidências usadas/qualificadas, limites, pedido normalizado e identidade.
Identidade do resultado selecionado não depende de alternativas futuras rejeitadas;
audit_id inclui o pacote integral e decisões. derivedAt é execução, separado da
identidade semântica. CLI valida antes de publicar em destino novo com marcador,
rename exclusivo e proibição de public/data. Falhas não publicam artefato parcial.

## Mapeamento E5b-2 e lacunas

metric_source_revision/blob => FILE; source_set/member => SET;
metric_calculation => calculations/metadata; coverage + calculation_coverage =>
jogo/coverage_revision_id; team_game_metric_sums => statistics;
archive_receipt => ARCHIVE_OBSERVATION com receipt_id original adicional;
persisted_at somente como SYSTEM_INGESTION se política/registro provar a ligação
àqueles bytes. Artefato/file preservam cálculo original, não timestamps novos.
Calendário completo/fechamento/estado/kickoff precisam de documentos explícitos
arquivados, não da entidade games mutável. Não há leitor SQL ou writer novo.

Exemplo mínimo da lacuna: FILE histórico tem hash e receipt de outubro, manifesto
declara available_at setembro com {basis,reference}. Sem registro confiável de
setembro, PIT em setembro exclui; reconstruction só funciona se existir bound
aceito do evento. Relações E5b-2 preservam declaração e receipt, mas não fornecem
prova histórica ou estado temporal automaticamente. E5b-4 precisa materializador
que conserve precisão/origem e documentos autenticados pela política da aplicação;
nenhuma migration é proposta silenciosamente por esta entrega.
