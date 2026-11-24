# Percurso integrado · relatório de 22/10/2026

Implementado e percorrido: calendário preservado → jogo identificado → relação conferida no documento →
observação real correta → retorno ao confronto e à seleção. O [README](README.md) reúne URL, rotas nominais,
capturas e comandos. Implementação no commit `2f7af1b`; commit documental seguinte contém esta prova.
O HEAD final é informado na entrega, sem hash autorreferente neste relatório.

## Fontes e identidades

[Preflight do calendário](calendar-preflight.json): schemaVersion 1, defaultSeason 2026, seasons [2026],
272 jogos, semanas 1–18, generatedAt `2026-09-22T05:13:34.372884Z`. Sem arquivo público de 2025.
Há 32 trios completos válidos nesta base; os números do parágrafo histórico do contrato público não
substituem os bytes efetivos. BAL–DAL W3 conserva gameday 2026-09-27 e trio nulo. O estado em outubro
é “resultado não disponível neste arquivo”, sem estado ao vivo, quarto/relógio ou placar derivado.
A seleção inicial usa `initialWeek` existente em UTC (semana 7 na prova), nunca W3 fixa.

`StaticNflDataClient` é instanciado explicitamente como `NflDataClient`. A entrada só usa publicação e
lista de jogos; não solicita homeMetrics, awayMetrics, análise pública antiga nem API Java. A configuração
local serve o public existente em /data sem copiar nem alterar arquivos. Production/alias permanecem iguais.

[Reader completo](preflight.json) e [reconciliação HTTP](http.json): principal e backup validados,
pin `sha256:2fae3be2b1ab7e5799287469ec29b9a98ff652a365ccafcb11b46c55d98ace8a`,
sessão `sha256:a0b4a5b4ffbac39ef3ea827c1c7b0b53a30156aa1a94214da3722630dd3d9e2c`.
São 48 DTOs, 42 com fonte, seis lacunas BAL W3. Catálogo efetivo: BAL/DAL REG2026 W1, W2, W1–2;
BAL REG2026 W3; NE POST2025 W19–22; ataque/defesa × geral/passe/corrida.
A entrada operacional usa o bundle completo pelo transporte aceito, nunca extrato/DTO salvo.
O startup não foi modificado: reader/adapter, catálogo e documentos congelados, GETs relativos,
marcador, sessão, Host/Origin exatos, IP e porta explícitos, no-store/nosniff e recusas originais.
As 16 contraprovas HTTP e todos os 48 documentos coincidiram exatamente com o reader.

## Relações e navegação

A [matriz](RELATIONS.md) foi gravada antes de implementar os vínculos. `relations.ts` confere
participante por igualdade literal de abreviação, temporada/fase, período solicitado, membro gameId,
semana/round, presença/includedGameIds e escopo. Resumo de catálogo não prova associação: os 48 documentos
validados são carregados na mesma sessão antes de anunciar disponibilidade. Não há aliases novos.
Ausência de membro vira outro recorte, jamais individual. Escopo/membro contraditório é incompatível.
Agregado com membro ausente explicita que não oferece estatísticas desse jogo.

Central conserva todos os jogos por padrão. O filtro opcional “Com recortes dos participantes” declara
que inclui outros períodos, temporadas e lacunas. Confronto mostra regiões para individual, inclusivo,
lacuna, outros recortes e outra temporada/fase, com período próprio antes do clique. IND sem observações
e GB–MIN sem leituras dos dois participantes continuam navegáveis. NE POST2025 exige seleção explícita;
nenhum calendário 2025 foi construído. Não há leitura padrão arbitrária do confronto.

A URL contém season/week/filter/game/entry/observation e estados opcionais details/composition.
Retorno é a seleção do calendário preservada nos mesmos parâmetros. Clique, recarga e voltar/avançar
foram exercitados. IDs inexistentes produzem ausência explícita; origem indisponível produz “relação não
conferida”, mesmo que uma observação nominal ainda possa ser explorada. URL de BAL–IND com DAL é bloqueada
como incompatível e não renderiza números. A troca BAL W2 → W1 → W1–2 refaz os rótulos individual → outro
recorte → inclusivo. Preferência anterior da entrada real não é lida, migrada ou escrita por esta entrada.
Não há DTO em URL/storage nem novo protocolo.

