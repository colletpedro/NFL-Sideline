# NFL Sideline · hub semanal e leituras diretas

Base exata `30140bee6af3eb02d00fb4b624399c1ff6e88f3d`. Branch `codex/broadcast-live-hub-v1`, worktree isolada gerenciada. Sem merge/push/deploy.

- [Hub · semana 1](http://127.0.0.1:18097/?season=2026&week=1).
- [Semana 2](http://127.0.0.1:18097/?season=2026&week=2).
- [NYJ · ataque/passe imediato](http://127.0.0.1:18097/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&play=classified_pass).
- [Lacuna BAL W3](http://127.0.0.1:18097/?season=2026&week=3&game=2026_03_BAL_DAL&team=BAL).
- [Versão anterior preservada](http://127.0.0.1:18096/?season=2026&week=1).

O calendário oferece semanas 1–18. As leituras individuais reais continuam restritas a W1–2, além da lacuna BAL W3 e do histórico separado de NE. Mostrar uma semana não cria PBP nem atualiza placares.

## Operação

Instância própria: Node PID **5687**, somente `127.0.0.1:18097`, porta estrita. Confira antes de encerrar. A instância anterior em 18096 permanece independente.

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-live-hub-v1/NFL Sideline'
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export NFL_OBSERVATION_CONFIG="$PWD/docs/plans/broadcast-live-hub-v1/lab-config.json"
export NFL_LOCAL_JOURNEY_PORT=18097
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:dev
# Somente para encerrar a instância identificada desta entrega:
lsof -nP -a -p 5687 -iTCP:18097 -sTCP:LISTEN && kill -TERM 5687
```

Não iniciar outra instância se a porta estiver ocupada. Ctrl+C encerra uma instância iniciada no próprio terminal.

A config fixa o bundle aceito da expansão, ainda localizado na worktree `broadcast-w12-expansion-v1`. Não houve nova geração, cópia ou aquisição de dados. Preserve essa raiz enquanto a config a referenciar. O acervo grande permanece ignorado no Git; os dados e as duas cópias da recuperação anterior continuam intactos.

## Checks

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
python3 -B docs/plans/broadcast-live-hub-v1/verify-isolation.py
"$NFL_OBSERVATION_PYTHON" -B docs/plans/broadcast-w12-expansion-v1/verify_http.py --config "$NFL_OBSERVATION_CONFIG" --port 18097 --output /private/tmp/nfl-live-hub-http-review.json
git diff --check 30140bee6af3eb02d00fb4b624399c1ff6e88f3d
```

## Reprodução de uso

1. Abra o hub sem busca: conte 18 semanas e os 16 jogos de W1. Escolha W2 e W18 sem abrir lista ou menu.
2. Digite `b`: quatro sugestões surgem antes de Enter. Teste ArrowDown/ArrowUp, Enter, Escape e clique. Nomes, cidades, aliases e siglas são normalizados; a sugestão representa um confronto existente.
3. Abra NYJ–TEN, selecione NYJ/ataque/passe e depois corrida e defesa. Os números mudam imediatamente; não existe botão Abrir leitura. Troque o participante e o período. Confira URL, recarga, voltar/avançar e retorno à busca.
4. Abra BAL W3: nenhuma contagem ou taxa é fabricada. Use um ID nominal inexistente: o alerta aparece sem substituir por outro documento. Observe a diferença entre Deste jogo e Semanas 1–2.
5. Confira 1440, 390, 320 e texto ampliado. As capturas e medições desta sessão estão em evidence/. Não foi realizado estudo de compreensão ou toque em dispositivo físico.

[Relatório](REPORT.md) · [Prova do navegador](evidence/browser.json) · [HTTP](checks/http.json) · [Isolamento](checks/isolation.json).
