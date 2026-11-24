# Progressão e improvisação — laboratório local v1

Entrega funcional em 06/11/2026, com classificação **2.0.0**, esquema de consumo **2**, métrica principal **1.0.0** e apresentação **1.0.0**. Integração autorizada após revisão da pesquisa. Sem novo modelo, publicação externa, merge, push ou deploy.

[Abrir nova leitura](http://127.0.0.1:18127/?view=risk-lab&season=2026&reading=progression) · [Mahomes](http://127.0.0.1:18127/?view=risk-lab&season=2026&reading=progression&player=00-0033873) · [Maye](http://127.0.0.1:18127/?view=risk-lab&season=2026&reading=progression&player=00-0039851) · [Willis](http://127.0.0.1:18127/?view=risk-lab&season=2026&reading=progression&player=00-0038128) · [Stroud](http://127.0.0.1:18127/?view=risk-lab&season=2026&reading=progression&player=00-0039163) · [Stafford](http://127.0.0.1:18127/?view=risk-lab&season=2026&reading=progression&player=00-0026498).

[Relatório antes/depois](REPORT.md) · [decisão/contrato](DECISION.md) · [direção visual](DESIGN.md) · [capturas](CAPTURES.md) · [verificações](evidence/qa-summary.json) · [reconciliação](evidence/reconciliation.json).

## Operação

Worktree: `/Users/pedrocollet/.codex/worktrees/qb-progression-improvisation-lab-v1/NFL Sideline`.
Branch: `codex/qb-progression-improvisation-lab-v1`, base exata `1f72767b514cc1617046378fe00824ad957ad8f8` (contém a integração M3/B2 `01f23cf`).

Na raiz da worktree:

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui ci
docs/plans/qb-progression-improvisation-lab-v1/run-local.sh
```

Somente `127.0.0.1:18127`, `strictPort`, sem escolher outra porta automaticamente. O servidor desta entrega fica disponível após QA. A configuração lê os stores M3/B2 existentes em modo somente leitura e o store próprio da nova leitura. `envFile:false`, `envPrefix:[]`; nenhuma variável `VITE_*` seleciona pacotes; não há `.env`, segredo, banco ou Gemini. `NFL_PROGRESSION_STORE` permite escolher somente a fonte local da terceira leitura no processo do servidor.

Para encerrar **exclusivamente** o servidor desta worktree:

```sh
docs/plans/qb-progression-improvisation-lab-v1/stop-local.sh
```

O script confere porta, comando e cwd antes de SIGTERM. Não encerra 18124/18125, nem usa PID histórico isoladamente. Os servidores anteriores não foram reiniciados. A referência 18125 estava indisponível antes/depois; isso não foi tratado como autorização para modificá-la.

## Pacote versionado

Store próprio:
`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-progression-improvisation-lab-v1`.

- `current.json`: ponteiro exclusivo da terceira leitura, com esquema, ID, hash do índice e instante da conferência.
- `packages/5b780052143352a5abf8ffec/`: pacote inicial imutável. `index.json`, `players/{GSIS}.json`, `integrity.json`, `sources.json`, `plays.parquet`, `history.json`, `classification-transition.csv`, `reconciliation.json`.
- `runs/{UTC}/`: recibos, revisão e falhas de ativação; `.updating` impede concorrência de publicação local.
- `qa-update/`: replay com regras fixas, byte a byte igual ao pacote ativo, sem tocar em seu ponteiro.
- `recovery-final/`: arquivo local de recuperação, conteúdo/hashes extraídos e verificados, sem alegação de backup remoto. [Recibo](evidence/recovery.json).

O índice aceita somente esquema 2/classificação 2.0.0 e as sete categorias exatas. Índice antigo de seis categorias é rejeitado. O endpoint `/__progression/` é separado de `/__risk-lab/` e `/__risk-outcomes/`; não há adaptação silenciosa do contrato de passes. O pacote guarda todo o histórico 2023–2026; as 20.210 linhas de 2022 continuam somente na auditoria elementar. A interface inicial mostra 2026 e semanas 1–8.

Para reconstruir a apresentação a partir da pesquisa congelada, sem aquisição ou ajuste:

```sh
QB_PY='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-structure-production-v1/20261105-v1/runtime/environment/bin/python'
"$QB_PY" research/qb_progression_lab/package.py
```

O pacote científico anterior e fontes são conferidos por manifest/hashes. Somente DES auditado migra; A/B e sensibilidades mantêm as mesmas chaves e EPA. IDs e conteúdo são determinísticos; reexecução do mesmo conteúdo reutiliza o pacote após conferir integridade. Ativação usa troca atômica do ponteiro próprio após validar todos os documentos. Falha preserva o ponteiro anterior e deixa recibo.

## Atualização manual fixa

Sem dados novos, replay em store de QA separado:

```sh
"$QB_PY" research/qb_progression_lab/update.py \
  --frozen-science '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-structure-production-v1/20261105-v1/package-release' \
  --fixed-index '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-progression-improvisation-lab-v1/packages/5b780052143352a5abf8ffec/index.json' \
  --store '/CAMINHO/NOVO/QA' \
  --out '/CAMINHO/NOVO/RECIBO'
```

O replay foi executado e conferiu 74 arquivos byte a byte idênticos. O ponteiro ativo da interface não foi substituído pelo de QA. Para aquisição futura explícita de 2026, omitir `--frozen-science`: o wrapper executa o update científico com regras v1 fixas em diretório novo → valida → classifica DES em v2 → gera revisão/pacote → ativa somente a terceira leitura. `--sources` permite usar outra aquisição já congelada sem rede. O hash da implementação v2 é conferido antes da aquisição; mudança requer revisão. Não há retreino, atualização automática, ponteiros M3/B2 ou espera por semana completa. Não foi necessária nova aquisição nesta entrega.

## Interface e URL

`reading=progression` abre a terceira leitura; links antigos continuam em M3/B2. Jogador, período e posição são conservados, com ausência explícita quando não disponíveis. `scale=per100` herdado é conservado para as outras leituras, mas nunca aplicado ao EPA ou oferecido como controle nesta leitura. `category` filtra somente evidências, sem alterar resumo/composição; fica na URL e é retirado ao sair para consumidores M3/B2 que não o suportam. `play`, `game` e `page` continuam explícitos. Voltar, avançar e recarregar foram verificados.

Cada sessão conserva o índice carregado; detalhes são solicitados por packageId, impedindo mistura durante atualização. “Conferir versão disponível” é uma ação explícita. Respostas tardias e detalhes de outra versão são descartados/rejeitados. Falhas não reutilizam números de outra leitura.

## Verificações

```sh
docs/plans/qb-progression-improvisation-lab-v1/checks.sh
"$QB_PY" -m pytest research/qb_progression_lab/test_package.py -q
"$QB_PY" research/qb_progression_lab/reconcile.py \
  --out '/CAMINHO/NOVO/reconciliation.json'
```

Suíte frontend configurada com todos os artefatos locais: 425 resultados aprovados = **420 passes comuns + 5 expected failures legados**, zero falhas inesperadas, zero skips. Novos testes Python: 15 passes, zero skips. Preservados: M3 23, B2 33, pesquisa v1 42. TypeScript passa. Lint: zero erros, um warning preexistente em `reading-polish/main.tsx`. Logs iniciais de configuração/teste incorreto ficam separados dos finais.

SQL independente confere chaves/EPA e o predicado DES nos brutos das cinco temporadas. A/B e sensibilidades são comparados exatamente à v1; HTTP confere índice e todos os 68 detalhes. O DOM foi reconciliado nos cinco exemplos, incluindo 260 coordenadas observadas, com tolerância 1e−12. Períodos semanais foram confrontados com as jogadas de todos os 68 participantes em todos os nove recortes (612 combinações), sem rateio.

[Preservação](evidence/preservation-summary.json): M3/B2, fontes, pesquisa anterior e build público intactos; cinco arquivos públicos idênticos em bytes. Servidor novo e entrada local separados; a configuração da terceira leitura recusa build público. O build público continua `npm --prefix web-ui run build`; não contém esta interface nem seus dados.

A recuperação inclui o pacote da terceira leitura, patch de código sobre a base Git exata, documentação e manifests. As fontes brutas pinadas e stores M3/B2 permanecem em seus caminhos originais preservados; não são duplicados no arquivo. Para reconstituir somente a leitura local, extrair o arquivo e apontar `NFL_PROGRESSION_STORE` ao `restored/store`, mantendo a base e os demais stores existentes. Não sobrescrever a base/pacotes anteriores.
