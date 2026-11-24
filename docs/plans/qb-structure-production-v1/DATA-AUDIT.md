# Auditoria de fontes e classificação

Leitura independente dos PBP/FTN brutos, sem limitar ao dataset de tentativas do XINT. [Manifest das cópias próprias](evidence/sources.json) conserva URLs, instantes de aquisição originais, tamanhos, SHA-256, atribuição/licença e hash do manifest pai. Os 27 arquivos do pai foram conferidos antes da cópia; as 20 fontes necessárias desta pesquisa foram copiadas, sem substituir revisões pinadas ou baixar dados novos. [Manifest pai](evidence/parent-sources.json).

## Universo, cobertura e reconciliação

| temporada | dropbacks | lançamentos | sacks_PBP | scrambles_PBP | jogos | dropbacks_QB | dropbacks_outras_posições | FTN_ausente | EPA_ausente |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2023 | 20693 | 18248 | 1410 | 1035 | 272 | 20649 | 44 | 0 | 0 |
| 2024 | 20116 | 17740 | 1314 | 1062 | 272 | 20074 | 42 | 0 | 0 |
| 2025 | 19734 | 17358 | 1287 | 1089 | 272 | 19708 | 26 | 0 | 0 |
| 2026 | 8962 | 7970 | 557 | 435 | 121 | 8951 | 11 | 0 | 0 |

Cada chave PBP/FTN é única e não nula. Duplicata, mesmo idêntica, aborta; não se escolhe cache arbitrariamente. Zero FTN órfão de PBP nas cinco fontes. Os funis, nulls, penalidades, overtime, abortos e códigos brutos estão em `package-release/audit/raw.json`; excluídas conservadas por ano em Parquet fora do Git. Penalidades entram somente quando PBP conserva evento pass/run elegível; no_play, deleted, spikes, kneels e conversões não passam. Não filtramos por sinal de EPA ou pessoa.

2026: 7.970 lançamentos + 557 sacks + 435 scrambles = 8.962 dropbacks. 2023–2026: 69.505. A pista inicial é reconciliada no universo bruto, não usada como meta. As diferenças nas categorias vêm de DES, aborto, flags contraditórias e posição auditada. Nenhuma diferença foi corrigida por imputação.

A segunda implementação usa **SQLite sobre os arquivos brutos**, com filtro, LEFT JOIN FTN, join roster, CASE de classificação e soma/média por GSIS/categoria. Não importa o classificador nem o agrupador principal. Comparou todas as chaves, identidades, categorias, EPA e 1.643 agregados não vazios de 2023–2026; contagens exatas e somas/médias com tolerância absoluta 1e−10. Também reconcilia 20.210 linhas em 2022. [Recibo final](evidence/independent-reconciliation-final.json). Verificador adicional reconstrói todas as sensibilidades, sinal, somas e denominadores por jogador.

## Dicionários e significado

