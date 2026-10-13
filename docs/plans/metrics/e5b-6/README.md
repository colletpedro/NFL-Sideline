# E5b-6 — backfill limitado e auditoria real

**Candidata ao aceite do orquestrador**, executada em 12/10/2026 (Fortaleza).
Base exata `f8a258b64116aa7f67f4d4d6253d3f00dc91f5e2`; branch
`codex/metrics-backfill-e5b6`; worktree inicialmente limpa:
`/Users/pedrocollet/.codex/worktrees/metrics-backfill-e5b6/NFL Sideline`.
Não se partiu de main nem se copiaram mudanças não commitadas. Implementação
final executada: `cd753da49c752f0545d14d0dad30195af03ca44e`.
Commits posteriores acrescentam somente evidências/documentação; a conferência
final de hashes está em `delivery-verification.json`. Aceite não foi presumido.

A cadeia real passou: inventário → cópias congeladas → plan offline → CLI ETL
local skip-acquire → writer/archive → reconciliação independente → reexecução →
extração nominal/materialização → algoritmo temporal → leitura Java. A cadeia
funcionar **não certifica completude, comparação ou conhecimento POINT_IN_TIME**.

## Escopo congelado antes da execução

O [protocolo inicial](PROTOCOL.md) e [inventário inicial](inventory.json) foram
commitados em `e4150df`, antes da carga. O [inventário final](inventory-final.json)
registra as novas cópias da prova final, com os mesmos bytes. Busca restrita à
raiz de dados explicitamente citada em E5a/E5b-1, sem varredura pessoal.

Seis Parquets encontrados: calendário/PBP de 2023, 2025 e 2026. Todos os seis
hashes conferem com as auditorias anteriores; não há segunda revisão real local
nessa raiz. 2023 foi inventariada e excluída pelo limite de duas temporadas.
2025/2026 incluem todas as partições existentes de cada temporada, sem seleção
por jogo, semana, EPA ou sucesso de validação. Nenhuma sobreposição ou réplica
nesses bytes; os testes sintéticos separados exercitam partições sobrepostas.
Limites prévios: oito arquivos, 256 MiB, 150 mil linhas PBP, mil jogos.
Selecionados quatro arquivos / **14.995.734 bytes**, 54.260 linhas PBP e 557 jogos.

| Temporada / arquivo | SHA-256 dos bytes congelados |
|---|---|
| 2025 schedules | `56818014e9d3d8f42bbfa5e8f787f1c6c412a4fe3f38b55b3d40a8ee3ce10a91` |
| 2025 PBP | `5ed293fdf54d79e34426133829f3111faf577db29b8cfc25cf910d75eb55b2ef` |
| 2026 schedules | `fe33824f2d7519a7e550feccedb66d670d0de1af83e27c5af6084c45f488f81d` |
| 2026 PBP | `4e3707397912babcd0d7d02abd3be95db8e66785250e62bf9d874f37229d895e` |

Caminhos, tamanho, schema inteiro, fases, semanas, participantes, todos os IDs de
jogos, exclusões e comparação histórica estão nos inventários. As cópias foram
rehashadas antes/depois de execução e tornadas somente leitura; originais
preservados. Nenhum archive anterior foi movido ou copiado.

Origem nflverse via nflreadpy é **declarada** nos documentos anteriores. Os bytes
locais/hashes e auditorias são as evidências efetivamente disponíveis; não há
receipt da aquisição upstream, atestado de versão EPA, completude ou ingestão
histórica. Hash distinto em reprodução futura deve identificar revisão distinta;
não implica corrupção nem permite exigir as contagens históricas. O harness só
compara essas contagens quando os hashes são os mesmos. Sem as fontes reais,
não se substitui por fixture nem se adquire automaticamente.

**2026 contém REG W1/W2**, frente ao calendário REG W1–18. Não é atualização da
semana corrente. Calendário com 272 jogos não prova PBP completo nem completude
certificada do próprio calendário. Nome, mtime, placar e data de jogo não foram
usados como prova temporal.

## Reconciliação e qualidade

