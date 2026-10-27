# W1–7 · ampliação do acervo local

Entrega em `codex/broadcast-w1-7-v1`, a partir de `38aa975c0bdd8c3d49c0acff8475cc106d149ae4`. A referência W1–2 em 18108 e seus contratos/pins foram preservados. Sem merge, push, deploy, banco ou geração Gemini.

[Hub W7](http://127.0.0.1:18109/?season=2026&week=7) · [W1](http://127.0.0.1:18109/?season=2026&week=1) · [DAL × PHI W7](http://127.0.0.1:18109/?view=matchup-season&game=2026_07_DAL_PHI) · [BUF W1–7](http://127.0.0.1:18109/?view=team-season&team=BUF&returnWeek=7).

## O que está disponível

107 confrontos, 214 produções ofensivas e 32 páginas de time, com EPA geral/passe/corrida, terceiras por distância/tipo, campanhas de red zone, EPA das jogadas que começam na red zone e posições descritivas semanais. A identidade aprovada foi reutilizada, inclusive links de identidade, símbolos de tentativas, ícones de campanhas e classificação recolhida por padrão.

O hub inicia em W7 e oferece as sete semanas sem busca obrigatória. Busca e sugestões incluem o acervo ampliado. Folgas aparecem no hub, no time e na referência semanal. Os agregados usam os jogos efetivos: 22 equipes têm sete jogos; dez têm seis. Uma folga não cria componente vazio ou taxa de 0%.

| Semana | Jogos | Folgas | Taxas de terceira disponíveis | Taxas de red zone disponíveis |
| --- | --- | --- | --- | --- |
| W1 | 16 | Nenhuma | 32 | 31 |
| W2 | 16 | Nenhuma | 32 | 31 |
| W3 | 16 | Nenhuma | 31 | 31 |
| W4 | 16 | Nenhuma | 32 | 32 |
| W5 | 15 | CAR, KC | 30 | 30 |
| W6 | 14 | CIN, DET, MIA, MIN | 28 | 28 |
| W7 | 14 | BUF, JAX, LAC, WAS | 27 | 27 |

Uma página de confronto usa somente o próprio jogo e a liga daquela semana. W1 não recebe dados futuros. A página do time é explicitamente retrospectiva e inclusiva em W1–7. Não há contexto pré-jogo inferido nem referência agregada/ranking de EPA.

## Fontes, revisão e unidades

Fontes oficiais congeladas em 27/10/2026: [PBP 2026](https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet) e [calendário](https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet). Os SHA-256 foram confrontados com os digests dos assets GitHub antes do cálculo. URLs, asset IDs, atualização, aquisição, bytes e hashes estão em `source/receipts.json`, cujo hash também participa do pin da coleção. O pacote guarda os Parquets originais completos; a projeção restringe temporada/fase/semanas explicitamente. A fonte pode receber novas correções; este pacote é uma revisão congelada.

18.738 registros PBP, com identidades únicas e associação ao calendário conferida. A reconciliação independente verificou seis EPA por jogo (642), 192 agregados EPA por perspectiva/fundamento, 214 produções de terceiras, 214 de campanhas, 128 agregados situacionais e 278 leituras de EPA da red zone (214 individuais + 64 agregadas). Há 2.722 tentativas elegíveis com flags definidas, 723 campanhas e 2.096 jogadas elegíveis que começam na red zone. Esses totais de unidades não autorizam uma taxa global da temporada nem tornam disponíveis os recortes insuficientes.

A revisão W1–2 tem os mesmos 5.489 registros. Cinco colunas mudaram (`surface`, `receiver`, `receiver_id`, `fantasy`, `fantasy_id`), sem alteração nos valores, denominadores ou IDs das análises exibidas. Não foi misturado o arquivo antigo com semanas novas. Comparação registrada em [reconciliation.json](checks/reconciliation.json).

As definições anteriores foram reutilizadas nos classificadores: flags e exclusões do EPA, terceira elegível e reconstrução cronológica de campanha. O novo módulo orquestra a janela W1–7 e os componentes variáveis. Somas de EPA usam aritmética exata; agregados reúnem unidades e somam numeradores/denominadores, sem média de médias. As regras de campanha e EPA da red zone continuam distintas.

## Insuficiências reais, sem conversões inventadas

MIN W3 contra TB (jogada 3948) e CHI W7 contra NE (3669) apresentam terceira com flags `converted=0` e `failed=0`, após penalidade. Pela regra existente, suas taxas completas de terceira ficam INSUFFICIENT, sem posição semanal. Unidades conhecidas e exclusões continuam auditáveis. Os adversários e demais métricas permanecem visíveis.

O bloqueio acompanha o componente nos agregados: ataque de MIN/CHI e produção adversária contra TB/NE. As taxas não são completadas descartando silenciosamente a tentativa ambígua. Campanhas sem oportunidade permanecem NO_OPPORTUNITIES, distintas de SOURCE_ABSENT e INSUFFICIENT; zero oportunidades não vira 0%.

Completude, cobertura esperada, modelo EPA e disponibilidade histórica continuam UNKNOWN. Posições descrevem a razão observada entre candidatos ativos da semana; empates usam 1,2,2,4. Não há inferência de qualidade, significância, causalidade, previsão ou novo modelo.

## Integração e isolamento

Novo contrato `broadcast-season-analysis-v1` e política `broadcast-season-comparison-1.0.0`; leitores/validadores W1–2 continuam com seus limites originais. Os componentes recebem contexto explícito de apresentação, período, links e pin; valores padrão preservam o escopo antigo. Novas rotas `matchup-season` e `team-season` recusam semanas/identidades repetidas ou incompatíveis, sem selecionar substituto.

Boundary privado `/__season-analysis/`, somente GET exato em 127.0.0.1:18109, com marcador e pin. Startup valida bytes e reproduz semanticamente todo o pacote antes de servi-lo. O cliente verifica o SHA-256 de cada documento e sua identidade. O pin antigo não é aceito como equivalente. Falha de transporte não usa dados públicos ou semanas antigas.

A troca Geral/Passe/Corrida continua no mesmo bloco e agora fica na URL. Não recarrega a coleção ao mudar somente o fundamento. Histórico restaura o fundamento. Retorno distingue semana de origem da semana do jogo, inclusive em links diretos: W3 → MIN → jogo W1 → retorno W3, mantendo a busca. Evidência em [journey.json](evidence/journey.json) e [continuidade](evidence/foundation-continuity.json).

Pin: `sha256:77af196874e984bfa85a270da8733073f97836e959b6dd3d2cd2ec8a98bc7a0c`.

## Verificação concluída

- Python: suíte com 685 aprovados e nove testes privados inicialmente sem configuração; os quatro arquivos pertinentes foram reexecutados com seus pacotes e passaram 87 testes, incluindo os nove. São **694 casos únicos verificados**, com 25 novos testes de escopo, folgas, ausência, soma e incompatibilidade. Os 25 foram reconferidos no pacote final. Não se somam as repetições como novos testes.
- Frontend: **346 testes em 35 arquivos**, com todas as fixtures privadas configuradas; cinco falhas esperadas legadas preservadas. Inclui validação dos 139 documentos, renderização das 107 composições de confronto e 32 de time, origens de URL e falha de transporte sem fallback. [Log](checks/frontend-final.log).
- TypeScript da UI e boundary, lint sem erros (um aviso já existente), build novo e nove entradas experimentais anteriores aprovados. Build público normal e sob variáveis adversas mantêm os hashes JS/CSS da base. [Isolamento](checks/isolation.json).
- **140 documentos HTTP byte a byte** (índice + 107 jogos + 32 times) e **16 contraprovas** de método, origem, host, corpo, pin, identificador, query e cabeçalhos duplicados. [Registro](checks/http.json).
- **48 combinações**: oito cenários em 1440/390/320 px e fonte raiz 16/32 px. Sem overflow horizontal ou colisões nos eixos dos cenários conferidos. O reflow ampliado é de texto, não somente zoom de imagem. A barra de semanas foi ajustada e reconferida para caber com texto a 200%. Mais 12 combinações conferiram os extremos de EPA de passe (SF +1,060; PHI −0,718), sem colisões: nos domínios assimétricos, o zero ocupa outra linha. Os valores, a escala e seus limites foram preservados; somente a apresentação de eixos nesta nova entrada usa o ajuste. [Extremos](evidence/extreme-pass-axes.json). [Medições](evidence/layouts.json).
- Navegador: busca desde uma letra, acesso ao time com folga, origem/retorno entre semanas, seleção imediata de fundamento, histórico, teclado, skip link focando `main`, expansão de classificação e movimento reduzido (`0s`). URL W8 recusada e retorno explícito à W7. Referências W1–2 preservadas.
- Navegação final sem erros de console; há dois avisos de migração futura do React Router na entrada de desenvolvimento. Não foi feita migração de framework nesta entrega.
- Pacote físico de 147 arquivos (~62,4 MB), cópia integral e reprodução a partir da cópia byte a byte idênticas. [Recuperação](checks/recovery.json).

## Limites e próximo trabalho

Esta é uma integração local de W1–7, não publicação nem sistema automático de atualização. Não foram acrescentadas análises por jogador, pressão ou novos modelos. Não houve nova coleta humana; a evidência anterior continua P01/N=1, com o esclarecimento de EPA sem reconfirmação. Toque em celular físico não foi testado nesta entrega.

A próxima conversa pode definir perguntas para modelos usando este acervo e o inventário de campos/ausências, antes de escolher alvos, janelas temporais e validação. Nenhum treinamento foi iniciado.
