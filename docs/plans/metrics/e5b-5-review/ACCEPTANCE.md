# Aceite E5b-5 — integração ETL optativa, 12/10/2026

**Aceita com ajustes de revisão e integrada localmente.** Candidata original
`6f2ad34eb7dc6a04e031acd352ec8f7151559aaa`, base
`b6b244bb68f17d089135f8ad3665747bb6c140c5`. Branch
`codex/metrics-integration-e5b5`, ajuste funcional/documental `8391b88`.
Main continua em `5096a585f0cc5455160ff9c2ee64555cfcb59fc0`.

## Escopo encerrado

O orquestrador conserva `off` como default, oferece planejamento somente da
etapa nova e execução `local` explícita com skip-acquire e duas conexões verificadas.
As etapas legadas leem cópias dos bytes congelados; o lote novo inclui o inventário
inteiro de partições. A etapa privada termina antes do sucesso global. Journal
por tentativa, IDs, contagens e fronteiras de recuperação ficam auditáveis.
Fórmulas, loaders, contratos, schema/grants versionados e workflow permanecem
intactos. As permissões de domínio do harness existem somente no cluster próprio.

Não há atomicidade distribuída: SQL legado, archive, SQL privado e status global
têm fronteiras próprias. Falha global posterior pode coexistir com conteúdo
privado válido. Reexecutar usa tentativa/destino novos e mesmo archive, com
revalidação e reuso de conteúdo; não apaga commits válidos para simular rollback.

## Ajustes necessários na revisão

1. O gate do HEAD original falhou ao comparar o diff contra a base: nove linhas
   do java-build.txt tinham espaços finais. Removidos somente esses espaços;
   original preservado na história da candidata e em cópia local. Hashes estão
   na [reconciliação](integration-verification.json). O gate anterior não foi
   apresentado como aprovado pelo orquestrador.
2. A falha de start_run sem ID devolvido marcava global_status NOT_STARTED.
   Uma contraprova simulada de commit com confirmação perdida demonstrou que
   essa classificação não prova ausência de linha SQL. Agora uma chamada já
   tentada dá UNKNOWN; falha anterior à chamada mantém NOT_STARTED. Sem ID não
   se atualiza arbitrariamente uma linha. Dois testes de fronteira preservam
   a exceção original. [Contraprova anterior](start-uncertain-before.json).

O segundo caso é uma condição simulada, não teste de perda real de rede. A
correção torna a classificação conservadora; não promete recuperação automática
do ID nem ausência de RUNNING após resultado indeterminado do commit.

## Verificação independente

- Gate integral da integração corrigida, commit 8391b88: **498 testes ETL**,
  sem falhas/skips; 26 exemplos/23 testes E5a/12 hashes; CLI E5b-1 byte a byte;
  dry-run E5b-2 sem banco/archive; regressões temporais/identidades/materializador;
  diff contra a base aprovado.
- **51 regressões PostgreSQL reais** em uma instância própria separada da prova
  operacional. Writer/archive não mudaram depois dessa execução.
- Prova operacional PostgreSQL da candidata e nova prova do checkout integrado
  após o ajuste: default legado, execução local pela CLI, idempotência, revisão
  corrigida, falhas/recuperação após archive e commit privado, fail-fast entre
  temporadas, guards de role/remoto, ausência/vazio e consumo temporal/Java.
- JAR reconstruído com Java 21, `mvn -o clean package -DskipTests`, e leitura do
  artefato novo. Java permaneceu inalterado; sua suíte completa não foi repetida.
  Binários anteriores do root foram arquivados antes do clean.

Na prova final: reexecução com **zero inserções e 66 reutilizações**, mantendo
linhas privadas/persisted_at/blobs/receipts. Correção preservou revisões anteriores.
Após falha em ARCHIVED, SQL privado ficou intacto, a próxima temporada não rodou
e recuperação reutilizou o mesmo artefato/receipts. Após PRIVATE_COMMITTED, estado
global FAILED conservou resultado privado PERSISTED; recuperação inseriu zero e
reutilizou 78 registros. PBP ausente não persistiu lote; arquivo vazio permaneceu
distinto. PIT sem provas continuou UNKNOWN/sem agregados.

[Gate offline](offline-verification.json), [prova operacional final](database-proof.json),
[regressões SQL](postgres-regressions.json), [reconciliação/hashes](integration-verification.json).
Conferidos 52 hashes de fontes/testes/gate/harness; 36 arquivos históricos não
rastreados preservados. As provas são sintéticas, não certificam temporadas reais.

O gate final foi executado antes desta atualização de docs/current-state.md e
do pacote documental de aceite. Seu guard de escopo congela esses documentos
contra a base da candidata; não se afirma que ele passa sem adaptação em todas
as futuras branches de integração. A implementação/testes não mudaram depois
do commit verificado 8391b88. Evidências e verificadores históricos preservados.

## Encerramento

Os harnesses encerraram exclusivamente suas instâncias. Prova final na porta
50500 e regressões na porta 49771: pg_ctl status=3, postmaster.pid ausente e probe
de bind aprovado. A primeira reprodução da candidata também foi encerrada.
Roots, CAS, receipts, fixtures e logs locais foram preservados em /private/tmp;
credenciais não foram versionadas. Os relatórios registram UUIDs/roots completos.
Não se reutilizou/resetou cluster histórico ou serviço global.

## Continuação

**Próxima entrega: E5b-6, backfill limitado e auditoria com dados locais reais.**
Definir antecipadamente arquivos/temporadas, hashes, volumes e critérios de
reconciliação, executando inicialmente apenas no ambiente descartável identificado.
Não adquirir dados, aplicar migration remota ou publicar como efeito deste aceite.
Supabase completo/advisors deve preceder aplicação fora desse ambiente.

Semanal/Production continuam desativados para o novo caminho; default legado
preservado. Nenhum backfill real, .env, banco remoto, aquisição, modelos,
Java/frontend modificado, integração editorial/JPA, snapshot/aprovação, merge em
main, push ou deploy. Qualidade editorial, E4 humano, BASIC/FULL, defeitos legados,
EVENT_END_EXACT e rollout público permanecem pendentes.
