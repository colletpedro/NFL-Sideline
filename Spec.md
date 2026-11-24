# NFL Sideline — Especificação Técnica

**Versão documental:** 2.5

**Status:** protótipo funcional em estabilização

**Baseline documental:** pacote de consistência e observabilidade do ETL validado localmente em 2026-09-09, com rollout estático oficial confirmado em 2026-09-14.

**Estado do editorial:** caminho Gemini por claims v3 preservado; motor descritivo local por regras
implementado com claims descritivas v5 e execução offline auditável. A validação mecânica não comprova
qualidade editorial; a avaliação Gemini permanece separada e pendente. Não há novas aprovações ou
publicação decorrentes desta entrega.

**Autoridade:** esta especificação descreve o comportamento observado no código e no schema nessa baseline. Itens sem evidência são marcados como planejados, não comprovados ou pendentes.

## 1. Produto e posicionamento

NFL Sideline é uma plataforma de análise tática de confrontos da NFL. Seu objetivo primário é transformar dados semanais de eficiência em uma leitura clara de como o ataque aéreo e terrestre de cada time se contrapõe à defesa adversária.

Uma conclusão preditiva pode surgir naturalmente dessa análise e aparece hoje no campo `veredito`, mas é uma saída secundária. O produto ainda não possui um modelo quantitativo próprio de previsão, calibração ou backtest.

Odds, spreads, totais e probabilidades implícitas pertencem ao fluxo de mercado consultável, separado da geração tática. Encontrar assimetrias de mercado não é a tese central atual. As probabilidades exibidas vêm do mercado: a versão fair resulta da remoção proporcional da vig e a versão bruta inclui vig. A normalização não produz uma probabilidade verdadeira nem uma estimativa independente. Esta entrega não exibe indicador de confiança editorial ou vantagem de modelo. Na ausência de probabilidade válida, nenhum favorito ou percentual é mostrado. O caminho Gemini usa claims internas v3; o motor local por regras usa claims v5.

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
- Operação confiável e observada do ETL semanal.
- Alertas, retenção, dashboard operacional ou fechamento automático de runs presos em `RUNNING`.

## 2. Arquitetura implementada

```text
nflverse
  -> nflreadpy
  -> Parquet em etl-pipeline/data/raw/{schedules,pbp}/season=YYYY/
  -> run_pipeline.py
     -> seed_teams.py / load_games.py / load_metrics.py
  -> conexão psycopg2 direta
  -> Supabase PostgreSQL
  -> Spring Boot 3.3.5 / Java 21 / JPA
     -> API REST local -> Gemini (sob solicitação) + analysis_cache
     -> exportador batch read-only -> snapshots JSON públicos
  -> React 18 / TypeScript / Vite -> Production estática
```

O fluxo principal não passa por um data lake remoto. S3 existe como caminho opcional/legado: `run_local.py` envia schedules somente quando `--upload-s3` é informado; credenciais AWS isoladamente não provocam chamadas a boto3. Os loaders ativos leem Parquet local e gravam diretamente no Supabase.

### Production publicada

O rollout oficial está comprovado em 2026-09-14 no projeto Vercel `nfl-sideline`. As URLs canônicas `https://nfl-sideline.vercel.app/` e `https://nfl-sideline-git-main-colletpedros-projects.vercel.app/` servem o site React/Vite estático. Production lê somente `/data/manifest.json` e `/data/seasons/2026.json`; não hospeda Java, Cloud Run, `/api/v1`, Supabase ou Gemini.

O projeto Vercel temporário `web-ui` (`web-ui-khaki.vercel.app`) permanece preservado para segurança/rollback e não é canônico. No projeto oficial, `Root Directory = web-ui`; um deployment manual pela CLI deve ser iniciado na raiz do repositório, pois iniciá-lo dentro de `web-ui` faria a Vercel resolver incorretamente `web-ui/web-ui`.

O snapshot publicado é a temporada 2026 com 272 jogos nas semanas 1–18, 32 times, 112 jogos com mercado, 160 sem mercado, quatro métricas da semana 1 (LA, NE, SEA e SF), oito análises e dois jogos com placar completo: `NE 10 @ SEA 13` e `SF 27 @ LA 7`. O contrato de scores e o mercado opcional permanecem os descritos nesta especificação.

