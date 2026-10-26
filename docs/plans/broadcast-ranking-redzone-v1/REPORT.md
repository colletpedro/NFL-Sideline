# Classificação compacta e campanhas · relatório local

Entrega motivada por decisão direta do usuário: dois participantes na abertura, posições numéricas por taxa observada, referência completa expansível com movimento curto e ícones de desfecho. Não houve nova avaliação humana. Sem EPA de red zone, laboratório de quarterbacks ou alteração de dados.

## Regra e permissões

[PRESENTATION-RULE.md](PRESENTATION-RULE.md) documenta **broadcast-observed-rate-position-1.0.0**, extensão isolada que substitui a orientação de produto anterior de não numerar posições. A política antiga não é apresentada como certificadora de ranking. Nenhum contrato/pin/política anterior foi editado. A apresentação continua exigindo a permissão leagueReference concreta, seus observationIds e inventário validado da semana/família. Recusa não produz classificação substituta. Não concede qualidade, prognóstico, referência EPA ou distribuição agregada W1–2 ao time.

Ordenação exata decrescente; posição = 1 + quantidade de taxas estritamente maiores. BigInt compara produtos cruzados antes de arredondar. Empates equivalentes compartilham posição; sigla só ordena visualmente. Zero válido tem posição; 0/0, ausência e insuficiência não têm ponto, percentual ou posição.

Resumo segue visitante/casa do jogo, mantendo as colocações da referência completa. NE 21º, SEA 29º em terceiras W1; na red zone, NE 20º e SEA 30º (0/2 válido). TEN 1/1 compartilha a primeira colocação com outros ataques de taxa 100%, sem demonstrar estabilidade. Famílias têm universos de 32 e 31 taxas; ambas as semanas reais têm esses tamanhos, com razões/posições próprias. Não foi fabricada uma diferença de tamanho entre semanas.

Marcação distingue `data-ranking-scope=summary`, `full` e `without-rate`. O tamanho vem apenas dos pontos válidos originais. Os participantes reaparecem na lista completa sem criar observação, oportunidade ou soma adicional. Mesmas razões/posições/coordenadas nos dois escopos; taxa conjunta original intacta.

## Expansão

Botão acima da lista, com aria-expanded e aria-controls. Região fechada fica inert e aria-hidden. Grid passa de 0fr a 1fr em 220 ms e opacidade em 180 ms, sem animação por linha. Movimento reduzido elimina a transição. Não há rota, modal, consulta adicional ou seletor. Sem botão inferior: o foco permanece no controle previsível acima da expansão.

A inspeção registrou quadros intermediários: altura 0 → 83,7 → 247,6 → 477,2 → 711,1 → 1.026,4 → 1.349,2 → 1.371,8 px; opacidade 0 → 1. Topo do botão, resumo e scroll permaneceram constantes durante a abertura observada em desktop. A altura final permaneceu estável nos quadros posteriores, sem salto de finalização. Fechamento/reversões rápidas terminaram em altura zero, controle focado, inert=true. Após mudar largura durante abertura, altura final coincidiu com a altura natural (1.607,6 px no caso de 390 px). Com movimento reduzido, abertura/fechamento imediatos, transitionDuration=0s e altura igual ao conteúdo/zero.

Essas são verificações mecânicas do comportamento real no navegador, não uma conclusão humana sobre conforto de movimento. [Telemetria e matriz](checks/browser.json).

## Símbolos das campanhas

Um componente CampaignSymbol serve às marcas reais e à legenda dos desfechos presentes. Marca tem SVG, rótulo curto, número da campanha e W1/W2 no time. Nome acessível inclui perspectiva/time, ataque e defesa, semana, campanha e desfecho. Clique/Enter preservam as evidências e ID; seleção tem base azul e foco próprio. Alvo confortável, sem borda permanente de cartão. Uma marca por unidade, na ordem original.

| Desfecho | Símbolo e rótulo | Campanhas reais únicas |
| --- | --- | ---: |
| TOUCHDOWN | Bola · TD / Touchdown ofensivo | 124 |
| FIELD_GOAL | Traves e bola · FG / Field goal convertido | 52 |
| MISSED_FIELD_GOAL | Traves e X · FG perdido / perdido ou bloqueado | 2 |
| TURNOVER | Seta de retorno · Turnover / mudança de posse | 8 |
| OPPONENT_TOUCHDOWN | Bola e seta de retorno · TD adversário | 0 |
| DOWNS | Descidas e barra de parada · Descidas / perda por descidas | 15 |
| PUNT | Chute e trajetória · Punt | 0 |
| END_HALF_GAME | Relógio · Fim de tempo / tempo ou jogo | 7 |
| SAFETY | Escudo e dois pontos · Safety | 0 |

Os três desfechos ausentes não foram inseridos na experiência; seu mapeamento é coberto apenas por testes sintéticos. Fallback preserva o texto original com símbolo de informação, sem converter um desfecho desconhecido em TD/FG/turnover. Não há emoji ou imagem adquirida.

NE × SEA conserva 1/2 e 0/2, NYJ × TEN 2/3 e 1/1, ATL W1–2 0/0 sem taxa e adversários contra ATL 4/8. Numerador continua TD ofensivo, denominador campanhas elegíveis. Não se inferem entradas por TD nem se multiplicam campanhas por evidências repetidas.

## Refinamentos após inspeção

