# Hardening remoto do Supabase

## Objetivo

Aplicar, sob autorização explícita, a baseline já existente e a migration `20260908224641_harden_data_api_access.sql` sem alterar o contrato relacional. O resultado esperado é: RLS sem policies nas seis tabelas da aplicação, ausência de grants para `anon`, `authenticated` e `PUBLIC`, grants explícitos apenas para `service_role` nos objetos atuais, nenhum grant automático para objetos futuros e Data API desativada no Dashboard.

Este é um procedimento reutilizável. Use exclusivamente a CLI `supabase@2.117.0`. Não use `supabase link`; passe uma URL de banco percent-encoded em `REMOTE_DB_URL`, fornecida apenas no shell seguro da pessoa autorizada. Nunca registre URL, senha, token, project ref ou conteúdo de `.env` nas evidências.

## Pré-condições

- Aprovação explícita para cada etapa mutável e janela de manutenção definida.
- Backup/restore point confirmado pelo responsável pelo projeto.
- A aplicação confirmada sem consumidores de REST, GraphQL ou clientes Supabase.
- Backend e ETL identificados como conexões PostgreSQL diretas e com credenciais válidas.
- Checkout revisado, com estas duas migrations e sem modificações não aprovadas nelas.
- `REMOTE_DB_URL` disponível somente no ambiente seguro de execução e já percent-encoded.

Abortar antes de qualquer escrita se a aplicação tiver consumidor da Data API, se não houver backup, se a fingerprint não corresponder à baseline ou se o inventário diferir do esperado.

## Inventário read-only

Execute antes de qualquer comando mutável. Registre a saída sanitizada em um ticket restrito:

```sql
select to_regclass('supabase_migrations.schema_migrations') as migration_history;

select version
from supabase_migrations.schema_migrations
order by version;

select c.relname, c.relrowsecurity, c.relforcerowsecurity,
       count(p.policyname) as policies
from pg_class c
left join pg_policies p on p.schemaname = 'public' and p.tablename = c.relname
where c.relnamespace = 'public'::regnamespace
  and c.relname in ('teams', 'games', 'team_week_metrics', 'market_implied', 'analysis_cache', 'ingestion_runs')
group by c.relname, c.relrowsecurity, c.relforcerowsecurity
order by c.relname;

select grantee, table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name in ('teams', 'games', 'team_week_metrics', 'market_implied', 'analysis_cache', 'ingestion_runs')
  and grantee in ('anon', 'authenticated', 'PUBLIC', 'service_role')
order by grantee, table_name, privilege_type;

select pg_get_userbyid(defaclrole) as owner,
       defaclnamespace::regnamespace as schema,
       defaclobjtype, defaclacl
from pg_default_acl
where defaclnamespace = 'public'::regnamespace
order by owner, defaclobjtype;
```

Também registre fingerprint de colunas, PKs, FKs, uniques e defaults das seis tabelas. Compare-o à baseline local aprovada antes de prosseguir. Registre somente a propriedade `rolbypassrls` da role de conexão do backend, nunca seu nome se ele for sensível. A visibilidade da Data API pode não estar disponível por SQL; nesse caso, registre `indisponível por auditoria SQL` e confirme no Dashboard durante a etapa apropriada.

**Gate adicional:** registre o owner de cada entrada de `pg_default_acl`. Esta migration altera somente os defaults do criador `postgres`. Se outra role, inclusive uma role de plataforma, ainda tiver defaults que exponham objetos em `public`, não amplie este pacote nem altere a role sem decisão e autorização separadas; confirme que os objetos da aplicação são criados por `postgres` ou abra um pacote específico para o outro criador.

Se `supabase_migrations.schema_migrations` não existir, apenas registre a ausência nesta fase. Não a crie durante o inventário.

## Reconciliação da baseline

**Ação mutável futura — requer aprovação explícita.** Depois de confirmar que a fingerprint remota é idêntica à baseline, marque somente a baseline como aplicada:

```bash
npx --yes supabase@2.117.0 migration repair \
  --db-url "$REMOTE_DB_URL" \
  --status applied 20260908201813
```

- Efeito esperado: cria/atualiza somente o histórico de migrations para a baseline; não executa o DDL da baseline.
- Prossiga somente se a tabela de histórico estiver ausente ou não contiver essa versão, se o fingerprint tiver correspondido e se o gate de criadores de objetos estiver aprovado.
- Aborte se aparecer qualquer versão inesperada ou se a CLI indicar que também marcaria `20260908224641`.
- Rollback antes do hardening: execute o mesmo comando com `--status reverted 20260908201813`; isto reverte apenas a marca no histórico, não o schema existente.

Nunca marque `20260908224641` como aplicada antes de seu SQL ter executado.

## Dry-run

**Ação de planejamento futura — não altera o banco.**

```bash
npx --yes supabase@2.117.0 db push \
  --db-url "$REMOTE_DB_URL" \
  --skip-vault \
  --dry-run
```

- Efeito esperado: listar exclusivamente `20260908224641_harden_data_api_access.sql` como pendente.
- Prossiga somente se a lista contiver exatamente essa migration.
- Aborte se incluir baseline, seed, roles, Vault ou qualquer migration adicional.
- Rollback: não aplicável; corrija a reconciliação ou interrompa a mudança.

