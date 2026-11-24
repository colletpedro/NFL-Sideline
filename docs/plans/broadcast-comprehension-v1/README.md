# Compreensão da página de confronto · entrega 3/5 encerrada

**Entrega 3/5 encerrada no escopo revisado pelo usuário.** Uma sessão humana recebida, **P01/N=1**, respostas como **paráfrases revisadas**, coleta encerrada sem recrutamento adicional. Análise qualitativa individual; limiares originais não aplicáveis. Recomendação: **avançar para 4/5**, mantendo os limites conhecidos.

- [Versão refinada 18103](http://127.0.0.1:18103/?view=matchup-reading).
- [Referência preservada 18102](http://127.0.0.1:18102/?view=matchup-reading).
- [P01 corrigido](results/P01.md), [emenda posterior à coleta](AMENDMENT-01.md), [procedência e registro original completo](results/provenance/README.md).
- [Relatório final](REPORT.md), [passagem para 4/5](HANDOFF-4-OF-5.md), [isolamento técnico](checks/closure/isolation.json), [navegador](evidence/closure/browser.json).

## História e interpretação

A preparação original, commit `68eaf4179de72c6accc56749f9d4565666a23536`, tinha zero sessões registradas. Depois foi recebido o registro chamado SIM01 em outra conversa/raiz local. O usuário esclareceu sua origem humana e a revisão posterior das respostas; a classificação foi corrigida para P01. O [protocolo original](PROTOCOL.md) continua integral, histórico, sem reinterpretar a meta anterior como se previsse N=1. Seus recibos `checks/technical.json` e walkthrough de preparação também são históricos, não o N atual.

P01 respondeu às comparações gerais, distinguiu taxa/contagem de red zone, identificou o período e encontrou caminhos de consulta. O limite de estabilidade de 1/1 foi explicitado **após** o complemento. EPA permaneceu parcialmente compreendido. Responder pelo resumo e consultar a lista da liga são caminhos legítimos.

O único acabamento é uma explicação visível de EPA, sem novo controle ou exemplo. **Foi implementado em resposta ao relato e ainda não recebeu reconfirmação humana; não se afirma que resolveu a dúvida.** Marcas individuais, identificação direta dos times no gráfico, celular físico e frequência desses comportamentos em outras pessoas continuam não avaliados.

## Antes e depois de EPA

Antes: “EPA · pontos esperados por jogada com EPA válido · deste jogo”.

Depois: “EPA/jogada é a variação média dos pontos esperados nas jogadas com EPA válido deste jogo. Positivo indica ganho; negativo, perda. Não é o placar.”

A frase substitui o parágrafo de unidade anterior nos três fundamentos. Denominadores, escala e populações originais permanecem; detalhes existentes de sacks/scrambles e modelo não identificado são mantidos. [Antes desktop](evidence/closure/epa-before-1440.png), [depois desktop](evidence/closure/epa-after-1440.png), [antes 320](evidence/closure/epa-before-320.png), [depois 320](evidence/closure/epa-after-320.png), [390](evidence/closure/epa-after-390.png), [texto 200%](evidence/closure/epa-text200-320.png) e [valores ampliados](evidence/closure/epa-text200-320-values.png). Capturas e cliques técnicos não são uma segunda sessão humana.

## Operação

Worktree: `/Users/pedrocollet/.codex/worktrees/broadcast-comprehension-v1/NFL Sideline`; branch `codex/broadcast-comprehension-v1`. A referência 18102 segue na worktree `broadcast-matchup-reading-v1`, código `c5be5b0dbb525faea85fab350039d8a5c1c87af5`, limpa. Base da preparação conferida limpa em `68eaf4179de72c6accc56749f9d4565666a23536`. Correção documental em commit separado `bfd1688`; HEAD final informado no chat e consultável por `git rev-parse HEAD`.

A instância refinada está ativa: **127.0.0.1:18103, strictPort, PID 44780**. O script abaixo fornece explicitamente a porta, as três configurações do operador e o Python existentes. `vite.matchup.config.ts` já passa a mesma porta às fronteiras comparison/observation/situational; não foi modificado. Host/Origin são exatos para 18103; Origin/Host de 18102 não são aceitos na nova fronteira. Sem alteração da política de 18101 ou de endpoints anteriores. Configuração/pin validados pelo reader no startup, snapshot congelado e nenhuma escolha de caminho pelo browser.

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-comprehension-v1/NFL Sideline'
./docs/plans/broadcast-comprehension-v1/run-refined-local.sh
```

Não iniciar duplicata enquanto estiver ativo; porta ocupada causa falha, sem encerrar outro processo. Log e PID fora da worktree: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comprehension-v1/20261024-epa-v1/server.log` e `server.pid`. Encerramento direcionado:

```sh
lsof -nP -a -p 44780 -iTCP:18103 -sTCP:LISTEN
kill -TERM 44780
```

Referências preservadas com os mesmos PIDs: 18098/30244, 18099/30251, 18100/30265, 18101/95101 e 18102/97976. Nenhuma porta liberada por encerramento de processo.

Pacote preservado: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled`; pin `sha256:b10a2028f26d6acc229f80bbd27269016dd2e6b2e4b432a6d8a9109f643e5ee4`. As respostas 18102 e 18103 são os mesmos 243.841 bytes do artefato. O refinamento não altera dados, definições ou permissões.

## Verificação reproduzível

Na raiz desta worktree, com as dependências já presentes e os servidores ativos:

```sh
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
export NFL_MATCHUP_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled'
npm --prefix web-ui test -- broadcast-journey/matchup/matchup.test.tsx src/components/visual-preparation-regressions.test.tsx
npm --prefix web-ui run lint
web-ui/node_modules/.bin/tsc -p web-ui/tsconfig.matchup.json
npm --prefix web-ui run journey:build
web-ui/node_modules/.bin/vite build --config web-ui/vite.matchup.config.ts
npm --prefix web-ui run real:build
npm --prefix web-ui run experience:build
npm --prefix web-ui run build
'/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -B docs/plans/broadcast-comprehension-v1/verify_closure.py
git diff --check 68eaf4179de72c6accc56749f9d4565666a23536
```

18 testes selecionados, lint, TypeScript e cinco builds passaram; cinco falhas esperadas legadas preservadas. Verificador de isolamento aceita somente a substituição do primeiro parágrafo de unidade e documentos desta entrega, confirma hashes públicos e recusas HTTP. Não foi criada uma asserção de teste que espelha a redação nova. Não houve reconciliação bruta histórica, backend/ETL ou generalização de confrontos.

Os instrumentos de coleta e `verify_preparation.py` permanecem históricos; o gate atual é `verify_closure.py`. Não recrutar novas pessoas para fechar esta entrega. Sem merge, push, deploy ou publicação. A 4/5 está recomendada e **não implementada**.
