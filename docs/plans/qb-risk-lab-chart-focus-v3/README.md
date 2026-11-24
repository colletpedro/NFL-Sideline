# Laboratório — foco no gráfico v3

[Abrir laboratório](http://127.0.0.1:18124/?view=risk-lab&season=2026) · [Daniel Jones](http://127.0.0.1:18124/?view=risk-lab&season=2026&player=00-0035710).

Worktree gerenciada `/Users/pedrocollet/.codex/worktrees/qb-risk-lab-chart-focus-v3/NFL Sideline`, branch `codex/qb-risk-lab-chart-focus-v3`, a partir de `dc43f02c4c00e36e7b069b6a7dd7b7040c9f1ee8`. A referência 18123, seus arquivos e os servidores anteriores permanecem preservados. Não houve aquisição, treinamento, recalibração, alteração da população, merge, push, deploy ou publicação.

## Operação

Comandos nesta worktree:

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui ci
docs/plans/qb-risk-lab-chart-focus-v3/run-local.sh
```

Somente `127.0.0.1:18124`, strictPort, sem fallback. O script usa o store ativo existente da v1 em modo de leitura. Não acionar o mecanismo de atualização para reproduzir esta mudança visual. Nenhuma variável de segredo ou arquivo `.env` é necessário.

Para encerrar exclusivamente o servidor desta worktree:

```sh
docs/plans/qb-risk-lab-chart-focus-v3/stop-local.sh
```

O script confere porta, comando e cwd antes do SIGTERM. Não confie em PIDs históricos. Não encerre 18123, 18121, 18111 ou outros servidores de referência.

## Verificação reproduzível

```sh
docs/plans/qb-risk-lab-chart-focus-v3/checks.sh
python3 docs/plans/qb-risk-lab-chart-focus-v3/verify.py
```

O wrapper mantém os exports de fontes locais da auditoria anterior, configura o store de QA do laboratório e grava somente em `checks/` desta entrega. Os 68 casos condicionais permanecem habilitados. Executa a suíte completa, TypeScript, lint, build público e build separado. Logs contêm tempos e paths do ambiente, sem promessa de igualdade de bytes entre execuções.

O verificador reaproveita a reconciliação independente da v2, com projeções retangulares e inspeção das prévias. Lê os recibos reais do DOM em `evidence/browser-cases.json`, soma evidências por passe das fontes congeladas e confere unidade, população, coordenadas, resumos, nomes e ausência de recorte por volume. Também verifica hashes do pacote/modelo, fontes brutas, checkouts de referência, paths protegidos e bytes dos builds. Reexecutá-lo não atualiza fontes nem escreve em documentos anteriores.

O build permanece separado em `web-ui/risk-lab-dist`, com 209 documentos GET idênticos à referência. O build público protegido em `web-ui/dist` continua idêntico. Esta entrega não altera publicação ou contratos.

## Interação

Hover/foco mostram a identificação. Clique, toque sintetizado pelo navegador ou Enter/Espaço selecionam imediatamente. A seta para baixo, com um ponto focado, abre os nomes próximos; Escape fecha a prévia. Os nomes da prévia e a lista completa são alternativas aos pontos difíceis de distinguir. A prévia fica sob os eixos no celular e com texto ampliado; no desktop fica dentro do painel.

A seleção mantém período, escala e distribuição inteira. O resumo e a lista ficam abaixo do gráfico; o aprofundamento carrega sem botão adicional e tem acesso explícito. URLs antigas, evidências diretas, recarga e histórico permanecem válidos. `group` legado é explicado sem substituir um `player` válido nem selecionar outro automaticamente.

[Relatório](REPORT.md) · [Capturas](CAPTURES.md) · [Design](DESIGN.md) · [Passagem](HANDOFF.md) · [Preservação](evidence/preservation.json) · [Reconciliação](evidence/browser-reconciliation.json).
