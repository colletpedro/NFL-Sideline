# NFL Sideline · leitura real individual v1

Entrada local: **http://127.0.0.1:18090/**. Base exata
`b59a8deb60aec318a6ed984a55b87a993b44b14d`; branch
`codex/broadcast-real-observation-v1` na worktree gerenciada
`/Users/pedrocollet/.codex/worktrees/broadcast-real-observation-v1/NFL Sideline`.

[Relatório e aceite técnico](REPORT.md) · [reconciliação HTTP](http.json) ·
[preflight](preflight.json) · [navegador](evidence/browser.json) ·
[reflow da referência](evidence/reflow-reference.json) · [isolamento](isolation.json).

## Iniciar novamente

A cópia completa principal permanece fora de web-ui. [lab-config.json](lab-config.json)
conserva path nominal, classificação REAL_ARCHIVE e pin aceito. Não editar o
pedido/bundle, não usar review-observations.json ou DTO salvo como entrada.

Da raiz desta worktree, sem carregar `.env`:

```sh
cd '/Users/pedrocollet/.codex/worktrees/broadcast-real-observation-v1/NFL Sideline'
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export NFL_OBSERVATION_CONFIG="$PWD/docs/plans/broadcast-real-observation-v1/lab-config.json"
export NFL_REAL_OBSERVATION_PORT=18090
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:dev
```

Dependências já existentes reutilizadas por symlink ignorado. Não houve instalação.
Um checkout independente precisa ter as dependências do lockfile disponíveis.
A porta é estrita: uma colisão encerra o startup, sem selecionar outra porta.
Uma porta alternativa requer configuração explícita por NFL_REAL_OBSERVATION_PORT
(inteiro 1024..65535). Vite e barreira HTTP usam esse mesmo valor; Host literal
127.0.0.1:porta e Origin ausente ou exatamente http://127.0.0.1:porta.
O laboratório antigo continua usando 18083 por padrão.

O startup executa o reader completo e congela catálogo e documentos como unidade.
A interface consome somente GETs relativos de mesma origem, com os marcadores e
sessão existentes. Clicar não valida novamente o arquivo, gera observações, consulta
banco ou chama modelo. Recarregar catálogo lê os mesmos bytes congelados do servidor.
Para revalidar bytes alterados é necessário reiniciar explicitamente. Conteúdo idêntico
pode conservar legitimamente o mesmo sessionId após reinício.

Servidor deixado ativo: **PID 21282**, somente 127.0.0.1:18090.
Encerrar apenas esta instância:

```sh
kill -TERM 21282
```

Se iniciado em outro terminal, Ctrl+C naquele terminal. Não usar pkill/killall.
O ensaio temporário de reflow em 18091 foi encerrado. Servidores anteriores
18086/18087/18088/18089 e suas worktrees foram preservados.

## Casos reais e capturas

A seleção inicial é derivada do catálogo, privilegiando geral/ataque de um período
com várias semanas quando disponível. Aqui ela é BAL W1–2. A URL preserva entry e
observation; também há preferência própria em sessionStorage. Nenhuma preferência
do laboratório anterior é modificada. Abra “Alterar recorte” para escolher somente
combinações presentes no catálogo. Uma alteração de período exigida por troca de
time é anunciada. Identidade removida não dispara fallback.

| Leitura real | Desktop | Mobile |
|---|---|---|
| BAL ataque geral 2026 W1–2 | [1440](evidence/available-1440.png) · [900](evidence/available-900.png) | [390](evidence/available-390.png) · [320](evidence/available-320.png) |
| BAL W3 sem fonte | [1440](evidence/absent-1440.png) · [900](evidence/absent-900.png) | [390](evidence/absent-390.png) · [320](evidence/absent-320.png) |
| DAL defesa contra passe W2 | [1440](evidence/defense-pass-1440.png) | — |
| NE defesa contra corrida POST2025 | — | [390](evidence/postseason-rush-390.png) |
| Texto ampliado a 200% | — | [320 real](evidence/reflow-real-320-text200.png) |

Estados de transporte com o mesmo documento real, em ensaio de navegador separado:
[carregamento](evidence/mobile-loading.png), [falha recuperável](evidence/mobile-network-error.png),
[sessão divergente](evidence/mobile-session-error.png). A rede é interceptada somente
pelo teste para atrasar/falhar a resposta; a entrada operacional não tem modo de fixture.
Vazio presente, COMPLETE vazio, zero, denominador zero, EPA ausente/não finito e
valores próximos de zero usam somente fixtures sintéticas dos testes, fora de REAL_ARCHIVE.

## Reproduzir os checks

```sh
PYTHONDONTWRITEBYTECODE=1 "$NFL_OBSERVATION_PYTHON" -B \
  docs/plans/broadcast-real-observation-v1/proof.py \
  --config "$NFL_OBSERVATION_CONFIG" --port "$NFL_REAL_OBSERVATION_PORT" \
  --output /private/tmp/nfl-real-http-review.json
export PLAYWRIGHT_MODULE='/Users/pedrocollet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
/opt/homebrew/opt/node@24/bin/node docs/plans/broadcast-real-observation-v1/browser.cjs
# O ensaio abaixo usa a referência anterior em 18089 e cria/encerra só seu 18091.
/opt/homebrew/opt/node@24/bin/node docs/plans/broadcast-real-observation-v1/reflow.mjs
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run real:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run experience:build
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
python3 docs/plans/broadcast-real-observation-v1/isolation.py
git diff --check
```

browser.cjs/reflow.mjs atualizam apenas suas evidências desta entrega. Os bundles
originais nunca são escritos. real:build cria real-dist ignorado; a operação local
usa real:dev, pois o transporte é preparado no servidor local, sem publicação estática.
