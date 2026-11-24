# Features e fronteira de informação

| Campo | Significado | Tratamento fixo |
| --- | --- | --- |
| down | Descida antes do snap | Categórica one-hot; moda só no treino |
| qtr | Quarto; 5=OT | Categórica one-hot; moda só no treino |
| ydstogo | Jardas até first down/endzone | Contínua + log1p |
| yardline_100 | Distância até endzone adversária | Contínua + max(20−yardline,0) |
| quarter_seconds_remaining | Relógio no início da jogada | Contínua; indicador últimos 120s Q2/Q4 |
| score_differential | Placar ataque−defesa no início | Contínua, déficit=max(−score,0), déficit × end_half |
| air_yards | Profundidade do alvo perpendicular à LOS | Somente sensibilidade: contínua, max(−air,0), max(air−20,0) |


Principal: as seis colunas brutas anteriores ao passe estão completas em todos os 78.460 elegíveis. A implementação usa nove termos numéricos e duas categorias; fit 2022–24 produz 18 coeficientes + intercepto. Mediana/indicador de ausência e StandardScaler são ajustados exclusivamente no treino; categorias desconhecidas ficam com zeros no one-hot. A escolha de colunas é allowlist, não seleção baseada no teste. Features geradas conservam nulos antes da imputação. Não há time/QB/receiver/defesa como feature.

Air_yards é resultado da escolha e realização do lançamento, não informação pré-passe garantida. A variante não serve a uma previsão pré-snap equivalente. A profundidade em si não é decisão boa/ruim. Duas ausências históricas recebem mediana e indicadores aprendidos só no treino; zero ausências em 2024–26. Hinge e coluna ausente são colineares em duas raras linhas; regularização estabiliza o fit, mas coeficientes desses indicadores não têm interpretação substantiva.

| Ano | n | wind presente | temp presente | air_yards ausente |
| --- | --- | --- | --- | --- |
| 2022 | 18008 | 34.58% | 34.58% | 1 |
| 2023 | 18248 | 54.39% | 54.39% | 1 |
| 2024 | 17740 | 63.04% | 63.04% | 0 |
| 2025 | 17358 | 63.61% | 63.61% | 0 |
| 2026 | 7106 | 41.09% | 41.09% | 0 |


**Ambientais excluídas de ambos os modelos antes do treino**: cobertura muda muito por temporada/estádio/roof; timestamp de medição anterior ao passe não demonstrado. Wind ausente permanece desconhecido, nunca vento zero. Roof é somente auditoria de grupo, não feature; mesmo quando conhecido, optamos por uma baseline situacional mais simples. [Cobertura por estádio](evidence/environment_by_stadium.csv) contém n e jogos, vento/temperatura presentes. [Distribuições](evidence/feature_distributions.csv) mostram nulos, médias, quantis e extremos por ano. Sem probabilidades inventadas de vento.

Campos de resultado (INT, EPA, reception/drop/catchability, texto, placar posterior), identidade e agregados futuros excluídos. Sem WP, odds, `read_thrown`, `qb_hit`, blitz, pass rushers, saída do pocket, participação ou tempo para lançar. `qb_hit==0` não é clean pocket. A [agenda oficial](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) informa que participação FTN desde 2023 só é disponibilizada após a pós-temporada, não continuamente; não simulamos pressão2026 com outros campos.

Revisões históricas do PBP e features derivadas hoje não provam que os mesmos bytes estavam disponíveis em tempo real. A avaliação é retrospectiva. Metadados de campo pré-jogada vêm do [dicionário PBP oficial](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv), congelado no store. Ranges são validados; nenhum valor foi substituído com informação futura. Score pré-jogada foi conferido contra seus componentes.

Associação de coeficientes: descida4 tem maior log-odds que descida1 neste fit, mas categorias não têm referência única (one-hot completo penalizado), e transformações compartilham efeitos. Consulte coeficientes e parâmetros de escala, sem ler um coeficiente isolado como efeito causal. O modelo não observa defesa/cobertura, precisão, alternativas ou instruções da comissão.
