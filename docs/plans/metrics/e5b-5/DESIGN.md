# E5b-5 — desenho de execução controlada

Base exata b6b244bb68f17d089135f8ad3665747bb6c140c5; branch
codex/metrics-pipeline-e5b5. Worktree nova e limpa, sem copiar arquivos locais.
Este desenho precede a implementação. Candidata a aceite, não aceite implícito.

## Modos e entradas

`--game-metrics off` é o default: nenhuma configuração/conexão/archive nova.
`--game-metrics plan --metrics-inputs FILE --metrics-output NEW_DIR` executa
somente planejamento offline. Não lê .env, não adquire, não conecta SQL, não
cria ingestion_runs e não escreve archive. `--skip-acquire`/`--data-dir` e
configurações SQL/archive são recusadas neste modo para evitar ambiguidade.
`--game-metrics local` exige `--skip-acquire`, `--data-dir`, os dois argumentos
anteriores, `--legacy-local-config FILE`, `--metrics-local-config FILE` e
`--metrics-archive DIR`. O destino operacional é sempre novo; o archive CAS
identificado pode ser reutilizado. Não há credenciais ambientais/fallback.

Inputs JSON versão 1: `{"inputsVersion":1,"seasons":{"2026":{"calendar":["/absolute/schedules.parquet"],"pbp":["/absolute/pbp.parquet"],"metadata":null}}}`.
As chaves de seasons correspondem exatamente à seleção central seasons.py.
Metadados opcionais apontam para JSON explícito, congelado com seu hash.
Planejamento admite fontes JSON/Parquet. Local exige calendário único no caminho
canônico do loader e inventário PBP Parquet inteiro explícito por temporada,
incluindo pbp.parquet quando existir. Partições adicionais são processadas pelo
adapter; o loader legado mantém sua seleção canônica e fórmulas existentes.
Não se escolhe arquivo mais recente. O relatório distingue essas seleções.

## Ordem, fontes e identidades

Preflight valida todos os argumentos/destinos/configurações, inventários e ambas
as conexões antes da primeira escrita. Cada conexão usa loopback literal,
parâmetros explícitos, marker UUID do harness E5b-2 e login não administrativo.
Banco, host, porta e UUID devem coincidir. O writer continua usando a API aceita.
O login de domínio separado só recebe SELECT/INSERT/UPDATE nas quatro tabelas
legadas e ingestion_runs, sequências necessárias e SELECT no marker na instância
própria; não pertence ao writer e não recebe bypass RLS. O harness cria políticas
locais nas tabelas de domínio, sem alterar migrations/grants versionados.

Por temporada: tentativa UUID + congelamento → start_run → validação local →
seed_teams → games_market → métricas legadas → etapa de métricas por jogo →
finish_success. As etapas legadas leem cópias dos mesmos bytes congelados.
A etapa nova usa read_inputs/calculate/write_artifact/prepare/persist aceitos,
sem fórmulas novas e sem calculation_id por jogo. Antes de persistir, verifica
novamente os hashes originais e congelados, incluindo metadata. prepare valida
artefato e fontes integralmente; persist revalida seu snapshot em memória.

## Estados e ausência

Journal append-only `metrics-pipeline-attempt-v1`, eventos numerados publicados
sem substituição: FROZEN, RUNNING, VALIDATED, ARCHIVED, PRIVATE_COMMITTED,
SUCCEEDED; falhas registram FAILED com última fronteira conhecida. Resultado
da etapa e estado global são separados. Inclui temporada/run, UUID da tentativa,
fontes/hashes/versões, calculation/artifact/coverage IDs, archive e contagens.
Falha no journal é fatal; falha secundária de journal/FAILED não substitui a
exceção original. Interrupção abrupta deixa última fronteira e status global
potencialmente RUNNING; reexecução usa destino/UUID novos, preserva anterior.

PBP ausente (lista vazia ou caminho explicitamente ausente) exige
--allow-missing-pbp e resulta UNAVAILABLE_MISSING_PBP: sem cálculo, archive ou
persistência privada. Não se fabrica arquivo vazio. Arquivo vazio existente é
EMPTY_PRESENT: adapter conserva NO_SOURCE_OBSERVATION/UNKNOWN, e COMPLETE vazio
somente com prova explícita. Requer allow-missing-pbp quando não há linhas para
compatibilidade com a validação legada. Ausência de parte do conjunto torna a
etapa inteira indisponível; não persiste subset silencioso. Corrupção, schema,
conflito, arquivos trocados são fatais, mesmo com allow-missing-pbp.

Não inferir encerramento de score, início efetivo de kickoff, completude da
coleta ou disponibilidade histórica de receipt/persisted_at. PIT sem provas
continua UNKNOWN. Ingestão não exige documento tático ou gera análises.

## Transações e recuperação

Cada loader e status global mantém seus commits. O archive é CAS independente;
a persistência privada é uma transação separada. Não existe rollback total ou
atomicidade entre SQL legado, writer, archive e filesystem.

Antes do archive: somente artefato/tentativa e commits legados podem existir.
Após archive/antes do commit: blobs/receipts ficam válidos para reuso; SQL privado
faz rollback. Após commit/antes de finish_success: métricas privadas válidas
permanecem; falha global não as apaga. Falha ao registrar FAILED pode deixar
RUNNING; journal conserva diagnóstico e limites. Resultado do commit pode ser
indeterminado em falha de conexão: reexecutar e comparar conteúdo imutável.

Nova tentativa recalcula/valida a partir das fontes congeladas; o writer verifica
conteúdo existente antes de reutilizar CAS/receipts/linhas. Mesmos bytes e
metadados preservam IDs, não duplicam conteúdo; correção legítima gera revisão
nova e preserva anterior. Nenhum artifact existente é aceito sem prepare.

Fluxo semanal, produção, Supabase completo/advisors, E5b-6, backfill, publicação,
editorial/JPA/frontend e aprovações continuam fora desta entrega.
