# Expansão real 2026 W1–2 · candidata ao aceite humano

Entrega disponível localmente em **http://127.0.0.1:18096/**, com 32 jogos, 32 times e 576 leituras da expansão. O catálogo ativo possui **588 documentos únicos**: 384 individuais, 192 agregados inclusivos e 12 preservados (NE POST2025 e lacuna BAL W3). Diferença para a expectativa da expansão: zero. [Seleção nominal](selection.json), [pedido anterior à geração](request.json), [reconciliação](reconciliation.json), [HTTP](checks/http.json), [navegador](evidence/browser.json), [destinos completos](evidence/routes.json), [isolamento](checks/isolation.json).

## Base, fontes e preservação

Base exata `cae1fbba71368508681997e6ca167e92b56223f7`, referência limpa em `/Users/pedrocollet/.codex/worktrees/broadcast-media-pilot-v4/NFL Sideline`. Nova worktree gerenciada `/Users/pedrocollet/.codex/worktrees/broadcast-w12-expansion-v1/NFL Sideline`, branch `codex/broadcast-w12-expansion-v1`, inicialmente limpa. O plano foi registrado no commit `f683163` antes da implementação e da geração. A referência permaneceu limpa e na base ao final. Downloads possui arquivos locais históricos, que foram preservados. Nenhum merge, push, deploy ou publicação.

As duas cópias completas `real-recovery/20261019T024130Z-50e03b27` e `backups/20261019T024130Z-50e03b27`, em `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/`, foram conferidas arquivo a arquivo: 162 arquivos iguais por cópia. [Hashes completos](preserved-hashes.json). Os readers operacionais de materialização e bundle foram executados em ambas; `load_source` também rederivou materialization-v2/input-v3 a partir de relations/recoveredArchives/auxiliary. Conferir input.json ou um extrato isolado não foi usado como validação de linhagem.

Inventário integral observado: 2025 REG 272 jogos, POST 13, 2026 REG 32. A expansão seleciona exclusivamente 2026 REG semanas 1 e 2. O calendário original e a cobertura original de cada jogo concordam em participantes, semana e fase; cada time aparece uma vez por semana. As 32 associações aceitas são únicas; os IDs de cálculo, cobertura, artefato, archive, revisão temporal e calendário foram copiados dos originais, sem seleção latest ou identidade recalculada por conveniência.

Materialização `sha256:f7a70f61b442d8d631e858ac05c5c6191652b8d0ed0ffd5a7ac8094939a8d3fa`; input `sha256:9dc7e6de11af1d0e494877c82f6cc234be3cbe002ab5ee47bf29cc2cf1d3a0e6`. Os quatro SHA-256 de Parquets estão em selection.json/reconciliation.json. Fontes e cópias antigas permaneceram byte a byte idênticas.

## Catálogo ativo e artefatos

A configuração própria [lab-config.json](lab-config.json) fixa um único bundle novo, `entryId=w12-expansion-v1`, REAL_ARCHIVE, pin:

`sha256:05541d2703de6ad55e8858ebfbc17115a6d2747c01a2f73bad78d1eb7566876a`

O pedido combina três seleções explícitas de 2026 REG ([1], [2], [1,2], todos os 32 times, off/def × general/classified_pass/classified_rush) com as duas seleções nominais anteriores NE POST2025 e BAL W3 copiadas do pedido aceito. Essas últimas 12 observações preservam o mesmo observationId, valores, garantias e linhagem; somente derivedAt registra a nova projeção. Bundle/DTO/sessão novos não fingem ser a sessão anterior.

Os 36 documentos BAL/DAL W1/W2/W1–2 anteriores permanecem integralmente no bundle histórico, mas não são carregados como alternativas ativas. Cada escopo ativo tem uma única observação. Nenhuma escolha depende da ordem dos bundles, data mais recente ou fallback. Os links nominais da nova experiência usam a nova entry; links e servidores antigos continuam disponíveis nas respectivas entregas. Os recortes NE e BAL W3 continuam acessíveis pela navegação do confronto nesta nova sessão.

Raiz durável privada:

`/Users/pedrocollet/.codex/worktrees/broadcast-w12-expansion-v1/NFL Sideline/editorial/local-artifacts/broadcast-w12-expansion-v1/20261022-v1/`