### 2.1 Responsabilidades

| Camada | Implementação atual | Responsabilidade |
|---|---|---|
| Origem | nflverse via `nflreadpy` | schedules, play-by-play e times |
| Dados brutos | Parquet local | interface entre download e cargas |
| ETL | Python 3.11+, Polars, psycopg2 | filtros, agregações, odds e upserts |
| Banco | Supabase/PostgreSQL | contrato relacional e cache |
| Backend | Java 21, Spring Boot 3.3.5, JPA | API local, domínio, Gemini sob solicitação e exportação batch |
| LLM | Gemini `gemini-3.1-pro-preview` | narrativa tática estruturada |
| Frontend | React 18, TypeScript, Vite | calendário e detalhe via API local ou snapshots em Production |

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
│   ├── run_pipeline.py
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
| `GEMINI_API_KEY` | somente para geração local | backend Gemini; não é exigida pelo batch |
| `PORT` | não (`8080`) | porta HTTP do Spring local |
| `APP_CORS_ALLOWED_ORIGINS` | não | origens locais explícitas da API |
| `VITE_API_BASE_URL` | não | override público somente para development/test local; ignorado em builds de produção e proibido em Preview/Production |
| `AWS_ACCESS_KEY_ID` | não | S3 legado via boto3, somente com `--upload-s3` |
| `AWS_SECRET_ACCESS_KEY` | não | S3 legado via boto3, somente com `--upload-s3` |
| `AWS_REGION` | não | S3 legado via boto3, somente com `--upload-s3` |

O bucket S3 é constante em `run_local.py`; `S3_BUCKET` não é lida do ambiente. `GEMINI_API_KEY_PROD` também não é consumida. Toda variável `VITE_*` é pública e incorporada ao bundle; senha PostgreSQL e chave Gemini nunca podem usar esse prefixo.

### 3.1 Política compartilhada de temporadas

`nfl_sideline_etl.seasons` é a única implementação da política usada pelas cinco CLIs e pelo workflow por meio dos defaults das CLIs:

- `--season YEAR` pode ser repetido; valores são deduplicados e ordenados;
- sem a opção, março a dezembro usa o ano corrente e janeiro/fevereiro usa o ano anterior;
- a função aceita uma data injetável para testes determinísticos;
- a faixa plausível é 1999 (início do PBP suportado pelo nflreadpy) até a temporada seguinte à corrente, permitindo schedules publicados antecipadamente;
- `--data-dir PATH` troca a raiz, cujo default permanece `etl-pipeline/data`.

## 4. Pipeline de dados

### 4.1 Ordem de preparação

1. Abrir e conferir a conexão PostgreSQL.
2. Inserir `RUNNING` em `ingestion_runs` e commitar.
3. Adquirir schedules e PBP, salvo com `--skip-acquire`.
4. Carregar/atualizar times.
5. Carregar games e `market_implied`.
6. Carregar métricas.
7. Registrar `SUCCEEDED` com as contagens finais.

A ordem é implementada diretamente por `run_pipeline.py`, sem subprocessos, e é obrigatória por causa das FKs de times e jogos. Os scripts individuais continuam funcionando como CLIs. Todos os loaders usam `INSERT ... ON CONFLICT DO UPDATE`.

Cada temporada é uma execução independente e sequencial. A política é fail-fast: qualquer exceção após a criação do run identifica a etapa, faz rollback aplicável, tenta registrar `FAILED` e é propagada; nenhuma temporada seguinte é iniciada. Se a própria gravação de `FAILED` falhar, o erro secundário é sanitizado no log e a exceção original permanece a exceção do pipeline.

`run_local.py` baixa schedules e PBP de cada temporada pedida. `--schedules-only` e `--pbp-only` selecionam uma fonte e são mutuamente exclusivos; schedules são obrigatórios salvo no segundo modo. Arquivos com zero linhas não contam como sucesso. `--allow-missing-pbp` é restrito a PBP vazio, temporada futura ou HTTP 404 de arquivo ainda não publicado. Timeout, DNS/conexão, HTTP 401/403, 429, 5xx, parsing e schema continuam fatais; schedules nunca recebem essa tolerância. S3 é estritamente opt-in por `--upload-s3` e preserva a chave legada de schedules. O orquestrador não oferece S3.

