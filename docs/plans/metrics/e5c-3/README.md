# E5c-3 — laboratório de observações auditáveis (candidato)

Entrada local e somente leitura: bundle E5c-2 completo → reader Python aceito,
com rederivação → DTO reduzido → sessão Vite congelada → uma observação.
Não há seleção PIT, comparação, tese editorial ou conexão com Production.

Leia [desenho anterior ao código](DESIGN.md), [transporte](TRANSPORT.md) e
[relatório de integração](REPORT.md). A prova real está **pendente**, conforme
orientação do usuário/orquestrador: os bundles temporários desapareceram; os
quatro Parquets preservados serão tratados numa reconstrução separada. Não usar
`real-observations.json` como fonte ou converter relatórios em proveniência.

## Inicialização e encerramento

Todos os comandos partem da raiz desta worktree. Use runtimes/dependências já
instalados; nenhum comando abaixo instala ou adquire dados. Defina `PYTHON`
como o executável Python 3.11+ existente com as dependências ETL e `PYTHONPATH`:

```sh
export PYTHON='/caminho/absoluto/venv/bin/python'
export PYTHONPATH="$PWD/etl-pipeline/src"
```

Preparação **explícita de demonstração sintética**, fora do servidor; exige
diretório novo. Cria cinco bundles completos, fechados, pelo caminho aceito.
Não é uma restauração dos artefatos reais. A entrada real ausente ficará ERROR.

```sh
"$PYTHON" -B docs/plans/metrics/e5c-3/prepare_demo.py --output /tmp/nfl-e5c3-demo
export NFL_OBSERVATION_PYTHON="$PYTHON"
export NFL_OBSERVATION_CONFIG=/tmp/nfl-e5c3-demo/config.json
npm --prefix web-ui run editorial:dev
```

Abrir `http://127.0.0.1:18083/`, escolher **Observações auditáveis**, bundle e
recorte. Ctrl-C no terminal encerra Vite; durante preparação encerra também o
filho Python próprio. Não precisa do serviço Java para este modo.
Os modos anteriores continuam dependendo da API local e de seu próprio fluxo.

Para bundles reais restaurados e aceitos, crie configuração local conforme
[exemplo](operator-config.example.json), com path absoluto e bundleId conferido.
Configuração e bundles devem ficar **fora de web-ui**, inclusive symlinks para
esse diretório: ele faz parte do allowlist estático preexistente do Vite.
Não utilizar variáveis VITE_*, URLs ou argumentos vindos do browser.

Inspeção explícita da adaptação, sem HTTP (a saída não é bundle de entrada):

```sh
"$PYTHON" -B -m nfl_sideline_etl.metrics_lab --config "$NFL_OBSERVATION_CONFIG" > /tmp/lab-session.json
```

O Vite sempre executa o reader; não possui opção de aceitar `/tmp/lab-session.json`.
Cada entrada inválida fica em erro e não é substituída. Mudanças no disco exigem
**parar e iniciar novamente**. Recarregar catálogo/page lê somente bytes da sessão.

## Verificação reproduzível

```sh
"$PYTHON" -B -m pytest -p no:cacheprovider etl-pipeline/tests/test_metrics_lab.py etl-pipeline/tests/test_metrics_observations.py etl-pipeline/tests/test_metrics_materialization.py
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run build
python3 docs/plans/metrics/e5c-3/verify_production.py
python3 docs/plans/metrics/e5c-3/verify_preservation.py

git diff --check
```

Com o laboratório iniciado com a demonstração acima, executar HTTP real:

```sh
python3 docs/plans/metrics/e5c-3/verify_http.py
```

Chrome/Playwright já instalados, sem instalar browser ou runtime:

```sh
export PLAYWRIGHT_MODULE=/caminho/absoluto/node_modules/playwright
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
/caminho/node-20-ou-superior docs/plans/metrics/e5c-3/verify_browser.cjs /tmp/e5c3-visual
```

Contraprova opt-in altera **somente a demonstração sintética descartável**:

```sh
python3 docs/plans/metrics/e5c-3/verify_freeze.py before-restart --state /tmp/e5c3-freeze --synthetic-bundle /tmp/nfl-e5c3-demo/synthetic
# Ctrl-C e iniciar novamente com a mesma configuração.
python3 docs/plans/metrics/e5c-3/verify_freeze.py after-restart --state /tmp/e5c3-freeze
# Os bytes originais sintéticos foram restaurados; reiniciar para READY novamente.
```

Não executar essa contraprova em arquivos históricos ou bundles operacionais.
Os testes unitários usam vetores versionados e preparações temporárias fechadas;
não dependem de `/tmp` prévio. `prepare_demo.py` reaproveita o construtor sintético
E5c-2 e componentes operacionais aceitos, nunca o verificador de fixtures E5c-1.
Não executar o main histórico de verify.py E5c-1 contra esta base documental.
