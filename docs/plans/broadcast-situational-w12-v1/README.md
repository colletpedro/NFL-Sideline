# Broadcast situacional W1–2 · versão local para avaliação

[Relatório](REPORT.md) · [Plano prévio](PLAN.md) · [Definições](DEFINITIONS.md) · [Contrato e procedência](CONTRACT.md) · [Reconciliação independente](reconciliation.json) · [Auditoria dos campos](field-audit.json).

32 jogos, 32 times, 192 documentos com terceiras descidas e red zone: por jogo W1/W2 e agregado inclusivo W1–2, ataque/defesa. Somente fonte real preservada. Sem modelos, rankings ou nova aquisição. Aceite humano pendente.

- [Hub W1](http://127.0.0.1:18098/?season=2026&week=1).
- [NYJ · terceiras W1](http://127.0.0.1:18098/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&analysis=third&reading=game).
- [NYJ · red zone W1](http://127.0.0.1:18098/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&analysis=redzone&reading=game).
- [NYJ · defesa/red zone W1–2](http://127.0.0.1:18098/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=def&analysis=redzone&reading=2026%2FREG%2F1%2C2).
- [MIN · terceiras W2, origem da busca](http://127.0.0.1:18098/?season=2026&week=2&game=2026_02_MIN_CHI&team=MIN&side=off&analysis=third&q=Minnesota&scope=season).
- [ATL · fonte presente sem oportunidade de red zone](http://127.0.0.1:18098/?season=2026&week=1&game=2026_01_ATL_PIT&team=ATL&analysis=redzone).
- [BAL W3 · fonte situacional ausente](http://127.0.0.1:18098/?season=2026&week=3&game=2026_03_BAL_DAL&team=BAL&analysis=redzone).
- [Resumo existente](http://127.0.0.1:18098/?season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&analysis=summary&play=general).

## Operação local

Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/broadcast-situational-w12-v1/NFL Sideline`. Branch `codex/broadcast-situational-w12-v1`, base exata `3f4335691c9d4d126561ed03df4b775640cae7ed`. Servidor próprio conferido: **PID 49375**, comando `node scripts/journey-dev.mjs`, somente **127.0.0.1:18098**, strictPort. Não iniciar outra instância enquanto estiver ativo.

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-situational-w12-v1/NFL Sideline'
./docs/plans/broadcast-situational-w12-v1/run-local.sh
# Encerrar somente o servidor próprio, depois de conferir o listener:
lsof -nP -a -p 49375 -iTCP:18098 -sTCP:LISTEN && kill -TERM 49375
```

O script não carrega `.env`, não instala pacotes nem libera portas. Dependências npm locais existentes foram reutilizadas. Ctrl+C encerra uma instância iniciada no próprio terminal. Nenhum servidor anterior foi encerrado; a referência 18097 já não respondia na reprodução inicial.

## Artefato durável e recuperação

Raiz fora de qualquer worktree descartável:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/`

- Operacional: `bundle-reconciled/`.
- Cópia física autocontida: `verified-copy/`.
- Recibo da verificação das fontes: `provenance.json`.
- `bundle/` é uma primeira geração de diagnóstico, anterior à correção de punt/safety. Não está configurada, não é aceita pelo cálculo final e não substitui o pacote reconciliado. Seus bytes foram preservados.

Pin operacional: `sha256:2af2a33211c09658fb6b831188dc5c5ac3bee9b3fc4b2b6008748921ac7c339c`. [Config explícita](situational-config.json) · [Prova da cópia](checks/copy.json). A cópia passou em processo novo com abertura das fontes, do bundle antigo e do principal bloqueada. Duas cópias no mesmo disco não demonstram proteção contra perda do disco. O bundle de 588 observações mantém sua config e localização originais, integralmente preservadas.

```sh
export NFL_SIT_PY='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export PYTHONPATH="$PWD/etl-pipeline/src"
export PYTHONDONTWRITEBYTECODE=1
export NFL_SIT_ART='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1'
"$NFL_SIT_PY" -B -m nfl_sideline_etl.situational validate --bundle "$NFL_SIT_ART/bundle-reconciled"
"$NFL_SIT_PY" -B -m nfl_sideline_etl.situational validate --bundle "$NFL_SIT_ART/verified-copy"
```

## Gerar e reconciliar em destino novo

Escolha uma raiz ainda inexistente. Nenhum download/banco é usado. `prepare_sources.py` confere as duas recuperações completas, rederiva materialização/input e lê o bundle aceito antes da nova geração. Um novo recibo tem outro instante de verificação e portanto outro pin; a população/contagens são as mesmas. A configuração ativa nunca é atualizada automaticamente.

```sh
export NFL_SIT_NEW='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/reproduction-new'
"$NFL_SIT_PY" -B docs/plans/broadcast-situational-w12-v1/prepare_sources.py "$NFL_SIT_NEW"
"$NFL_SIT_PY" -B -m nfl_sideline_etl.situational generate \
  --raw '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery/20261019T024130Z-50e03b27/data/raw/pbp/season=2026/pbp.parquet' \
  --provenance "$NFL_SIT_NEW/provenance.json" --output "$NFL_SIT_NEW/bundle"
"$NFL_SIT_PY" -B -m nfl_sideline_etl.situational validate --bundle "$NFL_SIT_NEW/bundle"
"$NFL_SIT_PY" -B docs/plans/broadcast-situational-w12-v1/reconcile.py \
  --bundle "$NFL_SIT_NEW/bundle" --output "$NFL_SIT_NEW/reconciliation.json"
"$NFL_SIT_PY" -B docs/plans/broadcast-situational-w12-v1/copy_verify.py \
  "$NFL_SIT_NEW/bundle" "$NFL_SIT_NEW/verified-copy" "$NFL_SIT_NEW/copy-proof.json"
```

Para usar outra raiz, crie outra config `situational-config-v1` com o caminho e o pin devolvido; configure `NFL_SITUATIONAL_CONFIG` explicitamente. Não edite os pacotes nem use latest/fallback. Os arquivos privados completos são ignorados no Git; contrato, scripts, pins, reconciliação e evidências estão versionados.

## Reproduzir verificações

```sh
"$NFL_SIT_PY" -B -m pytest -p no:cacheprovider -q etl-pipeline
export NFL_SITUATIONAL_QA_BUNDLE="$NFL_SIT_ART/bundle-reconciled"
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
"$NFL_SIT_PY" -B docs/plans/broadcast-situational-w12-v1/verify_http.py --port 18098
"$NFL_SIT_PY" -B docs/plans/broadcast-w12-expansion-v1/verify_http.py \
  --config docs/plans/broadcast-live-hub-v1/lab-config.json --port 18098 \
  --output /private/tmp/nfl-situational-legacy-http.json
python3 -B docs/plans/broadcast-situational-w12-v1/verify-isolation.py
git diff --check 3f4335691c9d4d126561ed03df4b775640cae7ed
git log --oneline 3f4335691c9d4d126561ed03df4b775640cae7ed..HEAD
git rev-parse HEAD
git status --short
```

Sem a variável QA, somente o ensaio privado real de renderização fica explicitamente pulado; os testes sintéticos continuam offline/autocontidos. Nesta entrega, a variável foi configurada e todos os 384 contextos reais foram exercitados.

No navegador: abra NYJ W1, alterne as três análises, time, lado e período; recarregue e teste voltar/avançar. Abra o hub W2, digite Minnesota, ArrowDown/Enter e retorne pelo link do calendário; a busca e a origem devem permanecer. Confira ATL 0/0 sem taxa e BAL W3 sem painel numérico. Use Tab/Enter nas análises e metodologia, viewports 1440/390/320 e fonte raiz 200% via ferramenta de desenvolvimento; restaure a fonte/recarregue ao terminar. [Evidência da sessão integrada](evidence/browser.json) e capturas abaixo documentam a execução real, sem interceptar positivos nem usar fixtures na aplicação.

[Terceiras desktop](evidence/third-1440-final.png) · [Red zone desktop](evidence/redzone-1440-final.png) · [Defesa agregada mobile](evidence/redzone-def-inclusive-390.png) · [Terceiras 320](evidence/third-320-final.png) · [Texto 200% refinado](evidence/redzone-320-text200-refined.png) · [Zero real](evidence/zero-opportunities-390.png) · [Fonte ausente](evidence/source-absent-320.png).
