# Aceite E5b-3/4 — identidades e ponte isolada, 12/10/2026

**Aceita e incorporada localmente.** Candidata
`60948abab73d575dce630cb66f9908125f2039c6`, base
`f2d946593d1e6b2ed32ad1aa331c630f271c44db`, commits `401b7d5`, `1282fd4`,
`f208739` e `60948ab`. Branch de integração `codex/metrics-integration-e5b4`.
As revisões anteriores permanecem históricas; o bloqueio da
[E5b-4 inicial](../e5b-4-review/REVIEW.md) foi resolvido nesta versão.
Main permanece em `5096a585f0cc5455160ff9c2ee64555cfcb59fc0`.

## Identidades e versões

A validação distingue manifesto global do lote, cobertura original, associação
por jogo e revisão temporal. O mesmo calculation_id pode projetar vários jogos;
calculation/coverage/source/artifact/receipt IDs persistidos não foram substituídos.
Os objetos `original.manifest` e `original.coverage` conservam tipos e ordem dos
arrays originais, sem a normalização de conjuntos temporais. Qualificações não
reescrevem o conteúdo persistido. Conflitos continuam rejeitados.

Novo caminho: **input-v3 → algoritmo 1.1.0 → result-v3**, materialization-v2.
Input-v1/v2 mantém algoritmo 1.0.1/result-v2 e seus checks anteriores. Java aceita
explicitamente esses dois pares de resultado/algoritmo e recusa pares cruzados
ou desconhecidos. Materializações v1 não são promovidas silenciosamente.

A identidade completa do cálculo continua conferida pelo adapter/prepare/writer
e materializador sobre o lote integral. O núcleo temporal e o Java validam suas
projeções, vínculos e invariantes; não recalculam PBP nem autenticam terceiros.

## Verificação independente do orquestrador

- Gate offline do candidato: **434 testes ETL**, sem falhas/skips; 26 exemplos,
  23 testes E5a, 12 hashes, CLI E5b-1 byte a byte, dry-run E5b-2 sem banco/archive,
  evidências históricas, regressões temporais e contraprovas preservadas.
- Java 21 `mvn -f core-api/pom.xml -o clean verify`: **170 testes**, zero
  falhas/erros/skips, BUILD SUCCESS.
- Prova PostgreSQL **real própria**, usando runtime 17.6 existente, novo cluster
  e porta 55486: adapter/writer/archive → extração → materialização integral →
  seleção temporal → seis leituras Java.
- Três cenários reais passaram: lote antes bloqueado, dois cálculos com cobertura
  compartilhada após mudança de declaração de modelo e dois jogos não vazios
  junto de COMPLETE vazio e jogo sem PBP.
- CLI real repetiu a seleção explícita com outros cálculos presentes, produziu
  arquivos byte a byte iguais ao fluxo direto e passou no leitor Java.
- As onze relações, persisted_at, blobs, receipts e marcador do archive permaneceram
  idênticos antes/depois das leituras; INSERT foi recusado em transação read-only.

O lote antes bloqueado mantém
`sha256:9344d1b8902207a39b5321f939da1bae8aaddbb848b33b1155152ac1a38eeca7`,
quatro associações e dois candidatos observados, incluindo COMPLETE vazio.
Na reconstrução: denominador 3, sourceRatio 1/3, volume observado 3 e EPA -1/3;
synthetic-5 permanece esperado sem fonte. Cobertura compartilhada não duplicou
amostra. Os casos PIT sem prova histórica permaneceram UNKNOWN/sem agregados.

[Gate offline](offline-verification.json), [prova real](database-proof.json),
[paridade CLI](cli-proof.json), [reconciliação da integração](integration-verification.json).
Após incorporar, 17 hashes Python de fontes/testes conferiram e runtime/testes/
fixtures Python/Java são idênticos ao candidato testado. Não se repetiram esses
gates sem alterações de implementação; a integração mudou somente a documentação
de estado/aceite. `git diff --check` passou.

Os gates dos pacotes candidatos também congelam docs/current-state.md contra
suas bases. A execução integral acima foi no checkout exato candidato; não se
afirma que esse mesmo guard documental passa em qualquer branch de integração
posterior. Os verificadores e relatórios históricos não foram adulterados.

## Instância própria e preservação

Instância da revisão: UUID `75e2c1d1-48e5-4b0e-8a2f-d80122e5a093`, banco
`nfl_e5b2_75e2c1d148e5`, root
`/private/tmp/nfl-e5b4-instance-orchestrator-identities-20261012`, porta 55486.
Somente essa instância foi iniciada/encerrada. pg_ctl status retornou 3,
postmaster.pid ausente e probe de bind na porta aprovado. [Encerramento](shutdown.json).
Dados e evidências locais foram preservados; não são dependências dos testes
offline versionados. Nenhum cluster histórico ou serviço global foi alterado.

## Limites e próximo passo

O aceite encerra a **ponte isolada E5b-4**, não integração ao produto, publicação
ou certificação de dados reais. A prova real usa fixtures sintéticas e comprova
o transporte/persistência/materialização/leitura. Receipts atuais, persisted_at,
derivedAt e hashes não certificam conhecimento histórico. Supabase completo/
advisors permanece pendente antes de aplicar migration fora do ambiente descartável.
A consulta à [documentação PostgreSQL 17](https://www.postgresql.org/docs/17/transaction-iso.html)
apoia a escolha de snapshot estável para extração; a prova local verificou o
comportamento read-only, sem mudanças no schema.

Próxima entrega: **E5b-5, integração controlada ao ETL**, com modo explícito,
planejamento/validação local e política de falha/recuperação. Deve preservar o
fluxo legado e distinguir dados coletados de provas de completude/encerramento/
disponibilidade. Não aplicar migration remota ou iniciar carga/backfill/publicação
como consequência automática deste aceite. Planejar separadamente o consumo
editorial/visual das métricas; Java oferece leitor offline, não consultas JPA.

E4 humano, BASIC/FULL, cinco falhas legadas, EVENT_END_EXACT, avaliação com dados
reais e rollout público continuam pendentes. Não houve .env, banco remoto,
aquisição/backfill, modelos, frontend/snapshots/aprovações, ETL semanal, merge em
main, push ou deploy.
