# Cobertura e clareza — relatório da entrega

**Avaliação interna, não publicada. Zero inéditos confirmados.** Este lote amplia a inspeção local para 11 jogos fora dos seis revisados, mas todos têm geração prévia registrada em cache. Não é avaliação independente nem evidência sobre o Gemini.

## Implementação e ordem de execução

- Seletor `local-descriptive-rules` **2.0.0** e contrato de claims **5** inalterados; entrada tática **3**. Renderer **controlled-claims-v5.0.1**; harness **coverage-harness-1.0.0**.
- Correção limitada à redação: ataque e defesa adversária identificados no veredito; semanas com sinais distintos descritas sem inferir trajetória, instabilidade ou magnitude. Zeros permanecem atribuídos ao lado correto. Não houve mudança de seleção, classificação, recortes ou agregação.
- Em 10/10 regressões conhecidas/sintéticas, selection.json permaneceu semanticamente idêntico à versão 2 preservada; vantagem_tatica e alerta_vermelho ficaram idênticos. Teste Java acrescentado verifica atribuição em ambos os sentidos, zeros, oposição e variação. Contratos v3/v4 continuam aceitos sob suas regras anteriores.
- Protocolo e complemento de calendário foram registrados antes da primeira geração dos 11 casos adicionais. O inventário lê apenas entrada e metadados de uso; respostas antigas desses 11 não foram usadas para ajustar o renderer.
- Congelamento em 2026-10-01T20:18:40.434543+00:00: **138 arquivos** (fontes, testes, docs, protocolo, manifesto, entradas, calendário, harness e JAR). Verificações antes/depois/final: nenhuma divergência. Nenhuma correção após exposição do lote.
- JAR executado: `core-api/target/core-api-0.1.0.jar`, SHA-256 `30c4880142f393d5314022ad5bb5ee43495757957388b1a7f805d053af2dda1c`.

## Inventário, seleção e novidade

Foram inventariados **263 arquivos**: 65 contextos diretos v3, 192 JSONs de outras estruturas e 6 Parquet brutos não consumíveis diretamente. Os 65 contextos reduziram-se a **21 conteúdos/jogos únicos**, com **44 cópias** deduplicadas. Os seis Parquet foram registrados; não se criaram novas métricas a partir de PBP. Os calendários existentes foram usados exclusivamente para auditoria de lacunas.

Foi executado o universo elegível único, em ordem determinística, sem amostragem (semente não aplicável). Não houve entradas rejeitadas pelo motor (0/21). Os 198 arquivos não contexto não são falhas de geração. Origem, hashes brutos/normalizados, versões duplicadas e histórico verificável estão no manifesto.

| Grupo | Casos | Observação |
|---|---:|---|
| Inéditos confirmados | 0 | Sem cadeia local afirmativa de reserva sem uso |
| Seis regressões conhecidas | 6 | Inclui SEA–WAS e MIN–TB |
| Adicionais com uso anterior comprovado | 11 | Registros de cache preservados, sem ler seus textos para ajustes |
| Sintéticos conhecidos | 4 | Separados dos jogos reais |
| Histórico desconhecido | 0 | Categoria prevista, sem casos neste universo |

Os 17 reais incluem 16 jogos da semana 3 de 2026 (duas semanas por time) e um da semana 8 de 2025 (três semanas desencontradas). Só um caso de meio de temporada; nenhum real com uma única semana, ausência total, apenas histórico, zero observado ou métricas parcialmente ausentes. Não foram produzidos casos artificiais para preencher estratos reais. As fixtures e testes cobrem alguns desses limites sem representar avaliação independente.

## Execução e cobertura

| Grupo | Sucesso / entradas | Pareáveis / encontros | Adequados / encontros | Oportunidades / encontros | Jogos com oportunidade |
|---|---:|---:|---:|---:|---:|
| Seis conhecidos | 6/6 | 36/36 | 30/36 | 5/36 | 2/6 |
| 11 adicionais com uso prévio | 11/11 | 66/66 | 66/66 | 3/66 | 3/11 |
| Sintéticos | 4/4 | 6/24 | 6/24 | 4/24 | 2/4 |

Total **21/21 válidos**, falhas de validação **0/21**, falhas de processo/harness **0/21**, rejeições de entrada **0/21**, resultados direcionais **0/21**. Todos NONE/INCONCLUSIVE, que expressam ausência de estimativa de vencedor, não equilíbrio nem abstenção por falta de dados. Não foram substituídos casos com resultado desfavorável.

Nos 11 adicionais, **8/11 não tiveram oportunidade apesar de 66/66 encontros adequados**: faltou convergência estritamente positiva nos sinais observados. Os outros 3 jogos tiveram uma oportunidade cada (passe de BUF contra LAC, LV contra NO e PHI contra CHI). Não comparar valores ofensivos/defensivos por subtração.

