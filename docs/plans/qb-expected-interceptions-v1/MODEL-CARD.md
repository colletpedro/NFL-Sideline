# Model card — XINT-FTN-B2-v1-fit2025

**Uso autorizado:** pesquisa retrospectiva exploratória sobre interceptações sofridas em relação à classificação de risco FTN do passe. Material para revisão; sem promoção a produção ou integração visual nesta entrega.

**Estimando:** P(interceptação observada no PBP | classificação FTN do passe). O candidato C acrescentou contexto autorizado; não mostrou ganho defensável e não foi escolhido. B2 usa uma taxa por grupo FTN, estimada somente na temporada completa anterior à aplicação. Na versão final 2026: FTN=1, 305/553 = 0,5515370705244123; FTN=0, 75/16805 = 0,0044629574531389465. Cada passe dos dois grupos contribui para o esperado.

**Alvo:** `interception`, binário no PBP. **Entrada:** `is_interception_worthy`, binário FTN. Ausência não vira False. **Identificador:** `XINT-FTN-B2-v1-fit2025`; formato JSON `xint-ftn-reference-v1`; SHA-256 `ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8`. Não é M3, não estima passes interceptáveis esperados, não usa probabilidades do M3 e não multiplica uma previsão M3 por conversão.

**População:** tentativa oficial REG elegível segundo o laboratório: pass_type, pass_attempt, not_deleted, not_sack, not_scramble, not_spike, not_two_point. Overtime incluído; penalidades se a tentativa continua válida. Todos os lançadores entram no ajuste/aplicação, com posição auditada somente para apresentação. GSIS define identidade; equipe(s) e nome não são features. Jogo com lacuna em 2026 é identificado e fica fora por inteiro; outros válidos entram mesmo em semana parcial.

**Tempo e desenho:** desenvolvimento 2022→2023 e 2022–2023→2024; C em [.01,.1,1], escolhido .1; regra de utilidade congelada antes de comparações. Configuração/modelos de avaliação congelados antes de avaliar 2025. Parâmetros/transformações de cada previsão avaliada vêm apenas de temporadas anteriores. B2 de avaliação usa 2024; final usa 2025. O procedimento de refit sobre 2022–2025 seleciona somente a temporada mais recente por definição. Nenhuma calibração usando o período avaliado, sem alteração estatística após o teste.

**Avaliação temporal retrospectiva de 2025:** 17.358 passes / 272 jogos / 380 INT. B2 log loss 0,049853; Brier 0,012188; AP 0,447002; ROC-AUC 0,894012. B0: 0,105335 / 0,021414; B1: 0,050298 / 0,012358; C: 0,050521 / 0,012512. AP implementada por sklearn.average_precision_score, não área trapezoidal. [Métricas completas, incluindo os dois grupos](evidence/evaluation-metrics.csv).

**Calibração material:** total 380 / 364,506 esperadas, O/E 1,043; FTN=1 305 / 311,589, O/E 0,979; FTN=0 75 / 52,917, O/E 1,417. Portanto, calibração global não garante calibração condicional. Não houve correção pós-teste. Bootstrap pareado de jogos: 2.000 réplicas, seed 20261105, log loss/Brier, percentis 95%, condicional às previsões; não cobre parâmetros/charting, dependência entre jogos ou multiplicidade. C−B2 é desfavorável em ambos os escores em 2025. [Detalhes](REPORT.md).

**Aplicação atual:** 121 jogos 2026 W1–8 encerrados até 02/11, adquiridos em 05/11, 7.970 passes / 170 INT / 167,961706 esperadas. O/E global 1,012; FTN=1 1,049; FTN=0 0,870. Exploratória; não prova desempenho futuro. A atualização reaplica o JSON fixo sem fit, em pacote novo e sem ativação do laboratório.

**Limitação central:** FTN é anotação/revisão retrospectiva manual e pode conhecer o desfecho. Não temos evidência de anotação cega ao resultado. Desempenho condicionado a esse rótulo não demonstra previsão independente anterior ao evento, pré-snap ou antes do lançamento. 2025/2026 já tinham estatísticas examinadas; fora do ajuste não significa confirmação intocada.

**Outros limites:** mudança temporal das taxas/composição/charting; histórico com revisões adquiridas posteriormente; fontes revisáveis; duas probabilidades não distinguem contexto dentro dos grupos; calibração FTN=0 inadequada em 2025; zero demonstração de causalidade, habilidade persistente ou responsabilidade individual. Sem uso de tracking, pressão, profundidade, texto revelador de resultado, EPA, drops ou identidade no candidato C. Não inferir responsabilidades de descrições/nomes.

**Por jogador:** soma das probabilidades nos passes elegíveis. Total canônico é contribuição FTN=1 + FTN=0; observado−esperado positivo significa mais INT que a referência. `difference_per_100_passes` é 100×residual/n. Não são interceptações derrubadas, sorte comprovada, culpa ou qualidade de decisão. Não há intervalos de habilidade ou bootstrap individual. Pouco suporte/zero eventos continuam visíveis; não extrapolar taxa de uma tentativa como projeção.

**Bordas:** taxa empírica quando 0<k<n. Se k=0 ou k=n, usar (k+.5)/(n+1); grupo ausente recorre ao global com flag explícita; treino global vazio falha. Sem fallback aplicado nos grupos reais desta entrega. Inferência verifica target, família, esquema e hashes; não carrega pickle/joblib.

**Fontes e atribuição:** FTN Data via nflverse, CC BY-SA 4.0; dados transformados, sem endosso. PBP/calendário/roster conforme [manifest](evidence/sources.json), licença geral nflverse-data CC BY4.0 com escopo subjacente não certificado. [Auditoria](DATA-AUDIT.md), [contrato](RESEARCH-CONTRACT.md), [reprodução](README.md). Nenhuma publicação externa nesta entrega.
