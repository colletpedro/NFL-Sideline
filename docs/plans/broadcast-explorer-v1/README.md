# NFL Sideline · Explorador de recortes v1

Experimento local reversível, sem substituição da copy-v2 nem promoção automática. [Relatório](REPORT.md) · [Plano anterior ao código](PLAN.md) · [Interações e limites](INTERACTION.md) · [Comparação das seis tarefas](TASKS.md).

- [Entrar no explorador · exemplo inicial identificado](http://127.0.0.1:18100/?view=explorer).
- [NYJ/W1/ataque · todas as terceiras · ponto de partida equivalente](http://127.0.0.1:18100/?view=explorer&season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&analysis=third&question=distance&reading=game).
- [Referência 18099 · mesmo contexto](http://127.0.0.1:18099/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&analysis=third&reading=game).
- [NYJ/W1 · terceiras longas](http://127.0.0.1:18100/?view=explorer&season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&analysis=third&question=distance&refine=long&reading=game).
- [NYJ/W1 · destaque FG sobre todas as campanhas](http://127.0.0.1:18100/?view=explorer&season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&analysis=redzone&question=outcomes&refine=FIELD_GOAL&reading=game).
- [ATL/W1 · sem oportunidades](http://127.0.0.1:18100/?view=explorer&season=2026&week=1&game=2026_01_ATL_PIT&team=ATL&side=off&analysis=redzone&question=outcomes&reading=game).
- [BAL/W3 · sem fonte](http://127.0.0.1:18100/?view=explorer&season=2026&week=3&game=2026_03_BAL_DAL&team=BAL&side=off&analysis=redzone&question=outcomes&reading=game).

Branch `codex/broadcast-explorer-v1`, worktree gerenciada `/Users/pedrocollet/.codex/worktrees/broadcast-explorer-v1/NFL Sideline`, criada da base exata `5348ab117bffd01c75323a0c56466e450b522260`. Plano `e2f818f`; implementação `8fe7253`. HEAD final e árvore conferidos no chat para evitar hash autorreferente neste documento.

## Operação local

Instância própria **PID74464**, `node scripts/journey-dev.mjs`, bind **127.0.0.1:18100**, strictPort. Não iniciar outra instância se a porta já estiver ocupada. Referência **18099/PID64333** preservada e não encerrada. Nenhum processo foi encerrado para liberar porta.

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-explorer-v1/NFL Sideline'
./docs/plans/broadcast-explorer-v1/run-local.sh
# Ctrl+C encerra a instância iniciada nesse terminal.
# Para encerrar somente a instância própria desta entrega, conferir antes:
lsof -nP -a -p 74464 -iTCP:18100 -sTCP:LISTEN && kill -TERM 74464
```

O script não instala dependências nem carrega `.env`. Foram reutilizadas dependências npm existentes por symlink. As mesmas configurações explícitas antigas são usadas. Bundle situacional físico: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled`. Pin `sha256:2af2a33211c09658fb6b831188dc5c5ac3bee9b3fc4b2b6008748921ac7c339c`. Bundle anterior de588 observações e seu transporte também preservados.

## Reprodução técnica

```sh
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
# Com 18099 e 18100 ativos:
python3 -B docs/plans/broadcast-explorer-v1/verify-preservation.py
'/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -B docs/plans/broadcast-w12-expansion-v1/verify_http.py --config "$PWD/docs/plans/broadcast-live-hub-v1/lab-config.json" --port 18100 --output /private/tmp/nfl-explorer-http-review.json
git diff --check 5348ab117bffd01c75323a0c56466e450b522260
git log --oneline 5348ab117bffd01c75323a0c56466e450b522260..HEAD
git rev-parse HEAD
git status --short
```

281 testes/28 arquivos, cinco expected-failure intactos, lint e quatro builds passaram. [Provas](checks/preservation.json) incluem fontes/cópias, igualdade HTTP e hashes JS/CSS públicos. Testes novos exigem variável QA para ensaios reais; sem ela, os casos reais ficam explicitamente skipped.

## Capturas

[Referência terceiras1440](evidence/before-third-1440.jpg) · [Referência red zone1280](evidence/before-redzone-1280.jpg) · [Explorador1440](evidence/explorer-third-1440.jpg) · [Comparação1440](evidence/comparison-1440.jpg) · [390](evidence/explorer-third-390.jpg) · [320](evidence/explorer-third-320.jpg) · [Comparação390](evidence/comparison-390.jpg) · [Comparação320](evidence/comparison-320.jpg) · [Sobreposição](evidence/overlap-320.jpg) · [Incompatíveis](evidence/incompatible-320.jpg) · [Texto200%320](evidence/third-320-text200.jpg) · [Comparação200%320](evidence/comparison-320-text200.jpg) · [Zero](evidence/zero-1440.jpg) · [Ausência](evidence/absent-1440.jpg) · [Registro DOM/URL](evidence/browser.json).

Comparação é descritiva, limitada a dois recortes, sem cruzamento distância×tipo. Dados somente2026 REG W1–2; outras semanas permanecem sem fonte. A posição da comparação e a extensão do aprofundamento continuam abertas à avaliação. Não houve validação humana nem comprovação de ganho de esforço/compreensão.
