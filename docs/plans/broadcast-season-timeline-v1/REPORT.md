# Classificação da temporada e timeline do placar

Implementação local sobre `8f05138502f51bd80cf8299a687d8dfdeb32c50a`, na branch `codex/broadcast-season-timeline-v1`. Referência W1–7 preservada em 18109; nova entrada própria em 18110. Sem merge, push, deploy ou publicação.

## Resultado

| Pedido | Entrega |
| --- | --- |
| Classificação da temporada como padrão | Acumulado retrospectivo W1–7, usando as mesmas razões, componentes e elegibilidade dos times já reconciliados. |
| Troca para a semana do jogo | Switch “Somente Wn”, sincronizado nos dois blocos, com `rank=week` na URL. Não muda as taxas daquele confronto. |
| Campanhas numa timeline dos dois lados | Eventos em ordem comum, time visitante à esquerda e mandante à direita, com ícone completo, relógio, placar e indicação de red zone. |
| Curva da pontuação | Degraus da vantagem real visitante − mandante, início 0 × 0, zero de empate, pontuação ofensiva/defensiva/special teams e filtros por quarto/OT. |
| Clareza sobre cada evento | Seleção por clique/Enter destaca a posição na curva; TD + extra e TD + dois preservam seus componentes e relógios. Tabela individual e evidências permanecem expansíveis. |

A curva considera todos os pontos do jogo, incluindo os marcados fora da red zone. Ela acompanha o desfecho das campanhas sem transformar turnover em pontuação nem representar probabilidade, qualidade ou EPA. As taxas de red zone e o EPA de jogadas com início nas 20 continuam com suas definições originais.

[Curva desktop](evidence/timeline-1440.png) · [Mobile](evidence/timeline-390.png) · [Eventos mobile](evidence/events-390.png) · [Texto a 200%](evidence/timeline-320-text200.png) · [Classificação](evidence/ranking-1440.png).

## Fonte e reconciliação

O pacote complementar contém uma cópia física integral da coleção W1–7 e uma nova projeção `story.json`. Nada na coleção anterior foi recalculado ou sobrescrito. As mesmas regras de população e os mesmos IDs de unidades sustentam os valores acumulados. O novo leitor verifica hashes e refaz a projeção a partir da fonte congelada antes de aceitar o pacote.

- **107 cronologias**, todas AVAILABLE neste pacote.
- **1.418 transições de pontuação**: comparadas independentemente às mudanças dos dois placares pós-evento no PBP; todos os resultados finais coincidem com o calendário.
- **723 campanhas de red zone**: IDs originais, evento terminal, relógio e placar conferidos nas linhas-fonte.
- **32 candidatos da temporada**: red zone com 32 taxas; terceiras com 30. MIN/W3 e CHI/W7 permanecem inconsistentes e seus acumulados de terceira não recebem taxa/posição. Os jogos e demais métricas desses times continuam disponíveis.
- Acumulado válido de terceiras: **1.022/2.538 (40,3%)**, somente nos 30 times autorizados. Red zone: **422/723 (58,4%)**, nos 32 times. As taxas conjuntas são pelas somas.
- Na referência semanal W7, só entram os 28 participantes: 27 com taxa em cada família; CHI é insuficiente em terceiras e KC não tem oportunidades de red zone. Folgas não viram zeros.

[Reconciliação e HTTP](checks/reconciliation-http.json) · [Regras detalhadas](RULES.md).

O complemento tem pin `sha256:93b6cad3ea3a1db822c16e4bfdadf70f28122e2dd60002708d44745776129624`; a fonte mantém `sha256:77af196874e984bfa85a270da8733073f97836e959b6dd3d2cd2ec8a98bc7a0c`. Pacote, cópia física e regeneração a partir da cópia têm **149 arquivos byte a byte idênticos**. [Recuperação](checks/recovery.json); caminhos e comandos no [README](README.md).

## Casos que mudam a interpretação

Em DAL × PHI, FG de DAL gera 3 × 0 (+3); TD de PHI gera 3 × 6 (−3); extra gera 3 × 7 (−4). A linha visual pode agrupar TD + extra como +7, mas a curva e a tabela usam as duas alterações reais. O jogo também demonstra TD + conversão de dois, +6 e +2. O primeiro quarto termina 10 × 7 e seu filtro não modifica o resumo do jogo.

BAL × ATL/W5 começa a prorrogação em 23 × 23 e termina 30 × 23. A reconstrução usa quarto + segundos restantes, evitando o reinício do relógio em OT. Safety de LV/W2 vale +2 para LV. Retorno defensivo na tentativa de extra de CAR/W7 vale +2 para TB, separado do TD de CAR. Turnover de NE/W7 conserva 7 × 13, sem salto na curva. Esses caminhos foram verificados no navegador, além dos testes sobre toda a coleção.

[Interações e casos especiais](evidence/interactions.json). As regras também cobrem evento a 0:00 na fronteira de quartos: fica no quarto da fonte e integra o placar inicial do seguinte, sem duplicação.

