# Estado consolidado — 07/10/2026

Esta página sucede os estados operacionais descritos em [avaliação de cobertura](../editorial/coverage-clarity-v1/REPORT.md), [integração local](../editorial/local-integration-v1/REPORT.md) e [validação operacional](../editorial/operational-validation-v1/REPORT.md). Esses relatórios são registros históricos das respectivas entregas; suas pendências e contagens não são afirmações sobre o estado atual.

## Implementado e verificado

- Frontend: calendário e detalhe com linguagem de mercado sem favorito, confiança ou vantagem de modelo inventados. Production permanece um build estático que lê snapshots JSON; a API editorial local ainda não está conectada à interface principal.
- Caminho Gemini: prompt/cache com claims v3 e renderização Java dos quatro textos. Gemini é necessário apenas ao comando de geração Gemini; testes, exportação de snapshots e motor local por regras não o exigem.
- Motor local descritivo: seletor `local-descriptive-rules` 2.0.0, entrada 3, claims v5, renderer `controlled-claims-v5.0.2`, `LocalGenerationService` 1.1.0, CLI e servidor HTTP de loopback. Novas tentativas compatíveis com o contrato visual usam artefato interno v4; o leitor preserva v3. O motor não prevê vencedor, não aprova análises e não publica.
- Os relatórios da última validação registram 116 testes Java e 12 Python aprovados, 75 requisições HTTP reais com CLI/API e persistência após reinício nos 21 casos conhecidos, e inspeção visual em 1440 × 1000 e 390 × 844 px. A apresentação de faixas próximas de zero foi verificada nessa inspeção. São evidências dos casos conhecidos, não avaliação editorial independente.
- Nesta organização, o gate local reconstruiu Java 21 com 116 testes, executou 43 testes frontend, lint e build, e descobriu 15 testes Python nos scripts. A diferença de 12 para 15 corresponde à inclusão dos três testes de calendário na descoberta ampla; não altera o registro histórico.
- O manifesto editorial versionado contém 69 seleções aprovadas de entregas anteriores. O trabalho local por regras não modificou o manifesto, os snapshots públicos ou aprovações.

- Entrega da interface: 118 testes Java, 48 frontend, lint/build e 21 verificações HTTP reais do proxy aprovados; geração, recuperação após reinício e apresentação desktop/mobile verificadas. Fonte: [relatório da interface](../editorial/local-interface-v1/REPORT.md).

## Limites e próximo passo

- A política BASIC/FULL para o **novo motor local** ainda precisa ser definida; as regras existentes do fluxo Gemini/publicação não a definem automaticamente.
- Registrar `asOfDate` e filtrar semanas anteriores não reconstrói todo o conhecimento disponível na data: fontes, correções, disponibilidade e contexto histórico podem ter mudado.
- Os casos conhecidos servem a regressão mecânica e operacional. Não houve avaliação editorial independente, prova de generalização ou nova publicação dessas entregas.
- A [interface local de desenvolvimento](local-editorial-ui.md) está implementada em uma entrada Vite separada, com catálogo, geração explícita e recuperação de tentativas. Proxy restrito em loopback; Production segue estática. A API continua recusando Origin e sem CORS.
- E4 de apresentação e auditoria interna incorporada à branch local `codex/visual-integration-e4`, a partir de `c238d36` da frente E4: leitura rápida com papéis/períodos, limitação antes dos pontos, acesso ao histórico, foco/tabelas e ampliação de texto a 200%. Verificados 125 testes frontend (cinco falhas esperadas preservadas), 127 Java offline, contrato/lint/build, HTTP real e falhas de transporte. **Compreensão humana e amostra independente permanecem pendentes**; próximo passo: rodada curta preparada e contrato de métricas/recortes E5 antes de E6/E7. [Relatório E4](plans/visual-v1/e4/REPORT.md) e [aceite da integração](plans/visual-v1/e4/integration-review.md). BASIC/FULL e publicação não foram implementados.

## Política de arquivos

