# Pesquisa local — passes interceptáveis acima do esperado

Baseline executada e avaliada retrospectivamente. Contexto melhora modestamente a log loss, mas superestima a frequência do rótulo; não está pronto para produção ou ranking de decisão dos QBs. [Relatório e tabela completa](REPORT.md) · [Contrato](RESEARCH-CONTRACT.md) · [Auditoria](DATA-AUDIT.md) · [Features](FEATURE-AVAILABILITY.md) · [Model card](MODEL-CARD.md) · [Passagem](HANDOFF.md) · [Licença](NOTICE.md).

## Localizações

Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/qb-interception-risk-baseline-v1/NFL Sideline`, branch `codex/qb-interception-risk-baseline-v1`, base `5b38f04e559bad5fc1b4ef25116cc0afb93293d9`. Não houve merge/push/deploy/publicação. Código isolado em `research/qb_interception_risk`; documentação neste diretório. Nada é importado pelo produto, ETL ou backend.

Store durável: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-interception-risk-baseline-v1/20261104-v1`.

- `raw/`, `documentation/`, `sources.json`: fontes, documentação, esquemas e hashes.
- `build-v2/dataset.parquet`: 78.460 linhas, chave por passe, features/alvo/auditoria. Campos de resultado existem para auditoria, mas o modelo usa allowlist.
- `build-v2/splits.csv`: atribuição por chave a desenvolvimento, folds, teste e aplicação. Sem jogos repartidos aleatoriamente.
- `build-v2/audit/`: inclusão/exclusão, joins externos, penalidades/no_play, nomes/times, contagens e cobertura ambiental.
- `development-v3/`: escolha C, previsões fora do treino 2023/24, freeze anterior ao teste, modelos JSON2022–24 e ambiente.
- `evaluation-v1/`: única avaliação inicial2025, previsões por passe, métricas, grupos, calibração, coeficientes.
- `application-v1/`: modelos refit2022–25, previsões por passe2026 W1–7, tabelas de todos os62 passers e sensibilidade.
- `figures-v3/`: quatro figuras PNG/SVG e CSV de suporte.
- `reproduction-final/`: reconstrução offline em destino novo; `reproduction-check.json`: comparações de hashes. Versões anteriores/tentativas preservadas.
- `wheelhouse/` e `requirements-final.lock`: dependências locais para instalar sem rede (CPython3.11/macOS arm64). Lock versionado em `research/qb_interception_risk/requirements.lock`.
- Cópia de recuperação: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/qb-interception-risk-baseline-v1/20261104-v1`. Manifesto de recuperação registra hashes, não substitui os bytes.

Os binários pesados ficam fora do Git. `evidence/` e `figures/` são cópias pequenas de revisão; não substituem fontes/modelos/previsões completos. Não usar fontes locais antigas do ETL como substitutas silenciosas. Aquisição nova pode baixar revisão diferente: exige novo store e nova auditoria; não equivale à reprodução congelada.

## Ambiente isolado

Na raiz da worktree:

```sh
python3.11 -m venv research/qb_interception_risk/.venv
research/qb_interception_risk/.venv/bin/pip install -r research/qb_interception_risk/requirements.lock
```

Alternativa offline na mesma plataforma, a partir da cópia conservada:

```sh
STORE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-interception-risk-baseline-v1/20261104-v1'
research/qb_interception_risk/.venv/bin/pip install --no-index --find-links "$STORE/wheelhouse" -r research/qb_interception_risk/requirements.lock
```

Não lê `.env`, não precisa banco, Docker, Gemini, Vercel, nflreadpy, conta ou serviço pago. Não modifica ambientes compartilhados. NumPy final2.3.4 evita avisos espúrios de Accelerate observados com2.2.6; [histórico](CHECKPOINTS.md). Linux/outra arquitetura exige wheels compatíveis, não prometemos identidade bit a bit entre BLAS/plataformas.

## Aquisição explícita (rede pública)

```sh
research/qb_interception_risk/.venv/bin/python research/qb_interception_risk/acquire.py --store "$STORE"
```

Se já há `sources.json`, somente confere hashes e não atualiza. Primeiro uso baixa PBP2022–25, FTN2022–26, schedules, documentação/licenças; copia PBP2026 do path aprovado fornecido pelo usuário. `--approved-pbp` aceita a mesma fonte restaurada em outro local. Aquisição parcial só retoma arquivos já registrados e com hash igual; arquivo parcial não verificado é preservado e recusado. Não sobrescrever/editar manifest para acomodar revisão nova. [URLs e instantes exatos](evidence/sources.json).

## Etapas separadas

Os destinos abaixo precisam ser novos. Na execução original, build-v2/development-v3/evaluation-v1/application-v1 já existem e são recusados para evitar sobrescrita.

```sh
PY='research/qb_interception_risk/.venv/bin/python'
CLI='research/qb_interception_risk/pipeline.py'
$PY "$CLI" build --store "$STORE" --out "$STORE/my-build"
$PY -W error::RuntimeWarning "$CLI" develop --build "$STORE/my-build" --out "$STORE/my-development"
# Conferir e congelar C/config/modelos ANTES de avaliar um teste novo.
$PY -W error::RuntimeWarning "$CLI" evaluate --build "$STORE/my-build" --development "$STORE/my-development" --out "$STORE/my-evaluation"
$PY -W error::RuntimeWarning "$CLI" apply --build "$STORE/my-build" --development "$STORE/my-development" --out "$STORE/my-application"
$PY -W error::RuntimeWarning research/qb_interception_risk/plots.py --evaluation "$STORE/my-evaluation" --application "$STORE/my-application" --out "$STORE/my-figures"
```

2025 foi examinado nesta entrega. Reexecução desses mesmos bytes é reprodução; não se torna teste novo nem autoriza ajustar hiperparâmetros com esse desempenho. Para nova pesquisa, reservar outro bloco temporal e outro contrato.

## Reprodução completa offline

```sh
research/qb_interception_risk/reproduce.sh \
  "$STORE" \
  "$STORE/development-v3" \
  "$STORE/reproduction-review-new"
