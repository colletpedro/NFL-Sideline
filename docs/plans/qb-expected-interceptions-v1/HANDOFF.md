# Passagem — revisão dos resultados e integração visual posterior

Pesquisa concluída nesta branch isolada. B2 é a primeira referência de INT esperadas condicionadas ao charting FTN; C foi implementado e avaliado, sem ganho convincente. Não houve alteração no laboratório aprovado em `http://127.0.0.1:18124/?view=risk-lab&season=2026`, em seu pacote ativo, M3, fontes ou servidor. O principal conserva seu estado preexistente. Sem merge, push, deploy ou publicação.

## Material pronto para consumo

Store `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1`.

- `application-complete/consumer/index.json`: versão, modelo/hash, cobertura por jogo, 66 jogadores, decomposição/observado/residual/unidades e limites.
- `application-complete/consumer/players/{gsis_id}.json`: todos os passes e descrições/referências PBP/FTN para inspeção; probabilidade `p_interception_given_ftn`, sem campos ambíguos `expected` ou aliases M3.
- `application-complete/players.csv`, `pass_predictions.parquet`, `cases/`, `metrics.csv`, `calibration.csv`, `integrity.json`: pacote completo auditável.
- `final/model.json` / `fixed.json`: modelo transparente e hash fixo, sem retreino na atualização.
- [Contrato de consumo versionado](../../../research/qb_expected_interceptions/consumer-contract.json), [índice para revisão](evidence/consumer-index.json), [manifest de todos os artefatos](evidence/package-manifest.json), [figuras exportáveis](figures/README.md), [reprodução](README.md).

O pacote não está conectado a rota, ponteiro ou build aprovado. A revisão de resultados vem antes da integração visual. Não copiar os arquivos para snapshots públicos ou substituir o pacote do laboratório.

## Próxima entrega recomendada

Após revisar os resultados e os limites, integrar em outra worktree uma leitura explícita de **“Interceptações sofridas em relação ao risco dos passes”**. Apresentar separadamente o M3 de passes interceptáveis e a referência B2 de INT efetivas. Preservar todos os identificadores e unidades: “INT esperadas dado charting FTN”; rótulo retrospectivo visível perto do gráfico e do detalhe, sem sugestão de previsão pré-snap.

Usar X=INT esperadas, Y=INT observadas, diagonal identidade, suporte por passes/jogos e cobertura atual. Detalhe deve decompor FTN=1/FTN=0, permitir inspecionar todas as jogadas e mostrar lacunas por jogo. Separar contagens e taxas. Lançadores ocasionais e pouco suporte precisam de acesso explícito; sem intervalos de habilidade, ordenação de azar/culpa ou linguagem de passes bons/ruins.

Mostrar o diagnóstico: em 2025, B2 subestimou FTN=0 (75 observadas / 52,92 esperadas), mesmo com total próximo. A aplicação atual 2026 tem O/E 1,012 global, 1,049 em FTN=1 e 0,870 em FTN=0; isso não elimina a limitação histórica. Contexto adicional não merece destaque como modelo superior nesta versão.

Manter aquisição/aplicação manual separada de ativação visual. `update.py` entrega outro pacote com modelo fixo e revisão; não retreina nem atualiza ponteiro. Usar o comando de atualização da [README](README.md), aceitar jogos utilizáveis de semanas parciais e seguir acompanhamento contínuo. Não existe espera até dezembro ou nova janela obrigatória para utilizar estes resultados de pesquisa.

## Evidência e ocorrências preservadas

Contrato inicial `4c705fb`; freeze/seleção antes de 2025 `decbc33`. A saída `application/` foi interrompida somente ao gravar casos sem diretório; foi preservada, e `application-complete/` é a entrega válida. [Correção por hash](evidence/output-fix.json), sem alteração de procedimentos estatísticos. Reprodução conserva os dois freezes e comprova todos os modelos/seleção/resultados, com 156 arquivos científicos idênticos.

Testes em processos separados: 33 novos e 59 preservados passaram; a tentativa conjunta falhou em collection por módulos legados homônimos, sem alterar o legado. O resultado dessa tentativa fica em `evidence/tests.log`. Não foi repetida auditoria visual porque a interface não mudou. [Isolamento](evidence/isolation.json), [recuperação verificada](evidence/recovery.json), [relatório](REPORT.md).
