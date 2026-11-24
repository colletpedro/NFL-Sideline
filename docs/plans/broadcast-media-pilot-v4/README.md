# NFL Sideline · orientação e mídia local v4

Base exata **13597af9dafb910e345ef0bcc519f3d1352ca941**. Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/broadcast-media-pilot-v4/NFL Sideline`. Branch `codex/broadcast-media-pilot-v4`.

- [Busca BAL com origem na semana 3](http://127.0.0.1:18095/?season=2026&week=3&filter=participants&q=BAL&scope=season&explore=open) — abra NO × BAL; seleção inicial BAL, sem abrir documento automaticamente.
- [NO × BAL corrigido](http://127.0.0.1:18095/?season=2026&week=3&filter=participants&q=BAL&scope=season&game=2026_02_NO_BAL).
- [Escolha explícita NO sem leitura](http://127.0.0.1:18095/?season=2026&week=3&game=2026_02_NO_BAL&team=NO).
- [Galeria dos oito candidatos](http://127.0.0.1:18095/?season=2026&week=1&view=media).
- [Abertura BAL × IND com capacetes](http://127.0.0.1:18095/?season=2026&week=1&filter=all&media=helmets).
- [Abertura com logos preservada](http://127.0.0.1:18095/?season=2026&week=1&filter=all).
- [Servidor anterior, abertura preservada](http://127.0.0.1:18094/?season=2026&week=1&filter=all).
- [32 logos](http://127.0.0.1:18095/logos.html).

[Relatório e comparação](REPORT.md) · [Inventário](assets.json) · [Procedência e limitações](ASSETS.md) · [Plano](PLAN.md) · [Gate](checks/isolation.json).

## Operação

Servidor próprio **127.0.0.1:18095**, Node PID **64983** nesta sessão. Nenhum bind público. Porta estrita; se ocupada, escolha outra porta livre. Dependências reutilizadas por symlink ignorado, sem instalação. Fonte real completa via configuração anterior, sem extrato/fixture substituta.

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-media-pilot-v4/NFL Sideline'
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export NFL_OBSERVATION_CONFIG='/Users/pedrocollet/Downloads/NFL Sideline/docs/plans/metrics/e5c-3r/lab-config.json'
export NFL_LOCAL_JOURNEY_PORT=18095
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:dev
```

Para encerrar **a instância desta entrega**, confira o PID/porta antes de enviar o sinal:

```sh
lsof -nP -iTCP:18095 -sTCP:LISTEN
kill -TERM 64983
```

Se iniciado no seu terminal, Ctrl+C encerra sua instância. Servidores anteriores 18093/PID39598 e 18094/PID55895 foram encontrados ativos e preservados. A worktree anterior foi observada limpa em `1b2fd1a9aa6870987e4318eb191ab29381a41c3e`, um commit posterior à base solicitada; ela não foi usada como nova base nem editada. A nova branch parte exatamente de 13597af.

## Reprodução dos checks

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
python3 -B docs/plans/broadcast-media-pilot-v4/verify.py
NFL_MEDIA_EVIDENCE=/private/tmp/nfl-media-v4-recheck PATH=/opt/homebrew/opt/node@24/bin:$PATH node docs/plans/broadcast-media-pilot-v4/verify-browser.cjs
"$NFL_OBSERVATION_PYTHON" -B docs/plans/broadcast-real-observation-v1/proof.py --config "$NFL_OBSERVATION_CONFIG" --port 18095 --output /private/tmp/nfl-media-v4-http-recheck.json
```

O script de navegador usa Playwright já disponível no runtime local e Chrome headless próprio; NFL_PLAYWRIGHT pode apontar para outra instalação. Não controla nem encerra o navegador pessoal. Capturas/evidências registram uma avaliação técnica, sem aceite humano.
