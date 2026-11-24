# Figuras de pesquisa — INT observadas e esperadas

PNG e SVG exportáveis; scripts e dados fixos, sem alteração de interface. FTN Data via nflverse, CC BY-SA 4.0; dados transformados, sem endosso. A anotação FTN pode conhecer o resultado; não há evidência de cegueira ao desfecho. Nenhuma figura mede causalidade, sorte comprovada ou qualidade de decisão.

| Figura | Conteúdo | Suporte |
| --- | --- | --- |
| [Calibração PNG](calibration_global_and_ftn.png) / [SVG](calibration_global_and_ftn.svg) | Global, FTN=1 e FTN=0; 2025 e aplicação 2026 W1–8 | [Bins completos, eventos e n](calibration_support.csv), inclusive vazios |
| [Desempenho PNG](performance_vs_references_2025.png) / [SVG](performance_vs_references_2025.svg) | Log loss/Brier contra B0/B1/B2/C e diferenças pareadas de jogos | [Todas as métricas/grupos](performance_2025.csv), [bootstrap](../evidence/evaluation-bootstrap.json) |
| [QBs PNG](qb_observed_vs_expected_2026.png) / [SVG](qb_observed_vs_expected_2026.svg) | X=INT esperadas; Y=INT sofridas; nomes e passes/jogos; diagonal identidade | [Todos os jogadores, contagens e taxas](all_players_2026.csv) |
| [Pouco suporte PNG](small_support_all_positions_2026.png) / [SVG](small_support_all_positions_2026.svg) | Painel complementar com todos os 33 lançadores abaixo de 100 passes/outras posições | Nenhuma amostra pequena ocultada; suporte explícito |
| [Decomposição PNG](expected_decomposition_2026.png) / [SVG](expected_decomposition_2026.svg) | Contribuição FTN=1 + FTN=0 para cada lançador; contagens | [Tabela de composição](decomposition_support.csv) |

O corte de 100 passes no gráfico principal é de legibilidade, sem alterar a população/modelo/tabela. Os 66 lançadores estão no painel de decomposição e no CSV. Acima da diagonal há mais INT que a estimativa; abaixo, menos. A linha é identidade matemática, sem regressão ajustada aos jogadores. As taxas por 100 ficam em colunas separadas das contagens.

Bins de calibração são fixos no contrato; n≥200 e eventos≥10 marca suporte descritivo, sem certificação. B2 tem somente duas probabilidades e por isso cada grupo produz um ponto. Interpretação e limitações no [relatório](../REPORT.md). [Regerar/reproduzir](../README.md).
