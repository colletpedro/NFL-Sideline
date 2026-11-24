# Contrato privado broadcast-comparison-foundation-v1

Projeção 1.0.0 e política `broadcast-comparison-policy-1.0.0`. Somente `2026_01_NYJ_TEN`, 2026 REG W1; referências da liga somente W1. Incompatibilidade exige nova versão. Nenhum contrato anterior é estendido.

## Pacote e leitura

| Caminho | Conteúdo |
| --- | --- |
| comparison.json | Resposta integral para o próximo consumidor, JSON canônico UTF-8, chaves ordenadas, sem NaN, newline final |
| request.json | Pedido nominal exato, sem seleção de fonte pelo navegador |
| definitions.md | Definições situacionais 1.0.0 preservadas e definição da população EPA reutilizada |
| policy.md | Requisitos e matriz normativa das operações novas |
| source-receipt.json | Inventário completo dos hashes verificados das quatro raízes e resultado dos readers operacionais |
| sources/situational/ | Cópia física completa do pacote pinado situational-v1, inclusive PBP/ledger/procedência |
| sources/observations/ | Cópia física completa das 588 observações e shared-source; nenhuma dependência de leitura da worktree original |
| COMPLETED.json | Versão, bundleId = SHA-256 dos bytes de comparison.json e hashes de todos os outros arquivos |

Reader rejeita destinos relativos, symlinks, arquivos/diretórios inesperados, versão, pin e hashes divergentes. Executa os readers antigos nas cópias e rederiva integralmente comparison.json. Recibo contém caminhos históricos como evidência; não são dependências de leitura. Publicação usa diretório temporário irmão e rename exclusivo; destino existente é recusado. A reprodução conserva os mesmos bytes e pin, inclusive o recibo, sem novo relógio. Recibo demonstra integridade operacional, não autentica a verdade externa nem o conhecimento histórico.

## Documento

`productions[0]` = NYJ com a bola, `[1]` = TEN com a bola. `defense` dá contexto adversário à mesma produção. `metrics.third/redZone` conserva a medida original e sua referência; `thirdLong` é o subconjunto de unidades com 7+ jardas, com referências próprias. Cada descritor contém métrica, definição/população/unidade, fonte/coluna, período/jogos, IDs, contagens, estado e garantias. Operações em `comparisons` identificam as duas observações e a permissão aplicada. Diferença é A−B, com A=NYJ/B=TEN; razão exata em fração reduzida, numerador string. Não é diferença de capacidades.

`thirdAttempts`: uma marca por tentativa incluída, ID game/play, ataque/defesa, playId, yardsToGo original, distance, kind, converted, sack/scramble e sourceOrder original. `thirdDistanceByType`: oito células com os IDs reais, contagens e soma das conversões; não é produto de marginais. Distância desconhecida permanece categoria explícita. Tipo `pass` inclui sacks; `run` inclui scrambles.

`redZoneCampaigns`: uma marca por campanha incluída, identidade game/fixed_drive, ataque/defesa, entryPlayIds/entryEvidence, touchdownPlayIds, outcome/outcomeEvidence e todos os IDs cronológicos da campanha. Ordem: order_sequence original crescente; campanha usa primeiro evento da fonte. As 12 evidências de entrada do piloto representam quatro oportunidades, sem multiplicar o denominador. Evidências terminais do piloto são TD/FG; os demais desfechos continuam representados nas referências e fontes preservadas.

`epa`: seis entradas (dois ataques × geral/passe/corrida), cada qual com observação ofensiva original, documento defensivo adversário original, IDs elegíveis e com EPA finito, fonte/coluna e igualdade demonstrada. Originais não recebem novos estados; o descritor/política pertence apenas à nova projeção. Geral usa todos os 60/49 registros elegíveis, não as 10/12 terceiras ou 3/1 campanhas. Numerador original é soma decimal, denominador EPA finito; razão epa original não é média arredondada. Modelo permanece UNKNOWN.

`leagueReferences.third/redZone`: candidatos do calendário W1, inventário ofensivo único por time, representados e sem taxa com motivo. `teamRateDistribution.points` tem uma razão inteira não reduzida por time; `pooledRate` é soma dos numeradores/soma dos denominadores. Ausência, insuficiência e zero ficam fora dos pontos. Não há percentis/rankings/mediana calculados. NYJ e TEN pertencem à referência; não há independência do piloto. IDs referem-se ao ledger da cópia situacional.

`facts`: três fatos restritos ao piloto, participantes, recorte, numeradores/denominadores, IDs das observações/unidades, permissão e limites. `temporalContext`: retrospectivo, sem W2; falta de semanas anteriores na W1 é NOT_APPLICABLE por domínio, não erro de transporte. `market`: inventário apenas dos schedules preservados, valores originais e hash de origem; captura/fornecedor/disponibilidade histórica UNKNOWN, sem permissão de chamar pré-kickoff ou fechamento. `unavailableOperations` preserva os motivos dos usos fora de evidência/escopo.

## Fronteira HTTP própria

Config `broadcast-comparison-config-v1`, `path` absoluto físico, `expectedBundleId`, `port`, `strictPort:true`. Startup valida tudo antes de bind. Host fixo 127.0.0.1, porta exata, sem incremento/fallback. Conflito não encerra processo e não escolhe outra porta. Config/fonte inválida encerra startup sem listener substituto.

Somente `GET /__comparison/`, cabeçalho `X-Local-Comparison: 1`, Host exato `127.0.0.1:18101`; Origin ausente ou `http://127.0.0.1:18101`. Sem query, subcaminho, corpo, Transfer-Encoding ou Expect; duplicatas de cabeçalhos de autoridade/origem/marcador são recusadas. Métodos alternativos não recebem dados. Rotas anteriores não estão registradas nesta instância. Resposta sem envelope: bytes exatos de comparison.json, Content-Type JSON, no-store/nosniff e X-Comparison-Bundle. Snapshot imutável em memória durante a vida do servidor, sem releitura por requisição. Nenhum path ou parâmetro do navegador escolhe arquivo. A recuperação requer outra config explícita; não há fallback automático.
