# Runbook: recuperação segura do deployment

Este runbook prepara a cadeia `browser -> /api/v1 same-origin -> função Vercel -> Spring HTTPS -> PostgreSQL/Supabase JDBC`. Ele não autoriza mutations remotas. Execute primeiro o inventário e obtenha autorização específica para cada bloco de criação/configuração/deploy.

## Estado observado em 2026-09-09/10

- O domínio Production `https://nfl-sideline.vercel.app` está público e serve um build Vite.
- O deployment Production mais recente exposto pelos metadados públicos do GitHub foi concluído com sucesso em 2026-09-06 para o commit `705536f0799fe0e7e45fde8fbce4dcafb4a865be`; o HEAD local posterior não tem status de deployment registrado.
- O deployment imutável desse registro exige Vercel Authentication; o alias Production não exige.
- No alias Production atual, `/api/v1/health` retorna `index.html`, comprovando que não há função backend nessa rota e que o fallback SPA a captura.
- O bundle publicado contém `http://localhost:8080/api/v1`; seu SHA-256 observado é `0c983e6151667c6fac3f14f2dabdd8e79a057cf9b1f245c8446b75de4177648b`.
- Não há URL Cloud Run/backend versionada no repositório. A CLI Vercel não está instalada e o browser não tem sessão Vercel; por isso Root Directory, overrides do dashboard e nomes/escopos de variáveis ainda não estão autenticadamente confirmados.
- O `gcloud` 542.0.0 está instalado e possui configuração local apontando para `geminimgi`, mas a credencial está expirada. Projetos, billing, APIs e serviços Cloud Run não puderam ser enumerados.
- A CLI Supabase não está instalada. Nenhuma conexão ao Supabase remoto foi feita neste pacote.

## 1. Contrato e segurança

- Vercel Root Directory: `web-ui`.
- Framework: Vite; install `npm ci`; build `npm run build`; output `dist`.
- O fallback SPA para `/index.html` roda depois da resolução de arquivos/funções, portanto não captura `/api/*`.
- `CORE_API_BASE_URL`: origem HTTPS do backend sem caminho, query, credenciais ou barra final.
- `CORE_API_SHARED_TOKEN`: segredo compartilhado entre a função e o Spring, com ao menos 32 caracteres.
- `APP_ENV`: obrigatório e explicitamente `preview` ou `production` no backend hospedado; ausência, vazio ou valor desconhecido falham no startup. Somente `local` explícito dispensa token.
- `VITE_API_BASE_URL`: público e opcional, somente para development/test local. Nunca cadastrar em Preview/Production nem cadastrar secrets em `VITE_*`; builds de produção sempre usam `/api/v1`.
- O Spring usa JDBC; este fluxo não reativa nem usa a Supabase Data API.
- CORS não é autenticação. Em produção, browser e proxy são same-origin; o salto proxy -> Spring é server-to-server.

## 2. Inventário read-only

Não continue se as sessões não estiverem autenticadas ou se projeto/região forem ambíguos.

```bash
vercel whoami
vercel project ls
vercel project inspect <VERCEL_PROJECT_NAME>
vercel list <VERCEL_PROJECT_NAME>
vercel env ls

gcloud auth list
gcloud config configurations list
gcloud projects list
gcloud billing projects describe <GCP_PROJECT_ID>
gcloud services list --enabled --project <GCP_PROJECT_ID>
gcloud run services list --project <GCP_PROJECT_ID> --region <GCP_REGION>
gcloud run services describe <CLOUD_RUN_SERVICE> --project <GCP_PROJECT_ID> --region <GCP_REGION>
```

No dashboard Vercel, conferir `Settings > General` (Root Directory, Build Command e Output Directory), `Settings > Environment Variables` (somente nomes, ambientes e presença) e `Settings > Deployment Protection`. Não copiar valores. Preview protegido deve ser acessado com `vercel curl`, sem desativar a proteção.

## 3. Recursos possivelmente necessários

