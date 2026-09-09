# NFL Sideline — Especificação Técnica

**Versão documental:** 2.0

**Status:** protótipo funcional em estabilização

**Baseline documental:** 2026-09-08, commit `705536f`

**Autoridade:** esta especificação descreve o comportamento observado no código e no schema nessa baseline. Itens sem evidência são marcados como planejados, não comprovados ou pendentes.

## 1. Produto e posicionamento

NFL Sideline é uma plataforma de análise tática de confrontos da NFL. Seu objetivo primário é transformar dados semanais de eficiência em uma leitura clara de como o ataque aéreo e terrestre de cada time se contrapõe à defesa adversária.

Uma conclusão preditiva pode surgir naturalmente dessa análise e aparece hoje no campo `veredito`, mas é uma saída secundária. O produto ainda não possui um modelo quantitativo próprio de previsão, calibração ou backtest.

Odds, spreads, totais e probabilidades implícitas são contexto complementar. Encontrar assimetrias de mercado não é a tese central atual. Em particular, todas as probabilidades chamadas de **“Model”** na UI são probabilidades implícitas sem vig calculadas a partir das moneylines do mercado; elas não são estimativas de um modelo independente.

### 1.1 Escopo implementado

- Extração de schedules, play-by-play e referência de times via nflverse/`nflreadpy`.
- Persistência local dos dados brutos em Parquet.
- Cálculo semanal de EPA, success rate, volume e taxa de passes com Polars.
- Carga direta de times, jogos, probabilidades de mercado e métricas no PostgreSQL/Supabase.
- API REST Spring Boot para times, jogos, métricas e análise de confronto.
- Análise estruturada via Gemini, cacheada por hash SHA-256.
- Dashboard React/Vite para calendário, mercado, matchup e análise.

### 1.2 Não implementado ou não comprovado

- Modelo preditivo quantitativo independente, calibração ou backtest.
- Odds ao vivo, movimentação de linha, recomendação de aposta ou gestão de banca.
- Dados de tracking, lesões em tempo real ou charting proprietário.
- Autenticação, autorização e multi-tenancy.
- Deploy comprovado em Cloud Run ou Vercel.
- Operação confiável e observada do ETL semanal.

## 2. Arquitetura implementada

```text
nflverse
  -> nflreadpy
  -> Parquet em etl-pipeline/data/raw/{schedules,pbp}/season=YYYY/
  -> seed_teams.py / load_games.py / load_metrics.py
  -> conexão psycopg2 direta
  -> Supabase PostgreSQL
  -> Spring Boot 3.3.5 / Java 21 / JPA
  -> Gemini (análise) + analysis_cache
  -> React 18 / TypeScript / Vite
```

O fluxo principal não passa por um data lake remoto. S3 existe como caminho opcional/legado: `run_local.py` pode enviar o Parquet de schedules de 2023 quando as credenciais AWS estão presentes, por meio de `src/nfl_sideline_etl/load.py`. Os loaders ativos leem Parquet local e gravam diretamente no Supabase.

### 2.1 Responsabilidades

| Camada | Implementação atual | Responsabilidade |
|---|---|---|
| Origem | nflverse via `nflreadpy` | schedules, play-by-play e times |
| Dados brutos | Parquet local | interface entre download e cargas |
| ETL | Python 3.11+, Polars, psycopg2 | filtros, agregações, odds e upserts |
| Banco | Supabase/PostgreSQL | contrato relacional e cache |
| Backend | Java 21, Spring Boot 3.3.5, JPA | leitura, janelas, contexto e Gemini |
| LLM | Gemini `gemini-3.1-pro-preview` | narrativa tática estruturada |
| Frontend | React 18, TypeScript, Vite | calendário e detalhe do matchup |

### 2.2 Estrutura real do monorepo

```text
NFL Sideline/
├── .github/workflows/
│   ├── ci-java.yml
│   └── weekly_etl.yml
├── core-api/
│   ├── src/main/java/com/nflsideline/coreapi/
│   │   ├── controller/
│   │   ├── domain/
│   │   ├── llm/
│   │   ├── repository/
│   │   └── service/
│   ├── src/main/resources/application.yml
│   ├── Dockerfile
│   └── pom.xml
├── etl-pipeline/
│   ├── src/nfl_sideline_etl/{extract.py,load.py}
│   ├── load_games.py
│   ├── load_metrics.py
│   ├── run_local.py
│   ├── seed_teams.py
│   └── pyproject.toml
├── supabase/
│   ├── config.toml
│   └── migrations/
│       └── *_baseline_schema.sql
├── web-ui/
│   ├── src/{components,pages,services}/
│   ├── package.json
│   └── vercel.json
├── .env.example
├── README.md
└── Spec.md
```

