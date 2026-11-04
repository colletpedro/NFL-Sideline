# Laboratório — comunicação e visualização v2

[Abrir laboratório refinado](http://127.0.0.1:18123/?view=risk-lab&season=2026) · [Daniel Jones](http://127.0.0.1:18123/?view=risk-lab&season=2026&player=00-0035710) · [Anthony Richardson](http://127.0.0.1:18123/?view=risk-lab&season=2026&player=00-0039164).

Base exata: `8e98296dd9352b5ea51ea69b2be67ea0f163f473`, na worktree gerenciada `/Users/pedrocollet/.codex/worktrees/qb-risk-lab-communication-v2/NFL Sideline`, branch `codex/qb-risk-lab-communication-v2`. A referência em 18121 permanece no checkout e HEAD anteriores. Não houve aquisição, treino, recalibração, merge, push, deploy ou publicação.

## Operação

A partir desta worktree:

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui ci
docs/plans/qb-risk-lab-communication-v2/run-local.sh
```

Servidor somente em `127.0.0.1:18123`, `strictPort`, sem fallback nem encerramento de outro processo. Usa o mesmo store ativo da referência, somente para leitura. Não executar a atualização de dados para reproduzir esta mudança visual. O mecanismo de atualização manual da v1 não foi alterado nem acionado.

Encerramento direcionado:

```sh
docs/plans/qb-risk-lab-communication-v2/stop-local.sh
```

O script confere porta, comando e cwd antes de enviar SIGTERM ao próprio processo. Em nova sessão, confira o listener novamente; não confie em PID histórico. Os servidores 18121/18111 e demais referências não foram encerrados.

## Verificação reproduzível

```sh
docs/plans/qb-risk-lab-communication-v2/checks.sh
python3 docs/plans/qb-risk-lab-communication-v2/verify.py
```

O wrapper copia **somente os exports** do wrapper de auditoria anterior, acrescenta o store de QA do laboratório e grava em `checks/` desta entrega. Os relatórios antigos não são sobrescritos. Todos os 68 casos condicionais ficam configurados. TypeScript, lint, build público e build separado são executados. A reconciliação lê recibos reais do DOM em `evidence/browser-cases.json` e compara com somas independentes das evidências por passe, além de verificar hashes e isolamento.

O build continua separado em `web-ui/risk-lab-dist`. São 209 documentos de dados GET com os mesmos bytes da referência; somente os assets de apresentação mudam. O build público normal em `web-ui/dist`, contrato e snapshots públicos continuam idênticos. Não configurar publicação externa nesta entrega.

## Navegação e unidades

O gráfico começa com todos os QBs identificados que têm passes no período, sem corte de volume. “Todos os lançadores” inclui outras posições. “Totais / Por 100 passes” muda os dois eixos com o mesmo denominador. A diagonal é igualdade numérica, sem regressão ajustada aos pontos.

Círculos são os dados; caixas e linhas-guia são identificações. Marcas próximas abrem uma lista de integrantes, sem somar suas estatísticas. Ao abrir um grupo, a seleção individual anterior é limpa para evitar atribuir seus números ao grupo. Nome ou ponto seleciona imediatamente o jogador, mantém os demais pontos e carrega seu detalhe abaixo. A lista é alternativa acessível ao gráfico, com logo, nome e unidades. Ela tem rolagem vertical própria, sem rolagem horizontal da página.

`player`, `period`, `game`, `cross` e `play` antigos continuam válidos. `scale` e `group` são opcionais. Os parâmetros antigos de ordenação/busca/volume são aceitos com aviso: a nova visão coletiva apresenta todo o recorte de posição e período. Selecionar jogo filtra as evidências; os totais do jogador continuam explicitamente no período selecionado. Sem passes, a apresentação usa travessões e não inventa taxa zero.

[Relatório e revisão técnica](REPORT.md) · [Design](DESIGN.md) · [Prova de preservação](evidence/preservation.json) · [Reconciliação do navegador](evidence/browser-reconciliation.json) · [Contagem dos testes](evidence/checks.json).
