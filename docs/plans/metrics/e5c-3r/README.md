# E5c-3R — operação e recuperação reproduzíveis

Candidata ao aceite. [Protocolo anterior à carga](PROTOCOL.md), [relatório](REPORT.md),
[identidades](inventory/identities.json), [inventário completo de hashes](inventory/artifact-hashes.json).
A execução usa código aceito sem alteração; os scripts desta pasta são wrappers novos.
Não executar `real_proof.py` histórico com IDs novos, nem alterar seus alvos.

## Ler os artefatos preservados

Da raiz da worktree `codex/metrics-real-recovery-e5c3r`, sem carregar `.env`:

```sh
NFL_PY='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export PYTHONPATH="$PWD/etl-pipeline/src"
export PYTHONDONTWRITEBYTECODE=1
NFL_ART='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery/20261019T024130Z-50e03b27'
NFL_BACKUP='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/20261019T024130Z-50e03b27'
"$NFL_PY" -B -m nfl_sideline_etl.metrics_observations validate --bundle "$NFL_ART/bundle"
"$NFL_PY" -B -m nfl_sideline_etl.metrics_observations inspect --bundle "$NFL_BACKUP/bundle"
```

`inventory/files.json` enumera 162 arquivos / 249.063.080 bytes por cópia.
`SHA256SUMS.json` em cada raiz cobre todos os demais arquivos; seu próprio hash
está em `recovery-summary.json`. Cópias completas incluem fontes, archive,
journals de plan/carga/reexecução, artifacts, snapshot das onze tabelas privadas,
extração relacional, seleção, materialização-v2/input-v3, pedido e bundle.
Operações/PGDATA/credenciais ficam em `editorial/local-artifacts/operations/`
com o mesmo run-id; não fazem parte da distribuição nem do Git.

Os 48 documentos de `review-observations.json` são um extrato de revisão dos
bytes de `bundle/observations.json`, não uma fonte operacional. O bundle contém
`shared-source/` integral; o reader sempre verifica originais e rederiva.
O extrato histórico foi apenas alvo de comparação depois de verificar os quatro
hashes originais; não forneceu números à cadeia.

## Recuperar exclusivamente pela segunda cópia

O ensaio [restore-drill.json](restore-drill.json) executou este caminho sem banco.
Escolher três destinos absolutos novos e disjuntos, fora de web-ui:

```sh
"$NFL_PY" -B docs/plans/metrics/e5c-3r/restore.py \
  --backup "$NFL_BACKUP" \
  --destination '/caminho/duravel/novo/artefatos' \
  --config '/caminho/duravel/novo-operador/config.json' \
  --report '/caminho/duravel/novo-operador/restauracao.json'
```

O script confere todos os hashes, copia sem sobrescrever, lê materialização e
bundle completos pelo reader aceito, verifica que o backup não mudou e cria uma
**configuração externa nova** com path restaurado/pin conferido. A configuração
congelada dentro da cópia é registro da execução original; não é usada para
resolver o path novo. Não há banco, rede, novos receipts ou nova derivação.
Os três destinos devem ser disjuntos entre si e também do backup: nunca coloque
a cópia, a configuração ou o relatório dentro da árvore preservada. O preflight
recusa essa situação antes de ler/copiar, além de recusar symlinks e `..`.
O reader do bundle funciona em paths físicos diferentes, sem symlinks.
[backup-verification.json](backup-verification.json) também demonstra leitura
integral com a primeira localização temporariamente inexistente.

**Restrição intencional do archive bruto:** receipts incluem `archive_root` em
sua identidade; `metrics_materialization.recovery.recover` recusa a cópia bruta
em outra root. Não alterar receipts nem os rehashear para fazê-los antigos.
O contrato E5b-4 já diz: “Outra root é outra observação”. Use materialização/bundle
autocontidos para recuperação em path novo. Para refazer a extração do archive
bruto sem novos receipts, restaure bytes ao path nominal registrado **somente
quando esse destino não existir**; jamais sobrescreva uma localização sobrevivente.
Uma futura portabilidade de receipts brutos exigiria contrato/aceite separado.
Esta entrega não modifica esse comportamento nem anuncia recover bruto relocável.

Duas cópias no mesmo disco protegem da perda de temporários. Não protegem da perda
do disco e não constituem recuperação de desastre.

## Abrir o laboratório com os dados reais

Node 24 e `web-ui/node_modules` já existentes. Nesta worktree node_modules é um
symlink para dependências locais do checkout original; não houve instalação.
A configuração versionada contém apenas path local e pin, sem credenciais:

```sh
export NFL_OBSERVATION_PYTHON="$NFL_PY"
export NFL_OBSERVATION_CONFIG="$PWD/docs/plans/metrics/e5c-3r/lab-config.json"
/opt/homebrew/opt/node@24/bin/node web-ui/scripts/editorial-dev.mjs
```

Abrir `http://127.0.0.1:18083/`, selecionar **Observações auditáveis** e o bundle
**Arquivo 2026 W1, W2, W1–2; NE POST2025; lacuna BAL W3**. CURRENT é a origem
declarada, sem atualização corrente. Ctrl-C encerra esse servidor próprio.
Para uma cópia restaurada, usar o `--config` externo criado por restore.py.
Cada startup lê o bundle completo; não recebe snapshot DTO salvo.

Com esse servidor ativo e saída nova:

```sh
"$NFL_PY" -B docs/plans/metrics/e5c-3r/probes.py http \
  --config "$NFL_OBSERVATION_CONFIG" --output /private/tmp/e5c3r-http-new.json
"$NFL_PY" -B docs/plans/metrics/e5c-3r/probes.py negatives \
  --config "$NFL_OBSERVATION_CONFIG" --output /private/tmp/e5c3r-negatives-new.json
export PLAYWRIGHT_MODULE='/Users/pedrocollet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
/opt/homebrew/opt/node@24/bin/node docs/plans/metrics/e5c-3r/browser.cjs /private/tmp/e5c3r-browser-new
```

Parar o servidor manual antes do ensaio de ciclo de vida abaixo. Ele inicia e
encerra somente seus próprios processos, usa cópia descartável canônica
`/private/tmp` (os aliases `/tmp`/`/var` são recusados pelo safe-path aceito),
e mantém logs/cópia em caso de falha:

```sh
/opt/homebrew/opt/node@24/bin/node docs/plans/metrics/e5c-3r/lifecycle.cjs \
  "$NFL_OBSERVATION_CONFIG" /private/tmp/e5c3r-lifecycle-new
```

O ensaio verifica bytes congelados após adulteração no disco; reinício recusa
entrada e responde 409 à sessão antiga; a preferência removida não faz fallback.
Depois restaura somente a cópia descartável, reinicia/revalida e confirma bytes e
escolha. Conteúdo idêntico após reinício conserva legitimamente sessionId; 409
requer conteúdo de sessão diferente, não apenas um PID novo.

## Refazer carga/derivação com tempos e IDs novos

Não é necessário para usar/restaurar o bundle. Requer os quatro Parquets locais
autorizados e a imagem **já local**. Conferir Docker ativo/espaço/portas e ler o
protocolo antes. Não iniciar Docker/Supabase global ou instalar dependências.
Todos os destinos abaixo são novos, absolutos, disjuntos e fora de `/tmp`/web-ui:

```sh
"$NFL_PY" -B docs/plans/metrics/e5c-3r/recover.py \
  --original '/Users/pedrocollet/Downloads/NFL Sideline' \
  --primary '/caminho/duravel/real-recovery/novo-run-id' \
  --backup '/caminho/duravel/backups/novo-run-id' \
  --operations '/caminho/privado/operations/novo-run-id' \
  --image sha256:6942962433a569e87f228b4d4ab7e11db5deca64e43babb3a038443ad6c4f1bb \
  --report '/caminho/duravel/relatorio-novo.json'
```

Imagem local PostgreSQL 17.6, `--pull never`, initdb vazio/entrypoint próprio,
UUID/label, bind host em 127.0.0.1, servidor PostgreSQL em loopback interno e relay
BusyBox nc local. O endpoint real é conferido pelo guard aceito sem relaxamento.
Não usa o entrypoint Supabase nem conecta a container existente. Aplica exatamente
as três migrations versionadas ao próprio banco, conserva roles/grants/RLS dos
harnesses, usa logins não administrativos separados. Sem Auth/PostgREST/advisors;
isso não certifica a stack Supabase completa.

O código aceito é conferido contra a base, os quatro hashes são fixos, o plan e
auditor independente rodam antes do banco. Carga, idempotência, SQL exato,
extração e materialização usam componentes aceitos. Nenhum PIT vazio/Java é fonte
de números. Instância própria encerra em finally; arquivos/relatório e duas cópias
permanecem mesmo em falha posterior ao início. Se faltar runtime, concluir
verificações independentes e reportar o bloqueio; nunca fabricar persistência.

`summarize.py --artifacts <raiz-completa> --output <diretorio-novo>` produz
inventários/tabela de IDs a partir da execução preservada e referências históricas.
`inventory/accepted-code-hashes.json` registra os bytes usados. Igualdade de
cálculo/cobertura/associação temporal não exige igualdade de input/materialização,
archive/receipts/observação/bundle ou sessão.

## Testes reproduzidos

```sh
"$NFL_PY" -B -m pytest -p no:cacheprovider -q \
  etl-pipeline/tests/test_metrics_lab.py etl-pipeline/tests/test_metrics_observations.py \
  etl-pipeline/tests/test_metrics_materialization.py etl-pipeline/tests/test_metrics_persistence.py \
  etl-pipeline/tests/test_metrics_pipeline.py docs/plans/metrics/e5b-6/test_audit.py
"$NFL_PY" -B -m pytest -p no:cacheprovider -q etl-pipeline/tests/test_offline_metrics.py
"$NFL_PY" -B contracts/metrics/e5a-v1/verify.py
# Python 3.14 local já possui jsonschema; o venv ETL não possui esse pacote.
/opt/homebrew/opt/python@3.14/bin/python3.14 -B -m unittest discover \
  -s contracts/metrics/consumption-e5c1-v1 -p 'test_*.py'
/opt/homebrew/opt/python@3.14/bin/python3.14 -B docs/plans/metrics/e5c-2/check_schema.py \
  --observations "$NFL_ART/review-observations.json"
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
git diff --check
```

Não executar mains de gates históricos contra bases documentais novas.
Não há aquisição, `.env`, modelo, novas métricas, comparação, pregame, snapshots,
aprovações, processo semanal, publicação, merge em main, push ou deploy.