## 3. Configuração e variáveis de ambiente

Variáveis efetivamente consumidas:

| Variável | Obrigatória | Consumidor |
|---|---:|---|
| `SUPABASE_DB_URL` | sim | Spring datasource e loaders Python |
| `SUPABASE_DB_USER` | sim | Spring datasource e loaders Python |
| `SUPABASE_DB_PASSWORD` | sim | Spring datasource e loaders Python |
| `GEMINI_API_KEY` | sim | backend Gemini |
| `AWS_ACCESS_KEY_ID` | não | S3 legado via boto3 |
| `AWS_SECRET_ACCESS_KEY` | não | S3 legado via boto3 |
| `AWS_REGION` | não | S3 legado via boto3 |

O bucket S3 é constante em `run_local.py`; `S3_BUCKET` não é lida do ambiente. `GEMINI_API_KEY_PROD` também não é consumida. O frontend não lê uma variável `VITE_*`: a base URL está fixa em localhost.

## 4. Pipeline de dados

### 4.1 Ordem de preparação

1. Criar um banco vazio usando a migration baseline.
2. Disponibilizar os Parquet no layout local.
3. Executar `seed_teams.py`.
4. Executar `load_games.py`, que também popula `market_implied`.
5. Executar `load_metrics.py`.
6. Iniciar backend e frontend.

A ordem dos loaders é obrigatória por causa das FKs de times e jogos. Todos os loaders usam `INSERT ... ON CONFLICT DO UPDATE`.

### 4.2 Schedules e mercado

`load_games.py` lê todos os `schedules.parquet`, mas filtra as temporadas constantes `(2025, 2026)` e os tipos `REG`, `POST`, `WC`, `DIV`, `CON` e `SB`. Jogos sem moneylines de casa/fora ou sem spread são descartados. O loader atual grava somente:

- identidade, temporada, semana, tipo e data do jogo;
- times da casa e visitante;
- `spread_line`, `total_line`, `home_moneyline` e `away_moneyline`;
- probabilidades brutas, fair e vig em `market_implied`.

Ele não grava placares, resultado, odds de spread, odds de total, teto, superfície ou indicador divisional, embora essas colunas existam no contrato.

Para moneyline americana `ml`:

```text
ml < 0: p_raw = |ml| / (|ml| + 100)
ml > 0: p_raw = 100 / (ml + 100)
overround = p_raw_home + p_raw_away
p_fair = p_raw / overround
vig_pct = overround - 1
```

A remoção de vig usa normalização proporcional. O loader rejeita moneyline zero, probabilidade fora de `(0, 1)`, vig menor ou igual a zero e soma fair divergente de 1 por mais de `1e-9`.

### 4.3 Métricas semanais

Antes da agregação, `load_metrics.py` mantém apenas jogadas com:

- `epa` não nulo;
- `play_type` igual a `pass` ou `run`;
- `qb_kneel` e `qb_spike` iguais a zero após preenchimento de nulos;
- `posteam` e `defteam` presentes.

#### Implementadas e populadas

| Coluna | Definição no código |
|---|---|
| `off_epa_play` | média de EPA das jogadas válidas agrupadas por ataque/time/semana |
| `def_epa_play` | média do EPA produzido pelo adversário nas jogadas válidas agrupadas por defesa |
| `off_epa_pass`, `off_epa_rush` | média ofensiva de EPA filtrada por passe/corrida |
| `def_epa_pass`, `def_epa_rush` | média do EPA adversário filtrada por passe/corrida |
| `off_success_rate` | média do indicador `epa > 0` no ataque |
| `def_success_rate` | média do indicador `epa > 0` concedido pela defesa |
| `plays_offense`, `plays_defense` | contagem de jogadas válidas |
| `dropback_rate` | média de `play_type == pass`, isto é, passes divididos por passes + corridas em todas as jogadas válidas |

