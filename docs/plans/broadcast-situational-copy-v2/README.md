# Acabamento editorial situacional · copy-v2

Implementados somente os três ajustes editoriais solicitados. [Relatório antes/depois](REPORT.md) · [Plano prévio](PLAN.md) · [Preservação](checks/preservation.json) · [Navegador](evidence/browser.json).

## Avaliação local

- [NYJ ataque/W1 · terceiras](http://127.0.0.1:18099/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&analysis=third&reading=game).
- [NYJ ataque/W1 · red zone](http://127.0.0.1:18099/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&analysis=redzone&reading=game).
- [NYJ defesa · terceiras W1–2](http://127.0.0.1:18099/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=def&analysis=third&reading=2026%2FREG%2F1%2C2).
- [NYJ defesa · red zone W1–2](http://127.0.0.1:18099/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=def&analysis=redzone&reading=2026%2FREG%2F1%2C2).
- [MIN W2 · uma campanha](http://127.0.0.1:18099/?season=2026&week=2&game=2026_02_MIN_CHI&team=MIN&side=off&analysis=redzone).
- [ATL W1 · fonte presente sem oportunidades](http://127.0.0.1:18099/?season=2026&week=1&game=2026_01_ATL_PIT&team=ATL&side=off&analysis=redzone).
- [BAL W3 · fonte ausente](http://127.0.0.1:18099/?season=2026&week=3&game=2026_03_BAL_DAL&team=BAL&analysis=redzone).

Worktree gerenciada `/Users/pedrocollet/.codex/worktrees/broadcast-situational-copy-v2/NFL Sideline`, branch `codex/broadcast-situational-copy-v2`, base exata `d410cc5ad9749255b241797a0f8c91a273b6a560`. Referência limpa na base e servidor **18098/PID49375 preservados**.

Servidor próprio conferido: **PID 64333**, `node scripts/journey-dev.mjs`, bind **127.0.0.1:18099**, strictPort. Não iniciar outra instância se já estiver ativo. Nenhum processo foi encerrado para liberar porta.

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-situational-copy-v2/NFL Sideline'
./docs/plans/broadcast-situational-copy-v2/run-local.sh
# Encerrar somente esta instância, depois de conferir o listener:
lsof -nP -a -p 64333 -iTCP:18099 -sTCP:LISTEN && kill -TERM 64333
```

O script apenas configura os mesmos dados pinados e inicia a entrada journey existente em outra porta. Não carrega `.env` nem instala dependências. Foram reutilizadas as dependências npm locais existentes; nenhum arquivo de configuração/build foi alterado nesta entrega. Ctrl+C encerra uma instância iniciada no próprio terminal.

## Dados e reprodução dos checks

Mesmos pacotes físicos, sem geração, cópia ou modificação:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled`

Cópia preservada: `verified-copy`, irmã dessa raiz. Pin permanece `sha256:2af2a33211c09658fb6b831188dc5c5ac3bee9b3fc4b2b6008748921ac7c339c`. A [config situacional anterior](../broadcast-situational-w12-v1/situational-config.json), contrato, reader, backend e ledger estão intactos.

```sh
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
# Com os dois servidores ativos, compara integralmente as respostas e fontes:
python3 -B docs/plans/broadcast-situational-copy-v2/verify-preservation.py
git diff --check d410cc5ad9749255b241797a0f8c91a273b6a560
git log --oneline d410cc5ad9749255b241797a0f8c91a273b6a560..HEAD
git rev-parse HEAD
git status --short
```

269 testes frontend passaram em 27 arquivos, com os ensaios privados reais habilitados e cinco expected-failure legados intactos. Lint, quatro builds e preservação passaram. O ensaio real percorre os 192 documentos/384 contextos; os casos sintéticos de empate, desconhecidas e insuficiência ficam exclusivamente nos testes. [Logs](checks/).

No navegador, compare os dois links NYJ/W1 com 18098; alterne lado/período, recarregue e use voltar/avançar. Use Tab/Enter no expansível existente e confira seus grupos de método/procedência. Observe MIN, ATL e BAL nos links acima. Foram inspecionados 1440, 390 e 320 px e fonte raiz 200%, restaurando viewport/fonte depois. Não foi feita simulação de dados na aplicação.

[Antes · terceiras](evidence/before-third-1440.png) · [Depois · terceiras](evidence/after-third-1440.png) · [Antes · red zone](evidence/before-redzone-1440.png) · [Depois · red zone](evidence/after-redzone-1440.png) · [Mobile 390](evidence/nyj-redzone-390.png) · [Mobile 320](evidence/defense-inclusive-third-320.png) · [Texto 200% e procedência](evidence/method-320-text200.png).

A entrega termina nesses três ajustes de apresentação. Não houve redesign da organização, novos controles, métricas, modelos, semanas, merge, push, deploy ou publicação. Aceite humano permanece para avaliação.
