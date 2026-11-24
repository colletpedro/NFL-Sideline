# Auditoria de dados — gate PASS para pesquisa retrospectiva local

| Temporada | Jogos REG | Passes elegíveis | Interceptáveis FTN | Taxa | INT |
| --- | --- | --- | --- | --- | --- |
| 2022 | 271 | 18008 | 941 | 5.225% | 418 |
| 2023 | 272 | 18248 | 738 | 4.044% | 430 |
| 2024 | 272 | 17740 | 591 | 3.331% | 387 |
| 2025 | 272 | 17358 | 553 | 3.186% | 380 |
| 2026 | 107 | 7106 | 219 | 3.082% | 146 |


Total: **78.460 passes**, dos quais 71.354 históricos (2022–25) e 7.106 na aplicação. 2023, 2025 e 2026 reproduzem as pistas fornecidas (18.248/738/430; 17.358/553/380; 7.106/219/146). Nenhuma regra foi ajustada para obter esses números.

## Fontes e congelamento

Aquisição em 04/11/2026, instantes UTC por arquivo no [manifesto](evidence/sources.json). PBP2022–25: cópias próprias dos assets oficiais `play_by_play_YEAR.parquet`, sem usar o cache de procedência não comprovada. FTN2022–26: assets `ftn_charting_YEAR.parquet`. PBP2026: cópia byte a byte da fonte aprovada de 27/10, SHA-256 `7a5f4fa5b933b24474d8a5a8c76e57b23b8b50b7e62950ab1e5c9ea00cbf4507`, 107 jogos/18.738 linhas. Nunca foi substituído pelo PBP2026 remoto ou pelo cache W1–2. Schedules nfldata também pinados para confrontar o universo de jogos. Esquemas Arrow completos, metadados Parquet, tamanho, hash, URL, instante e cobertura por arquivo no manifesto. Ambiente de aquisição inicial e ambiente final têm locks preservados; mudança numérica documentada no checkpoint.

