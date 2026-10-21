# NFL Sideline — Broadcast experience v1

Entrega local de 21/10/2026. [Abrir a central](http://127.0.0.1:18086/?round=7) · [Dallas × New England](http://127.0.0.1:18086/confronto/dallas-new-england?round=7).

Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/broadcast-experience-v1/NFL Sideline`. Branch `codex/broadcast-experience-v1`, base exata `f174af8d3bdca4f72f7b97d9eebb1cbb3889ecf0`. Código em `1e5767f` + acabamento em `4162eed`; o commit documental seguinte contém esta entrega. Árvore final e commits podem ser conferidos com `git status --short` e `git log -3 --oneline`.

## A experiência

A [proposta de composição](PLAN.md) foi registrada antes da implementação. Foram lidos o relatório/código do piloto, o estudo e a análise do orquestrador, e abertas visualmente as 12 referências e as três capturas obrigatórias do piloto. A [referência 03](evidence/reference-03.png) foi copiada somente para a evidência; nenhuma captura integra a interface.

O piloto virou três densidades da mesma linguagem: abertura editorial ampla; mesa de análise contínua; linhas compactas de outros duelos. O limite de 520 px e o molde do laboratório não foram transportados. Logos, cor e placar abrem a leitura; a manchete se conecta ao painel claro, com uma coluna ardósia de produção ofensiva. A mesa mantém essa identidade junto dos gráficos, sem empilhar o cartaz sobre um dashboard anterior.

O cenário usa #18232B/#24323C, cabeçalhos #2B414E/#3E5360 e painel #D6E1E6/#C3CED7. Dallas conserva azul/navy e Patriots vermelho intenso. O roxo de Baltimore generaliza a família sem misturar cores entre participantes. Lima fica na assinatura, seleção e foco. As marcas locais mantêm proporções e cores originais.

Archivo local faz títulos, nomes, contexto e interface, com pesos distintos; Roboto Condensed fica nos fatos/valores curtos. Explicações usam caixa normal. Não há `scaleX` nem condensação artificial. [CDP de fontes renderizadas](evidence/rendered-fonts.json) confirmou Archivo customizada — Regular no texto, instâncias de peso nos nomes/marca — e RobotoCondensed-SemiBold nos valores. Licenças e arquivos originais continuam em `web-ui/local-editorial/matchup/assets/`.

## Conteúdo e comportamento

[fixtures.ts](../../../web-ui/broadcast-experience/fixtures.ts) é a origem única dos três cenários, nas rodadas fictícias 6–8. Uma partida por rodada permite explorar três duelos usando os três escudos disponíveis, sem marcar uma equipe duas vezes na mesma rodada. É uma seleção demonstrativa, não um calendário completo nem a temporada real de 2026.

Contagens por metade e fundamento geram totais, taxas, médias e fatos. Dallas 27 × 24 NE, 312 jardas de passe e 7/13 em terceiras descidas reconciliam. O sucesso de Dallas é 32/64 = 50,0%; não foi herdado de uma taxa avulsa. Red zone de Baltimore no duelo da rodada 6 permanece “Não disponível”. As situações de jogo identificam que abrangem todos os fundamentos, mesmo quando o gráfico está filtrado.

A navegação abre os três duelos, volta à rodada de origem e permite recarga/destino direto. `round`, `period`, `play` e `details` estão na URL. Títulos, amostras, valores, gráficos e tabela respondem à mesma seleção. Há saída para confrontos desconhecidos. O aviso “Demonstração · dados simulados” permanece no cabeçalho fixado entre as páginas. [Registro funcional](evidence/browser-checks.json).

As duas visualizações principais respondem a perguntas complementares: EPA por jogada em barras assinadas (−0,20 a +0,40, zero explícito) e sucesso dentro da amostra (0–100%, contagem e complemento). São geometrias CSS simples, sem perspectiva ou biblioteca adicional. Identificadores/valores ficam visíveis; detalhes oferecem tabela equivalente. A nota de defesa identifica jardas **permitidas** ao adversário. Na central, uma terceira leitura mostra passe/corrida em escala comum de 450 jardas.

## Refinamento real no navegador

| Rodada | Problema observado e correção | Evidência |
| --- | --- | --- |
| 1 · composição | Placar dominava os logos. Aumentadas ocupação óptica, área de identidade e presença dos nomes, mantendo a conexão com o painel. | [Antes](evidence/round1-home-before.png), [depois](evidence/round1-home-after.png); mesa [antes](evidence/round1-matchup-before.png), [depois](evidence/round1-matchup-after.png) |
| 2 · tipo/cor | Legendas pequenas e corrida escurecida apesar de ser descrita como trecho claro. Ampliadas legendas/valores, refinados pesos e diferenciados passe/corrida por luminosidade real. | [Home](evidence/round2-home-after.png), [mesa](evidence/round2-matchup-after.png) |
| 3 · mobile/interação | O min-content do logo deslocava NE; o arquivo quebrava em colunas estreitas. Corrigidas identidades e linhas. Texto 200% revelou overflow no botão/fatos; a composição passou a refluir por conteúdo. | Mobile [antes](evidence/round3-mobile-before.png), [depois](evidence/round3-mobile-after.png); texto 200% [antes](evidence/text200-mobile-before.png), [depois](evidence/text200-mobile-after.png) |

O acabamento seguinte reforçou contraste de legendas, contorno dos controles e alvos de 44 px. Comparações de contraste: tinta/painel ≥10:1; texto secundário no extremo claro mais escuro ≥4,82:1; séries azul/vermelha contra o complemento ≥3,22:1. As capturas finais abaixo incorporam esse acabamento.

## Capturas finais e verificação

| Viewport CSS | Central completa | Mesa completa |
| --- | --- | --- |
| 1440 | [Home](evidence/home-1440.png) | [Confronto](evidence/matchup-1440.png) |
| 1024 | [Home](evidence/home-1024.png) | [Confronto](evidence/matchup-1024.png) |
| 390 | [Home](evidence/home-390.png) | [Confronto](evidence/matchup-390.png) |
| 320 | [Home](evidence/home-320.png) | [Confronto](evidence/matchup-320.png) |

Inspeção no navegador integrado, DPR 1 e viewports via CDP. As capturas finais usam `Page.captureScreenshot` com largura/altura explícitas; alguns registros intermediários da API de screenshot excluem 15 px de scrollbar. [Dimensões e hashes dos arquivos](evidence/capture-files.json).

- Teclado: skip link focou `main`; Tab revelou foco de 3 px; Espaço mudou fundamento; Enter expandiu detalhes. [Captura do foco](evidence/keyboard-focus.png).
- Zoom: ampliação visual real de 200% via `Emulation.setPageScaleFactor`, confirmada por `visualViewport.scale = 2`. [Captura](evidence/zoom200.png). O atalho de zoom do app não mudou a escala nesta sessão. Separadamente, fonte raiz de 16→32 px verificou reflow de texto em desktop/mobile; [mesa ampliada](evidence/text200-matchup.png). Não se alega que a alteração CSS, sozinha, seja zoom nativo.
- Nomes longos, valor negativo e ausência: [320 px, segundo tempo/corrida, detalhes abertos](evidence/negative-missing-320.png). Sem rolagem horizontal da página nos viewports normais e na contraprova de texto 200%; tabelas/gráfico podem ter rolagem própria quando ampliados.
- Reduced motion confirmado: transição `0s`. Recursos observados somente em `http://127.0.0.1:18086`; sem chamadas de dados/API. Console sem erro da aplicação; React Router 6 emitiu avisos de migração futura.
- [155 testes / 14 arquivos](tests.txt), incluindo os cinco `it.fails` legados **inalterados**, e quatro testes novos de reconciliação/estado. [Lint sem avisos](lint.txt), [build experimental](experimental-build.txt), [build público](public-build.txt).
- [Contraprova Production sob flags adversas](production.txt) e [verificador adicional](verify-isolation.py): JS/CSS públicos idênticos à base; `src`, snapshots, laboratório, contratos, backend, ETL e publicação sem diff. Nenhuma correção legada é reivindicada.
- Revisão React: URL como origem da seleção, cálculos derivados no render, componentes pequenos, chaves estáveis, links/botões semânticos, fallback de logo e nenhum efeito de aquisição de dados. A entrada pública não importa o experimento.

## Execução e estado

```bash
cd '/Users/pedrocollet/.codex/worktrees/broadcast-experience-v1/NFL Sideline'
npm --prefix web-ui run experience:dev
# http://127.0.0.1:18086/?round=7
```

Somente um servidor foi criado por esta entrega: Vite, loopback 18086, PID `69029`. Para encerrá-lo: `kill 69029`. Dependências locais reutilizadas por symlink ignorado; nenhum pacote novo. A [README da entrada](../../../web-ui/broadcast-experience/README.md) reúne comandos e rotas. Build experimental em `web-ui/experience-dist/`, ignorado; configurações e barreiras do laboratório anterior não foram alteradas.

O checkout original permanece na branch anterior e sem alterações rastreadas; o piloto continua em f174af8d. Não houve merge, push ou deploy. Não encerrei processos preexistentes. As portas 18083/18084/18085/8777 estavam presentes no inventário inicial e ausentes no final; não foram reiniciadas ou substituídas por este trabalho.

## Autocrítica e limites

A composição tem uma abertura de futebol reconhecível e uma mesa coesa; não usa uma grade de cartões independentes. A tipografia alterna papéis e a geometria dos gráficos mostra direção/parte do total. Outros duelos e recortes dão continuidade funcional ao piloto isolado.

A parte inferior da mesa continua mais utilitária e textual; no mobile a leitura completa é longa (~3,5 mil px com detalhes fechados). O arquivo tem apenas três cenários. Não há capacetes, retratos, pesquisa com participantes, teste em dispositivos físicos ou integração pública. Esses limites não impedem avaliar esta direção, mas o experimento não é uma migração pronta do produto real.