`run_pipeline.py --skip-acquire` não chama nflverse nem S3: exige schedules válidos da temporada no `--data-dir` e usa uma referência mínima de times derivada deles, preservando metadados ricos já existentes em conflitos. PBP ausente só é tolerado com `--allow-missing-pbp`; schema incompatível permanece fatal.

### 4.2 Schedules e mercado

`load_games.py` lê somente as partições pedidas e filtra explicitamente as temporadas selecionadas e os tipos `REG`, `POST`, `WC`, `DIV`, `CON` e `SB`. Se houver Parquets locais, mas nenhum da seleção, a carga falha de forma clara. Todo jogo estruturalmente válido é mantido, independentemente de odds. O loader grava:

- identidade, temporada, semana, tipo e data do jogo;
- times da casa e visitante;
- `home_score`, `away_score` e `result` fornecidos diretamente pelo schedule;
- `spread_line`, `total_line`, `home_moneyline` e `away_moneyline`;
- probabilidades brutas, fair e vig em `market_implied`.

`home_score`, `away_score` e `result` formam um snapshot atômico: devem ser todos nulos ou todos preenchidos. Valores preenchidos devem ser inteiros, scores não negativos e `result = home_score - away_score`, com empate representado por zero. Jogos futuros com o trio nulo são válidos. Não há derivação de `result` nem preenchimento de campo ausente; qualquer combinação parcial aborta antes do banco com `game_id`, sem serializar o registro completo.

No conflito, uma única condição — a presença de `EXCLUDED.home_score`, garantida pela validação all-or-none — controla os três campos: trio novo nulo preserva integralmente o resultado conhecido; trio novo completo o substitui integralmente. Assim, snapshots diferentes nunca são combinados. Todo upsert, inclusive idempotente, define `updated_at = now()`. Odds de spread/total, teto, superfície e indicador divisional continuam sem produtor.

Para moneyline americana `ml`:

```text
ml < 0: p_raw = |ml| / (|ml| + 100)
ml > 0: p_raw = 100 / (ml + 100)
overround = p_raw_home + p_raw_away
p_fair = p_raw / overround
vig_pct = overround - 1
```

A remoção de vig usa normalização proporcional. O loader rejeita moneyline zero, não inteira ou não finita, probabilidade fora de `(0, 1)`, vig menor ou igual a zero e soma fair divergente de 1 por mais de `1e-9`.

`market_implied` exige apenas as duas moneylines completas e válidas, nunca spread. O par é substituído atomicamente com seu mercado. Dados ausentes/parciais posteriores preservam o último par completo conhecido e não atualizam nem removem o mercado. Jogo novo sem par completo recebe `NULL/NULL` e nenhum `market_implied`. Cada spread/total não nulo atualiza sua linha; ausência preserva a linha anterior via `COALESCE`. Jogos e mercados são persistidos na mesma transação. Warnings de pares incompletos são agregados por temporada, sem log por jogo.

### 4.3 Métricas semanais

`load_metrics.py` seleciona explicitamente as partições e linhas das temporadas pedidas. Ausência de PBP ou de métricas elegíveis falha por padrão; `--allow-empty` a transforma em sucesso com warning. Schema incompatível é sempre erro e não é reclassificado como vazio permitido.

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
- campos adicionais de odds e ambiente de `games` não incluídos no upsert atual

#### Planejadas

- EPA em descidas iniciais com definição formal.
- Taxa de jogadas explosivas com limiares formalizados.
- Ajuste por força de adversário.
- Histórico e backtest para eventual modelo quantitativo próprio.

### 4.4 Contrato de `ingestion_runs`

Há uma linha por execução e por temporada. `week` é sempre NULL porque o pipeline reprocessa a temporada inteira. Os estados usados exatamente pelo código são `RUNNING`, `SUCCEEDED` e `FAILED`; este pacote não adiciona enum nem constraint.

