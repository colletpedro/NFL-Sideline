# Model card v2 — M3 escolhido para avaliação futura, sem validação final

Regra predefinida cumprida por M2 e M3 nos dois anos completos2024/2025. M3 tem menor LL pooled e é o único candidato contextual congelado para reserva. M0 e M1 continuam referências obrigatórias; M2 fica apenas auditável. [Protocolo](EXPERIMENT-PROTOCOL.md), [decisão completa](evidence/selection.json), [freeze](evidence/frozen/freeze.json).2025 e2026 W1–7 eram conhecidos antes desta rodada; não são novos testes.

M3 para2026: estrutura/contexto v1 em2023–24, C=.1, preprocessing só nesse treino. Offset de intercepto −0,1593395890254225 estimado em2025 separado, com estrutura e escalas imutáveis. Não houve refit da estrutura com2025 após calibrar. Features/sigmoide/JSON/solver são da v1. Sem profundidade, identidade, modelo de pressão, WP ou segundo alvo. Referência M1 usa553/17.358 da temporada2025. M0 usa estrutura original2022–25.

| Período conhecido | Modelo | LL ↓ | Brier ↓ | AP ↑ | AUC ↑ | Observados | Esperados | O/E |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | M0 | 0.14680295 | 0.03227239 | 0.057770 | 0.573713 | 591 | 820.12 | 0.721 |
| 2024 | M1 | 0.14677663 | 0.03225550 | 0.033315 | 0.500000 | 591 | 717.46 | 0.824 |
| 2024 | M2 | 0.14563726 | 0.03217296 | 0.048773 | 0.570050 | 591 | 715.23 | 0.826 |
| 2024 | M3 | 0.14539418 | 0.03214285 | 0.054561 | 0.572271 | 591 | 715.95 | 0.825 |
| 2025 | M0 | 0.14120157 | 0.03087377 | 0.044762 | 0.584272 | 553 | 734.47 | 0.753 |
| 2025 | M1 | 0.14117772 | 0.03084566 | 0.031859 | 0.500000 | 553 | 578.27 | 0.956 |
| 2025 | M2 | 0.14026540 | 0.03078537 | 0.042402 | 0.570951 | 553 | 582.83 | 0.949 |
| 2025 | M3 | 0.13966077 | 0.03074278 | 0.045524 | 0.585908 | 553 | 583.27 | 0.948 |
| 2026 W1–7 | M0 | 0.13734305 | 0.02984317 | 0.052824 | 0.578097 | 219 | 282.19 | 0.776 |
| 2026 W1–7 | M1 | 0.13759546 | 0.02987029 | 0.030819 | 0.500000 | 219 | 226.39 | 0.967 |
| 2026 W1–7 | M2 | 0.13706474 | 0.02984047 | 0.040229 | 0.559587 | 219 | 226.02 | 0.969 |
| 2026 W1–7 | M3 | 0.13632541 | 0.02977043 | 0.051078 | 0.574272 | 219 | 226.12 | 0.969 |


| Ano | M3−M1 LL | IC95% jogos | M3−M1 Brier | IC95% jogos |
| --- | --- | --- | --- | --- |
| 2024 | -0.00138245 | [-0.00241914; -0.00045358] | -0.00011265 | [-0.00023149; -0.00000889] |
| 2025 | -0.00151695 | [-0.00259206; -0.00054188] | -0.00010289 | [-0.00019062; -0.00002367] |
| 2026 | -0.00127005 | [-0.00242924; -0.00015241] | -0.00009987 | [-0.00020243; -0.00000779] |


Pooled2024/2025, M3−M1 LL−0,00144896, IC95%[−0,00215155;−0,00077219]; Brier−0,00010782, IC[−0,00017580;−0,00004294]. Dois anos conhecidos apoiam uma utilidade contextual modesta além da referência recente. Seleção após examinar o histórico não é evidência confirmatória independente. Não avaliamos se a diferença entre M3 e M2 é estatisticamente conclusiva.

| Ano | Modelo | Intercepto offset [IC95%] | Inclinação [IC95%] |
| --- | --- | --- | --- |
| 2024 | M0 | -0.343 [-0.426; -0.258] | 0.925 [0.658; 1.203] |
| 2024 | M1 | -0.201 [-0.286; -0.116] | não identificável (constante) |
| 2024 | M2 | -0.199 [-0.282; -0.115] | 0.860 [0.586; 1.142] |
| 2024 | M3 | -0.200 [-0.284; -0.115] | 0.914 [0.648; 1.188] |
| 2025 | M0 | -0.296 [-0.383; -0.212] | 0.944 [0.662; 1.228] |
| 2025 | M1 | -0.046 [-0.133; +0.037] | não identificável (constante) |
| 2025 | M2 | -0.054 [-0.141; +0.030] | 0.855 [0.525; 1.179] |
| 2025 | M3 | -0.055 [-0.143; +0.029] | 0.963 [0.683; 1.243] |
| 2026 | M0 | -0.264 [-0.413; -0.122] | 0.974 [0.605; 1.315] |
| 2026 | M1 | -0.034 [-0.186; +0.106] | não identificável (constante) |
| 2026 | M2 | -0.033 [-0.182; +0.109] | 0.674 [0.318; 1.016] |
| 2026 | M3 | -0.033 [-0.183; +0.109] | 0.971 [0.564; 1.346] |


Intercepto offset ideal0; slope ideal1. Intercepto conjunto com inclinação também está no JSON. Constantes têm slope não identificável (null). Diagnósticos ajustados no período avaliado **não alteram** previsões nem selecionam recalibração pós-hoc. CIs usam2.000 reamostragens de jogos; todos os2.000 fits diagnósticos nos modelos reais foram válidos. Falhas/zero classes em fixtures produzem null e contagem explícita, não substituições falsas. Incerteza não inclui toda seleção/treino/verdade do rótulo. AP é average_precision_score, não área trapezoidal; ROC-AUC é complemento.

A correção de intercepto somente desloca probabilidades e preserva AP/AUC da mesma estrutura; essa igualdade é verificada executavelmente. `same_structure_before_offset_diagnostic` mostra os scores antes do deslocamento. M3 conserva discriminação relativa ao M1, mas isso não atribui efeito ao QB.2024 ainda superestima715,95 contra591, como M1 também superestima717,46; em2025 M1 está até mais perto em soma esperada (578,27 vs583,27), embora M3 melhore proper scores. Calibração futura pode falhar se o nível voltar a mudar.

Grupos com suporte suficiente não melhoram todos: M3 perde LL para M1 em distância1–3 de2024 (n1.782/y56; delta+0,000868) e roof fechado (n2.774/y109; +0,000078); em2026 Q1(n1.496/y45; +0,000452) e atrás9+(n1.525/y43; +0,001719). São diagnósticos, sem alegação de significância múltipla. [Todos os grupos](evidence/groups.csv).

Uso: pesquisa retrospectiva e candidato fixo para2026 W9–13. Não produção, ranking de decisão, culpa, causalidade ou habilidade persistente. Avaliação reservada pendente até maturidade, no mínimo16/12/2026 01:15 UTC (15/12 às22:15 em Fortaleza), se calendário não atrasar. [Guarda e exposição anterior](RESERVED-EVALUATION.md). Não foi aberta a reserva.