[audit.py](audit.py) não importa adapter, writer ou loaders: lê a projeção bruta,
valida join/season/phase/round e participantes antes de filtrar, normaliza números,
deduplica por game/play sem resolver conflitos por ordem, classifica exclusões
com precedência contratual e acumula `Fraction(Decimal(str(value)))`.
Confronta todos os jogos/grupos com artefato e SQL, inclusive colunas numeric e
record_json. Recalcula IDs de conteúdo/cobertura/conjuntos e hashes de cálculo/
artefato. Associações e conjuntos completos são conferidos independentemente;
nenhuma duplicação por associação/revisão foi observada. Sem médias de médias
ou aproximação float como prova de igualdade das somas novas.

| Temporada/fase | Calendário | Jogos observados | Brutas = únicas | Elegíveis | Excluídas |
|---|---:|---:|---:|---:|---:|
| 2025 REG | 272 | 272 | 46.452 | 32.813 | 13.639 |
| 2025 POST | 13 | 13 | 2.319 | 1.689 | 630 |
| 2026 REG | 272 | 32 | 5.489 | 3.830 | 1.659 |

2025: 14.139 fora de pass/run +130 conversões =14.269 exclusões; 34.502 elegíveis.
2026: 1.654 fora de pass/run +5 conversões =1.659 exclusões; 3.830 elegíveis.
Zero réplicas/conflitos. Todos os 3.804 grupos reconciliam general=passe+corrida,
ataque=produção permitida pela defesa adversária e eligible=finite+missing+nonfinite;
success usa apenas EPA finito. Volume independe da disponibilidade de EPA.
Somas exatas globais ofensivas gerais (cada jogada uma vez):
2025 `10974902863875509417649/62500000000000000000`;
2026 `148858071784017686597/10000000000000000000`.

Há **570 EPA nulos brutos em 2025 e 64 em 2026**. Eles estão fora de pass/run,
conforme [evidências selecionadas](selected-evidence.json). A flag two_point_attempt
é nula em 1.511 linhas brutas de 2025 e 172 de 2026, também fora de pass/run.
Nenhum candidato pass/run tem EPA nulo ou flag nula; nenhuma elegível tem EPA
não finito/ausente ou flag desconhecida. Isso descreve esses arquivos, não fontes
externas. As exclusões não imputam times em eventos administrativos.

O legado foi auditado separadamente: 34.632 elegíveis em 2025 e 3.835 em 2026,
570 e 64 linhas time-semana. A diferença exata para a população nova é a inclusão
legada de 130/5 conversões. Fórmulas/filtros/caminho canônico permanecem intactos.
Chaves/volumes legados são exatos; médias SQL são diagnósticos float com tolerância
absoluta explícita de 1e-12 (maior erro observado 1.11e-16). Essa tolerância não é
usada para provar as somas novas nem comparar contratos distintos.

Casos reais escolhidos pela primeira identidade lexical que satisfaz cada
condição: `2025_01_ARI_NO`, `2026_01_ARI_LAC` (passe/corrida, volumes distintos,
exclusões); `2025_19_BUF_JAX` (POST); `2026_03_ARI_SF` (sem observação).
O supplement registra também a primeira linha bruta com EPA ausente/flag nula
por temporada e uma conversão excluída. Cada fundamento conserva denominadores
próprios: EPA=soma/epa_n, SR=success_n/epa_n, frequência=eligible_n/eligible_n geral
do mesmo time/jogo/papel, com razões racionais exatas. Não existem casos reais
**elegíveis** de EPA ausente/não finito, nem réplicas/correção upstream; não foram
inventados para preencher a auditoria.

## Persistência, journals e idempotência

Prova final: UUID `a7e3e0df-45c6-4294-810f-9f37a882b21e`, banco
`nfl_e5b2_a7e3e0df45c6`, porta **55514**, root
`/private/tmp/nfl-e5b6-instance-20261012-03`.
Runtime PostgreSQL 17.6 existente, sem download. Harness próprio adapta E5b-2
sem seed sintético; grants de domínio são os de E5b-5, somente nesse cluster.
Duas configs explícitas/domain e writer, ambos sem superuser/CREATEDB/CREATEROLE/
REPLICATION/BYPASSRLS. Admin apenas prepara a instância. `.env` e configuração
ambiental do caminho legado não foram usadas.

| Lote | Run inicial / repetição | INSERT inicial | Reuso inicial | INSERT repetição | Reuso repetição |
|---|---|---:|---:|---:|---:|
| 2025 | 1 / 3 | 4.020 | 0 | 0 | 4.020 |
| 2026 | 2 / 4 | 956 | 2 | 0 | 958 |

