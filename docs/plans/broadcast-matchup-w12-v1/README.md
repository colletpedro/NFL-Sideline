# Entrega 4/5 · leitura comparativa W1–2

Os **32 confrontos / 64 produções ofensivas** de 2026 REG W1–2 abrem diretamente com dados próprios, duas produções juntas e a estrutura vertical aprovada. O calendário reutiliza o componente existente, com destinos diretos. Sem seletores obrigatórios, dados novos de rede, banco, credenciais, Gemini, merge, push ou deploy.

- [Calendário W1](http://127.0.0.1:18104/?season=2026&week=1) · [W2](http://127.0.0.1:18104/?season=2026&week=2).
- [NYJ × TEN W1](http://127.0.0.1:18104/?view=matchup-w12&game=2026_01_NYJ_TEN): TEN 1 TD / 1 campanha, 100%, sem inferir estabilidade.
- [JAX × DEN W2](http://127.0.0.1:18104/?view=matchup-w12&game=2026_02_JAX_DEN): outro jogo/semana, nomes longos e referência W2.
- [ATL × PIT W1](http://127.0.0.1:18104/?view=matchup-w12&game=2026_01_ATL_PIT) e [CAR × ATL W2](http://127.0.0.1:18104/?view=matchup-w12&game=2026_02_CAR_ATL): ATL sem oportunidades de red zone, 0/0 **sem taxa**, preservando o dado válido do adversário.
- [Referência refinada 18103](http://127.0.0.1:18103/?view=matchup-reading) preservada. Para NYJ/TEN, seis EPA/populações, 22 terceiras, quatro campanhas, pontos/taxa conjunta W1 e mercado são iguais; mudam contrato, fatos genéricos, calendário, temporalidade e URLs. [Comparação exata](checks/reference-comparison.json).
- Entradas anteriores nesta instância: [piloto](http://127.0.0.1:18104/?view=matchup-reading), [explorador](http://127.0.0.1:18104/?view=explorer&season=2026&week=1), [percurso anterior](http://127.0.0.1:18104/?view=legacy&season=2026&week=1).

[Plano prévio](PLAN.md) · [inventário inicial](inventory.json) · [matriz final](MATRIX.md) · [contrato](CONTRACT.md) · [política](POLICY.md) · [relatório](REPORT.md) · [passagem 5/5](HANDOFF-5-OF-5.md).

## Operação local

Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/broadcast-matchup-w12-v1/NFL Sideline`; branch `codex/broadcast-matchup-w12-v1`. Base exata limpa `d82d4a6eafb85acb3cd9c94736a2160a4036281f`. Commits locais separados para plano, coleção, interface e evidências/documentação. HEAD final consultável por `git rev-parse HEAD` e informado no chat, sem autorreferência neste documento.

Instância própria ativa: **127.0.0.1:18104, strictPort, PID 57181**. Log/PID duráveis: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-matchup-w12-v1/20261024-v1/server.log` e `server.pid`. O servidor inicial próprio 49178 foi encerrado de forma direcionada para esta inicialização durável; os seis servidores anteriores permanecem nos mesmos PIDs. Uma segunda inicialização foi recusada com `Port 18104 is already in use`, sem encerrar o listener ativo. [Recibo](checks/server.json), [strictPort](checks/strict-port.log), [isolamento](checks/isolation.json).

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-matchup-w12-v1/NFL Sideline'
# Executar só após encerrar a instância própria ativa; Ctrl+C encerra o foreground.
./docs/plans/broadcast-matchup-w12-v1/run-local.sh
# Encerramento direcionado da instância deixada por esta entrega:
lsof -nP -a -p 57181 -iTCP:18104 -sTCP:LISTEN && kill -TERM 57181
```

O script fornece configurações e Python explicitamente, não instala nada e não carrega .env. Dependências já locais: Python 3.11.13 e Node observado v26.0.0; node_modules é o symlink explícito para `/Users/pedrocollet/Downloads/NFL Sideline/web-ui/node_modules`. Não depende de node_modules de outra worktree. Em outro checkout, preparar dependências conforme AGENTS.md antes de iniciar.

## Artefato e recuperação

Raiz durável fora das worktrees: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-matchup-w12-v1/20261024-v1`.

- Operacional imutável: `bundle-final/`.
- Recuperação física verificada: `verified-final-copy/`.
- Reprodução integral a partir da recuperação, com origens bloqueadas em processo novo: `reproduced-final-bundle/`.
- Três árvores finais idênticas, **50 arquivos cada**, com índice, 32 documentos e fontes completas. Índice/manifesto versionados aqui; dados privados nunca copiados para public/data.
- Pin final: `sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc`.
- `bundle/`, `bundle-reconciled/`, `verified-copy/` e `reproduced-bundle/` preservam candidatas internas anteriores desta sessão, não são operacionais nem fallback. Seus pins não são o pin final.

[Prova da cópia](checks/final-copy-check.json) e [recuperação independente](checks/final-recovery-check.json). As cópias são no mesmo disco; a prova não demonstra proteção contra perda física do disco. Código de reprodução está nos commits locais e pode ser aberto em outro checkout da branch; o pacote não exige sobrevivência desta worktree ou de processo anterior. Recibos históricos dentro das fontes não são paths de leitura obrigatórios.

```sh
export NFL_W12_PY='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export PYTHONPATH="$PWD/etl-pipeline/src"
export PYTHONDONTWRITEBYTECODE=1
export NFL_W12_ART='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-matchup-w12-v1/20261024-v1'
"$NFL_W12_PY" -B -m nfl_sideline_etl.matchup_w12 validate --bundle "$NFL_W12_ART/bundle-final" --expected-pin 'sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc'
"$NFL_W12_PY" -B -m nfl_sideline_etl.matchup_w12 validate --bundle "$NFL_W12_ART/verified-final-copy" --expected-pin 'sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc'
# Destino novo, absoluto e disjunto; recusa sobrescrever.
"$NFL_W12_PY" -B -m nfl_sideline_etl.matchup_w12 reproduce --bundle "$NFL_W12_ART/verified-final-copy" --output "$NFL_W12_ART/reproduction-review-new"
# Prova com acesso às origens bloqueado; usar outro destino novo:
"$NFL_W12_PY" -B docs/plans/broadcast-matchup-w12-v1/verify_recovery.py --recovery "$NFL_W12_ART/verified-final-copy" --output "$NFL_W12_ART/recovery-review-new" --report "$NFL_W12_ART/recovery-review-new.json"
```

Para reoperar a recuperação depois de encerrar o listener próprio, escolher explicitamente a config com o mesmo pin, sem fallback:

```sh
NFL_W12_CONFIG="$PWD/docs/plans/broadcast-matchup-w12-v1/recovery-source-config.json" ./docs/plans/broadcast-matchup-w12-v1/run-local.sh
```

Regeneração desde as fontes congeladas do piloto, em destino novo:

```sh
"$NFL_W12_PY" -B -m nfl_sideline_etl.matchup_w12 generate --pilot '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled' --policy docs/plans/broadcast-matchup-w12-v1/POLICY.md --output "$NFL_W12_ART/regeneration-review-new"
```

O reader anterior verifica o pin nominal do piloto para ler suas cópias completas. A autorização dos outros jogos é do pedido/política/contrato/índice novos, não do pin do piloto.

## Checks reproduzíveis

```sh
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
export NFL_W12_QA_BUNDLE="$NFL_W12_ART/bundle-final"
export NFL_MATCHUP_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled'
export NFL_COMPARISON_QA_BUNDLE="$NFL_MATCHUP_QA_BUNDLE"
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
"$NFL_W12_PY" -B docs/plans/broadcast-matchup-w12-v1/reconcile.py --bundle "$NFL_W12_ART/bundle-final" --output /private/tmp/w12-reconciliation-review.json
"$NFL_W12_PY" -B -m pytest -p no:cacheprovider -q etl-pipeline
npm --prefix web-ui test
npm --prefix web-ui run lint
web-ui/node_modules/.bin/tsc -p web-ui/tsconfig.journey.json
web-ui/node_modules/.bin/tsc -p web-ui/tsconfig.matchup.json
web-ui/node_modules/.bin/tsc -p web-ui/tsconfig.w12.json
npm --prefix web-ui run journey:build
web-ui/node_modules/.bin/vite build --config web-ui/vite.matchup.config.ts
web-ui/node_modules/.bin/vite build --config web-ui/vite.w12.config.ts
npm --prefix web-ui run real:build
npm --prefix web-ui run experience:build
npm --prefix web-ui run build
"$NFL_W12_PY" -B docs/plans/broadcast-matchup-w12-v1/verify_http.py
"$NFL_W12_PY" -B docs/plans/broadcast-matchup-w12-v1/verify_isolation.py
git diff --check d82d4a6eafb85acb3cd9c94736a2160a4036281f
git log --oneline d82d4a6eafb85acb3cd9c94736a2160a4036281f..HEAD
git status --short
```

Testes reais ficam explicitamente skipped sem as variáveis QA; os logs desta entrega usam as fontes reais. O verificador de isolamento é local e pressupõe as seis referências preservadas ativas. Após o ajuste final de metadados, os 18 testes Python pertinentes, 302 frontend, lint, TypeScript, build W12 e HTTP foram reconferidos. Sem alteração Java/banco/ETL de publicação, não se executaram Maven ou comandos que precisam de credenciais.