## Refinamento no navegador

A primeira composição revelou três pontos a corrigir: o rótulo de zero cobria o trecho inicial da curva; o eixo por flex distribuía os quartos sem respeitar sua posição temporal; os rótulos extremos ficavam apertados no celular. O zero ganhou uma margem própria; os quartos passaram a posições temporais reais; em telas estreitas a visão integral conserva os quatro quartos e dispensa os extremos redundantes.

Com fonte raiz de 32 px em 320 px, a margem e as legendas da curva foram refinadas para manter quatro rótulos separados. As linhas de momentos passam de duas colunas para alinhamento alternado apenas quando o espaço de leitura é insuficiente, mantendo o nome do time e o relógio explícitos. O ranking mantém a expansão existente e a preferência de movimento reduzido.

A troca de classificação não refaz a requisição do confronto nem transfere o foco para o título. A posição do controle medida antes/depois ficou em 537,2/536,5 px no cenário desktop; mudanças de altura do conteúdo anterior são compensadas pela ancoragem do navegador. `rank=week` sobrevive à recarga, ida ao time e retorno. Uma URL com `rank` duplicado produz estado de erro, sem gráfico substituto.

Foram conferidos 1440, 390 e 320 px com fonte raiz 16 e 32 px (**seis combinações**), sem overflow horizontal da página. A tabela de auditoria tem rolagem própria. O teste é de reflow de texto, não uma alegação de zoom nativo por atalho. Seleção de eventos por Enter mostrou foco de 3 px e atualizou a leitura; switch por Espaço funcionou. Movimento reduzido foi conferido e restaurado. Nenhum erro de console na inspeção final.

[Layout](evidence/layout.json) · [Interações](evidence/interactions.json). As alterações temporárias de viewport, fonte e emulação de movimento foram restauradas; a aba final permanece na versão entregue.

## Verificação técnica

- **38 testes Python selecionados**, incluindo 13 novos de cronologia/referência e a suíte da integração W1–7. [Log](checks/python-final.log). Não foi alegada reexecução de toda a suíte ETL nesta entrega.
- **357 testes frontend** em 36 arquivos, com as fixtures locais configuradas. Os novos testes renderizam os 107 confrontos, verificam os dois universos de classificação, transições de quarto, eventos especiais, ausência, alteração do pacote e URL ambígua. Cinco falhas esperadas legadas intactas. [Log](checks/frontend-full.log).
- TypeScript das entradas season e node passou. Lint sem erros, com um aviso herdado de Fast Refresh em `reading-polish/main.tsx`. [TypeScript](checks/typescript.log), [lint](checks/lint.log).
- Oito builds experimentais passaram: story, season, ranking-redzone, redzone-epa, w12, hub-team, reading-polish e matchup. Build público normal e sob variáveis `VITE_*` adversas também passaram. Os logs `checks/build-*.log` registram os dez comandos.
- **152 verificações HTTP**: complemento com bytes/pin exatos; 140 documentos anteriores (índice, 107 jogos e 32 times) byte a byte; 11 contraprovas de método, host, origem, corpo, caminho, query e pin. A execução foi repetida após reiniciar com a fonte contida no novo pacote.
- Isolamento: snapshots, frontend público, runtime de produção, backend, migrations, Spec, contratos e projetores anteriores intactos. JS público `73f18e…59ad5`; CSS público `2b4ae1…4d41d`, idênticos à referência mesmo no build adverso. [Prova completa](checks/isolation.json).
- Revisão dos componentes: hooks antes das saídas condicionais, identidades estáveis por jogo/evento, efeito com aborto e proteção de resposta tardia, contexto optativo para preservar entradas anteriores, texto equivalente aos SVGs e controle por teclado.

## Limites e operação

O ranking é descritivo do acumulado observado até W7, não classificação ajustada ou informação disponível antes de jogos antigos. Completude, cobertura esperada, modelo EPA e conhecimento temporal continuam UNKNOWN. A reconciliação é com os dados disponíveis, não certificação de completude externa.

A lista cronológica mostra pontuação e desfechos de campanhas de red zone; não pretende listar cada snap do jogo. O gráfico usa tempo proporcional; as linhas de eventos são ordenadas, sem fingir duração proporcional das campanhas. O relógio é o observado no evento terminal, não uma estimativa do momento da entrada nas 20. A escala é comum ao jogo inteiro, inclusive em quartos com pequenas vantagens. As páginas de time não unem cronologias de partidas diferentes.

Sem novos modelos, Gemini, coleta externa, imagens, banco, alterações do produto publicado ou pesquisa humana. A avaliação visual desta entrega e toque em aparelho físico ficam para o usuário. O histórico humano anterior permanece P01/N=1, sem nova reconfirmação do EPA.

Servidor próprio **18110 / PID 80609**, loopback e strictPort, com configuração explícita e pacote durável autossuficiente. Referência 18109 e demais versões preservadas. Inicialização e encerramento direcionado no [README](README.md).