Bundle operacional: `bundle/` nessa raiz (~58 MB). Cópia integral independente (~58 MB):

`/Users/pedrocollet/.codex/worktrees/broadcast-w12-expansion-v1/NFL Sideline/editorial/local-artifacts/broadcast-w12-expansion-v1/20261022-v1-portable/`

Ambos possuem os mesmos sete arquivos e hashes. A cópia passou no reader público em processo novo com cwd `/private/tmp`, com audit hook recusando qualquer abertura nas duas raízes preservadas e no bundle novo principal. Também passou em `metrics_observations inspect`. Nenhuma fonte foi renomeada ou removida para esse ensaio. Os bundles são autocontidos, não symlinks nem DTO/extratos. A raiz da entrega também preserva pedido, inventário, relatórios, logs e os quatro Parquets extraídos dos bytes originais para auditoria independente; tudo ignorado no Git. Duas cópias no mesmo disco não certificam recuperação contra perda do disco.

## Reconciliação independente

O script reconcile.py usa o auditor aceito `docs/plans/metrics/e5b-6/audit.py`, que lê os Parquets com Polars e acumula Fraction/Decimal sem importar o projetor ou seus acumuladores. Os quatro bytes embutidos na materialização validada foram extraídos e seus hashes conferidos antes da leitura.

Foram conferidos os 3.804 grupos originais observados, além das coberturas e contagens brutas; para os 588 documentos ativos foram conferidos **792 componentes por jogo**, numeradores, denominadores, volume geral, sucesso, EPA finito/ausente/não finito, somas exatas e razões. As combinações esperadas foram enumeradas independentemente dos documentos. Todo agregado da expansão contém exatamente os dois jogos pertinentes daquele time. Não houve soma de documentos, duplicação de jogo dentro de agregado ou média de médias. Flags de filtro desconhecidas mantêm escopo de jogo, sem serem apresentadas como medida individual de time.

Foram precomputados 1.552 valores decimais por aritmética racional independente e arredondamento HALF_UP; o navegador confrontou todos com o formatador real da aplicação. Em W1–2 não há EPA ausente entre as jogadas elegíveis observadas; a lacuna BAL W3 fornece o caso real de ausência de fonte e continua sem números.

## Aplicação, HTTP e navegação

Preservados calendário → confronto → participante → observação → retorno, busca por cidade/nome/sigla, destaque/apoios, arquivo recolhido, filtros e contexto na URL, histórico, acesso nominal e reload. A disponibilidade e os agrupamentos já eram derivados dos DTOs validados; a expansão os alimenta sem nova lista de times. A abertura local sem parâmetros passa a W1. O cabeçalho identifica arquivo 2026 W1–2, não a data de início do servidor como atualização dos dados.

A barreira HTTP e os contratos existentes não foram alterados. Cada startup lê o bundle completo e congela a sessão. Os 588 documentos foram servidos e comparados integralmente ao DTO do reader operacional. Dez recusas verificadas: Origin/Host/marcador inválidos, POST, GET com corpo, query/path não autorizados, sessão ausente/divergente (409), documento inexistente (404). Falha de catálogo em ensaio de transporte identificado no navegador não confirmou disponibilidade nem selecionou fonte alternativa.

A prova completa no navegador verificou **64 participantes × 6 combinações × 2 relações = 768 destinos**. Todas as leituras individuais têm o membro exato e SINGLE_GAME; os agregados têm dois membros e relação includes. Nenhum jogo posterior a W2 ganhou leitura individual. Comparações com calendário e seleção foram feitas pelos IDs/participantes originais. Os testes de relações continuam distinguindo other/archive/gap/incompatible.

Percurso interativo adicional pelo agente no navegador integrado: ARI–LAC W1 → escolha explícita LAC → defesa/passe → leitura individual → retorno preservado → agregado inclusivo. Individual: 38 jogadas, EPA permitido +0,237, sucesso permitido 21/38, frequência 38/69. Agregado: 69 jogadas, EPA permitido +0,217, sucesso 36/69, frequência 69/126; os membros mostram 38 e 31 jogadas. Depois: busca “Minnesota” em W2 → MIN–CHI → escolha MIN/ataque/corrida → leitura com EPA −0,160, 8/28 com EPA positivo e frequência 28/51. Dados são descrições do recorte, sem qualificação de desempenho ou previsão.

