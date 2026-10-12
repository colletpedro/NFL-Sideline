# E5b-5 — candidata ao aceite do orquestrador

Implementação e provas concluídas em 12/10/2026. **Não é aceite automático.**
Base exata `b6b244bb68f17d089135f8ad3665747bb6c140c5`; branch `codex/metrics-pipeline-e5b5`.
Worktree criada limpa, sem partir de main ou copiar alterações não commitadas:
`/Users/pedrocollet/.codex/worktrees/metrics-pipeline-e5b5/NFL Sideline`.
Código/testes/harness final verificado: `178a5e2fca564566cf7e078fd9e975635a571712`.
O commit posterior de entrega acrescenta somente documentação/evidências;
[reconciliação](delivery-verification.json) confere hashes contra esse commit testado.

## Modos e comandos

Todos os comandos partem da raiz da worktree. `NFL_ETL_PYTHON` representa um
Python 3.11+ já provisionado com as dependências do projeto. Nenhum modo novo
usa .env, credenciais ambientais, aquisição ou banco remoto.

| Modo | Efeito | Obrigatório |
|---|---|---|
| `--game-metrics off` (default) | ETL legado, com configuração anterior | Nenhum argumento de métricas; argumentos novos são recusados |
| `--game-metrics plan` | Congela fontes, valida e prepara artefato offline; não executa loaders | `--metrics-inputs`, `--metrics-output` novo |
| `--game-metrics local` | ETL local legado seguido de adapter/prepare/archive/writer | `--skip-acquire`, `--data-dir`, inputs/output e duas configurações locais + archive |

```bash
# Planejamento somente da etapa nova; não cria ingestion_runs.
PYTHONPATH=etl-pipeline/src "$NFL_ETL_PYTHON" etl-pipeline/run_pipeline.py \
  --season 2026 --game-metrics plan \
  --metrics-inputs /private/tmp/minhas-fontes.json \
  --metrics-output /private/tmp/e5b5-plano-NOVO

# Execução integrada exclusivamente na instância própria identificada.
PYTHONPATH=etl-pipeline/src "$NFL_ETL_PYTHON" etl-pipeline/run_pipeline.py \
  --season 2026 --game-metrics local --skip-acquire \
  --data-dir /private/tmp/minhas-fixtures \
  --metrics-inputs /private/tmp/minhas-fontes.json \
  --metrics-output /private/tmp/e5b5-tentativa-NOVA \
  --legacy-local-config /private/tmp/instancia-propria/domain.json \
  --metrics-local-config /private/tmp/instancia-propria/writer.json \
  --metrics-archive /private/tmp/meu-archive-identificado
```

Plan recusa `--skip-acquire`, `--data-dir` e argumentos SQL/archive. Local não
aceita aquisição nem factory legada injetada que burle seu preflight. `--season`
continua centralizado em seasons.py; chaves do manifesto precisam corresponder
exatamente à seleção normalizada. Cada temporada calcula um lote inteiro;
calculation_id nunca é gerado por jogo.

Formato do arquivo de seleção (paths absolutos, `metadata` obrigatório, anulável):

```json
{
  "inputsVersion": 1,
  "seasons": {
    "2026": {
      "calendar": ["/private/tmp/minhas-fixtures/raw/schedules/season=2026/schedules.parquet"],
      "pbp": [
        "/private/tmp/minhas-fixtures/raw/pbp/season=2026/pbp.parquet",
        "/private/tmp/minhas-fixtures/raw/pbp/season=2026/extra.parquet"
      ],
      "metadata": null
    }
  }
}
```

Plan admite JSON e Parquet explícitos. Local exige calendário canônico único e
inventário Parquet PBP inteiro listado, com `pbp.parquet` quando houver arquivos.
Partições extras pertencem ao lote novo; **a seleção e as fórmulas legadas continuam
canônicas**, sem concatenação/regravação de fontes. Assim, contagens antigas de
rows_pbp/rows_metrics e reconciliação nova podem diferir legitimamente.
Todos os loaders leem cópias dos mesmos bytes originais; arquivos extras não são
escolhidos durante a execução. Troca/corrupção de fonte, metadados, cópia congelada
ou inventário causa falha. Os JSONs operacionais guardam descritores/hashes,
cópias e caminhos da seleção legada, metadados, versões e IDs completos.

