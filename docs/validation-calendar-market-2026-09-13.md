# Validação local: calendário completo e mercado opcional

Data: 2026-09-13. Continuação da implementação não commitada sobre `34a7ac54417263f646d95a4e3b68dd4d3f1c8984`, branch `main`.

## Resultado e causa

O filtro de `prepare_games()` exigia home/away moneyline e spread, descartando 160 jogos válidos. A fonte local tem 272 jogos REG/POST únicos; agora todos são preparados e persistidos. Mercado depende somente de um par completo e válido de moneylines, resultando em 112 mercados. A arquitetura Java REST local / Java batch / React estático permanece preservada.

## Contrato de atualização

- `rows_games`: todos os jogos preparados, com ou sem odds. É o valor gravado em `ingestion_runs.rows_games`.
- `rows_market`: mercados calculados/upsertados na execução, informado pelo resultado/log do pipeline; não é uma nova coluna no banco.
- Par completo válido substitui as duas moneylines e o mercado na mesma transação.
- Par parcial/ausente em jogo novo vira NULL/NULL; em conflito preserva o último par completo e seu mercado. Não há combinação de observações diferentes nem exclusão de mercado.
- Spread e total ausentes preservam cada linha conhecida; uma linha nova não nula a substitui.
- Moneyline zero, não inteira, não finita ou matematicamente inválida continua sendo erro explícito.
- O trio atômico de scores/result e seu tratamento de NULL/correção permanecem intactos.
- Warnings de mercado ausente são agregados por temporada.

## Contagens da mesma fonte por semana

Antes = seleção do loader anterior. Depois = persistência e exportação local corrigidas. Mercados = pares válidos; a diferença se deve exclusivamente à ausência de cotação.

| Semana | Antes | Depois | Mercados |
|---|---:|---:|---:|
| 1 | 16 | 16 | 16 |
| 2 | 16 | 16 | 16 |
| 3 | 16 | 16 | 16 |
| 4 | 16 | 16 | 16 |
| 5 | 15 | 15 | 15 |
| 6 | 14 | 14 | 14 |
| 7 | 7 | 14 | 7 |
| 8 | 0 | 14 | 0 |
| 9 | 1 | 15 | 1 |
| 10 | 1 | 14 | 1 |
| 11 | 1 | 13 | 1 |
| 12 | 5 | 16 | 5 |
| 13 | 0 | 14 | 0 |
| 14 | 0 | 15 | 0 |
| 15 | 0 | 16 | 0 |
| 16 | 4 | 16 | 4 |
| 17 | 0 | 16 | 0 |
| 18 | 0 | 16 | 0 |
| Total | 112 | 272 | 112 |

## PBP e integração local

A tentativa oficial `run_local.py --season 2026 --pbp-only --allow-missing-pbp` encontrou PBP publicado. Uma primeira tentativa limitada pelo sandbox falhou por DNS e permaneceu erro; a execução com acesso de rede autorizado baixou 323 linhas REG de 2026, semana 1, jogos `2026_01_NE_SEA` e `2026_01_SF_LA`. Produziu quatro métricas time/semana, sem uso de dados 2025, S3 ou banco remoto.

As duas migrations existentes foram reaplicadas via `supabase db reset --local --no-seed --yes`. O script opt-in `etl-pipeline/validate_local_calendar.py` conecta exclusivamente a `127.0.0.1:54322` (host e hostaddr explícitos), não lê `.env`, usa schedules reais e reaproveita somente metadados públicos dos times. Duas execuções consecutivas passaram, e a revisão final repetiu a validação:

```text
attempt=1 games=272 markets=112 pbp=323 metrics=4 ingestion_rows_games=272
attempt=2 games=272 markets=112 pbp=323 metrics=4 ingestion_rows_games=272
orphans=0 idempotency=PASS quote_preservation=PASS score_atomicity=PASS rollback=PASS
```

Também foi validado no PostgreSQL local: observações ausentes/home-only/away-only preservam o par e mercado anterior; par completo substitui ambos; scores completos substituem o trio; scores ausentes o preservam; falha real de FK em mercado faz rollback da escrita anterior de games. As alterações de teste de cotações/scores foram revertidas por rollback dentro desse banco local.

O exportador Java leu o banco local e escreveu apenas em diretório temporário:

```text
season=2026 games=272 teams=32 metrics=4 analyses_valid=0 analyses_missing=272 analyses_rejected=0
market_null=160
```

O banco local não possui caches de análise. O snapshot temporário foi removido após a verificação; nenhum dado de validação substituiu o snapshot público.

