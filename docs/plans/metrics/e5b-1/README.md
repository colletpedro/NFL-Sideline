# E5b-1 — adapter e estatísticas suficientes offline

Implementado em branch local `codex/metrics-offline-e5b1`, base exata
`2ad629831e5ff7385687841ccb93030c0fabc4ee`, confirmada antes da edição.
Worktree: `/Users/pedrocollet/.codex/worktrees/metrics-offline-e5b1/NFL Sideline`.
Os arquivos locais da origem foram preservados. Sem push, merge ou deploy.

A entrega calcula conteúdo presente, por jogo/time/papel/fundamento, aplicando
CONTRACT.md **com a errata de REVIEW.md**. Não altera o pacote congelado E5a,
load_metrics.py, pipeline principal, schema, Java, frontend ou snapshots.

## Organização e identidade

Código: `etl-pipeline/src/nfl_sideline_etl/offline_metrics/`.
`inputs.py` lê bytes uma vez, registra SHA-256/schema/contagem bruta e projeta
colunas locais; Parquet usa Polars já declarado no projeto. JSON usa somente a
stdlib. `validation.py` valida/junta calendário e PBP, normaliza fase/round e
deduplica **todo o bruto**. `population.py` aplica filtros. `statistics.py`
acumula decimais exatos. `provenance.py` valida evidências explícitas vinculadas
aos hashes. `artifact.py` calcula auditoria/reconciliação e publica um diretório
novo atomicamente. `__main__.py` fornece a CLI, sem importar loaders ou aquisição.

Versões: adapter `1.0.0`, artefato **`metrics-offline-v1`**, definição `1.0.0`,
população `classified-scrimmage-v1`, metadataVersion `1`. Essas versões são
independentes dos artefatos editoriais v3/v4 e da versão do modelo EPA, que
permanece `UNKNOWN` quando não fornecida com evidência.

Cada arquivo tem source_revision_id `sha256:<hash dos bytes>`. As partições
recebidas formam **uma revisão composta**, identificada pelo conjunto ordenado
dessas referências; não se escolhe a revisão mais nova. Uma mesma chave em
arquivos diferentes continua sujeita a conflito. Outra correção exige nova
invocação/artefato, sem seleção entre revisões nesta entrega.

O pbp_content_id de cada jogo representa a projeção única normalizada; é estável
sob permutação e reparticionamento com os mesmos valores. coverage_revision_id
incorpora jogo, referências dos arquivos, conteúdo, evidência e versões.
calculation_id incorpora entradas/versões/parâmetros/auditoria/estatísticas.
Caminhos absolutos, nome de arquivo, mtime e relógio da execução não entram nessas
identidades. Outro particionamento físico muda hashes de fonte e a identidade
de proveniência, preservando conteúdo e somas. Reordenar arquivos idênticos
preserva todos os bytes do artefato; acrescentar uma réplica altera auditoria,
sem acrescentar volume elegível. Os checks globais de contagem usam o bruto.

Projeção para réplicas PBP: game_id, play_id, drive, season, season_type, week,
posteam, defteam, play_type, qb_kneel, qb_spike, play_deleted, special_teams_play,
two_point_attempt e epa. season_type é normalizado em phase/round; valores
numéricos em decimais canônicos, incluindo play_id fracionário sem truncamento.
Diferença de drive, EPA, participante, flag ou identidade na mesma chave falha.
Colunas extras (sack, qb_scramble, penalty, qtr, wp, texto etc.) não participam:
não afetam esse núcleo e não são interpretadas como classificadores.

Calendário compara game_id, season, game_type normalizado, week, home_team e
away_team. Scores/datas/odds extras não definem essa identidade de cálculo nem
provam completude; os hashes preservam a identidade dos bytes originais.
REG fica REG/round REG; WC/DIV/CON/SB ficam POST com round conhecido; POST genérico
fica POST/round null. Não se deduz round pela semana ou temporada pelo ano civil.
A validação de temporadas reutiliza `seasons.normalize_seasons`; `--season`
opcional restringe o lote e rejeita entradas de outras temporadas, sem filtrá-las
silenciosamente. A CLI nunca assume arquivos/default de temporada corrente.

## Fronteira bruta corrigida