`dropback_rate` não usa `wp`, neutral game script, sacks ou um indicador nflverse de dropback. O nome representa, na implementação atual, a proporção simples de jogadas classificadas como passe.

#### Presentes no schema, mas não populadas

- `early_down_epa`
- `explosive_play_rate`
- `games.home_score`, `games.away_score` e `games.result`
- `ingestion_runs` inteira
- campos adicionais de odds e ambiente de `games` não incluídos no upsert atual

#### Planejadas

- EPA em descidas iniciais com definição formal.
- Taxa de jogadas explosivas com limiares formalizados.
- Ajuste por força de adversário.
- Histórico e backtest para eventual modelo quantitativo próprio.

## 5. Schema PostgreSQL/Supabase

A fonte versionada do schema a partir desta baseline é `supabase/migrations/*_baseline_schema.sql`. O DDL foi cruzado com as entidades JPA, os SQLs dos loaders e introspecção read-only do banco em 2026-09-08.

O ambiente local usa `supabase/config.toml`, gerado com os defaults da Supabase CLI 2.117.0 e versionado sem vínculo ou credenciais remotas. A versão validada da CLI para esta baseline é `2.117.0`.

Em 2026-09-08, `supabase db reset --local` executou a baseline com sucesso em um stack Supabase local vazio. Não foi necessária correção no DDL: as seis tabelas foram criadas sem dados, e as consultas de introspecção confirmaram colunas, nullability, defaults, sequences, PKs, FKs e a unique do cache. A ausência de `supabase/seed.sql` gerou somente um aviso e não impediu o reset.

| Tabela | Contrato |
|---|---|
| `teams` | `team_abbr text` PK; `team_name text` obrigatório; `conference`, `division`, `logo_url` opcionais |
| `games` | `game_id text` PK; `season`, `week`, `game_type` obrigatórios; data, times, placares, linhas, odds e ambiente opcionais; `updated_at timestamptz not null default now()`; FKs `home_team`/`away_team` para `teams` |
| `team_week_metrics` | PK composta `(season, week, team_abbr)`; FK de time; métricas `numeric`; volumes `integer` |
| `market_implied` | `game_id text` como PK e FK para `games`; probabilidades/vig `numeric`; `computed_at timestamptz not null default now()` |
| `analysis_cache` | `id bigserial` PK; FK opcional `game_id`; `analysis_type`, `prompt_hash`, `context_json jsonb`, `response_text`, `model_name` obrigatórios; `created_at timestamptz not null default now()`; unique `(game_id, analysis_type, prompt_hash)` |
| `ingestion_runs` | `id bigserial` PK; `status` e `started_at timestamptz` obrigatórios; demais campos opcionais |

Os únicos índices observados são os criados pelas PKs e pela constraint única do cache. Esta baseline não adiciona índices de otimização.

### 5.1 RLS e Data API

O aplicativo usa PostgreSQL diretamente: o frontend conversa somente com o backend Spring, enquanto o backend usa JDBC e os loaders Python usam psycopg2. Não há consumidor atual da Supabase Data API.

A migration `*_harden_data_api_access.sql` habilita RLS, sem `FORCE ROW LEVEL SECURITY`, nas seis tabelas da aplicação e não cria policies. Ela revoga todos os privilégios de tabela e das sequences da aplicação para `anon`, `authenticated` e `PUBLIC`, preservando explicitamente todos os privilégios de `service_role` nos objetos atuais. Também revoga os default privileges de `postgres` para tabelas, sequences e funções futuras; em funções, a revogação é global ao criador para substituir o `EXECUTE` implícito de `PUBLIC`. Até `service_role` exige GRANT explícito para objetos novos criados por `postgres`; objetos criados por outra role exigem auditoria e decisão separada. O `config.toml` local define `auto_expose_new_tables = false` e desativa a Data API local (`[api].enabled = false`), sem desativar PostgreSQL. RLS e revogações permanecem como defesa em profundidade caso a Data API seja reativada. Qualquer uso futuro da Data API exige decisão arquitetural, grants explícitos, policies e novos testes. `service_role` é uma credencial privilegiada exclusivamente server-side e jamais pode ser exposta no frontend.