- Em 320 px, os rótulos do botão tinham alturas diferentes (61 e 52 px). Um texto de medição oculto da árvore acessível mantém a altura do rótulo maior: 70,8 px em ambos os estados observados, sem mover o resumo.
- “Sem posição” de ATL disputava largura com logo/sigla. A identidade sem posição passou a quebrar de maneira própria. Nova conferência sem cortes em 1440/390/320 e 200%.
- As campanhas do NYJ quebravam irregularmente como itens flex de larguras diferentes. Uma grade sem caixas alinha as marcas, preservando cada unidade e sua ordem. “Campanha” e seu número permanecem juntos para evitar número isolado na linha seguinte.
- Fontes, logo/identidades clicáveis, quatro exemplos de terceira, cores semânticas e hierarquia dos percentuais permanecem. Nenhuma fonte foi reduzida para caber.

## Provas de preservação e execução

- Oráculo independente em Python Fraction conta todas as razões estritamente maiores, sem importar o algoritmo frontend. Confere 32 jogos × duas famílias, inventários/razões conjuntas e os hashes dos 86 arquivos listados no pacote. [Recibo](checks/representation.json). Não houve geração de pacote nem reconciliação histórica refeita.
- **325 testes frontend, 33 arquivos, sem skips**: posições exatas/empates/valores de mesmo arredondamento/100%/saltos/zero/sem taxa/recusa, participantes em ordem visitante/casa e inventário completo, igualdade dos dois escopos, campanha/símbolo/legenda e fallback, IDs/ordem/desfechos de todos os jogos e ambas as perspectivas dos 32 times. As 208 campanhas únicas e as 787 tentativas foram preservadas. Cinco `it.fails` legados intactos. Testes sintéticos ficam fora da aplicação.
- **5 testes Python pertinentes**, sete casos não selecionados: reader integral real e estados de zero/ausência/componentes. Nenhum Python de processamento foi alterado.
- **158 requisições HTTP**: documentos dos 32 times e 32 jogos idênticos byte a byte ao pacote durável e à referência 18106; hashes/no-store e recusas de método, Host, Origin, marcador, pin, query/subpath, corpo e cabeçalhos duplicados. [Recibo](checks/http.json).
- TypeScript e **nove builds**: ranking-redzone, reading-polish, hub-team, journey, matchup, W12, real, experience e público. Público também sob variáveis VITE adversas, sem mudança do cliente. Lint passa sem erros; um aviso de Fast Refresh na entrada reading-polish/main.tsx já existe na base preservada e foi reconferido nela. Nenhum aviso novo foi mantido nem regra de lint relaxada. [Baseline do aviso](checks/reference-lint.log).
- JS público `73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5`; CSS `2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d`. Hashes originais, snapshots/cliente público intactos.
- Gate de escopo e hashes: só dois componentes compartilhados recebem branches opt-in; padrão antigo preservado. Backend/ETL/fontes/contratos/políticas/calculadores/configurações anteriores não foram alterados. Referência f144a68 limpa e nove listeners anteriores preservados. Nova entrada em 127.0.0.1:18107, strictPort, cinco readers coerentes com a porta, sem relaxar Host/Origin. `git diff --check`.

Os logs enumeram comandos e rodadas. Após os últimos acabamentos de quebra de legenda, a verificação final da entrada própria, TypeScript/lint/frontend e público foi registrada separadamente.

## Navegador e limites

NE × SEA, NYJ × TEN, ATL × PIT, GB × NYJ W2, time NYJ e time ATL em 1440/390/320. Compacto, aberto, recolhido, reversões rápidas, mudança de largura, redução de movimento e texto 200%. Teclado, foco, seleção e evidência original; retorno preserva consulta NYJ e W2. Fonte e viewport temporários restaurados. A inspeção não é nova sessão humana, teste de toque físico ou leitor de tela falado.

A lista completa permanece longa quando aberta, sem caixa de rolagem interna. Posição é descrição da amostra; não há ranking de qualidade, certificação, prognóstico ou independência do piloto. Garantias UNKNOWN permanecem. Não houve investigação humana de reconhecimento dos novos ícones. Desfechos inexistentes neste acervo têm cobertura sintética, sem alegar observação real. Sem EPA de red zone, nova população/denominador, endpoint por atleta, laboratório, aquisição, merge, push, deploy ou publicação.

Capturas em `captures/`: referência anterior, resumo compacto e campanhas desktop/mobile, classificação expandida, participante sem taxa e campanhas do time com semanas. Operação no README.

Capturas: [liga anterior](captures/before-league.png), [cartões anteriores](captures/before-redzone.png), [compacto desktop](captures/compact-desktop.png), [compacto 390](captures/compact-390.png), [expandido 390](captures/expanded-390.png), [campanhas 390](captures/redzone-390.png), [ATL sem posição](captures/atl-summary-390.png), [time NYJ](captures/team-nyj-390.png), [texto 200%/320](captures/compact-320-200.png). Capturas anteriores aos pequenos ajustes de alinhamento são complementadas pela matriz final sem cortes, registrada no recibo do navegador.

## Commits locais

Plano/regra anterior à implementação: `fedd982`. Implementação e oráculo independente necessários aos testes: `423f55d959a93c1fa5132072f5afea8950036d25`. Fechamento documental em commit posterior, informado no chat final e verificável por Git. Árvore conferida após o commit final. Servidor próprio mantido em 18107/PID 64656; referência 18106/PID 25458 preservada.
