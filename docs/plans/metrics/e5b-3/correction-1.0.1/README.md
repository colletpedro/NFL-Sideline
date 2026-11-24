# E5b-3 — candidata corrigida 1.0.1

Corrige os dois problemas do HEAD 767cf7f1d15f26022a7c4a982545a6c24c125134,
sem incorporar a branch documental do orquestrador. Ainda candidata ao aceite.
Base aceita 8176e08668a6db4c837fb4de60f52d9b9011217e; E5b-4 não iniciado.

## Política e antes/depois

Acumulada e histórica classificam **todos** os eventos do calendário completo do
time/temporada/fase: alvo excluído por ID; fora comprovado por limite inferior
aceito; FINAL encerrado antes do corte elegível; resto incerto. Incerto/completude
não provada mantém UNKNOWN. Jogo elegível sem PBP continua esperado. Semana aberta
continua aberta; fechamento semanal é obrigatório nas duas janelas semanais.
Reagendamento posterior não desloca a revisão PIT; reconstruction continua nominal.
Detalhes e lacunas estão no [contrato](../CONTRACT.md).

| Contraprova | 1.0.0 | 1.0.1 |
|---|---|---|
| Alvo excluído W1→W4, três jogos anteriores idênticos | expectedGames 3→null, PERIOD_NOT_CLOSED W4 | 3→3, fonte2/3, agregados iguais |
| Recentes [1] vs [1,2], EPA1/2 dos dois lados | comparação aceita | MISMATCH_REQUESTED_PERIOD |
| Observação W1 vs W3, EPA1/2 vs -1/3 | comparação aceita | MISMATCH_REQUESTED_PERIOD, valores conservados |

[evidência anterior](counterexamples-before.json) foi gerada no HEAD exato, antes
até do primeiro commit documental da correção, usando o reproduce.py da revisão.
[resultado corrigido](counterexamples-after.json) e [script atual](reproduce.py)
permitem repetir as três contraprovas sem banco/rede. [Três falhas antigas](three-regressions-old.txt)
executam as regressões novas contra os fontes extraídos do HEAD revisado; apenas
removeu-se o import do helper novo inexistente para coletar esses três testes.

Comparação usa requestedPeriod normalizado, com semana/intervalo solicitados ou
recorte de eventos por corte. Conserva season/phase/origin/mode/corte e todos os
checks anteriores. Times, eventos e actualWeeks diferentes não mudam o pedido.
Offsets equivalentes são compatíveis; byes e fontes ausentes não alteram assinatura.

## Versões e identidades

Algoritmo metrics-temporal-1.0.1; resultado **metrics-temporal-result-v2** pela
estrutura nova requestedPeriod/outsideCutoffGameIds/lower bound. Não há promessa
de leitura por consumidores v1. Entrada v2 opcionalmente representa limite inferior
documentado de início efetivo; v1 continua aceito com seus campos/kinds originais.
Kickoff previsto não vira limite inferior. Prova de não início em/depois do corte
normalmente é posterior e não demonstra conhecimento PIT; defaults ficam UNKNOWN.
Nenhum ID/contrato/adapter/writer/schema E5b-1/2 foi alterado. Policy de confiança
permanece condicional, sem autenticação externa.

[Exemplos corrigidos](examples) conservam pedidos/estatísticas dos três exemplos
históricos. result_id muda porque versões e projeção dos blocos mudaram; audit_id
inclui esse resultado e muda também. O [gate atual](verification.json) registra
IDs/hashes antigos e novos por exemplo. Mudar semana do alvo modifica o calendário
usado e seu inventário auditável, portanto pode modificar result_id/audit_id mesmo
preservando exatamente denominador/agregados. Revisões futuras **rejeitadas**
conservam result_id e modificam audit_id, como testado. Os exemplos e verification
1.0.0 originais são conferidos byte a byte contra o HEAD revisado pelo gate atual.

A materialização antiga da regressão E5a exclusive_cut_boundary perdia a informação
OFFICIAL_END e mantinha apenas um upper bound. Agora esse pacote é UNKNOWN quando
bound=corte; não há alteração no ledger/testes congelados E5a. Proposta mínima para
representar exatidão futura está documentada, não implementada silenciosamente.

## Reprodução e gates

Da raiz da worktree, com runtime ETL instalado, sem .env:

```bash
export PYTHONPATH=etl-pipeline/src
export PYTHONDONTWRITEBYTECODE=1
python -B docs/plans/metrics/e5b-3/correction-1.0.1/reproduce.py --output /tmp/e5b3-corrected-new.json
python -B docs/plans/metrics/e5b-3/verify.py --output /tmp/e5b3-gate-new.json
```

O verificador executa suíte ETL offline; 26 exemplos/23 testes E5a; 12 hashes
congelados; seis arquivos E5b-1 byte a byte; E5b-2 dry-run sem archive/banco;
CLI temporal com três exemplos corrigidos e marcadores byte a byte; contraprovas;
integridade dos registros históricos; caminhos protegidos; git diff --check.
Os testes extras cobrem semanas futuras, calendário completo/incompleto, prova
de futuro/incerteza, PBP ausente, reagendamento, histórico, corte exato/fracionário,
PIT/reconstruction, incompatibilidade/equivalência de períodos e IDs distintos.

Limites: dados/provas sintéticos sob confiança declarada; nenhuma autenticação
histórica ou validação PostgreSQL/Java/frontend. Não se leu .env, fez aquisição,
chamada externa, modelo, push/deploy/merge ou alteração de contratos aprovados.

## Resultado da validação

Gate atual: **350 testes ETL offline**, incluindo 151 casos temporais (58 novos
casos parametrizados/propriedades desta correção); **26 exemplos e 23 testes E5a**;
**12 hashes congelados**; seis arquivos CLI E5b-1 byte a byte; E5b-2 dry-run com
DB=false/archive inexistente; três exemplos CLI corrigidos e marcadores idênticos;
três contraprovas corrigidas; sete arquivos de evidência histórica intactos;
`git diff --check` passou. Nenhum skip/falha no gate final.

verification.json identifica o commit de código testado e os hashes dos
arquivos Python do núcleo/testes. O commit seguinte somente registra documentação,
verificador e artefatos; os fontes do algoritmo/testes continuam esses bytes.
A worktree alvo ficou limpa no fechamento, na mesma branch; commits anteriores
foram preservados. Artefatos de teste com v2/futuro passam pela CLI em tmp_path e
são descartados pelo teste; exemplos fixos corrigidos estão versionados em examples/.