Se não existirem, serão necessários: projeto GCP com billing, APIs Cloud Run/Cloud Build/Artifact Registry/Secret Manager, repositório Artifact Registry, service account de runtime com acesso mínimo aos secrets, cinco secrets no Google Secret Manager, serviço Cloud Run e duas variáveis server-side por ambiente Vercel.

Cloud Run cobra CPU, memória, requests e egress conforme uso/região, após os free tiers aplicáveis. Artifact Registry, Cloud Build, Secret Manager e tráfego até o PostgreSQL também podem gerar custo. `min-instances=0` reduz custo ocioso, mas introduz cold start. Limitar `max-instances` protege custo e também limita a pressão de conexões JDBC no Supabase.

Riscos operacionais principais: cold start; esgotamento do pool/conexões do PostgreSQL; rotação dessincronizada do token; URL JDBC incompatível com a rede de saída do Cloud Run; endpoint Cloud Run publicamente alcançável no nível IAM, embora negado no nível da aplicação sem o token; abuso do endpoint Gemini através da função pública da Vercel. O token compartilhado protege o salto Vercel -> Spring, não autentica o usuário do browser.

## 4. Comandos propostos de preparação GCP

Os comandos abaixo são mutations e exigem autorização específica. Defina os identificadores aprovados antes de executar.

```bash
export NFL_GCP_PROJECT_ID=<GCP_PROJECT_ID>
export NFL_GCP_REGION=<GCP_REGION>
export NFL_AR_REPOSITORY=nfl-sideline
export NFL_CLOUD_RUN_SERVICE=nfl-sideline-core-api
export NFL_IMAGE="${NFL_GCP_REGION}-docker.pkg.dev/${NFL_GCP_PROJECT_ID}/${NFL_AR_REPOSITORY}/core-api:preview"

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com --project "$NFL_GCP_PROJECT_ID"
gcloud artifacts repositories create "$NFL_AR_REPOSITORY" --repository-format=docker --location "$NFL_GCP_REGION" --project "$NFL_GCP_PROJECT_ID"

gcloud secrets create nfl-sideline-core-api-shared-token --replication-policy=automatic --project "$NFL_GCP_PROJECT_ID"
gcloud secrets create nfl-sideline-db-url --replication-policy=automatic --project "$NFL_GCP_PROJECT_ID"
gcloud secrets create nfl-sideline-db-user --replication-policy=automatic --project "$NFL_GCP_PROJECT_ID"
gcloud secrets create nfl-sideline-db-password --replication-policy=automatic --project "$NFL_GCP_PROJECT_ID"
gcloud secrets create nfl-sideline-gemini-api-key --replication-policy=automatic --project "$NFL_GCP_PROJECT_ID"
```

Para cada secret, executar `gcloud secrets versions add <SECRET_NAME> --data-file=- --project "$NFL_GCP_PROJECT_ID"`, colar o valor fora do histórico do shell e encerrar stdin. Não incluir credenciais na URL JDBC.

Antes do build/deploy, conceder `roles/secretmanager.secretAccessor` somente à service account de runtime aprovada. Criar service account ou alterar IAM exige autorização própria.

```bash
gcloud builds submit core-api --tag "$NFL_IMAGE" --project "$NFL_GCP_PROJECT_ID"
gcloud run deploy "$NFL_CLOUD_RUN_SERVICE" \
  --image "$NFL_IMAGE" \
  --project "$NFL_GCP_PROJECT_ID" \
  --region "$NFL_GCP_REGION" \
  --service-account <RUNTIME_SERVICE_ACCOUNT> \
  --allow-unauthenticated \
  --set-env-vars APP_ENV=production \
  --set-secrets CORE_API_SHARED_TOKEN=nfl-sideline-core-api-shared-token:latest,SUPABASE_DB_URL=nfl-sideline-db-url:latest,SUPABASE_DB_USER=nfl-sideline-db-user:latest,SUPABASE_DB_PASSWORD=nfl-sideline-db-password:latest,GEMINI_API_KEY=nfl-sideline-gemini-api-key:latest \
  --min-instances 0 \
  --max-instances <APPROVED_MAX_INSTANCES> \
  --timeout 30s
```

