# E5a — contrato de métricas e recortes 1.0.0

**Candidato à revisão do orquestrador — 08/10/2026.** Base exata: `6d99e66ccbe62861a7658dda67be51cf5773ff24`, de `codex/visual-integration-e4`; branch desta entrega: `codex/metrics-contract-e5a`. Não é implementação nem substituição da Spec, claims v5, contexto v3, E1 ou snapshot v1.

O núcleo recomendado conserva **passe/corrida classificados pela fonte**, com sacks no passe e scrambles na corrida. Eficiência usa EPA finito; volume e frequência usam jogadas elegíveis independentemente da presença de EPA. Cada família tem contagens próprias. Conversões de dois pontos são explicitamente excluídas pela nova população; o legado permanece intacto. Recortes derivam de estatísticas por jogo e revisão de fonte, nunca de taxas arredondadas.

| Arquivo | Conteúdo |
| --- | --- |
| [INVENTORY.md](INVENTORY.md) | Comportamento vigente comprovado e divergências |
| [CONTRACT.md](CONTRACT.md) | Decisões normativas **propostas**, fórmulas, filtros, janelas, temporalidade |
| [contract.json](contract.json) | Representação estruturada das mesmas decisões e 22 métricas |
| [EXAMPLES.md](EXAMPLES.md) | Ledger manual e resultados esperados independentes |
| [fixtures/cases.json](fixtures/cases.json) | Casos sintéticos explícitos; não são dados NFL reais |
| [verify.py](verify.py), [test_verify.py](test_verify.py) | Modelo mecânico offline e propriedades; isolados da produção |
| [PROVENANCE.md](PROVENANCE.md), [local-audit.json](local-audit.json) | Fontes, versões, hashes, leitura de dados locais e limites |
| [probe_local.py](probe_local.py) | Reproduz auditoria local opcional, somente leitura de Parquet |
| [E5B.md](E5B.md) | Persistência aditiva por jogo/revisão e entregas executáveis |
| [REPORT.md](REPORT.md), [verification.json](verification.json) | Aceite mecânico, questões críticas e limites |

Da raiz da worktree, sem dependências extras, rede, .env ou banco:

```bash
python3 contracts/metrics/e5a-v1/verify.py
python3 -m unittest discover -s contracts/metrics/e5a-v1 -p 'test_*.py' -v
git diff --check
```

Os exemplos fixam somas/contagens e razões exatas; decimais publicados nos exemplos usam strings. O verificador não importa o ETL, Java ou modelo. `probe_local.py` exige o Polars já instalado e arquivos locais indicados explicitamente; não é pré-requisito dos exemplos.

A revisão deve decidir a adoção desta versão, especialmente a exclusão de conversões e a distinção entre reconstrução por evento e conhecimento histórico comprovado. Não existe aprovação de publicação implícita. Compreensão humana E4, amostra independente, BASIC/FULL, explosividade, ajustes por adversário, shrinkage, percentis e confiança estatística continuam fora desta entrega.
