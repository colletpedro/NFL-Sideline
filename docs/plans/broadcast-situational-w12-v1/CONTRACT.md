# Contrato situacional privado v1

Este contrato é separado de métricas de EPA, DTOs de observações e snapshots públicos. Não é uma extensão implícita deles. Implementação: `nfl_sideline_etl.situational`; apresentação exclusiva da entrada `broadcast-journey`. [Definições](DEFINITIONS.md) versão 1.0.0; cálculo 1.0.0.

## Pacote físico e procedência

`COMPLETED.json` tem `version=situational-v1`, `bundleId` SHA-256 de `situational.json` canônico e hashes dos quatro arquivos abaixo. JSON canônico usa UTF-8, chaves ordenadas, separadores compactos e newline final; NaN/infinito proibidos.

| Arquivo | Conteúdo |
| --- | --- |
| pbp.parquet | Cópia física dos bytes brutos preservados; pin fixo 4e3707397912babcd0d7d02abd3be95db8e66785250e62bf9d874f37229d895e |
| provenance.json | Raízes verificadas, 162 hashes de cada recuperação, pins de materialização/input e bundle antigo, instante da verificação operacional |
| ledger.json | 882 registros candidatos de terceira e 684 campanhas, incluídos/excluídos, motivos, eventos de entrada/TD/desfechos e IDs originais |
| situational.json | Contrato, versões, garantias UNKNOWN, inventário dos jogos e 192 documentos com ambas as famílias |

Pin ativo: `sha256:2af2a33211c09658fb6b831188dc5c5ac3bee9b3fc4b2b6008748921ac7c339c`. Ledger: `sha256:b3a2cd46ae9e08b1438f3cd707d8dbe214c21a3f6f85c147f0fe0bc3ccc8063d`.

Materialização/input são os pins fornecidos pelo usuário, conferidos por `load_source`, que rederiva a linhagem completa nas duas recuperações. O bundle antigo foi lido integralmente e conferido contra seu pin. O novo pacote não herda os cálculos antigos: usa o PBP bruto copiado e seu próprio cálculo. O instante de verificação não é atualização dos jogos nem evidência de conhecimento temporal.

O reader valida árvore física, rejeita symlinks, confere todos os hashes e pins e recalcula integralmente artefato e ledger a partir do Parquet contido no próprio pacote. Não consulta o banco nem baixa dados. A geração recusa destino existente e publica por diretório temporário irmão. Contagens e razões são inteiros; não se armazena taxa decimal arredondada.

## Documentos e unidades

ID nominal: `TIME/off|def/1|2|1-2`. Matriz exata: 32 times × 2 perspectivas × 3 períodos = 192 documentos; cada documento contém `third` e `redZone`. `season=2026`, `phase=REG`, semanas inclusivas e jogos/adversários explícitos. Jogos individuais têm um membro; W1–2 tem dois, sem sobreposição de unidade original. Os dados não oferecem ranking ou seleção automática de melhor time.

Cada medida tem `numerator`, `denominator`, `denominatorState`, `ratio` (par inteiro ou null), `status`, `unitIds`, `excludedIds`, `exclusions` e `ambiguousIds`. Os IDs de jogada são `game_id:play_id`; campanha `game_id:drive:fixed_drive`, conservando a representação numérica da fonte. Registros originais e `order_sequence` estão no Parquet; o ledger permite rastrear as contagens até eles. A razão não é reduzida: 2/10 conserva o denominador observado.

`third` inclui `byType`, `byDistance`, sacks, scrambles e first downs por penalidade incluídos/excluídos. As faixas e os tipos particionam exatamente a população incluída. Distância inválida/ausente fica em `unknown`. `redZone` inclui desfechos confirmados e `observedEntries`, distinto de campanhas com desfecho confirmado em situações insuficientes. `entryPlayIds` no ledger pode conter várias jogadas, mas a oportunidade é uma só por campanha.

| Estado | Significado | Taxa |
| --- | --- | --- |
| AVAILABLE | Fonte presente e denominador positivo, sem unidades ambíguas | razão inteira |
| NO_OPPORTUNITIES + ZERO | Fonte presente sem oportunidades elegíveis | null |
| INSUFFICIENT | Unidades/flags/posições/desfechos contraditórios ou incompletos | null, mesmo com contagens confirmadas |
| SOURCE_ABSENT | Seleção fora do inventário PBP desta entrega | sem documento substituto ou painel numérico |

SOURCE_ABSENT é o estado da resolução de seleção, não um documento com zeros para semanas não observadas. A seleção confronta jogo, semana, fase e ambos os participantes do calendário com o inventário validado. URL inválida é erro de seleção, não ausência nem preferência anterior. As quatro garantias `completeness`, `expectedCoverage`, `epaModel`, `temporalKnowledge` permanecem UNKNOWN em todos os documentos.

## Transporte e isolamento

Config de operador: `situational-config-v1`, caminho absoluto físico e `expectedBundleId`; variável `NFL_SITUATIONAL_CONFIG`. O startup executa o reader em processo Python com ambiente reduzido, valida o contrato no Node e congela a resposta. O snapshot não muda durante uma seleção. A cópia de recuperação não é fallback; operá-la requer outra config explícita com o mesmo pin.

Endpoint próprio `GET /__situational/`, `X-Local-Situational: 1`, Host exato `127.0.0.1:18098`, Origin ausente ou igual à origem local, sem corpo/query/subcaminhos. Resposta `situational-response-v1` com `bundleId` e `data`. Nenhum caminho é escolhido pelo navegador; POST, Host/Origin/marcador/corpo/path inválidos recebem 403. Config/artefato indisponível recebe 503 e não escolhe outro bundle. Resposta JSON no-store/nosniff. Procedência é privada/local; nada disso entra em `/data`, API pública ou bundle público.

O adaptador Node segue o padrão `.mjs` + declaração já existente, sem nova dependência ou relaxamento de TypeScript. Somente `vite.journey.config.ts` conecta o plugin local. Os gates históricos não foram editados. O [gate próprio](verify-isolation.py) enumera caminhos exatos autorizados e verifica todo arquivo histórico restante, os pins privados e os mesmos JS/CSS públicos.
