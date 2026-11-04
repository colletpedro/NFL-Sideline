# Passagem — comunicação v2

A implementação está funcional na worktree `codex/qb-risk-lab-communication-v2`, derivada do commit exato `8e98296dd9352b5ea51ea69b2be67ea0f163f473`. A referência 18121 e o site aprovado 18111 permanecem intactos. Nenhuma alteração científica foi feita.

A revisão do usuário pode começar pelo [laboratório](http://127.0.0.1:18123/?view=risk-lab&season=2026) e por [Daniel Jones](http://127.0.0.1:18123/?view=risk-lab&season=2026&player=00-0035710). Seus valores são lidos do pacote, sem constantes no código: 267 passes, 8 jogos, 17 classificados como interceptáveis, aproximadamente 8,66 esperados e 9 interceptações sofridas.

Conferir a densidade de grupos perto de zero e a continuidade entre gráfico, lista e detalhe. Os grupos dependem do tamanho disponível; não são categorias estatísticas. Não promover o residual a ranking de habilidade. O modelo continua sem estimar interceptações sofridas.

Reprodução e encerramento direcionado estão em [README](README.md). Executar `checks.sh` com as fontes locais e depois `verify.py`; ambos gravam somente nos relatórios desta entrega. A prova de preservação verifica hashes, os checkouts de referência, dados do build e paths protegidos. Não acionar atualização de dados para reproduzir a interface.

O servidor desta entrega usa somente 127.0.0.1:18123 e strictPort. Conferir o listener antes de qualquer encerramento; `stop-local.sh` recusa processo ou checkout diferente. Não encerrar servidores anteriores. Não houve merge, push, deploy ou publicação.
