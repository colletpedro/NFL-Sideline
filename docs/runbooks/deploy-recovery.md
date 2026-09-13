# Runbook: publicação estática

O site público não depende de backend hospedado. O fluxo é `ETL controlado -> PostgreSQL -> exportador Java read-only -> snapshots JSON -> build Vite -> Vercel estática`.

## Preparação

1. Execute a suíte offline.
2. Carregue as credenciais PostgreSQL já existentes somente no processo local.
3. Gere o snapshot com o comando documentado em `docs/static-snapshot-contract.md`.
4. Inspecione `manifest.json` e os arquivos de temporada. É proibida a presença de `context_json`, prompts, hashes de prompt, segredos ou configuração interna.
5. Execute `npm --prefix web-ui run build`.
6. Confirme no diretório `web-ui/dist` que não existem chamadas para backend, localhost, Supabase ou Gemini.

## Leitura remota controlada

Quando autorizada, a geração remota usa JDBC PostgreSQL em conexão read-only e uma transação `@Transactional(readOnly = true)`. Não execute ETL, migrations ou qualquer comando de escrita. Compare antes e depois as contagens de `teams`, `games`, `team_week_metrics`, `market_implied`, `analysis_cache` e `ingestion_runs`; qualquer diferença invalida a execução.

## Vercel

- Root Directory: `web-ui`;
- Framework: Vite;
- Install: `npm ci`;
- Build: `npm run build`;
- Output: `dist`;
- fallback SPA: `/(.*) -> /index.html`.

Production serve somente assets e `/data/**`. Não configure destino de backend, token de proxy nem override de API na Vercel. Não há Function em `api/`.

## Validação local antes de publicar

Sirva `web-ui/dist`, abra a home e um detalhe, teste navegação direta e retorno, e confira desktop/mobile. A aba de rede deve mostrar apenas arquivos estáticos; são proibidos `/api/v1`, POST, localhost, Supabase e Gemini.

## Rollback

Como snapshots são versionados, restaure em uma mudança posterior o último conjunto conhecido e gere novo build. Nunca reexecute a baseline do banco e nunca edite o banco para corrigir um snapshot público. S3/AWS permanecem fora deste fluxo e serão tratados separadamente.
