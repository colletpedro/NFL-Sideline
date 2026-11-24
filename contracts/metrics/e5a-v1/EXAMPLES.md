# Exemplos mecânicos e ledger manual

`fixtures/cases.json` contém **26 casos sintéticos**, uma revisão por jogo, times fictícios A/B, timestamps/evidências explicitamente sintéticos. Não são amostra de avaliação humana, dataset NFL, backfill ou certificação point-in-time real. Resultados esperados foram escritos a partir dos ledgers abaixo; o gerador temporário apenas expandiu campos repetidos, não chamou o modelo para produzir goldens. O arquivo expandido é a fonte versionada e dispensa o gerador.

As somas e razões do modelo são strings de frações **exatas reduzidas** (`-1/8`, `1/1000000`); são um formato de auditoria do exemplo, não mudança de JSON público. E5b preserva numeric/decimal e numerador/denominador. Os goldens são subconjuntos escolhidos do resultado, complementados por invariantes sobre todos os campos/roles/fundamentos. Não há comparação do resultado com outro chamado idêntico como única evidência.

## Ledgers que fixam a aritmética

### Volumes semanais diferentes

`unequal_week_volumes`: W1 tem EPA `[1,0]`, soma=1, n=2, sucessos=1; W3 tem `[-0.5,-0.5,-0.5,-0.5,0,0]`, soma=−2, n=6, sucessos=0. Todas classificadas pass. W2 é bye **declarado pelo calendário completo e fechado**.

- Temporada/recorte observado: soma=−1, n=8 → EPA=−1/8=−0,125; sucesso=1/8=12,5%; frequência passe=8/8=100%.
- Média simples das médias semanais: `(1/2 + (−2/6))/2 = 1/12 ≈ +0,083333`. Produz sinal oposto; é proibida na proposta.
- Volume rush=0 conhecido; EPA rush=null. Frequência rush=0/8=0. Não usar o total 8 como denominador de EPA rush.

### EPA ausente em parte das jogadas

`partial_epa`: passe `[0,−0.2,null]`; corrida `[0.000001,NaN,+Infinity,−Infinity]`.

| Fundamento | Volume B | n EPA finito | Soma | Sucessos | Missing / nonfinite | EPA médio | Frequência |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Passe | 3 | 2 | −1/5 | 0 | 1 / 0 | −1/10 | 3/7 |
| Corrida | 4 | 1 | 1/1000000 | 1 | 0 / 3 | 1/1000000 | 4/7 |
| Geral | 7 | 3 | −199999/1000000 | 1 | 1 / 3 | −199999/3000000 | 1 |

SR geral=1/3, passe=0/2=0, corrida=1/1=1. `eligible_n=epa_n+missing+nonfinite` em todos. Missing não é derrota nem zero de EPA. NaN/Infinity são sentinelas **strings na fixture** para que o JSON seja válido. Média simples dos dois fundamentos também não produz o EPA geral. Uma frequência sobre somente EPA finito seria passe=2/3, diferente da frequência proposta=3/7.

### Passe classificado versus dropback

`classified_pass_vs_dropback`:

| Jogada | play_type | EPA | qb_dropback | sack | scramble | pass_attempt fonte |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Lançamento | pass | +1 | 1 | 0 | 0 | 1 |
| Sack | pass | −1 | 1 | 1 | 0 | 1 |
| Scramble | run | +0,5 | 1 | 0 | 1 | 0 |
| Corrida | run | 0 | 0 | 0 | 0 | 0 |

Passe classificado: soma=0, n=2, EPA=0; corrida: soma=1/2, n=2, EPA=1/4. Geral=1/8. Frequência passe=2/4=1/2. Dropbacks diagnósticos=3/4; tentativas de lançamento sem sack=1 (não o `pass_attempt` da fonte, que vale 2). EPA por dropback, **fora do núcleo**, seria `(1−1+0.5)/3=1/6`; não pode receber o ID do EPA por passe. As flags extras são observações diagnósticas, não classificadores ocultos do núcleo.

### Filtros e papéis

`population_boundaries`: interceptação pass EPA−2, passe final com penalidade EPA+0,5 e corrida em OT/aborted EPA+1 permanecem. Soma=−1/2; n=3; EPA=−1/6; SR=2/3. Mais seis candidatos com kneel/spike/deleted/special/conversion=1 ou kneel desconhecido ficam fora; no_play e kickoff ficam fora por tipo. Garbage time (wp alto na corrida) não muda o cálculo. Todas as flags suplementares estão no arquivo; o modelo não precisa interpretar descrições.

