# Fixture sintética offline E5b-1

Versão da fixture: 1. Sem dados NFL reais, rede, banco ou PBP ignorado.

Os quatro primeiros jogos reutilizam **linhas sintéticas** dos ledgers E5a
`partial_epa`, `classified_pass_vs_dropback`, `population_boundaries` e
`no_eligible_plays`, preservando o pacote de origem intacto. Identidades foram
renomeadas e synthetic-2 usa calendário WC/PBP POST para testar o join. As flags
suplementares sack/scramble/penalty/aborted/OT/wp permanecem no JSON para mostrar
que não são classificadores ocultos. `ledger.json` contém expectativas escritas
a partir de EXAMPLES.md, sem chamar o adapter para calculá-las.

synthetic-1 acrescenta duas linhas fora de pass/run com times nulos, uma delas
replicada, IDs fracionários e drive null. Seus 10 registros brutos viram 9 únicos,
2 excluídos e 7 elegíveis. Os 7 têm apenas 3 EPA finitos: soma −0,199999,
1 sucesso, 1 EPA ausente e 3 não finitos. Passe tem volume3/n2/soma−0,2;
corrida volume4/n1/soma+0,000001. Isso fixa denominadores diferentes.

synthetic-2: lançamento +1, sack −1, scramble +0,5, corrida 0.
Passe soma0/n2; corrida soma0,5/n2; geral soma0,5/n4. EPA zero observado
é uma string `"0"`, distinta da soma null quando não há EPA finito.

synthetic-3: interceptação, penalidade em jogada final e corrida em OT/aborted/
garbage time permanecem, soma−0,5/n3. Os oito excluídos seguem precedência:
fora de tipo2; kneel/spike/deleted/especial/conversão/flag desconhecida1 cada.
synthetic-4 contém no_play e conversão: conteúdo presente, população vazia,
completude UNKNOWN, zeros apenas no subset auditável.
synthetic-5 não tem linhas nem evidência: auditoria SOURCE_UNKNOWN, sem registros
de estatísticas; não representa bye nem zero certificado.

## synthetic-6

A fixture **declara explicitamente** uma fonte completa vazia para esse jogo,
com contagem bruta única esperada0 e evidência `SYNTHETIC_COMPLETE_EMPTY_SOURCE`.
É uma prova dentro do exemplo sintético, não afirmação sobre futebol real.
`metadata.json` liga essa declaração aos SHA-256 dos bytes de calendar.json e
pbp.json. Sem esse arquivo, o jogo continua UNKNOWN sem estatísticas. Com ele,
materializam-se 12 registros FULL_GAME_CONTENT/COMPLETE, contagens0 e soma null.

Os outros jogos continuam UNKNOWN mesmo com scores inexistentes ou counts
consistentes. Nenhum timestamp ou modelo EPA conhecido é fornecido.
