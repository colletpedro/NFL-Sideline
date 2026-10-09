# E5b-3 — seleção temporal e agregação offline

Branch `codex/metrics-temporal-e5b3`, base confirmada antes da edição:
`8176e08668a6db4c837fb4de60f52d9b9011217e`. Worktree isolada preservada em
`/Users/pedrocollet/.codex/worktrees/metrics-temporal-e5b3/NFL Sideline`.
O contrato inicial foi commitado antes do código. [Contrato final](CONTRACT.md)
e [matriz de exclusões](REASONS.md) fecham a política e os detalhes implementados.

Implementação: `etl-pipeline/src/nfl_sideline_etl/temporal_metrics/`.
`validation.py` verifica estrutura fechada/bytes/IDs/vínculos/somas;
`times.py` conserva precisão arbitrária e converte Eastern/DST;
`evidence.py` qualifica evidência segundo premissas explícitas e dependências;
`core.py` seleciona revisões, eventos, quatro janelas, cobertura, razões exatas e
comparação descritiva; `__main__.py` publica somente um destino novo offline.
Versões: input/result v1, algoritmo 1.0.0, política materialized-evidence-v1.
População/definição/adapter E5b-1 permanecem intactos, sem fórmulas novas.

## Exemplos completos

| Pedido em 2026-09-28T12:00:00Z | alpha | beta | Conhecimento/cobertura |
|---|---|---|---|
| [POINT_IN_TIME](examples/point-in-time/result.json) | alpha-old: soma1/E2 | beta: soma-0.5/E5 | geral soma0.5/E7 => EPA1/14; fonte2/3, gap permanece esperado |
| [EVENT_RECONSTRUCTION](examples/reconstruction/result.json) | alpha-corrected: soma4/E2 | beta: soma-0.5/E5 | soma3.5/E7 => EPA1/2; bytes/provas posteriores explicitamente listados |
| [POINT_IN_TIME sem prova suficiente](examples/unproven/result.json) | não selecionado | não selecionado | calendário inelegível, expectedGames=null; nenhum conhecimento histórico certificado |

PIT rejeita alpha-corrected por disponibilidade/ingestão e declarações posteriores;
rejeita beta-composed por uma partição tardia. Reconstruction usa mapa nominal,
ainda exige encerramento anterior, e declara knowledgeAtCutoff=NOT_DEMONSTRATED.
Target W1/FINAL com bound anterior continua fora por ID; kickoff aceito sustenta
somente a condição pregame do pedido. Sem kickoff aceito, TIME_UNVERIFIED.

A cobertura2/3 não torna a comparação íntegra: gap não possui fonte, beta tem
EPA missing, comparação de eficiência fica false com razões separadas. Subsets e
modelos diferentes ficam em grupos próprios; incerteza NOT_ESTIMATED.
O [ledger manual](../../../../etl-pipeline/tests/fixtures/temporal_metrics/ledger.json)
é independente do seletor. Fixtures e exemplos são inteiramente versionados.

## Reprodução

Da raiz da **worktree**, com Python3.11+ e dependências de teste do ETL instaladas.
Não carregar .env. Para checkout novo, o runtime pode ser preparado conforme
AGENTS.md; nenhum archive/runtime PostgreSQL temporário é requisito.

```bash
export PYTHONPATH=etl-pipeline/src
export PYTHONDONTWRITEBYTECODE=1
python3.11 -B -m nfl_sideline_etl.temporal_metrics \
  --input etl-pipeline/tests/fixtures/temporal_metrics/package.json \
  --season 2026 --phase REG --team A --target-game-id target --target-week 4 \
  --window LAST_3_CALENDAR_WEEKS --window SEASON_TO_CUTOFF \
  --window WEEK_OBSERVATION --week 3 \
  --as-of-instant 2026-09-28T12:00:00Z --mode POINT_IN_TIME \
  --derived-at 2026-10-09T12:00:00Z --output /tmp/nfl-e5b3-pit-new
```

