# Contrato recomendado 1.0.0 — candidato

Todas as regras abaixo são **propostas para E5b**, implementadas somente pelo modelo mecânico de exemplos E5a. A versão da população é `classified-scrimmage-v1`; não é um alias de `dropback_rate` nem do filtro legado. Identificação completa: `metricId@definitionVersion` + populationVersion + papel + recorte + revisões de fonte.

## 1. População e identidade

A unidade é uma jogada final de uma revisão identificada de PBP, vinculada a um jogo do calendário. Campos exigidos no adapter: `game_id, play_id, drive, season, season_type, week, posteam, defteam, play_type, qb_kneel, qb_spike, play_deleted, special_teams_play, two_point_attempt, epa`. `drive` pode ser null e não define elegibilidade. O adapter valida tipos, IDs e times; não imputa EPA, time, classificação ou flag desconhecida. Flags usadas no filtro devem ser binárias 0/1; valor null é desconhecido, outro valor é erro. Coluna inteira ausente é erro de schema, não zero implícito. Fonte local não contém campo `no_play`: o filtro usa `play_type`.

Chave operacional proposta `(game_id,play_id)` com play_id numérico finito, preservado sem truncamento. O dicionário menciona também drive; os três PBP locais têm game_id/play_id únicos. Por isso drive é armazenado e **diferença de drive na mesma chave é conflito**, nunca permissão para contar duas vezes. Identidade sem game_id/play_id é rejeitada. Réplica idêntica dos campos contratuais da mesma revisão é deduplicada e contada em `duplicateRowsIgnored`; mesma chave com conteúdo diferente falha a unidade de ingestão. Não escolhe último/primeiro por ordem. E5b precisa conferir esse guard em todas as partições do backfill antes de adotar a chave; fonte que exija outra identidade necessita adapter versionado.

Jogada candidata tem `play_type=pass|run`. Base elegível `B` exige:

1. Jogo, season/week e phase da jogada reconciliados com calendário; posteam e defteam distintos, presentes e exatamente os dois participantes. `season_type=REG|POST`; normalização de games WC/DIV/CON/SB para phase=POST preserva `round` original. `game_type=POST` genérico conserva round desconhecido, sem inventar rodada.
2. `qb_kneel=0`, `qb_spike=0`, `play_deleted=0`, `special_teams_play=0`, `two_point_attempt=0`, todos **conhecidos**.
3. Identidade sem conflito, e revisão da fonte íntegra. Não filtra por EPA nesta base.

Populações: `B_general=B`, `B_classified_pass=B∩(play_type=pass)`, `B_classified_rush=B∩(play_type=run)`. Para cada uma `E_f = B_f∩EPA finito`, por papel off/posteam e def/defteam. Geral conserva suas **próprias** somas/contagens; não é média de EPA passe e corrida com pesos iguais. As identidades de reconciliação com a partição pass+run são verificações, não substituição por taxas arredondadas.

| Situação | Regra proposta / justificativa / efeito comparado ao vigente |
| --- | --- |
| Kneel/spike | Excluir por flag=1 e por classificação fora pass/run. Null em candidato fica excluído/unknown_filter_flags, não assume 0; difere do fill_null vigente |
| Sack | Incluído em passe classificado, com EPA total da jogada; não é tentativa oficial de lançamento |
| Scramble | Incluído em corrida classificada. Não reclassificar para passe neste núcleo |
| Penalidade | `no_play` excluído. Penalidade em pass/run final válido permanece, inclusive EPA que reflete a penalidade; `penalty=1` isolado não anula uma jogada. Não tentar reconstruir jogada hipotética sem penalidade |
| Anulada/deleted | Excluir play_deleted=1; replay usa registro final da revisão. Não interpretar texto livre para decidir validade |
| Turnover | Incluir interceptação/fumble/safety em B, conservar EPA da fonte sob posteam/defteam do início; não subtrair turnover nem inverter sinal para defesa |
| Especiais/conversões | Excluir special_teams_play=1 e two_point_attempt=1 mesmo se classificado pass/run; tipos punt/kickoff/FG/XP já fora. Fake punt/FG marcado especial também fora. Isto **muda** o legado (126/130/5 conversões nos locais) e exige nova versão |
| Overtime | Incluir, sem peso extra, sob a mesma fase/jogo. Não excluir qtr>4 |
| Garbage time | Incluir integralmente; não há filtro wp, placar, tempo ou neutral script. Nenhum limiar ad hoc |
| Aborted play | Se final classificado pass/run e demais regras satisfeitas, incluir; flag aborted não é sinônimo automático de no-play |
| Incompleta | EPA ausente/não finito não tira jogada de B, mas tira de E. Metadado estrutural inválido bloqueia lote; flags null excluem candidato e contam motivo. Fonte de jogo parcial não é COMPLETE |
| Duplicada | Réplica idêntica uma vez; conflito rejeitado. Correção entre revisões fica em revisão nova imutável |
| REG/POST | Separar fases e temporada em toda agregação. REG e playoffs nunca entram na mesma média; fases PRE/outros não suportadas. POST pode conter WC/DIV/CON/SB sob escopo POST explícito, rounds retidos |