As duas configurações JSON têm exatamente `host`, `port`, `database`, `user`,
`password`, `instance_id`. Host somente `127.0.0.1`/`::1`, porta explícita e banco
`nfl_e5b2_` + os primeiros 12 caracteres do UUID sem hífens. Os endpoints reais e
markers devem coincidir. PG* ambiental, DSN remoto, login administrativo (inclusive
membro de role administrativa), login de domínio pertencente ao writer ou
permissões de domínio insuficientes são recusados antes da primeira escrita.
O writer continua com seus próprios guardrails, schema e grants aceitos.
No harness descartável, o login de domínio tem SELECT/INSERT/UPDATE somente nas
cinco tabelas legadas necessárias, USAGE da sequência ingestion_runs e leitura
do marker. Policies locais dão acesso sob RLS sem BYPASSRLS; não são migrations.

## Ordem, estados e limites

Preflight de argumentos/inventários e ambas as conexões → tentativa UUID e
congelamento → start_run → validação local → seed_teams → games_market →
**load_metrics legado** → **etapa nova** (adapter → validação prepare → archive →
writer privado) → finish_success. A etapa nova obrigatoriamente termina antes do
sucesso global. Falhas interrompem a próxima temporada.

Journal `metrics-pipeline-attempt-v1`: eventos numerados append-only em diretório
UUID novo. Inclui temporada/ingestion_run, resultado da etapa, estado global,
fontes, versões, calculation/artifact/coverage IDs, archive, receipts e contagens.
FROZEN/RUNNING/CALCULATING/VALIDATED/PERSISTING/ARCHIVED/PRIVATE_COMMITTED/
FINISHING_GLOBAL/SUCCEEDED mostram as fronteiras conhecidas. FAILED conserva a
fronteira anterior, diagnóstico sanitizado e instrução de recuperação.

| Situação | Resultado da etapa | Consequência global |
|---|---|---|
| PBP ausente, inclusive parte do conjunto | UNAVAILABLE_MISSING_PBP, sem cálculo/archive/SQL privado | Só é tolerado com `--allow-missing-pbp` |
| Arquivo existente sem linhas | EMPTY_PRESENT como estado da fonte; PLANNED ou PERSISTED como resultado | Exige allow-missing-pbp; UNKNOWN sem prova |
| Planejamento válido | PLANNED, sem SQL | NOT_STARTED; não declara ingestão concluída |
| Persistência confirmada | PERSISTED | Pode terminar SUCCEEDED ou FAILED numa fronteira posterior |
| Falha antes do commit privado confirmado | FAILED | FAILED quando o status puder ser registrado; UNKNOWN se o registro falhar |

Arquivo vazio não representa ausência. COMPLETE vazio só existe com prova
explícita; jogo sem observação fica sem estatísticas. Conflitos, corrupção e erros
de schema/metadados continuam fatais mesmo com ausência tolerada. Scores/kickoff/
coleta/receipts/persisted_at não viram provas de encerramento, início efetivo,
completude ou conhecimento histórico. Nenhuma análise/documento tático é exigido.

**Não há atomicidade distribuída.** Loaders/status legados têm commits próprios;
archive CAS é separado; writer usa outra conexão/transação. Antes do archive
podem existir commits legados e artefato. Após archive e antes do commit privado,
blobs/receipts são preservados e reutilizáveis. Após commit privado e antes do
status global, métricas válidas permanecem, mesmo com run FAILED. Erro de conexão
no commit pode exigir reconciliação; não é prova de rollback. Falha ao registrar
FAILED não esconde a exceção original. Interrupção abrupta pode deixar RUNNING;
o journal mostra somente a última fronteira confirmada.