Para reproduzir reconstruction, no mesmo comando usar
`--mode EVENT_RECONSTRUCTION --retrospective etl-pipeline/tests/fixtures/temporal_metrics/retrospective.json`
e um destino novo `/tmp/nfl-e5b3-reconstruction-new`. Para ausência de prova,
usar `package-unproven.json` e destino novo `/tmp/nfl-e5b3-unproven-new`.
`derived-at` é metadado explícito de derivação; os exemplos fixam-no para bytes
reprodutíveis, sem alegar que fontes existiam no corte. Não vem do relógio no núcleo.

Histórico acrescenta `--window HISTORICAL_REFERENCE --historical-season 2025
--historical-phase REG`; precisa de calendário/estado/fontes históricos explícitos.
O pacote básico não os contém, então produz bloco histórico com expectativa
UNKNOWN, sem fallback. Teste contrafactual contém histórico POST observado separado.
W1/W2 e bye nunca estendem calendar3; LAST_3_GAMES permanece opcional não implementado.

```bash
python3.11 -B -m pytest etl-pipeline -q -p no:cacheprovider
python3.11 -B contracts/metrics/e5a-v1/verify.py
python3.11 -B -m unittest discover -s contracts/metrics/e5a-v1 -p 'test_*.py' -v
python3.11 -B docs/plans/metrics/e5a-review/reproduce_boundary.py
python3.11 -B docs/plans/metrics/e5b-3/verify.py \
  --output /tmp/nfl-e5b3-verification-new.json
git diff --check
```

`verify.py` executa esses gates, regressão CLI E5b-1 byte a byte, dry-run E5b-2
sem criar archive/conectar, regressão dos três exemplos pela CLI real e comparação
contra a base dos caminhos congelados. Usa diretórios temporários novos e os
apaga; nenhum arquivo temporário pré-existente é dependência. Relatório também
exige caminho novo. Não executa SQL/Java/frontend. Nesta máquina foi usado o
venv já instalado da origem, com PYTHONPATH da worktree:
`/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python`.

## Validação e limites

[verification.json](verification.json): **292 testes ETL offline**, incluindo
**93 novos E5b-3**, oito regressões E5a temporais; **26 exemplos/23 testes E5a**,
**12 hashes congelados**, seis arquivos E5b-1 iguais, dry-run E5b-2 sem DB/archive,
três exemplos CLI completos idênticos, diff check aprovado. Sem skip/falha final.
Testes de propriedade: permutação/reexecução/identidade; réplica não aumenta
amostra; alternativa/calendário futuro inelegível não altera result_id; remover
PBP não melhora cobertura. Audit_id registra alterações de entrada/execução.

Durante desenvolvimento houve correções dos próprios testes (nome reservado
request, reutilização do pedido retrospectivo, ordem de array de razões e instante
da revisão contrafactual após o máximo de evidência requerido e comparação da
auditoria por chave de grupo, independentemente de ordenação). Os ledgers manuais,
pacote E5a e estatísticas/artefatos aceitos não foram ajustados para passar testes.

O núcleo aplica uma **política condicional sobre evidência materializada**. Strings
de origin/reference, hashes e fixtures não autenticam fatos externos. Dados locais
históricos não ganharam receipts passados, encerramento, completude ou modelo EPA.
Essas lacunas permanecem UNKNOWN. Calendar completeness e fechamento de período
precisam de documentos explícitos; scores/datas/mtime/updated_at não os produzem.

Para E5b-4, preparar leitor/materializador separado que recupere conjuntos inteiros,
cálculo/cobertura/somas/manifestos E5b-2 e preserve instantes com precisão original,
origem e política confiável. [Mapeamento e lacuna mínima](DESIGN.md)
explicam que E5b-2 guarda declarações e receipts, mas não fornece automaticamente
prova histórica ou documentos de estado/calendário. Nenhuma lacuna exigiu alterar schema/writer: o pacote temporal
explícito representa as informações adicionais e preserva a ausência de prova.
Java precisa goldens de decimais/razões, revisão e hash novos, sem adaptar FrozenContext.

Supabase completo/advisors continua pendente no escopo E5b-2. Não foi iniciado
Docker/PostgreSQL, lido .env, acessada rede/banco, executado modelo, integrado
consumidor, alterado artefato aceito/snapshot/editorial, feito push/deploy/merge.
