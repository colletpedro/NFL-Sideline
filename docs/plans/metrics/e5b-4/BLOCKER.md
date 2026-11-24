# Bloqueio de contrato para aceite completo E5b-4

**Confirmado; nenhuma alteração silenciosa nos contratos aceitos.**

E5b-1 calcula calculation_id sobre o lote inteiro. E5b-2 preserva esse ID em
metric_calculation e associa todos os jogos por metric_calculation_coverage.
O writer aceita o lote da contraprova e suas estatísticas, inclusive COMPLETE
vazio: synthetic-1 e synthetic-6 têm doze grupos cada, com o mesmo calculation_id.

No final de temporal_metrics/validation.py, a projeção para calculation_id é
`lambda c: c` (removendo apenas revision_id). Logo game, coverage_revision_id e
statistics diferentes no mesmo lote causam IDENTITY_CONFLICT. Não é corrupção
SQL, falha de hash ou falta de evidência temporal. O conflito ocorre na fronteira
entre identidade de lote persistida e projeção temporal por jogo.

[Reprodução offline](reproduce_gap.py) valida relações e recalcula o artefato
aceito antes de chegar ao validador temporal. [Contraprova](contract-gap.json)
registra o ID original, as quatro associações e os dois jogos observados.
[Prova real](database-verification.json) também persiste o lote com writer E5b-2
na instância própria e reproduz o erro sem alterar linhas, timestamps ou archive.
Nenhum pacote final inválido é publicado. Não se escolhe apenas synthetic-1,
nem se substitui calculation_id por coverage_id/hash por jogo.

## Proposta mínima para revisão própria

No contrato/validador E5b-3, distinguir identidade de lote de identidade da
associação por jogo. Comparar a projeção por associação `(calculation_id,
coverage_revision_id)` e conservar a imutabilidade dos campos de lote pertinentes.
A semântica do calculation_id original continua conferida contra o manifesto
completo pelo materializador/E5b-2; nunca é recalculada com outra projeção.
A revisão deve definir também quais documentos auxiliares pertencem à revisão
temporal, e quais campos imutáveis pertencem à cobertura original.

Adicionar regressão com dois jogos observados no mesmo cálculo e com dois
cálculos legítimos compartilhando cobertura. Reexecutar todos os gates temporais,
IDs, comparação, modos, fontes compostas e contraprovas. Documentar/versionar a
correção separadamente antes de liberar o materializador geral.

Essa proposta **não foi aplicada**. Não se implementou EVENT_END_EXACT.
A candidata E5b-4 tem infraestrutura e leitor validados, mas não é entrega
completa para lotes usuais com várias coberturas observadas. O caminho positivo
usa explicitamente dois cálculos de fixtures, cada um com uma cobertura observada;
**não divide nem reconstrói** um lote persistido para contornar o bloqueio.
