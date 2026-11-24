# Contrato privado broadcast-matchup-w12-v1

Projeção 1.0.0; política broadcast-matchup-policy-1.0.0. Novo contrato e pin, sem mudar `broadcast-comparison-foundation-v1`, situational-v1 ou snapshots públicos. Autoriza retrospectiva nominal de 32 confrontos 2026 REG W1–2; não generaliza para outros jogos/arquivos/períodos.

## Coleção física

`index.json` canônico UTF-8 (chaves ordenadas, compact, newline, sem NaN) inventaria 32 gameIds, calendário/placar, origem/hash do schedule e `path`/`documentHash` de cada documento. `bundleId = SHA-256(index.json)`. `COMPLETED.json` contém versão, bundleId e os hashes de todos os outros 49 arquivos. A cópia versionada de índice/marker nesta pasta permite revisar a identidade, sem expor dados privados em public/data.

| Caminho | Conteúdo |
| --- | --- |
| index.json | Identidade/verificação dos 32 documentos, calendário e contagens |
| games/GAME_ID.json | Um confronto com duas produções, seis EPA, comparações/fatos e referências da semana |
| request.json | Pedido exato 2026 REG W1–2, retrospectivo e referência ofensiva da mesma semana |
| definitions.md | Definições originais situacionais 1.0.0 e EPA classified-scrimmage-v1 preservadas |
| policy.md | Política nova por operação |
| source-receipt.json | Identidade da leitura do piloto e inventário de seus arquivos; não transfere a autorização nominal do piloto |
| sources/situational/ | Cópia física integral do pacote pinado, PBP bruto e ledger |
| sources/observations/ | Cópia física das 588 observações e shared-source autocontido, com calendários embutidos |

Reader exige paths absolutos físicos, rejeita symlinks, arquivos/diretórios inesperados, versões, pins, identidades ou hashes incompatíveis. Roda os dois readers originais e rederiva o índice e todos os 32 documentos, comparando bytes exatos. Identidade do calendário é conferida contra PBP e observações; placar é trio completo válido ou trio ausente, sem preenchimento/derivação. Fontes antigas nunca são editadas.

Publicação usa estágio temporário irmão, validação completa e rename exclusivo. Destino existente é recusado; geração/reprodução exigem origem/destino disjuntos. Não existem dependências de /tmp nem de processos. `reproduce` usa somente fontes internas da cópia, preserva bytes/marker e não consulta banco. Recibos históricos são evidência de origem, sem obrigação de abrir os caminhos históricos. Recuperação não é fallback automático.

## Documento por jogo

`game` declara gameId/season/phase/weeks (uma semana), offenses em ordem visitante/casa, away/home. `calendar` conserva a associação e trio de placar da mesma linha do schedule, com hash. `productions` segue a mesma ordem, label “TIME com a bola”, defesa adversária e jogo explícitos. Defesa é contexto da mesma evidência, sem duplicação de amostra.

`metrics.third/redZone` preserva a observação situacional original, descriptor e permissão display. `thirdLong` aponta somente IDs de 7+ jardas, com estado próprio de denominador (zero não é taxa). Descriptor conserva definição/população/unidade, arquivo/coluna, período, IDs e contagens/estado/garantias.

`thirdAttempts`: cada tentativa incluída real game/play, ataque/defesa, semana, playId, yardsToGo original, faixa/tipo/conversão, sack/scramble e sourceOrder. Oito células `thirdDistanceByType` vêm dessas unidades reais; não são reconstruídas das marginais. Flags/exclusões/penalidades e distância desconhecida seguem definição original.

`redZoneCampaigns`: uma unidade game/fixed_drive, entrada e desfecho com evidências dos registros, cronologia por order_sequence. Várias entradas não multiplicam campanhas. Evidência terminal cobre TD, FG, FG perdido/bloqueado, turnover, TD adversário, downs, punt, fim de tempo/jogo e safety quando existentes; não se infere entrada de um TD. Unidades ambíguas não viram falha.

`epa`: três observações ofensivas originais por ataque e espelhos defensivos correspondentes; igualdade é a mesma amostra. População própria, sem filtro de terceira/red zone. Soma decimal, denominador finito, precisão e flags originais; eligibleUnitIds e finiteEpaUnitIds separados, contagens ausentes/não finitas conservadas. Não há referência EPA da liga. Modelo UNKNOWN.

