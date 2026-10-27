# Curva suave e eventos no gráfico · v2

[Abrir DAL × PHI](http://127.0.0.1:18111/?view=matchup-season&game=2026_07_DAL_PHI#mr-redzone) · [CIN × BAL](http://127.0.0.1:18111/?view=matchup-season&game=2026_07_CIN_BAL#mr-redzone) · [Referência 18110](http://127.0.0.1:18110/?view=matchup-season&game=2026_07_DAL_PHI#mr-redzone).

O gráfico usa Recharts 3.10.1, já instalado, com curva monotônica, áreas nas cores dos participantes e ícones selecionáveis. O painel ardósia destaca a visualização dentro da identidade existente. O placar dos marcadores vem dos registros; a linha entre eles é uma ligação visual suavizada. Não representa a pontuação mudando continuamente, EPA ou probabilidade.

A sequência por escrito começa recolhida. Touchdown, field goal e turnover podem ser consultados no próprio gráfico por mouse, toque, foco e Enter/Espaço. No celular a partida inteira cabe na tela; “Ampliar gráfico” oferece mais espaço com rolagem contida. Marcas numeradas reúnem ícones que disputariam o mesmo espaço e oferecem os eventos individuais no painel abaixo.

[Relatório e limites](REPORT.md) · [Ajuste das logos e orientação vertical](LOGO-AXES.md) · [Plano](PLAN.md).

## Teste visual curto

1. No primeiro FG de DAL, o ícone está ligado ao ponto de +3 e o painel mostra **DAL 3 × 0 PHI**. No TD + extra de PHI, mostra **3 × 7** e a curva passa para o lado de PHI.
2. No turnover de PHI do último quarto, o placar permanece **31 × 21**, sem salto artificial. O ícone de mudança de posse aparece na curva.
3. Abra “Ver sequência por escrito” somente se quiser a lista completa; feche por clique ou Enter. Os números e a curva não mudam.
4. Em 390/320 px, consulte uma marca numerada e escolha seus eventos. “Ampliar gráfico” separa melhor os marcadores, sem causar rolagem horizontal da página. “Ajustar à tela” retorna à visão completa.
5. [Prorrogação BAL × ATL](http://127.0.0.1:18111/?view=matchup-season&game=2026_05_BAL_ATL#mr-redzone): filtre OT; começa 23 × 23. [ATL × PIT](http://127.0.0.1:18111/?view=matchup-season&game=2026_01_ATL_PIT#mr-redzone) mostra um TD defensivo ligado à interceptação. [CHI × CAR](http://127.0.0.1:18111/?view=matchup-season&game=2026_01_CHI_CAR#mr-redzone) inclui fumble em retorno de punt.

## Operação

Worktree `/Users/pedrocollet/.codex/worktrees/broadcast-score-curve-v2/NFL Sideline`, branch `codex/broadcast-score-curve-v2`.
Servidor: **127.0.0.1:18111 / PID 83042**, strictPort, somente loopback. Confirme o PID/porta antes de encerrar:

```bash
cd '/Users/pedrocollet/.codex/worktrees/broadcast-score-curve-v2/NFL Sideline'
./docs/plans/broadcast-score-curve-v2/run-local.sh
# Ctrl+C encerra uma execução em foreground.
# Encerrar somente a instância deixada nesta entrega:
lsof -nP -a -p 83042 -iTCP:18111 -sTCP:LISTEN && kill -TERM 83042
```

O script recebe três configurações explícitas para a coleção original, a cronologia e os turnovers adicionais. Todas apontam para cópias dentro do novo pacote físico. Não usa `.env`, banco, Gemini ou instalação de bibliotecas. A porta ocupada produz falha, sem escolher outra porta ou encerrar processos.

## Fonte complementar e reprodução

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-score-curve-v2/20261027-v1/` contém `bundle`, `verified-copy` e `reproduced-from-copy`, com **151 arquivos e os mesmos bytes**. Os pins e bytes dos pacotes anteriores permanecem intactos.

- Novo pin: `sha256:86fd64d2e3ac628cf8a99ca1befe95d4528e8cf7acba1f4937235fe9fb3f7ecd`.
- Fonte cronológica: `sha256:93b6cad3ea3a1db822c16e4bfdadf70f28122e2dd60002708d44745776129624`.
- Coleção W1–7: `sha256:77af196874e984bfa85a270da8733073f97836e959b6dd3d2cd2ec8a98bc7a0c`.

```bash
export PYTHONPATH=etl-pipeline/src PYTHONDONTWRITEBYTECODE=1
PY='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-score-curve-v2/20261027-v1/bundle'
export NFL_CURVE_QA_BUNDLE="$BUNDLE"
export NFL_STORY_QA_BUNDLE="$BUNDLE/source"
"$PY" -B -m nfl_sideline_etl.score_curve verify --source "$BUNDLE"
# Com 18111 ativo: bytes HTTP, fonte e recuperação completa:
"$PY" -B docs/plans/broadcast-score-curve-v2/verify.py --recovery
"$PY" -B -m pytest -q etl-pipeline/tests/test_score_curve.py etl-pipeline/tests/test_game_story.py -p no:cacheprovider
npm --prefix web-ui test -- broadcast-journey/score-curve/curve.test.tsx broadcast-journey/game-story/story.test.tsx
node web-ui/node_modules/typescript/bin/tsc -p web-ui/tsconfig.season.json
npm --prefix web-ui run lint
node web-ui/node_modules/vite/bin/vite.js build --config web-ui/vite.curve.config.ts
npm --prefix web-ui run build
python3 docs/plans/broadcast-score-curve-v2/check-isolation.py
```

A suíte frontend completa foi executada com todas as fixtures privadas anteriores configuradas, além da nova. Logs e provas em `checks/` e `evidence/`. Não houve merge, push, deploy, publicação ou nova pesquisa humana.
