# Revisão E5b-4 — 11/10/2026

**Decisão: aceite completo pendente de correção do contrato temporal.**
Candidata `f2d946593d1e6b2ed32ad1aa331c630f271c44db`, base
`8f583c4ec9ed83f86c2229b0f1656d32403bcc31`. Não incorporada à integração.
Código e commits da candidata foram preservados; esta revisão contém somente
documentação/evidência na branch `codex/metrics-review-e5b4`.

## Verificação reproduzida

O orquestrador executou o gate offline próprio E5b-4: **410 testes ETL**, checks
E5a (26 exemplos/23 testes/12 hashes), CLI E5b-1 byte a byte, dry-run E5b-2 sem
banco/archive e regressões/contraprovas temporais 1.0.1. Escopos aceitos e evidência
histórica permaneceram intactos. Reproduzido Java 21 `mvn -o clean verify`:
**154 testes, zero falhas/erros/skips**, BUILD SUCCESS. Worktree candidata sem
alterações rastreadas após a revisão. [Resultados](verification.json).

A contraprova offline criou archive/artefatos sintéticos novos, confrontou as
relações e recalculou o artefato pelo caminho aceito antes de chegar à validação
temporal. Confirma um calculation_id original de lote com quatro associações e
dois jogos observados, synthetic-1 e synthetic-6, sendo um COMPLETE vazio.
O validador aceito rejeita as projeções por IDENTITY_CONFLICT.

A revisão leu o bloqueio, contrato, materialização, extração read-only e leitor
Java, além das definições de identidade E5b-1/2/3. Não repetiu a prova PostgreSQL:
o bloqueio já é reproduzível offline e precisa ser corrigido antes da prova geral.
As evidências de PostgreSQL e encerramento são as da candidata, não uma nova
execução independente do orquestrador. Não se iniciou banco nesta revisão.

## Causa confirmada

E5b-1 calcula calculation_id sobre o lote completo. E5b-2 mantém esse ID e
associa todas as coberturas via metric_calculation_coverage. No entanto, o final
de temporal_metrics/validation.py compara todo candidato temporal sob
calculation_id, removendo somente revision_id. Como game, coverage_revision_id
e statistics mudam por jogo, um lote válido é classificado como conflito.

O problema está na representação/validação E5b-3, não na validade do lote SQL.
Preservar os contratos e recusar saída inválida foi a decisão correta da candidata.
O caminho com apenas uma cobertura observada por cálculo não comprova o fluxo
geral de lotes e não encerra esta entrega.

## Correção mínima a especificar

Definir separadamente as quatro dimensões:

1. **Lote/calculation_id:** identidade original e propriedades realmente globais,
   conferidas contra o manifesto completo pelo adapter/writer/materializador.
2. **Cobertura/coverage_revision_id:** jogo, fontes e conteúdo estatístico
   congelados; não se torna um alias de calculation_id.
3. **Associação (calculation_id, coverage_revision_id):** projeção daquele jogo
   naquele lote, com referências e invariantes documentadas.
4. **Revisão temporal/revision_id:** documentos/qualificações usados para avaliar
   a associação. Separar campos persistidos de envelopes auxiliares; uma prova
   posterior não reescreve a cobertura original nem substitui automaticamente PIT.

Não basta remover o check calculation_id ou trocar a chave pelo par mantendo
indiscriminadamente todos os envelopes como conteúdo imutável. É necessário
definir quais campos podem variar legitimamente entre revisões temporais e
quais divergências representam corrupção. Preservar validação de lote pelo
materializador, invariantes por cobertura e conflitos de revision_id.

Não dividir lotes, escolher somente um jogo, gerar calculation_id por jogo,
alterar writer/schema ou recalcular IDs antigos para contornar a lacuna.

## Critérios para destravar

Adicionar regressões positivas/negativas com:

- um lote com pelo menos dois jogos observados e um sem PBP;
- COMPLETE vazio junto de conteúdo observado, sem grupos fabricados para ausência;
- cálculos legítimos diferentes compartilhando uma cobertura, incluindo a
  mudança de declaração de modelo já demonstrada na E5b-2;
- revisões temporais da mesma associação com documentos distintos, preservando
  as regras de conhecimento no corte;
- mesmo ID com conteúdo estatístico/fontes/jogo incompatíveis: rejeição;
- duplicatas idênticas, ordem permutada e alternativas de revisão: sem duplicar
  amostra ou escolher duas coberturas do mesmo jogo no mesmo agregado.

Versionar a correção temporal, declarar compatibilidade de input/result e
preservar exemplos 1.0.1 como história. O Java atual aceita especificamente o
algoritmo 1.0.1; qualquer nova versão precisa de suporte deliberado e testes,
sem liberar indiscriminadamente algoritmos desconhecidos.

Após revisar o contrato, revalidar o materializador e repetir o fluxo real:
adapter → writer/archive → extração → materialização de lote com várias coberturas
→ seleção temporal → leitor Java. Conferir IDs, somas, denominadores, modos,
read-only e imutabilidade SQL/archive. As recusas atuais por ContractGap ficam
como evidência histórica; o teste do lote válido deve então exigir sucesso.

## Escopo e continuação

Próxima ação é uma correção coordenada das identidades E5b-3 e adaptação/teste
E5b-4, com commits e versões separados, baseada na candidata existente.
Não iniciar E5b-5 nem integrar ao produto antes do novo aceite.

PIT sem provas históricas continua UNKNOWN. O contrato não deve ser relaxado
para obter métricas certificadas. Supabase completo/advisors, E4 humano,
BASIC/FULL e defeitos legados permanecem pendências independentes.

Nesta revisão não houve alteração da implementação, banco, Docker, .env,
aquisição, chamadas externas, frontend, snapshot, aprovação, merge em main,
push ou deploy.