```

O wrapper bloqueia conexões Python antes de executar: valida SHA de todas as fontes, reconstrói população/SQLite independente/splits, refaz toda a pequena busca de desenvolvimento e modelos finais, exige que o freeze resultante seja **idêntico** ao pré-teste conservado, só então reproduz avaliação/aplicação/gráficos. Se divergir, aborta antes da avaliação. Não carrega pickle, apenas JSON produzido pelo código local. Para comparar:

```sh
$PY research/qb_interception_risk/verify_reproduction.py \
  --store "$STORE" --reproduction "$STORE/reproduction-review-new" \
  --out "$STORE/reproduction-review-new-check.json"
```

Esses comandos não fazem aquisição/instalação. O ambiente precisa estar instalado com o lock; a entrega conserva wheelhouse para reconstruí-lo sem rede. Hashes de dataset/splits/modelos/previsões/métricas/agregados precisam coincidir na mesma plataforma. PNG/SVG são exportáveis; identidade entre versões de renderer não é promessa de equivalência científica, embora os artefatos finais locais sejam também confrontados.

## Testes e isolamento

```sh
$PY -W error::RuntimeWarning -m pytest research/qb_interception_risk/tests -q
npm --prefix web-ui test -- src/components/visual-preparation-regressions.test.tsx
$PY research/qb_interception_risk/check_isolation.py --out "$STORE/isolation-review.json"
```

Testes novos offline com fixtures: duplicatas/cardinalidade/rótulos, penalidades/elegibilidade, fronteiraW7, temporalidade/jogos, preprocessing só no treino, allowlist, identidade GSIS, soma/sinal/unidades, determinismo e adulteração de fontes. Se frontend deps faltarem, `npm --prefix web-ui ci` instala só nesta worktree. Não há necessidade de repetir auditoria visual do site: nenhum arquivo do produto mudou. Seis testes legados executados, cinco são `it.fails` e continuam defeitos conhecidos. Prova de isolamento compara árvores Git/bytes dos paths protegidos e HEAD/status da worktree aprovada, além do hash do PBP pinado e escuta do servidor existente. Não mata/reinicia o servidor.

[Resultados de verificação](evidence/verification.json). Checkpoints e commits locais: [CHECKPOINTS](CHECKPOINTS.md). O pacote é material técnico de revisão, sem aprovação estatística/editorial/jurídica automática para publicação.
