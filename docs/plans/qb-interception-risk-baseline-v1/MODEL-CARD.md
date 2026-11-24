# Model card — pesquisa v1, não produção

Estimador: regressão logística binária L2, C=0.1, solver lbfgs, tolerância1e-9, máximo2.000 iterações; sem class weights/oversampling. C selecionado entre [.01,.1,1,10] pela média por passe da log loss dos folds temporais 2023 e 2024. Configuração congelada no commit `35ac931`, SHA `3add5c6113c91f720ae7dfde759617f114daf66f700b4ce7229c2efa21f3e90a`. Sem ajuste com desempenho de 2025 ou ranking2026. [Contrato](RESEARCH-CONTRACT.md) e [freeze](evidence/frozen-config.json).

Treino final2022–24: 53.996 passes/2.270 positivos (4,204%); teste2025: 17.358/553 (3,186%). Baseline constante usa somente prevalência de treino. Variante com profundidade usa o mesmo alvo/população/protocolo, com pergunta condicional diferente. Sem pós-calibração.

| Validação | Treino | Const. LL | Contexto LL | Profundidade LL | Const. Brier | Contexto Brier | Profundidade Brier |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023 | 2022 | 0.17087087 | 0.16912282 | 0.16037567 | 0.03894669 | 0.03880635 | 0.03802414 |
| 2024 | 2022–23 | 0.14819234 | 0.14680295 | 0.13812333 | 0.03237356 | 0.03227239 | 0.03157546 |


Teste temporal2025 (sem refit após inspeção):

| Modelo | Log loss ↓ | Brier ↓ | PR/AP ↑ | ROC-AUC ↑ | Prob. média | Soma esperada |
| --- | --- | --- | --- | --- | --- | --- |
| Constante | 0.14254487 | 0.03094721 | 0.031859 | 0.500000 | 4.204% | 729.73 |
| Contexto principal | 0.14120157 | 0.03087377 | 0.044762 | 0.584272 | 4.231% | 734.47 |
| + profundidade | 0.13438312 | 0.03040905 | 0.077416 | 0.702882 | 4.245% | 736.85 |


| Variante | Métrica | Delta modelo−constante | IC95% por jogos |
| --- | --- | --- | --- |
| context | brier | -0.00007344 | [-0.00018132; 0.00002132] |
| context | log_loss | -0.00134330 | [-0.00237655; -0.00038150] |
| depth | brier | -0.00053816 | [-0.00082020; -0.00027112] |
| depth | log_loss | -0.00816175 | [-0.01035563; -0.00613806] |


PR-AUC aqui é `sklearn.metrics.average_precision_score` (AP ponderada por incrementos de recall), não integração trapezoidal. Constante AP=prevalência de teste, ROC=.5. Accuracy não é argumento de utilidade. LL/Brier calculados em todos os passes com peso igual; intervalos pareados usam jogos inteiros sorteados com reposição, 2.000 réplicas, seed20261104. Intervalos condicionais aos modelos já treinados; não incluem incerteza da seleção ou verdade do alvo.

Calibração principal:

| Faixa p | n | Positivos | p médio | Taxa observada |
| --- | --- | --- | --- | --- |
| [0.0, 0.02) | 23 | 0 | 1.89% | 0.00% |
| [0.02, 0.03) | 2283 | 47 | 2.74% | 2.06% |
| [0.03, 0.04) | 6576 | 177 | 3.49% | 2.69% |
| [0.04, 0.05) | 4987 | 159 | 4.45% | 3.19% |
| [0.05, 0.075) | 3003 | 139 | 5.77% | 4.63% |
| [0.075, 0.1) | 304 | 15 | 8.34% | 4.93% |
| [0.1, 0.15) | 182 | 16 | 11.74% | 8.79% |
| [0.15, 0.25) | 0 | 0 | — | — |
| [0.25, 1.0) | 0 | 0 | — | — |


Probabilidade média4,231% versus3,186% observada: **superestimação de cerca de181,5 rótulos em 2025**. Nas faixas com maior suporte, 3,49% estimado versus2,69% observado (n6.576) e 4,45% versus3,19% (n4.987). Não está adequadamente calibrado em nível para uso individual. A variante com profundidade também superestima (4,245% média), apesar de discriminar melhor. Brier melhor não resolve isso. Faixa superior da variante tem somente3 passes/1 positivo; não sustenta precisão. Gráfico e CSV preservam todas as faixas, inclusive vazias; barras Wilson são descritivas por passe, sem correção de cluster.

Grupos de teste em `groups_context/depth.json`, com critério descritivo n>=200 e positivos>=10. Contexto perde para constante na terceira descida (n4.497; LL0,16808 vs0,16669) e no quarto período (n4.891; LL0,15624 vs0,15608), embora melhore no total. OT (n101/3positivos) e roof `open` sem suporte suficiente não recebem inferência de estabilidade. Múltiplos grupos não constituem bateria confirmatória corrigida.

Aplicação: refit2022–25 com configuração congelada, 2026W1–7; 7.106 passes/219 positivos, esperado282,19 (3,971% vs3,082%). Uso permitido nesta entrega: exploração condicionada e diagnóstico do modelo. Sem ranking definitivo de habilidade, culpa, decisão ou previsão individual confiável; sem avaliação causal, persistência de talento ou sorte nas INT.

Serialização: JSON transparente com features, medianas, indicadores, médias/escalas, categorias, coeficientes e intercepto, versão `qb-iw-json-logistic-v1`. Sem pickle/joblib e sem carregar modelo externo. Preditor JSON é confrontado com sklearn no treino e aplicação (atol1e-13/rtol1e-12); modelos/hash no freeze. Implementação/schema e versões devem acompanhar o JSON; não é formato universal garantido entre versões. Não carregar JSON arbitrário como artefato confiável de produção.

Limitações: mudança de prevalência/definição do provedor não explicada; período curto; charting subjetivo; dados revisados retrospectivamente; modelos de contexto incompletos; dependência entre passes; identidade de posição não certificada; bootstrap não inclui toda incerteza. [Atribuição/licença](NOTICE.md). Próximo experimento deve tratar deriva e calibração em novo bloco temporal, antes de dar significado comparativo aos resíduos.
