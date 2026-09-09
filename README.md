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

S3 permanece apenas como caminho opcional/legado em `run_local.py`; não participa da carga principal. Cloud Run e Vercel ainda não estão implantados.

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

Preencha `SUPABASE_DB_URL`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD` e `GEMINI_API_KEY`. O `.env` contém segredos e não deve ser commitado. As variáveis AWS são opcionais e só atendem ao fluxo S3 legado.

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

O hardening foi validado somente no ambiente local. O ambiente remoto permanece no estado anterior até uma aplicação explicitamente autorizada; desativar a Data API remota é uma configuração do projeto no Dashboard, não um efeito de `db push`. Antes de qualquer `db push`, a baseline precisa ser reconciliada com o histórico de migrations remoto conforme o [runbook](docs/runbooks/supabase-remote-hardening.md).

### 2. Preparar o ETL e carregar os times

Os scripts esperam Parquet em `etl-pipeline/data/raw/schedules/season=YYYY/` e `etl-pipeline/data/raw/pbp/season=YYYY/`. `run_local.py` baixa apenas 2023, enquanto `load_games.py` aceita somente 2025/2026. Portanto, um checkout novo ainda precisa receber Parquets compatíveis antes da carga completa; essa lacuna de preparação dos dados será resolvida no próximo pacote do ETL. O fluxo abaixo documenta a ordem correta, mas o ETL completo ainda não é reproduzível apenas a partir do checkout.

```bash
python3.11 -m venv etl-pipeline/.venv
source etl-pipeline/.venv/bin/activate
pip install -e etl-pipeline
python etl-pipeline/seed_teams.py
```

### 3. Carregar jogos e mercado

```bash
source etl-pipeline/.venv/bin/activate
python etl-pipeline/load_games.py
```

### 4. Carregar métricas

```bash
source etl-pipeline/.venv/bin/activate
python etl-pipeline/load_metrics.py
```

Essa ordem é obrigatória por causa das chaves estrangeiras.

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
mvn -f core-api/pom.xml -o test
npm --prefix web-ui run build
npm --prefix web-ui run lint
```

## Limitações conhecidas

- Não há modelo preditivo quantitativo próprio; o fair value exibido vem do mercado.
- `early_down_epa` e `explosive_play_rate` existem no schema, mas não são populadas.
- Placares e `ingestion_runs` existem no schema, mas os loaders atuais não os gravam.
- A validação anti-alucinação verifica somente números enviados em `metricas_citadas`; ela não inspeciona todos os números que possam aparecer nos quatro textos finais.
- O frontend usa uma URL de API localhost fixa.
- O ETL semanal e a CI existem, mas não possuem evidência suficiente de confiabilidade contínua.
- O hardening da Data API é local e ainda não foi aplicado ao ambiente remoto; a reconciliação do histórico remoto é pré-requisito para qualquer `db push`.

Consulte [`Spec.md`](Spec.md) para contratos, schema, métricas, decisões e roadmap completos.
