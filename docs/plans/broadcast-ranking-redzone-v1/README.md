# Classificação compacta e campanhas de red zone

Base conferida: f144a685db633d95692a0225a572d0b01878b00d, branch codex/broadcast-reading-polish-v1, árvore limpa. Referência 18106 preservada. Nova decisão direta do usuário: posições descritivas, participantes na abertura, expansão fluida e ícones. Sem nova avaliação humana.

## Plano antes da edição

- Entrada própria 18107, loopback/strictPort, mesmos cinco readers e configurações de operador. Reutilizar Route/páginas, acabamento anterior e snapshot. Contexto opt-in adicional, false por padrão, preserva consumidores anteriores.
- Referência compacta: visitante/casa com posição da amostra completa, logo/sigla, taxa/razão e eixo 0–100%. Botão fixo acima da expansão; lista completa em grid de altura animada (220 ms) e opacidade, sem animação por linha. aria-expanded/controls, região recolhida inert/aria-hidden; redução de movimento sem transição. Sem botão inferior para evitar perda de foco.
- Regra versionada em PRESENTATION-RULE.md. Ordenar razões exatas e atribuir posições compartilhadas. Não tocar pacotes/políticas antigas. Conferir permissões antes da apresentação.
- Campanhas: símbolo SVG compartilhado entre legenda e marcas, rótulo e campanha/semana; alvo confortável sem cartão permanente. TD/bola, FG/traves, turnover/seta de retorno; símbolos/rótulos distintos para os demais desfechos. Preservar handlers, IDs, ordem, evidências e uma marca/unidade.
- Tokens preservados: ardósia #18232B, papel #D6E1E6, tinta #15232C, grafite #263C48, foco #17628D. Archivo para leitura, Roboto Condensed para resultados. Não criar ativos, dependências, novos controles analíticos ou população EPA.

Composição: identidade+posição à esquerda, eixo comum ao centro, taxa/razão à direita. Nos ícones, símbolo é o assunto e texto resolve significado; não depender de adivinhar formas. A interação acrescenta profundidade sem mudar a leitura vertical ou esconder os dois ataques.

## Inventário anterior à implementação

208 campanhas únicas: TOUCHDOWN 124; FIELD_GOAL 52; DOWNS 15; TURNOVER 8; END_HALF_GAME 7; MISSED_FIELD_GOAL 2. OPPONENT_TOUCHDOWN, PUNT e SAFETY não ocorrem neste pacote, mas terão mapeamento explícito testado. Não serão inseridos dados sintéticos na aplicação.

Fonte durável imutável: /Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle.
Pin sha256:8971d767b6ec0557465aeb65aeb00533fd10255a62f4b916954b3854daa15cef; coleção incorporada source/matchups pin sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc. Não haverá geração ou modificação dos bytes.

Antes: capturas NE × SEA de liga completa e cartões de campanhas em captures/before-*. Verificação planejada: posições por contagem independente de taxas maiores, inventário integral/duplicação só visual, campanhas antes/depois, transporte/hash/público, testes/lint/TypeScript/builds e navegador 1440/390/320/200%, transições reais/reversão rápida/resize/reduced motion.

## Operação e verificação

Servidor próprio **127.0.0.1:18107**, PID **64656**, strictPort. Referência 18106/PID 25458 e demais servidores preservados. Encerramento direcionado: `kill -TERM 64656` (reconfira o PID antes de operar em outra sessão).

```sh
cd "/Users/pedrocollet/.codex/worktrees/broadcast-ranking-redzone-v1/NFL Sideline"
sh docs/plans/broadcast-ranking-redzone-v1/run-local.sh
lsof -nP -iTCP:18107 -sTCP:LISTEN
python3 docs/plans/broadcast-ranking-redzone-v1/check-representation.py
python3 docs/plans/broadcast-ranking-redzone-v1/check-http.py
python3 docs/plans/broadcast-ranking-redzone-v1/check-builds.py
python3 docs/plans/broadcast-ranking-redzone-v1/verify-isolation.py
```

O startup escolhe configurações de operador existentes para os pacotes duráveis e valida antes de servir. Todos os cinco readers usam 18107. Não existe path/fonte escolhido por browser. Cache Vite isolado em node_modules/.vite-broadcast-ranking-redzone-v1; build privada ranking-redzone-dist, sem copiar dados privados para public/data.

Testes reais, na raiz:

```sh
export NFL_TEAM_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle'
export NFL_W12_QA_BUNDLE="$NFL_TEAM_QA_BUNDLE/source/matchups"
export NFL_MATCHUP_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled'
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
npm --prefix web-ui test
PYTHONPATH="$PWD/etl-pipeline/src" '/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -m pytest -q etl-pipeline/tests/test_team_w12.py -k 'real_package_reader_integrity or zero_opportunities or unavailable_component or missing_component'
```

Links: [NE × SEA](http://127.0.0.1:18107/?view=matchup-w12&game=2026_01_NE_SEA), [NYJ × TEN](http://127.0.0.1:18107/?view=matchup-w12&game=2026_01_NYJ_TEN), [ATL × PIT sem taxa](http://127.0.0.1:18107/?view=matchup-w12&game=2026_01_ATL_PIT#mr-redzone), [time NYJ](http://127.0.0.1:18107/?view=team-w12&team=NYJ&season=2026&returnWeek=1#team-redzone), [time ATL](http://127.0.0.1:18107/?view=team-w12&team=ATL&season=2026&returnWeek=2#team-redzone), [referência preservada](http://127.0.0.1:18106/?season=2026&week=1).

[Relatório e limites](REPORT.md), [regra de posição versionada](PRESENTATION-RULE.md). Branch codex/broadcast-ranking-redzone-v1; commits locais e HEAD final informados no fechamento e consultáveis por Git. Sem promoção automática.