Reexecutar com **destino operacional novo** e mesmo archive. Nova tentativa tem
UUID/ingestion_run novos, preservando todas as anteriores. Adapter/prepare/writer
revalidam conteúdo; CAS, receipts e registros válidos são reutilizados sem mover
a primeira observação. Conteúdo corrigido gera revisão nova e preserva a anterior.
Não se apagam registros válidos para simular rollback total.

## Gates e prova real

- **496 testes ETL offline**: 434 anteriores +62 desta integração, zero falhas/skips.
- E5a: **26 exemplos, 23 testes e 12 hashes congelados**.
- CLI E5b-1 byte a byte e dry-run E5b-2 sem DB/archive; regressões temporais,
  identidades, materializador e contraprovas aceitas preservadas.
- **51 regressões PostgreSQL reais E5b-2** em outra instância nova própria. A suíte
  histórica limpa somente suas relações de teste; nunca o banco da prova integrada.
- PostgreSQL integrado real: legado desativado, integração, idempotência, revisão
  corrigida, falhas após archive e commit privado, recuperação, ausência/vazio,
  recusa efetiva de login CREATEDB/remoto, IDs/somas/contagens e fail-fast.
- Java 21: `mvn -f core-api/pom.xml -o clean package -DskipTests`, **BUILD SUCCESS**,
  seguido de leitura real do artefato recém-materializado. Não se usou target antigo.
  Java não mudou; sua suíte completa não foi repetida. [Log do rebuild](java-build.txt).
- `git diff --check` passou; gate próprio protege E5a, adapter, writer/archive,
  materializador/temporal, Java/frontend/schema/loaders/workflow e evidência histórica.

[Gate offline](offline-verification.json), [prova integrada](database-proof.json),
[regressões SQL](postgres-regressions.json), [desenho anterior à implementação](DESIGN.md).
Archives novos têm receipts novos; isso pode mudar input_id/audit_id temporal.
O gate verifica os invariantes da reprodução nova e a integridade dos goldens
históricos separadamente, sem adulterar verificadores ou exigir IDs falsamente iguais.

Fixture reproduzível: quatro jogos, dois observados, COMPLETE vazio e jogo sem PBP;
seis linhas brutas em duas partições, cinco únicas, uma réplica. Para A/off/general
no primeiro jogo: volume 3, EPA_n 2, EPA_missing_n 1, success_n 1, soma **-0.5**;
segundo jogo: volume 1 e soma **0.5**. A reexecução inicial inseriu zero e reutilizou
66 registros, com linhas/persisted_at/blobs/receipts idênticos. A correção anterior
preservou todas as linhas/receipts. O lote com prova de COMPLETE vazio tem quatro
associações e 36 somas; o jogo sem observação não ganha grupos zero.

Versões: adapter `1.0.0`, definição `1.0.0`,
população `classified-scrimmage-v1`, artefato `metrics-offline-v1`;
materialization-v2 → input-v3 → algoritmo 1.1.0 → result-v3.

| Identidade da prova final | Valor |
|---|---|
| calculation_id | `sha256:00989e1760f7fbce6eec8d96cefbafe07566b99ce33466e338149031b5d42992` |
| artifact_id | `sha256:d5a82ad18fb82e8f6282bca75c6c369363903dfc1acf6a123cb898db89289a62` |
| archive_id | `50a90c03-f793-4bb3-a4c2-3245275c8eab` |
| materialization_id | `sha256:25cfde0c15db672b019a7cb983ad21274b6146b95e499325f179886997bbf045` |
| input_id | `sha256:05c335c47e6438fd872ee2ebfe11f643d223dca69b0e7f9fb3c9c2a165e5fec7` |
| result_id | `sha256:6d21c6f13e8c51f6c5e687089f9d4a165f439e99bc5bc6d98d3049d1303b723f` |
| SHA-256 JAR offline | `3b98051b415872452a71572d1c2674fd30ae104d580a0662ae565c45d62ef9ce` |

