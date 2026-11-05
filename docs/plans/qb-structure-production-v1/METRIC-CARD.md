# Cartão da métrica · produção situacional QB 1.0.0

**Nome de apresentação:** produção em progressão registrada e improvisação identificada. **Status:** experimental, descritiva e pronta para revisão de integração; não ativada. Não é medida causal de dependência do sistema, qualidade de decisão, pressão ou habilidade de improvisação.

## População e unidades

REG 2023–2025 separadamente e 2026 W1–8 disponível até 02/11, conforme cobertura por jogo. Auditoria 2022 separada. A unidade é o dropback elegível com chave jogo/jogada. Dados PBP nflverse + charting FTN Data via nflverse; rosters semanais para identidade. Fontes e revisões são pinadas por SHA-256.

EPA é o campo **`epa` da jogada PBP**, em pontos esperados adicionados pelo ataque, conforme dicionário oficial. Não usamos `qb_epa`, WPA ou proxy. Inclui contribuição do ataque, recebedores/YAC, contexto e penalidades válidas; não isola a contribuição causal do QB. Não certificamos a versão exata do modelo de EPA subjacente além dos bytes da fonte adquirida.

## Cálculo

Para categoria ou grupo G, `n` é o número de eventos; `n_epa` é o número com EPA finito; `sum_epa = soma(epa válido)`; `mean_epa = sum_epa/n_epa`. Sem EPA válido, soma/média são indisponíveis, não zero. Com zero oportunidades, status `unavailable_no_opportunities`; com eventos e EPA ausente, `unavailable_epa`.

Diferença principal `D = mean_epa(A) − mean_epa(B)`, A=passes 0/1/2/CHK sem throwaway, B=passes SD sem throwaway + scrambles QB verificados. S1 adiciona descartes a B, S2 adiciona descartes e sacks, S3 usa só passes SD. A e universo total não mudam entre definições. Sinal positivo significa maior produção observada em A; mostrar A e B junto de D.

`pct_all = 100*n_G/n_dropbacks` usa todos os elegíveis do jogador. `pct_classifiable = 100*n_G/(n_dropbacks−n_indeterminate)` usa denominador explicitamente diferente, incluindo sacks/throwaways mas excluindo DES e outros residuais. O residual não recebe percentual sobre classificáveis. A frequência principal é percentual sobre todos os dropbacks, não sobre A+B. Indeterminados não são escondidos por troca de denominador.

Categorias têm n, n_epa, soma, média, jogos e composição. Agregados por GSIS/temporada conservam todas as posições, equipes e suporte, inclusive categorias vazias. `dropback_games` é volume de jogos do universo; `games` na categoria é jogos dessa categoria; `comparison_games` é jogos com pelo menos uma jogada de A/B. Não confundir esses campos.

## Referência e suporte

Referência da liga: todos os **QB auditados** com eventos válidos na condição/temporada, média ponderada por n_epa, incluindo pouco suporte individual. Outras posições aparecem nas tabelas e cobertura, mas não na referência QB. O scatter usa referências de todos os QB, não só dos 15 exibidos.

Corte de legibilidade principal: A n_epa≥100, B n_epa≥25 e ≥5 jogos A/B; flag `legible`. Valores fora dele permanecem como `low_support` ou indisponíveis. Cada sensibilidade registra seu próprio suporte; figuras de sensibilidade conservam a coorte principal e exibem os n B de cada versão. Um corte de volume não garante estabilidade, ausência de viés ou robustez inferencial.

Sem intervalos nesta versão. Estabilidade histórica é correlação descritiva por pares de temporadas adjacentes com corte equivalente nos dois anos; não é teste de habilidade persistente. Diagnóstico dos cinco maiores |EPA| conserva a métrica principal intacta; `difference_without_top5_each` é uma conta de influência que altera o universo, sem recomendação de uso como métrica corrigida.

## Limites, versões e atualização

Anotação FTN retrospectiva/revisável; códigos em sacks/corridas não significam passe lançado. DES é conhecido como desenho sem progressão, separado no residual. Pocket, blitzers e qb_hit não identificam toda pressão ou improvisação. Contextos, adversários, proteção, recebedores e alternativas não observadas impedem atribuição individual da diferença.

`fixed.json` congela hashes do classificador, agrupador, helpers e contrato. Atualização verifica esses hashes **antes** de adquirir. Diretórios novos e sem sobrescrita, fontes próprias, revisão por chave/campo, manifesto de saída e reconciliação independente. Sem retreino e sem ponteiro ativo. Nova temporada requer decisão explícita de contrato de fonte; esta primeira atualização cobre 2026.

FTN Data via nflverse, dados transformados CC BY-SA 4.0; demais fontes conforme licença nflverse pinada. Sem endosso ou publicação externa. [Contrato](RESEARCH-CONTRACT.md) · [auditoria](DATA-AUDIT.md) · [relatório](REPORT.md) · [reprodução](README.md).