- `rows_pbp`: altura do PBP bruto selecionado para a temporada, antes do filtro de jogadas válidas;
- `rows_games`: todos os jogos preparados REG/POST, inclusive sem odds, antes do upsert;
- `rows_market`: resumo retornado/logado pela etapa e pipeline, somente mercados calculados/upsertados nessa execução; não é nova coluna de `ingestion_runs`;
- `started_at`: `now()` do banco no insert inicial, commitado antes das etapas;
- `finished_at`: `now()` do banco no encerramento;
- `error_message`: NULL no sucesso; na falha contém etapa, classe e descrição sem quebras de linha, com credenciais redigidas e limite de 1.000 caracteres.

Linhas de mercado e métricas aparecem no log e no resultado interno tipado, sem novas colunas no schema. Idempotência não zera contagens: uma reexecução processa/upserta as mesmas linhas e cria outro run auditável. Ausência explicitamente permitida de PBP pode terminar em `SUCCEEDED` com `rows_pbp = 0`. Uma interrupção abrupta pode permanecer `RUNNING`, representando corretamente a falta de fechamento.

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

O aplicativo usa PostgreSQL diretamente: em desenvolvimento o frontend conversa com o Spring; em Production lê snapshots públicos. O Java e os loaders Python usam JDBC e psycopg2. Não há consumidor atual da Supabase Data API.

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
| `GET` | `/analysis/matchup/{gameId}` | retorna somente a análise cacheada mais recente, ou 404 |
| `POST` | `/analysis/matchup` | recebe `gameId`, `analysisType` (`matchup_full_v0` ou `matchup_basic_v0`), `asOfDate` UTC e `revisionKey`; rejeita tipo ou janela incompatível |

Não existe uma rota separada `/games/{gameId}/market`; o mercado vem no detalhe do jogo. Erros de parâmetros e recursos usam `ProblemDetail`; falhas de LLM tratadas pelo controller retornam 503. O `RestClient` do Gemini tem timeout explícito e erros sanitizados.

## 7. Análise Gemini e contrato JSON

O backend monta um `context_json` tático canônico v3 com jogo, cobertura de dados e evidências semanais
até três semanas elegíveis por time. Odds, spreads, totais, probabilidades e favorito não entram nesse contexto
nem no prompt; continuam nos fluxos de consulta e publicação de mercado. O hash SHA-256 inclui tipo, versão
do prompt/contrato (`editorial-claims-v3`), contexto, modelo, `asOfDate` e `revisionKey`; por isso um cache
v0/v2 não atende uma nova geração v3. Alterar somente mercado não altera contexto ou hash tático.

Cada evidência interna identifica time, métrica, temporada, semana, origem corrente/histórica, valor original,
unidade, volume quando pertinente e disponível, e chave de origem de `team_week_metrics`. O ID deriva da
chave da linha e da métrica, nunca da ordem. Janelas recentes derivadas preservam IDs de origem, semanas,
média, método e faixa semanal. Médias usam volumes pertinentes quando completos; passe/corrida usam média
das médias semanais explicitamente não ponderada. Volumes totais não substituem denominadores específicos. `ContextQuality`/`data_coverage`
mede cobertura: COMPLETE significa dados correntes dos dois times, não suficiência de amostra, confiança ou
qualidade preditiva. O catálogo de métricas e o contrato de claims constam em
`docs/analysis-claims-contract.md`.

O Gemini devolve somente `contract_version`, `thesis_team`, `verdict`, `claims` tipadas e referências em
`sections`. Claims permitidas são observação, comparação semanal, comparação de janelas recentes da mesma
métrica/temporada/origem/método, perfil ataque-defesa no mesmo fundamento e limitação factual. O servidor valida IDs, origem/período, time, métrica, predicado, ordem numérica e papéis editoriais,
então redige integralmente os quatro campos públicos `fator_chave`, `vantagem_tatica`, `alerta_vermelho` e
`veredito`. A API continua devolvendo esse JSON de quatro campos dentro de `markdownText`.

