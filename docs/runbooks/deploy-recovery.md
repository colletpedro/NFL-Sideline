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

## Diagnóstico da geração editorial

O prompt `editorial-matchup-v1` mantém os tipos `matchup_full_v0`/`matchup_basic_v0` e exige
resposta estruturada com quatro textos não vazios e `metricas_citadas` como objeto de números
escalares. Todo número métrico nos textos precisa ser citado e existir no contexto; anos de
1999 a 2100 não são tratados como métricas. Dados históricos devem ser identificados como
“temporada anterior”, sem representar forma atual. O cache público guarda apenas os quatro textos.

O timeout padrão é 180 segundos, substituível por `GEMINI_TIMEOUT` (por exemplo, `180s`).
O batch não repete chamadas que falham. Seu resumo inclui `failure_categories` (contagens) e
`failed_games` (categoria e gameId); nenhuma mensagem remota, corpo de resposta ou credencial
é impressa. As categorias são `HTTP_400`, `HTTP_401`, `HTTP_403`, `HTTP_404`, `HTTP_429`,
`HTTP_5XX`, `TIMEOUT`, `INVALID_JSON`, `MISSING_FIELDS`, `INVALID_NUMERIC_CITATIONS`,
`EMPTY_RESPONSE` e `UNKNOWN`. Havendo falhas de geração, o batch termina com código 1,
mas preserva os caches concluídos para revisão e publicação seletiva, sem retry implícito.

### Publicação com corte editorial em 2026-09-16

Correção validada por testes focados e uma execução de `mvn -o clean verify` (49 testes).
Canário único aprovado: `2026_02_DET_BUF`, cache FULL 25. O lote restante foi iniciado uma
única vez com `max-analyses=32`, reutilizando a identidade do canário; não houve reinício nem
retry após a interrupção da sessão por limite de uso. Na retomada, o processo não estava ativo
e foram recuperados 19 caches novos (14 FULL e 5 BASIC, incluindo o canário). A saída final
do lote não ficou disponível; o número exato de tentativas e as categorias dos jogos sem cache
não são comprováveis. O teto autorizado foi de 32 chamadas totais, incluindo o canário.

Revisão direta concluída sem bloqueios materiais nos 19 caches: times, números no contexto,
campos completos, ausência de truncamento e distinção entre histórico e forma atual.
O snapshot exportado em 2026-09-20 preserva o corte solicitado `--as-of 2026-09-16`, as seis
legacy da Week 1 e inclui 14 FULL da Week 2 e cinco BASIC da Week 3: 25 análises públicas,
272 jogos, schemaVersion 1, sem dados internos. A data real da revisão consta no manifesto.

Pendências para fix-forward, sem nova chamada nesta execução (ausência de cache; causa
individual indisponível após a interrupção):

- `2026_02_JAX_DEN`
- `2026_02_NYG_LA`
- `2026_03_ARI_SF`
- `2026_03_BAL_DAL`
- `2026_03_KC_MIA`
- `2026_03_LAC_BUF`
- `2026_03_LA_DEN`
- `2026_03_LV_NO`
- `2026_03_MIN_TB`
- `2026_03_NE_JAX`
- `2026_03_SEA_WAS`
- `2026_03_TEN_NYG`
- `2026_03_PHI_CHI`

## Deployment manual na Vercel

No projeto oficial, `Root Directory = web-ui`. Para a CLI resolver essa configuração corretamente, execute o deployment manual na raiz do repositório, nunca já dentro de `web-ui`; o segundo caso procura incorretamente `web-ui/web-ui`.

- Projeto oficial/canônico: `nfl-sideline`;
- Framework: Vite; instalação `npm ci`; build `npm run build`; saída `dist`; fallback SPA `/(.*) -> /index.html`;
- Não configure proxy, token de backend ou override de API na Vercel.

## Rollback

Como os snapshots são versionados, restaure em uma mudança posterior o último conjunto conhecido e gere/publice o build estático correspondente. O ambiente temporário `web-ui` pode servir como referência de segurança, mas não substitui as URLs canônicas. Nunca reexecute a baseline do banco nem edite o banco para corrigir um snapshot público.
