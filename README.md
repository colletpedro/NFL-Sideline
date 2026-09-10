# NFL Sideline

NFL Sideline é um protótipo funcional para análise tática de confrontos da NFL. O sistema combina métricas semanais de eficiência, contexto de calendário e mercado e uma análise textual estruturada gerada pelo Gemini.

A prioridade do produto é explicar o confronto entre ataques e defesas. Uma previsão pode aparecer como conclusão secundária da análise, mas ainda não existe um modelo preditivo quantitativo independente. As probabilidades chamadas de “Model” na interface são probabilidades implícitas sem vig, derivadas das moneylines do mercado.

## Arquitetura atual

```text
nflverse / nflreadpy
  -> Parquet local
  -> ETL Python + Polars + psycopg2
  -> PostgreSQL no Supabase
  -> API Java 21 / Spring Boot / JPA protegida por token de servico
  -> análise Gemini + cache PostgreSQL
  -> proxy server-side da Vercel
  -> React 18 / TypeScript / Vite via /api/v1 same-origin
```

- `etl-pipeline/`: `run_pipeline.py` orquestra aquisição, times, jogos/mercado, métricas e auditoria de cada temporada diretamente no PostgreSQL do Supabase.
- `core-api/`: expõe a API REST e orquestra o Gemini, cache e validação numérica.
- `web-ui/`: dashboard Vite; em desenvolvimento usa `http://localhost:8080/api/v1` por default e em produção usa `/api/v1` na mesma origem.
- `supabase/config.toml` e `supabase/migrations/`: configuração local e baseline versionadas para reconstruir o schema em um banco vazio.
- `.github/workflows/`: CI Java e ETL semanal existentes; a confiabilidade do workflow semanal ainda não foi comprovada.

S3 permanece apenas como caminho opcional/legado em `run_local.py`; nenhum upload ocorre sem `--upload-s3`. A existência de um frontend Vercel publicado foi relatada, mas o inventário autenticado de Vercel e Cloud Run ainda precisa ser concluído antes de qualquer mutation remota.

O frontend não usa a Supabase Data API: acessa somente o backend Spring. O backend e os loaders Python acessam o PostgreSQL diretamente por JDBC e psycopg2.

## Pré-requisitos

- Java 21 e Maven 3.9+
- Python 3.11+
- Node.js 18+ e npm
- PostgreSQL/Supabase acessível
- Supabase CLI 2.117.0 via `npx` e Docker somente se você quiser reconstruir e testar o banco localmente

## Configuração

Crie o arquivo local de ambiente a partir do exemplo:

```bash
cp .env.example .env
```