Automação de navegador adicional percorreu MIN, SF, LAC e MIA, ambas as semanas, ataque/defesa, geral/passe/corrida e agregado; reload, escolha explícita, voltar/avançar, busca/retorno, NE POST e BAL W3, documento nominal inexistente e catálogo indisponível. Os cenários de falha de rede usam interceptação de teste identificada; os documentos e percursos positivos usam dados reais.

## Inspeção visual e escopo

Preservados Archivo, Roboto Condensed, neutros, painéis e identidades cromáticas. Foram inspecionadas capturas reais de central 1440, confronto LAC 390, defesa SF 390, agregado MIN 320, lacuna BAL 320 e texto ampliado. A primeira inspeção de 320/200% mostrou o logo comprimindo o título; o ajuste local coloca a identidade em uma coluna até 360 px. A segunda rodada reexecutou os mesmos percursos e confirmou títulos íntegros e ausência de overflow. São 22 combinações de estado/largura/texto verificadas, com 12 capturas representativas; não se reivindica pesquisa de compreensão com pessoas.

[Central desktop](evidence/calendar-1440.png) · [Confronto mobile](evidence/matchup-390.png) · [Defesa mobile](evidence/individual-390.png) · [Agregado 320](evidence/inclusive-320.png) · [Lacuna 320](evidence/gap-320.png) · [Texto 200%](evidence/reading-320-text200.png).

Os quatro capacetes candidatos preservados têm máscara à direita. Não existe par frente a frente. O piloto agora verifica orientação dos dois originais e usa logos na falta do par; nenhum scaleX(-1), nova coleta ou alteração de inscrições. [Pendência visível](evidence/helmet-pending-logos-1440.png). Galeria e retratos associados aos atletas continuam candidatos locais sem aprovação de publicação. Não há retrato em estatística coletiva.

## Verificação e limitações

- 110 testes Python de laboratório/observações/materialização: passaram.
- 235 testes frontend em 23 arquivos: passaram; cinco expected-failure legados preservados sem alteração.
- Lint, journey:build, real:build, experience:build e build público: passaram.
- Gate de isolamento: src público, snapshots, contratos, schema, ETL, transporte, Java e arquivos históricos inalterados. Os hashes JS/CSS do build público são os mesmos da referência anterior aceita. Nenhum bundle privado foi versionado.
- CLI generate, validate, inspect; reader integral na cópia; HTTP integral; 1.552 arredondamentos; relações/destinos completos e 22 layouts no navegador: passaram.
- git diff --check: passou. Não foram repetidas suítes de banco/Java sem relação com esta alteração.

Os comandos finais de seleção → CLI generate → reconciliação foram ainda reproduzidos em uma raiz adicional nova de teste; produziram o mesmo bundleId semântico, as mesmas contagens e outra cópia com leitura independente. Essa raiz temporária é somente evidência adicional; os dois bundles da entrega permanecem nas raízes duráveis documentadas.

Tentativas de verificação corrigidas sem mudar contratos/gates: nome inicial do script http.py colidiu com a biblioteca padrão (renomeado verify_http.py); script de navegador inicialmente tratou SnapshotGame como Game hidratado (corrigiu o join com teams); lint detectou declaração duplicada na edição do piloto (removida, checks repetidos). Não houve erro de dados ou relaxamento de validação. Scripts finais não ocultam falhas nem substituem casos reais por fixtures.

Completude, cobertura esperada, modelo EPA e conhecimento temporal continuam UNKNOWN. O arquivo não certifica comparação/ranking, previsão, pregame, conhecimento histórico ou atualização até outubro. Não há aquisição, backfill, semanas posteriores, novas métricas, jogadores, banco, migrations, Supabase, Gemini, processo semanal, alterações de contratos públicos/snapshots ou conexão ao build público.

Verificação técnica concluída; **aceite humano pendente**. Servidor próprio PID **85128**, somente **127.0.0.1:18096**, mantido ativo. Servidores anteriores 18093/PID39598, 18094/PID55895 e 18095/PID64983 continuavam ativos e foram preservados. [Operação e reprodução](README.md). A lista de commits e o HEAD completo final são entregues no chat e conferíveis por git log/rev-parse; não se grava um hash autorreferente neste relatório.
