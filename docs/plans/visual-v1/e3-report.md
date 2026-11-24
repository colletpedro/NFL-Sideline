# E3 — leitura visual no laboratório local

**Base:** checkpoint E1 `3a06bbb`; preparação congelada E1 aplicada como `7b69316` (mesmo conteúdo de `5096a58`). Branch `codex/visual-analysis-e3`, worktree isolada. Sem push, deploy ou alteração dos snapshots públicos.

## Entrega

- `web-ui/src/features/analysis-visual/`: tipos do documento v1, validação fechada pelo schema congelado e invariantes observáveis, Decimal exato para sinal/exibição, escala assinada compartilhada, cartões de passe/corrida, panorama geral expansível, tabela de evidências e limites.
- Laboratório `web-ui/local-editorial/`: leitura textual existente, consulta GET de insights vinculada ao jogo/UUID/identidade da tentativa, aviso para v3 sem visual, rejeição visível de documento inválido, recuperação pelo histórico e modo de fixtures sintéticas separado de catálogo/geração reais.
- Proxy: apenas `GET /__editorial/{gameId}/{uuid}/insights` acrescentado à allowlist. Host, Origin, marker, corpo vazio, query recusada, sem CORS, sem `.env` e sem método POST adicional.
- Build público: `vite build` permanece estático; busca no `dist/` por `SHARED_SYMMETRIC_ZERO_V1`, `/__editorial/`, `FIXTURE SINTÉTICA` e `visual-projector-1.0.0` não encontrou módulos locais.

A validação browser recusa versões desconhecidas, campos extras, referências faltantes, papéis de métricas trocados, origem fixture na API real e identidades divergentes entre contexto, tentativa, envelope e documento. O hash `visualIdentity` é validado em formato; a prova dos bytes persistidos cabe ao E2, porque o envelope HTTP entrega o documento como objeto JSON. O browser não reinterpreta relação ou destaque a partir da posição do gráfico.

## Verificação

- `python3 scripts/verify_visual_contract.py`: 20 fixtures válidas, 15 inválidas rejeitadas; proveniência do motor não verificada por esse gate.
- `npm --prefix web-ui test`: 96 testes aprovados, incluindo as cinco regressões legadas `it.fails` ainda abertas. Os testes E3 cobrem as 20 fixtures, 15 negativas, envelope/proveniência, ausência e dados unilaterais, empates, zero, sinais pequenos, extremos e geometria assinada.
- `npm --prefix web-ui run lint`, `npm --prefix web-ui run build`, `git diff --check`: aprovados.
- Inspeção manual no navegador local: 1440 × 1000, 390 × 844 e 320 × 700. `documentElement.scrollWidth === clientWidth` nas três larguras. Tabela expandida por Enter com foco visível; os seis valores apareceram com papel, time, período, decimal exato e volume. Não houve auditoria formal WCAG nem teste automatizado de zoom do navegador.

Evidências sintéticas de layout:

- [Desktop, cabeçalho e leitura rápida](e3-evidence/desktop-1440-top.jpg)
- [Desktop, cartões e gráfico assinado](e3-evidence/desktop-1440-cards.jpg)
- [Mobile 390](e3-evidence/mobile-390.jpg)
- [Mobile 320](e3-evidence/mobile-320.jpg)

## Limite de aceite

Nesta revisão, o documento visual foi exercitado com fixtures E1, não com um resultado gerado por E2. O endpoint Java e o artefato real estão na frente backend separada. O aceite final exige: catálogo real → POST explícito → GET visual da tentativa → histórico → recarga → GET do mesmo documento, além da verificação de identidade e persistência após reinício. Não inferir qualidade editorial a partir das fixtures sintéticas.
