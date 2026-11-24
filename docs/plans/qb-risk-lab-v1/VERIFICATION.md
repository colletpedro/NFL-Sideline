# Verificação executada · 04/11/2026

## Dados e atualização

**59 testes Python passaram:**12 novos e 47 das pesquisas v1/v2. Fixtures pequenas, sem downloads: chaves duplicadas/nulas, alvo ausente/ inválido, passer ausente, semana parcial, jogo truncado, placar/identidade contraditórios, penalidade com tentativa mantida, exclusões, OT sob a mesma população, GSIS em várias equipes, posição desconhecida, zero eventos/denominador, soma de probabilidades e unidade/sinal por 100. Ativação: replay sem mudanças preserva bytes do pacote; revisão altera pacote e lista o rótulo; corrupção/falha de aquisição/falha no swap preservam o último ponteiro válido. SHA do modelo congelado conferido; não há ajuste no fluxo.

A fonte bruta real foi reconciliada por SQLite independente, sem reler uma tabela agregada gerada pelo mesmo filtro. Todas as 7.970 chaves/GSIS/rótulos/INT/semanas coincidiram. Por jogador e globalmente, somas concordam dentro de 1 e-9. [Recibo completo](evidence/reconciliation.json).

## Frontend

Suite completa: **311 testes passaram,68 skips preexistentes** (39 arquivos passaram,2 arquivos pulados). Os cinco casos `it.fails` legados não foram editados nem transformados em skips. Há 9 testes novos: contrato numérico, ausência/duplicidade, zero suporte, URL inválida/parâmetros repetidos, período, identidade, back/forward, carregamento, erro/retry, resposta tardia de outro jogador, evidência depois da primeira página e cruzamento vazio. A suite afetada foi repetida após os últimos ajustes.

Lint: 0 erros,1 warning preexistente em `reading-polish/main.tsx`. TypeScript da experiência e build separado passaram. O build público normal também passou. Foi usada a revisão `vercel:react-best-practices`:estado derivado de URL, carregamento em paralelo apenas quando independente, detalhe vinculado ao pacote, abort e chave/flag de validade para recusar respostas antigas, lazy loading do laboratório e ausência de novas bibliotecas de gráficos no runtime.

O componente anterior só ganhou uma prop opt-in `labEnabled`, padrão false, e um link adicional quando habilitada. A referência anterior permanece. Sua navegação móvel foi conferida para que a regra legada de esconder o último link não esconda o laboratório.

## Interface versus artefatos

Leitura do DOM real da visão inicial: 33 QBs com 100+passes; todos reconciliados por GSIS com o pacote. Observados, passes e jogos exatos;esperado, diferença e diferença/100 dentro do arredondamento de 0,005. [Valores lidos no navegador](evidence/browser-rows.json),[recibo da comparação](evidence/browser-reconciliation.json).

Daniel Jones W8:28 passes,2 rótulos,1,0343 esperado e 2 INT. O cruzamento “não interceptável e interceptado” contém uma jogada, ID `2026_08_IND_JAX:2125`, Q2/0:25,1ª para 10,17 jardas até a endzone adversária, diferencial pré−21, modelo 2,6%. A descrição PBP e as duas classificações estão visíveis, separadas. Enter abre a evidência;reload mantém o estado;voltar fecha e avançar reabre, com período/cruzamento preservados na URL.

## Inspeção visual e acessibilidade

Navegador real, sem screenshots do site usadas como gráficos científicos. Desktop 1440 × 1000 e larguras 390/320, com detalhe/evidência abertos. Medida do documento: 390→375 px úteis/375 scroll;320→305 px úteis/305 scroll. Texto a 200% em 320:heading 64 px,305 px úteis/305 scroll. Sem corte horizontal nesses estados. [Recibo do layout](evidence/browser-layout.json).

Foco viaTab: link “Entender o cálculo”,`:focus-visible` verdadeiro, outline 3 pxRGB(215,245,107). Enter operou a evidência nativa `<summary>`. Números não dependem só da cor;há rótulos observados/esperados, diferença e volume. A experiência mantém nomes, logos e links de times. Não houve auditoria exaustiva com leitor de tela;capturas e checks não a substituem.

Carregamento e falha foram inspecionados pausando/falhando somente o fetch do índice na ferramenta de desenvolvimento do navegador. O app mostrou estado explícito, sem números inventados, e recuperou pelo botão. Interceptação de rede, tamanho de texto e emulação temporária foram removidos ao terminar. Testes offline também exercitam os estados e respostas tardias.

Capturas:

- [Abertura desktop](captures/overview-desktop.png) e [comparação desktop](captures/comparison-desktop.png).
- [Evidência390px](captures/evidence-390.png),[320px](captures/evidence-320.png),[texto200%](captures/text-200-320.png).
- [Foco de teclado](captures/keyboard-focus.png),[carregamento](captures/loading-desktop.png),[falha](captures/failure-desktop.png).
- [Hub com entrada](captures/hub-with-lab-link.png) e [seleção móvel](captures/overview-390.png).

## Build, isolation e recuperação

O preview compilado foi aberto no navegador: detalheMatthewStafford e páginaLosAngelesRams carregaram sem execução Python no servidor. **209 endpoints GET** conferidos por HTTP: corpos e headers iguais ao mapa congelado;Host/Origin estrangeiros recusados. [Recibo](evidence/built-http.json).

Os cinco arquivos do build público normal coincidem em bytes com o checkout aprovado, incluindoJS `73f18e…` eCSS `2b4ae1…`. Diretórios `web-ui/public`,`web-ui/src`, contratos, ETL, backend, schemas e pesquisa/documentos v1/v2 têm diff vazio. Checkouts aprovado e v2 continuam limpos nos HEADs previstos. [Isolamento](evidence/isolation.json).

Reprodução offline em destino novo: mesmos 70 arquivos do pacote em bytes, modelo pinado, SQL e fontes conferidos. Recibos de execução/diretórios/timestamps não são anunciados como byte-idênticos. [Reprodução](evidence/reproduction.json). Arquivo de recuperação 114.762.457 bytes, SHA em [evidence/recovery.json](evidence/recovery.json),365 membros conferidos, incluindo fontes, wheels, modelo e build. O ambiente foi reconstruído sem rede;wheels são específicos deste Python/macOS/arquitetura.

Nenhum servidor anterior foi encerrado. O preview temporário 18122 foi usado somente nesta verificação e encerrado de forma direcionada;18121 permanece para revisão. Não houve merge, push, deploy, publicação, acesso a segredos, banco ou serviços pagos.