## Aplicação da migration

**Ação mutável futura — requer aprovação explícita após dry-run aprovado.**

```bash
npx --yes supabase@2.117.0 db push \
  --db-url "$REMOTE_DB_URL" \
  --skip-vault
```

- Efeito esperado: executar somente o hardening, registrar sua versão no histórico, habilitar RLS sem policies, ajustar ACLs dos objetos atuais e alterar default privileges de `postgres` para objetos futuros.
- Prossiga somente se o dry-run anterior estiver anexado à mudança e houver backup confirmado.
- Aborte em qualquer erro de migration, timeout, lock inesperado ou divergência de migrations.
- Rollback: restaure o backup se a migração falhar parcialmente. Após uma aplicação bem-sucedida, um rollback de acesso deve ser um SQL revisado contra o inventário prévio: restaure apenas os grants que existiam antes, restaure os default privileges necessários e desabilite RLS somente se essa for uma decisão de segurança aprovada. Não use grants em massa sem comparar a evidência prévia.

## Desativação da Data API no Dashboard

**Ação mutável futura — configuração do projeto, não efeito de `db push`.**

1. Abra o projeto correto no Dashboard.
2. Abra a integração **Data API**.
3. Desative **Enable Data API**.
4. Registre captura sanitizada, data, hora e operador.

- Efeito esperado: REST e GraphQL auto-gerados deixam de responder, independentemente de grants e RLS.
- Prossiga somente após confirmar novamente que não há consumidores.
- Aborte se a tela indicar dependência, integração ou consumidor não avaliado.
- Rollback: reative **Enable Data API** no Dashboard somente com aprovação; antes, revalide RLS, grants, policies e consumidores.

## Verificações pós-aplicação

1. Reexecute integralmente o inventário read-only e compare-o com a evidência prévia.
2. Confirme RLS habilitado, `relforcerowsecurity = false` e zero policies nas seis tabelas.
3. Confirme ausência de privilégios atuais para `anon`, `authenticated` e `PUBLIC`; confirme os grants explícitos de `service_role` somente nos objetos atuais.
4. Confirme em `pg_default_acl` que tabelas e sequences futuras em `public` não concedem grants automáticos às três roles, e que funções futuras criadas por `postgres` não concedem `EXECUTE` automático às três roles ou a `PUBLIC`. A revogação de funções é global ao criador para substituir o `EXECUTE` implícito de `PUBLIC`.
5. Execute uma transação PostgreSQL direta do backend/ETL: insert, select e update de registro temporário, seguido de rollback. Confirme ausência de resíduo.
6. Inicie o backend contra o banco remoto e confirme Hikari, validação JPA, health endpoint e ausência de erro de permissão. Execute uma carga ETL controlada somente se houver aprovação separada para dados.
7. Sem usar chaves no relatório, confirme que os endpoints REST e GraphQL da Data API não respondem como serviços funcionais.
8. Registre `supabase migration list --db-url "$REMOTE_DB_URL"` e confirme que as duas versões aparecem aplicadas.

## Evidências a registrar

- Aprovação, janela, operador e identificação do backup/restore point.
- Versões de CLI e das duas migrations, com hash dos arquivos revisados.
- Fingerprints pré e pós de colunas, constraints e defaults.
- Saídas sanitizadas de RLS, policies, ACLs atuais e `pg_default_acl`.
- Dry-run mostrando exclusivamente a migration de hardening.
- Saída sanitizada do histórico após a aplicação.
- Evidência da configuração **Enable Data API** desativada no Dashboard.
- Resultados do teste PostgreSQL direto, backend e, quando autorizado, ETL.
- Decisão explícita caso qualquer rollback seja necessário.

## Registro de execução — 2026-09-08

- A baseline `20260908201813` foi reconciliada somente no histórico do schema remoto; seu DDL não foi executado novamente.
- A migration `20260908224641_harden_data_api_access.sql` foi aplicada pelo fluxo versionado, sem alteração do contrato relacional ou de dados de negócio.
- O histórico remoto passou a conter exclusivamente a baseline e o hardening. As seis tabelas permaneceram íntegras, com RLS habilitado, `FORCE ROW LEVEL SECURITY` desabilitado e zero policies.
- `anon`, `authenticated` e `PUBLIC` não mantêm privilégios nas tabelas e sequences da aplicação. `service_role` mantém somente os grants explícitos concedidos aos objetos atuais.
- Os default privileges de `postgres` não concedem acesso automático futuro às roles da Data API nem `EXECUTE` a `PUBLIC`. Defaults residuais de `supabase_admin` permanecem gerenciados pela plataforma e não foram alterados.
- O proprietário confirmou no Dashboard, em 2026-09-08, que **Enable Data API** estava desativado e que não havia schemas consultáveis. REST e GraphQL não expõem a aplicação; JDBC e psycopg2 continuam como os únicos caminhos de acesso.
- Qualquer reativação da Data API exige uma nova revisão de grants, default ACLs, funções, policies e consumidores. Migrations futuras devem usar exclusivamente o fluxo versionado; não execute novamente a baseline histórica.
