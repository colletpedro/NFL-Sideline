# Hub semanal e leitura direta · candidata ao aceite de uso

A nova versão elimina a confirmação intermediária. Ao abrir um confronto, exibe a observação individual única disponível; time, ataque/defesa, fundamento e período permanecem na tela e atualizam o documento ao clicar. Recortes agregados são explicitamente identificados. A busca oferece até quatro partidas desde uma letra, com logos, nomes, semana e data. A central mostra as 18 semanas e todos os jogos da semana em duelos horizontais com as cores dos participantes, sem arquivo recolhido.

## Antes e depois

| Antes | Agora |
|---|---|
| Selecionar ataque/passe → clicar Abrir leitura → abrir seletor novamente | Seletores sempre visíveis; uma troca atualiza números e gráficos no mesmo painel |
| Campo de busca só apresentava resultados após submissão | Quatro sugestões desde uma letra; ArrowDown/Up, Enter, Escape e clique |
| Três partidas destacadas; demais escondidas no arquivo | Todos os jogos da semana visíveis; semanas 1–18 selecionáveis diretamente |
| Identidade da observação duplicava uma abertura grande | Identidade compacta, mantendo time, lado, fundamento e período próximos dos números |

[Hub desktop](evidence/hub-1440.png) · [Hub mobile](evidence/hub-390.png) · [Busca desde uma letra](evidence/search-390.png) · [Leitura mobile](evidence/reading-390.png) · [Texto 200%](evidence/reading-320-text200.png).

## Fronteiras preservadas

`liveSelection.ts` resolve somente uma observação do time/lado/fundamento/período correspondente ao jogo. Mais de uma fonte é ambiguidade, não ordem de preferência. Um link nominal inexistente ou contraditório bloqueia números, sem fallback; uma seleção sem documento continua indisponível. O período é mantido nas trocas e nunca é substituído por outro agregado ou jogo. Os links nominais anteriores continuam válidos.

O painel usa o componente Reading e seu adaptador existentes, sem editar cálculos, formatação, originais ou garantias. Ao selecionar um controle, consulta a sessão já validada em memória. Uma captura CDP durante cinco trocas registrou zero novas requisições. Isso evita respostas atrasadas por seleção; a aquisição inicial continua independente do calendário, com estados de carregamento/erro e nova sessão somente pelo leitor operacional.

A busca usa apenas jogos existentes do calendário. Siglas literais como NE não se confundem com New York; prefixos como BA e letras isoladas encontram nomes/cidades/aliases. A semana selecionada tem precedência nas sugestões; isso não significa desempenho ou recomendação esportiva. O confronto sugerido recebe o time inequivocamente identificado pela busca, preservando o contexto de retorno.

Completude, cobertura esperada, modelo EPA e conhecimento temporal continuam UNKNOWN conforme os documentos. Defesa mantém valores permitidos ao ataque adversário. Ausência não vira zero. Não há comparação qualificada, previsão, estatística de jogador ou nova interpretação editorial.

## Refinamentos e verificação

O plano foi commitado antes da implementação. Foram aplicadas frontend-design e ui-ux-pro-max para composição/interação e react-best-practices para a revisão dos componentes. Nenhuma nova fonte, imagem, dependência ou paleta foi introduzida.

Na primeira inspeção, o estilo genérico dos botões anulava o fundo das semanas; o seletor foi isolado para distinguir a semana ativa. O Enter disparava a ação implícita do formulário em vez da sugestão destacada; o teclado agora trata essa escolha explicitamente. A barra móvel mudava de largura quando surgia um segundo botão de limpar; o campo conserva o cancelamento nativo durante a digitação e as sugestões usam a largura do formulário. O campo cresce com a fonte ampliada, sem altura fixa que corte os caracteres.

- **246 testes frontend em 24 arquivos** passaram; cinco expected-failure legados preservados. Onze casos novos verificam seleção imediata, período, participantes, ausência, ambiguidade, URLs nominais e sugestões de uma letra. Expectativas do teste antigo do arquivo recolhido foram atualizadas para exigir todos os jogos visíveis; os gates anteriores não foram editados.
- Lint e quatro builds passaram. Após os últimos ajustes locais, testes/lint/journey:build foram repetidos; os outros três builds e hashes públicos permanecem válidos, com todos os seus caminhos protegidos intactos.
- **588 documentos HTTP** comparados integralmente ao reader operacional e **dez recusas** passaram na nova porta. Não foi repetida a geração nem se anuncia nova auditoria dos Parquets: a materialização aceita não mudou.
- Navegador integrado: quatro sugestões desde uma letra, escolha por teclado e clique, Escape, passe/corrida/defesa/time/período, recarga, voltar/avançar, retorno preservando busca, lacuna BAL W3, ID inexistente e semana 18 sem busca. [Registro](evidence/browser.json).
- Nove medições de layout/texto em 1440, 390 e 320, incluindo texto 200%, não mostraram overflow horizontal. A captura final do campo em 320/200% registra altura 100 px, mantendo a mesma fonte. O viewport e a fonte temporários foram restaurados ao terminar.
- Isolamento: snapshots, public/src, build público, componente/formatador real, transporte, dados, contratos, ETL, Java, migrations e relatórios anteriores preservados. As 162 fontes preservadas e os dois bundles continuam com seus hashes originais. [Gate](checks/isolation.json).

O navegador foi operado pelas ferramentas integradas; não se confunde simulação de viewport com toque físico. Os testes de fonte ausente e URL inválida usam os estados indicados, sem substituir as observações reais por fixtures. Capturas são evidência técnica, não aprovação humana da experiência.

## Entrega e limites

Worktree: `/Users/pedrocollet/.codex/worktrees/broadcast-live-hub-v1/NFL Sideline`. Branch `codex/broadcast-live-hub-v1`, base `30140bee6af3eb02d00fb4b624399c1ff6e88f3d`. Servidor próprio em `127.0.0.1:18097`, PID **5687**; 18096 e seus arquivos preservados. [Inicialização, encerramento e reprodução](README.md).

Os dados ativos continuam 588 documentos (576 expansão W1–2 + 12 históricos/lacuna), com pin `sha256:05541d2703de6ad55e8858ebfbc17115a6d2747c01a2f73bad78d1eb7566876a`. A config depende do bundle preservado na worktree da expansão. Não arquive essa fonte enquanto ela for referenciada. As semanas 3–18 exibem calendário e somente os vínculos de arquivo realmente existentes, sem inventar leituras individuais.

Sem aquisição, novas métricas, coleta de imagens, banco, Gemini, Supabase, publicação, merge, push ou deploy. Aceite visual e de uso humano pendente. HEAD completo final é apresentado no chat, sem hash autorreferente neste arquivo.

## Correção posterior · 2026-10-23

As placas claras de LA/NYG/NYJ foram substituídas por marcas brancas transparentes sobre os painéis coloridos. A busca mantém a cor original sem placa. Esta correção modifica somente o tratamento visual do Logo compartilhado e o CSS local; [detalhes e capturas atuais](LOGO-CONTRAST.md). As capturas anteriores neste relatório preservam o estado anterior à correção.