Preencha `SUPABASE_DB_URL`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD` e `GEMINI_API_KEY`. `APP_ENV` é obrigatório e aceita somente `local`, `preview` ou `production`; ausência, vazio ou valor desconhecido encerram o startup. Para desenvolvimento, defina explicitamente `APP_ENV=local`. `PORT` usa `8080` por default. Em `preview` e `production`, `CORE_API_SHARED_TOKEN` é obrigatório e deve ter ao menos 32 caracteres. O `.env` contém segredos e não deve ser commitado. Variáveis AWS, quando presentes, não disparam upload: o fluxo S3 legado exige também `--upload-s3`.

Na Vercel, `CORE_API_BASE_URL` e `CORE_API_SHARED_TOKEN` são variáveis exclusivamente server-side e devem existir separadamente em Preview e Production. `CORE_API_BASE_URL` deve ser exclusivamente uma origem HTTPS, sem caminho, query, fragmento ou credenciais; o token deve ter 32+ caracteres. `VITE_API_BASE_URL` é pública e só vale em development/test local: não a cadastre em Preview ou Production, pois builds de produção usam obrigatoriamente `/api/v1`. Toda variável `VITE_*` é visível no browser. Nunca use `VITE_*` para senha do banco, chave Gemini ou token compartilhado.

## Execução local

### 1. Preparar o banco

A baseline está em [`supabase/migrations/`](supabase/migrations/) e a configuração local já está versionada em `supabase/config.toml`; num checkout normal, não execute `supabase init`. Aplique a baseline somente a um PostgreSQL/Supabase novo e vazio:

```bash
npx --yes supabase@2.117.0 start
npx --yes supabase@2.117.0 db reset --local
```

Esses comandos exigem Docker ativo. Não aplique esta baseline sobre o Supabase remoto existente: a reconciliação do histórico será feita separadamente.

Validação da baseline e do hardening: a Supabase CLI 2.117.0 executa `db reset --local` em um stack vazio. As seis tabelas são criadas sem dados; a migration `*_harden_data_api_access.sql` habilita RLS sem policies e remove os privilégios de `anon`, `authenticated` e `PUBLIC`. Como não há `supabase/seed.sql`, a CLI emite um aviso de arquivo de seed ausente, mas o reset termina normalmente.

### Segurança da Data API

Não há consumidores atuais da Data API. O stack local a mantém desativada (`[api].enabled = false`); o PostgreSQL local permanece disponível para o backend e ETL. Nas seis tabelas da aplicação, RLS é habilitado sem policies e `anon`/`authenticated` não recebem privilégios, como defesa em profundidade. A migration também revoga os default privileges de `postgres` para tabelas, sequences e funções futuras; em funções, a revogação é global ao criador para substituir o `EXECUTE` implícito de `PUBLIC`. Objetos criados por outra role exigem auditoria e decisão separada. Qualquer acesso futuro pela Data API exige decisão arquitetural, grants explícitos, policies e novos testes. `service_role` conserva somente os grants explícitos dos objetos atuais, é exclusivamente server-side e nunca pode ser exposta no frontend.

O rollout remoto foi concluído em 2026-09-08: a baseline foi reconciliada somente no histórico, a migration de hardening foi aplicada e o proprietário confirmou no Dashboard que **Enable Data API** está desativado. REST e GraphQL não expõem a aplicação; JDBC e psycopg2 permanecem como os únicos caminhos de acesso. O remoto tem RLS habilitado sem policies, sem acesso para `anon`, `authenticated` ou `PUBLIC`, e com `service_role` privilegiada apenas nos objetos atuais por grants explícitos. Os defaults residuais de `supabase_admin` são gerenciados pela plataforma e não foram alterados. Reativar a Data API exige nova revisão de grants, default ACLs, funções, policies e consumidores. Para mudanças futuras, aplique somente migrations versionadas; não execute novamente a baseline existente. Consulte o [runbook](docs/runbooks/supabase-remote-hardening.md).

### 2. Preparar e testar o ETL

As dependências diretas são pinadas e o extra `test` instala pytest e Pandas para validar também a compatibilidade do adaptador de extração.

```bash
python3.11 -m venv etl-pipeline/.venv
source etl-pipeline/.venv/bin/activate
pip install -e "etl-pipeline[test]"
python -m pytest etl-pipeline
```

### 3. Executar o pipeline observável

Sem `--season`, todos os scripts usam a temporada NFL corrente: o ano civil de março a dezembro e o ano anterior em janeiro/fevereiro. A faixa aceita é 1999 até a temporada seguinte à corrente; flags repetidas são deduplicadas e ordenadas.

```bash
source etl-pipeline/.venv/bin/activate
python etl-pipeline/run_pipeline.py --allow-missing-pbp
python etl-pipeline/run_pipeline.py --season 2024 --season 2025
python etl-pipeline/run_pipeline.py --season 2025 --data-dir /tmp/fixture --skip-acquire
```

Sem `--season`, a temporada NFL corrente é usada; múltiplas temporadas são processadas sequencialmente, com uma linha independente em `ingestion_runs`, e o pipeline para na primeira falha. Por temporada, a ordem é: conexão PostgreSQL, `RUNNING`, aquisição de schedules/PBP, times, games/market, métricas e `SUCCEEDED`. Uma falha após o início faz rollback da etapa aplicável, tenta registrar `FAILED` e é propagada ao processo.

Os arquivos são gravados em `etl-pipeline/data/raw/{schedules,pbp}/season=YYYY/`. `--allow-missing-pbp` permite sucesso com `rows_pbp = 0` quando o PBP ainda não existe, desde que schedules, seed e games tenham concluído; schema inválido e falhas operacionais continuam fatais. `--skip-acquire` exige schedules locais válidos, usa somente Parquets do `--data-dir`, não chama nflverse nem S3 e só tolera PBP ausente junto com `--allow-missing-pbp`.

`run_local.py`, `seed_teams.py`, `load_games.py` e `load_metrics.py` permanecem disponíveis como CLIs individuais. Somente o `run_local.py` legado aceita `--upload-s3`; S3 não faz parte de `run_pipeline.py`.

### 4. Contratos de jogos e execução

```bash
result = home_score - away_score
```

`load_games.py` persiste diretamente `home_score`, `away_score` e `result` do schedule como um snapshot atômico. Os três campos devem ser todos nulos ou todos preenchidos; valores preenchidos são inteiros, scores são não negativos e `result` deve ser a diferença acima, incluindo empate com zero. Não há derivação nem preenchimento de campo ausente. Em conflito, um trio integralmente nulo preserva integralmente o resultado conhecido; um trio completo e válido o substitui integralmente. Qualquer combinação parcial falha antes do banco. Todo upsert define `games.updated_at = now()`. A seleção continua descartando jogos sem cotação completa.

`ingestion_runs` tem uma linha por execução/temporada: `week` fica NULL porque a temporada inteira é reprocessada; `status` usa exatamente `RUNNING`, `SUCCEEDED` ou `FAILED`; `rows_pbp` conta o PBP bruto selecionado antes do filtro de jogadas válidas; `rows_games` conta o DataFrame final após os filtros e antes do upsert; `started_at` e `finished_at` vêm do banco; sucesso deixa `error_message` NULL e falha grava mensagem sanitizada de até 1.000 caracteres. Uma interrupção abrupta pode deixar `RUNNING`; ainda não há tratamento automático desses runs.

O workflow semanal instala o pacote versionado e chama somente `python etl-pipeline/run_pipeline.py --allow-missing-pbp`. Isso fornece um único caminho observável, mas ainda não comprova confiabilidade contínua em produção.

### 5. Backend

Carregue as quatro variáveis obrigatórias do `.env` no ambiente do processo sem `export $(xargs ...)` e execute a partir da raiz:

```bash
set -a
source .env
set +a
mvn -f core-api/pom.xml test
mvn -f core-api/pom.xml spring-boot:run
```

A API ficará em `http://localhost:8080/api/v1`.