## Frontend e verificação visual

- Contexto estático vem de `manifest.defaultSeason` e `manifest.generatedAt`; REST local usa `/api/v1/publication`. Home, header, footer e seletor compartilham a temporada.
- Semana inicial: intervalo inclusivo UTC contendo hoje; entre semanas, próxima; antes, primeira; depois, última. Data é injetável nos testes; escolha independe de odds/análises.
- `favoriteOf()` aceita ausência e empate sem eleger mandante. Apenas fair probabilities válidas habilitam destaque, confiança, edge e sinal agregado.
- Desktop 1440×1000 e mobile 390×844: semana 8 exibiu 14 jogos sem mercado; nenhum favorito/sinal/confiança foi renderizado. Corrigidos seletores CSS mobile de away/home que antes não correspondiam às classes dos componentes.
- `CAR @ GB` abriu via navegação e URL direta. Times/data permanecem visíveis; aba Market informa indisponibilidade. Voltar preserva a semana manual.
- Contagem DOM de destaques indevidos: zero. `—%`: ausente. Nenhum overflow horizontal. Console sem warnings/erros.
- Detalhe `NE @ SEA`, aba Matchup: métricas reais 2026 presentes e renderizadas.
- Rede observada: documentos SPA, assets JS/CSS, logos ESPN, fontes Google e `/data/manifest.json` + `/data/seasons/2026.json`. Log do servidor somente GET; zero POST. Zero `/api/v1`, hostname `localhost`, Supabase ou Gemini. O servidor de teste usou loopback `127.0.0.1:4173`.
- A disponibilidade de análise cacheada sem mercado é coberta por fixture e teste de renderização; não foi fabricado cache no banco local.

## Gates e testes adicionados

| Gate | Resultado |
|---|---|
| Python completo | 79 aprovados, sem reduzir os 58 existentes |
| `python -m pip check` | No broken requirements found |
| Java | 17 aprovados, zero falhas/erros |
| Package Java 21 | aprovado |
| Frontend | 32 aprovados |
| Build Production | aprovado; JS 200,57 kB / gzip 63,10 kB |
| ESLint | aprovado, sem supressão de regras |
| `git diff --check` | aprovado |
| Integração local/idempotência | aprovado |
| Verificação visual desktop/mobile | aprovado |
| Bundle/segredos | zero literais proibidos; nove valores locais do `.env` verificados, zero vazamentos |

Novos testes Python cobrem calendário sem odds/spread, pares completos/parciais/ausentes, odds inválidas, atualização atômica e preservação com SQL executado offline, idempotência, limites de transação/rollback, contagens diferentes, ingestão do calendário completo e warnings agregados. HTTP 429/500 e timeout ampliam os testes de falhas de aquisição.

A contagem Java autoritativa vem exclusivamente do resumo final de uma execução limpa de Maven com Java 21. A contagem anterior de 26 somava indevidamente os 17 testes executados com nove XMLs residuais de `ApiSecurityConfigurationTest`, classe já removida, presentes em `target/surefire-reports`. Uma compilação limpa com o JDK 26 local não é suportada neste pacote e falha na inicialização do compilador/Lombok; Java 26 está fora do contrato de validação.

Novos testes frontend cobrem semana inicial, contexto do manifesto, schema incompatível, detalhe/análise sem mercado, ausência de sinais/percentuais fictícios, empate, odds inválidas e renderização de Home/header com temporada diferente de 2026. Novos testes Java cobrem contexto REST/UTC, jogo com mercado nulo e códigos de erro batch úteis e sanitizados.

## Arquivos desta continuação

- ETL: `load_games.py`, `tests/test_calendar_market.py`, `tests/test_etl.py`, `validate_local_calendar.py`.
- Java: `PublicationController`, `NflSeason`, `GameRepository`, `SnapshotOptions`, `SnapshotBatchApplication`, `SnapshotExporter`; testes `PublicationControllerTest`, `SnapshotAssemblerTest`, `SnapshotFailureTest`.
- React: clientes/contexto/calendário/model/types, Home/MatchupDashboard, Layout/SportsHeader/WeekSelector, GameRow/ModelSignal/MatchupHero/OverviewPanel/MarketComparison/ProbabilitySplit e CSS mobile; testes de mercado, calendário e cliente estático.
- Documentação: README, Spec, contrato do snapshot, ADR-010 e este relatório.

## Limitações e integridade

