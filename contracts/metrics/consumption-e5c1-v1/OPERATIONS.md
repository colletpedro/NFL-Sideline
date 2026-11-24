# Política mecânica por operação e métrica

## Pré-condições

**D**: integridade RECONCILED, origem offline/persistida aceita, escolha nominal
inequívoca, grupo/fórmula exatos e valor definido (denominador positivo).
Para ponto de volume zero, D vale; para EPA com epaN=0 não. Série aplica D a cada
ponto, preserva gaps e não interpola nem liga a lacuna como continuidade observada.
Informar UNKNOWN de modelo/completude/tempo junto dos valores é obrigatório.

**B**: D em ambos + igualdade de definição/unidade/população/papel/fundamento,
season/phase/origin, método/versões e assinatura do período solicitado. Para
ARCHIVED_DECLARED_PERIOD a assinatura é season/phase/origin/kind/weeks, sem
team/gameIds/actualWeeks; se houver modo/corte, ambos precisam coincidir. Não
comparar semanas 1 versus 3, REG versus POST ou períodos “quase iguais”. Diferentes
jogos dos times são aceitáveis sob o mesmo período, com listas explícitas.
O estado básico de compatibility precisa ser KNOWN em ambos; esse estado cobre
definição/população/período, enquanto epaModel qualifica separadamente a família
EPA/SR. UNKNOWN ou CONFLICT básico recusa B mesmo que as strings coincidam.
Se cutoff estiver declarado, deve coincidir nos dois documentos (inclusive
null versus corte declarado); a igualdade do período semanal não o substitui.

**S-V** (volume em amostras): B + manifesto exato de seleção das amostras e
denominadores/IDs disponíveis, sem filtro desconhecido que mude a população entre
lados. Admite PARTIAL/UNKNOWN de completude/cobertura, incluindo expected UNKNOWN;
é somente contagem dos bytes, não taxa de temporada ou desempenho.

**S-F** (frequência em amostras): S-V + geral conhecido do mesmo conjunto/revisões
em cada lado e generalEligibleN>0. EPA missing não importa. Subsets selecionados
com populações diferentes, seleção oculta/conveniente ou flags desconhecidas
podem ser exibidos, mas nem comparação de amostras é defensável.

**P-V/F** (período solicitado): S-V/F + cobertura KNOWN com todos esperados,
calendário/fechamento aplicáveis provados, completude COMPLETE de cada membro,
sem conflitos relevantes. Quantidade de jogos distinta por bye não autoriza
chamar volume de eficiência; contagem bruta admite comparação só literal.

**P-E** (EPA e SR): B + requisitos P-V/F de cobertura/completude + epaN>0 em
ambos, missing=nonfinite=unknownFilterFlags=0 e modelo conhecido **igual** em
todos os arquivos e lados. SR depende de EPA>0, portanto usa a mesma política.
Não há permissão de comparar eficiência em subsets nesta v1, mesmo com modelo
conhecido: decisão conservadora compatível com E5b-3. A alternativa de comparar
somente eficiência amostral requer outro aceite/política, não rename de P-E.

**T**: P-V/F ou P-E conforme família + POINT_IN_TIME aceito separado, target
excluído por ID, corte pregame verificado ≤ kickoff aceito, FINAL/bound < corte
para eventos utilizados, disponibilidade/ingestão e todas as evidências/dependências
< corte. Expectativa conhecida sem remover evento sem fonte; requisito de semanas
fechadas nos modos aplicáveis preservado. Política/origens explícitas e nenhum
conflito pendente. T é elegibilidade dos **dados** para futura regra, não autorização
para conclusão. UNKNOWN nunca passa como true. Não há limiar estatístico.
Na testemunha sintética PREGAME_CUTOFF, corte/alvo/kickoff precisam estar
presentes, ambos os lados referem o mesmo alvo/kickoff e o alvo não pode constar
em nenhum membro, inclusive ABSENT. Cortes distintos já recusam B. Essa
testemunha não executa seleção PIT nem comprova as dependências de PIT_CHAIN.

## Matriz de operações visuais (todos os 22 IDs do catálogo)

| Operação | volume (6) | frequency (4) | EPA (6) | success rate (6) |
|---|---|---|---|---|
| Ponto/série individual | D | D com geral>0 | D com epaN>0; modelo UNKNOWN visível | D com epaN>0; dependência EPA/modelo visível |
| Alinhar séries numa escala comum | S-V; escopo amostral explícito ou P-V | S-F ou P-F | P-E | P-E |
| Diferença numérica A−B | S-V ou P-V, contagem literal | S-F ou P-F, pontos percentuais | P-E, pontos esperados/jogada | P-E, pontos percentuais |
| Ordenar times pelo número | S-V ou P-V; “quantidade observada” | S-F ou P-F; “frequência observada” | P-E; ordem numérica no período | P-E; ordem numérica no período |
| Destacar melhor/pior | RECUSADO: sem direção de qualidade | RECUSADO: sem direção de qualidade | P-E; off maior/def menor, rótulo estritamente “maior/menor EPA [permitido] observado no período” | P-E; off maior/def menor, “maior/menor sucesso [permitido] observado no período” |
| Frase de superioridade | RECUSADO | RECUSADO | RECUSADO como superioridade do time; P-E só frase numérica delimitada | RECUSADO como superioridade do time; P-E só frase numérica delimitada |
| Dados para futura conclusão pregame | T para contagens, não eficiência | T para distribuição, não eficiência | T | T |

Ordenação/destaque coletivo exige **todos os pares** comparáveis e coorte explícita.
Não excluir silenciosamente time recusado para fabricar ranking da liga; ranking
restrito identifica participantes e exclusões. Empates exatos preservados; não
usar arredondamento para desempatar. Defense EPA/SR não invertem os valores;
menor permitido é a direção descritiva, sem previsão. “Melhor time”, “defesa
superior”, vantagem tática, força e vencedor permanecem recusados mesmo com T.
Frase permitida P-E: “Neste período completo declarado, A teve EPA permitido
menor que B (x versus y)”. Isso não valida uma tese editorial.

## Recusa e apresentação lado a lado

Decisão registra operation, metricId, scope (INDIVIDUAL, OBSERVED_SAMPLE,
REQUESTED_POPULATION, PREGAME_DATA), ALLOW/REFUSE e reasonCodes vinculados aos
IDs. Ausência de um requisito recusa a operação; preserve observationIds,
frações e linhagem de cada lado. Recusa de comparação nunca apaga pontos
individuais. Não deixar só um booleano “comparável” sem família/operação/escopo.

Lado a lado com mesmo eixo, sparklines com escalas pareadas, cores favorecendo
um lado, barras de comprimento relativo, ordem por valor ou títulos contrapostos
já comunica comparação e exige a mesma permissão. Se recusada: cartões
independentes em ordem fixa de identidade/time, separados e intitulados por
período; sem eixo comum, diferença, ranking, badges, setas ou verde/vermelho
relativo. Exibir “Comparação recusada: [motivos]” próximo de ambos e os limites
individuais. Se nem essa separação evita leitura comparativa, usar seleção de um
time por vez. Mesma ordem temporal dentro de série individual é organização,
não ranking; sobreposição entre times exige alinhamento permitido.
