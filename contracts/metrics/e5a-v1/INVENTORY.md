# Inventário comprovado em 6d99e66

Esta página descreve **código existente**, não o contrato proposto. Inspeção estática e leitura local; banco remoto não consultado. A fonte do cálculo é `etl-pipeline/load_metrics.py::load_pbp/build_team_week_metrics`, não os nomes das colunas.

Defina `V`: EPA não nulo; `play_type ∈ {pass,run}`; kneel/spike nulos preenchidos com 0 e depois iguais a 0; posteam/defteam não nulos. `P=V∩pass`, `R=V∩run`. `S(X)=Σepa`, `N(X)=count`, `K(X)=count(epa>0)`. Ataque agrupa por posteam; defesa por defteam. Todos têm chave **(season,week,team_abbr)**, sem game_id ou fase, granularidade semanal. Unidade das médias: pontos esperados adicionados/jogada da respectiva população. Sem truncar sinal.

Consumidores: **J** = `TeamWeekMetrics`/repository, `TeamService` (season/l4/l6 são listas), `GameService` e API local; **E** = `MetricCatalog`, `AnalysisContextBuilder`, `EvidenceWindow`, claims e renderer; **S** = `SnapshotAssembler`/`SnapshotContract.MetricDto` público v1; **F** = tipos/clients React e comparação pública; **V** = projetor/laboratório visual E2/E4, que usa evidências congeladas do mesmo resultado.

| Campo / significado anunciado | Cálculo real; população; numerador/denominador | Unidade / direção vigente | Ausência | Consumidores / divergência |
| --- | --- | --- | --- | --- |
| off_epa_play / EPA ofensivo por jogada | S(V ataque)/N(V ataque) | EPA/jogada; HIGHER em E | Sem V não há grupo; não cria zero | J,E,S,F,V; “geral” só pass/run, não todo PBP |
| def_epa_play / EPA permitido por jogada | S(V defesa)/N(V defesa), EPA adversário **sem inverter sinal** | EPA/jogada; LOWER em E | Idem | J,E,V; ausente do DTO público S |
| off_epa_pass / EPA por passe | S(P ataque)/N(P ataque) | EPA/passe classificado; HIGHER | null se P vazio | J,E,S,F,V; denominador N(P) descartado |
| off_epa_rush / EPA por corrida | S(R ataque)/N(R ataque) | EPA/corrida classificada; HIGHER | null se R vazio | J,E,S,F,V; N(R) descartado; inclui scramble pela fonte |
| def_epa_pass / EPA permitido por passe | S(P defesa)/N(P defesa) | EPA/passe adversário; LOWER | null se P vazio | J,E,S,tipos F,V; N(P) descartado; não é sucesso defensivo |
| def_epa_rush / EPA permitido por corrida | S(R defesa)/N(R defesa) | EPA/corrida adversária; LOWER | null se R vazio | J,E,S,tipos F,V; N(R) descartado |
| off_success_rate / taxa ofensiva | K(V ataque)/N(V ataque), limiar estrito EPA>0 | razão 0..1; NONE em E | Sem grupo não há taxa | J,E; S/F público não expõem; não usa campo success da fonte |
| def_success_rate / sucesso permitido | K(V defesa)/N(V defesa) | razão 0..1; NONE em E | Idem | J,E; sucesso do **ataque adversário**, não 1−taxa |
| plays_offense / volume de ataque | N(V ataque) | contagem inteira; sem direção | Não há linha se sem grupo | J,E,S,tipos F; não é total de snaps, nem denominador de passe |
| plays_defense / volume de defesa | N(V defesa) | contagem inteira; sem direção | Idem | J,E; não exposto em S; depende de EPA presente |
| dropback_rate / “frequência de dropback” em E/F | N(P ataque)/N(V ataque) | razão; NONE | Se só run =0, só pass =1; sem grupo ausente | J,E,S,F; Spec §4.3 descreve proporção classificada corretamente; catálogo/label dropback não reconciliam |
| early_down_epa / EPA early downs | **Nenhum cálculo/INSERT** | catálogo EPA/NONE | Pode vir null ou valor persistido de outra origem; produtor desconhecido | J,E; coluna não comprova capacidade |
| explosive_play_rate / explosividade | **Nenhum cálculo/INSERT** | catálogo RATE/NONE | Idem | J,E; catálogo permite ponderação por total sem produtor comprovado |
| success/volume por fundamento; frequência de corrida | **Ausentes** | não implementado | não reconstruir | Nenhum contrato vigente os produz |

A frase da Spec sobre não usar sacks significa ausência de filtro/indicador sack no cálculo, não exclusão de sacks classificados pass; os exemplos locais confirmam inclusão. O catálogo anuncia dropback onde o predicado comprova outra população.

