# Auditoria de dados e do alvo — XINT v1

Aquisição própria: `2026-11-05T17:34:52.773643+00:00`. [Manifest completo com URLs, instantes, tamanhos, SHA-256, atribuição e licenças](evidence/sources.json). Histórico 2022–2025 copiado após conferir todos os hashes do manifest v1; sem nova aquisição que substitua essas revisões. Os manifests antigos, dados e pesquisas permanecem intactos. Modelo não lê `.env`, banco ou ETL operacional.

## População e quatro cruzamentos

Mesma definição aprovada: REG; play_deleted=0; play_type=pass; pass_attempt=1; sack=0; qb_scramble=0; qb_spike=0; two_point_attempt=0; GSIS e FTN explícitos. Overtime incluído; penalidades permanecem somente se PBP conserva a tentativa válida. Nulo não vira zero, FTN ausente não vira False. Sem filtro de posição para construir o modelo.

| Temporada | Passes | FTN=1 / INT=1 | FTN=1 / INT=0 | FTN=0 / INT=1 | FTN=0 / INT=0 | Den. FTN=1 | Den. FTN=0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | 18008 | 376 | 565 | 42 | 17025 | 941 | 17067 |
| 2023 | 18248 | 375 | 363 | 55 | 17455 | 738 | 17510 |
| 2024 | 17740 | 333 | 258 | 54 | 17095 | 591 | 17149 |
| 2025 | 17358 | 305 | 248 | 75 | 16730 | 553 | 16805 |
| 2026 | 7970 | 140 | 102 | 30 | 7698 | 242 | 7728 |

Os quatro cruzamentos somam exatamente o denominador em cada unidade. [Por semana](evidence/cross-by-week.csv) e [por jogo](evidence/cross-by-game.csv) repetem todas as quatro células, inclusive zeros, denominador total e denominador do grupo FTN. A segunda rotina parte dos arquivos brutos, aplica WHERE/LEFT JOIN em SQLite e compara chaves, GSIS, FTN e INT com pandas antes de confrontar todas as células/denominadores. [Recibos](evidence/independent-reconciliation.json). Não usa o agregado do modelo como fonte de verdade.

## Semântica do alvo

O [dicionário PBP oficial pinado](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv) define interception como indicador binário de passe interceptado; pass_attempt também inclui sacks, que o filtro remove. score_differential se refere ao início da jogada, conferido contra posteam_score−defteam_score. Placar posterior, EPA, texto e identificadores não são features. O alvo é um desfecho registrado, não um rótulo de culpa.

[Consistência independente dos campos de evento](evidence/target-consistency.json): zero INT sem GSIS de interceptador, zero GSIS de interceptador em passe com INT=0, zero INT simultaneamente marcadas complete_pass ou incomplete_pass nos elegíveis; zero INT em no_play nas fontes adquiridas. Isso é verificação mecânica do alvo, sem inferir responsabilidade a partir de nomes. Descrições completas ficam nos Parquets/JSONs e nos casos para inspeção posterior.

| Ano | Penalidades elegíveis / INT | Overtime elegível / INT | FTN=1 em no_play excluído | INT em dois pontos excluídos | Alvo/GSIS ausente incluído |
| --- | --- | --- | --- | --- | --- |
| 2022 | 225 / 13 | 163 / 5 | 68 | 0 | 0 / 0 |
| 2023 | 241 / 14 | 84 / 0 | 35 | 0 | 0 / 0 |
| 2024 | 230 / 14 | 78 / 1 | 34 | 0 | 0 / 0 |
| 2025 | 251 / 19 | 101 / 3 | 25 | 0 | 0 / 0 |
| 2026 | 120 / 6 | 82 / 2 | 22 | 0 | 0 / 0 |

Jogadas anuladas, deletadas e dois pontos ficam fora conforme flags/classificação, sem reclassificação por texto. `audit/excluded_YYYY.parquet` conserva linhas/descritivos excluídos. [Funil, nulls de flags e contagens brutas](evidence/raw-audit.json). Todas as chaves PBP e FTN são únicas/não nulas; duplicata até idêntica aborta. Sem deduplicação arbitrária. FTN sem chave PBP: zero nas fontes adquiridas. Todas as tentativas incluídas encontraram um rótulo binário e alvo binário.

## Cobertura e revisão

Histórico elegível: 271 jogos em 2022; 272 em cada ano 2023–2025. Exatamente a base histórica reconciliada anterior; a ausência do jogo cancelado de 2022 não é preenchida. Nenhuma janela foi redefinida para melhorar os números. 2026: 121 jogos encerrados e utilizáveis, W1–8, até 2026-11-02; zero pendências entre encerrados e 151 ainda sem resultado final. Cada um consta no [arquivo de cobertura](evidence/coverage.json).

O gate por jogo exige trio de placar consistente, marcador END GAME único com placar final concordante, calendário/semana/equipes/data concordantes, charting e identidade completos. END GAME é apenas gate de encerramento; descrição não entra no modelo. Um jogo sem alvo/FTN/GSIS/contexto fica como lacuna e outros jogos válidos entram, mesmo em semana parcial. Testes simulam todas essas lacunas. Contradições estruturais abortam em vez de escolher uma revisão.

PBP e FTN 2026 novos têm hashes diferentes do pacote aprovado; **zero adições, remoções ou alterações** nas chaves e campos elegíveis auditados em 7.970 passes: FTN, INT, GSIS e contexto. Não afirmar que todo byte ou campo bruto permaneceu igual. [Revisão](evidence/revision.json). Histórico 2022–2025 pinado não foi redownloaded; sua revisão é a já reconciliada da pesquisa v1, não informação conhecida em tempo real naquele ano. Não temos o histórico completo de revisões do provedor.

## Identificação

GSIS é a identidade; roster semanal por temporada+semana+equipe fornece nome completo e posição. Aliases documentados LAR→LA, JAC→JAX, WSH→WAS. Conflito ou ausência permanece unknown_or_conflicting, nunca resolvido por nome. Troca de equipe não cria outro jogador. Nome PBP é conservado ao lado do nome auditado; se roster não resolve nome, apenas exibição usa fallback PBP.

Em 2026, 66 lançadores: 57 QB, nove P/WR, nenhum desconhecido/conflitante; 7.961 tentativas QB e nove outras. [Identidade por equipe/temporada](evidence/identity.csv). As posições não são features nem filtro estatístico; tabelas e figuras identificam os ocasionais separadamente.

## Rótulo FTN e licenças

[FTN loader oficial](https://nflreadr.nflverse.com/reference/load_ftn_charting.html) descreve charting manual disponível desde 2022; [dicionário](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html) identifica is_interception_worthy. **A anotação/revisão pode conhecer o desfecho; não temos evidência de revisão cega.** `date_pulled` representa obtenção pela rotina do provedor, não comprova instante de anotação nem cegueira. Não usar bom desempenho condicionado ao rótulo como prova de previsão anterior à INT.

FTN: **FTN Data via nflverse, CC BY-SA 4.0**, dados transformados, sem endosso. PBP/roster/schedule: atribuição/licença geral nflverse-data CC BY 4.0, com escopo subjacente não certificado juridicamente. [Licença pinada](https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md), bytes no store/documentation. Preservar atribuição e tratar obrigações aplicáveis dos derivados numa futura publicação. Esta entrega não publica dados/modelo/site externamente.
