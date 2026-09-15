# Runbook: publicação e recuperação estática

## Estado recuperado e vigente

A recuperação do site foi concluída em 2026-09-14. O site oficial é o React/Vite estático publicado no projeto Vercel `nfl-sideline`, nas URLs canônicas `https://nfl-sideline.vercel.app/` e `https://nfl-sideline-git-main-colletpedros-projects.vercel.app/`. Production serve assets e `/data/**` e não possui backend Java/Cloud Run, Function, `/api/v1`, localhost, Supabase ou Gemini no caminho público.

O fluxo vigente é `ETL Python controlado -> PostgreSQL/Supabase -> exportador Java read-only -> snapshots JSON versionados -> build Vite -> Vercel estática`. Java continua API local, camada de domínio, integração Gemini explicitamente acionada e exportador batch; Python continua o ETL que grava diretamente no PostgreSQL. A Data API do Supabase permanece desativada. S3/AWS é opcional/legado e não integra esse fluxo.

O projeto `web-ui`, disponível em `web-ui-khaki.vercel.app`, é ambiente temporário de segurança/rollback e não é endereço canônico.

## Atualização manual futura do snapshot

O workflow semanal atualiza o PostgreSQL, mas não exporta snapshots, não os versiona, não cria commit e não publica a Vercel. Para uma atualização autorizada:

1. Execute e revise o ETL conforme o procedimento aprovado; não trate o workflow atual como publicação automática.
2. Quando a leitura remota for autorizada, use JDBC PostgreSQL read-only e transação `@Transactional(readOnly = true)` no exportador. Não execute migrations nem escrita; compare antes e depois as contagens de `teams`, `games`, `team_week_metrics`, `market_implied`, `analysis_cache` e `ingestion_runs`.
3. Empacote Java 21, carregue `.env` explicitamente no processo e execute o exportador read-only:

   ```bash
   set -a
   source .env
   set +a
   java -jar core-api/target/core-api-0.1.0.jar snapshot-export \
     --season 2026 \
     --as-of 2026-09-15 \
     --output web-ui/public/data
   ```

   O Java não carrega `.env` sozinho. Substitua `--as-of` pela data UTC de corte editorial aprovada; ela é
   obrigatória e não é inferida de `generatedAt`.
4. Revise `manifest.json` e os snapshots. Não publique `context_json`, prompts, hashes de prompt, segredos ou configuração interna. Preserve o contrato atômico de scores e o estado neutro para mercado ausente.
5. Valide o build Vite e a navegação direta. A rede deve conter apenas assets e GETs de `/data/**`; são proibidos `/api/v1`, POST, localhost, Supabase e Gemini.
6. Versione o artefato revisado e faça a publicação manual aprovada.

## Deployment manual na Vercel

No projeto oficial, `Root Directory = web-ui`. Para a CLI resolver essa configuração corretamente, execute o deployment manual na raiz do repositório, nunca já dentro de `web-ui`; o segundo caso procura incorretamente `web-ui/web-ui`.

- Projeto oficial/canônico: `nfl-sideline`;
- Framework: Vite; instalação `npm ci`; build `npm run build`; saída `dist`; fallback SPA `/(.*) -> /index.html`;
- Não configure proxy, token de backend ou override de API na Vercel.

## Rollback

Como os snapshots são versionados, restaure em uma mudança posterior o último conjunto conhecido e gere/publice o build estático correspondente. O ambiente temporário `web-ui` pode servir como referência de segurança, mas não substitui as URLs canônicas. Nunca reexecute a baseline do banco nem edite o banco para corrigir um snapshot público.
