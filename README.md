# NFL Sideline

NFL Sideline é um protótipo funcional para análise tática de confrontos da NFL. O sistema combina métricas semanais de eficiência, contexto de calendário e mercado e uma análise textual estruturada gerada pelo Gemini.

A prioridade do produto é explicar o confronto entre ataques e defesas. Uma previsão pode aparecer como conclusão secundária da análise, mas ainda não existe um modelo preditivo quantitativo independente. As probabilidades chamadas de “Model” na interface são probabilidades implícitas sem vig, derivadas das moneylines do mercado.

## Arquitetura atual

```text
nflverse / nflreadpy
  -> Parquet local
  -> ETL Python + Polars + psycopg2
  -> PostgreSQL no Supabase
  -> API Java 21 / Spring Boot / JPA
  -> análise Gemini + cache PostgreSQL
  -> React 18 / TypeScript / Vite
```

- `etl-pipeline/`: baixa dados do nflverse, grava Parquet local e carrega times, jogos, mercado e métricas diretamente no Supabase.
- `core-api/`: expõe a API REST e orquestra o Gemini, cache e validação numérica.
- `web-ui/`: dashboard local que hoje aponta para `http://localhost:8080/api/v1`.
- `supabase/config.toml` e `supabase/migrations/`: configuração local e baseline versionadas para reconstruir o schema em um banco vazio.
- `.github/workflows/`: CI Java e ETL semanal existentes; a confiabilidade do workflow semanal ainda não foi comprovada.

S3 permanece apenas como caminho opcional/legado em `run_local.py`; nenhum upload ocorre sem `--upload-s3`. Cloud Run e Vercel ainda não estão implantados.

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

Preencha `SUPABASE_DB_URL`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD` e `GEMINI_API_KEY`. O `.env` contém segredos e não deve ser commitado. Variáveis AWS, quando presentes, não disparam upload: o fluxo S3 legado exige também `--upload-s3`.

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

### 3. Adquirir uma ou mais temporadas

Sem `--season`, todos os scripts usam a temporada NFL corrente: o ano civil de março a dezembro e o ano anterior em janeiro/fevereiro. A faixa aceita é 1999 até a temporada seguinte à corrente; flags repetidas são deduplicadas e ordenadas.

```bash
source etl-pipeline/.venv/bin/activate
python etl-pipeline/run_local.py --allow-missing-pbp
python etl-pipeline/run_local.py --season 2024 --season 2025
python etl-pipeline/run_local.py --season 2025 --schedules-only
```

Os arquivos são gravados em `etl-pipeline/data/raw/{schedules,pbp}/season=YYYY/`. Use `--data-dir PATH` em aquisição e loaders para outra raiz. Schedules são obrigatórios, exceto com `--pbp-only`. PBP vazio, temporada futura ou HTTP 404 de arquivo ainda não publicado falha por padrão, mas pode terminar com warning explícito via `--allow-missing-pbp`, sem criar arquivo vazio. Timeout, DNS/conexão, autenticação, rate limit, HTTP 5xx e parsing continuam fatais mesmo com a flag. `--schedules-only` e `--pbp-only` são mutuamente exclusivos. Upload do schedules ao caminho S3 legado só ocorre com `--upload-s3`; credenciais AWS isoladamente não têm efeito.

### 4. Carregar na ordem das chaves estrangeiras

```bash
source etl-pipeline/.venv/bin/activate
python etl-pipeline/seed_teams.py
python etl-pipeline/load_games.py
python etl-pipeline/load_metrics.py --allow-empty
```

Repita `--season YEAR` e use `--data-dir PATH` da mesma forma nos três loaders. `load_metrics.py` falha sem PBP válido por padrão; `--allow-empty` termina com sucesso e warning somente quando não há PBP/métricas elegíveis. Schema Parquet incompatível continua sendo erro, mesmo com essa flag. `load_games.py` mantém a regra vigente de descartar jogos sem cotação completa.

Essa ordem é obrigatória por causa das chaves estrangeiras. O workflow semanal instala o pacote versionado e executa exatamente aquisição, seed, jogos/mercado e métricas, usando os defaults compartilhados de temporada. Seu `--allow-missing-pbp` tem semântica restrita: tolera apenas PBP vazio, futuro ou 404 de arquivo ainda não publicado; não mascara outages.

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

### 6. Frontend

```bash
npm --prefix web-ui ci
npm --prefix web-ui run dev
```

A interface ficará em `http://localhost:5173`.

## Verificações

```bash
npx --yes supabase@2.117.0 db reset --local
python3.11 -m venv /tmp/nfl-sideline-etl-test-venv
/tmp/nfl-sideline-etl-test-venv/bin/pip install -e "etl-pipeline[test]"
/tmp/nfl-sideline-etl-test-venv/bin/python -m pytest etl-pipeline
mvn -f core-api/pom.xml -o test
npm --prefix web-ui run build
npm --prefix web-ui run lint
```

Em 2026-09-09, a validação local aplicou as duas migrations num stack vazio e carregou fixtures representativas duas vezes: 2 times, 1 jogo, 1 mercado e 2 métricas, sem órfãos nem duplicação. Um smoke real de schedules 2025 gravou 285 linhas e 46 colunas no diretório ignorado; o PBP real completo não foi baixado por volume, permanecendo coberto por fixtures e testes offline. Isso valida a reprodutibilidade local, não a confiabilidade contínua do cron em produção.

## Limitações conhecidas

- Não há modelo preditivo quantitativo próprio; o fair value exibido vem do mercado.
- `early_down_epa` e `explosive_play_rate` existem no schema, mas não são populadas.
- Placares e `ingestion_runs` existem no schema, mas os loaders atuais não os gravam.
- A validação anti-alucinação verifica somente números enviados em `metricas_citadas`; ela não inspeciona todos os números que possam aparecer nos quatro textos finais.
- O frontend usa uma URL de API localhost fixa.
- O ETL semanal reutiliza as CLIs versionadas e é autossuficiente quanto à ordem, mas ainda não possui evidência de execuções reais suficientes para afirmar confiabilidade contínua em produção.
- A Data API remota está desativada. Qualquer reativação ou nova migration remota exige revisão de segurança e o fluxo versionado documentado no runbook; a baseline histórica não deve ser executada novamente.

Consulte [`Spec.md`](Spec.md) para contratos, schema, métricas, decisões e roadmap completos.