O loader faz **inner join** ataque/defesa: time-semana com apenas um papel desaparece. Não cria linha para semana vazia e não remove uma linha velha que deixe de ser calculada numa reingestão; `ON CONFLICT` substitui médias/volumes das linhas presentes, não reconcilia exclusões. `load_pbp` seleciona só oito campos e temporadas explícitas, mas descarta game_id, IDs de jogadas, fase e proveniência. Não há deduplicação, teste de finitude, validadores de flags, filtros explícitos de conversão/deleted/special, nem rastreamento de ausência por jogo. `is_not_null` não rejeita NaN/±Infinity. Times vazios (string vazia) também não são rejeitados nesse predicado. Impactos não finitos dependem do runtime; não há garantia contratual vigente para eles.

## Recortes e contratos existentes

- `AnalysisContextBuilder` registra `as_of_date_utc`, mas a consulta **não usa asOfDate**. REG seleciona semanas `< game.week`, depois as últimas **três linhas disponíveis por time**, podendo ser 2,4,5; não são três semanas de calendário nem três jogos. Se nada existe, usa as últimas três linhas do ano anterior como referência histórica. Para fases não REG abandona a série corrente e registra `POSTSEASON_METRIC_CUTOFF_UNVERIFIABLE`.
- `EvidenceWindow` separa time/métrica/temporada/origem. Deduplica IDs iguais, rejeita conflitos e pondera gerais/success/dropback por total pertinente **somente se todos os volumes são positivos**. Passe/corrida ficam `MEAN_OF_WEEKLY_MEANS`; nenhuma inferência de N(P/R). A ponderação vigente multiplica médias persistidas por volumes; E5a propõe somas de origem, ainda não existentes.
- `missingMetricWeeks` detecta ausência relativa às semanas de outras métricas do time; semana inteiramente vazia não aparece. `ContextQuality.COMPLETE` significa ambos os times correntes observados, não amostra suficiente. `EditorialParameters.expectedRecentWeeks` espera semanas numéricas w−3..w−1; v5 aplica requisitos distintos da seleção das últimas linhas disponíveis. Não chamar essa combinação de cobertura do calendário.
- `Evidence` identifica `tw:season:week:team:metric`. `FrozenContext` aceita entrada v3, no máximo três semanas por time, remove datas opcionais do canônico e recompõe janelas. Nada nesse caminho comprova disponibilidade histórica. E5b não poderá encaixar temporada inteira nesse leitor sem novo contrato.
- Snapshot v1 só inclui offEpaPlay, off/defEpaPass/Rush, dropbackRate e playsOffense. Exporta linhas da temporada, sem aplicar corte de métricas por jogo; `generatedAt` não equivale a availableAt. A comparação pública usa ataque contra ataque, barras absolutas e seleção de semana com fallback já registrada nos defeitos E0/E4. E4 melhorou apresentação do laboratório, sem corrigir esses cálculos públicos.
- Migration baseline: numeric sem escala fixa, contagens integer; apenas FK de time para métricas. `games` tem gameday/date e game_type, mas não horário, encerramento ou revisão de fonte. `updated_at` e runs de ingestão não são disponibilização histórica de cada revisão PBP. A migration de hardening preserva Data API desativada/RLS sem políticas; não há migration E5a.

## Evidências inspecionadas e lacunas

`test_etl.py::test_minimal_offense_and_defense_metrics` prova um exemplo de quatro jogadas, não casos de filtros, duplicatas ou temporalidade. Fixtures ETL são DataFrames sintéticos construídos nos testes, com Parquet temporário; `test_run_pipeline` cobre orquestração/rollback e ausência. Os testes `AnalysisContextBuilderTest` e `EvidenceWindowTest` documentam corte semanal, histórico, médias ponderadas gerais, médias simples específicas e conflitos. `VisualAnalysisProjectorTest` reconcilia 17 contextos conhecidos; testes snapshot mantêm allowlist/legados. Foram lidos; não reexecutados nesta alteração isolada.

Dados locais opcionais na **origem**, ausentes do checkout novo: PBP 2023/2025 completos REG+POST (285 jogos cada), 2026 somente semanas 1/2 (32 jogos). Não houve aquisição. Há 126/130/5 conversões elegíveis no legado; excluí-las na proposta muda números reais. Não há duplicatas game_id/play_id ou EPA não finito nesses arquivos; isso não prova ausência no universo da fonte. Calendários 2025/2026 pequenos estão versionados; PBP não. [Auditoria com hashes](local-audit.json).

Política de temporadas já suficiente: módulo `seasons.py`, 1999..corrente+1, Jan/Fev ano anterior, argumentos deduplicados/ordenados. Reutilizar em E5b; nunca inferir temporada pelo ano civil do jogo de janeiro.
