# Leitura do confronto · entrega 2/5

Página funcional e retrospectiva de **NYJ × TEN, 2026 REG W1**, com os dois ataques juntos. Entrada reversível: [abrir piloto](http://127.0.0.1:18102/?view=matchup-reading). Home e URLs anteriores permanecem disponíveis; o cabeçalho oferece retorno explícito ao explorador. Nenhum parâmetro seleciona fonte, caminho ou transporte.

A página reúne resultado, três fatos com evidências, EPA, todas as terceiras por distância, campanhas de red zone, referências ofensivas da liga W1, cotações arquivadas e método. Apenas o fundamento do EPA pode ser alternado. Não houve estudo com participantes.

## Documentação

- [Plano anterior à implementação e mapa bloco → campo → permissão](PLAN.md), commit `4ef5394`.
- [Reconferência, inspeção, ajustes, isolamento e limitações](REPORT.md).
- [Roteiro preparado para a entrega 3/5](STUDY-3-OF-5.md).
- [Captura desktop](evidence/desktop-1440.png), [390](evidence/mobile-390.png), [320](evidence/mobile-320.png), [fonte 200%: terceiras](evidence/text200-third-320.png), [fonte 200%: auditoria](evidence/text200-method-320.png), [falha de fonte](evidence/source-failure-320.png).
- [Registro de navegador](evidence/browser.json), [oráculo racional independente](checks/numerical-oracle.json), [HTTP](checks/http.json), [isolamento](checks/isolation.json).

## Base e integração

Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/broadcast-matchup-reading-v1/NFL Sideline`; branch `codex/broadcast-matchup-reading-v1`. Base confirmada limpa em `3c1a99b675cb4182323952ab08be8a7d8658175a`, branch `codex/broadcast-comparison-foundation-v1`. O plano foi commitado antes da implementação. O HEAD final consta na entrega do chat e pode ser obtido por `git rev-parse HEAD`, sem autorreferência no documento.

O operador fornece [source-config.json](source-config.json). Pacote físico preservado:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled`

Pin: `sha256:b10a2028f26d6acc229f80bbd27269016dd2e6b2e4b432a6d8a9109f643e5ee4`. Contrato `broadcast-comparison-foundation-v1`, projeção `1.0.0`. Nenhum pacote foi regenerado. As fontes autocontidas e a cópia de recuperação da entrega 1 foram novamente conferidas pelo inventário de hashes original.

A configuração própria `vite.matchup.config.ts` reutiliza o reader Python completo, sem editar processamento. Valida pacote/pin no startup e congela os **243.841 bytes** de `comparison.json`. `GET /__matchup-reading/` exige marcador `X-Local-Matchup: 1`, Host `127.0.0.1:18102`, Origin ausente ou da mesma origem e corpo vazio. Recusa outros métodos, autoridades duplicadas, caminhos e query. Falha de validação mantém a fonte indisponível (503), sem fallback; mudar o arquivo exige reiniciar a instância. O navegador não escolhe arquivos. A política restrita de 18101 permanece intacta.

O calendário usa o `StaticNflDataClient` existente, com identidade exata de jogo/participantes/REG/W1. Nomes, data e placar não vêm de constantes de apresentação. O adaptador aplica permissões de operação e vínculos de evidências antes de renderizar. Fixtures e mutações sintéticas existem somente em testes; não entram no bundle da página.

## Execução local

A instância já está disponível. Para iniciar novamente após encerrá-la:

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-matchup-reading-v1/NFL Sideline'
./docs/plans/broadcast-matchup-reading-v1/run-local.sh
```

Somente `127.0.0.1`, porta 18102 com `strictPort`; porta ocupada causa falha, sem encerrar outro processo. PID observado: **97976**. Log e recibo do processo ficam fora da worktree, em `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-matchup-reading-v1/20261023-v1/server.log` e `server.pid`.

Encerramento direcionado, após conferir o PID:

```sh
lsof -nP -a -p 97976 -iTCP:18102 -sTCP:LISTEN
kill -TERM 97976
```

Referências preservadas: [base comparável 18101](http://127.0.0.1:18101/__comparison/) (GET exige `X-Local-Comparison: 1`), [explorador 18100](http://127.0.0.1:18100/?view=explorer), [editorial 18099](http://127.0.0.1:18099/), [situacional 18098](http://127.0.0.1:18098/). PIDs atuais: 95101, 30265, 30251 e 30244, respectivamente. Ao retomar em 24/10, as portas 18098–18100 estavam sem listener e os processos anteriores ausentes. Foram restauradas pelas respectivas worktrees/configurações originais, sem alterar arquivos, após conferir portas livres. [Recibo da restauração](checks/restored-references.json); [conferência anterior à retomada](checks/isolation-before-resume.json). Não se encerrou processo para liberar porta.

## Reprodução dos checks

Usa dependências já presentes; não instala nada. A configuração do servidor é a do script acima. Na raiz da worktree:

```sh
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
export NFL_MATCHUP_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled'
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
"$NFL_OBSERVATION_PYTHON" docs/plans/broadcast-matchup-reading-v1/verify_numbers.py
npm --prefix web-ui test
npm --prefix web-ui run lint
web-ui/node_modules/.bin/tsc -p web-ui/tsconfig.matchup.json
npm --prefix web-ui run journey:build
web-ui/node_modules/.bin/vite build --config web-ui/vite.matchup.config.ts
npm --prefix web-ui run real:build
npm --prefix web-ui run experience:build
npm --prefix web-ui run build
"$NFL_OBSERVATION_PYTHON" docs/plans/broadcast-matchup-reading-v1/verify_http.py
"$NFL_OBSERVATION_PYTHON" docs/plans/broadcast-matchup-reading-v1/verify_isolation.py
git diff --check
```

Os dois últimos checks HTTP pressupõem os cinco listeners da avaliação ativos. O teste real não deve ser interpretado como executado quando `NFL_MATCHUP_QA_BUNDLE` estiver ausente: nesse caso o Vitest sinaliza o grupo como skipped. Na rodada registrada, todos os testes reais foram executados.

Sem merge, push, deploy, publicação ou promoção da interface.