Antes de qualquer filtro, **todas** as linhas passam por validação de schema,
game/play/drive, season/phase/week e join com calendário, validação dos valores
estruturais presentes e dedup/conflitos. Participantes presentes precisam ser
válidos; times ausentes em linhas fora de pass/run são permitidos, sem imputação.
Essas linhas são excluídas por `outside_pass_run`, auditadas por jogo e jamais
atribuídas artificialmente a time/papel. Flags presentes inválidas e EPA não
numérico continuam erros estruturais até nessas linhas.

Candidatos pass/run exigem ambos os participantes distintos do calendário
**antes** dos filtros, incluindo conversões/kneels que serão excluídos.
Precedência disjunta: fora de tipo → kneel → spike → deleted → especial →
conversão → flag desconhecida. Null não equivale a zero. As contagens raw_n,
unique_n e duplicate_rows_ignored precedem a população e são separadas da
estatística atribuída aos participantes.

Sacks permanecem no passe, scrambles na corrida. Turnovers, penalidade em
jogada final, overtime, aborted e garbage time permanecem conforme a fonte.
Não se inventa dropback ou jogada sem penalidade. EPA defensivo é produção
permitida ao adversário, sem inversão.

## Uso e reprodução

Da raiz da worktree, com Python 3.11+ e dependências de teste já instaladas:

```bash
PYTHONPATH=etl-pipeline/src python3.11 -m nfl_sideline_etl.offline_metrics \
  --calendar etl-pipeline/tests/fixtures/offline_metrics/calendar.json \
  --pbp etl-pipeline/tests/fixtures/offline_metrics/pbp.json \
  --metadata etl-pipeline/tests/fixtures/offline_metrics/metadata.json \
  --season 2026 --output /tmp/nfl-e5b1-synthetic-new

PYTHONPATH=etl-pipeline/src python3.11 -m pytest etl-pipeline
python3 contracts/metrics/e5a-v1/verify.py
python3 -m unittest discover -s contracts/metrics/e5a-v1 -p 'test_*.py' -v
python3 docs/plans/metrics/e5a-review/reproduce_boundary.py
git diff --check
```

`--calendar` e `--pbp` aceitam repetição para arquivos/partições explícitos.
Obrigatórios, assim como `--output`; não há glob, aquisição ou descoberta de
arquivos. Extensões suportadas: `.parquet` e `.json`. JSON tem exatamente
`{"columns": ["..."], "rows": [{"...": "..."}]}`. Declaração de schema é
obrigatória mesmo com rows vazio; tipos Parquet incompatíveis são rejeitados
mesmo sem linhas. Cada registro deve conter todas as colunas
contratuais. EPA não finito em JSON usa string NaN/Infinity/-Infinity;
números JSON não padrão e chaves duplicadas são rejeitados. JSON decimal é lido
sem conversão intermediária para float. Em Parquet, float converte por
Decimal(str(x)) round-trip, conforme E5a. Null e não finito ficam distintos.

Foi usado de fato o runtime já instalado na origem, sem instalação ou .env:

```bash
NFL_E5B_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
PYTHONPATH=etl-pipeline/src "$NFL_E5B_PYTHON" -m pytest etl-pipeline -q
PYTHONPATH=etl-pipeline/src "$NFL_E5B_PYTHON" -m nfl_sideline_etl.offline_metrics \
  --calendar etl-pipeline/tests/fixtures/offline_metrics/calendar.json \
  --pbp etl-pipeline/tests/fixtures/offline_metrics/pbp.json \
  --metadata etl-pipeline/tests/fixtures/offline_metrics/metadata.json \
  --season 2026 --output docs/plans/metrics/e5b-1/synthetic-result
```

O exemplo já existe e a CLI recusará sobrescrevê-lo. Para reproduzir, use um
novo destino em `/tmp`, como no primeiro comando. Não se copiou o venv para a
worktree; PYTHONPATH garante a implementação deste checkout. Não rode comandos
do pipeline para reproduzir essa entrega.

## Artefatos internos

O [resultado sintético completo](synthetic-result/manifest.json) inclui:

| Arquivo | Conteúdo |
| --- | --- |
| manifest.json | calculation_id, versões, hashes dos bytes, schemas projetados, linhas brutas por arquivo, revisões, projeção de dedup, parâmetros, evidência e modelo EPA separado |
| game-audit.json | Todo jogo do calendário, participantes/season/phase/week/round, IDs de revisão, raw/unique/duplicates, exclusões disjuntas, times nulos fora da população, estado/escopo e proveniência |
| statistics.json | Por jogo/revisão/time/off ou def/general ou classified_pass ou classified_rush, eligible_n, epa_n, epa_sum, success_n, epa_missing_n e epa_nonfinite_n |
| reconciliation.json | Totais brutos/únicos/elegíveis/excluídos, motivos, jogos sem linhas PBP e invariantes verificados |
| limitations.json | Limitações explícitas de subset, completude, modelo e temporalidade |
| COMPLETED.json | Marcador de sucesso, calculation_id e SHA-256 de cada arquivo final |

Somas são strings decimais exatas sem escala fixa/rounding intermediário.
O acumulador alinha expoentes e soma coeficientes inteiros, sem depender da
ordem ou da precisão corrente do contexto Decimal. `epa_sum=null` quando
`epa_n=0`; zero finito observado é `"0"`. Não se geram taxas auxiliares.
Eficiência futura deriva de soma/epa_n; SR de success_n/epa_n; frequência de
eligible_n do fundamento/eligible_n geral. Não se reconstrói soma por média.

Toda validação/cálculo ocorre antes de criar a saída. A serialização usa um
diretório irmão oculto `.pending-*`, removido em erro, e um rename atômico
**sem sobrescrita**, inclusive numa corrida com um destino vazio concorrente.
O marcador só é escrito após todos os arquivos. Linux (renameat2) e macOS
(renamex_np) são suportados; outros sistemas não publicam a saída final.
O destino existente/symlink é recusado. Qualquer destino resolvido em
`web-ui/public/data`, inclusive via symlink, é proibido.

## Evidência explícita e estados

O metadata opcional segue [metadata.json sintético](../../../../etl-pipeline/tests/fixtures/offline_metrics/metadata.json).
Formato: metadataVersion1, listas calendar_sha256/pbp_sha256 iguais aos hashes
**únicos** do lote, games por game_id e sources por SHA-256 de PBP.
Cada jogo aceita completeness UNKNOWN/PARTIAL/COMPLETE, expected_unique_rows e
evidence `{basis, reference}`. COMPLETE exige evidência e contagem bruta única
esperada; contagem divergente preserva a declaração e rebaixa o estado efetivo
a PARTIAL. Contagem esperada nunca é comparada com eligible_n.

available_at, event_upper_bound e ingested_at só podem ser fornecidos como
`{value: timestamp ISO com timezone, evidence: {basis, reference}}`; ausentes
ficam null. A CLI normaliza instantes explícitos em UTC, sem derivar de mtime,
gameday, horário de execução ou scores. Não aplica corte temporal a eles.
`sources[sha].source_model_version` usa o mesmo envelope de valor/evidência.
Modelos conhecidos diferentes exigem lotes separados; UNKNOWN não comprova
igualdade de modelo. Evidências são declarações recebidas e vinculadas aos
bytes: o adapter não autentica externamente o documento apontado por reference.

Sem prova, completeness UNKNOWN. Conteúdo observado, inclusive população
vazia, materializa registros com scope AUDITABLE_SUBSET e statistics_status
PARTIAL. Suas contagens são apenas do conteúdo. Jogo sem linhas e sem prova
fica NO_SOURCE_OBSERVATION/SOURCE_UNKNOWN, eligible_content_n null e **sem**
registros de estatísticas. Fonte explicitamente COMPLETE vazia materializa os
12 registros com contagens0 e soma null. O calendário mantém todos esses jogos;
a lista calendar_without_pbp significa sem linhas observadas, inclusive a
fonte vazia declarada, sem inferência de causa. Fonte COMPLETE não significa
EPA/flags completos nem adequação estatística. Não se certifica conhecimento
histórico, completude do calendário, bye ou disponibilidade pregame.

## Resultados e validação

[Sintético](synthetic-result/reconciliation.json): 6 jogos, 27 linhas brutas,
26 únicas, 1 réplica, 12 exclusões e 14 elegíveis. 60 registros de estatísticas:
quatro jogos com conteúdo + uma fonte completa vazia, 12 por jogo.
synthetic-5 continua sem estatísticas; synthetic-6 tem prova explícita sintética
de fonte completa vazia. [Ledger manual](../../../../etl-pipeline/tests/fixtures/offline_metrics/ledger.json)
e [explicação das fixtures](../../../../etl-pipeline/tests/fixtures/offline_metrics/README.md)
fixam resultados independentemente do adapter.