O snapshot público permanece exatamente o anterior: 112 jogos, oito análises e zero métricas. Aguarda o pacote autorizado de rollout remoto e não está pronto para commit/deploy. A fonte de schedules local preservada ainda tem scores/result nulos nos 272 jogos; o PBP adquirido já cobre dois jogos realizados. O rollout posterior deverá atualizar controladamente a fonte de schedules e o banco remoto antes de regenerar o snapshot. Nenhum score foi inferido do PBP neste pacote.

Changelog Supabase consultado em `https://supabase.com/changelog.md`; as mudanças observadas não exigem alteração do schema para este caminho PostgreSQL local. Nenhuma migration foi criada ou editada. Política editorial futura permanece apenas planejada. S3 legado preservado.

Zero conexão/mutação no Supabase remoto nesta continuação; zero Gemini/AWS/S3. Nenhum commit/push/deploy/tag/amend/troca de branch. `Handoff.md` foi apenas hashado e permanece não rastreado, sem alteração.

| Arquivo | SHA-256 preservado |
|---|---|
| baseline | `0f4c0e79cbf56dd2437a8f9fd720585cc069ffaa538b4abe674eda6fb6fe940e` |
| hardening | `70abdc879e6884a13f2990d56897969c71fecb1d26d7f49bc5b8b6801bb2258d` |
| Handoff.md | `b9622fbd1d5c9fa0fc345abc014b873bfc645762aab36d2668825ff7a5c40e64` |
| manifest público | `f343134e9a7a24a4b925f2aa29ffe6390cc78714a3fc3094b2a87f2f819a01ee` |
| temporada pública 2026 | `41dae3ff4b6a5e606a155156c7b38a567ff0b9caddcd4f1a989e3679b1947e3d` |

## Git final

O diff é cumulativo: inclui o pacote estático anterior não commitado. `git diff --stat` não inclui arquivos novos não rastreados.

```text
 .env.example                                       |  13 +-
 .gitignore                                         |   4 +-
 README.md                                          |  50 +++--
 Spec.md                                            |  61 +++---
 core-api/pom.xml                                   |  13 ++
 .../nflsideline/coreapi/CoreApiApplication.java    |  10 +
 .../coreapi/config/ApiSecurityConfiguration.java   |  75 --------
 .../coreapi/config/ApiSecurityFilter.java          |  56 ------
 .../coreapi/controller/AnalysisController.java     |  11 ++
 .../com/nflsideline/coreapi/llm/GeminiClient.java  |   4 +-
 .../repository/AnalysisCacheRepository.java        |  11 ++
 .../coreapi/repository/GameRepository.java         |   5 +-
 .../repository/TeamWeekMetricsRepository.java      |   2 +
 .../coreapi/service/AnalysisService.java           |  10 +-
 core-api/src/main/resources/application.yml        |   4 +-
 .../config/ApiSecurityConfigurationTest.java       | 130 -------------
 .../coreapi/config/HealthHttpIntegrationTest.java  |  48 ++---
 docs/runbooks/deploy-recovery.md                   | 165 +++-------------
 etl-pipeline/load_games.py                         |  79 +++++---
 etl-pipeline/tests/test_etl.py                     |   8 +-
 web-ui/.env.example                                |   2 +-
 web-ui/api/_proxy.test.ts                          | 166 ----------------
 web-ui/api/_proxy.ts                               | 214 ---------------------
 web-ui/api/v1/[...path].ts                         |   5 -
 web-ui/index.html                                  |   3 +-
 web-ui/public/vite.svg                             |   1 -
 web-ui/src/components/AnalysisSections.tsx         |   4 +-
 web-ui/src/components/GameRow.tsx                  |  18 +-
 web-ui/src/components/Layout.tsx                   |  62 +++---
 web-ui/src/components/MarketComparison.tsx         |  17 +-
 web-ui/src/components/MatchupHero.tsx              |  24 +--
 web-ui/src/components/ModelSignal.tsx              |   9 +-
 web-ui/src/components/OverviewPanel.tsx            |  26 +--
 web-ui/src/components/ProbabilitySplit.tsx         |   8 +-
 web-ui/src/components/SportsHeader.tsx             |  12 +-
 web-ui/src/components/WeekSelector.tsx             |   6 +-
 web-ui/src/index.css                               |   6 +-
 web-ui/src/pages/Home.tsx                          |  75 +-------
 web-ui/src/pages/MatchupDashboard.tsx              | 114 +++++------
 web-ui/src/services/api.test.ts                    |  12 +-
 web-ui/src/services/api.ts                         |  37 ----
 web-ui/src/services/model.ts                       |  45 +++--
 web-ui/src/services/types.ts                       | 103 +++++++++-
 web-ui/tsconfig.api.json                           |  19 --
 web-ui/tsconfig.app.json                           |   4 +
 web-ui/tsconfig.json                               |   3 +-
 web-ui/tsconfig.node.json                          |   4 +-
 web-ui/vercel.json                                 |   5 -
 web-ui/vite.config.ts                              |  13 +-
 49 files changed, 545 insertions(+), 1231 deletions(-)
```