Uma oportunidade condicional relaciona ataque e defesa adversária no mesmo fundamento, com EPA ofensivo e
permitido positivos em cada semana observada e cobertura da métrica nas semanas representadas. Não exige
superioridade da defesa do próprio time nem transforma média positiva com semanas negativas em convergência.
O perfil descritivo permite inconclusivo; semanas diferentes são admitidas e explicitadas, sem inferir bye.
A regra de sinais é editorial, não calibrada nem relativa à média da liga. O alerta usa contraponto corrente
realmente contrário à tese ou limitação factual; o veredito preserva o contraponto. A realização textual fixa
impede que texto livre do modelo adicione fatos aos quatro campos.

### 7.1 Janelas temporais

- A API de times aceita `season`, `l4` e `l6`. `l4`/`l6` retornam as últimas quatro/seis semanas registradas na temporada solicitada, em ordem crescente.
- O contexto editorial inclui até três registros anteriores à week do jogo; métricas da própria rodada ou posteriores são excluídas.
- Se não houver métricas elegíveis na temporada do jogo, a forma recente usa a temporada anterior (`season - 1`) e a rotula como `HISTORICAL_REFERENCE`, nunca como momento atual. Com menos de três registros, usa os disponíveis.
- Na postseason, o schema atual não permite associar cada métrica a fase/data. O resolver de rodadas continua
  cronológico, mas o contexto não usa `metric.week < game.week` como prova: degrada para referência histórica
  com `POSTSEASON_METRIC_CUTOFF_UNVERIFIABLE` até que uma evolução de schema resolva o corte sem ambiguidade.
- O detalhe do jogo retorna a série semanal completa da temporada do jogo.

### 7.2 Garantias e limite da validação

A validação é determinística sobre evidências semanais, janelas derivadas e relações restritas; falha ou timeout não grava cache
utilizável. EPA usa sinal e três casas, taxas percentual com uma casa, em português. Uma ou duas partidas são
sempre descritas como desempenho observado, sem identidade duradoura. `response_text` persiste somente os
quatro textos; `context_json` e o hash/modelo ficam no cache interno. Claims, papéis, referências e o JSON
bruto do gerador são transitórios e não podem ser auditados retrospectivamente a partir de uma linha salva.
Esta garantia cobre a consistência mecânica dos textos renderizados, não a escolha editorial do Gemini nem a
veracidade da fonte. Testes offline com Gemini simulado não avaliam a qualidade comportamental do modelo real.

### 7.3 Motor descritivo local por regras

`ClaimSelector` separa seleção tipada de `ClaimValidator` e `ClaimRenderer`. O seletor
`local-descriptive-rules` 2.0.0 enumera simetricamente os seis encontros passe/corrida/jogada geral,
com dimensões separadas para padrões semanais do ataque, da defesa, relação entre eles e cobertura.
Distingue indicadores favoráveis ao ataque e à defesa, ataque sem produção positiva diante de defesa
que permitiu EPA positivo, variação semanal, zeros e convergência. Nenhuma categoria prevê exploração.

Recortes atuais, completos e comparáveis têm prioridade; fundamentos específicos adequados precedem
o panorama geral. Todos os empates são preservados, com números e períodos nos textos públicos.
Agregações, denominadores e limite de três registros permanecem. Claims próprias de limitação do
recorte substituem autorreferência como contraponto; vínculos distinguem evidência restritiva adicional
e oportunidade independente do adversário. Agrupamentos validados evitam repetir panorama redundante
sem omitir sinais distintos, particularmente do outro time. Política: `docs/local-rules-editorial.md`.

A saída interna v5 mantém `thesis_team=NONE`, `verdict=INCONCLUSIVE`: significa que esta análise
descritiva não estima o vencedor, **não** que o jogo seja equilibrado ou estatisticamente indecidível.
O renderer `controlled-claims-v5.0.2` preserva os quatro campos públicos; valores não zero que
arredondariam a zero são mostrados com desigualdade explícita, sem limiar de relevância prática.
Documentos v3/v4 mantêm interpretação e textos anteriores. O caminho Gemini continua restrito a v3.

`java -jar core-api/target/core-api-0.1.0.jar editorial-local <contexto-v3.json> <diretorio-novo>`
executa sem Spring, banco, rede, modelo ou revisão humana obrigatória. Os artefatos atuais v3 incluem contexto,
hashes, versões, candidatos, dimensões, decisões, groupings, claims, relações, textos e falhas
sanitizadas. As avaliações históricas preservam artefatos v2. Não grava cache nem snapshots. A interface permanece disponível para seletores futuros.

