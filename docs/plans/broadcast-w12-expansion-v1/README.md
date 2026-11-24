# NFL Sideline · 2026 W1–2 ampliado

Candidata ao aceite humano, pronta para avaliação local: **32 jogos, 32 times, 576 documentos da expansão** (384 individuais + 192 agregados). **588 ativos** incluindo NE POST2025 e lacuna BAL W3, sem duplicar os recortes BAL/DAL anteriores. [Relatório](REPORT.md) · [Plano prévio](PLAN.md) · [Seleção](selection.json) · [Pins](lab-config.json) · [Reconciliação](reconciliation.json).

- [Central · semana 1](http://127.0.0.1:18096/?season=2026&week=1).
- [Semana 2](http://127.0.0.1:18096/?season=2026&week=2).
- [MIN · ataque geral deste jogo W1](http://127.0.0.1:18096/?season=2026&week=1&game=2026_01_GB_MIN&team=MIN&side=off&play=general&entry=w12-expansion-v1&observation=sha256%3A34eab6d267d579885b61dc27381c7c0f5535522b4efb292bcb64eb9ca3b18363).
- [MIN · agregado W1–2 inclusivo](http://127.0.0.1:18096/?season=2026&week=1&game=2026_01_GB_MIN&team=MIN&side=off&play=general&entry=w12-expansion-v1&observation=sha256%3Afb42e6228083ea8d1aa1233c86bea4666a51fe30d4b082a2b1d51fa6bd8f1a35).
- [SF · defesa contra passe W1](http://127.0.0.1:18096/?season=2026&week=1&game=2026_01_SF_LA&team=SF&side=def&play=classified_pass&entry=w12-expansion-v1&observation=sha256%3A49d492bfedd956094f8324768027b4498f9d2c6b972420d9bc715ad93a8c888c).
- [LAC · ataque de corrida W2](http://127.0.0.1:18096/?season=2026&week=2&game=2026_02_LV_LAC&team=LAC&side=off&play=classified_rush&entry=w12-expansion-v1&observation=sha256%3A86a5c47eb61ade385712f81b680abc11cdec6bac7af1749108e4d52f832d6488).
- [BAL W3 · lacuna preservada](http://127.0.0.1:18096/?season=2026&week=3&game=2026_03_BAL_DAL&team=BAL).
- [NE · acesso ao arquivo separado POST2025](http://127.0.0.1:18096/?season=2026&week=3&game=2026_03_NE_JAX&team=NE).

## Iniciar e encerrar

Da worktree gerenciada, sem carregar .env, sem instalação:

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-w12-expansion-v1/NFL Sideline'
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export NFL_OBSERVATION_CONFIG="$PWD/docs/plans/broadcast-w12-expansion-v1/lab-config.json"
export NFL_LOCAL_JOURNEY_PORT=18096
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:dev
```

Porta estrita, bind 127.0.0.1. Uma instância já está ativa, PID **85128**. Não iniciar outra na mesma porta. Para encerrar somente esta instância, confira o listener e envie TERM:

```sh
lsof -nP -a -p 85128 -iTCP:18096 -sTCP:LISTEN && kill -TERM 85128
```

Ctrl+C encerra uma instância iniciada no próprio terminal. Não usar pkill/killall. Servidores anteriores foram preservados.

## Bundle durável e cópia verificada

```sh
NFL_ART="$PWD/editorial/local-artifacts/broadcast-w12-expansion-v1/20261022-v1"
NFL_COPY="$PWD/editorial/local-artifacts/broadcast-w12-expansion-v1/20261022-v1-portable"
export PYTHONPATH="$PWD/etl-pipeline/src"
export PYTHONDONTWRITEBYTECODE=1
"$NFL_OBSERVATION_PYTHON" -B -m nfl_sideline_etl.metrics_observations validate --bundle "$NFL_ART/bundle"
"$NFL_OBSERVATION_PYTHON" -B -m nfl_sideline_etl.metrics_observations inspect --bundle "$NFL_COPY"
```

São cópias físicas completas e autocontidas. A prova em processo novo bloqueou acesso às fontes e ao bundle principal. Não dependem de /private/tmp. A config atual aponta somente para o bundle novo principal; a cópia é prova de recuperação, não fallback silencioso. Para operar pela cópia, crie outra config externa nova com o mesmo pin e path nominal da cópia, sem editar os registros existentes.

## Gerar novamente em destino novo

Usa as duas fontes preservadas existentes; nenhum dado novo, banco ou receipt é criado. Escolha uma raiz nova; os scripts recusam sobrescrita. Este exemplo é separado da entrega ativa:

```sh
NFL_SOURCE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery/20261019T024130Z-50e03b27'
NFL_BACKUP='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/20261019T024130Z-50e03b27'
NFL_NEW="$PWD/editorial/local-artifacts/broadcast-w12-expansion-v1/reproduction-$(date -u +%Y%m%dT%H%M%SZ)"
"$NFL_OBSERVATION_PYTHON" -B docs/plans/broadcast-w12-expansion-v1/nominal_selection.py \
  --source "$NFL_SOURCE" --backup "$NFL_BACKUP" --output "$NFL_NEW"
# request.json e selection.json já existem antes deste generate:
"$NFL_OBSERVATION_PYTHON" -B -m nfl_sideline_etl.metrics_observations generate \
  --materialized "$NFL_SOURCE/materialized" --request "$NFL_NEW/request.json" --output "$NFL_NEW/bundle"
"$NFL_OBSERVATION_PYTHON" -B -m nfl_sideline_etl.metrics_observations validate --bundle "$NFL_NEW/bundle"
"$NFL_OBSERVATION_PYTHON" -B -m nfl_sideline_etl.metrics_observations inspect --bundle "$NFL_NEW/bundle"
"$NFL_OBSERVATION_PYTHON" -B docs/plans/broadcast-w12-expansion-v1/reconcile.py --artifacts "$NFL_NEW"
```

reconcile.py cria `<nome-da-raiz>-portable` ao lado da raiz nova, copia o bundle completo, verifica por reader em processo separado e gera config nova. Preserva a config ativa versionada. Nova derivedAt registra o instante da projeção; não modifica tempos históricos. O pin semântico é conferido, não escolhido por data.

## Reproduzir verificações

Com o servidor ativo:

```sh
"$NFL_OBSERVATION_PYTHON" -B docs/plans/broadcast-w12-expansion-v1/verify_http.py \
  --config "$NFL_OBSERVATION_CONFIG" --port 18096 --output /private/tmp/nfl-w12-http-review.json
NFL_W12_EVIDENCE=/private/tmp/nfl-w12-browser-review PATH=/opt/homebrew/opt/node@24/bin:$PATH \
  node docs/plans/broadcast-w12-expansion-v1/verify-browser.cjs
"$NFL_OBSERVATION_PYTHON" -B -m pytest -p no:cacheprovider -q \
  etl-pipeline/tests/test_metrics_lab.py etl-pipeline/tests/test_metrics_observations.py \
  etl-pipeline/tests/test_metrics_materialization.py
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
python3 -B docs/plans/broadcast-w12-expansion-v1/isolation.py
git diff --check
git log --oneline cae1fbba71368508681997e6ca167e92b56223f7..HEAD
git rev-parse HEAD
git status --short
```

O script de navegador usa Playwright e Chrome já instalados; cria e fecha somente seu próprio Chrome. NFL_PLAYWRIGHT/NFL_W12_ORIGIN/NFL_W12_EVIDENCE permitem configurar módulo/origem/saída. A prova usa catálogo e documentos HTTP reais; a indisponibilidade é uma interceptação explícita somente no teste. Nenhuma captura é certificação de compreensão humana.

Resultados: 110 Python, 235 frontend, cinco expected-failure preservados, lint/quatro builds/isolamento aprovados; 588 DTOs HTTP integrais, 768 destinos e 1.552 arredondamentos reconciliados. [Logs](checks/) · [Capturas e fluxos](evidence/).