`git status --short`:

```text
 M .env.example
 M .gitignore
 M README.md
 M Spec.md
 M core-api/pom.xml
 M core-api/src/main/java/com/nflsideline/coreapi/CoreApiApplication.java
 D core-api/src/main/java/com/nflsideline/coreapi/config/ApiSecurityConfiguration.java
 D core-api/src/main/java/com/nflsideline/coreapi/config/ApiSecurityFilter.java
 M core-api/src/main/java/com/nflsideline/coreapi/controller/AnalysisController.java
 M core-api/src/main/java/com/nflsideline/coreapi/llm/GeminiClient.java
 M core-api/src/main/java/com/nflsideline/coreapi/repository/AnalysisCacheRepository.java
 M core-api/src/main/java/com/nflsideline/coreapi/repository/GameRepository.java
 M core-api/src/main/java/com/nflsideline/coreapi/repository/TeamWeekMetricsRepository.java
 M core-api/src/main/java/com/nflsideline/coreapi/service/AnalysisService.java
 M core-api/src/main/resources/application.yml
 D core-api/src/test/java/com/nflsideline/coreapi/config/ApiSecurityConfigurationTest.java
 M core-api/src/test/java/com/nflsideline/coreapi/config/HealthHttpIntegrationTest.java
 M docs/runbooks/deploy-recovery.md
 M etl-pipeline/load_games.py
 M etl-pipeline/tests/test_etl.py
 M web-ui/.env.example
 D web-ui/api/_proxy.test.ts
 D web-ui/api/_proxy.ts
 D web-ui/api/v1/[...path].ts
 M web-ui/index.html
 D web-ui/public/vite.svg
 M web-ui/src/components/AnalysisSections.tsx
 M web-ui/src/components/GameRow.tsx
 M web-ui/src/components/Layout.tsx
 M web-ui/src/components/MarketComparison.tsx
 M web-ui/src/components/MatchupHero.tsx
 M web-ui/src/components/ModelSignal.tsx
 M web-ui/src/components/OverviewPanel.tsx
 M web-ui/src/components/ProbabilitySplit.tsx
 M web-ui/src/components/SportsHeader.tsx
 M web-ui/src/components/WeekSelector.tsx
 M web-ui/src/index.css
 M web-ui/src/pages/Home.tsx
 M web-ui/src/pages/MatchupDashboard.tsx
 M web-ui/src/services/api.test.ts
 D web-ui/src/services/api.ts
 M web-ui/src/services/model.ts
 M web-ui/src/services/types.ts
 D web-ui/tsconfig.api.json
 M web-ui/tsconfig.app.json
 M web-ui/tsconfig.json
 M web-ui/tsconfig.node.json
 M web-ui/vercel.json
 M web-ui/vite.config.ts
?? Handoff.md
?? core-api/src/main/java/com/nflsideline/coreapi/config/LocalCorsConfiguration.java
?? core-api/src/main/java/com/nflsideline/coreapi/controller/PublicationController.java
?? core-api/src/main/java/com/nflsideline/coreapi/service/NflSeason.java
?? core-api/src/main/java/com/nflsideline/coreapi/snapshot/
?? core-api/src/test/java/com/nflsideline/coreapi/controller/
?? core-api/src/test/java/com/nflsideline/coreapi/snapshot/
?? core-api/src/test/resources/
?? docs/adr/
?? docs/static-snapshot-contract.md
?? docs/validation-calendar-market-2026-09-13.md
?? etl-pipeline/tests/test_calendar_market.py
?? etl-pipeline/validate_local_calendar.py
?? web-ui/build/
?? web-ui/public/data/
?? web-ui/src/services/apiDataClient.ts
?? web-ui/src/services/calendar.test.ts
?? web-ui/src/services/calendar.ts
?? web-ui/src/services/dataClient.ts
?? web-ui/src/services/market.test.tsx
?? web-ui/src/services/publicationContext.ts
?? web-ui/src/services/runtimeClient.development.ts
?? web-ui/src/services/runtimeClient.production.ts
?? web-ui/src/services/runtimeClient.test.ts
?? web-ui/src/services/staticDataClient.test.ts
?? web-ui/src/services/staticDataClient.ts
```