O rollout remoto foi concluído em 2026-09-08. A baseline foi reconciliada apenas no histórico remoto, a migration de hardening foi aplicada e o proprietário confirmou no Dashboard que **Enable Data API** está desativado. REST e GraphQL não expõem a aplicação; JDBC e psycopg2 continuam sendo os únicos caminhos de acesso. As seis tabelas remotas têm RLS habilitado sem policies, `anon`, `authenticated` e `PUBLIC` não possuem acesso e `service_role` mantém grants explícitos somente nos objetos atuais. Defaults residuais de `supabase_admin` continuam gerenciados pela plataforma e não foram alterados. Reativar a Data API exige nova revisão de grants, default ACLs, funções, policies e consumidores. Migrations futuras devem seguir exclusivamente o fluxo versionado; a baseline existente não deve ser executada novamente. O procedimento reutilizável e o registro de execução estão em `docs/runbooks/supabase-remote-hardening.md`.

## 6. API REST implementada

Base: `/api/v1`.

| Método | Rota | Contrato atual |
|---|---|---|
| `GET` | `/health` | retorna `{ "status": "UP" }` |
| `GET` | `/teams` | lista times |
| `GET` | `/teams/{abbr}/metrics?season=&window=` | métricas do time; `window=season`, `l4` ou `l6` |
| `GET` | `/games?season=&week=` | lista jogos; `week` é opcional |
| `GET` | `/games/{gameId}` | retorna `game`, `market`, `homeMetrics` e `awayMetrics` |
| `POST` | `/analysis/matchup` | recebe `{ "gameId": "...", "analysisType": "matchup" }` |

Não existe uma rota separada `/games/{gameId}/market`; o mercado vem no detalhe do jogo. Erros de parâmetros e recursos usam `ProblemDetail`; falhas de LLM tratadas pelo controller retornam 503. Não há timeout explícito configurado no `RestClient` do Gemini.

## 7. Análise Gemini e contrato JSON

O backend monta `context_json` com jogo, odds, mercado, séries semanais dos dois times e forma recente. O prompt completo é hashado com SHA-256; `(game_id, analysis_type, prompt_hash)` identifica o cache.

O Gemini deve devolver um objeto JSON com:

```json
{
  "fator_chave": "texto",
  "vantagem_tatica": "texto",
  "alerta_vermelho": "texto",
  "veredito": "texto",
  "metricas_citadas": {
    "nome_interno": 0.0
  }
}
```

Os quatro primeiros campos, todos não vazios, formam o contrato entregue à UI. `metricas_citadas` é usada internamente durante a validação e é removida antes de salvar `response_text`. A API ainda devolve esse JSON serializado dentro do campo legado `markdownText`; o frontend executa `JSON.parse`.

### 7.1 Janelas temporais

- A API de times aceita `season`, `l4` e `l6`. `l4`/`l6` retornam as últimas quatro/seis semanas registradas na temporada solicitada, em ordem crescente.
- O contexto do Gemini inclui `recent_form_last_3_weeks`, com até três registros mais recentes.
- Se não houver métricas na temporada do jogo, a forma recente usa a temporada anterior (`season - 1`). Com menos de três registros, usa os disponíveis.
- O detalhe do jogo retorna a série semanal completa da temporada do jogo.

### 7.2 Limite real da validação anti-alucinação

`validateCitedNumbers` coleta todos os números de `context_json` e valida, com tolerância `0.01`, somente valores numéricos presentes no objeto raiz `metricas_citadas`. Se esse objeto estiver ausente, não for objeto, contiver valores não numéricos ou se um número aparecer apenas nos textos finais sem ser repetido em `metricas_citadas`, esse número não é validado.

Portanto, a implementação reduz um tipo de alucinação numérica, mas não garante que todos os números de `fator_chave`, `vantagem_tatica`, `alerta_vermelho` e `veredito` pertençam ao contexto.

## 8. Frontend

O React Router expõe `/` e `/game/:id`. A home usa a temporada 2026 fixa, carrega jogos e calcula favoritos, confiança e “edge” a partir do fair value de mercado. O detalhe carrega jogo e análise em paralelo e oferece abas de visão geral, análise, mercado e comparação tática.