Os quatro ingestion_runs terminaram SUCCEEDED. A diferença de duas reutilizações
na carga inicial 2026 corresponde ao blob/receipt de limitations.json, compartilhado
entre lotes. Persistidos: 2 cálculos, 2 artefatos/12 arquivos, 4 fontes, 4 conjuntos/
4 membros, **557 coberturas/associações**, **3.804 somas**, 15 blobs/receipts.
240 jogos sem observação ficam com cobertura UNKNOWN e **sem grupos zero**.

Plan cria tentativas próprias sem ingestion_run/SQL. Cada carga conserva nove
estados: FROZEN, RUNNING, CALCULATING, VALIDATED, PERSISTING, ARCHIVED,
PRIVATE_COMMITTED, FINISHING_GLOBAL, SUCCEEDED. UUIDs, estados, fontes, versões,
IDs por jogo e receipts estão na [prova estruturada](database-proof.json).
Na reexecução: novos output/tentativa/run, mesmo archive/bytes/metadata; **zero
inserções privadas /4.978 reutilizações**. Snapshot de todas as linhas (incluindo
persisted_at), blobs, receipts e journals anteriores exatamente preservados.
IDs de cálculo/artefato/cobertura/conjuntos/fontes/receipts iguais.

Não houve falha da cadeia aceita com esses dados nem revisão real corrigida
local disponível. Não se sobrescreveram fontes nem se apagaram registros válidos.
Recuperação após falha/rollback e revisões sintéticas são regressões separadas
aceitas; não constituem uma correção autêntica do fornecedor. Não há atomicidade
distribuída ou prova de recuperação de queda abrupta nesta carga real. Start_run
já tentado sem ID permanece UNKNOWN, conforme testes aceitos, sem atualizar
arbitrariamente uma linha. Supabase completo/advisors permanece pendente.

## Materialização, temporal e Java

Extração read-only REPEATABLE READ com seleção nominal dos dois lotes completos,
recuperação integral das quatro fontes e dos artefatos. Materializador v2 conserva
557 associações, 3.804 somas e 240 diagnósticos NO_SOURCE_OBSERVATION.
Input `metrics-temporal-input-v3`, algoritmo `metrics-temporal-1.1.0`, resultado
`metrics-temporal-result-v3`. Manifestos/coberturas/IDs/precisão/subsets/UNKNOWN
originais preservados; modelo desconhecido não foi promovido a conhecido.

| Identidade | Valor |
|---|---|
| calculation 2025 | `sha256:8d5c1e68b2e63ebb23663cb108f61b8eb23b3aa68226a6184cbc9e810299ddd3` |
| calculation 2026 | `sha256:a8dcb12f222da8e1beebf92baf7e75f81413220202cbe26b6190ad356a3b7e37` |
| artifact 2025 | `sha256:5065c785a921229a3cbb9d0fc92b9b9993bb82c34febb3f238ca802408aa9dd1` |
| artifact 2026 | `sha256:9283dccd46c76e56ee5246dd8009f07870a6e21eb7e6f5a949840e755593b64e` |
| materialization | `sha256:5a0f23fa26fe9b90eddbae03c6b587498e58829b22f9806f9312f76d964d2ea5` |
| input | `sha256:448a1b9601a73260b12083fafb815f0759b3dac392d61d6b637e295db3f8e172` |
| JAR reconstruído offline | `895dd6efd0eb463a41c1248381bebff22ee63f367882a296df9b0cb9a051130e` |

Três pedidos PIT explícitos (2025 REG/POST, 2026 REG), corte
`2026-10-13T00:00:00Z` (12/10 21h Fortaleza): UNKNOWN, expectedGames/sourceRatio
null e **nenhum agregado**. A equipe/alvo lexical serve somente à prova do leitor;
não é um pedido pregame certificado. Assinatura do período, request e decisões
permanecem nos resultados. Nenhum documento histórico/fim de evento foi inventado;
trustedOrigins vazio e nenhuma evidência auxiliar adicionada. Receipts novos são
observações locais desta execução, posteriores ao corte, não disponibilidade
histórica nem ingestão inferida de persisted_at. Não se usou EVENT_RECONSTRUCTION.

Java 21: `mvn -o clean package -DskipTests` com BUILD SUCCESS; JAR novo, sem target
antigo. Leitura real dos três artefatos pelo comando metrics-temporal-read passou.
Java/frontend não foram alterados; suas suítes completas não foram repetidas.
Input/materialization/audit IDs diferem entre instâncias porque receipts/derivedAt
são novos; calculation/artifact e os três result IDs sem agregados permanecem.

