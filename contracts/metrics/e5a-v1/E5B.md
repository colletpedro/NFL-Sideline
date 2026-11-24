# Plano executável E5b — condicionado à revisão de E5a

É um plano de implementação, **sem SQL executável nesta entrega**. Primeiro enriquecimento: núcleo classificado + temporada acumulada e últimas três semanas NFL, observações semanais derivadas, histórico separado. LAST_3_GAMES fica opcional e exige ordenação real dos eventos comprovada. Motor/claims/BASIC/FULL e publicação continuam em entregas próprias.

## 1. Campos suficientes versus faltantes

| Necessidade | Já disponível | Falta / ação mínima |
| --- | --- | --- |
| EPA, SR geral e por tipo | PBP epa, play_type, posteam/defteam; médias/volumes gerais legados | Preservar soma, epa_n e success_n por fundamento/papel; não inverter defesa |
| Volume/frequência | PBP classificado e flags; dropback_rate legado tem outra definição | eligible_n independente de EPA; contagens missing/nonfinite; nomes novos explícitos |
| População reproduzível | PBP local tem flags de kneel/spike/deleted/special/conversion | Loader hoje seleciona só oito colunas; adapter novo deve preservar campos e validar desconhecidos |
| Identidade e fase | PBP game_id/play_id/drive/season_type; schedules game_id/type | Não persistidos nas métricas; validar joins, guardar phase REG/POST e round sem inferência por week |
| Completude/cobertura | Calendário completo de arquivos existentes; runs de temporada | Manifesto congelado por revisão/jogo, contagens brutas/únicas, estados/evidência; não deduzir completude só de linha presente |
| Horário | Schedules gameday+gametime local; PBP tem campos de relógio | games guarda só gameday. Novo metadata kickoff UTC com timezone origem; encerramento/bound com prova, nunca duração típica |
| Disponibilidade histórica | Sem receipt por bytes/revisão nos dados locais | available_at/basis/evidence nullable; coleta prospectiva; histórico desconhecido. ingested_at separado |
| Reconstrução de correções | Hashes de arquivos podem ser calculados | Archive de bytes, source revision imutável, data/model/schema version ou UNKNOWN, calendário/status revisados |

## 2. Decisão de persistência mínima: por jogo e revisão

**Escolhida: estatísticas suficientes por jogo**, com rollup semanal derivado após filtrar eventos. Acrescentar apenas somas semanais melhoraria ponderação, mas continuaria incapaz de excluir um jogo da mesma semana, separar reagendamento, distinguir dois eventos, resolver fase e avaliar revisão disponível antes do corte. Guardar só gameday em uma linha semanal não sustenta instante. Não armazenar PBP inteiro no banco inicialmente: manter Parquet arquivado com SHA-256 para auditoria.

Três relações novas, com nomes propostos (detalhes DDL em E5b-2):

| Relação | Chave / campos / invariantes |
| --- | --- |
| metric_source_revision | `revision_id` content-addressed; kind PBP/SCHEDULE, season, file_sha256, archive_locator, source_schema_hash, source_model_version nullable/UNKNOWN, adapter_version, source_uri, fetched_at nullable, available_at nullable, availability_basis/evidence nullable, ingested_at comprovado, raw_rows. Bytes/revisão imutáveis; timestamp de ingestão não fabrica disponibilidade anterior |
| game_metric_coverage_revision | `coverage_revision_id` hash de conteúdo; game_id FK games; schedule_revision_id e pbp_revision_id nullable; season/week/phase/round/participants **congelados**, status com prova, kickoff_at/precision/basis nullable, event_upper_bound/basis/evidence nullable; pbp_status/evidence, expected_unique_rows nullable, raw/unique/duplicate/excluded counts e motivos, known/unknown flags, calculation_version. Inclui jogos esperados sem PBP; calendário completo/fechamento de período vem de manifesto arquivado ligado à schedule_revision |
| team_game_metric_sums | PK `(coverage_revision_id,team,role,foundation,population_version,definition_version)`; eligible_n/epa_n/success_n/missing/nonfinite bigint, epa_sum numeric nullable; FK de team, checks de contagens e reconciliação. No máximo duas equipes × dois papéis × três fundamentos por jogo; materializar inclusive papel/fundamento vazio de fonte COMPLETE, sem inner join eliminatório |

`metric_source_revision` identifica **bytes**, não um run; mesma fonte idêntica reingerida não vira revisão nova nem empurra available_at. Primeiro receipt confiável é preservado; uma prova melhor posterior só acrescenta evidência auditável, sem retrodatagem implícita. Outro hash => revisão nova. `coverage_revision_id` incorpora referências de fonte, status/proveniência e definição, porque esses metadados também podem mudar. API de seleção não se baseia em PK sequencial ou updated_at. Tudo que entra no contexto congela a identidade das fontes escolhidas.

