# Hub semanal e página do time · entrega 5/5

Integração local concluída para **2026 REG W1–2**: hub → confronto → time → jogos componentes → retorno. Não é publicação, cobertura de temporada completa nem validação ampla com usuários.

## Abrir

- [Hub W1](http://127.0.0.1:18105/?season=2026&week=1)
- [Hub W2](http://127.0.0.1:18105/?season=2026&week=2)
- [NYJ, W1–2, retorno à W1](http://127.0.0.1:18105/?view=team-w12&team=NYJ&season=2026&returnWeek=1)
- [ATL: zero campanhas elegíveis em ambas as semanas](http://127.0.0.1:18105/?view=team-w12&team=ATL&season=2026&returnWeek=2#team-redzone)
- [GB × NYJ, jogo W2 do time, retorno à W1](http://127.0.0.1:18105/?view=matchup-w12&game=2026_02_GB_NYJ&season=2026&week=2&returnWeek=1)
- [Referência 4/5 preservada](http://127.0.0.1:18104/?season=2026&week=1)

Convenção: hub `/?season=2026&week=1|2`; confronto `/?view=matchup-w12&game=ID`; time `/?view=team-w12&team=SIGLA&season=2026`. Time sempre W1–2; confronto sempre sua semana. `returnWeek`, `q`, `scope`, `filter` e `page` acompanham o percurso, sem mudar os dados. IDs mistos, desconhecidos, fase/temporada/semana incompatíveis ou repetidos recebem erro explícito. Não há parâmetro de transporte/fonte.

Todos os 16 jogos de cada semana ficam acessíveis sem busca. Destaque = primeiro por data, desempate por ID; dois apoios seguintes e 13 compactos. Hierarquia de apresentação, sem importância esportiva inferida. Busca existente distingue Time/Partida desde a primeira letra e preserva Escape, setas, Enter e o destino selecionado. Diretório oferece os 32 times. “Ver confronto” e “Ver time” são links separados.

A página do time abre preenchida: identidade e W1–2 → síntese factual → EPA nas duas perspectivas → terceiras → red zone → dois jogos componentes → método recolhido. “Adversários contra TIME” descreve produção ofensiva real dos adversários; não soma outra amostra nem produz nota de qualidade. Controle de fundamento só altera EPA. Razões, marcas reais, regras, denominadores e originais ficam consultáveis. Sem nova referência agregada da liga, ranking ou previsão.

## Fontes duráveis

Raiz nova, fora de worktrees:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1`

| Destino | Função |
| --- | --- |
| `bundle/` | Operacional; 87 arquivos físicos, índice e 32 times |
| `verified-copy/` | Cópia física verificada, inodes distintos |
| `reproduced-from-recovery/` | Reprodução exata a partir da cópia, com origens históricas bloqueadas |

**Pin novo:** `sha256:8971d767b6ec0557465aeb65aeb00533fd10255a62f4b916954b3854daa15cef`.

Cada árvore inclui fisicamente a coleção 4/5 inteira em `source/matchups/`, pin preservado `sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc`. Ali estão os 32 confrontos, calendários, PBP, ledger, originais EPA e situacionais W1–2, definições/política. Não depende do servidor 18104 nem de sua worktree. Caminhos históricos dentro da procedência não são dependências de leitura. Não há fallback automático para cópias.

[Contrato](CONTRACT.md), [política de agregação](POLICY.md), [matriz dos 32 times](MATRIX.md), [reconciliação independente](checks/reconciliation.json), [recuperação](checks/recovery.json), [relatório e limites](REPORT.md), [plano anterior à geração](PLAN.md).

## Operar

Worktree: `/Users/pedrocollet/.codex/worktrees/broadcast-hub-team-w12-v1/NFL Sideline`.

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-hub-team-w12-v1/NFL Sideline'
sh docs/plans/broadcast-hub-team-w12-v1/run-local.sh
```

Configurações explícitas do operador: `team-source-config.json` e `matchup-source-config.json`, ambas usando a raiz nova durável. Script configura coerentemente todos os readers para 18105, sem carregar `.env`. Validação completa no startup; bytes congelados, loopback, strictPort, Host/Origin/método/marcador/pin/corpo/caminho estritos. Índice GET `/__team-w12/`, documentos `/__team-w12/NYJ`; requer `X-Local-Team-W12: 1` e `X-Team-Collection: PIN`. Fonte inválida recebe 503; pin de cliente desatualizado 409; time desconhecido 404; transporte recusado 403. Sem paths de arquivo fornecidos pelo browser.

Servidor entregue: **PID 59966**, `127.0.0.1:18105`. Log/PID na raiz durável (`server.log`, `server.pid`). Encerrar somente essa instância, após conferir o listener:

```sh
lsof -nP -a -p 59966 -iTCP:18105 -sTCP:LISTEN
kill -TERM 59966
```

Não executar o encerramento para avaliar a entrega. Preservados 18098, 18099, 18100, 18101, 18102, 18103 e 18104. Calendário anterior, explorador, percurso e piloto continuam como entradas secundárias na própria instância.

## Reproduzir e conferir

```sh
export PYTHONPATH="$PWD/etl-pipeline/src"
export NFL_TEAM_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle'
export NFL_W12_QA_BUNDLE="$NFL_TEAM_QA_BUNDLE/source/matchups"
export NFL_MATCHUP_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled'
export NFL_COMPARISON_QA_BUNDLE="$NFL_MATCHUP_QA_BUNDLE"
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
export NFL_TEAM_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
"$NFL_TEAM_PYTHON" -B -m nfl_sideline_etl.team_w12 validate --bundle "$NFL_TEAM_QA_BUNDLE" --expected-pin 'sha256:8971d767b6ec0557465aeb65aeb00533fd10255a62f4b916954b3854daa15cef'
"$NFL_TEAM_PYTHON" -B docs/plans/broadcast-hub-team-w12-v1/reconcile.py --bundle "$NFL_TEAM_QA_BUNDLE" --output /tmp/team-reconciliation.json
"$NFL_TEAM_PYTHON" -B -m pytest -p no:cacheprovider -q etl-pipeline/tests/test_team_w12.py etl-pipeline/tests/test_matchup_w12.py etl-pipeline/tests/test_comparison_foundation.py etl-pipeline/tests/test_situational.py etl-pipeline/tests/test_metrics_observations.py
npm --prefix web-ui test
npm --prefix web-ui run lint
web-ui/node_modules/.bin/tsc -p web-ui/tsconfig.journey.json
web-ui/node_modules/.bin/tsc -p web-ui/tsconfig.hub-team.json
web-ui/node_modules/.bin/vite build --config web-ui/vite.hub-team.config.ts
python3 docs/plans/broadcast-hub-team-w12-v1/check-http.py
python3 docs/plans/broadcast-hub-team-w12-v1/verify-isolation.py
```

Reprodução exige destino **novo e disjunto**, passado em `--output`, sem sobrescrita:

```sh
"$NFL_TEAM_PYTHON" -B -m nfl_sideline_etl.team_w12 reproduce --bundle "$NFL_TEAM_QA_BUNDLE" --output /tmp/nfl-team-new-reproduction
```

Geração nominal: `team_w12 generate --source CAMINHO_DA_COLECAO_W12 --policy docs/plans/broadcast-hub-team-w12-v1/POLICY.md --output DESTINO_NOVO`. Não reutilizar pins para conteúdo novo. A cópia recuperada pode ser escolhida explicitamente na configuração do operador após validar seu pin; o browser nunca escolhe arquivos.

As entradas secundárias conservam dependências duráveis existentes, distintas da fonte principal autocontida: piloto em `broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled` (pin `b10a2028…e5ee4`), observações completas em seu `sources/observations` (pin `05541d27…56876a`) e situacional em `broadcast-situational-w12-v1/20261023-v1/bundle-reconciled` (pin `2af2a332…339c`), todos sob `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/`. Os pins completos estão nas configurações preservadas referenciadas pelo script. Nenhuma dessas entradas depende de uma worktree histórica.
