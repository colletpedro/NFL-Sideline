# Proveniência e alcance da evidência

Inspeção em **08/10/2026**, sem .env, credenciais, banco, download de dataset, pipeline, migration, Gemini ou modelos locais. Worktree criada pela ferramenta do app com ref exata `6d99e66`; branch local `codex/metrics-contract-e5a` criada sobre esse commit. Nenhuma mudança não commitada da origem foi copiada.

## Fontes primárias de semântica consultadas

| Fonte / link | Versão disponível na consulta | Uso / limite |
| --- | --- | --- |
| [nflreadr — dicionário PBP, fonte CSV documental](https://raw.githubusercontent.com/nflverse/nflreadr/master/data-raw/dictionary_pbp.csv) e [página oficial](https://nflreadr.nflverse.com/articles/dictionary_pbp.html) | Página identifica 1.5.1.9002; CSV em master, commit exato não resolvido | Define play_type, qb_dropback, pass_attempt, EPA e flags. Documento, não dataset de jogadas |
| [nflreadr — dicionário schedules](https://raw.githubusercontent.com/nflverse/nflreadr/master/data-raw/dictionary_schedules.csv) e [página oficial](https://nflreadr.nflverse.com/articles/dictionary_schedules.html) | Página 1.5.1.9002; CSV master sem pin de commit | Define season/game_type/gameday/gametime; não fornece availableAt de PBP |
| [nflfastR — Field Descriptions](https://nflfastr.com/articles/field_descriptions.html) | Cabeçalho 6.0.0 | Página consultada; ferramenta não expôs a tabela dinâmica, por isso a semântica foi conferida na fonte documental nflreadr |
| [nflreadpy — load functions](https://nflreadpy.nflverse.com/api/load_functions/) e [changelog](https://nflreadpy.nflverse.com/CHANGELOG/) | Changelog inclui 0.1.5 (19/11/2025), mais seção de desenvolvimento | load_pbp retorna Polars e aceita temporadas desde 1999; sem promessa de reconstrução histórica de revisões |

Resumo derivado do dicionário PBP: passe classificado inclui sacks; corrida inclui scrambles. qb_dropback cobre tentativa, sack e scramble; pass_attempt inclui sacks. EPA é do posteam. A descrição da identidade menciona play_id/game_id/drive. Estes campos não provam que os bytes já existiam numa data histórica. Do schedules: season não é necessariamente ano civil do evento; usar game_type para fase, gametime está em Eastern. Nenhuma dessas descrições certifica fim do evento ou horário de disponibilização.

Tentativas de consultar `R/clean_pbp.R` e `R/helper_clean_pbp.R` em master e API contents do GitHub não trouxeram código utilizável (404/inacessível). Não atribuímos comportamento ao código upstream não lido. Um resultado de pesquisa não primário foi descartado. A documentação forneceu semântica suficiente para o núcleo classificado; reclassificar para dropbacks exigiria conferir normalização upstream/versionamento de dados em E5b ou iniciativa própria.

**Inferências, não fatos certificados:** um arquivo local com EPA, flag e chave únicos permite calcular estatísticas do conteúdo presente. Não demonstra que está completo, nem qual versão do modelo nflfastR o gerou, nem disponibilidade histórica. O cabeçalho 6.0.0 da documentação não é a versão dos EPA nos Parquets locais. Sem metadado de geração, `source_model_version=UNKNOWN`. Os filtros e janelas propostos são decisões de contrato do NFL Sideline, não recomendações oficiais atribuídas ao nflverse.

## Fontes locais versionadas

Todos os caminhos seguintes foram examinados em `6d99e66`; esse commit identifica seus bytes sem consultar estado remoto:

- AGENTS.md, Spec.md (incluindo §§4.3,6/7, snapshot e estado editorial), docs/current-state.md, docs/static-snapshot-contract.md.
- docs/plans/2026-10-06-visual-analysis.md, docs/plans/visual-v1/e4/integration-review.md e REPORT.md; contratos de claims e fixtures congeladas relacionadas.
- etl-pipeline/load_metrics.py, seasons.py, pyproject.toml, testes test_etl/test_run_pipeline e conftest; política de Parquet e loaders de jogos nas referências do inventário.
- As duas migrations existentes, TeamWeekMetrics/Id/repository, MetricCatalog, AnalysisContextBuilder, Evidence/EvidenceWindow, EditorialParameters, MatchupAssessment e FrozenContext.
- Testes de contexto, janela, visual e SnapshotAssembler; allowlist SnapshotContract/Assembler; TeamService/GameService; tipos e comparação pública React.

O pacote não depende de PBP ignorado para seus checks obrigatórios. As afirmações sobre cálculo vigente vêm da leitura direta do código; não confundem nomes de campos com semântica de população.

## Auditoria dos dados locais existentes

[local-audit.json](local-audit.json) registra paths absolutos na origem, tamanho, SHA-256, schema relevante, contagens e dois exemplos diagnósticos por temporada. Os dados foram **apenas lidos**; não copiados nem alterados. Calendários 2025/2026 são versionados; PBP e calendário2023 são locais opcionais. Hash não torna arquivo ignorado reproduzível num clone novo.

| PBP | Linhas brutas | Jogos | Elegíveis legado | Base candidata antes de validar identidade/corte | Conversões retiradas |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 REG+POST | 49.665 | 285 | 35.600 | 35.474 | 126 |
| 2025 REG+POST | 48.771 | 285 | 34.632 | 34.502 | 130 |
| 2026 REG W1/W2 | 5.489 | 32 | 3.835 | 3.830 | 5 |

Nos arquivos: game_id/play_id sem duplicatas, EPA pass/run sem null/não finito, flags de filtro candidatas sem null, e participantes sem divergência no predicado auditado. Elegíveis especiais/deleted=0. Logo a diferença de contagem do predicado base nesses arquivos é exatamente a exclusão de conversões. A base candidata auditada **não certifica** joins com calendário, completude por jogo, source revision ou elegibilidade temporal. Não é saída do ETL novo.

Campos existentes no PBP: drive, phase, IDs, start_time, time_of_day, end_clock_time, play_deleted, special_teams_play, two_point_attempt. Não há no_play ou available_at como coluna; no_play é valor de play_type. Schedules incluem gametime, mas nem status final explícito nem end_time no schema local. Scores podem ajudar a reconhecer registro final no momento observado; não comprovam horário histórico de encerramento nem publicação de PBP.

Reprodução opcional com ambiente **já instalado** na origem (Polars1.44.1, nflreadpy0.1.5, pytest9.0.2):

```bash
'/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' \
  contracts/metrics/e5a-v1/probe_local.py \
  --source-root '/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/data/raw' \
  --seasons 2023 2025 2026
```

A saída deve reconciliar com o registro versionado enquanto esses bytes e runtime forem os mesmos. Script não adquire dados, abre banco, importa loader, chama main de ETL ou lê ambiente/.env. Não foi usado mtime como availableAt. Futuro backfill precisa de archive/receipt próprio e metadados explícitos desconhecidos para o passado.