Cloud Run injeta `PORT`; não a configure manualmente. `--allow-unauthenticated` é necessário para a função Vercel sem identidade GCP, mas o Spring continua negando qualquer chamada sem `X-NFL-Sideline-Token`. Uma evolução futura pode substituir o segredo estático por Vercel OIDC + Google Workload Identity Federation.

## 5. Secrets exigidos

Backend/Google Secret Manager:

- `CORE_API_SHARED_TOKEN`
- `SUPABASE_DB_URL`
- `SUPABASE_DB_USER`
- `SUPABASE_DB_PASSWORD`
- `GEMINI_API_KEY`

Runtime não secreto: `APP_ENV=production` (obrigatório); `PORT` é injetada pelo Cloud Run. O backend deve recusar startup se `APP_ENV` estiver ausente, vazio ou não for `local`, `preview` ou `production`.

Vercel, separadamente para Preview e Production:

- `CORE_API_BASE_URL`
- `CORE_API_SHARED_TOKEN`

Marcar o token como Sensitive e usar ao menos 32 caracteres. Preview deve apontar para backend/token de staging sempre que houver separação de ambientes. Não cadastrar `VITE_API_BASE_URL` em Preview/Production; o build ignora essa variável em produção e `/api/v1` é o contrato obrigatório.

Antes de Production, criar no Vercel Firewall uma regra de rate limiting com condição `Request Path equals /api/v1/analysis/matchup` e método `POST`, inicialmente em modo de observação e depois com resposta `429`. Limite, janela e chave (por exemplo IP/JA4, conforme o plano) devem ser aprovados após observar o Preview. Essa configuração é uma mutation remota, pode ter cobrança por requests e não foi aplicada neste pacote.

## 6. Preview Vercel proposto

Este bloco altera configuração/deployment Vercel e exige autorização específica. Não executar Production.

```bash
cd web-ui
vercel link
vercel env add CORE_API_BASE_URL preview
vercel env add CORE_API_SHARED_TOKEN preview
vercel deploy
```

Guardar a URL retornada como `<PREVIEW_URL>` e validar:

```bash
vercel curl /api/v1/health --deployment <PREVIEW_URL>
vercel curl '/api/v1/games?season=2026' --deployment <PREVIEW_URL>
curl -i '<CLOUD_RUN_URL>/api/v1/health'
```

Os dois primeiros devem retornar JSON do Spring; o acesso Cloud Run direto sem token deve retornar `401`. Depois, abrir o Preview no browser, confirmar lista/detalhe, console e requests, e verificar ausência total de chamadas para localhost e de secrets em bundle/respostas. CORS não substitui autenticação nem rate limiting. Não promover automaticamente.

## 7. Rollback

- Vercel Preview: parar de usar/remover o deployment Preview; Production permanece intocada.
- Variáveis Vercel: restaurar os valores/escopos registrados no inventário; se eram novas, remover somente as duas entradas criadas.
- Cloud Run: direcionar 100% do tráfego à revisão anterior com `gcloud run services update-traffic <SERVICE> --to-revisions=<PREVIOUS_REVISION>=100 --region <REGION> --project <PROJECT_ID>`.
- Se o serviço foi criado apenas para este preview, mantê-lo com zero tráfego ou removê-lo somente mediante nova autorização destrutiva.
- Secrets: desabilitar a versão nova após restaurar consumidores; não destruir versões durante rollback emergencial.
- Código: descartar apenas este diff local de forma seletiva. Não usar `git reset --hard` e não tocar em `Handoff.md`.

## 8. Gate para promoção

Promoção para Production requer evidências de health, jogos 2026, detalhe de jogo, console sem erros relevantes, nenhuma chamada a localhost, backend direto negado sem token, auditoria de bundle/respostas sem secrets e rate limiting validado para `POST /api/v1/analysis/matchup`. Exige autorização separada após entrega do Preview.