`comparisons`: sideBySide e difference por família/fundamento, IDs e motivos; diferença racional exata A−B apenas quando permitida. `facts`: somente terceira geral, terceira longa e contagem/taxa red zone; editorialFact tem operação própria, evidência exata e comparação racional antes do arredondamento. Empate exato não vira vencedor; denominador inexistente não gera frase comparativa. Não exige três fatos.

`leagueReferences.third/redZone`: usa exclusivamente a semana do jogo. Inventário candidato dos 32 times validado, uma observação ofensiva/time, sem duplicar defesas. Cada ponto é razão inteira original; taxas inexistentes fora da distribuição e em teamsWithoutRate com motivo. PooledRate = soma dos numeradores/soma dos denominadores. Contagens visuais vêm dos arrays; participantesIncluded e participantsIndependentOfReference=false explicitam sobreposição.

Estados independentes: AVAILABLE (razão definida); NO_OPPORTUNITIES (fonte presente, 0/0, sem taxa); INSUFFICIENT (registros ambíguos/insuficientes, sem taxa); SOURCE_ABSENT (sem fonte, sem número substituto). Permissão individual é preservada mesmo se a comparação for recusada. Não se aplica mínimo universal de amostra. Ausência não muda jogo/semana/fundamento ou usa o piloto.

`temporalContext`: retrospectiva do jogo. `otherGamesContextAllowed=false` restringe a composição temporal com outros jogos, sem proibir a referência transversal da mesma semana (`referenceWeeks` explícito). W1 tem NOT_APPLICABLE para semanas regulares anteriores no recorte; W2 tem OUT_OF_SCOPE porque a página descreve somente aquele jogo. Nada disso prova conhecimento pré-kickoff. Completude, cobertura esperada, modelo e disponibilidade histórica UNKNOWN. Mercado usa somente campos existentes do schedule, origem/hash e captura/fornecedor desconhecidos; spread bruto sem atribuição e sem nomear fechamento/pré-jogo.

## URLs e calendário

`/?view=matchup-w12&game=2026_02_JAX_DEN` é direta e estável. `season` e `week` são opcionais; quando presentes devem coincidir exatamente. IDs desconhecidos/duplicados ou período incompatível são erros explícitos, sem substituição. Recarga e histórico usam BrowserRouter. Mudança de consulta cancela requisições e invalida estado por chave; uma resposta antiga nunca renderiza na seleção nova.

O calendário reutiliza Discovery, GameSearch, busca, filtros e semanas existentes com os 32 registros reconciliados, acrescentando destinos diretos. Não redesenha hub/página de time. `returnWeek`, `q`, `scope`, `filter`, `page` conservam o contexto do calendário; a semana da leitura continua sendo a do jogo, inclusive ao achar W1 em busca feita na W2. Links anterior/próximo não exigem seletores. Entradas piloto, percurso e explorador permanecem.

## Transporte próprio

Vite `vite.w12.config.ts`, root broadcast-journey com entry exclusiva reescrita antes da análise do HTML (`transformIndexHtml.order=pre`), somente 127.0.0.1:18104, strictPort, cors:false, envFile:false e envPrefix:[]. `NFL_W12_CONFIG` é configuração do operador com configVersion/path absoluto/expectedBundleId; não é VITE_* nem input do navegador.

Startup Python executa reader integral antes de disponibilizar; Node valida hashes/identidade de índice/documentos e congela bytes em memória. Falha de fonte mantém a fronteira 503, sem fallback. `GET /__matchup-w12/` entrega índice; `GET /__matchup-w12/GAME_ID` só entrega documentos do inventário validado. Corpo é byte exato do arquivo, sem envelope. Sem consulta por path/query ou releitura por requisição.

Host exato 127.0.0.1:18104; Origin ausente ou a mesma origem. Exige `X-Local-Matchup-W12: 1` e `X-Matchup-Collection: PIN`; versão de coleção divergente recebe 409. Cabeçalhos de autoridade/origem/marcadores/body duplicados são recusados; método, query, sufixo, corpo/Content-Length positivo ou Transfer-Encoding recebem 403; Expect é recusado (Node pode retornar 417 antes da aplicação). ID com sintaxe válida mas fora do inventário recebe 404. JSON no-store/nosniff e X-Matchup-Collection/X-Matchup-Document; cliente confere SHA-256 dos bytes com índice pinado e identidade esperada.

As fronteiras antigas são reutilizadas só nesta instância com sua própria autoridade 18104; servidores anteriores não foram alterados. Nenhum cliente/alias/build público importa a entrada experimental, nem VITE_* redireciona produção. Pacote privado fica fora de web-ui/public/data.
