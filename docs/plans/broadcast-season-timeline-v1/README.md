# Temporada e cronologia do placar

Versão local em **http://127.0.0.1:18110/**. Base exata `8f05138502f51bd80cf8299a687d8dfdeb32c50a`, preservada em 18109.

- [DAL × PHI: curva do placar e campanhas](http://127.0.0.1:18110/?view=matchup-season&game=2026_07_DAL_PHI#mr-redzone).
- [CIN × BAL: classificação acumulada por padrão](http://127.0.0.1:18110/?view=matchup-season&game=2026_07_CIN_BAL#mr-redzone).
- [Somente W7, por escolha explícita](http://127.0.0.1:18110/?view=matchup-season&game=2026_07_CIN_BAL&rank=week#mr-redzone).
- [BAL × ATL: prorrogação](http://127.0.0.1:18110/?view=matchup-season&game=2026_05_BAL_ATL#mr-redzone).
- [NE × CHI: turnover sem alteração do placar](http://127.0.0.1:18110/?view=matchup-season&game=2026_07_NE_CHI#mr-redzone).
- [LV × LAC: safety](http://127.0.0.1:18110/?view=matchup-season&game=2026_02_LV_LAC#mr-redzone).
- [TB × CAR: retorno defensivo em conversão](http://127.0.0.1:18110/?view=matchup-season&game=2026_07_TB_CAR#mr-redzone).

[Relatório](REPORT.md) · [Regras e limites](RULES.md) · [Plano anterior à implementação](PLAN.md).

## O que avaliar

1. Em CIN × BAL, a classificação começa em W1–7. Ligue “Somente W7”: as posições, razões e universo mudam para aquela semana; as taxas do confronto permanecem iguais. Expanda/recolha a lista. A posição do controle permanece estável. Recarregue e use voltar/avançar.
2. Em DAL × PHI, o primeiro FG leva a vantagem de DAL a +3; o TD de PHI e o extra levam a −3 e −4. Na lista, esses dois registros aparecem como TD + extra, com ambos os valores e relógios. Selecione esse momento para destacar o ponto na curva.
3. Filtre o primeiro quarto: o placar ao fim do recorte é DAL 10 × 7 PHI. Os percentuais de red zone continuam do jogo inteiro. Na prorrogação de BAL × ATL, o recorte começa 23 × 23.
4. Em NE × CHI, o turnover de NE conserva 7 × 13. No outro exemplo, o retorno defensivo de TB vale dois pontos para TB, separado do TD de CAR.
5. Confira no celular e pelo teclado: nome do time, relógio, pontuação e condição de red zone não dependem apenas da cor ou do ícone. A tabela e as evidências ficam no expansível ao final da cronologia.

## Operação

Worktree: `/Users/pedrocollet/.codex/worktrees/broadcast-season-timeline-v1/NFL Sideline`.
Branch: `codex/broadcast-season-timeline-v1`.
Servidor desta entrega: **PID 80609**, host `127.0.0.1`, porta estrita **18110**. O PID vale para esta execução; confira a porta antes de encerrar.

```bash
cd '/Users/pedrocollet/.codex/worktrees/broadcast-season-timeline-v1/NFL Sideline'
./docs/plans/broadcast-season-timeline-v1/run-local.sh
# Em foreground, Ctrl+C encerra apenas essa execução.
# Para encerrar a instância deixada nesta entrega:
lsof -nP -a -p 80609 -iTCP:18110 -sTCP:LISTEN && kill -TERM 80609
```

O script não instala dependências, não lê `.env`, não usa banco/Gemini e não mata servidores existentes. `web-ui/node_modules` é um symlink local ignorado para as dependências já instaladas. Se a porta estiver ocupada, `strictPort` falha sem escolher outra porta.

As duas configurações são explícitas: `source-config.json` aponta o complemento; `source-season-config.json` aponta a cópia W1–7 contida **dentro** dele. A execução não depende da worktree 18109. O cliente continua validando a coleção anterior e o complemento separadamente.

## Artefato durável e reprodução

Diretório físico: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-season-timeline-v1/20261027-v1/`.

- `bundle/`: complemento + fonte W1–7 integral em `source/`.
- `verified-copy/`: cópia física verificada, 149 arquivos com os mesmos bytes.
- `reproduced-from-copy/`: regeneração integral a partir dessa cópia, também byte a byte idêntica.
- Pin próprio: `sha256:93b6cad3ea3a1db822c16e4bfdadf70f28122e2dd60002708d44745776129624`.
- Pin da fonte W1–7, inalterado: `sha256:77af196874e984bfa85a270da8733073f97836e959b6dd3d2cd2ec8a98bc7a0c`.

```bash
export PYTHONPATH=etl-pipeline/src PYTHONDONTWRITEBYTECODE=1
PY='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-season-timeline-v1/20261027-v1/bundle'
"$PY" -B -m nfl_sideline_etl.game_story verify --source "$BUNDLE"
# Use um destino novo; o comando recusa sobrescrita:
"$PY" -B -m nfl_sideline_etl.game_story reproduce --source "$BUNDLE" --output /tmp/nfl-game-story-reproduction
# Com 18110 ativo: conferência HTTP, das campanhas e dos placares:
"$PY" -B docs/plans/broadcast-season-timeline-v1/verify.py --recovery
```

## Verificação reproduzível

```bash
export NFL_STORY_QA_BUNDLE="$BUNDLE"
export NFL_SEASON_QA_BUNDLE="$BUNDLE/source"
"$PY" -B -m pytest -q etl-pipeline/tests/test_game_story.py etl-pipeline/tests/test_season_analysis.py -p no:cacheprovider
npm --prefix web-ui test -- broadcast-journey/game-story/story.test.tsx broadcast-journey/season/season.test.tsx
npm --prefix web-ui run lint
node web-ui/node_modules/typescript/bin/tsc -p web-ui/tsconfig.season.json
node web-ui/node_modules/typescript/bin/tsc -p web-ui/tsconfig.node.json
node web-ui/node_modules/vite/bin/vite.js build --config web-ui/vite.story.config.ts
npm --prefix web-ui run build
python3 docs/plans/broadcast-season-timeline-v1/check-isolation.py
```

A suíte frontend completa foi executada com as fixtures locais legadas configuradas, sem skips de novos testes; o registro está em `checks/frontend-full.log`. Os cinco `it.fails` legados continuam intactos. Nenhum estudo humano adicional, toque físico, merge, push, deploy ou publicação faz parte desta entrega.
