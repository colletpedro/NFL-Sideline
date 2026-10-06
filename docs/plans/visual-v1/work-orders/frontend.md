# Ordem de trabalho E3 — frontend visual

Status: pronta para despacho pelo orquestrador; nenhuma sessão frontend aberta nesta preparação. Abrir worktree sobre o mesmo commit E1 da frente backend, com checkpoint `3a06bbb` e freeze do contrato verificado. Não trabalhar na mesma pasta/branch do backend.

## Objetivo

Implementar componentes React compartilháveis de análise visual e integrá-los ao laboratório local. Começar com fixtures E1 identificadas como sintéticas; depois integrar o documento real de E2. Conclusão com fixtures é parcial; aceite final exige API real.

## Leitura inicial

`AGENTS.md`, `Spec.md`, `docs/current-state.md`, `docs/plans/2026-10-06-visual-analysis.md`, `contracts/visual-analysis/v1/README.md`, schema/copy-catalog/fixtures, `docs/plans/visual-v1/states.md`, `known-defects.md` e `docs/local-editorial-ui.md`.

## Área sob responsabilidade

`web-ui/src/features/analysis-visual/`, shell/cliente de `web-ui/local-editorial`, allowlist estrita de `web-ui/build/local-editorial.ts`, testes frontend e documentação E3. Evitar mudanças em arquivos públicos Home/MatchupDashboard/StaticNflDataClient/manifesto. O wireframe orienta hierarquia e comportamento; não copiar o app.js monolítico como implementação de produto.

## Implementação

1. Tipos e validação de entrada conforme contrato, com recusa de schema desconhecido/identidades divergentes. Preservar separação entre achado e ausência. Tratar Decimal como valor exato para exibição/referência; coordenada do gráfico nunca define relação, força ou vencedor.
2. Componentes para cartões, grade dos quatro encontros, pontos semanais, cobertura, limitação visível e tabela/definição expansíveis. Compartilhar componentes puros; módulos de geração/histórico permanecem no shell local.
3. Aplicar escala SHARED_SYMMETRIC_ZERO_V1, incluindo todos os extremos e zero; sinais e papéis claros. Dados unilaterais permanecem visíveis. Panorama geral agrupado acessível sem igualar seus números. Múltiplos destaques permanecem equivalentes. Não fazer parsing de texto nem consulta ao banco.
4. Preservar tema escuro/lima; refinar tipografia, espaçamento e responsividade. Preferir a dependência de gráficos já instalada se apropriada; SVG simples também é válido. Nenhuma biblioteca nova sem necessidade concreta.
5. Integrar GET visual por tentativa e novo caminho estrito no proxy. Preservar Host/Origin/header/body/sem query/sem CORS/sem `.env`. Não abrir rotas genéricas para acomodar o endpoint.
6. Preservar geração explícita, histórico, troca de jogo, respostas obsoletas e recuperação após falhas. Erro após POST não repete geração. Legado v3 sem visual mostra leitura textual existente e aviso de compatibilidade. Documento inválido não vira análise silenciosa.
7. A mesma página pode oferecer modo de fixture para desenvolvimento, sempre rotulado e separado do catálogo/resultados reais. Não deixar “CONTRACT_FIXTURE” se passar por resultado gerado ou publicar dados sintéticos.
8. Manter o build público estático independente. E3 não migra Production para schema v2 e não conecta o site publicado à API local.

## Verificação de saída

- `npm --prefix web-ui test`, lint e build; conferir ausência de módulos locais no bundle público.
- Todos os estados da matriz; tests de geometria assinada, zero, extremos, ausência, sinal pequeno, empates e escala compartilhada. UI não reclassifica por arredondamento/float.
- Teclado, foco visível, rótulos/formas além de cor, tabela alternativa, desktop 1440 e mobile 390/320, detalhes longos e zoom de texto; nenhuma informação essencial só em hover.
- Testes de envelope/proveniência e inconsistência entre tentativa/documento consultado; erros de rede e respostas obsoletas.
- Fluxo real E2: catálogo → POST explícito → recuperar visual da tentativa → histórico → recarregar → recuperar mesmo documento. Se backend ainda não estiver integrado, registrar entrega parcial.
- Preservar as cinco regressões legadas expected-failure. Não removê-las por substituir apenas o laboratório; correção pública é trabalho separado coordenado pela integração.
- `python3 scripts/verify_visual_contract.py` e `git diff --check`.

## Integração

Commits locais na branch da frente, sem push/deploy. Entregar commit(s), telas, evidências desktop/mobile, comandos, testes e limites. Informar mudanças necessárias de contrato ao orquestrador; não adicionar campos privados para contornar o schema.

O primeiro ciclo entrega leitura visual integrada. Comparação semântica de duas tentativas, migração pública, BASIC/FULL e enriquecimento ETL serão trabalhos seguintes. O histórico existente deve continuar funcional.