Arquivo do calendário deve preservar o conjunto completo e os períodos fechados, não apenas lista dos jogos observados. Sem prova de completude/fechamento, não emitir BYE nem cobertura percentual esperada. Banco pode guardar resumo de manifesto na source revision e archive_locator; o conteúdo completo deve permanecer recuperável e validável offline. Instantes são timestamptz UTC, fonte Eastern convertida com IANA/DST, nunca offset fixo. Em primeiros ingests, bound `FINAL_OBSERVED_AT` é conservador e só permite cortes posteriores à observação; backfill não cria timestamp histórico de encerramento.

Somas de E vazio ficam null, contagens0 quando COMPLETE. Jogo PBP parcial/ausente não grava somas como observação completa; preservar subset auditável em archive, status/evidência na coverage. Invalidade estrutural/conflicto falha stage/lote antes de persistir métricas novas. Unknown filter flags excluem candidatos e deixam contador/limite explícito.

A migration futura é aditiva: criar com CLI conforme skill, após revisão; RLS e acesso SQL seguindo hardening atual, sem policies/grants anon/authenticated/PUBLIC, Data API permanece desativada. Não usar service_role fictícia para contornar permissões. Tests/migration locais em stack isolada E5b; nunca reexecutar baseline remota. Novo acesso JDBC/psycopg2 exige grants deliberados da role de aplicação nos objetos novos.

## 3. Compatibilidade e impacto em cada camada

- **ETL:** adapter/cálculo puros novos primeiro. Integrar no orchestrator em stage próprio por season com transação e provenance; política seasons.py intacta. Contagens v1 antigas continuam com seu cálculo, inclusive conversões e volume condicionado a EPA. Novo caminho não preenche colunas legadas com definições novas. Se manter custo duplo, medir; não eliminar legado sem inventário de consumidores.
- **Persistência:** upsert/dedup de chave content-addressed sem mudar bytes; revisão nova por correção e atualização explícita de ponteiro de seleção atual. Falha não publica subset. Revisão antiga fica consultável; correção que elimina todas as jogadas deve produzir COMPLETE vazio/revisão nova, sem conservar médias antigas por ausência de linha.
- **Java:** domínio/repository novos para game sums, source revisions e coverage; DTO de scope com Instant. `MetricCatalog` vigente não muda silenciosamente. Novo catálogo `metrics-core-1.0.0` distingue classificados e permitido, direção SR descritiva. Reader/aggregator novo usa somas/contagens originais, não EvidenceWindow legado nem reconstrução por média×volume.
- **Contextos:** contrato novo namespaced `metrics-context-v1`, leitor separado; não fingir compatibilidade com input v3/FrozenContext, que admite só três semanas. Identidade contém métrica/população, season/phase, game IDs, janela e algoritmo, cutoff/time mode, calendário e revisões. Canonicalização inclui proveniência temporal; disponibilidade desconhecida faz parte do conteúdo. Não enviar o contrato novo ao seletor v5 por adaptação silenciosa. Integração editorial exige revisão explícita posterior.
- **Histórico:** arquivos/contextos/claims/resultados existentes continuam byte-for-byte; novas revisões não regeneram artefato antigo. Se uma comparação retrospectiva for solicitada, produzir artefato derivado novo com parent identity, nunca regravar o pai.
- **Frontend/visual/snapshot:** E5b prepara dados/DTO internos, não modifica E1 nem lê BASIC/FULL como autorização. Nova projeção/publicação exige contrato explícito (E6/E7); snapshot v1 continua legível e allowlist vigente preservada. Nenhum denominador novo é anexado a um texto antigo como se o tivesse sustentado.

O nome `dropback_rate` legado continua com semântica classificada condicionada a EPA; nova frequência classificada independente de EPA usa ID próprio. Conversões excluídas, flags desconhecidas e finitude podem mudar valores; apresentar relatório de diferenças, não “melhoria de eficiência”. Dropback verdadeiro não será um alias/adaptação silenciosa. Geral preserva sua população pass/run própria; não muda para “todas as jogadas NFL”.

## 4. Dados e futuro backfill

Escopo inicial recomendado: **2026 disponível localmente + 2025 REG como referência histórica**; 2023 REG+POST é corpus de controle da fase/identidade, sem referência automática aos três anos. Dados locais2026 somente W1/W2; preencher W3 em diante exige aquisição futura explicitamente autorizada em E5b, nunca declarar calendário como PBP observado. Não baixar 1999..corrente inteiro por default. A faixa seasons.py é suporte, não obrigação de backfill.

Backfill necessita PBP completo dos jogos escolhidos, schedules da mesma season com game_type/week/participantes, hash/archive e metadados de schema/modelo se existirem. Verificar jogo-a-jogo integridade, conversões removidas e contagens por papel/fundamento. Sem manifesto de completude, status não é COMPLETE presumido. Sem archive/receipt histórico, available_at passado fica UNKNOWN. Sem end bound verificável, métricas históricas podem existir como estatísticas **fora de recorte de instante certificado**, não servem como evidência pregame histórica garantida.

