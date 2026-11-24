# NFL Sideline · descoberta visual v3

[Central](http://127.0.0.1:18094/?season=2026&week=1&filter=all) · [Busca na temporada](http://127.0.0.1:18094/?season=2026&week=3&filter=participants&q=BAL&scope=season) · [Painel dos 32 logos](http://127.0.0.1:18094/logos.html).

[Relatório e antes/depois](REPORT.md) · [Plano inicial](PLAN.md) · [Inventário](assets.json) · [Procedência](ASSETS.md) · [Piloto de capacetes](HELMET-PILOT.md) · [Isolamento](checks/isolation.json).

## Percursos reais

- [BAL–IND, leitura individual e IND sem observação](http://127.0.0.1:18094/?season=2026&week=1&game=2026_01_BAL_IND).
- [BAL–DAL, lacuna](http://127.0.0.1:18094/?season=2026&week=3&game=2026_03_BAL_DAL).
- [NO–BAL, período inclusivo disponível](http://127.0.0.1:18094/?season=2026&week=2&game=2026_02_NO_BAL&team=BAL).
- [NE–JAX, arquivo separado de 2025 POST](http://127.0.0.1:18094/?season=2026&week=3&game=2026_03_NE_JAX).
- [GB–MIN, participantes sem observação](http://127.0.0.1:18094/?season=2026&week=1&game=2026_01_GB_MIN).
- [Busca sem resultados](http://127.0.0.1:18094/?season=2026&week=1&q=zzzinexistente).

Os links escolhem semanas explicitamente para avaliação. A URL sem parâmetros continua usando publicação e data UTC; nenhum padrão temporal foi substituído.

## Operação local

Worktree gerenciada: /Users/pedrocollet/.codex/worktrees/broadcast-discovery-assets-v3/NFL Sideline. Branch codex/broadcast-discovery-assets-v3. Base exata 4f6095fd205da9230abc8c82e8a3a457a47bbaba.

Servidor próprio em **127.0.0.1:18094**, processo Node **55895** nesta sessão. Servidor anterior 127.0.0.1:18093, processo 39598, preservado. Não encerrar processos de outras versões.

    cd '/Users/pedrocollet/.codex/worktrees/broadcast-discovery-assets-v3/NFL Sideline'
    export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
    export NFL_OBSERVATION_CONFIG='/Users/pedrocollet/Downloads/NFL Sideline/docs/plans/metrics/e5c-3r/lab-config.json'
    export NFL_LOCAL_JOURNEY_PORT=18094
    PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:dev

A porta deve estar livre antes de iniciar outra instância. Dependências já disponíveis são reutilizadas por symlink ignorado; sem instalação de pacote/runtime. A configuração aponta para o bundle completo real preservado, sem substituição por extrato ou fixture. Para encerrar a instância acima:

    kill -TERM 55895

Se iniciado em seu terminal, Ctrl+C encerra somente sua instância.

## Reproduzir gates

    PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
    PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
    PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:build
    PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
    PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
    PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
    python3 -B docs/plans/broadcast-discovery-assets-v3/verify.py
    "$NFL_OBSERVATION_PYTHON" -B docs/plans/broadcast-real-observation-v1/proof.py --config "$NFL_OBSERVATION_CONFIG" --port 18094 --output /private/tmp/nfl-discovery-v3-http-recheck.json
    git diff --check 4f6095fd205da9230abc8c82e8a3a457a47bbaba
    git log -3 --oneline
    git status --short

O gate verifica preservação e evidências registradas; não substitui uma nova inspeção visual. O painel logos.html é uma entrada de evidência do servidor de desenvolvimento, independente da central e fora do build público.