Os seis casos usados em 1.0.0, inclusive os antigos reservados, agora são **regressão conhecida**.
`scripts/compare_local_rules.py` compara todos com os artefatos 1.0.0 preservados; não seleciona por
resultado nem representa avaliação independente. Generalização/qualidade editorial continuam sem
comprovação, e a avaliação Gemini permanece separada.

## 8. Frontend

O React Router expõe `/` e `/game/:id`. O contexto de publicação fornece a temporada padrão de `manifest.defaultSeason` e a atualização de `manifest.generatedAt`. No REST, `/api/v1/publication` retorna a temporada NFL corrente e a última atualização dos jogos. Home, header e footer compartilham o contexto, sem constantes sazonais duplicadas. A semana inicial usa intervalos inclusivos de datas UTC: semana contendo hoje; entre semanas, a próxima; antes da temporada, a primeira; depois do último jogo, a última. O seletor manual é preservado. A escolha independe de mercado/análises.

O favorito de mercado exige probabilidade fair válida e desigual; empate fair não cria favorito. A UI identifica as probabilidades fair como probabilidades de mercado após remoção proporcional da vig e diferencia as probabilidades implícitas brutas com vig. Não há indicador de confiança editorial nem vantagem de modelo. Sem odds, os jogos permanecem navegáveis com mercado indisponível e análise cacheada independente. O detalhe carrega jogo e análise em paralelo e oferece abas de visão geral, análise, mercado e comparação tática. Na comparação tática, dropback rate aparece como frequência percentual, sem vencedor. Métricas estáticas pertencem somente à temporada exportada; ausência de PBP é apresentada honestamente, sem fallback de outra temporada. A geração Gemini usa o contrato interno v3; análises já cacheadas e aprovadas continuam legíveis.

`NflDataClient` unifica lista de jogos, detalhe e análise disponível. Development/test usa o Spring local e aceita `VITE_API_BASE_URL`; Production resolve em build um módulo separado que lê `/data/manifest.json` e `/data/seasons/{season}.json`. A seleção estática não pode ser desviada por variável Vite, mantém cache de requests em memória, usa somente GET e devolve erros incompatíveis sanitizados. `Home`, `Layout` e `MatchupDashboard` não conhecem Axios.

O detalhe estático monta times, mercado e séries de métricas em memória. Análise ausente é um estado válido e não dispara geração. Não existe Function Vercel nem rota catch-all de API. O Spring lê `PORT` e mantém CORS centralizado apenas para as origens locais configuradas.

O contrato completo de `schemaVersion: 1`, ordenação, atomicidade e campos públicos está em `docs/static-snapshot-contract.md`. O exportador usa três queries por temporada, não serializa entidades JPA e não instancia Gemini no perfil `snapshot`.

## 9. Infraestrutura e operação

| Componente | Estado comprovado |
|---|---|
| Supabase/PostgreSQL | ativo e usado pelas cargas e backend |
| Parquet local | fluxo ativo entre extração/download e loaders |
| S3 | código opcional/legado; não está no caminho principal ativo |
| GitHub Actions | `ci-java.yml` e `weekly_etl.yml` existem; confiabilidade contínua não comprovada |
| Cloud Run | fora do caminho público atual; Dockerfile preservado para usos locais/futuros separados |
| Vercel | Production oficial comprovada em 2026-09-14; build Vite estático com snapshots versionados e fallback SPA |
| Frontend/API | Production usa somente `/data`; API Spring permanece local |

O workflow semanal preserva `workflow_dispatch`, o cron e os pins existentes de `actions/checkout@v4` e `actions/setup-python@v5`. Ele instala `etl-pipeline` pelo `pyproject.toml` e executa somente `python etl-pipeline/run_pipeline.py --allow-missing-pbp`. A temporada corrente é resolvida pelo módulo compartilhado. A flag não mascara outage: apenas PBP vazio, futuro ou 404 ainda não publicado segue sem bloquear; qualquer outra falha tenta registrar `FAILED` e falha o job. Os três secrets PostgreSQL existentes continuam sendo os únicos secrets do job; S3 e Data API não participam. O YAML corrigido ainda não comprova confiabilidade contínua em produção.