Hashes de todas as fontes/arquivos, coverage IDs e receipt IDs constam na prova
JSON. Extração em snapshot read-only, recuperação integral do archive,
materialização sem documentos artificiais e leitor Java passaram. PIT ficou
**UNKNOWN/sem agregados**, como exigido pela falta de provas históricas.
Dados sintéticos não certificam temporadas reais.

Reprodução (roots e output obrigatoriamente novos; runtime deve existir):

```bash
PYTHONPATH=etl-pipeline/src "$NFL_ETL_PYTHON" docs/plans/metrics/e5b-5/verify.py \
  --candidate "$(git rev-parse HEAD)" --output /private/tmp/e5b5-gate-NOVO.json

PYTHONPATH=etl-pipeline/src "$NFL_ETL_PYTHON" docs/plans/metrics/e5b-5/proof.py \
  --instance-root /private/tmp/e5b5-instancia-NOVA \
  --workspace /private/tmp/e5b5-prova-NOVA --output /private/tmp/e5b5-prova-NOVA.json \
  --pg-bin /private/tmp/nfl-e5b2-pg-runtime/bin \
  --java /opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home/bin/java

PYTHONPATH=etl-pipeline/src "$NFL_ETL_PYTHON" docs/plans/metrics/e5b-5/postgres_regressions.py \
  --root /private/tmp/e5b5-regressoes-NOVAS \
  --pg-bin /private/tmp/nfl-e5b2-pg-runtime/bin \
  --output /private/tmp/e5b5-regressoes-NOVAS.json
```

O gate exige HEAD declarado e fontes/testes commitados. O harness injeta falhas
somente por hooks internos de teste, sem flags operacionais escondidas. O fluxo
local real passa por `run_pipeline.main`; prova do default usa a factory existente
apontando explicitamente ao banco próprio, sem acionar sua configuração ambiental.

## Instâncias encerradas e evidências preservadas

Prova final: UUID `6674d6dc-8d99-40ae-b198-bbf35694537a`, banco `nfl_e5b2_6674d6dc8d99`,
porta **49558**, root `/private/tmp/nfl-e5b5-instance-20261012-06`.
Runtime PostgreSQL 17.6 existente, sem download. pg_ctl status=3, postmaster.pid
ausente, probe de bind livre. Instância separada de regressões também encerrada.
Todas as instâncias pertencem exclusivamente a esta tarefa; nenhum serviço global,
stack existente ou cluster histórico foi reutilizado/resetado.

Tentativas anteriores, inclusive as duas diagnósticas, permanecem nos roots próprios
[registrados](prior-attempts.json). Seus reports/logs, clusters desligados, CAS,
receipts e fontes não foram apagados. A primeira corrigiu representação do endpoint;
a segunda corrigiu a fixture para satisfazer o inner join legado. Nenhum loader
foi ajustado para obter sucesso. [Conferência final de encerramento](shutdown.json).
O workspace final é `/private/tmp/nfl-e5b5-proof-20261012-06`; fontes, artefatos,
journals, extração, materialização e resultado temporal ficam preservados nele.
Credenciais geradas ficam somente nos roots privados, fora da entrega versionada.

Commits locais: `728396e` desenho; `f4d3cc7` integração; `4251905` testes/prova;
`9731677` gate com identidades independentes; `41c6a0e` validação de metadata/
inventário; `178a5e2` privilégio mínimo do harness; commit posterior de documentação.
HEAD final e estado limpo da worktree são informados na entrega do chat; nenhum
commit foi publicado, mergeado ou aplicado em main.

## Limites de entrega

Integrado **somente ao ETL local optativo**. Fluxo semanal/produção continuam
no modo legado, sem nova configuração ou conexão exigida. Nada mudou em workflow,
loaders/fórmulas, contratos aceitos, schema/grants versionados, Java/frontend,
snapshots, análises/aprovações, publicação ou ambiente remoto.
Supabase completo/advisors permanece **pendente**; migration remota não autorizada.
E5b-6, backfill, aquisição, modelos, integração editorial/JPA e publicação não foram
iniciados. Próximo ato é o aceite independente do orquestrador.
