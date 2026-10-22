# NFL Sideline · percurso local integrado v1

Entrada ativa: **[http://127.0.0.1:18092/](http://127.0.0.1:18092/)**.
Base exata `c193bb8116e347a76ac31f8fbe78cdbf57cda8a6`, conferida na referência preservada.
Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/broadcast-local-journey-v1/NFL Sideline`.
Branch `codex/broadcast-local-journey-v1`. Implementação: `2f7af1b`.
Entrega experimental local, sem merge, push ou deploy.

[Matriz implementada](RELATIONS.md) · [relatório](REPORT.md) · [rotas em JSON](routes.json) · [prova do navegador](evidence/browser.json) · [HTTP/reader](http.json) · [isolamento](isolation.json).

## Iniciar e encerrar somente este servidor

Sem `.env`, instalação, banco, Docker, geração ou aquisição:

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-local-journey-v1/NFL Sideline'
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export NFL_OBSERVATION_CONFIG='/Users/pedrocollet/Downloads/NFL Sideline/docs/plans/metrics/e5c-3r/lab-config.json'
export NFL_LOCAL_JOURNEY_PORT=18092
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:dev
```

A instância entregue já está ativa no **PID 27714**; não iniciar uma segunda na mesma porta.
Encerrar somente a instância entregue:

```sh
kill -TERM 27714
```

Em nova execução, Ctrl+C no terminal próprio; o script também imprime seu PID.
Porta explícita 1024..65535, estrita, IP literal 127.0.0.1; colisão encerra startup.
Os servidores anteriores 18086/18087/18088/18089/18090 continuam nos PIDs 69029/770/4041/15045/21282.

## Casos reproduzíveis

| Caso | Rota nominal completa |
|---|---|
| Central · semana 1 | [Abrir](http://127.0.0.1:18092/?season=2026&week=1&filter=all) |
| BAL–IND W1 · BAL ataque geral individual | [Abrir](http://127.0.0.1:18092/?season=2026&week=1&filter=all&game=2026_01_BAL_IND&entry=real-recovery&observation=sha256%3Acbd7c41072386044ec653ed437bcb14894e019f5268904302877c9535eb3d3d1) |
| NO–BAL W2 · BAL ataque geral W2 | [Abrir](http://127.0.0.1:18092/?season=2026&week=2&filter=all&game=2026_02_NO_BAL&entry=real-recovery&observation=sha256%3Aa06eb4752149432d973a6ce562780585e643f86ef04413c73261182eeeddd5a6) |
| NO–BAL W2 · BAL ataque geral W1–2 inclusivo | [Abrir](http://127.0.0.1:18092/?season=2026&week=2&filter=all&game=2026_02_NO_BAL&entry=real-recovery&observation=sha256%3A1c585c0ae1e0b24df3ef8815e01d0af5de065c4a504b35420728bca810e24e9b) |
| BAL–DAL W3 · lacuna BAL | [Abrir](http://127.0.0.1:18092/?season=2026&week=3&filter=all&game=2026_03_BAL_DAL&entry=real-recovery&observation=sha256%3A31a25efd933623bc532ea1f323fab742e71214565b5445340b5f50a7507a6257) |
| GB–MIN W1 · nenhum participante com leitura | [Abrir](http://127.0.0.1:18092/?season=2026&week=1&filter=all&game=2026_01_GB_MIN) |
| NE–JAX REG2026 · arquivo NE POST2025 | [Abrir](http://127.0.0.1:18092/?season=2026&week=3&filter=all&game=2026_03_NE_JAX&entry=real-recovery&observation=sha256%3Aad890fc8e4b41cba0c623bd3d20bfc363e2519146d9bd8589c4b799a0aa74302) |
| BAL–IND com observação DAL · vínculo recusado | [Abrir](http://127.0.0.1:18092/?season=2026&week=1&filter=all&game=2026_01_BAL_IND&entry=real-recovery&observation=sha256%3Acdab1203292c2f9a35ac1075de43e59765574a0c3677a84e01d10a954e56ee95) |

Na central, selecione semana e abra o confronto. Cada região descreve a categoria antes do clique.
Na leitura, “Explorar outro recorte” oferece apenas os 48 documentos do catálogo; cada troca refaz o vínculo.
A origem, o período próprio e os retornos ficam acima da leitura. A escolha nominal prevalece sobre qualquer
preferência anterior. `details=open` e `composition=open` preservam exploração e recarga.
O caminho de retorno é o par temporada/semana/filtro na mesma URL, sem serializar DTO.

## Capturas

| Tela | Desktop | Intermediária | Mobile |
|---|---|---|---|
| Central | [1440](evidence/calendar-1440-text100.png) | [900](evidence/calendar-900-text100.png) | [390](evidence/calendar-390-text100.png) · [320](evidence/calendar-320-text100.png) |
| Confronto NO–BAL | [1440](evidence/matchup-1440-text100.png) | [900](evidence/matchup-900-text100.png) | [390](evidence/matchup-390-text100.png) · [320](evidence/matchup-320-text100.png) |
| Leitura inclusiva contextualizada | [1440](evidence/reading-1440-text100.png) | [900](evidence/reading-900-text100.png) | [390](evidence/reading-390-text100.png) · [320](evidence/reading-320-text100.png) |

Casos: [BAL individual](evidence/bal-individual-1440.png), [W2 individual](evidence/bal-week2-1440.png),
[W1–2 inclusivo](evidence/bal-inclusive-1440.png), [confronto com lacuna e resultado ausente](evidence/gap-matchup-1440.png),
[leitura sem fonte](evidence/bal-gap-1440.png), [sem leituras](evidence/no-readings-1440.png),
[NE POST2025 separado](evidence/ne-archive-1440.png), [vínculo incompatível](evidence/incompatible-1440.png).

Texto 200% a 320: [central](evidence/calendar-320-text200.png), [confronto](evidence/matchup-320-text200.png),
[leitura](evidence/reading-320-text200.png). [Teclado](evidence/keyboard-390.png).
Falhas: [arquivo](evidence/archive-failure-390.png), [calendário](evidence/calendar-failure-390.png),
[sessão divergente](evidence/session-failure-390.png).

## Repetir os checks

Da worktree acima:

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
PYTHONDONTWRITEBYTECODE=1 "$NFL_OBSERVATION_PYTHON" -B docs/plans/broadcast-real-observation-v1/proof.py \
  --config "$NFL_OBSERVATION_CONFIG" --port 18092 --output /private/tmp/journey-http-review.json
export PLAYWRIGHT_MODULE='/Users/pedrocollet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
/opt/homebrew/opt/node@24/bin/node docs/plans/broadcast-local-journey-v1/browser.cjs
python3 docs/plans/broadcast-local-journey-v1/isolation.py
git diff --check
```

`browser.cjs` cria e encerra apenas seu Chrome headless em finally, atualiza evidências desta pasta e não usa
DTO salvo como entrada. O build integrado é local e sem transporte estático publicável; a operação usa `journey:dev`.
