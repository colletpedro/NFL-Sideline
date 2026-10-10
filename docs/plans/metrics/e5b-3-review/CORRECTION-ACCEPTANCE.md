# Aceite da correção E5b-3 — 09/10/2026

**Aceita para integração local e preparação da E5b-4.** Candidato
`25ba895bd611811f0d6291c374827d2d76ed6be9`, incluindo commits de correção
`e9db0ba`, `a42c0ca` e `25ba895`. Incorporado à branch
`codex/metrics-integration-e5b3`, preservando a revisão anterior e o histórico
da candidata. Main continua em `5096a585f0cc5455160ff9c2ee64555cfcb59fc0`.
Não há aceite de publicação, dados reais ou integração com consumidores.

## Critérios atendidos

As três contraprovas da [revisão anterior](REVIEW.md) foram reproduzidas com
comportamento corrigido, inclusive depois da integração:

- Mover somente o alvo excluído para a semana aberta mantém expectedGames=3,
  cobertura 2/3 e os agregados anteriores.
- Janelas recentes [1] versus [1, 2] são recusadas por
  MISMATCH_REQUESTED_PERIOD.
- Observações das semanas 1 versus 3 são recusadas, preservando EPA 1/2 e -1/3.

Acumulada/histórica classificam eventos por evidências e não exigem fechamento
de todas as semanas do calendário. Alvo excluído não acrescenta incerteza;
evento elegível sem PBP continua esperado. Janelas semanais continuam exigindo
fechamento do período. Limite superior posterior ao corte não comprova futuro.
A nova prova de limite inferior é distinta de kickoff previsto e tem vínculo,
origem, recebimento e dependências explícitos. Bounds contraditórios são rejeitados.

A assinatura de período solicitado depende da definição da janela, temporada,
fase, origem, modo e corte normalizado. Não depende dos times, jogos observados,
actualWeeks ou da identidade do resultado. Testes cobrem períodos diferentes,
representações equivalentes, byes, fontes ausentes e eventos diferentes.

## Evidência da revisão

Reproduzido o gate completo no checkout exato do candidato:

- 350 testes ETL offline, sem falhas/skips;
- 26 exemplos, 23 testes E5a e 12 hashes congelados;
- seis arquivos da CLI E5b-1 byte a byte;
- dry-run E5b-2 sem banco nem criação de archive;
- três exemplos temporais corrigidos e marcadores byte a byte;
- evidências 1.0.0 preservadas e contraprovas corrigidas;
- caminhos protegidos inalterados e git diff --check aprovado.

[Gate reproduzido](correction-verification.json). Após incorporar, os oito hashes
de fontes/testes conferiram com os bytes testados. Runtime ETL, fixtures e docs do
pacote são idênticos ao candidato; as três contraprovas passaram no checkout de
integração. [Reconciliação da integração](correction-integration-verification.json).
Os 36 arquivos históricos não rastreados foram preservados.

O verificador do pacote também compara docs/current-state.md com a base E5b-2.
Por isso seu gate integral acima foi executado no checkout candidato, antes da
atualização documental do orquestrador. Não anunciar que esse comando passa sem
adaptação em toda branch de integração que já atualizou o estado consolidado.
As fontes/testes não foram modificados pela integração.

## Versões e limites

Algoritmo metrics-temporal-1.0.1, input-v2 com leitura fechada de input-v1 e
result-v2. Resultado v2 não é anunciado como compatível com consumidores v1.
Os documentos atuais e históricos têm identidades distintas e estão separados.

**Limite operacional importante:** a política continua conservadora. Em PIT,
jogos futuros conhecidos apenas pelo calendário/kickoff previsto não recebem
prova de início efetivo. Um calendário completo da temporada com esses eventos
pode manter expectedGames UNKNOWN, mesmo havendo agregados anteriores auditáveis.
A prova de não início até o corte normalmente é posterior e serve ao retrospectivo,
sem certificar conhecimento histórico. Este aceite não afirma que a cobertura
acumulada PIT será sempre conhecida ou utilizável em produção.

Disponibilidade, ingestão, encerramento, completude e modelo EPA de fontes reais
continuam dependentes de documentos e premissas de confiança. Fixtures não os
certificam. EVENT_END_EXACT é uma proposta documentada para preservar a distinção
de OFFICIAL_END; não foi implementado nem alterou o contrato E5a congelado.

## Transição para E5b-4

Próxima entrega: materializar explicitamente as relações E5b-2 em input temporal
v2 e definir um contrato Java separado para ler result-v2. Preservar cada identidade,
bytes, conjunto completo de partições, cálculos, somas e receipts; não transformar
persisted_at, calendário mutável ou manifesto declarativo em prova histórica.

Antes de integrar consumidores, documentar como informações UNKNOWN chegarão ao
Java e como recortes/versões serão identificados. Leitura de banco exige modo local
explícito e validação do ambiente; não pode virar acesso remoto implícito. E5b-4
não deve alterar schema/writer ou conectar o ETL semanal, frontend ou snapshots
sem uma entrega própria e contrato revisado.

Pendências independentes: stack Supabase completa/advisors antes de aplicar a
migration fora do PostgreSQL descartável; rodada humana E4; BASIC/FULL; cinco
falhas legadas; avaliação e rollout público. Nenhuma delas é encerrada por este aceite.

Nesta revisão não houve banco, Docker, .env, aquisição, chamadas externas,
Java/frontend, alteração de snapshot/aprovação, merge em main, push ou deploy.
