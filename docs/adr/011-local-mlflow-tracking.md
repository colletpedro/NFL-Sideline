# ADR-011: MLflow local como índice dos experimentos de ML

Status: aceito (24/11/2026, pelo dono do projeto; proposto em 23/11/2026). Implementado no branch
`codex/mlflow-tracking-v1`. Plano: [docs/plans/mlflow-tracking-v1](../plans/mlflow-tracking-v1/PLAN.md).

## Contexto

Os experimentos do laboratório de ML (passes interceptáveis v1, calibração temporal v2 e interceptações esperadas
v1) rodam em scripts Python locais, gravam saídas em stores fora do Git e garantem proveniência com hashes
SHA-256, freezes anteriores ao teste e reprodução offline byte a byte. Comparar execuções exige abrir JSON/CSV à
mão, e métricas exibidas no laboratório local foram copiadas para o código da interface. Um desenho com servidor
hospedado foi descartado pelo dono do projeto por custo recorrente e exposição de credenciais.

## Decisão

- Adotar MLflow (versão fixa, venv próprio) somente como ferramenta local de desenvolvimento, com backend SQLite e
  artefatos em `editorial/local-artifacts/mlflow/`, fora do Git e acessível só em `127.0.0.1`.
- Alimentar o MLflow por um importador que só lê os stores científicos; o código congelado dos experimentos não é
  instrumentado nem alterado.
- Os arquivos e hashes dos stores continuam a fonte de verdade; o MLflow é índice de consulta e comparação.
- Registrar os modelos em uso pelo laboratório como pyfunc definido em código, com o JSON congelado como
  artefato e sem pickle, rotulados pelo alias `champion`.
- Ligar o laboratório à execução de origem por um arquivo de proveniência versionado, indexado pelo SHA-256 do
  modelo; o snapshot público e os pacotes do laboratório não mudam de formato.

## Consequências

- Production continua estática; nenhum segredo novo; nenhum serviço pago.
- Comparações e a tabela de seleção passam a sair de script, sem cópia manual de números.
- O banco do MLflow não é reprodutível pelo Git; reprodução continua sendo a offline existente seguida da
  reimportação.
- Upgrades do MLflow exigem trocar o lock e reimportar.