## Matriz de prontidão

| Temporada/fase | Integridade/reconciliação | Cobertura observada | Completude | Modelo EPA | Disponibilidade/ingestão histórica | Fim eventos | Temporal/comparativa | Consumo editorial |
|---|---|---|---|---|---|---|---|---|
| 2025 REG | igualdade exata | 272/272; W1–18 | UNKNOWN | UNKNOWN | UNKNOWN / UNKNOWN | UNKNOWN | UNKNOWN / não elegível | subset por jogo auditável; bloqueado para comparação certificada |
| 2025 POST | igualdade exata | 13/13; W19–22; 6 WC/4 DIV/2 CON/1 SB | UNKNOWN | UNKNOWN | UNKNOWN / UNKNOWN | UNKNOWN | UNKNOWN / não elegível | mesma limitação; fase/round conservados |
| 2026 REG | igualdade exata | 32/272; PBP W1–2; 240 sem observação | UNKNOWN | UNKNOWN | UNKNOWN / UNKNOWN | UNKNOWN | UNKNOWN / não elegível | conteúdo local antigo/incompleto; causa da ausência não comprovada |

Integridade descreve bytes e reconciliação mecânica; não autentica fornecedor.
Ausência não foi atribuída a delay, falha de ingestão ou bye. EPA conhecido nas
jogadas não significa versão do modelo conhecida. Não se estimaram confidence,
threshold de relevância, incerteza estatística ou vencedor.

Bloqueios e próximos passos, em ordem:

1. **Aquisição/proveniência:** projetar observações prospectivas verificáveis de
   fontes/partições, modelo EPA, completude por jogo/calendário, ingestão e estados/
   encerramento de eventos. Recuperar documentos históricos somente se realmente
   existirem; não retrodatá-los. Aquisição permanece outra autorização/entrega.
2. **Dados/cobertura:** obter/validar o restante de 2026 em entrega própria; manter
   240 lacunas explícitas e não atribuir causa sem prova. Mesmo 2025 observado
   integralmente em quantidade ainda precisa de comprovação de completude.
3. **Contratos/consumidores:** planejar integração JPA/editorial/visual em contrato
   próprio que conserve populações, fase/round, denominadores, modelos/subsets,
   assinatura do período e UNKNOWN. Não exigir equivalência ao legado. Um modo
   retrospectivo exigiria escolha nominal e prova temporal suficiente própria.
4. **Infraestrutura/rollout:** Supabase completo/advisors antes de aplicação fora
   do cluster descartável; depois avaliação humana/editorial e decisões de rollout
   separadas. Nenhuma dessas integrações/publicações foi iniciada aqui.

**Defeitos novos de código aceito:** nenhum encontrado nesses bytes/regressões.
As lacunas observadas são de proveniência/cobertura; não foram corrigidas por
alteração de adapter/writer/schema/materializador/temporal/loaders/Java. Defeitos
legados já documentados continuam pendentes, fora desta entrega.

## Validação e reprodução

[Gate offline](offline-verification.json): **498 testes ETL**, **9 testes do auditor**,
26 exemplos/23 testes E5a/12 hashes congelados; CLI E5b-1 byte a byte, dry-run E5b-2
sem SQL/archive, contraprovas temporais e identidades/materializador aceitos.
[51 regressões PostgreSQL reais](postgres-regressions.json), em outra instância
nova própria (porta 54777), incluindo casos **sintéticos** de revisão, recuperação,
precision/missing/nonfinite e guardrails. Nenhum mock equivale à prova da carga real.
Gate E5b-6 próprio, base exata; gates históricos intactos. Diff check contra a base
inclui arquivos commitados. Todos os componentes aceitos permanecem byte a byte
iguais à base, comprovado pelo gate e conferência final.

Da raiz da worktree; Python/dependências, Maven/cache, Java21 e PostgreSQL17 devem
**já existir**. O harness não instala/baixa runtime. Use roots/output sempre novos:

```bash
NFL_E5B6_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export PYTHONPATH=etl-pipeline/src
E5B6_RUN_ID=$(uuidgen)
E5B6_WORKSPACE="/private/tmp/nfl-e5b6-real-$E5B6_RUN_ID"
E5B6_INSTANCE="/private/tmp/nfl-e5b6-instance-$E5B6_RUN_ID"

"$NFL_E5B6_PYTHON" -B docs/plans/metrics/e5b-6/freeze.py \
  --source-root '/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/data/raw' \
  --workspace "$E5B6_WORKSPACE"

"$NFL_E5B6_PYTHON" -B etl-pipeline/run_pipeline.py --season 2025 --season 2026 \
  --game-metrics plan --metrics-inputs "$E5B6_WORKSPACE/inputs.json" \
  --metrics-output "$E5B6_WORKSPACE/plan"

JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home \
  mvn -f core-api/pom.xml -o clean package -DskipTests

"$NFL_E5B6_PYTHON" -B docs/plans/metrics/e5b-6/backfill.py \
  --workspace "$E5B6_WORKSPACE" --instance-root "$E5B6_INSTANCE" \
  --pg-bin /private/tmp/nfl-e5b2-pg-runtime/bin \
  --java /opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home/bin/java \
  --output "$E5B6_WORKSPACE/proof.json"

"$NFL_E5B6_PYTHON" -B docs/plans/metrics/e5b-6/supplement.py \
  --workspace "$E5B6_WORKSPACE" --output "$E5B6_WORKSPACE/selected-evidence.json"

"$NFL_E5B6_PYTHON" -B docs/plans/metrics/e5b-6/verify.py \
  --candidate "$(git rev-parse HEAD)" --output "$E5B6_WORKSPACE/offline.json"

"$NFL_E5B6_PYTHON" -B docs/plans/metrics/e5b-5/postgres_regressions.py \
  --root "/private/tmp/nfl-e5b6-regressions-$E5B6_RUN_ID" \
  --pg-bin /private/tmp/nfl-e5b2-pg-runtime/bin \
  --output "$E5B6_WORKSPACE/postgres-regressions.json"

git diff --check f8a258b64116aa7f67f4d4d6253d3f00dc91f5e2
```

Backfill chama a CLI real duas vezes, ambas com `--game-metrics local --skip-acquire`,
seleção congelada, data-dir próprio, domain.json/writer.json explícitos e mesmo
archive. Configs têm exatamente host/port/database/user/password/instance_id,
sem credenciais na CLI. Os comandos efetivos e sua construção estão em
backfill.py/pipeline; os logs locais integrated.log/repeat.log conservam a execução.
Não importa a função de fixture de E5b-5 para gerar fontes; só reutiliza helpers
de login mínimo e snapshots. Não altera gates históricos para uma base diferente.

Em checkout novo, os testes offline e exemplos/ledgers sintéticos são reproduzíveis
sem os dados reais ignorados. Inventários e hashes permitem validar as fontes quando
elas estiverem presentes no caminho autorizado. A execução real exige seus bytes e
runtimes locais já provisionados; hashes não recuperam Parquets inexistentes.
Ausência/corrupção preserva inventário/diagnóstico e não autoriza adquirir nem
substituir silenciosamente por fixture. Uma correção de componente aceito exigiria
reprodução e entrega corretiva separada.

## Encerramento e arquivos locais

A prova final confirmou **pg_ctl status=3**, postmaster.pid ausente, listener
próprio ausente e bind liberado na porta 55514. As duas provas anteriores e a
instância separada de regressões também foram encerradas; UUIDs, roots, hashes
e shutdowns em [local-attempts.json](local-attempts.json). Não houve reset/reuso
ou encerramento de cluster histórico/serviço global.

Workspace final `/private/tmp/nfl-e5b6-real-20261012-03`: cópias Parquet, archives,
journals completos, extração, input/lineage, três resultados e logs permanecem
locais. Clusters desligados e configs privadas mode0600/root0700 preservados.
Input de 23 MiB e lineage de 31 MiB não foram versionados; também não foram
versionados Parquets, banco, archive completo, credenciais ou logs gigantes.
Versionados inventários/hashes, resumos/IDs, evidências selecionadas, scripts,
testes e documentação. Nenhum teste tem esses arquivos locais como dependência
oculta. Observações/receipts de cada execução pertencem ao respectivo archive;
não são cópias da mesma observação histórica.

Sem aquisição, carga/migration remota, modelo, integração JPA/editorial/visual,
workflow semanal alterado, snapshot/aprovação, publicação, push, deploy ou merge.
Semanal/Production conservam o caminho legado e `off` padrão.
