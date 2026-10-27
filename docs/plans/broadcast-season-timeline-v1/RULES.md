# Regras da classificação e da cronologia · v1

## Classificação observada

O padrão é o acumulado retrospectivo de 2026 REG/W1–7. O switch “Somente Wn” usa a semana do confronto, tanto em terceiras quanto em red zone. `rank=season|week` preserva essa escolha na navegação e na recarga. As taxas do confronto continuam sendo somente daquele jogo.

A população, elegibilidade, unidades e política são as da coleção W1–7 já reconciliada. O numerador e denominador do acumulado vêm da soma dos componentes autorizados do time, nunca da média de percentuais. Cada equipe aparece uma vez. Folgas não criam jogos, zeros ou oportunidades. As posições usam a regra existente `broadcast-observed-rate-position-1.0.0`: razão exata em ordem decrescente, empates compartilham posição e a próxima posição considera todos os anteriores (1, 1, 3). A taxa conjunta é soma dos numeradores / soma dos denominadores dos times válidos, não média das taxas.

Os 32 times são candidatos no acumulado: 30 têm taxa autorizada de terceira e 32 de red zone. MIN/W3 e CHI/W7 têm flags contraditórias de terceira; seus acumulados de terceira permanecem INSUFFICIENT e não recebem posição. Não se somam apenas as semanas boas para produzir uma taxa parcial. Na W7 os candidatos são os 28 participantes: 27 taxas válidas em cada família, por motivos diferentes. A classificação completa preserva os estados sem taxa e a expansão com movimento reduzido.

Este acumulado inclui semanas posteriores a jogos antigos. É contexto retrospectivo W1–7, explicitamente identificado, sem alegação de informação disponível antes do jogo, desempenho ajustado, significância, estabilidade ou previsão. Não há nova classificação de EPA.

## Evolução do placar

A projeção percorre o PBP em `order_sequence`, começando em 0 × 0, e compara `total_away_score` e `total_home_score` após cada evento. Os campos `away_score`/`home_score` do PBP repetem o resultado final e não são usados para a cronologia. Cada alteração exige apenas um lado positivo, sem redução e com evidência compatível: TD=6; FG=3; extra=1; conversão de dois=2; retorno defensivo de conversão=2; safety=2. Todos os placares finais precisam coincidir com o calendário.

Uma transição excluída, relógio inválido, placar ausente, mudança sem evidência, duplicação de jogada ou divergência bloqueia a cronologia; não se inventa a sequência. No pacote atual, as 107 cronologias passam, com 1.418 transições de pontuação.

O eixo horizontal usa quarto + segundos restantes. Quatro quartos de 15 minutos e, neste acervo, uma prorrogação de até dez minutos. O relógio de OT não é tratado como relógio da regulação. A curva em degraus mostra visitante − mandante: positivo para visitante, negativo para mandante e zero para empate. A escala simétrica sobe em múltiplos de sete e permanece a mesma ao filtrar quartos. Não interpola pontos e não representa probabilidade, momentum ou EPA.

Todos os pontos, inclusive de fora da red zone, entram na curva. A lista de momentos inclui pontuação e desfechos de campanhas de red zone em uma ordem comum. Os times ficam em lados opostos, com ícone, nome, relógio, placar e indicação de campanha. Turnover sem pontuação não muda a curva. A curva registra pontuação ofensiva, defensiva e de special teams conforme a equipe que efetivamente pontuou.

TD e extra/conversão de dois podem virar uma linha visual somente se os eventos de pontuação forem consecutivos, do mesmo time, mesmo drive e mesmo quarto. “+7” é +6 e +1 comprovados; “+8” é +6 e +2 comprovados. Os dois relógios aparecem na linha agrupada e os registros individuais continuam na tabela. Um TD sem extra registrado continua +6. Retorno defensivo permanece separado do TD adversário.

As 723 campanhas são ligadas às evidências de entrada e ao evento terminal original. O relógio e placar do desfecho vêm dessa linha do PBP; a campanha não recebe artificialmente o placar final. Selecionar um momento destaca sua posição na curva e apresenta o placar correspondente. Há tabela equivalente e evidências expansíveis, sem depender da cor ou do desenho.

Filtrar um quarto muda somente a cronologia. A curva começa com o placar trazido do quarto anterior, inclusive eventos de 0:00 na fronteira; o resumo e as taxas continuam do jogo inteiro. Não se concatena uma curva de vários jogos na página do time.

## Limites e recuperação

Completude, cobertura esperada, modelo EPA e disponibilidade histórica continuam UNKNOWN. Reconciliação dos eventos disponíveis não certifica completude da fonte. Não houve pesquisa humana adicional ou teste de toque físico.

A coleção complementar tem contrato próprio `broadcast-game-story-v1` e pin próprio. Contém uma cópia integral da fonte W1–7, que permite reprodução offline. O boundary é GET-only em loopback, exige headers/pin e não serve arquivos arbitrários. Falha da fonte não vira referência semanal silenciosa: a classificação acumulada fica indisponível. As campanhas antigas continuam consultáveis quando a cronologia não pode ser apresentada. O produto público e os contratos anteriores não foram alterados.