Verificações registradas em [verification.json](verification.json):
83 testes novos; **162 testes ETL offline** (79 anteriores +83 novos);
**26 exemplos E5a e 23 testes originais E5a**; **12 hashes congelados**;
diagnóstico original executado e preservado em
[candidate-boundary-diagnostic.json](candidate-boundary-diagnostic.json).
As duas rejeições sintéticas desse diagnóstico continuam esperadas no modelo
candidato; os testes novos provam o comportamento corrigido do adapter.
`git diff --check` aprovado. Java/frontend não foram executados.

Os dez ledgers E5a aritméticos pertinentes foram confrontados diretamente,
com conversão de soma decimal para fração exata só no teste. Os exemplos
**temporais** continuam verificados no modelo original, sem implementar suas
janelas no adapter. Testes cobrem flags, filtros, identidade/round, réplicas e
conflitos até excluídos, ausência versus vazio/zero, precisão/cancelamento,
permutação de linhas e arquivos, caminhos diferentes com mesmos bytes,
partições sobrepostas deduplicadas antes da agregação por partes, reconciliação
de papéis/fundamentos e falha de validação/escrita sem conjunto final parcial.
A CLI também foi executada sob guard que rejeita imports de ambiente,
DB/aquisição/rede/ETL principal, usando as fixtures JSON.

## Auditoria local opcional, somente leitura

Comando real (novo destino; os arquivos da origem não foram copiados):

```bash
PYTHONPATH=etl-pipeline/src "$NFL_E5B_PYTHON" docs/plans/metrics/e5b-1/audit_local.py \
  --source-root '/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/data/raw' \
  --output /tmp/nfl-e5b1-local-audit
PYTHONPATH=etl-pipeline/src "$NFL_E5B_PYTHON" \
  docs/plans/metrics/e5a-review/reproduce_boundary.py \
  --source-root '/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/data/raw'
```

O probe opcional usa o adapter novo, compara hashes com local-audit.json E5a,
e **não ajusta** contagens. Ausência registra LOCAL_INPUT_ABSENT; hash diferente
registra a diferença e não usa as contagens antigas como alvo de aceite.
Mesmo hash com discrepância rejeita a auditoria. Não é requisito dos testes
nem depende de PBP local para gerar o resultado sintético.

[Registro local](local-audit.json): os **seis hashes** (calendário + PBP de cada
temporada) são exatamente os anteriores. Completude UNKNOWN em todos os jogos;
modelo EPA UNKNOWN; available_at/event_upper_bound null. Não é backfill.

| Season | Brutas = únicas | Fora de pass/run | Fora com time nulo | Conversões excluídas | Elegíveis no conteúdo | Jogos calendário / sem linhas |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2023 | 49.665 | 14.065 | 2.638 | 126 | 35.474 | 285 / 0 |
| 2025 | 48.771 | 14.139 | 2.729 | 130 | 34.502 | 285 / 0 |
| 2026 | 5.489 | 1.654 | 297 | 5 | 3.830 | 272 / 240 |

EPA finito presente em todas as elegíveis desses arquivos; não há réplica nesses
bytes. Isso não certifica completude nem ausência de problemas em outras fontes.

## Preparação para E5b-2 e pendências

Prontos para revisão de persistência: grão por jogo/revisão/time/papel/fundamento,
contagens/somas exatas, IDs de conteúdo e fontes, validação/dedup/filtros,
auditoria e estados explícitos com jogos ausentes. E5b-2 ainda deverá definir
migration/constraints/RLS/grants, archive/receipts, writer transacional e prova
das evidências, inclusive fontes completas vazias. Este formato é **interno**,
sem promessa de compatibilidade com DTO/editorial/visual.

Não implementados: seleção entre revisões, janelas/cortes certificados,
POINT_IN_TIME, prova de encerramento/DST/receipts (E5b-3), leitor/contexto Java,
integração do ETL principal, backfill, novo consumidor visual ou publicação.
Os dados locais não trazem prova de completude, modelo EPA ou disponibilidade
histórica. Essas são lacunas reais de proveniência, preservadas como UNKNOWN.