- **Fontes e testes:** `core-api/src`, `web-ui/src` e `scripts/` são versionados. Os scripts de avaliação e seus testes usam as fixtures abaixo sem depender de saídas ignoradas.
- **Documentação operacional:** `Spec.md`, `README.md`, `AGENTS.md`, `docs/` e relatórios de avaliação selecionados são versionados. `Handoff.md` permanece arquivo local histórico de 08/09/2026, não normativo.
- **Fixtures necessárias:** os contextos congelados de `editorial/evaluations/2026-09-26`, os 21 contextos de `editorial/coverage-clarity-v1/batch-01`, os resultados históricos v4 em `editorial/local-rules-runs` e os calendários Parquet de 2025/2026 usados por `scripts/test_local_calendar.py` são incluídos. Os Parquets são pequenos (aproximadamente 64 KiB juntos) e preservam exatamente a fonte usada no teste.
- **Evidências versionadas:** manifestos, protocolos, resultados e métricas selecionados das avaliações, a verificação HTTP, e uma imagem de cada largura inspecionada. Seus hashes e relatórios documentam a linhagem. O checkout permite executar os testes e inspecionar essas evidências.
- **Apenas local:** JARs de baseline, cópias completas de fontes históricas, respostas HTTP e tentativas operacionais reproduzíveis, `target/`, `node_modules/`, ambientes virtuais, caches, logs, HTMLs de inspeção gerados e capturas redundantes. Permanecem preservados nesta máquina. Um hash desses arquivos registra a evidência arquivada, mas **não** torna o arquivo reproduzível por um checkout novo. Um `freeze.json` histórico que inclui caminhos locais ou versões antigas de código serve à auditoria daquela execução, não como gate da revisão atual.

Os snapshots públicos em `web-ui/public/data` e o manifesto de aprovações não foram alterados por esta organização. Exportação, revisão editorial e publicação seguem etapas separadas no [runbook](runbooks/deploy-recovery.md).

## Inventário anterior à organização

O [inventário inicial com SHA-256](initial-inventory-2026-10-05.json) foi registrado antes de editar ou fazer staging: branch `main`, HEAD `a3868af056442e073c3f180f2d4681d83bb1ed31`, 1143 caminhos alterados ou novos, nenhum staged. Ele inclui o hash de `Handoff.md` sem versionar o conteúdo. SHA-256 do próprio inventário: `616bbae33a0402dce48ad22d2160adad8ad19b640897787bb3b4e9a884c0df88`.

Antes do `clean verify`, os JARs locais de baseline já estavam arquivados: integração `30c4880142f393d5314022ad5bb5ee43495757957388b1a7f805d053af2dda1c`, validação operacional `e742e8040b838356aac90a0fdbb1b0fd54df3b3ea9b763625a892bd95e6b0f7b` (SHA-256). Esses binários não integram o checkout; os hashes atestam somente as cópias locais preservadas.

## Preparação visual E0/E1

A interface local foi consolidada no commit `3a06bbb`. O [contrato visual interno v1](../contracts/visual-analysis/v1/README.md), schema, vocabulário, 20 fixtures sintéticas válidas e 15 inválidas continuam congelados. E2 projeta documentos reais por tentativa e expõe GET `/insights`; o frontend visual E3 está integrado somente ao laboratório local. O seletor, renderer e snapshot mantêm suas versões.

Cinco defeitos legados de sinal/tempo foram reproduzidos em testes expected-failure e continuam abertos. O pacote registra critérios, limites e ordens de trabalho de backend/frontend, sem abrir novas sessões ou publicar. Verificações desta preparação: [relatório estruturado](plans/visual-v1/verification.json).

## Projeção visual E2

`visual-projector-1.0.0` consome claims v5 validadas e contexto congelado para produzir observações semanais, seis encontros, achados, restrições tipadas e relações. A API HTTP local 1.2.0 oferece o documento apenas para a tentativa consultada; `visualIdentity` é o SHA-256 dos bytes persistidos de `insights.json`. POST e GET textual permanecem. O [relatório E2](../editorial/evaluations/2026-10-06-visual-e2/README.md) contém 17 documentos reais de contextos conhecidos e a lacuna de fase pós-temporada do contrato congelado. Production e snapshots públicos não foram tocados.

## Integração visual E2/E3

Branch local `codex/visual-integration-e2-e3`: cartões e séries semanais precedem o texto, que fica expansível. Legado v3 preserva leitura textual; fixtures sintéticas têm modo separado. O frontend consome os 17 documentos E2 e mantém o build público independente.

Verificados: 127 testes Java, 116 frontend (incluem cinco falhas esperadas legadas), 12 Python do contrato, lint/build e freeze E1. O roteiro HTTP executou 73 requisições de integração e 72 GETs após reinício, com identidades e bytes preservados. Browser: BAL–DAL e CHI–BAL reais, desktop/mobile, histórico/recarga, teclado e texto opcional. Nenhuma publicação ou avaliação editorial independente. [Relatório e reprodução](plans/visual-v1/integration-report.md).
