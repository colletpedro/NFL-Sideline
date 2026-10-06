# Ordem de trabalho E2 — backend visual

Status: pronta para despacho pelo orquestrador; nenhuma sessão backend aberta nesta preparação. Abrir worktree sobre o commit comum de E1 informado pelo orquestrador, contendo a UI local do checkpoint `3a06bbb`. Conferir `contracts/visual-analysis/v1/freeze.json` antes de editar.

## Objetivo

Implementar a projeção visual do resultado local validado e disponibilizá-la por tentativa, mantendo texto e leitura dos artefatos anteriores. Entrega termina com documento real que o frontend consegue consumir e testes de reconciliação contra contexto/claims, não apenas uma nova classe/rota.

## Leitura inicial

`AGENTS.md`, `Spec.md`, `docs/current-state.md`, `docs/plans/2026-10-06-visual-analysis.md`, `contracts/visual-analysis/v1/README.md`, schema/copy-catalog/fixtures e `docs/local-editorial-api.md`. A entrega está limitada a E2; o plano completo não autoriza antecipar E5–E9.

## Área sob responsabilidade

Java `editorial/visual` (ou pacote equivalente justificado), acesso controlado ao resultado do validador, `LocalGenerationService`, `LocalResultStore`, `LocalAnalysisServer`, testes Java e documentação técnica E2. A alteração da allowlist do proxy fica com frontend, conforme a rota congelada. Não editar componentes React, fixtures compartilhadas, schema, copy-catalog ou decisões do contrato unilateralmente.

## Implementação

1. Projetar o documento v1 a partir da representação validada/resolvida, sem parsing dos quatro textos nem serialização cega da auditoria. Cumprir todos os invariantes e reconciliações do README do contrato.
2. Preservar o seletor 2.0.0, suas decisões, empates, relações, agrupamentos, claims v5, semântica v3/v4 e renderer textual 5.0.2. Não aproveitar a entrega para criar ranking ou nova política de relevância.
3. Produzir valores exatos e display controlado. Preservar referências reais, dados unilaterais e falta de volume. Projetar restrições secundárias como fatos verificáveis com `claimId: null`, sem fingir que existem claims novas.
4. Estender artefato para v4 com `insights.json` e hash; leitor v3/v4 explícito e imutabilidade. Documento não contém ID/timestamp de tentativa, para preservar determinismo semântico. Metadata ausente, como corte declarado, pode ser null; não inferir nem carregar `.env` para preencher.
5. Implementar GET por tentativa `/api/v1/local-analysis/{gameId}/{attemptId}/insights`, envelope e erros conforme contrato. Preservar POST/GET anteriores. Nenhum GET gera, regrava ou migra resultado histórico.
6. Criar novas gerações reais somente offline em saída nova de avaliação local, usando contextos versionados conhecidos. Não alterar baselines ou análises públicas. Fixtures sintéticas não podem sair da API como resultado validado.
7. Preservar fronteiras loopback/Host/Origin/métodos/body e mensagens sanitizadas. Não iniciar Spring, banco ou Gemini.

## Verificação de saída

- `mvn -f core-api/pom.xml -o clean verify` com Java 21; paridade dos casos históricos obrigatória.
- Contrato cruzado: documentos reais do Java aceitos pelo schema; números/referências reconciliados com origens; datasets sintéticos não tratados como holdout.
- Mutação de valor, time, origem, semana, papel, claim, enum, restrição falsa, agrupamento falso, identidade e hash deve falhar antes de persistir sucesso.
- IDs repetidos/dangling, zero/tiny sign, empates, ausência, semanas diferentes, agrupamento geral e relação independente testados.
- Artefato antigo v3 continua recuperável; visual indisponível retorna erro documentado; bytes anteriores intactos. Nova tentativa sobre contexto idêntico mantém documento/visualIdentity idênticos.
- HTTP real em porta/diretório exclusivos, sem colidir com o laboratório. Registrar bloqueio de sandbox se existir; teste de handler não é HTTP real.
- `python3 scripts/verify_visual_contract.py` e `git diff --check`.

## Integração

Fazer commits locais coerentes na branch da frente, sem push/deploy. Entregar ao orquestrador commit(s), versões, arquivos, comandos, testes e limitações; fornecer ao menos um exemplo real por encontro/restrição possível nos contextos locais. Caso o contrato impeça representar uma saída válida, relatar exemplo mínimo e proposta de alteração à integração; não inventar uma extensão privada no payload.

Fora do escopo: migrations/ETL/backfill, publicação, BASIC/FULL, novos modelos, credenciais, alteração de snapshots/aprovações, redefinição de métricas, correção generalizada de frontend público.