Antes de ampliar: congelar plano com seasons/phases/jogos, input hashes, limites de captura, relatório de ausência e definição. Simular carga em diretório de revisão e banco local isolado. Comparar com agregação direta de PBP e ledgers E5a, separar diferenças esperadas de população de defeitos. Repetir mesmos bytes deve manter identidades/contagens, não duplicar amostra e não deslocar receipts; correção deve criar versão nova. Usar role local de teste, sem dados de validação no snapshot público.

## 5. Entregas menores e critérios de saída

| Pacote | Trabalho concreto | Critério de saída |
| --- | --- | --- |
| **E5b-1 — adapter e somas puras offline** | Novo módulo sem DB/rede para projeção de campos, join calendar/PBP, normalização phase/round e IDs, dedup/conflictos, filtros classified-scrimmage-v1 e sufficient stats por jogo/papel/fundamento. CLI dry-run recebe arquivos explícitos/season policy e produz JSON de revisão, nunca public/data | Reproduz os 26 ledgers e propriedades; auditoria2023/2025/2026 reconcilia 126/130/5 conversões retiradas antes de filtros temporais, classificação sacks/scrambles, sem inferir contagens; outliers/zero/null preservados. Completeness UNKNOWN permitido, não ignorado |
| E5b-2 — schema/proveniência local | Migration aditiva das três relações, archive/receipt, constraints/RLS/grants e persistence writer em stack local isolada | Empty/complete/missing distintos, rollback/conflict, duas rodadas mesmo arquivo idempotentes, revisão corrigida imutável, roles públicas sem acesso; baseline remota intocada |
| E5b-3 — seleção temporal e janelas puras | Instant UTC, target exclusion, event bound, modo estrito/retrospectivo, calendário congelado, season e calendar3, week rollups/historical separado | Testes com mesmo dia/período, futuros/target, limite exclusivo, DST, receipts posteriores, status revisto, missing source no denominador, ausência de bound=>expectativa desconhecida; nenhum availableAt=gameday |
| E5b-4 — Java reader e contexto novo | DTO/repository/catalogue/aggregator; metrics-context-v1 e identidades; leitura coexistente com legado | Golden cross-language de somas/contagens/decimais e scopes, ordenação e hashes; rejeição de fase/versão incompatível; input v3/E1/artefatos antigos preservados |
| E5b-5 — integração ETL controlada | Stage aditivo, métricas de auditoria e estados por jogo/season; sem novo consumidor público | Fail-fast/rollback, sem overwrite do caminho legado, dry-run reconciliado; no schema error reclassified as missing; relatório de desempenho e idempotência |
| E5b-6 — backfill limitado para revisão | Depois da revisão dos anteriores, seasons/phases escolhidos, hashes de entrada e dry-run, carga local/ambiente explicitamente autorizado | Reconciliação por jogo/papel/tipo, source completeness e limites históricos explícitos, nenhuma mistura, revisão do orquestrador antes de consumo/publicação |

Primeiro pacote concreto é **E5b-1**. Não depende de comprovar disponibilidade histórica hoje, pois mantém a lacuna explícita; os recortes certificados de E5b-3 não incluem registros sem prova. Não juntar migration, backfill, leitor Java e mudança editorial numa entrega indivisível.

## 6. Questões críticas ainda abertas

1. **Completude e publicação histórica dos bytes:** não há receipts/manifestos por jogo nos dados locais; impedir promessa PIT histórica. Resolução: investigar metadados já arquivados ou começar receipts prospectivos. Sem evidência, valor permanece UNKNOWN; não bloqueia as somas offline.
2. **Encerramento de eventos e ordem real:** campos PBP de relógio não foram certificados como instante final. E5b deve provar semântica/completude antes de usá-los. Caminho mínimo disponível: FINAL_OBSERVED_AT prospectivo; históricos sem proof não passam corte de instante. LAST_3_GAMES continua opcional até ordenar eventos de forma verificável.
3. **Versão do modelo de EPA:** arquivos têm hashes, mas não versão do modelo certificada; registrar UNKNOWN. Comparações entre revisões com modelo conhecido diferente exigem nova política de compatibilidade, não pooling automático. Mudança upstream sem metadata precisa de limitação explícita e revisão.
4. **Identidade/completude fora dos locais auditados:** game/play únicos nesses três arquivos; validar guard envolvendo drive no futuro backfill. Conflito real bloqueia lote; decidir adapter novo só com exemplo concreto, sem relaxar dedup para fazê-lo passar.

As escolhas rotineiras (classificação, denominadores, conversões, janelas e grain por jogo) estão fechadas no candidato. Essas questões são lacunas de evidência, não licença para inventar valores. Aprovação do orquestrador da versão1.0.0 antecede E5b; compreensão humana E4 e amostra independente seguem paralelas.