[Dicionário FTN](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html): 0 primeira; 1 segunda; 2 terceira ou posterior; CHK checkdown; DES lançamento desenhado sem progressão; SD lançamento após quebra da jogada. O documento explicita diferença de 2022, quando 0 ainda não é utilizado. [Loader FTN](https://nflreadr.nflverse.com/reference/load_ftn_charting.html): charting manual, FTN Data via nflverse, CC BY-SA 4.0. [Dicionário PBP](https://nflreadr.nflverse.com/articles/dictionary_pbp.html) e [CSV oficial pinado](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv): qb_dropback inclui lançamento/sack/scramble; pass_attempt inclui sacks; run inclui scrambles; epa é EPA do ataque na jogada. Não tratamos pass_attempt como lançamento executado.

As cópias exatas dos dicionários/licença estão em `sources/documentation/`, hash no manifest. A consulta atual à documentação oficial concordou com a cópia pinada sobre estes campos. Não reclassificar anos silenciosamente com base em uma nomenclatura moderna. [Cruzamento dos brutos, incluindo excluídas](tables/raw_cross_2026.csv) e os equivalentes 2022–2025 mostram códigos em corridas/sacks; não são leituras lançadas nesses eventos.

## Códigos, cruzamentos e sobreposições

| season | 0 | 1 | 2 | CHK | DES | SD |
| --- | --- | --- | --- | --- | --- | --- |
| 2023 | 479 | 9234 | 2184 | 2906 | 1966 | 1479 |
| 2024 | 536 | 9697 | 1485 | 2522 | 2022 | 1478 |
| 2025 | 367 | 9736 | 1936 | 2313 | 1714 | 1292 |
| 2026 | 136 | 4369 | 991 | 1038 | 817 | 619 |

Em 2022 são 379 lançamentos sem leitura e nenhum código 0, além de uma string com whitespace ` CHK` no bruto FTN. A normalização conserva original e aplica strip/uppercase, sem converter NA em primeira leitura. Os códigos em todos os eventos têm composição diferente dos lançamentos: não assumir estabilidade só pela presença da coluna. A comparação agrupa as leituras conhecidas e não tenta distinguir primária/segunda por inferência própria.

Scrambles PBP com SD: 7/905 em 2022; 252/1.035 em 2023; 293/1.062 em 2024; 962/1.089 em 2025; 415/435 em 2026. O comportamento muda fortemente. Sacks também podem carregar códigos registrados; a precedência conserva esses códigos como evidência secundária e classifica o evento sack. [Cruzamento elegível completo](tables/classified_cross.csv) inclui ano, valor bruto/normalizado, tipo de evento, categoria, throwaway e saída do pocket. [Flags desenhadas](tables/designed_flags.csv) incluem screen, RPO, play action, trick e sneak; não substituem uma anotação geral de rollout/run desenhado, indisponível nestas fontes.

2026: 355 throwaways. Destes, 192 carregam 0/1/2/CHK, 19 DES e 144 SD. Portanto a pista de 211 com código de leitura se decompõe em 192 de progressão registrada + 19 DES; não são 211 passes de A. Outros códigos não foram apagados. [Motivos por ano](tables/reasons.csv) expõe dois throwaways sem lançamento em 2023, dois throwaways completos/interceptados em 2024 e dois em 2022, além de abortos. Estes conflitos ficam no residual, sem resolver pelo EPA. Não houve código desconhecido após normalização; todos os lançamentos de 2023–2026 têm leitura bruta preenchida. Flags fora do domínio binário seriam residuais; ausência nunca vira false.

## Identidade e posições

GSIS no PBP, roster semanal na mesma temporada/semana/time, aliases documentados. Scramble usa rusher somente após verificar evento run + scramble, flags de passe/sack e concordância com passer se presente. Todos os scrambles têm passer ausente nas fontes; roster resolve seus rushers. Há 11 eventos 2022–2026 de rusher não-QB, todos WR: 3/3/2/2/1 por ano. Conservam GSIS/nome/posição, mas não entram no grupo B de QB; ficam em `scramble_non_qb_position`. Não são identidades desconhecidas. Nenhum GSIS desta aquisição ficou sem resolução após esse esclarecimento. [Tabela por identidade/equipe](tables/identity.csv).

Em 2026 há nove lançamentos de outras posições, um sack de WR e um scramble de WR; nenhum é removido do universo. Trocas de equipe agrupam pelo mesmo GSIS, com equipes no agregado. A unidade não é jogador+time. A primeira implementação de desenvolvimento agrupou os scrambles WR como identidade não resolvida; a correção preserva os GSIS conhecidos e não altera nenhum resultado de QB. Saídas intermediárias permanecem no store, sem consumo ativo.

## EPA, contexto e licença

Zero EPA ausente/infinto nas elegíveis destas revisões. O código mantém n de eventos separado de n EPA e deixa média/soma indisponíveis sem EPA, com testes sintéticos. Nenhuma imputação. Contexto pré-jogada tem distribuições e ausências explícitas nas tabelas; descrição é evidência de inspeção, não entrada de classificação. `qb_hit`, `n_blitzers` e fora do pocket não são medidas de pressão efetiva aqui.

FTN Data via nflverse: dados transformados sob CC BY-SA 4.0, sem endosso. PBP/roster/schedule: nflverse-data CC BY 4.0 com escopo subjacente não certificado juridicamente, licença pinada no store. Não houve publicação externa. Charting/EPA e fontes podem sofrer revisões; não temos o histórico completo do provedor. Atualização é uma nova aquisição imutável, com diferenças por chave/campo e sem ativação automática.