Somente o perfil explicitamente configurado como `APP_ENV=local` aceita rotas sem token. `preview` e `production` exigem `X-NFL-Sideline-Token` em todas as rotas `/api/v1/**`, inclusive health; ausência, token menor que 32 caracteres, ambiente vazio ou ambiente desconhecido fazem o processo falhar no startup. CORS é centralizado e, por default, permite somente `http://localhost:5173` e `http://127.0.0.1:5173` no perfil local. CORS não autentica chamadas.

### 6. Frontend

```bash
npm --prefix web-ui ci
npm --prefix web-ui test
npm --prefix web-ui run dev
```

A interface ficará em `http://localhost:5173`.

Para trocar a API apenas no desenvolvimento/teste local, copie `web-ui/.env.example` para `web-ui/.env.local` e ajuste `VITE_API_BASE_URL`. O build de produção ignora qualquer valor dessa variável e usa obrigatoriamente `/api/v1`. O proxy permite somente health, teams, games e `POST /analysis/matchup`, limita o body do POST, não encaminha cookies/Authorization do browser e injeta o token compartilhado apenas no servidor. Ele só aceita backend HTTPS de origem pura e recusa configuração ausente, curta ou inválida com resposta sanitizada.

O token compartilhado protege o Spring contra chamadas diretas, mas não limita clientes que chamem a função pública da Vercel. Antes de promover para Production, aplique e valide uma regra de rate limiting no Vercel Firewall especificamente para `POST /api/v1/analysis/matchup`. Uma futura autenticação de usuário pode fornecer quotas mais fortes, mas não faz parte deste pacote.

## Deploy seguro

O runbook de inventário, preparação de Cloud Run, configuração Preview da Vercel, validação e rollback está em [`docs/runbooks/deploy-recovery.md`](docs/runbooks/deploy-recovery.md). Nenhum comando de mutation remota deve ser executado sem autorização específica. O primeiro deploy remoto deve ser Preview; promoção para Production exige uma autorização separada.

## Verificações

```bash
npx --yes supabase@2.117.0 db reset --local
python3.11 -m venv /tmp/nfl-sideline-etl-test-venv
/tmp/nfl-sideline-etl-test-venv/bin/pip install -e "etl-pipeline[test]"
/tmp/nfl-sideline-etl-test-venv/bin/python -m pytest etl-pipeline
mvn -f core-api/pom.xml -o test
npm --prefix web-ui test
npm --prefix web-ui run build
npm --prefix web-ui run lint
```

Em 2026-09-09, a validação local reaplicou as duas migrations intactas e executou o novo orquestrador com fixtures: 2 times, 1 jogo, 1 mercado, 4 linhas brutas de PBP e 2 métricas. A segunda execução não duplicou dados e criou outro run auditável; `updated_at` avançou. Um placar válido sobreviveu a uma fonte posterior com NULL, outro placar não nulo o corrigiu, e uma inconsistência posterior encerrou com código não zero e `FAILED`, mantendo os dados válidos. Os testes e advisors usaram somente o stack local. Isso não comprova confiabilidade contínua do cron em produção.

## Limitações conhecidas

- Não há modelo preditivo quantitativo próprio; o fair value exibido vem do mercado.
- `early_down_epa` e `explosive_play_rate` existem no schema, mas não são populadas.
- A observabilidade é deliberadamente parcial: não há alertas, retenção, dashboard nem tratamento automático de runs presos em `RUNNING`.
- A validação anti-alucinação verifica somente números enviados em `metricas_citadas`; ela não inspeciona todos os números que possam aparecer nos quatro textos finais.
- O inventário remoto de Vercel e GCP depende de autenticação válida; a implementação local não comprova que o backend público e os secrets de Preview já existam.
- O ETL semanal usa o orquestrador único e é autossuficiente quanto à ordem, mas ainda não possui evidência de execuções reais suficientes para afirmar confiabilidade contínua em produção.
- A Data API remota está desativada. Qualquer reativação ou nova migration remota exige revisão de segurança e o fluxo versionado documentado no runbook; a baseline histórica não deve ser executada novamente.

Consulte [`Spec.md`](Spec.md) para contratos, schema, métricas, decisões e roadmap completos.