Calendário e arquivo têm estados/cache separados. Guarda de geração do calendário impede resposta de
2026 relabelada como 2025; AbortController e guarda de atividade descartam sessão antiga do arquivo.
Ao recarregar arquivo, a disponibilidade anterior deixa de ser anunciada. Falha de catálogo/sessão remove
leituras e oferece recuperação própria, mantendo calendário. Falha de calendário mantém o arquivo nominal
explorável com vínculo não conferido. Nenhuma fonte disponível mascara a falha da outra.

## Apresentação e limites

Mantidos cenário ardósia, Archivo/Roboto Condensed locais, faixas cromáticas dos times conhecidos,
logos/fallback por sigla, painel claro contínuo, listas compactas e controles explícitos. Não se importam
fixtures ou regras editoriais sintéticas. Times sem metadados visuais locais usam o fallback existente;
nome legível vem do cadastro do calendário, sem aquisição de imagens.

`Reading` e `presentObservation` continuam responsáveis pela observação individual e suas razões exatas.
Somente props opcionais foram acrescentadas: nomes dos membros vindos do calendário e exploração controlada
pela URL. Identidades técnicas continuam nos detalhes. `ObservationInspection` recebe controle opcional
apenas para a precisão; entradas anteriores sem props mantêm comportamento próprio. O adaptador numérico,
transporte e seleção temporal não mudaram. Na interface integrada, troca de recorte conserva foco e anuncia
a relação atualizada. O foco de mudança de página vai ao título, com skip link e retorno explícitos.

Completude, cobertura esperada, temporal e modelo EPA permanecem UNKNOWN. Integridade RECONCILED e
compatibilidade KNOWN não promovem essas garantias. Frações, precisão HALF_UP, denominadores, fontes
presentes vazias e ausentes conservam o contrato. Sem ranking, diferença entre times, soma de observações,
confiança, conclusão pregame, vencedor predito ou comparação de documentos. O arquivo retrospectivo não
comprova conhecimento anterior ao kickoff. Não há nova aprovação visual/editorial humana nem certificação
integral de acessibilidade.

## Prova e checks

[Chrome próprio](evidence/browser.json): fluxo por cliques, observação nominal em presença de preferência
anterior inválida, recarga com detalhes/composição, voltar/avançar e retorno à semana/filtro anteriores.
Os 48 DTOs reais foram percorridos e identificados por dtoId/observationId. EPA, sucesso e volume foram
conferidos com cálculo BigInt independente; limitações e UNKNOWN permaneceram acessíveis. Há 12 casos
registrados, incluindo todos os seis casos reais pedidos, troca de relação, IDs inexistentes, falhas
independentes, sessão 409, atraso de documentos e calendário atrasado após mudança de temporada.
Somente GETs locais e nenhum erro de página. Navegador de teste encerrado em finally.

24 medições: central/confronto/leitura × 1440/900/390/320 × texto 100%/200%.
scrollWidth coincide com viewport em todas. O excesso de 5 px encontrado em nome de time a 320/200%
foi corrigido por reflow, sem clipping ou redução de fonte. Detalhes e composição estão abertos na leitura
medida. Teclado: skip link em ordem real, foco visível, select sem perda de foco, Enter para composição;
também ensaiado landscape 900×390 com reduced motion. As capturas listadas no README mostram os estados.

[Logs](checks/): **205 testes frontend aprovados**, incluindo 26 novos e as cinco falhas esperadas legadas
preservadas byte a byte. Lint, journey:build, real:build, experience:build, build público e diff --check
passaram. Não houve suíte Java/ETL completa, pois esses componentes não mudaram. A validação Python foi o
reader completo necessário ao arquivo. Revisão React com a skill react-best-practices: efeitos separados,
Promise.all para documentos independentes, identidades/generation guardadas, cancelamento, controles
nativos, foco e imports sem fixtures. Frontend-design/UI/UX orientaram preservação visual e reflow.

[Isolamento próprio](isolation.json): bytes dos dois snapshots e bundle inalterados, cinco regressões
esperadas intactas, barreira do transporte intacta. Bundle público conserva JS SHA-256
`73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5` e CSS
`2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d`.
O gate lista explicitamente a extensão opcional de Inspection e o script novo nas áreas protegidas;
não altera gates históricos. Sem .env, remoto, banco, Docker, Gemini, aquisição, backfill, schema, writer,
aprovações, weekly workflow, merge, push, deploy ou alteração de Production.

Base de referência permanece c193bb8. Servidores anteriores 18086–18090 preservados.
Servidor próprio ativo: 127.0.0.1:18092, PID 27714. Iniciar/encerrar no README.
