# E5b-2 — persistência local e proveniência

Entrega isolada sobre `882c9013ec1a1cd08f2d0b7049fb74ff1cdb8491`, branch
`codex/metrics-persistence-e5b2`. [Desenho anterior ao DDL](DESIGN.md),
[prova real selecionada](database-proof.json) e [verificação](verification.json).
E5a/E5b-1, fixtures congeladas, pipeline, Java, frontend e snapshots intactos.

## Schema, identidade e acesso

Migration criada com Supabase CLI **2.117.0**, após `migration new --help`:
`supabase migration new metrics_persistence_e5b2` produziu
`supabase/migrations/20261009180021_metrics_persistence_e5b2.sql`.
Baseline/hardening/config principal não foram editados. Onze tabelas privadas;
as três relações propostas são mantidas, com associações para partições,
cálculos, artefatos e receipts explicadas no desenho. Um arquivo pode conter
várias temporadas; temporada/fase/round/participantes são congelados por jogo,
não atribuídos artificialmente à identidade dos bytes.

`metric_persistence_writer` é NOLOGIN, NOBYPASSRLS, sem privilégios administrativos.
SELECT/INSERT e policies restritas a essa role nas novas tabelas; nenhuma permissão
UPDATE/DELETE/TRUNCATE, nem acesso a entidades legadas. FKs confirmam existência
de jogos/times sem SELECT ou seed pelo writer. O jogo congelado vem do calendário
validado: não depende de valores mutáveis da linha de domínio para reconstrução.
Schema, domains, tipos compostos e tabelas sem grants públicos; RLS ENABLE/FORCE,
sem policies PUBLIC/anon/authenticated/service_role ou SECURITY DEFINER.

SQL impõe bigint não negativo, partição de EPA, success <= epa, numeric sem escala
fixa e sem NaN/Infinity, null somente sem observações EPA, fase/round,
estado/escopo, FKs e unicidade. Writer recalcula o artefato inteiro com o adapter
aceito: confirma contagens/reconciliações, participantes, 12 grupos por jogo
observado, cobertura dos jogos sem PBP, evidências e hashes canônicos. Não basta
rehashar estatísticas inválidas. JSON completo conserva versões, exclusões,
declarações e envelopes temporais com origem. Fonte COMPLETE vazia é distinta
de NO_SOURCE_OBSERVATION; UNKNOWN/PARTIAL ficam AUDITABLE_SUBSET/PARTIAL.

## Instância descartável usada

