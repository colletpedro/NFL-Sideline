# Passagem — foco no gráfico v3

Versão local funcional em [18124](http://127.0.0.1:18124/?view=risk-lab&season=2026), branch `codex/qb-risk-lab-chart-focus-v3`, worktree gerenciada derivada de `dc43f02c4c00e36e7b069b6a7dd7b7040c9f1ee8`. A v2 em 18123 e os artefatos científicos estão preservados. Nenhum merge, push, deploy ou publicação.

O gráfico tem largura integral e altura independente da largura. Sem nomes, quantidades ou linhas-guia permanentes. Hover é prévia local; clique/toque sintetizado/Enter selecionam e carregam o detalhe abaixo. A lista interna acompanha o nome selecionado sem mover a página. A prévia fica sob os eixos no celular/texto ampliado. O tooltip desktop respeita os limites do painel. Escape fecha sem limpar a seleção.

Começar a revisão pela [visão coletiva](http://127.0.0.1:18124/?view=risk-lab&season=2026), [Daniel Jones](http://127.0.0.1:18124/?view=risk-lab&season=2026&player=00-0035710) e [jogador + grupo legado](http://127.0.0.1:18124/?view=risk-lab&season=2026&player=00-0035710&group=00-0039164). O último link mantém Daniel e explica a marca anterior, sem substituir o jogador.

Conferências concluídas: 400 resultados esperados (395 normais e 5 expected failures), nenhum skip/falha inesperada; TypeScript, lint com warning legado e builds passaram. Reconciliação independente: 14 estados, 733 coordenadas. O M3, pacote, previsões, fontes e documentos GET preservam hashes; build público byte a byte igual. Ver [relatório](REPORT.md), [provas](evidence/preservation.json), [recibos](evidence/browser-reconciliation.json) e [capturas](CAPTURES.md).

Limite de ferramenta: gesto nativo `Input.dispatchTouchEvent` não disponível no IAB. Conferido por eventos de toque e clique sintetizados, clique real e teclado; não alegar teste em telefone físico. A avaliação humana de compreensão e o aceite visual ainda pertencem ao usuário. A região perto de zero permanece densa e tem prévia/lista como alternativa; não modificar coordenadas nem aplicar um corte para melhorar a composição.

[README](README.md) contém comandos de operação, suíte configurada, verificador offline e encerramento direcionado. Usar `stop-local.sh` desta entrega, que verifica porta/cwd/comando. Não encerrar servidores anteriores nem acionar aquisição/atualização para reproduzir esta interface.
