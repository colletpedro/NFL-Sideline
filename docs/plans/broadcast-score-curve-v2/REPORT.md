# Refinamento do gráfico de pontuação

Base exata `0e9855da47e7e1a77acea860296eb3c8b7d87435`, preservada em 18110. Nova versão local em 18111, branch `codex/broadcast-score-curve-v2`.

## Composição e interação

A curva passou a ser desenhada pela biblioteca Recharts 3.10.1 já presente no projeto, com `monotoneX`. Os componentes cuidam da interpolação, escalas, áreas e coordenadas responsivas; não há um caminho de curva escrito manualmente. A referência técnica é a [API oficial de Area](https://recharts.github.io/en-US/api/Area/); a integração usa as APIs exportadas pela versão instalada.

O painel tem fundo ardósia profundo, linha clara e preenchimento dividido no zero pelas cores dos times. As identidades menores usam as logos originais coloridas, com o visitante acima e o mandante abaixo da curva (refinamento em [LOGO-AXES.md](LOGO-AXES.md)); a identidade principal da página, cores, fontes, rankings e métricas permanecem. O ponto de empate e os limites de vantagem são explícitos.

FG e TD têm ícones presos aos seus pontos e rótulos +3/+7/+8 conforme o momento real. Turnover tem ícone próprio e acento âmbar. Um marcador pode reunir TD e conversão consecutivos, preservando a regra anterior, ambos os relógios e os componentes exatos na auditoria. Selecionar por mouse, toque, foco ou Enter/Espaço apresenta o placar e o evento no painel junto ao gráfico. Uma área transparente de 44 × 44 px amplia o alvo do ícone.

A linha suaviza visualmente o caminho entre eventos, sem afirmar que pontos foram marcados continuamente. Os valores nos marcadores são os registrados. A interpolação monotônica evita picos artificiais entre valores adjacentes. Não é probabilidade, momentum ou EPA. A decisão de usar curva substitui somente a apresentação anterior em degraus nesta nova entrada.

A sequência escrita agora é um `details` recolhido inicialmente. Abrir/fechar não muda a curva nem os resultados. A auditoria mantém os eventos individuais de pontuação e turnovers em ordem de fonte, além das evidências de campanhas.

[Desktop atual](evidence/logo-axes/desktop-1440.png) · [Turnover na entrega inicial](evidence/turnover-1440.png) · [Mobile na entrega inicial](evidence/mobile-390.png) · [Texto a 200%](evidence/text200-320.png).

## Espaço no celular

A visão inicial cabe na largura disponível e mostra a partida inteira. Quando ícones colidiriam, uma marca numerada conserva os eventos e abre opções individuais no painel. Grupos que contêm turnover recebem também sua indicação. Não se elimina um evento por falta de espaço.

“Ampliar gráfico” oferece uma linha mais larga com rolagem horizontal dentro do gráfico; “Ajustar à tela” retorna ao conjunto. Os filtros por quarto/OT continuam disponíveis. O filtro só muda o gráfico e a sequência, mantendo taxas e classificação. O placar inicial de um quarto vem dos eventos anteriores e a escala de vantagem continua comum ao jogo inteiro.

## Turnovers de toda a partida

A cronologia anterior tinha pontuações e campanhas de red zone; isso não continha todos os turnovers do jogo. A projeção complementar lê os **262 registros** com `interception=1` ou `fumble_lost=1`, sem `play_deleted`, no PBP congelado dos mesmos 107 jogos.

Interceptação usa os times ofensivo/defensivo registrados. Fumble perdido usa o par `fumbled_n_team` / `fumble_recovery_n_team` que demonstra troca, em vez de assumir que `posteam` perdeu a bola. Isso é necessário em punts: no evento 1812 de CHI × CAR/W1, CHI chutava, mas CAR perdeu e CHI recuperou. Um segundo fumble recuperado pelo próprio time não cria outro turnover. Flags sem evidência suficiente bloqueiam a projeção; não se interpreta o texto para inventar a identidade.

O clock e os dois placares são copiados da linha correspondente. Turnover sem pontuação conserva o placar. No TD defensivo, a perda de posse é associada ao mesmo momento de pontuação, sem duplicar o TD ou somar pontos de novo. Um turnover já ligado a campanha de red zone também não é duplicado. Perda por descidas continua identificada separadamente na sequência; a definição dos turnovers adicionais é interceptação/fumble perdido.

Nenhuma das **1.418 alterações de pontuação**, taxas, somas EPA ou classificações anteriores foi alterada. Os 140 documentos W1–7 e o documento cronológico anterior foram conferidos byte a byte por HTTP, com seus pins originais. O complemento tem contrato e pin próprios e inclui a fonte integral copiada para reprodução offline.

[Reconciliação](checks/http-reconciliation.json): 107 jogos, 262 turnovers, 1.418 pontuações anteriores, **zero divergências**, **150 verificações HTTP** incluindo oito contraprovas de método/host/origem/pin/query/corpo. [Recuperação](checks/recovery.json): pacote, cópia física e regeneração a partir da cópia com 151 arquivos e bytes idênticos. Caminhos/pins/comandos no [README](README.md).

## Refinamentos e verificação

A primeira inspeção encontrou o estilo antigo de ícones escuros sendo herdado no novo fundo. O desenho interno foi reutilizado como paths SVG, com traço claro e tamanho próprio do gráfico. A legenda e o painel de evento receberam a mesma correção de contraste. Não foram criadas ou baixadas imagens novas.

Na visão mobile inicial os ícones tinham espaço, mas a partida exigia rolagem. O padrão passou a mostrar toda a curva; a ampliação tornou-se uma opção explícita. Agrupamento por distância em pixels preserva cada evento e oferece escolha individual. Com fonte raiz em 32 px a 320 px, o placar e a orientação de ampliação estouravam a largura; ambos passaram a quebrar naturalmente.

- **365 testes frontend em 37 arquivos** passaram com as fixtures configuradas. Após os últimos ajustes, **19 pertinentes** foram reconferidos. Testes novos percorrem todos os 107 jogos, os 262 turnovers, totais de pontos, fronteiras de quarto, agrupamento sem perda, TD defensivo, retorno de punt e sequência inicialmente fechada. Cinco falhas esperadas legadas preservadas. [Suíte](checks/frontend-full.log), [reconfirmação](checks/frontend-final-targeted.log).
- **20 testes Python selecionados** passaram, incluindo corrupção de identidade, relógio, placar e evidência de recuperação; os 262 eventos foram reconciliados independentemente às flags e linhas do PBP. Não foi alegada reexecução de toda a suíte ETL. [Log](checks/python.log).
- TypeScript e lint passaram, sem erros; permanece um aviso herdado de Fast Refresh em `reading-polish/main.tsx`. [TypeScript](checks/typescript.log), [lint](checks/lint.log).
- Nove builds experimentais passaram: curve, story, season, ranking-redzone, redzone-epa, w12, hub-team, reading-polish e matchup. O público normal e sob variáveis `VITE_*` adversas também passaram. Logs `checks/build-*.log`.
- [Doze combinações](evidence/layouts.json): 1440/390/320 px, fonte raiz 16/32 px, jogo inteiro/primeiro quarto. Sem overflow da página, curva com segmentos cúbicos válidos, gráfico inicial cabendo na largura e sequência recolhida. Foi teste de reflow de texto, não zoom nativo por atalho.
- [Interações](evidence/interactions.json): marcador por Enter, placar de turnover, grupo com dois eventos individualmente consultáveis, abrir/fechar a sequência, ampliação contida, OT começando 23 × 23, retorno de punt e TD defensivo. A marca e seu placar não dependem de abrir a sequência escrita.
- [Isolamento](checks/isolation.json): frontend público, snapshots, backend, migrations, contratos, regras de ranking, projetores e pins anteriores intactos. JS/CSS públicos têm os mesmos hashes. A worktree referência 18110 permanece limpa no HEAD original, e o servidor anterior foi preservado.
- Revisão React: hooks antes das saídas, nova visualização carregada sob demanda, importação da biblioteca apenas na nova camada, aborto de requisição, proteção contra resposta tardia, identidades por evento/jogo, estados derivados e alternativas textuais. A curva não usa animação de entrada; a expansão existente dos rankings e a preferência de movimento reduzido permanecem.

## Limites

Marcadores numerados podem reunir eventos afastados no relógio que ficaram próximos em pixels numa tela pequena. O painel identifica cada um; a ampliação e o recorte por quarto oferecem mais espaço. A linha conecta os marcadores, não estima estados intermediários do placar. Não foram acrescentadas todas as jogadas do jogo à sequência; ela reúne pontuação, turnovers e desfechos de red zone.

Se a fonte adicional falhar, a interface identifica que os turnovers completos não puderam ser carregados, preservando somente os dados identificados disponíveis. Completude, cobertura esperada, modelo EPA e disponibilidade histórica continuam UNKNOWN. Sem nova avaliação humana ou teste em celular físico; o histórico humano anterior permanece P01/N=1.

Servidor próprio **127.0.0.1:18111, PID 83042**, strictPort. Dependências locais existentes reutilizadas. Sem Gemini, banco, coleta externa, instalação, merge, push, deploy ou publicação.
