# Laboratório — risco dos passes e interceptações sofridas

Versão local funcional, sem publicação. [Risco dos passes (M3)](http://127.0.0.1:18125/?view=risk-lab&season=2026&reading=passes) · [Interceptações sofridas (B2)](http://127.0.0.1:18125/?view=risk-lab&season=2026&reading=interceptions).

Daniel Jones: [M3, 17 classificados / 8,66 esperados / 9 INT](http://127.0.0.1:18125/?view=risk-lab&season=2026&reading=passes&player=00-0035710) · [B2, 9 INT / 10,49 esperadas](http://127.0.0.1:18125/?view=risk-lab&season=2026&reading=interceptions&player=00-0035710).

Worktree gerenciada `/Users/pedrocollet/.codex/worktrees/qb-risk-outcomes-lab-v1/NFL Sideline`, branch `codex/qb-risk-outcomes-lab-v1`, criada do HEAD B2 `a2466636dec1d7feb8c3975cf984d7b505711dde`. A base visual `5d7d7769ce71a6864edce4c7393a75913563595f` é ancestral confirmado. Ambos os checkouts originais estavam limpos e continuam preservados. Sem merge, push, deploy ou publicação externa.

[Relatório](REPORT.md) · [Capturas](CAPTURES.md) · [Contrato de apresentação](PRESENTATION-CONTRACT.md) · [Reconciliação](RECONCILIATION.md) · [Verificação](evidence/verification.json).

## Operação local

Na raiz desta worktree:

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui ci
docs/plans/qb-risk-outcomes-lab-v1/run-local.sh
```

Somente `127.0.0.1:18125`, `strictPort`, sem fallback de porta. O servidor lê o store M3 original somente em modo de leitura e o store B2 de apresentação separado:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-outcomes-lab-v1`.

`NFL_RISK_LAB_STORE` e `NFL_RISK_OUTCOMES_STORE` permitem configurar esses dois paths locais. Nenhuma variável `VITE_*` escolhe modelos/pacotes. `envFile:false`, `envPrefix:[]`; não ler `.env` nem usar segredos, banco ou Gemini. O acervo W1–7 anterior continua disponível pela entrada local existente, sem publicação.

Para encerrar exclusivamente este servidor:

```sh
docs/plans/qb-risk-outcomes-lab-v1/stop-local.sh
```

O script confere porta, comando e cwd antes de SIGTERM. Não encerrar 18124 ou outros servidores de referência. PID histórico não é identidade suficiente.

## URLs e continuidade

`reading=passes` escolhe M3; `reading=interceptions` escolhe B2. Links antigos sem `reading` continuam em M3. A escolha preserva jogador, período, escala e posição, além dos parâmetros de evidência existentes. `period=all` ou semana; `scale=total|per100`; `position=qb|all|other|unknown` conserva o contrato anterior. `cross`, `play`, `game` e `page` continuam consultáveis.

Não há seleção automática de outro jogador ou semana. Fonte sem jogador/período explica a ausência e não reutiliza números da outra leitura. Voltar/avançar/recarga restauram leitura e seleção. A sessão conserva o índice de cada leitura; cada pedido de detalhe usa a versão daquele índice. “Conferir versão disponível” é explícito. Nenhum refresh do B2 ativa ou atualiza M3.

## Preparação inicial sem aquisição

O pacote científico aprovado fica intacto em:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1/application-complete`.

Revalidar fontes/modelo/consumidor, projetar os campos de apresentação e ativar somente no store B2:

```sh
python3 research/qb_risk_outcomes_lab/package.py
```

Não baixa dados nem ajusta modelos. Confere todos os hashes do manifest científico e das fontes, esquema, alvo, GSIS, chaves únicas, cobertura/jogos, probabilidades por classe, agregados e decomposições. Reconciliou 7.970 chaves, lançadores, FTN e INT com M3; a comparação fica identificada pelo pacote M3 conferido. Modelos, fontes e pesquisas anteriores nunca são destinos de escrita.

O store possui `packages/<id>/index.json`, `players/<gsis>.json`, `sources.json`, `integrity.json`, `runs/<UTC>/{receipt,revision,failure}.json` e `current.json`. Pacotes são imutáveis; o ID identifica seu conteúdo. Só após validar o pacote completo, o ponteiro B2 é trocado por `os.replace`. Falhas preservam o ponteiro anterior e deixam recibo. `.updating` impede publicação concorrente; verificar processo antes de tratar um lock abandonado.

## Atualização manual, sempre com B2 fixo

Criar ambiente próprio offline, se necessário (CPython 3.11/macOS arm64):

```sh
python3.11 -m venv research/qb_risk_outcomes_lab/.venv
PY='research/qb_risk_outcomes_lab/.venv/bin/python'
SCI='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1'
"$PY" -m pip install --no-index --find-links "$SCI/wheelhouse" -r research/qb_expected_interceptions/requirements.lock
```

Atualização futura explícita, com novas cópias públicas próprias:

```sh
"$PY" research/qb_risk_outcomes_lab/update.py
```

O wrapper executa a aplicação científica com o JSON fixo → valida novamente → gera pacote/recibo de revisão → ativa atomicamente apenas B2. Não há fit, recalibração, ponteiro M3, exigência de semana completa ou espera por semanas futuras. Dados novos ficam em `applications/<UTC>/`; não sobrescrevem a pesquisa aprovada.

Repetir uma aquisição pinada sem rede, em store de QA separado:

```sh
"$PY" research/qb_risk_outcomes_lab/update.py \
  --sources "$SCI/update-replay-sources" \
  --store '/CAMINHO/NOVO/DE/QA'
```

Esse fluxo foi executado em `qb-risk-outcomes-lab-v1/qa-fixed-update`: todos os 7.970 registros/probabilidades e os agregados por jogador/jogo ficaram exatamente iguais. A ativação de QA não substituiu o pacote visível 404d23007ba98d989940f117. [Recibo](evidence/update-replay.json). O teste de falha na troca do ponteiro também preservou e recuperou a versão válida anterior.

## Build local separado

```sh
docs/plans/qb-risk-outcomes-lab-v1/build-local.sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH node web-ui/scripts/risk-outcomes-built.mjs
```

Saída somente em `web-ui/risk-outcomes-dist`; preview loopback 18126, sem fallback. São 276 documentos GET congelados, com hashes e mapa de rotas, sem snapshots públicos. Esse build é uma fotografia dos pacotes ativos no momento do build; regerar depois de atualização manual. Para encerrar somente o preview desta worktree:

```sh
docs/plans/qb-risk-outcomes-lab-v1/stop-built.sh
```

O preview foi conferido no navegador e encerrado após QA. O servidor de desenvolvimento 18125 permanece como entrega acessível. O build público em `web-ui/dist` foi reconstruído e é idêntico em bytes ao build público da referência aprovada.

## Verificações reproduzíveis

```sh
docs/plans/qb-risk-outcomes-lab-v1/checks.sh
"$PY" -m pytest research/qb_risk_outcomes_lab/test_package.py -q
"$PY" -m pytest research/qb_expected_interceptions/tests -q
"$PY" -m pytest research/qb_risk_lab/test_pipeline.py research/qb_interception_risk/tests research/qb_risk_temporal_v2/tests -q
python3 research/qb_risk_outcomes_lab/verify.py --out /tmp/nfl-outcomes-reconciliation-new.json
python3 research/qb_risk_outcomes_lab/preservation.py check \
  --before docs/plans/qb-risk-outcomes-lab-v1/evidence/preservation-before.json \
  --out /tmp/nfl-outcomes-preservation-new.json
```

`checks.sh` configura todas as fontes locais, inclusive os casos condicionais legados; executa suíte completa, TypeScript, lint, build público e build local. 415 testes frontend passaram, nenhum pulado; cinco expected failures legados permanecem. Seis testes novos de publicação e 33+59 científicos passaram. Grupos Python separados evitam colisões de módulos legados homônimos. O lint tem somente um warning preexistente em `reading-polish/main.tsx`.

`verify.py` reconcilia offline os recibos DOM congelados com os pacotes imutáveis, inclusive coordenadas, identidade matemática da diagonal e casos reais. Não deve ser confundido com uma nova execução do navegador. O teste de artefato renderiza as contas de todos os 66 jogadores nos nove períodos (594 combinações, incluindo ausências), confere ambas as contribuições e os números exibidos. O navegador conferiu 1.372 pontos em 36 visões das duas leituras, além de desktop, 390/320 px, texto 200%, teclado, toque sintetizado, histórico, evidências, carregamento e falha/recuperação.

Limites: o toque foi sintetizado por PointerEvent de tipo touch + clique, não em dispositivo físico; `Input.dispatchTouchEvent` não é suportado pelo navegador integrado. Overrides de viewport/texto/rede/toque foram removidos ao final. Os dados continuam retrospectivos, com possibilidade de revisão e sem atribuição causal. Na avaliação de 2025, os passes não classificados como interceptáveis tiveram 75 INT contra 52,92 esperadas; essa limitação aparece na metodologia. Não há intervalos de habilidade nem nova aprovação de publicação.
