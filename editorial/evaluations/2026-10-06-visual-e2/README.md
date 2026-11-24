# E2 — projeção visual local

Esta saída contém 17 documentos gerados offline pelo Java a partir de contextos versionados conhecidos: os 16 de `editorial/evaluations/2026-09-26/contexts/` e `editorial/coverage-clarity-v1/batch-01/2025_08_CHI_BAL/context.json`. Não é holdout editorial nem publicação. Nenhum snapshot público ou baseline foi alterado. `manifest.json` registra hash do arquivo de origem, contexto canônico, resultado local e bytes de cada documento.

Cada arquivo de `documents/` é o `insights.json` real produzido pelo modo `editorial-local`, apto a ser entregue como `document` pelo GET da tentativa correspondente. São objetos do schema `visual-analysis-1.0.0`, com `source.kind = VALIDATED_LOCAL_RESULT`; não há UUID nem timestamp de tentativa no documento.

## Exemplos observados nestes contextos

| Caso | Documento e ID |
| --- | --- |
| Encontro comparável | `2025_08_CHI_BAL.json` — `CHI:PASS` |
| Panorama geral representado | `2026_03_ARI_SF.json` — `ARI:GENERAL` |
| Relação adicional | `2026_03_LAC_BUF.json` — `f:BUF:RUSH` |
| Convergência positiva | `2026_03_BAL_DAL.json` — `f:BAL:PASS` |
| Ataque não demonstrado | `2026_03_ATL_GB.json` — `f:ATL:PASS` |
| Ambos negativos | `2025_08_CHI_BAL.json` — `f:BAL:GENERAL` |
| Ataque e defesa favoráveis | `2026_03_HOU_IND.json` — `f:IND:RUSH` |
| Variação semanal de sinal | `2025_08_CHI_BAL.json` — `f:CHI:PASS` |
| Cobertura limitada | `2025_08_CHI_BAL.json` — `r:CHI:PASS` |
| Semanas desiguais | `2025_08_CHI_BAL.json` — `r:global` |
| Amostra curta | `2026_03_ARI_SF.json` — `r:global` |
| Variação de sinal | `2026_03_ARI_SF.json` — `r:ARI:PASS` |
| Denominador indisponível | `2025_08_CHI_BAL.json` — `r:denominator:CHI:PASS` |
| Corte temporal não verificado | `2025_08_CHI_BAL.json` — `r:temporal` |
| Sem ajuste por adversário | `2025_08_CHI_BAL.json` — `r:adjustment` |

`UNAVAILABLE`, `HISTORICAL_ONLY`, `NO_DATA`, sinais zero/minúsculos, empate de destaques e `INDEPENDENT_OPPORTUNITY` não ocorrem nesses 17 contextos. São cobertos por casos unitários sintéticos em `VisualAnalysisProjectorTest`; esses casos não foram tratados como resultados reais nem incluídos nesta avaliação.

## Verificação

Com Java 21, `mvn -f core-api/pom.xml -o clean verify` passou com 127 testes, incluindo paridade dos 21 casos históricos de texto/claims, reconciliação dos 17 contextos versionados, mutações e leitura v3/v4. `python3 scripts/verify_visual_contract.py` passou: 20 fixtures válidas e 15 inválidas rejeitadas. Os 17 documentos desta saída também foram aceitos individualmente por `verify_visual_contract.validate`; seus valores, times, métricas, temporadas, semanas e origens foram comparados às observações dos `context.json` gerados na mesma execução. Esses 17 são regressões conhecidas, não avaliação independente.

HTTP real foi exercitado com um servidor Java em `127.0.0.1:63318` e diretórios exclusivos em `/tmp`: POST 201; GET textual 200; GET `/insights` 200 com seis encontros e hash de 64 caracteres; tentativa inexistente 404; Origin rejeitado 400; POST na rota de insights 405. Em outra porta/diretório, um artefato v3 íntegro foi recuperado após reinício: GET textual 200, GET visual 409 `VISUAL_DOCUMENT_NOT_AVAILABLE`, Host/Origin/query/body inválidos 400 e os seis arquivos anteriores byte a byte intactos. A recuperação também passou com uma cópia em `/tmp` de um artefato v3 histórico real de `editorial/local-interface-v1/runtime/results/`: GET textual e histórico 200, GET visual 409, seis hashes originais inalterados. A primeira tentativa de bind no sandbox retornou `SocketException`; os testes passaram com permissão local de socket. Os servidores foram encerrados. Nenhum Spring, banco, Gemini ou `.env` participou.

## Lacuna do contrato congelado

Um contexto v3 válido com `game.phase = WC`, temporada 2026, semana 20, times BAL/DAL e `evidence: []` é aceito pela validação textual local, mas o schema visual v1 permite apenas `REG` e `POST`. E2 preserva a geração textual em artefato v3, sem `insights.json`, e a consulta visual responde 409 `VISUAL_DOCUMENT_NOT_AVAILABLE`. O mesmo vale para `DIV`, `CON` e `SB`. A proposta à integração é versionar o contrato visual e ampliar `game.phase` para essas quatro fases, com suporte explícito no cliente; E2 não alterou o schema congelado nem criou valor privado no payload.