Docker API não respondeu a `docker ps`/`docker images` mesmo fora do sandbox,
com limites de 12 e 8 segundos. Tentativa de iniciar o runtime também não forneceu
inventário utilizável. Nenhuma stack/container foi criado/resetado pelo trabalho.
A alternativa permitida foi PostgreSQL **17.6**, compilado sob `/tmp` a partir da
[distribuição oficial](https://ftp.postgresql.org/pub/source/v17.6/).
A configuração principal especifica major 17. A alternativa reproduz as migrations
inteiras, roles anon/authenticated/service_role, default privileges/hardening,
RLS e um login writer INHERIT sem bypass, autenticado por SCRAM no TCP.
Não reproduz Auth/PostgREST/Studio nem executa advisors de um stack Supabase.
Não há serviço Data API na alternativa; `[api].enabled=false` e
`auto_expose_new_tables=false` do projeto permanecem intactos.

Antes de iniciar, foram inspecionados portas/listeners, processos e disponibilidade
do runtime. Porta **55482**, bind exclusivo **127.0.0.1**, diretório/Unix socket
próprios; nenhum PostgreSQL existente foi usado. Quatro diretórios E5b-2 foram
criados: o primeiro encontrou erro de preparação CREATE DATABASE/autocommit,
corrigido no harness; o segundo validou o desenho inicial; o terceiro verificou o hardening de tipos; o quarto aplicou a
migration final, incluindo contadores auxiliares bigint, em cluster limpo. Todos são desta entrega e foram encerrados.

Instância final: `nfl_e5b2_56ce36bfb0a8`, UUID
`56ce36bf-b0a8-4c63-a79a-0b21c67936c5`, root
`/tmp/nfl-e5b2-instance-20261009-04`. Runtime `/tmp/nfl-e5b2-pg-runtime`.
Credenciais aleatórias de teste só em `writer.json` local mode0600, diretório
mode0700; não versionadas. Marker `e5b2_instance.identity` só no harness, nunca
na migration do projeto. Writer recusa host remoto/DNS/socket/DSN implícito,
PG* ambiente, banco sem nome UUID correspondente, marker diferente e login
privilegiado ou sem herança explícita do writer. Nenhuma leitura de .env.

## Reprodução do runtime

Pode-se usar binários PostgreSQL 17 locais já instalados, sem serviço global.
Na execução registrada, fonte e runtime ficaram sob `/tmp`:

```bash
curl -L -fsS https://ftp.postgresql.org/pub/source/v17.6/postgresql-17.6.tar.bz2 \
  -o /tmp/nfl-e5b2-postgresql-17.6.tar.bz2
tar -xjf /tmp/nfl-e5b2-postgresql-17.6.tar.bz2 -C /tmp
cd /tmp/postgresql-17.6
./configure --help
./configure --prefix=/tmp/nfl-e5b2-pg-runtime --without-icu \
  --without-readline --without-zlib CC=clang \
  CFLAGS='-isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX26.sdk' \
  LDFLAGS='-isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX26.sdk'
make -j6
make install
```

O SDK26 explícito corrige incompatibilidade local do linker/SDK27. Em Linux ou
outro macOS, use o compilador/SDK válido dessa máquina. Não instala extensão.
Consulte `--help` dos comandos do runtime antes de usá-los; o harness registra
as ajudas de initdb/pg_ctl/psql e o inventário de portas dentro da instância.

Da raiz **da worktree** (Python3.11+ com dependências do ETL instaladas):

```bash
export PYTHONPATH=etl-pipeline/src
export PYTHONDONTWRITEBYTECODE=1
python -B docs/plans/metrics/e5b-2/instance.py --help
python -B docs/plans/metrics/e5b-2/instance.py start \
  --pg-bin /tmp/nfl-e5b2-pg-runtime/bin \
  --root /tmp/nfl-e5b2-reproduce-new --port 55482

python -B -m pytest etl-pipeline -q -p no:cacheprovider
python -B -m pytest docs/plans/metrics/e5b-2/postgres_tests \
  --e5b2-instance-root /tmp/nfl-e5b2-reproduce-new -q -p no:cacheprovider
python -B docs/plans/metrics/e5b-2/proof.py --help
python -B docs/plans/metrics/e5b-2/proof.py \
  --instance-root /tmp/nfl-e5b2-reproduce-new \
  --workspace /tmp/nfl-e5b2-proof-new --output /tmp/nfl-e5b2-proof-new.json

python -B contracts/metrics/e5a-v1/verify.py
python -B -m unittest discover -s contracts/metrics/e5a-v1 -p 'test_*.py' -v
python -B docs/plans/metrics/e5a-review/reproduce_boundary.py
git diff --check

python -B docs/plans/metrics/e5b-2/instance.py stop \
  --pg-bin /tmp/nfl-e5b2-pg-runtime/bin --root /tmp/nfl-e5b2-reproduce-new
```

Start recusa diretório existente; escolha novos nomes/porta livre para repetir.
Stop verifica a identidade do diretório e do binário; não remove arquivos.
Suite SQL exige opção explicitamente: sem instância ela **falha**, não faz skip.
Antes de cada teste, somente as tabelas novas da instância identificada são
limpas pelo administrador do harness. Games/teams sintéticos são preparados
pelo harness; writer testado usa o login real limitado. `proof.py` exige tabelas
vazias e não limpa nada. Na execução registrada foi usado o venv já instalado
na origem com PYTHONPATH da worktree, sem instalação de bibliotecas.

## CLI separada

```bash
python -B -m nfl_sideline_etl.metrics_persistence --help
python -B -m nfl_sideline_etl.metrics_persistence --dry-run \
  --artifact docs/plans/metrics/e5b-1/synthetic-result \
  --calendar etl-pipeline/tests/fixtures/offline_metrics/calendar.json \
  --pbp etl-pipeline/tests/fixtures/offline_metrics/pbp.json \
  --archive /tmp/nfl-e5b2-archive-new

python -B -m nfl_sideline_etl.metrics_persistence --persist \
  --artifact docs/plans/metrics/e5b-1/synthetic-result \
  --calendar etl-pipeline/tests/fixtures/offline_metrics/calendar.json \
  --pbp etl-pipeline/tests/fixtures/offline_metrics/pbp.json \
  --archive /tmp/nfl-e5b2-archive-new \
  --local-config /tmp/nfl-e5b2-reproduce-new/writer.json
```

Sem `--persist`, apenas plano: não conecta, não lê configuração de conexão,
não cria archive. Calendar/PBP repetíveis conservam partições e multiplicidade.
Config explícita tem **exatamente** host, port, database, user, password,
instance_id. Não passe senha na CLI/DSN nem imprima writer.json. Import não
executa persistência. Erros retornam2 e categoria/hint sem texto do driver,
senha/DSN. FK informa referência de domínio ausente; não cria times/jogos.
Resumo retorna inserted/reused/conflicts. Conflito aborta a transação, nunca
reescreve registro. A CLI offline original continua independente e intacta.

Na [prova](database-proof.json): primeira carga **102 inserções**, incluindo
60 somas, seis coberturas, dois arquivos fonte, seis arquivos artefato e oito
receipts. Mesmo comando/arquivo: **0 inserções e 102 reutilizações**, mantendo
contagens, amostra, receipts e persisted_at. Os valores incluem EPA negativo,
zero e null; nonfinite preserva volume e não entra em epa_n.

`proof.py` gera correção sintética em diretório novo, usa o adapter aceito para
novo artefato e hashes ligados aos novos bytes, e persiste: **93 novas linhas,
9 reutilizações**, com fontes/cálculo/coberturas antigos recuperáveis. Não altera
fixture ou resultado congelado. Depois muda somente declaração de modelo:
novo cálculo/artefato, mesma cobertura e mesmas estatísticas, manifesto antigo
preservado (**18 novas linhas, 84 reutilizações**). Testes adicionais mudam
evidência de jogo e preservam cobertura UNKNOWN anterior junto da PARTIAL nova.

## Archive, receipts e recuperação

```text
ARCHIVE.json                         # archiveVersion1, UUID local
blobs/sha256/ab/<64 hex>              # bytes originais, sem extensão
receipts/<64 hex>.json                # primeiro receipt comprovado neste archive
```

Blob hash verificado ao gravar/reusar e recuperar; gravação via arquivo temporário,
fsync e hard-link exclusivo, sem substituição. Componentes symlink são recusados.
Mesmo hash não duplica blob/source revision; outra formatação de artefato pode
ter artifact_id diferente com mesmo calculation_id. `metric_artifact_file`
reconstrói os nomes e bytes originais, inclusive COMPLETED. `metric_source_member`
reconstrói kind/ordinal/descritor de cada partição e seus bytes arquivados.
Não copiar/mover archive existente: archive_root integra o receipt. Para outro
root use archive novo, que registra observação nova sem mudar a anterior.

Receipt contém receiptVersion1, receipt_id hash, archive UUID/root, SHA, locator,
observed_at UTC e origin (caminho explícito/format/kind ou arquivo de artefato).
Instante é desta observação local, separado de persisted_at SQL. Se cair após
blob e antes do receipt, reexecução registra somente a observação então provada;
não recupera horário hipotético. Declaração de available_at/ingested_at/modelo
ou event_upper_bound fica no manifesto original, com evidência/origem; não é
receipt local nem autenticação externa. Hash não comprova completude.

Ordem: validar/recalcular semântica → verificar destino local/role/marker →
arquivar/verificar bytes e receipts → transação SQL única. Rollback após fontes
iniciais e antes de commit deixa **zero diferença SQL**; archive pode conservar
conteúdo não referenciado. Prova provoca falha após inserções iniciais e depois
reexecuta, reutilizando os receipts sem deslocamento. Os testes também falham
imediatamente após archive e antes de commit. Não remover blobs compartilhados
ou válidos para desfazer falha. Não há atomicidade distribuída entre disco/SQL,
proteção contra administrador malicioso nem teste de queda de energia.

## Resultado e limites

**199 testes ETL offline**, **51 PostgreSQL reais**, **26 exemplos e 23 testes
E5a**, **12 hashes** preservados; nenhuma falha/skip final. Um teste inicial
esperava FK na chave já existente e foi corrigido para exercitar a FK com chave
nova; dados/fixtures congelados não foram ajustados. A CLI E5b-1 real gerou seis
arquivos byte a byte iguais ao exemplo aceito; guard de imports comprova caminho
sem DB/rede/.env. Os logs compactos estão neste diretório.

Os testes cobrem os 21 itens solicitados, incluindo partições sobrepostas,
multiplas associações do mesmo arquivo, concorrência real com duas conexões,
semântica adversarial rehashada, ausência/corrupção/marcador incompleto, precision
além do contexto Decimal, FK/constraints, acesso herdado, login superuser/marker
incorreto recusados e proibição de alterações pelo writer. Data API não executada;
roles públicas/tipos/schema/grants e RLS foram conferidos no PostgreSQL real.

Arquivo operacional final: `/tmp/nfl-e5b2-proof-final-04/archive` (20 blobs/receipts),
correções/artefatos pequenos na pasta irmã; regressão CLI em
`/tmp/nfl-e5b2-original-cli-regression`; fontes/binários/logs de compilação e quatro
clusters sob `/tmp`. Permanecem locais, não versionados; clusters parados, porta
55482 livre. Testes também criaram arquivos temporários pytest fora do checkout.
Worktree preservada para revisão. Nenhum container E5b-2 criado; inventário da
stack Docker existente permaneceu indisponível, sem ação nela.

Para E5b-3: bytes/calendário, composição de fontes, projeções/IDs, coberturas,
modelos/evidências de todos os cálculos, receipts prospectivos e instantes SQL
separados ficam recuperáveis. **Pendente:** seleção temporal, confirmação de
encerramento/precisão/DST e política de disponibilidade histórica. Nenhuma
escolha "atual/última", POINT_IN_TIME, aquisição/backfill/modelo, integração
semanal, Java, frontend ou publicação nesta entrega.

## Fontes oficiais consultadas

[Changelog Supabase](https://supabase.com/changelog.md), inclusive
[mudanças PostgreSQL17.11](https://supabase.com/changelog/postgres-15-19-17-11-breaking-changes):
ltree/pgcrypto/btree_gist/custom operators não são usados aqui.
[CLI migration new](https://supabase.com/docs/reference/cli/supabase-migration-new),
[config local](https://supabase.com/docs/guides/local-development/cli/config),
[RLS Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security),
[constraints PostgreSQL](https://www.postgresql.org/docs/current/ddl-constraints.html),
[numeric](https://www.postgresql.org/docs/current/datatype-numeric.html),
[INSERT](https://www.postgresql.org/docs/current/sql-insert.html) e
[GRANT](https://www.postgresql.org/docs/current/sql-grant.html).
Skills Supabase e Postgres aplicados, inclusive privilégios mínimos, RLS, índices
para FKs necessários e locks transacionais; nenhum MCP de banco remoto usado.