O dicionário primário descreve pass com sacks, run com scrambles e qb_dropback com tentativa/sack/scramble. `pass_attempt` da fonte inclui sacks; não equivale à estatística oficial de tentativas de passe. Um dropback analítico futuro poderia usar qb_dropback=1 sobre B e registrar flags inconsistentes, com scrambles migrando do fundamento terrestre. Não entra no núcleo. Frequência de dropback e EPA por dropback exigirão IDs próprios e backfill, sem substituir os IDs classificados. [Dicionário PBP oficial](https://raw.githubusercontent.com/nflverse/nflreadr/master/data-raw/dictionary_pbp.csv).

## 2. Estatísticas suficientes e 22 métricas

Para cada game/revision/team/role/foundation/populationVersion armazenar:

- `eligible_n = |B_f|` (contagem de volume com classificação e filtros conhecidos).
- `epa_n = |E_f|`, `epa_sum = Σ E_f.epa`, `success_n = count(E_f.epa>0)`.
- `epa_missing_n`, `epa_nonfinite_n`, de modo que `eligible_n=epa_n+epa_missing_n+epa_nonfinite_n`.
- Contagens por motivo de exclusão, `unknown_filter_flags_n` e linhas brutas/únicas/duplicadas, em auditoria por jogo. Motivos disjuntos por precedência: tipo fora → flag=1 (kneel, spike, deleted, special, conversion) → flags desconhecidas; erros estruturais não são jogadas excluídas silenciosamente.

Se jogo comprovadamente COMPLETE tem B vazio: eligible_n/epa_n/success_n=0, epa_sum=null, taxas/médias=null. Zero observado é diferente de falta de observação. `success_n=0` com epa_n>0 produz success rate **0**; `epa_sum=0` com epa_n>0 produz EPA **0**. Se fonte ausente/parcial: números completos são desconhecidos, não 0; eventual subset auditável tem status PARTIAL e não é apresentado como volume do jogo completo. O modelo E5a apenas agrega revisões COMPLETE.

Definições aplicáveis aos dois papéis e três fundamentos (general, classified_pass, classified_rush), com `definitionVersion=1.0.0` em todos os IDs:

| Família / IDs em contract.json | Fórmula / numerador / denominador exato | Unidade e direção proposta | Apresentação e interpretação |
| --- | --- | --- | --- |
| `{off,def}.epa.{foundation}` (6) | epa_sum/epa_n, null se epa_n=0 | pontos esperados/jogada do fundamento; off maior, def menor | EPA médio + epa_n/eligible_n + período. DEF é EPA **permitido**, sem inversão de sinal |
| `{off,def}.success_rate.{foundation}` (6) | success_n/epa_n; mesmo E do EPA, sucesso estrito EPA>0 | razão 0..1; off maior, def menor como **sucesso permitido ao ataque adversário** | percentual e success_n/epa_n. Não chamar de sucesso defensivo nem usar 1−taxa |
| `{off,def}.volume.{foundation}` (6) | eligible_n; numerador contagem, sem denominador | jogadas; sem direção de qualidade | inteiro + status de fonte; epa_n é amostra da eficiência, não substituto do volume |
| `{off,def}.frequency.{classified_pass,classified_rush}` (4) | eligible_n do fundamento / eligible_n geral, null se geral=0 | razão 0..1; sem direção de qualidade | percentual + N(fundamento)/N(geral). DEF descreve frequência enfrentada |

A frequência não condiciona presença de EPA; é ID novo, mesmo quando coincidentemente igual ao legado. Não usar epa_n geral para frequência de B. Não reconstruir success_n ou N(P/R) a partir de médias/taxas. `epa_n` de cada fundamento é o único denominador de sua eficiência; `plays_offense/defense` legados não o substituem.

Somas preservam decimais finitos sem arredondar por semana/jogo. Adapter converte float da fonte pelo decimal de sua representação round-trip (`Decimal(str(x))` / BigDecimal equivalente); não a partir do valor formatado. Somar em ordem canônica ou acumulador decimal exato, sem soma float dependente da ordem. Persistir numeric sem escala fixa para somas; bigint para contagens novas. Divisões usam DECIMAL128 somente na saída, preservando soma e contagem e sua razão exata para auditoria. JSON de exemplos usa razão racional ou decimal string; implementação Java deve produzir decimal string canônico com sinal exato separado da apresentação.

Na apresentação EPA: 3 casas, arredondamento HALF_UP; zero exato `0,000`. Não nulo cujo módulo <0,0005 aparece `+<0,001` / `−<0,001`, com valor exato no detalhe; nunca rotular como zero. Taxas a 1 casa percentual, com fração e contagens exatas no detalhe; pequenas taxas positivas podem aparecer `<0,1%`. Sem truncar outliers, aplicar valor absoluto ou tratar NaN/Infinity como zero. EPA zero não é success. Sinal vem do decimal original, não da string arredondada.

EPA depende do modelo da fonte e da população; não prova mecanismo causal, pressão, controle de trincheiras, força verdadeira ou vencedor. Zero de EPA não é média da liga. Success rate permitido pode ter direção menor favorável descritivamente, mas o motor atual continua com sua política NONE até revisão própria. Esta proposta não altera seleção editorial.

## 3. Corte: duas garantias distintas

`asOfInstant` obrigatório para novos recortes: ISO-8601 UTC `Z`, precisão de **segundos**, limite exclusivo para encerramento e disponibilidade; offsets são normalizados pelo adapter sem arredondar timestamps futuros para trás. `asOfDate` é uma entrada legada/atalho **explicitamente conservador**: `YYYY-MM-DDT00:00:00Z` (início da data, não fim). Nunca adivinhar horário de kickoff. Análise pregame precisa de targetGameId; o próprio jogo é excluído por ID em todas as janelas, mesmo se arquivo errado lhe atribuir data anterior. Se kickoff verificável existir, exigir asOfInstant≤kickoff; se ausente, não certificar momento pregame, apenas `TARGET_GAME_EXCLUDED; PREGAME_TIME_UNVERIFIED`.

Elegibilidade do evento exige `status=FINAL`, `event_upper_bound` **com evidência** `< asOfInstant`. É um limite superior comprovado do encerramento, não hora de início, `gameday`, última jogada inferida ou hora fixa somada ao kickoff. Pode ser encerramento oficial com timestamp ou momento em que um registro final foi comprovadamente observado; no segundo caso o bound é conservador e `event_time_basis=FINAL_OBSERVED_AT`. Precisão e evidência ficam registradas. Fonte sem esse bound recebe `EVENT_TIME_UNKNOWN`, excluída de recorte com garantia de instante. Não fabricar um fim de jogo às 23:59 nem deduzir duração típica.

`gametime` em schedules usa Eastern; converter kickoff com **America/New_York** e regra de DST, não offset fixo. Gameday isolado permite ordenar datas e reconhecer eventos em dias posteriores, mas não comprova encerramento antes de um instante no mesmo dia; weekly key nem permite distinguir jogos no mesmo período. Campos start_time/time_of_day/end_clock_time locais precisam de semântica e completude validadas antes de produzir bound. A opção mínima de E5b é registrar FINAL_OBSERVED_AT prospectivamente. Datas históricas sem evidência continuam sem bound verificável. [Dicionário schedules oficial](https://raw.githubusercontent.com/nflverse/nflreadr/master/data-raw/dictionary_schedules.csv).

Dois modos explicitamente identificados:

- `EVENT_RECONSTRUCTION`: seleciona eventos cujo encerramento é comprovado antes do corte, sobre revisões escolhidas do dataset atual. `available_at` pode ser null ou posterior ao corte; declarar `historicalAvailability=UNKNOWN_OR_NOT_PROVEN` e revisão ingerida posteriormente. Este modo **não** reconstrói o conhecimento da época. Útil em estudo retrospectivo quando há prova do tempo do evento; não habilita interpretação point-in-time.
- `POINT_IN_TIME`: além do filtro de evento, exige `available_at < corte`, `ingested_at < corte`, ambos comprovados para os **bytes da revisão** e registros de calendário/estado usados. Selecionar última revisão conhecida antes do corte pela ordem (available_at,revision_id), nunca a revisão “mais nova hoje”. Revision_id ordena só empate; conflito de bytes sob o mesmo revision_id falha. Não usar uma revisão corrigida depois. `available_at` é quando esses bytes comprovadamente ficaram disponíveis ao sistema; primeiro archive/receipt local pode ser evidência conservadora e coincidir com ingested_at, com basis explícita. Não é data do jogo. Histórico sem receipt não participa do modo estrito.

O modelo sintético contém uma revisão por jogo e verifica os dois modos; seleção entre revisões, DST e prova dos receipts são critérios de E5b, não funcionalidades E5a. `event_upper_bound`, available_at e ingested_at têm significados separados mesmo quando recebem timestamps iguais por uma observação real. `generatedAt` de JSON/contexto e `updated_at` SQL não os substituem.

## 4. Janelas sem mistura

Todos os recortes têm season, phase, targetGameId, asOfInstant, temporalMode, populationVersion, definitionVersion, calendarRevision e sourceRevisionIds; referências históricas possuem origin próprio. Nenhuma média agrupa temporadas/fases/versões diferentes. Rollups por jogo permitem filtrar cada evento antes de resumir semana; **dois jogos no mesmo período são duas identidades**, não sobrescrita nem uma linha semanal indivisível.

| Janela / ID | Seleção exata | Byes, lacunas, início |
| --- | --- | --- |
| SEASON_TO_CUTOFF / season_to_cutoff-v1 | Todos os jogos da season e phase explícitas que passam o corte, sem limite de número de semanas | Não substituir season pela anterior; temporada inicial pode ser vazia |
| LAST_3_CALENDAR_WEEKS / last_3_calendar_weeks-v1 | Semanas de competição NFL `max(1,target.week−3)..target.week−1` na mesma season/phase, depois corte por evento | **Recomendado junto da temporada** no primeiro enriquecimento. Semana de calendário aqui é week NFL do schedule, não ISO nem 21 dias móveis. Bye não estende janela; lacuna não busca week mais antiga. W1=[]; W2=[1]. Explicitar semanas concretas |
| LAST_3_GAMES / last_3_games-v1 | Últimos até 3 eventos FINAL elegíveis no calendário da mesma season/phase, ordenados por (event_upper_bound,game_id), **antes de checar PBP disponível** | Opcional, não núcleo inicial. Fonte faltante permanece entre os 3; não selecionar “últimos 3 jogos com dados”. Bye pode estender distância cronológica. Se bound é observação conservadora, ordenar não prova ordem real de encerramento: exigir ordem de eventos comprovada para esse modo em produção |
| WEEK_OBSERVATION / week_observation-v1 | Somar os jogos elegíveis dessa season/phase/week/time; reter lista de IDs, revisões e corte | É rollup derivado; dois eventos no período entram separadamente. Semana parcialmente encerrada é rotulada parcial |
| HISTORICAL_REFERENCE / historical_reference-v1 | Season explicitamente anterior (default proposto S−1), phase REG explícita, todos os eventos que passam o próprio corte, origin=HISTORICAL_REFERENCE | Bloco separado, nunca fallback silencioso/current form. POST histórico precisa de pedido explícito. Nunca misturar média histórica e corrente |

Qualquer rollup usa `Σepa_sum/Σepa_n` e `Σsuccess_n/Σepa_n`, frequências `Σeligible_n(f)/Σeligible_n(general)`. N=0 não entra como média 0. Um jogo sem EPA contribui ao volume/frequência e à contagem missing, mas não à soma/amostra EPA. Somas de conjunto vazio são null no contrato de resultado; acumulador interno pode usar 0 com count=0. Não fazer média de médias semanais; não usar distribuição de tipos como peso de médias arredondadas.

## 5. Cobertura, amostra, exibição e incerteza

Cobertura pertence a um calendário congelado independente do PBP e inclui estados por **evento esperado**, não só linhas observadas. Por janela registrar requestedWeeks, scheduledGameIds, eventEligibleGameIds, observedCompleteGameIds, metricObservedGameIds, excludedEventIds/reasons, actualWeeks e availabilityKnownGameIds. Informar `observedComplete/expectedEventEligible` com denominador fixo daquela revisão; zero esperado => razão null, não 100%. Jogo sem jogadas B com fonte COMPLETE conta como cobertura de fonte, mas sem observação EPA. Jogada EPA missing reduz cobertura da métrica, não transforma o jogo em bye.

O denominador de fonte mantém os eventos comprovadamente elegíveis pelo tempo mesmo se sua revisão PBP não passa a checagem de disponibilidade POINT_IN_TIME; esse jogo continua como lacuna, sem repor por outro. Se qualquer evento programado no escopo tem encerramento desconhecido e poderia anteceder o corte, a expectativa temporal não está provada: `expectedGames=null`, com IDs certos e incertos separados. Sem calendário com completude/revisão provada, também `expectedGames=null`, não uma razão inventada. Remover dados não aumenta observed/expected; não recalcular expected a partir do que sobrou. Cobertura semanal separa `OBSERVED`, `SOURCE_UNKNOWN`, `PARTIAL`, `NOT_YET_CLOSED`, `CALENDAR_UNKNOWN`, `NO_ELIGIBLE_PLAYS` e `NO_EPA_OBSERVATIONS` (B não vazio, E vazio). `BYE` só quando revisão completa do calendário e confirmação do período sem evento do time sustentam isso. Nenhum jogo programado em calendário incompleto => CALENDAR_UNKNOWN. Partida adiada ou período não fechado não é bye.

Distinguir `PBP_ABSENT` (arquivo/revisão ausente comprovado), `SOURCE_DELAY` (registro de publicação/checagem sustenta atraso) e `INGESTION_FAILED` (run e etapa vinculados ao jogo/revisão) somente com evidência. Ausência de linha semanal ou um run de temporada não basta. Estado padrão: `SOURCE_UNKNOWN`, com causa não identificada. No offline, estados/evidências explícitos vêm da fixture; não são deduzidos pela falta de rows.

Volume/amostra: eligible_n descreve volume; epa_n descreve denominador efetivo; número de jogos/semanas descreve cobertura de período, não denominador de passe. Exibição descritiva permite qualquer epa_n≥1 (ou volume conhecido, incluindo 0), com ressalva de observação única e parcialidade. **Não propomos amostra mínima estatística**: não existe estudo para justificá-la.

Versões de modelo EPA conhecidas diferentes são rejeitadas no mesmo rollup; UNKNOWN é permitido somente com limitação explícita e revisões de bytes identificadas, sem alegar igualdade do modelo.

Comparação descritiva elegível no primeiro consumidor novo: versões, população, métrica/papel correspondente, season/phase/origin, modo/corte e tipo de janela iguais; ambos têm epa_n≥1 para eficiência, cobertura de fonte esperada completa conhecida e nenhum EPA missing/nonfinite em B da métrica e nenhum candidato excluído por flag desconhecida. Times podem ter byes/contagens diferentes; listar ambos os conjuntos de jogos/semanas e volumes, sem alinhamento artificial nem diferença como vantagem projetada. Caso contrário, valores podem aparecer separados com limitações, mas `comparisonEligible=false`. Isto é uma política de integridade/exibição conservadora, **não** significância, confiança, superioridade estatística ou regra de seleção claims v5.

Incerteza estatística permanece `NOT_ESTIMATED`. Uma observação, três jogos ou cobertura completa não validam independência, tendência, persistência ou previsão. Fases pós-temporada têm suas próprias janelas explícitas; não usar número de semana para interpretar phase sem calendário.
