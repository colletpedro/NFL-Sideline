# Revisão e integração E4 — 07/10/2026

Aceite técnico da apresentação e auditoria interna. **Compreensão humana permanece pendente**, com zero participantes, respostas e tempos. O relatório E4 não demonstra aumento de velocidade de leitura: o cartão medido ficou cerca de 13% menor, mas o texto visível cresceu ligeiramente. Não converter essa medida em comprovação de usabilidade.

Os quatro commits E4 foram incorporados por fast-forward, preservando protocolo e diagnóstico anteriores aos ajustes, em `codex/visual-integration-e4`, sobre `793ac7b`. A frente termina em `c238d36`; `main` permanece na base E1. Não houve push ou publicação.

A revisão examinou os componentes, navegação/foco, períodos, restrições, tabelas, estilos e testes. O cálculo dos gráficos, seletor, claims, renderer, projetor, contrato congelado, snapshots e migrations não mudaram. As seis capturas versionadas tiveram hashes conferidos; o desktop selecionado foi inspecionado. A ampliação a 200% reportada por E4 é de texto por CSS em viewport fixo, não zoom nativo ou certificação de acessibilidade.

Na integração passaram novamente 125 testes frontend (120 comuns, cinco falhas esperadas legadas), lint, build, 12 testes Python do contrato, 20 fixtures válidas e 15 inválidas rejeitadas. Java não mudou; os 127 testes `clean verify` são evidência da frente E4, não nova execução nesta revisão. [Registro estruturado](integration-verification.json).

## Correção do simulador de falhas

O harness E4 descartava todos os headers ao encaminhar pedidos para o Java, inclusive `Origin`. Isso poderia tornar aceitável no harness uma requisição que a API direta recusaria. A integração passou a recusar `Origin`, Host diferente de `127.0.0.1:18081`, corpo não vazio, múltiplos Content-Length e Transfer-Encoding antes de encaminhar. O proxy Vite legítimo continua funcionando, pois sua checagem precede a remoção de Origin.

A correção foi exercitada por HTTP real em processos e armazenamento próprios: catálogo, quatro pedidos rejeitados sem criar tentativas, POST normal e documento visual reconciliado com E2, mais um POST salvo cuja resposta foi descartada e recuperada por histórico. O log confirmou somente os dois POSTs válidos chegando ao backend. Os dois servidores temporários foram encerrados. Saídas completas ficam somente em `/tmp/nfl-e4-orchestrator-20261007`; o registro versionado identifica o escopo e hash dessa evidência.

## Próxima entrega

Iniciar **E5a: contrato de métricas e recortes**, antes de implementar ETL ou migration. Inventariar a definição vigente e fechar população de jogadas, somas/contagens e denominadores próprios de passe/corrida, agregação de temporada e últimas semanas, cobertura/amostra, fases, exclusões e corte temporal. Identificar requisitos suportáveis pelos dados locais e lacunas reais; não criar volumes a partir de taxas nem média de temporada a partir de médias semanais simples.

A rodada humana preparada pode avançar em paralelo e deve informar as decisões de BASIC/FULL e apresentação pública. Não bloqueia o estudo do contrato E5. A proposta de vocabulário visual 1.1.0 fica registrada, sem aprovação ou implementação automática. Fases de playoffs e as cinco regressões públicas continuam pendentes; nenhuma delas foi silenciosamente corrigida por E4.

Os 36 arquivos históricos não rastreados permanecem preservados fora do commit.