### 9.1 Reprodutibilidade e validação do ETL

As dependências diretas validadas estão fixadas em versões exatas no `pyproject.toml`; o extra `test` contém pytest e Pandas. Os testes offline cobrem política/CLI de temporadas, retorno Polars/Pandas, paths, S3 opt-in, ausência de PBP, classificação de 404 versus falhas operacionais, filtros, schema, moneyline, scores/result, sanitização, persistência de runs, rollback, ordem/falhas do orquestrador, fail-fast, `--skip-acquire`, contagens e agregação mínima.

No mesmo dia, as duas migrations intactas foram reaplicadas no Supabase local e fixtures temporárias executaram o orquestrador: 2 times, 1 jogo, 1 mercado, 4 linhas brutas de PBP e 2 métricas. A segunda execução não duplicou entidades e criou outro run; `updated_at` avançou. A regressão para NULL preservou `27–20/result=7`, a correção não nula atualizou para `30–24/result=6` e uma inconsistência posterior gerou código não zero e `FAILED`, sem alterar o jogo válido. O diretório temporário foi removido ao fim. Nenhum banco remoto ou S3 participou.

## 10. Roadmap

1. **Estabilização e reprodutibilidade** — baseline de schema, configuração segura, documentação coerente e processo repetível de ambiente local/remoto.
2. **Consistência de dados e análise** — corrigir lacunas de placares/execuções, formalizar métricas, alinhar janelas e fortalecer o contrato da análise.
3. **Confiabilidade e testes** — ampliar cobertura de integração/contrato e observar execuções reais do workflow semanal agora autossuficiente.
4. **Automação da publicação estática** — automatizar a geração controlada dos snapshots, validar o artefato e publicar o build estático na Vercel sem servidor permanente. O rollout manual atual já está publicado, mas esse fluxo automático não existe.
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
| ADR-007 | Gemini escolhe claims táticas estruturadas | O Java valida as relações e redige os quatro textos públicos. |
| ADR-008 | Supabase migrations como fonte versionada do schema | Mudanças futuras devem evoluir a partir da baseline em `supabase/migrations/`. |
| ADR-009 | Substituído pelo ADR-010 | O proxy hospedado não possui consumidor no desenho estático. |
| ADR-010 | Java exporta snapshots públicos; Production é estática | Sem servidor permanente; regras BASIC/FULL do novo motor local ainda pendentes. |
| ADR-011 | Aceito: MLflow local (SQLite) como índice dos experimentos de ML, alimentado por importador só leitura | Sem servidor nem custo; stores e hashes seguem como fonte de verdade; plano em `docs/plans/mlflow-tracking-v1/`. |
| ADR-012 | Aceito: hub de modelos de ML em `research/model_hub/` (aquisição própria do nflverse, feature store, backtest walk-forward no MLflow, modelos sem pickle) | Vários modelos pelo mesmo caminho, sem tocar ETL nem produção; plano em docs/plans/model-hub-v1/. |

## 12. Riscos e pendências

- A cobertura Python inicial existe, mas ainda não abrange falhas transitórias reais do nflverse nem execuções hospedadas do cron.
- Rollout remoto da Data API concluído em 2026-09-08; futuras migrations e qualquer reativação da Data API exigem nova revisão de segurança. A baseline histórica não deve ser reexecutada.
- Workflow semanal estruturalmente autossuficiente, porém ainda sem histórico suficiente para comprovar confiabilidade contínua.
- Campos avançados sem produtor e temporadas futuras potencialmente sem PBP.
- `ingestion_runs` oferece auditoria básica, não observabilidade completa: não há alertas, retenção, dashboard nem tratamento automático de runs presos em `RUNNING`.
- Campo `markdownText` carrega JSON, criando um contrato nominalmente enganoso.
- O snapshot público atual contém 272 jogos, mas sua atualização continua manual: o workflow semanal não exporta nem versiona snapshots e não publica a Vercel. As regras BASIC/FULL do novo motor local ainda precisam de definição.

## 13. Glossário mínimo