Nos 17 reais, há 12 sem oportunidade: 11 por padrão de sinais em pares adequados e CHI–BAL com **sinais sem convergência e limitações de cobertura coexistentes**. Nesse último não há sequer par positivo observado: seria incorreto atribuir o resultado somente às lacunas.

Limitações reais, denominador **102 encontros** (categorias coexistem): ausência de denominadores 68/102; janela de até duas observações 96/102; variação de valores semanais 102/102; lacunas identificáveis, recorte não recente completo e semanas diferentes, 6/102 cada. Variação de valores não equivale necessariamente a presença de sinais opostos. Cobertura adequada não é suficiência estatística.

Calendários locais completos confirmam **1/17 casos reais afetado por bye**: CHI na semana 5 e BAL na 7 de 2025. Lacunas reais restantes sem causa conhecida: **0/17**. O contexto do motor não recebe esse sidecar; o texto continua corretamente dizendo que a causa não está informada naquele contexto. Isso é uma diferença entre auditoria de calendário e dados disponíveis ao seletor, não uma regra editorial nova.

## Verificações textuais e indicadores exploratórios

No lote todo, 58/58 encontros principais passaram nas sondagens de números atribuídos, recortes e agregação; 82/82 claims MATCHUP tiveram par ataque/defesa e fundamento identificados no veredito; 58/58 limitações internas ficaram vinculadas e presentes. As sondagens de sinais/zero são condicionais ao padrão de cada claim, não 82 testes de oposição distintos. O validador comum verificou relações, evidências e 26 agrupamentos editoriais. Nenhuma exceção específica para o seletor.

Nos 11 adicionais: 35/35 principais e 50/50 MATCHUP passaram nessas sondagens; 16 panoramas foram agrupados com justificativa validada, preservando candidatos/evidências internamente. Isso demonstra conformidade mecânica, não correção editorial completa.

Comprimento por bloco nos **11 adicionais**; p90 nearest-rank. Palavras são sequências alfanuméricas Unicode; caracteres incluem espaços. Distribuições completas por coorte em metrics.json.

| Bloco | Palavras mediana / p90 / máximo | Caracteres mediana / p90 / máximo |
|---|---:|---:|
| fator_chave | 42 / 52 / 62 | 233 / 267 / 333 |
| vantagem_tatica | 204 / 224 / 227 | 1135 / 1198 / 1219 |
| alerta_vermelho | 58 / 170 / 182 | 338 / 1016 / 1074 |
| veredito | 186 / 210 / 219 | 1007 / 1141 / 1196 |
| total | 459 / 523 / 523 | 2638 / 2892 / 2903 |

Nos 17 reais: total mediano **454 palavras / 2.575 caracteres**, p90 **523 / 2.892**, máximo **523 / 2.903**. Comprimento não é nota de qualidade.

Repetição entre blocos: nos 11 adicionais, 0/66 pares integralmente iguais (exatos ou normalizados); 3/66 pares compartilham sentença normalizada de pelo menos cinco palavras. Nos 17 reais são 0/102 e 4/102, respectivamente. Os avisos compartilhados podem ser corretos, embora repetitivos. O método não detecta toda redundância semântica.

## Problemas encontrados e melhorias opcionais

**Defeitos de execução/validação do motor:** nenhum observado neste lote. A ausência de falhas não comprova qualidade editorial.

**Limitação concreta de clareza registrada após congelamento:** em LV–NO, o alerta contém `faixa semanal de 0 < EPA < 0,0005 a +0,116 EPA`. Os sinais e o limite de formatação estão preservados, mas uma desigualdade como extremidade de faixa é pouco fluida. Não foi corrigida nesta rodada; qualquer revisão futura deve reconhecer LV–NO como caso exposto.

**Falha de verificação visual, não do motor:** o servidor Python não conseguiu abrir 127.0.0.1 no sandbox e o navegador rejeitou file:// por política de URL. Não se contornou o bloqueio. Não há alegação de página inspecionada em navegador, screenshot ou clique real em details. Foram testados escape HTML, CSP sem conexões, ausência de assets externos, 21 cartões/quatro blocos, marcação de details e lógica JavaScript de 19 opções de filtro e filtros combinados. Layout visual e interação nativa de expansão ainda dependem de abertura local.

**Durante desenvolvimento do harness conhecido:** uma sondagem exigia o nome do ataque numa limitação que só dizia respeito à defesa; isso gerou falso positivo em MIN–TB. A sondagem foi corrigida antes do congelamento, segundo as dimensões da claim. Nenhuma saída adicional foi aberta para esse ajuste. Não houve falhas ou correções de harness após congelar.

