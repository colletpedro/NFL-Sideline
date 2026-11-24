# Aceite do orquestrador — E5b-2, 09/10/2026

**Aceita para persistência em PostgreSQL local identificado e descartável.** Não foi necessária alteração de runtime na revisão. A validação da stack Supabase completa/advisors permanece pendente antes de aplicar a migration fora do ambiente nativo descartável; o aceite não autoriza aplicação remota, integração semanal ou publicação.

Branch local: `codex/metrics-integration-e5b2`, base `882c9013ec1a1cd08f2d0b7049fb74ff1cdb8491`. Commits recebidos: `95e0686`, `c6865d7` e `401a7ea0413d11e59e94500fc06ddf55111fb22d`. Os relatórios originais e o pacote aceito E5b-1 permaneceram intactos. Evidências posteriores: [integration-verification.json](integration-verification.json) e [integration-database-proof.json](integration-database-proof.json).

## Resultado da revisão

Foram lidos migration, desenho, archive, verificação semântica, configuração local, writer, CLI e suites offline/SQL. Onze tabelas em schema privado preservam bytes/fontes compostas, cálculos, coberturas, somas, arquivos originais e receipts sem confundir seus IDs. Alteração de declaração do modelo EPA pode criar cálculo novo e reutilizar cobertura/somas, conservando ambos os manifestos.

O writer valida marcador/hashes/identidade e recalcula a semântica usando o adapter aceito e os bytes explícitos. A persistência é INSERT com comparação de conteúdo imutável; conflitos não sobrescrevem registros. As validações no writer complementam constraints SQL; RLS/policies não autenticam evidências fornecidas pelo chamador.

Role NOLOGIN/NOBYPASSRLS limitada a SELECT/INSERT nos objetos novos, com policies explícitas e sem privilégios UPDATE/DELETE/TRUNCATE. Schema, domains, tipos compostos e tabelas não concedem acesso às roles públicas. As FKs não dão acesso de leitura/escrita às entidades legadas. RLS habilitada e forçada nas onze tabelas.

Archive e SQL não têm transação distribuída: blobs/receipts podem permanecer sem referência após rollback. A recuperação reutiliza esses arquivos sem deslocar o primeiro receipt. Observação prospectiva e persistência SQL são diferentes de disponibilidade/encerramento declarados; histórico desconhecido não foi certificado.

## Verificação reproduzida

- **199 testes ETL offline**, **51 testes SQL reais**, sem falhas/skips; **26 exemplos, 23 testes E5a e 12 hashes** preservados.
- Uma instância **nova** PostgreSQL 17.6 foi criada pela revisão em `/tmp/nfl-e5b2-orchestrator-instance-20261009`, restrita a `127.0.0.1:55483`. Não foi reutilizado/resetado banco existente. Todas as migrations foram aplicadas no cluster limpo, com roles e fixture próprias do harness.
- Os testes reais usaram login limitado e cobriram idempotência, concorrência, revisão corrigida, evidência/modelo revisados, precisão SQL, constraints/FKs, semântica adversarial, rollback nos três checkpoints, recuperação e acesso público/herdado.
- A prova selecionada foi executada novamente após a suite: primeira carga **102 inserções**, reexecução **0 inserções / 102 reutilizações**. Correção, revisão de modelo, preservação de estatísticas, recuperação/receipts e contagens finais coincidiram com a prova entregue. Instâncias, caminhos e instantes dos receipts são próprios da nova execução.
- Artefatos originais foram recuperados byte a byte do archive; CLI E5b-1 gerou os mesmos seis arquivos congelados, sem conexão ao banco.
- Migration SHA-256: `4634d43181d33d7dbfaa772411fdabd6a2b1a6efa867df215f72edd1bd8945e5`. Nenhuma edição de baseline/hardening/config principal/adapter antigo/pipeline/Java/frontend/snapshots na entrega recebida.
- Instância da revisão encerrada, `pg_ctl status` confirmou ausência de servidor e porta 55483 liberada. Arquivos da instância, archive e runtime permanecem locais em `/tmp`; não são dependência de checkout nem credenciais versionadas.

Comandos de reprodução estão em [README.md](README.md): nesta revisão trocaram-se root/workspace/output por nomes novos e porta por 55483, usando o runtime PostgreSQL já disponível. O Python foi o venv existente na origem, com PYTHONPATH da worktree recebida, `-B`, `PYTHONDONTWRITEBYTECODE=1` e pytest sem cache. Java/frontend não foram reexecutados.

## Limites e próxima entrega

PostgreSQL nativo reproduziu o SQL e as roles relevantes, mas não Auth/PostgREST/Studio, ownership/defaults completos da plataforma ou advisors. Não houve nova tentativa de iniciar/reconfigurar Docker na revisão. O checklist real da stack Supabase isolada permanece aberto e deve preceder aplicação fora deste ambiente descartável. O harness atual usa caminhos `/private/tmp` do macOS; portabilidade para CI Linux não foi validada.

A documentação oficial consultada separa grants de acesso e políticas RLS: [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security). A revisão também consultou o [changelog](https://supabase.com/changelog); não são evidências de que a stack completa foi executada aqui. Não há recomendação de usar o runtime temporário como serviço de produção.

**E5b-3 pode avançar sem banco remoto:** seleção temporal e janelas puras sobre calendário/revisões/evidências congelados, mantendo conexão e dados públicos separados. Precisa qualificar o que cada receipt comprova, preservar precisão dos instantes, exigir prova de encerramento e selecionar tanto PBP quanto calendário/estado conhecidos antes do corte quando o modo for POINT_IN_TIME. Receipts prospectivos não tornam os dados locais históricos elegíveis por retroatividade.

Não implementados ainda: seleção por corte, confirmação independente de encerramento/disponibilidade histórica, leitor Java, ETL semanal, backfill, consumidor visual e publicação. E4 humano, BASIC/FULL e cinco falhas legadas seguem pendentes. Nenhum push, deploy ou merge em main.