`web-ui/src/services/api.ts` usa `http://localhost:8080/api/v1` de forma fixa. Não há configuração de endpoint para deploy. A terminologia visual “Model” permanece por compatibilidade, mas sua semântica nesta baseline é sempre probabilidade implícita sem vig derivada do mercado.

## 9. Infraestrutura e operação

| Componente | Estado comprovado |
|---|---|
| Supabase/PostgreSQL | ativo e usado pelas cargas e backend |
| Parquet local | fluxo ativo entre extração/download e loaders |
| S3 | código opcional/legado; não está no caminho principal ativo |
| GitHub Actions | `ci-java.yml` e `weekly_etl.yml` existem; confiabilidade contínua não comprovada |
| Cloud Run | Dockerfile existe; deploy não comprovado |
| Vercel | configuração SPA existe; deploy não comprovado |
| Frontend/API | endpoint de API ainda fixo em localhost |

O workflow semanal baixa a temporada corrente e executa `load_games.py` e `load_metrics.py`. Ele não executa `seed_teams.py`, não registra `ingestion_runs`, depende de PBP local disponível e convive com a lista fixa de temporadas em `load_games.py`. Esses pontos impedem afirmar que o cron é autossuficiente ou confiável.

## 10. Roadmap

1. **Estabilização e reprodutibilidade** — baseline de schema, configuração segura, documentação coerente e processo repetível de ambiente local/remoto.
2. **Consistência de dados e análise** — corrigir lacunas de placares/execuções, formalizar métricas, alinhar janelas e fortalecer o contrato da análise.
3. **Confiabilidade e testes** — testes unitários, de contrato, integração e ETL; workflow semanal autossuficiente e observável.
4. **Deploy** — endpoint configurável, segurança de acesso, ambientes, Cloud Run/Vercel ou alvos equivalentes e validação ponta a ponta.
5. **Evolução analítica/preditiva** — métricas avançadas, ajuste por adversário, dataset de avaliação, backtest e eventual modelo quantitativo próprio.

Nenhuma etapa posterior é considerada concluída apenas pela presença de código ou configuração.

## 11. ADR log

| ID | Decisão vigente | Consequência |
|---|---|---|
| ADR-001 | Monorepo único | ETL, API, UI, workflows e schema evoluem no mesmo repositório. |
| ADR-002 | Produto **tactical-first** | A explicação do confronto é o objetivo principal. |
| ADR-003 | Previsão como saída secundária | `veredito` pode projetar o jogo, sem alegar modelo quantitativo próprio. |
| ADR-004 | Mercado como contexto complementar | Odds e fair value apoiam a leitura, mas não definem a tese central. |
| ADR-005 | nflverse/`nflreadpy`, Polars e Parquet local | Este é o fluxo de ingestão implementado. |
| ADR-006 | Carga direta no Supabase | Os loaders atuais escrevem diretamente no PostgreSQL; S3 é opcional/legado. |
| ADR-007 | Gemini para narrativa tática estruturada | O LLM recebe somente o contexto serializado e responde em JSON. |
| ADR-008 | Supabase migrations como fonte versionada do schema | Mudanças futuras devem evoluir a partir da baseline em `supabase/migrations/`. |

## 12. Riscos e pendências

- Ausência de testes de negócio e integração nas três camadas.
- Rollout remoto da Data API concluído em 2026-09-08; futuras migrations e qualquer reativação da Data API exigem nova revisão de segurança. A baseline histórica não deve ser reexecutada.
- Workflow semanal não comprovadamente autossuficiente.
- Colunas contratuais sem produtor atual e dados futuros sem PBP.
- Campo `markdownText` carrega JSON, criando um contrato nominalmente enganoso.
- Hash do cache não inclui explicitamente o nome do modelo.
- Cliente Gemini sem timeout explícito.
- CORS aberto nos controllers de domínio.
- URL localhost e temporada 2026 fixas no frontend.

## 13. Glossário mínimo

- **EPA:** variação de pontos esperados produzida por uma jogada.
- **Success rate:** proporção de jogadas com EPA positivo.
- **Moneyline:** odd americana para vitória direta.
- **Vig/overround:** margem implícita no conjunto de odds.
- **Fair value:** probabilidade normalizada após remoção proporcional da vig; nesta baseline, é a “Model Probability” da UI.
- **RAG:** uso de dados recuperados do banco como contexto factual para a geração do Gemini.
