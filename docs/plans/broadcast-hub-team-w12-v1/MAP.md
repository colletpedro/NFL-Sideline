# Mapa de leitura, evidência e operação

| Bloco/destino | Fonte real | Operação e limite |
| --- | --- | --- |
| Hub, semanas e placares | Índice W12 congelado, `games[].calendar` validado e cliente `calendarGame` existente | Somente 32 jogos W1–2; sem heurística de importância ou novos jogos |
| Destaque/apoios/compactos | Mesmos 16 registros da semana | Ordenação por data, desempate ID; diferença apenas visual |
| Busca | `GameSearch`, `suggestGames`, normalização existente e `suggestTeams` | Resultados Time/Partida e destinos explícitos; não substitui seleção |
| Identidade do time | `teamIdentities`, 32 logos existentes e índice de times | Mesmo código do documento validado; variantes de contraste sem placas |
| Síntese W1–2 | `facts` da projeção de time | `facts.permission` + display/aggregate e IDs/unidades/numeradores reconferidos pelo consumidor |
| EPA do time e contra o time | `productions[].epa`, `originalObservation`, `components`, IDs elegíveis/finitos | aggregate/display por observação; escala comum apenas com sideBySide permitido; diferença e liga agregada recusadas |
| Terceiras W1–2 | `metrics.third`, `thirdAttempts`, `thirdDistanceByType` | Soma n/d e união real; uma marca por ID; distância × tipo × conversão da mesma unidade |
| Red zone W1–2 | `metrics.redZone`, `redZoneCampaigns` e entradas/desfechos | Uma campanha por ID. NO_OPPORTUNITIES = 0/0 sem taxa; sem área vazia de marcas |
| W1/W2 componentes | `productions[].components` e `games` | Razões semanais preservadas e links exatos; nenhuma semana é omitida para formar agregado parcial |
| Jogos por trás do recorte | Dois `games` da página, semana/adversário/placar | `Ver confronto` abre só aquela partida; `Ver time` abre W1–2 do participante |
| Confronto | Documento 4/5 original byte a byte | Permissões específicas/fatos/referências semanais/mercado arquivado preservados; links novos aos participantes |
| Regras/auditoria | `definitions`, `policy`, `sources`, originais, garantias e unidades | Modelo/completude/historicidade UNKNOWN. Sem certificação, previsão, ranking ou nova distribuição W1–2 |

## Estados

AVAILABLE permite valor/razão quando a operação específica autoriza. NO_OPPORTUNITIES mantém fonte presente e zero campanhas/tentativas, sem taxa; uma semana 0/0 pode contribuir zero para um agregado válido de outra semana. SOURCE_ABSENT e INSUFFICIENT recusam o agregado pretendido; numerador/denominador null, componentes válidos preservados e explicados. Comparação recusada não apaga resultados individuais, não fornece escala conjunta nem soma perspectivas. Fonte HTTP falha: erro próprio e retorno ao hub, sem fixtures ou troca de entidade/período.

## Navegação e preservação

Hub W1/W2 → confronto da própria semana → time W1–2 → qualquer um dos seus dois jogos → semana de retorno. `q/scope/filter/page/returnWeek` pertencem ao percurso; não são recortes analíticos. Mudança de entidade limpa a leitura anterior e uma revisão de requisição impede respostas atrasadas. Entrada direta, recarga, histórico, âncoras, sugestões, Escape e teclado conferidos. URLs antigas permanecem nas instâncias antigas; na instância nova, explorador/piloto/percurso/calendário anteriores são caminhos secundários.
