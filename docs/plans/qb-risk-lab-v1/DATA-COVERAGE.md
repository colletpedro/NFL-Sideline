# Dados e cobertura · aquisição de 04/11/2026

O fluxo novo consulta a disponibilidade atual, sem abrir ou alterar o avaliador reservado da v2. As fontes foram adquiridas entre 14:47:06 e 14:47:13 UTC (11:47 em Fortaleza). Cópias próprias no store do laboratório; nenhuma fonte anterior foi substituída.

**Incluídos: 121 de 121 jogos REG encerrados, W1–8; 7.970 passes elegíveis; 66 lançadores (57 QBs identificados, 9 de outras posições).** Nenhum jogo encerrado pendente nesta aquisição. 151 jogos sem resultado final no calendário permanecem fora; não são zero eventos. Não inferimos cobertura posterior à W8 a partir do calendário futuro.

| Semana | Jogos utilizáveis | Passes | Interceptáveis FTN | Esperados M3 | INT reais |
|---|---:|---:|---:|---:|---:|
| 1 | 16 | 993 | 33 | 31.0584 | 22 |
| 2 | 16 | 1013 | 25 | 31.6257 | 19 |
| 3 | 16 | 1098 | 43 | 34.8786 | 25 |
| 4 | 16 | 1092 | 32 | 35.5991 | 25 |
| 5 | 15 | 1011 | 23 | 32.6097 | 18 |
| 6 | 14 | 1020 | 34 | 32.3083 | 21 |
| 7 | 14 | 879 | 29 | 28.0391 | 16 |
| 8 | 14 | 864 | 23 | 27.0975 | 24 |

W1–7 preserva os totais conhecidos: 7.106 passes, 219 interceptáveis, 146 INT e 226,1188 esperadosM3. A W8 acrescenta 864 passes, 23 rótulos e 24 INT; não se transforma por isso em teste independente. Não houve escolha de janela por resultado.

## População e encerramento

Reutilizamos `FILTERS` da v1, retirando apenas a antiga fronteira W1–7, conforme decisão do usuário. Unidade: passe PBP `REG`, `play_type=pass`, `pass_attempt=1`, não deletado, sem sack/scramble/spike/dois pontos. Throwaways, incompletos, OT e penalidades com tentativa oficial mantida permanecem. Alvo/recebedor desconhecido não é feature nem exclusão. GSIS ausente ou alvo ausente exclui o **jogo inteiro** desta aplicação, em vez de completar a população com zeros ou fazer `dropna` silencioso.

Encerramento requer trio de placar do calendário completo e coerente **e** um único `END GAME` no PBP com placar final correspondente. Identidade, data, mandante/visitante, fase e semana devem coincidir. O marcador terminal ajuda a detectar truncamento; não demonstra que todas as estatísticas do provedor estão corretas. Scores posteriores/texto de encerramento são usados apenas na auditoria de disponibilidade, nunca nas features.

## Funil sequencial

| Etapa | Excluídos nesta etapa | Restantes |
|---|---:|---:|
| PBP bruto dos 121 jogos | — | 21191 |
| `regular_season` | 0 | 21191 |
| `not_deleted` | 0 | 21191 |
| `pass_type` | 12615 | 8576 |
| `official_attempt` | 0 | 8576 |
| `not_sack` | 557 | 8019 |
| `not_scramble` | 0 | 8019 |
| `not_spike` | 0 | 8019 |
| `not_two_point` | 49 | 7970 |

Funil é sequencial: zero excluído numa etapa posterior não afirma inexistência daquele tipo na fonte; ele pode ter saído em `pass_type`. Por exemplo, sacks ainda constam como `pass` no PBP e são removidos explicitamente. Não forçamos contagens do filtro para reproduzir números anteriores.

## Reconciliação

