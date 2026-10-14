# Aceite do orquestrador — E5c-1, 13/10/2026

Contrato aceito no escopo de desenho, schema e exemplos, após três correções
locais. Candidata original: `4c3ea453312e8696a38cc2fd0206d7e0a8edb350`,
base `fed166d1682a818b0cca8dd11325ff23ea672c07`. Branch de integração:
`codex/metrics-integration-e5c1`; a candidata e sua worktree foram preservadas.

## Revisão e correções

Os checks originais passaram: 34 observações, 17 cenários, 476 decisões,
12 casos inválidos e 12 testes. A revisão independente encontrou divergências
entre a matriz publicada e suas testemunhas finitas:

| Contraprova | Candidata | Corrigido |
|---|---|---|
| Conflito básico de compatibilidade, strings ainda iguais | EPA alinhável | Comparação recusada; valores individuais preservados |
| Cortes diferentes com semanas iguais | EPA alinhável e dados pregame permitidos | Comparação e dados pregame recusados |
| Mesmo alvo entre os membros de um lado | Dados pregame permitidos | Pregame recusado; descrição preservada |

O estado básico KNOWN agora é necessário para B; EPA/modelo permanece separado
para não bloquear volume por modelo UNKNOWN. Um corte declarado precisa
coincidir. PREGAME_CUTOFF exige corte/alvo/kickoff presentes, alvo/kickoff comuns
e alvo ausente de todos os membros. Isso não implementa PIT_CHAIN nem verifica
provas reais de disponibilidade, ingestão ou FINAL.

[Antes/depois](review-counterexamples.json) foi executado sobre o verificador
obtido do commit candidato e sobre a correção. [Testes de revisão](test_review.py)
exigem recusa das permissões antigas, permitem as decisões corrigidas e conferem
a preservação dos números/linhagem. Cobrem também UNKNOWN básico, alvos ausentes
ou distintos e corte ausente sem TypeError. São testes finitos sobre premissas
sintéticas, sem seleção temporal ou construção de observações reais.

## Verificação e reprodução

O gate estrutural da candidata e do pacote corrigido passou antes da atualização
de docs/current-state.md. Os 17 testes passaram no pacote corrigido. Schema,
34 observações, 17 cenários/476 decisões originais, 12 inválidos e testes originais
conservam seus bytes. [Verificação e hashes](review-verification.json) registra
o estado antes do registro de aceite; `verification.json` continua sendo a
evidência histórica da autora, com 12 testes, sem reescrita.

Na raiz, a suíte do contrato corrigido é reproduzível sem banco/rede:

```bash
python3 -B -m unittest discover -s contracts/metrics/consumption-e5c1-v1 -p 'test_*.py'
git diff --check
```

O main de verify.py também impõe que todo caminho fora deste pacote permaneça
idêntico à base E5b-6. Essa verificação foi mantida: após o registro do aceite em
docs/current-state.md, ela intencionalmente recusa essa mudança documental.
Para reproduzir o gate histórico completo, use o checkout candidato original;
para o pacote corrigido, use o commit de correção anterior ao registro de estado.
O commit correspondente aparece no histórico desta branch. Não se ampliou a
allowlist para fazer uma alteração posterior passar como preservação original.

Não foram repetidas suítes ETL/Java/PostgreSQL/frontend: seus componentes não
mudaram. Permanecem 36 arquivos históricos não rastreados, sem inclusão nos
commits; não houve leitura de .env, banco, aquisição ou modelos.

## Decisões e continuação

Observações reconciliadas com UNKNOWN são exibíveis como conteúdo arquivado,
com período, denominadores e limitações próximos dos dados. Volume/frequência
admitem comparação amostral explícita. EPA/SR comparáveis exigem os requisitos
de período, completude, cobertura e modelo da política. Conhecimento temporal
não demonstrado recusa pregame. Nenhuma dessas permissões valida uma tese.

Próxima entrega recomendada: projeção offline das escolhas nominais aceitas,
bundle auditável e documentos deste contrato. Depois, adaptador e apresentação
no laboratório local, com verificações de compreensão e de UNKNOWN. Coleta
prospectiva tem frente própria; dados pregame não são liberados por esta entrega.

Não há integração com API/editorial/frontend, alteração de schema SQL/snapshots,
acesso remoto, publicação, merge em main, push ou deploy. O aceite deste contrato
não encerra E4 humano, BASIC/FULL, falhas legadas ou Supabase completo/advisors.