`defense_is_opponent_success`: ataque A produz `[+1,−0.5,0]` contra B. Soma=1/2, n=3, EPA permitido por B=+1/6, sucesso **permitido**=1/3. Não inverter EPA nem chamar 2/3 de sucesso defensivo. Os checks reconciliam ataque A e defesa B em todos os fundamentos.

## Matriz de casos e expectativas

| ID | Expectativa concreta |
| --- | --- |
| unequal_week_volumes | Ledger ponderado acima; W2 BYE; 2/2 fontes |
| single_tiny_positive | Uma jogada EPA=10⁻¹⁸; SR=1/1; sinal positivo conservado, sem persistência/confiança |
| zero_and_negative | Passe EPA zero → SR0; corrida EPA−1; geral−1/2 |
| partial_epa | Ledger separado B/E acima; comparação geral inelegível por EPA faltante |
| classified_pass_vs_dropback | Frequência classificada1/2 versus dropback3/4 |
| no_eligible_plays | Fonte completa com no_play+conversão: volume0, EPA/SR/frequência=null; fonte1/1, métrica0/1 |
| all_epa_missing | B=2, epa_n=0, EPA/SR=null, frequência passe1/2 |
| population_boundaries | Ledger de filtros acima |
| bye_and_unknown_source_gap | W1 observado, W2 BYE, W3 SOURCE_UNKNOWN; fonte1/2, EPA observado+1 |
| only_unknown_source | Nenhum volume conhecido; volume=null, EPA=null; fonte0/1 |
| target_future_unknown_bound | Próprio jogo excluído mesmo com data anterior falsa; futuro excluído; bound desconhecido excluído; apenas earlier produz EPA+1. Expectativa temporal global desconhecida, razão de cobertura=null |
| two_events_same_period | Dois IDs W2, só primeiro antes do corte; EPA−1, segundo futuro excluído |
| two_events_same_period_both_eligible | Ambos antes do corte: soma2,n2,EPA1; sem sobrescrever semana |
| identical_duplicates | Mesma jogada repetida: n1,EPA1/2, duplicateRowsIgnored1 |
| conflicting_duplicate | Mesma chave com EPA diferente: rejeitar |
| conflicting_drive | Mesma game/play com drive diferente: rejeitar |
| seasons_phases_scoped_separately | Só REG2026 corrente entra; REG2025 e POST2026 ficam separados |
| post_explicit | POST explícito produz−1; não combina REG |
| historical_separate | REG2025 solicitado como origin HISTORICAL_REFERENCE; não forma atual |
| point_in_time_requires_receipts | Só known-before com receipt antes do corte entra. Unknown/late revisão excluídas; **eventos3 continuam esperados, fonte1/3** |
| exclusive_cut_boundary | event_upper_bound=corte excluído pelo limite estrito; expected0, razão=null |
| season_start_empty | W1 não tem semanas anteriores; sem fallback, expected0, razões/médias=null |
| calendar_unknown_not_bye | W2 não recebe BYE; expected/razão=null com calendário incompleto |
| last_three_games_keep_missing_event | Escolhe W2/W3/W4, inclusive W2 sem PBP; fonte2/3. Não usa W1 para preencher |
| play_calendar_conflict | Phase da jogada diverge do jogo: rejeitar |
| defense_is_opponent_success | Ledger de sucesso permitido acima |

## Propriedades e limites do modelo

23 testes adicionais exercitam goldens, fórmulas/IDs, permutações completas do caso de quatro jogadas, 40 permutações com seed5105 do ledger ponderado, todos os cortes de partição do exemplo com EPA ausente, reunião de batches sobrepostos com dedup, exclusão de futuro, remoção de dados sob calendário/manifesto fixos, vazio/zero, reconciliação de papéis, rejeição de mistura e conflitos, disponibilidade/bordas, schema e cancelamento exato de valores grandes com sinal muito pequeno. Contagens esperadas não são reconstruídas de taxas.

O teste de remoção mantém a expectativa do manifesto congelado; faltarem linhas transforma COMPLETE em PARTIAL, em vez de recalcular a expectativa com o subset restante. Não certifica completude da fonte NFL real. Duplicatas idênticas só mudam contador de auditoria, não cobertura ou números.

`general_integrity_eligible` do resultado é um pré-requisito unilateral geral, não aprovação de comparação; `comparison_eligible` verifica dois escopos/papéis/fundamento. Permitir uma jogada é exibição descritiva, sem limiar estatístico. O modelo não implementa captura de receipts, seleção entre múltiplas revisões, conversão DST, parsing de Parquet, contratos editoriais ou UI. Esses gates são E5b; nenhuma promessa temporal de produção foi validada por timestamps sintéticos.
