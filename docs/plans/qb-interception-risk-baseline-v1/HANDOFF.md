# Passagem técnica — pesquisa v1

Estado: baseline executada, avaliada e reproduzida localmente. Base reconciliada; ganho contextual modesto na log loss, calibração em nível insuficiente. Não há modelo de produção ou ranking definitivo de QBs. Abrir [REPORT](REPORT.md), [MODEL-CARD](MODEL-CARD.md) e [README/reprodução](README.md).

## Conferir ao retomar

1. HEAD/status da branch `codex/qb-interception-risk-baseline-v1` e hashes versionados em evidence. Base aprovada continua `5b38f04e559bad5fc1b4ef25116cc0afb93293d9`; servidor18111 deve ser preservado. Não usar o PID histórico como autorização para encerrar processo.
2. Store e cópia de recuperação do README: conferir os manifests antes de carregar fontes/modelos. São bytes necessários, não apenas hashes. Restauração usa fontes com paths relativos, sem reescrever os hashes dos originais. Não arquivar a worktree/venv antes de preservar o pacote.
3. Freeze pré-teste: SHA `3add5c6113c91f720ae7dfde759617f114daf66f700b4ce7229c2efa21f3e90a`, C=.1 em ambas. 2025 já foi examinado. Não usá-lo como holdout virgem numa segunda tentativa.
4. Rode o wrapper offline em um destino novo; confirme dataset, splits, busca de desenvolvimento, modelos, previsões e tabelas com verify_reproduction. Os arquivos `build-v1`, `development-v1/v2-singlethread`, figuras anteriores e logs registram tentativas/diagnósticos, não são a versão final recomendada.
5. Leia o funil e os casos de penalidades/no_play antes de alterar população.62IDs são passers, incluindo outras posições; nomes colidem e times mudam. Agregação sempre GSIS. Não reinterpretar o modelo como pressão/clean pocket, inteligência ou decisão.

## Evidência principal

REG2025: n17.358/y553. Constante LL.14254487/Brier.03094721; contexto LL.14120157/Brier.03087377/AP.044762/AUC.584272. Esperado734,47 vs553: superestimação clara. Diferença de LL por jogos IC95% [−.00237655;−.00038150]; Brier [−.00018132;+.00002132]. Profundidade LL.13438312/AUC.702882, pergunta condicional distinta e também mal calibrada em nível. Nenhum reajuste após ver o teste.

2026W1–7: n7.106/y219, esperado282,19; 107jogos/62passers, 32com100+tentativas. FTN pinado tem W8, excluída da aplicação. Não confundir com cache2026 do ETL W1–2. Resultados e ICs são exploratórios/condicionais ao modelo; zero rótulos torna bootstrap empírico degenerado. Tabela completa inclui suportes pequenos sem IC abaixo de3jogos.

## Próxima entrega recomendada

Investigar estabilidade do charting/prevalência e pré-registrar um único experimento de calibração/adaptação temporal usando apenas janelas anteriores.2025 passa a desenvolvimento conhecido; reservar novo bloco ainda não examinado antes de qualquer resultado. Definir critérios de calibração/ganho e tratamento da deriva. Revisar definição FTN e certificar posições com roster como auditoria de apresentação. Não construir novo hub, segunda regressão de INT/sorte, tracking/pressão ou busca ampla por algoritmos.

## Fora de escopo / desconhecido

Precisão/concordância dos rótulos FTN, completude absoluta de jogadas, disponibilidade histórica em tempo real, causalidade e habilidade persistente não comprovadas. Licença não equivale a permissão irrestrita para publicar derivados: conferir NOTICE antes de qualquer distribuição. Não houve banco/ETL operacional/Gemini/serviço pago, merge, push, deploy ou publicação. Cinco expected failures legados continuam intactos. Spec e estado operacional não foram reescritos para promover pesquisa ao produto.