Chaves PBP `(game_id,play_id)` e FTN `(nflverse_game_id,nflverse_play_id)` únicas e não nulas globalmente; IDs de jogada inteiros. Todas as 7.970 tentativas elegíveis encontraram um único rótulo binário e GSIS. 0 sem match, 0 alvos ausentes, 0 passers ausentes. As 20.572 linhas FTN têm chave no PBP; 12.602 estão fora da população de passes elegíveis. O PBP bruto tem 21.191 linhas; ausência de FTN numa jogada fora do universo elegível não é perda de cobertura do modelo.

A segunda rotina lê **os arquivos brutos**, executa `WHERE` e `LEFT JOIN` em SQLite e compara todas as chaves, GSIS, rótulos, INT e semanas com as evidências servidas. Também reconcilia agregados por jogador e a soma das probabilidades. [Recibo e funil por jogo](evidence/reconciliation.json). Completude do join não certifica completude ou verdade do charting.

| FTN | INT real | Passes |
|---|---|---:|
| Interceptável | Sim | 140 |
| Interceptável | Não | 102 |
| Não interceptável | Sim | 30 |
| Não interceptável | Não | 7698 |

Por isso, 242 interceptáveis e 170 interceptações não são a mesma variável.

## Identidades e posição

Roster semanal 2026, NFL.com via nflverse; join GSIS+temporada+semana+equipe. Aliases históricos de equipe são normalizados (LAR→LA, JAC→JAX, WSH→WAS). A posição primária é conferida no contexto semanal, não por nome abreviado ou posição atual. Classes: QB identificado, outra posição, desconhecida/conflitante. As nove outras posições são P/WR e somam nove tentativas; permanecem no dataset. Não houve desconhecidos nesta aquisição; os testes incluem esse caso. Trocas de equipe permanecem na identidade única e na lista de equipes; conflitos não são resolvidos por escolha arbitrária.

## Fontes pinadas

| Papel | Bytes | SHA-256 | URL |
|---|---:|---|---|
| pbp | 9035092 | `09b2bb5b93d6e825d96ab750f8a89ced4963c021ef1663f474bd15f4ed02ca03` | [arquivo](https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet) |
| ftn | 258662 | `923a2b83fa3f9788aac4301975234d22c70f00d277fb57b8f3d5acb3a0018f5c` | [arquivo](https://github.com/nflverse/nflverse-data/releases/download/ftn_charting/ftn_charting_2026.parquet) |
| schedule | 2188274 | `cea8fbb1705fee0a23c9e7d58aaee7b37f6e76557609c03731611c3c26d034eb` | [arquivo](https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv) |
| roster | 836804 | `881037e48d9f6ff6c72a36044622c66cfb9948f4ac5eeebd42716623195683a6` | [arquivo](https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2026.parquet) |

Os manifests preservam a data de aquisição de cada arquivo, sem confundi-la com data de revisão/anotação. Não temos histórico completo de todas as revisões do provedor. Futuras diferenças por passe serão registradas em `revision.json`, incluindo mudanças de rótulo. A primeira versão não inventa uma comparação com pacote anterior inexistente. Replays desta aquisição tiveram zero mudanças de passes; a promoção da versão 1.0.0 do pipeline alterou metadados do pacote, sem alterar parâmetros ou rótulos.

A [documentação oficial FTN](https://nflreadr.nflverse.com/reference/load_ftn_charting.html) confirma charting manual desde 2022 e atribuição **FTN Data via nflverse**, CC BY-SA 4.0. O [cronograma oficial](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) descreve atualizações periódicas, dependentes da disponibilidade do provedor e sujeitas a correções. Não tratamos esses horários como garantia por jogo. O [nflverse descreve](https://github.com/nflverse) a licença geral CC BY 4.0 e a exceção FTN/ShareAlike; o [repositório de releases](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md) contém a licença geral. A anotação genérica do manifest não certifica direitos subjacentes do calendário/NFL. Dados transformados, sem endosso; não se presume autorização irrestrita de distribuição de derivados/modelos/aplicações. A publicação futura requer preservar atribuição, indicação de transformação e tratar as obrigações aplicáveis; isto não é parecer jurídico.
