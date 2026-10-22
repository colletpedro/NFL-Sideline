# Matriz antes da implementação

A relação usa o DTO validado, nunca só o resumo. Identidades de time são igualdade literal das abreviações existentes, sem aliases. Fonte do calendário e sessão das observações são independentes.

| Categoria | Prova exigida | Exemplo real / apresentação |
|---|---|---|
| Individual | Participante, temporada/fase, semana solicitada, membro gameId exato e semana/fase compatível; único membro e SINGLE_GAME; fonte PRESENT incluída | BAL em 2026_01_BAL_IND W1: “Leitura arquivada deste jogo” |
| Inclui jogo | Mesmas conferências; múltiplos membros, MULTI_GAME, membro PRESENT incluído | BAL W1–2 em 2026_02_NO_BAL: “Recorte de semanas 1–2, que inclui este jogo” |
| Lacuna | Membro exato compatível, ABSENT, fora de includedGameIds | BAL W3 em 2026_03_BAL_DAL: “Lacuna deste jogo”; agregado com membro ausente não oferece estatísticas desse jogo |
| Outros recortes | Mesmo participante/temporada/fase, mas sem membro compatível que prove inclusão | BAL W1 ao abrir W2: arquivo separado, período explícito |
| Outra temporada/fase | Mesmo participante com temporada ou fase diferente | NE POST2025 ao abrir 2026_03_NE_JAX: arquivo separado, seleção explícita |
| Nenhuma | Nenhum DTO do participante | IND em BAL–IND; confronto GB–CHI W1 sem observações dos dois participantes |
| Incompatível | Time não participante, membro contraditório ou escopo incoerente | URL BAL–IND com DAL: nenhum vínculo válido; leitura bloqueada nessa origem |

Ausência de membro nunca prova exclusividade. Uma semana solicitada não substitui gameId. NO_OBSERVATION não vira SINGLE_GAME. O período declarado e os membros permanecem os originais; não há agregação nova, comparação ou inferência pregame. Trocar recorte recalcula a relação. UNKNOWN continua visível.

Direção visual: cenário #18232B/#24323C, contexto #2B414E/#3E5360, painel contínuo #D6E1E6/#C7D3DC e tinta #15232C. Archivo para contexto/editorial, Roboto Condensed para números. Central em lista compacta com destaque de um jogo real; confronto em duas identidades cromáticas, seguido de regiões de arquivo; leitura individual já aprovada. Retorno explícito e controles nativos. Nenhuma regra sintética entra nos dados.
