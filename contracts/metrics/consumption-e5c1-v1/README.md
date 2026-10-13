# E5c-1 — consumo de observações e política de evidências v1

**Candidata ao aceite do orquestrador.** Base exata
`fed166d1682a818b0cca8dd11325ff23ea672c07`, branch
`codex/metrics-consumption-e5c1`, worktree inicial limpa. O checkout original
continua na branch E5b-6; seus 36 arquivos históricos não rastreados foram
inventariados e preservados. Nenhuma conexão ou publicação foi feita.

Este pacote fecha formato, operações e exemplos. Não disponibiliza uma nova
projeção: observações reais ainda precisam ser transportadas pelo futuro consumidor
com a validação integral da cadeia aceita. Schema ou exemplos aprovados não
substituem essa validação. Elegibilidade dos dados é necessária, mas não comprova
validade de tese editorial. Não há score agregado de garantias.

- [Contrato e identidades](CONTRACT.md), [schema fechado](observation.schema.json).
- [Garantias independentes](GUARANTEES.md).
- [Matriz por operação e métrica](OPERATIONS.md).
- [Proveniência prospectiva, somente desenho](PROVENANCE.md).
- [Exemplos e propriedades](EXAMPLES.md), [vetores determinísticos](examples.json).
- [Relações, decisões e etapas seguintes](DECISIONS.md).
- [Verificação e preservação](VERIFICATION.md).

Reprodução na raiz, com Python e `jsonschema` **já existentes**, sem instalação:

```bash
python3 -B contracts/metrics/consumption-e5c1-v1/verify.py
python3 -B -m unittest discover -s contracts/metrics/consumption-e5c1-v1 -p 'test_*.py'
git diff --check fed166d1682a818b0cca8dd11325ff23ea672c07
```

O verificador só lê fixtures/catalogue/schema/Git locais. Não agrega PBP, escolhe
revisões, projeta resultado real, consulta banco ou executa o algoritmo temporal.
As expectativas operacionais são tabelas de aceite com testemunhas explícitas.
Não são uma API de consumo. Não executar gates históricos cuja base documental
é outra como se fossem checks deste pacote; preservação byte a byte os cobre.
