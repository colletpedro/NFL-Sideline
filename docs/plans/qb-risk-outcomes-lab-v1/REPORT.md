# Integração local — risco dos passes e interceptações sofridas

**Entrega funcional concluída em 05/11/2026, para aceite visual posterior.** O laboratório agora oferece duas perguntas na mesma composição, com seleção e URL contínuas. B2 foi integrado como outra leitura, sem substituir M3, sem adquirir dados NFL novos e sem alterar parâmetros, previsões científicas ou fontes.

[Abrir M3](http://127.0.0.1:18125/?view=risk-lab&season=2026&reading=passes) · [Abrir B2](http://127.0.0.1:18125/?view=risk-lab&season=2026&reading=interceptions) · [Operação/atualização](README.md) · [Capturas](CAPTURES.md) · [Reconciliação](RECONCILIATION.md).

## O que a pessoa encontra

| Leitura | Pergunta / alvo | Números do jogador |
| --- | --- | --- |
| Risco dos passes | Mais passes classificados como interceptáveis do que o contexto sugeria? Alvo FTN, modelo M3. | Classificados FTN, passes interceptáveis esperados, interceptações sofridas |
| Interceptações sofridas | Mais ou menos interceptações que a referência histórica esperava? Alvo INT observada, referência B2. | INT sofridas, INT esperadas, sofridas menos esperadas |

Os dois itens de navegação explicam as perguntas antes da metodologia. `reading=passes|interceptions` identifica a leitura; links antigos abrem M3. Jogador, período, escala e posição permanecem ao trocar. Voltar, avançar e recarregar foram conferidos. Seleção não escolhe outro jogador nem substitui semana sem cobertura. Ausência gera mensagem explícita e números indisponíveis, sem carregar valores da outra leitura.

M3 mantém o gráfico amplo, pontos sem nomes permanentes, hover/foco como prévia, seleção por clique/teclado/toque sintetizado, lista e resumo abaixo, seus três números, metodologia e evidências. Só a navegação e a explicação da existência da segunda pergunta mudaram nesse componente; modelo, probabilidades, agregações e geometria permanecem iguais.

B2 abre com a pergunta, a explicação das duas taxas de 2025, fonte FTN/PBP e indicação de comparação retrospectiva. Os eixos são **Interceptações esperadas × Interceptações sofridas**. A diagonal é identidade matemática, sem regressão ajustada. O detalhe decompõe a soma das probabilidades, conserva todos os passes e mostra os quatro cruzamentos com quantidades.

## Conta e conferência dos casos

B2 aplica 305/553 aos classificados como interceptáveis e 75/16.805 aos demais. Mesma taxa em cada classe para todos os jogadores, sem análise individual de dificuldade, pressão ou trajetória. As probabilidades vêm do pacote científico; o frontend não contém constantes dos exemplos.

| Caso real, acumulado W1–8 | Passes / jogos | INT sofridas | Esperadas | Contribuição classificados + demais |
| --- | --- | --- | --- | --- |
| Daniel Jones | 267 / 8 | 9 | 10,49 | 9,376130 + 1,115739 |
| Kirk Cousins | 280 / 8 | 5 | 5,08 | 3,860759 + 1,218387 |
| Sam Darnold | 209 / 7 | 9 | 5,31 | 4,412297 + 0,897054 |
| Jordan Love | 312 / 8 | 6 | 8,50 | 7,169982 + 1,334424 |
| Aaron Rodgers | 284 / 8 | 6 | 4,00 | 2,757685 + 1,245165 |
| Andy Dalton, suporte mínimo | 1 / 1 | 1 | 0,55 | 0,551537 + 0 |

Daniel tem 17 passes classificados como interceptáveis e 250 não classificados. A conta usa valores completos e só então arredonda: 9,38 e 1,12 são aproximações que não devem ser somadas para fabricar 10,49. A interface explica o esperado decimal. Valores positivos menores que 0,005 usam quatro casas, evitando mostrar uma expectativa pequena como zero; Mason Rudolph foi conferido com zero eventos, um passe e aproximadamente 0,0045 INT esperadas.

Rodgers tem cinco INT em passes não classificados como interceptáveis. A inspeção mostrou exatamente os cinco IDs, descrições e taxa de referência 0,446%; uma evidência foi aberta e restaurada por recarga. Cousins no mesmo cruzamento apresentou estado vazio explícito. [Recibos reais de casos](evidence/browser-real-cases.json), [evidência](evidence/browser-evidence.json), [vazios](evidence/browser-empty-states.json).

## Cobertura e fronteira de dados

| Fonte | Pacote | Modelo / SHA-256 | Cobertura |
| --- | --- | --- | --- |
| M3, fontes de 04/11 | `d3739e3d9103c48fda1c417a` | M3-2026-frozen-v2 / `38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6` | 121 jogos, 7.970 passes, W1–8 |
| B2, fontes de 05/11 | `404d23007ba98d989940f117` | XINT-FTN-B2-v1-fit2025 / `ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8` | 121 jogos, 7.970 passes, W1–8 |

Mesmas 7.970 chaves elegíveis, GSIS, FTN, INT e semana foram reconciliados antes de descrever o conjunto como comum. São 66 lançadores: 57 QBs e nove de outras posições; todos permanecem disponíveis. Nenhum jogo encerrado pendente na aquisição; 151 ainda sem placar final ficam fora. Não criamos uma interseção silenciosa. A comparação registra o ID M3 conferido; futuras diferenças ficam identificadas, e cada leitura conserva seus próprios numeradores e denominadores.

Os documentos B2 não foram copiados para snapshots públicos. A publicação local valida integridade científica/fontes/modelo/esquema/GSIS/cobertura, projeta campos explícitos de INT e gera pacote imutável em store próprio. Detalhes usam o ID do índice carregado. Respostas tardias de outra leitura, jogador ou versão não aparecem. A sessão guarda os índices até conferência explícita; refresh B2 não toca M3.

Atualização manual: aplicar modelo JSON fixo → validar → novo pacote/recibo de revisão → ativação atômica somente B2. Replay offline em store de QA reproduziu exatamente os 7.970 registros/probabilidades e agregados, sem alterar o pacote ativo da interface. Falha simulada na troca atômica preservou o ponteiro e o pacote anteriores, e a nova tentativa recuperou. [Recibo de atualização](evidence/update-replay.json).

## Revisão visual no navegador

Desktop 1440×1000, 390×844, 320×800 e texto ampliado a 200% foram inspecionados. O gráfico continua ocupando a largura útil, sem nomes, grupos ou linhas-guia permanentes. Nomes próximos e lista completa resolvem pontos densos sem alterar coordenadas nem somar jogadores. O clique/Enter de um ponto já focado manteve a posição da página; foco inicial do navegador pode rolar para tornar um controle visível, comportamento distinguido da seleção.

A primeira inspeção com texto 200% em 320 px revelou overflow no nome da segunda leitura. O ajuste usa largura mínima em rem para empilhar os dois itens nessa condição, sem novo seletor/tela. Resumos também permitem reflow entre rótulo e número. Depois do ajuste, `scrollWidth=305` em viewport de 320; texto de 32px, números e seleção preservados. A prévia passa para baixo dos eixos em telas pequenas/texto ampliado. A hierarquia dos alvos e a conta foram avaliadas visualmente, além da ausência de overflow.

Teclado: foco no ponto → seta para baixo → nome próximo → Enter selecionou Sam Darnold. Toque foi **sintetizado por PointerEvent(pointerType=touch) e clique**, identificado como emulação; selecionou Mason Rudolph e ofereceu 20 nomes próximos em lista rolável. Não foi teste em aparelho físico nem de gesto nativo: `Input.dispatchTouchEvent` não está disponível no navegador integrado. Não se declara esse caso como touch físico. [Recibo](evidence/browser-touch-emulated.json).

Carregamento foi capturado com latência simulada; falha com bloqueio apenas do índice B2 exibiu zero pontos e mensagem de recuperação, sem números antigos. Remover o bloqueio e tentar novamente restaurou jogador e versão. Overrides de rede, toque, tamanho e fonte foram removidos. O estado final foi recarregado, com fonte 16px e nenhum erro de console; permanecem dois avisos de evolução do React Router. O log histórico conserva um aviso de createRoot durante HMR da entrada, sem ocorrência na recarga final. [Estado final](evidence/browser-final.json).

## Verificação e preservação

| Fronteira | Resultado / evidência |
| --- | --- |
| Fonte científica → apresentação | Hashes, probabilidade por passe e agregados validados; M3/B2 científicos intactos |
| Apresentação → HTTP | 66 respostas de jogador idênticas em bytes aos pacotes; métodos/origens/rotas indevidas recusados |
| HTTP → interface | Casos reais conferidos; 1.372 pontos em 36 visões comparados aos artefatos e à projeção da diagonal |
| Conta por jogador/período | 594 combinações B2 renderizadas com contribuições, soma, suporte e números; ausências incluídas |
| Navegação / concorrência | Legado, nova URL, troca, histórico, recarga, ausência, cobertura divergente, respostas tardias e versão misturada testados |
| Suíte completa | 415 frontend passaram, nenhum pulado; expected failures legados preservados |
| Python | Seis de publicação + 33 B2 científicos + 59 M3/legados passaram, em processos separados |
| TypeScript / lint | TypeScript passou; lint sem erros, um warning preexistente em reading-polish/main.tsx |
| Builds | Público idêntico em bytes à referência; local separado com 276 GETs, conferido no navegador |
| Checkouts/fontes/servidores | Hashes e HEAD/status originais preservados; servidor 18124 continua com o mesmo listener |

[HTTP](evidence/http.json), [reconciliação final](evidence/reconciliation-final.json), [build público](evidence/public-build-isolation.json), [preservação](evidence/preservation-final.json), [logs completos](checks/frontend.log).

## Limites que continuam visíveis

A classificação FTN é posterior à jogada e pode conhecer o desfecho; não há evidência de anotação cega. B2 não é previsão pré-snap ou antes do lançamento. O residual não identifica sorte, culpa, inteligência ou qualidade de decisão. Pouco suporte/zero eventos não produzem intervalos de habilidade.

A metodologia mantém o problema de calibração em 2025: 75 INT observadas contra aproximadamente 52,92 esperadas entre passes não classificados como interceptáveis, apesar de total global próximo. Não houve recalibração ou novo treinamento. Dados podem ser revisados. A cobertura é W1–8, não a temporada inteira; novas atualizações são manuais, sem espera obrigatória por semanas futuras.

Esta entrega está pronta para uso local e revisão visual do usuário. Não promove resultados a produção nem autoriza publicação externa.