- **EPA:** variação de pontos esperados produzida por uma jogada.
- **Success rate:** proporção de jogadas com EPA positivo.
- **Moneyline:** odd americana para vitória direta.
- **Vig/overround:** margem implícita no conjunto de odds.
- **Fair value:** probabilidade normalizada após remoção proporcional da vig; apresentada como probabilidade de mercado na UI.
- **RAG:** uso de dados recuperados do banco como contexto factual para a geração do Gemini.


### Revisão histórica de clareza e avaliação local

Renderer 5.0.1 explicita ataque e defesa adversária no veredito e descreve sinais semanais
sem inferir trajetória. Seletor 2.0.0 e contrato v5 não mudam; artefatos 5.0.0 e contratos anteriores
permanecem preservados. O censo, os denominadores e os comandos estão em [avaliação de cobertura](docs/coverage-clarity-evaluation.md).
O renderer atual 5.0.2 acrescenta a correção de apresentação das faixas; veja [estado consolidado](docs/current-state.md).

### Integração local restrita do motor por regras

A entrada explícita `editorial-local-serve` e a CLI `editorial-local` compartilham
`LocalGenerationService` 1.1.0. O servidor JDK usa somente loopback, catálogo local v3
validado na inicialização e tentativas imutáveis em arquivos internos (v4 com visual;
v3 preservado e usado quando o contexto não cabe no contrato visual).
Não inicializa Spring, datasource, JPA, Gemini ou exportador; não registra endpoints
no modo normal/snapshot. Seletor 2.0.0 e claims 5 permanecem iguais; renderer 5.0.2 corrige apenas
a composição das faixas com desigualdade, identificando mínimo e máximo.
Comandos, identidade e limites: [API editorial local](docs/local-editorial-api.md).
A baseline histórica foi arquivada antes das alterações; a implementação nova não
corresponde aos hashes históricos. Esta integração não aprova nem publica análises.

A validação operacional executou 75 requisições HTTP reais em loopback, com paridade CLI/API e
consulta após reinício nos 21 casos conhecidos. A página interna foi inspecionada em 1440/390 px,
com filtros e evidências expansíveis. Não há integração da API local ao frontend público.
Evidências e comandos: [relatório operacional](editorial/operational-validation-v1/REPORT.md).

### Interface editorial local de desenvolvimento

A entrada Vite separada `editorial:dev` conecta um laboratório em 127.0.0.1:18083 à API
de loopback em 18081, por proxy com Host/Origin/método/rota/body restritos. A API mantém
a rejeição de Origin e não oferece CORS. HTTP 1.2.0 mantém o catálogo de metadados e
histórico de tentativas completas verificado, e acrescenta consulta visual por tentativa.
A página gera apenas por ação explícita, preserva tentativas anteriores, prioriza os gráficos
e mantém os quatro textos acessíveis. Identifica resultados como locais, sem aprovação/publicação. Não define BASIC/FULL.
A entrada pública e o snapshot schemaVersion 1 permanecem inalterados. A configuração
editorial não admite build/production; o build público não inclui a interface nem seu cliente.
Contrato, limites das datas informadas e reprodução: [interface local](docs/local-editorial-ui.md).

### Contrato visual e laboratório local — E0 a E3

O [contrato visual interno v1](contracts/visual-analysis/v1/README.md) rege a projeção de evidências/claims validadas para cartões e gráficos locais. E2 persiste `insights.json` em artefatos v4 e oferece GET por tentativa; mantém leitura imutável de v3, cujo visual retorna 409. E3 consome esse envelope no laboratório de desenvolvimento, com gráficos principais e texto expansível. O contrato público de snapshots permanece em v1, sem esse documento interno. O visual aceita `REG`/`POST`; fases `WC`/`DIV`/`CON`/`SB` preservam geração textual v3, até revisão coordenada do enum. [Aceite operacional integrado](docs/plans/visual-v1/integration-report.md).

O primeiro experimento preserva seletor 2.0.0, claims v5 e renderer textual 5.0.2. Não prevê vencedor, não muda o ETL e não publica o documento interno como snapshot. Estado e coordenação: [preparação visual](docs/plans/visual-v1/README.md).