**Melhorias opcionais futuras:** reduzir repetição de nomes e avisos sem perder atribuição; compactar alertas de 170–182 palavras com restrições distintas; ampliar diversidade quando existirem contextos novos rastreáveis. Nenhuma foi usada para retunar esta rodada.

## Recomendação

Iniciar **integração local restrita** é tecnicamente viável: interface, validação, auditoria, geração e compatibilidade passaram nos checks. Não recomendo promoção pública ou afirmação de qualidade comprovada. Antes de tratar a apresentação como pronta, verificar a página em navegador e revisar, numa entrega separada, a composição textual de faixas com desigualdade. O lote atual não fornece estimativa independente de generalização. Integração/publicação não foram executadas nesta entrega.

## Artefatos e reprodução

- [Protocolo](PROTOCOL.md), [manifesto](manifest.json), [congelamento](freeze.json), [calendário auditável](calendar-evidence.json).
- [Métricas completas](metrics.json), [HTML local](inspection.html), [comparação de clareza v2 → 5.0.1](clarity-comparison.json).
- [Resultados por caso](batch-01/execution.json), [verificação antes](batch-01/check-before.json), [depois](batch-01/check-after.json), [integridade final](final-verification.json).
- [Gate Java 21](java21-clean-verify.log): 107 testes, zero falhas/erros/skips. [Harness](harness-final-tests.log): 11 testes. [Calendário](calendar-tests.log): 3 testes. [Página, checagem de fonte](page-verification.json). `git diff --check` passou nesta entrega.
- [Comandos completos](../../docs/coverage-clarity-evaluation.md): geração, métricas, congelamento, HTML e abertura local. Destinos novos, sem carregar .env.

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
python3 scripts/evaluate_coverage.py check editorial/coverage-clarity-v1
python3 scripts/evaluate_coverage.py run editorial/coverage-clarity-v1 --output editorial/coverage-clarity-v1/reproduction-01
python3 scripts/evaluate_coverage.py metrics editorial/coverage-clarity-v1 --run editorial/coverage-clarity-v1/reproduction-01 --output editorial/coverage-clarity-v1/reproduction-01-metrics.json
python3 scripts/evaluate_coverage.py html editorial/coverage-clarity-v1 --metrics editorial/coverage-clarity-v1/reproduction-01-metrics.json --output editorial/coverage-clarity-v1/reproduction-01.html
python3 scripts/evaluate_coverage.py check editorial/coverage-clarity-v1
open editorial/coverage-clarity-v1/reproduction-01.html
```

## Preservação

394 arquivos protegidos foram comparados com os hashes anteriores: frontend e dados públicos, artefatos v1/v2, avaliação Gemini, aprovações e código semântico do motor. Nenhuma divergência. Mudanças preexistentes no workspace foram preservadas. Sem chamadas de geração externas, modelos locais, banco remoto, downloads, uso de tentativas Gemini, publicação, deploy, push ou commit. Apenas arquivos locais foram lidos/escritos; o browser local não chegou a carregar a página.

## Exemplo de atribuição — regressão conhecida MIN–TB

Antes (5.0.0): `TB — passe: EPA ofensivo e permitido negativos.`

Agora (5.0.1): `No recorte de passe do ataque de TB contra a defesa de MIN, o ataque de TB apresentou EPA negativo e a defesa de MIN permitiu EPA negativo nas semanas observadas.`

Os quatro blocos completos de cada caso estão na página e em `batch-01/<gameId>/rendered.json`; claims, decisões e evidências ficam no mesmo diretório.


## Complemento de integridade documental

O campo `protocolSha256` interno ao manifesto aponta à revisão vigente no inventário, anterior ao
complemento pré-congelamento de calendário. `freeze.json` registra separadamente o hash do protocolo
final usado na execução e o do manifesto. Para eliminar ambiguidade, [protocol-lineage.json](protocol-lineage.json)
associa ambos; [PROTOCOL.inventory.md](PROTOCOL.inventory.md) conserva o prefixo original, recuperado e
verificado byte a byte contra o hash já registrado. Não se alteraram manifesto, protocolo executado,
fontes ou saídas após congelar. É uma limitação de apresentação da linhagem no harness, sem efeito na
seleção ou nos resultados; uma versão futura deve distinguir esses dois hashes por nome.

O manifesto de aprovações `editorial/analysis-selections.json` também foi comparado, nesta execução,
com o conteúdo versionado em HEAD: [approval-integrity.json](approval-integrity.json), sem diferença.
Essa checagem adicional não usa resultados antigos como validação da entrega atual.
