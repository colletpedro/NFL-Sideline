# Passagem técnica — laboratório local

Entregue em 04/11/2026, branch `codex/qb-risk-lab-v1`, worktree:
`/Users/pedrocollet/.codex/worktrees/qb-risk-lab-v1/NFL Sideline`.

Base exata v2 `a6d3672f770e7d5db3728edbff216b229fc6aba7`, com ancestralidade do site aprovado `5b38f04e559bad5fc1b4ef25116cc0afb93293d9`. Ambos checkouts continuam limpos e sem alteração de HEAD. Nenhum merge/push/deploy/publicação. Não usar o `Handoff.md` antigo como norma.

## Estado para revisão

- [Abrir laboratório](http://127.0.0.1:18121/?view=risk-lab&season=2026). Servidor próprio ativo: PID79971,127.0.0.1:18121, script `web-ui/scripts/risk-lab-dev.mjs`. PID foi conferido por `lsof`/comando/cwd nesta entrega; em sessão futura, conferir novamente.
- Servidor aprovado 18111 preservado. Preview temporário 18122 foi encerrado por SIGTERM no próprio PID82187;nenhum outro processo foi encerrado.
- Para parar somente o laboratório: `docs/plans/qb-risk-lab-v1/stop-local.sh`. Confere listener, comando e cwd antes de SIGTERM;recusa outro processo/worktree. Ctrl-C no seu terminal também serve. Para reiniciar: `run-local.sh`, porta fixa e estrita.
- Fontes: 04/11/2026,14:47 UTC. 121 jogos W1–8 utilizáveis, sem encerrado pendente. 151 sem placar final fora. 7.970 passes,242 rótulos,253,2163 esperados,170 INT.
- Pacote ativo `d3739e3d9103c48fda1c417a`, pipeline 1.0.0. M3 e hash preservados;estrutura 2023–24, calibração 2025. Não retreinar nem recalibrar em atualização.
- `docs/plans/qb-risk-lab-v1/update.sh` faz a atualização inteira. Não confundir o botão “Conferir versão disponível” com aquisição;ele só relê o pacote já validado.

## Arquivos para conferir

[README](README.md):ambiente, comandos, atualização, replay e build. [REPORT](REPORT.md):observado/estimado/desconhecido, limites e tentativas. [DATA-COVERAGE](DATA-COVERAGE.md):população e fontes. [VERIFICATION](VERIFICATION.md):testes, capturas e igualdade numérica. [DECISION](DECISION.md):substituição explícita da antiga espera/reserva.

A interface está em `web-ui/broadcast-journey/risk-lab`. A entrada Vite separada só habilita o link na cópia de `season/App.tsx`;a entrada anterior tem `labEnabled=false`. Não importar o laboratório no `web-ui/src`nem alterar o public contract para publicar estes dados. Endpoints de leitura: `/__risk-lab/index.json` e `/__risk-lab/packages/<ID>/players/<GSIS>.json`. A cópia estática usa 209 endpoints e headers pinados de `local-routes.json`;precisa do adapter correspondente em eventual hospedagem futura.

## Artefatos e recuperação

Store durável:
`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-lab-v1`.

Aquisição inicial íntegra em `runs/20261104T144706530236Z`;a montagem inicial do resumo falhou e seu `failure.json` foi preservado. Replays corrigidos mantiveram os passes/rótulos. Cada run tem os seus próprios recibos;pacotes são imutáveis e o commit point é `current.json`. Nunca editar um pacote para “corrigir” um número;adquirir/construir uma nova versão e conferir `labelChanges`.

Recuperação canônica: `recovery/20261104-v1`dentro do store. Arquivo completo:
`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/qb-risk-lab-v1/20261104-v1.tar.gz`.
SHA-256 `d19cb8b3146503f2da04c5a201036be57b813fad371ae693011536da12a8558b`;114.762.457 bytes,365 arquivos verificados. [Recibo](evidence/recovery.json).

Para recuperar, se a pasta canônica sumir: conferir SHA do tar, extrair em **novo** diretório, conferir todos os hashes de `recovery-manifest.json`e apontar `NFL_RISK_LAB_RECOVERY`para a pasta extraída. Rodar `reproduce.sh` em destino novo. Não extrair por cima de arquivos existentes ou do produto aprovado. Os wheels incluem dependências deste Python 3.11/macOS;outras plataformas precisam resolver um ambiente equivalente e declarar diferenças.

Reprodução executada em `reproduction/20261104-v1`, sem rede e em venv novo;mesmos 70 arquivos do pacote em bytes. [Recibo](evidence/reproduction.json). O build preservado em `recovery/20261104-v1/web-ui/risk-lab-dist` pode ser servido com o script Node de preview arquivado em `web-ui/scripts`;não precisa de npm nem Python para a navegação.

## Próxima sessão

Primeiro, conferirHEAD/status, listener e `current.json`;não usar PIDs históricos cegamente. Rever a experiência visual, evidências e atribuição;então, se houver novos dados, executar atualização manual e conferir pendências/revisões. Atualizações de dados não são aprovação de um novo modelo. A antiga reserva deixou de ser bloqueio operacional por decisão expressa;nenhum retrospecto deve ser rebatizado de holdout intocado. Não há processo aguardando dezembro nem tarefa recorrente.

Na documentação de entrega, os commits anteriores são `2dfe8cb` (decisão) e `2ba1a78` (pipeline/laboratório). Os commits seguintes registram ajuste de navegação/revisão e reprodução/documentação. A resposta final registra o HEAD completo após o fechamento;`git log -4 --oneline` é a referência local verificável.