Armazenamento durável: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-interception-risk-baseline-v1/20261104-v1`. `raw/` contém fontes; `build-v2/` contém dataset, splits e auditorias; `development-v3/` contém freeze pré-teste e modelos; `evaluation-v1/` teste; `application-v1/` aplicação; `figures-v4/` gráficos finais; `wheelhouse/` dependências. Não há binários brutos versionados no Git. O manifesto não torna um checkout novo autossuficiente: é preciso restaurar essas fontes ou adquiri-las em um store novo, que poderá conter revisões diferentes.

## Funil explícito

| Etapa (remanescente) | 2022 | 2023 | 2024 | 2025 | 2026 W1–7 |
| --- | --- | --- | --- | --- | --- |
| raw | 49434 | 49665 | 49492 | 48771 | 18738 |
| regular_season | 47157 | 47399 | 47274 | 46452 | 18738 |
| window_W1_W7_for_2026 | 47157 | 47399 | 47274 | 46452 | 18738 |
| not_deleted | 47157 | 47399 | 47274 | 46452 | 18738 |
| pass_type | 19393 | 19735 | 19153 | 18741 | 7627 |
| official_attempt | 19393 | 19735 | 19153 | 18741 | 7627 |
| not_sack | 18096 | 18325 | 17839 | 17454 | 7147 |
| not_scramble | 18096 | 18325 | 17839 | 17454 | 7147 |
| not_spike | 18096 | 18325 | 17839 | 17454 | 7147 |
| not_two_point | 18008 | 18248 | 17740 | 17358 | 7106 |
| identified_passer | 18008 | 18248 | 17740 | 17358 | 7106 |


Os filtros são sequenciais, portanto zero em uma etapa pode significar que os casos já saíram antes. `pass_type` retira corridas/scrambles, spikes classificados como tal, special teams, `no_play` e marcadores administrativos; sacks saem depois. Conversões de dois pontos saem mesmo quando `play_type=pass`. Flags desconhecidas não viram zero. Não usamos um `dropna` geral: identidade e cobertura de alvo são etapas explícitas. As features principais não têm ausências entre os elegíveis.

## Penalidades e casos especiais

Penalidades com tentativa mantida pelo PBP permanecem: 225/241/230/251/107 por ano. Não se aplica `penalty==0`. Jogadas `no_play` ficam fora mesmo que FTN tenha charting: há respectivamente 67/34/32/25/19 rótulos positivos em `no_play` REG nos brutos; incluem interferência, holding, offside e outros. Em 2026 são 19 fora do universo, não rótulos elegíveis perdidos. Flags/descrições desses casos foram conservadas localmente em `build-v2/audit/no_play_worthy_YEAR.csv`; as listas de penalidades e tentativas revisadas também ficam em CSV. Não reinterpretamos descrição para salvar/descontar tentativa. Uma linha positiva fora de `no_play`/pass_type em 2022 é outra classificação não elegível; seis sacks em 2022 e quatro em 2023 também têm rótulo positivo. Isso mostra que o alvo bruto não deve ser somado sem população definida.

Throwaways mantidos: 684/744/701/722/318. Incompletos mantidos: 5.985/6.010/5.724/5.761/2.379. Receiver desconhecido: 702/765/727/749/302, sem exclusão. Overtime: 163/84/78/101/71 passes. `aborted_play` aparece em 0/1/2/0/1 elegíveis: uma tentativa após fumble recuperado e três descrições com decisão de replay que termina em passe incompleto; mantidos pela classificação final. Não é correto excluir automaticamente toda flag aborted. Não usamos receiver ou a decisão de replay como feature.

## Cardinalidade e reconciliação independente

Zero chaves nulas, zero duplicatas (até idênticas seriam recusadas) nos dois lados de todas as temporadas. Join validado 1:1 em `(game_id, play_id)` e metadados temporada/semana coerentes. Todos os elegíveis encontram rótulo binário não nulo; nenhum passer ausente. Regra futura: rótulo ausente aborta o gate, nunca False. Correção de fonte exige novo congelamento, não escolher uma duplicata arbitrária.

Na junção de todas as linhas, FTN2022 tem 41.643 correspondências e o PBP 7.791 linhas sem charting; 2023–25 têm respectivamente 48.225/48.031/47.316 correspondências e 1.440/1.461/1.455 linhas PBP sem charting. São fora da população elegível, não perda escondida. FTN2026 tem 18.191 matches no PBP aprovado e 2.381 linhas de 14 jogos W8 ausentes do PBP W1–7, além de 547 linhas PBP sem charting; os 2.381 registros W8 não eram esperados no join da aplicação e foram excluídos pela janela/conjunto de chaves. Mapas de razões e rótulos externos no JSON e Parquets `outside_eligible_YEAR`.

SQLite carregou diretamente os dois brutos, implementou WHERE/JOIN/GROUP BY próprio (sem chamar os filtros pandas), reconstruiu e comparou **cada chave, alvo e INT**, mais contagens/somas por temporada, semana, jogo e GSIS passer. Tudo exato em cinco temporadas. O score pré-jogada foi confrontado com `posteam_score - defteam_score`. [Auditoria completa](evidence/data-audit.json), [semanas](evidence/counts_by_week.csv), [jogos](evidence/counts_by_game.csv), [passers](evidence/counts_by_qb.csv).

O schedule pinado e o PBP compartilham exatamente os 271 jogos REG de 2022, 272 por ano em 2023–25 e 107 em 2026 W1–7. Não apareceu jogo esperado pelo schedule sem PBP. Isso não certifica todas as jogadas de cada partida, nem disponibilidade histórica ou precisão do charting. A menor cobertura FTN de linhas fora de passes em 2022 permanece característica da fonte, sem imputação.

## Alvo versus INT observada

| Ano | Não interceptável / não INT | Não interceptável / INT | Interceptável / não INT | Interceptável / INT |
| --- | --- | --- | --- | --- |
| 2022 | 17025 | 42 | 565 | 376 |
| 2023 | 17455 | 55 | 363 | 375 |
| 2024 | 17095 | 54 | 258 | 333 |
| 2025 | 16730 | 75 | 248 | 305 |
| 2026 | 6864 | 23 | 96 | 123 |


INT não implica automaticamente rótulo FTN positivo (23 INT em 2026 são negativas no charting). O modelo usa FTN como alvo e mantém INT separada, sem segunda regressão ou interpretação de sorte.

## Identidade e estabilidade histórica

Agregação exclusivamente pelo GSIS `passer_player_id`; abreviações e times são exibição. Há colisões reais de abreviação: `J.Daniels` e `K.Allen` representam mais de um ID no histórico. Em 2026 dois `J.Daniels` são mantidos separados (WAS e TB). Trocas de equipe aparecem em 2022 `00-0034855`, 2023 `00-0033949`, 2024 `00-0034177`, 2025 `00-0026158`; não criam dois indivíduos. [Mapa completo](evidence/identities.csv).

A população contém todos os lançadores elegíveis, incluindo jogadores ocasionais de outras posições. Há **62 IDs**, e não afirmamos que sejam 62 QBs de roster: posição não foi certificada por fonte de roster. Todos os QBs com suporte estão no conjunto maior; 32 IDs têm pelo menos 100 passes. A tabela completa evita uma exclusão silenciosa de reservas ou trick plays.

`read_thrown` muda estruturalmente: primárias de 2022 são NA, código 0 só desde 2023; em 2022 há ainda um valor ` CHK` com espaço. Frequências brutas e elegíveis preservadas, sem recodificação nem uso como feature. A queda do rótulo 5,23% → 4,04% → 3,33% → 3,19% → 3,08% não foi explicada como mudança real de comportamento. Dicionário consultado não prova estabilidade de avaliadores/critério entre anos. `date_pulled` é metadado da fonte revisada, não certificado de disponibilidade histórica de cada jogada.

[Licença e atribuição](NOTICE.md). Completude do join ≠ completude da fonte ≠ verdade do rótulo.
