# NFL Sideline — Technical Specification

**Versão:** 1.0
**Status:** Fase 1 (ETL local)
**Última atualização:** 2026-09-03
**Fonte única da verdade.** Nenhuma decisão arquitetural vale se não estiver aqui.

---

## 1. Visão Geral

NFL Sideline é uma plataforma autônoma de *sports analytics* que extrai dados semanais da NFL, calcula métricas quantitativas avançadas (foco em EPA — Expected Points Added), compara o desempenho medido contra o preço implícito do mercado de apostas e orquestra prompts para um LLM gerar relatórios táticos e de *scouting*.

O sistema roda 100% em nuvem, em camadas gratuitas, sem depender de hardware local ligado.

**Tese central do produto:** o mercado de apostas precifica narrativa e placar; EPA mede eficiência real. Onde os dois divergem existe assimetria. O sistema mede a divergência com código determinístico e usa o LLM apenas para *narrar* essa divergência — nunca para calculá-la.

---

## 2. Escopo

### 2.1 Dentro do escopo (v1)

- Ingestão semanal automatizada de play-by-play, schedules e rosters da NFL via nflverse.
- Cálculo de métricas de eficiência por time e por semana (EPA e derivados).
- Extração de linhas de mercado (moneyline, spread, total) nativas do dataset de schedules.
- Conversão de odds em probabilidade implícita com remoção de vig.
- API REST que serve métricas consolidadas e análises geradas por LLM.
- Dashboard web com séries temporais de métricas e leitura de confrontos.

### 2.2 Fora do escopo (não-objetivos explícitos)

- **Odds ao vivo / line movement em tempo real.** Os dados do nflverse são atualizados em lote e refletem linhas de fechamento. O sistema é de análise retrospectiva e pré-jogo com linha estática, não de *live betting*.
- **Execução ou recomendação de apostas.** O sistema descreve assimetria; não emite ordem, stake ou gestão de banca.
- **Dados de tracking (Next Gen Stats posicionais), charting proprietário pago e dados de lesão em tempo real.**
- **Autenticação de usuários e multi-tenancy** na v1. Aplicação pública, somente leitura.
- **Treino de modelos preditivos próprios.** A v1 usa métricas descritivas e baseline de mercado. Modelagem preditiva é candidata a v2.

---

## 3. Decisões Arquiteturais (ADR Log)

Decisões fechadas. Alterar qualquer uma exige atualizar este arquivo primeiro.

| ID | Decisão | Justificativa | Alternativa descartada |
|---|---|---|---|
| ADR-001 | **Monorepo único** (`nfl-sideline`) | Projeto solo. Três repositórios triplicam overhead de CI, versionamento e sincronização de contratos sem ganho real de isolamento. | Três repos separados por microsserviço. |
| ADR-002 | **Gemini como único motor cognitivo** | Reduz superfície de integração, custo e complexidade de prompt. Uma abstração `LLMProvider` mantém a porta aberta para trocar depois. | Benchmark obrigatório contra OpenAI. |
| ADR-003 | **`nflreadpy` como biblioteca de ingestão** | `nfl_read_py` está abandonado; `nfl_data_py` foi descontinuado e arquivado em set/2025. `nflreadpy` é o port oficial mantido do `nflreadr`. | `nfl_data_py`, `nfl_read_py`. |
| ADR-004 | **Odds nativas do nflverse** | `load_schedules()` já entrega moneyline, spread e total com odds de ambos os lados. Zero dependência de API paga ou scraping. | Odds API externa (The Odds API, scraping de sportsbook). |
| ADR-005 | **Polars como DataFrame primário no ETL** | `nflreadpy` retorna Polars nativamente. Converter tudo para pandas adiciona cópia de memória sem ganho. `.to_pandas()` fica disponível como escape hatch pontual. | pandas em toda a camada. |
| ADR-006 | **Parquet como formato do data lake** | Colunar, comprimido, tipado. Play-by-play tem ~400 colunas e centenas de milhares de linhas por temporada — CSV é inviável em custo de leitura. | CSV. |
| ADR-007 | **Amazon S3 como Data Lake (substituindo GCS)** | Validação sem atrito de conta e camada Always Free de 5GB. | Google Cloud Storage. |

---

## 4. Stack Tecnológica

| Camada | Tecnologia | Função | Hospedagem |
|---|---|---|---|
| ETL & Ingestão | Python 3.11+, `nflreadpy`, Polars | Extrair play-by-play e schedules, calcular EPA agregado, exportar Parquet | GitHub Actions (cron) |
| Data Lake | Amazon S3 | Armazenar Parquet bruto e processado | AWS |
| Banco relacional | PostgreSQL | Métricas consolidadas, metadados, cache de análises | Supabase |
| Backend Core | Java 21, Spring Boot 3 | Regras de negócio, REST API, orquestração RAG | Google Cloud Run (Docker) |
| Motor cognitivo | Gemini API | Gerar narrativa tática a partir de contexto numérico injetado | Google AI Studio |
| Frontend | React 18 + TypeScript, Recharts | Dashboards e visualização de séries temporais | Vercel |

**Restrição transversal:** todos os serviços devem operar dentro das camadas gratuitas. Cloud Run com `min-instances=0` (custo zero ocioso, cold start aceito).

---

## 5. Estrutura do Monorepo

```
nfl-sideline/
├── etl-pipeline/
│   ├── src/nfl_sideline_etl/
│   │   ├── extract.py          # wrappers nflreadpy (pbp, schedules, rosters)
│   │   ├── transform.py        # agregações EPA, success rate, janelas móveis
│   │   ├── market.py           # odds → probabilidade implícita, remoção de vig
│   │   ├── load.py             # escrita local e upload S3
│   │   └── config.py           # temporadas, caminhos, env vars
│   ├── tests/
│   └── pyproject.toml
├── core-api/                   # Java 21 / Spring Boot 3
│   ├── src/main/java/.../
│   │   ├── controller/
│   │   ├── service/
│   │   ├── repository/
│   │   ├── domain/
│   │   └── llm/                # abstração LLMProvider + GeminiClient
│   ├── src/test/java/
│   └── Dockerfile
├── web-app/                    # React 18 + TypeScript
│   ├── src/
│   └── package.json
├── docs/
│   ├── adr/                    # ADRs numerados, um arquivo por decisão
│   └── data-dictionary.md
├── .github/workflows/
│   ├── etl-weekly.yml
│   ├── ci-python.yml
│   ├── ci-java.yml
│   └── ci-web.yml
└── spec.md
```

---

## 6. Modelo de Dados

### 6.1 Layout do S3

```
s3://nfl-sideline-lake/
├── raw/
│   ├── pbp/season={YYYY}/pbp.parquet
│   ├── schedules/season={YYYY}/schedules.parquet
│   └── rosters/season={YYYY}/rosters.parquet
└── processed/
    ├── team_week_metrics/season={YYYY}/week={WW}/metrics.parquet
    └── market_snapshot/season={YYYY}/week={WW}/market.parquet
```

Escrita idempotente: reprocessar a mesma semana sobrescreve o mesmo caminho. Nunca acumular versões sufixadas por timestamp.

### 6.2 Schema PostgreSQL

```sql
teams (
  team_abbr        TEXT PRIMARY KEY,
  team_name        TEXT NOT NULL,
  conference       TEXT,
  division         TEXT,
  logo_url         TEXT
)

games (
  game_id          TEXT PRIMARY KEY,      -- formato nflverse: 2026_01_KC_BAL
  season           INT  NOT NULL,
  week             INT  NOT NULL,
  game_type        TEXT NOT NULL,         -- REG | POST
  gameday          DATE,
  home_team        TEXT REFERENCES teams,
  away_team        TEXT REFERENCES teams,
  home_score       INT,                   -- NULL se não jogado
  away_score       INT,
  result           INT,                   -- home_score - away_score
  spread_line      NUMERIC,               -- positivo = mandante favorito
  total_line       NUMERIC,
  home_moneyline   INT,
  away_moneyline   INT,
  home_spread_odds INT,
  away_spread_odds INT,
  over_odds        INT,
  under_odds       INT,
  roof             TEXT,
  surface          TEXT,
  div_game         BOOLEAN,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
)

team_week_metrics (
  season               INT  NOT NULL,
  week                 INT  NOT NULL,
  team_abbr            TEXT NOT NULL REFERENCES teams,
  off_epa_play         NUMERIC,
  def_epa_play         NUMERIC,
  off_epa_pass         NUMERIC,
  off_epa_rush         NUMERIC,
  def_epa_pass         NUMERIC,
  def_epa_rush         NUMERIC,
  off_success_rate     NUMERIC,
  def_success_rate     NUMERIC,
  early_down_epa       NUMERIC,
  dropback_rate        NUMERIC,
  explosive_play_rate  NUMERIC,
  plays_offense        INT,
  plays_defense        INT,
  PRIMARY KEY (season, week, team_abbr)
)

market_implied (
  game_id            TEXT PRIMARY KEY REFERENCES games,
  home_implied_raw   NUMERIC,   -- com vig
  away_implied_raw   NUMERIC,
  home_implied_fair  NUMERIC,   -- vig removido, soma = 1
  away_implied_fair  NUMERIC,
  vig_pct            NUMERIC,
  computed_at        TIMESTAMPTZ NOT NULL DEFAULT now()
)

analysis_cache (
  id            BIGSERIAL PRIMARY KEY,
  game_id       TEXT REFERENCES games,
  analysis_type TEXT NOT NULL,
  prompt_hash   TEXT NOT NULL,       -- SHA-256 do prompt completo
  context_json  JSONB NOT NULL,      -- números exatos injetados
  response_text TEXT NOT NULL,
  model_name    TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (game_id, analysis_type, prompt_hash)
)

ingestion_runs (
  id            BIGSERIAL PRIMARY KEY,
  season        INT,
  week          INT,
  status        TEXT NOT NULL,       -- SUCCESS | PARTIAL | FAILED
  rows_pbp      INT,
  rows_games    INT,
  error_message TEXT,
  started_at    TIMESTAMPTZ NOT NULL,
  finished_at   TIMESTAMPTZ
)
```

`analysis_cache` com `prompt_hash` no índice único garante que contexto idêntico não gasta chamada de LLM. Contexto diferente gera hash diferente e força regeração.

---

## 7. Definição das Métricas

Todas as métricas são calculadas em Python, no ETL. **O backend nunca calcula métrica; apenas lê e serve.**

| Métrica | Definição operacional |
|---|---|
| `off_epa_play` | Média de `epa` nas jogadas com `posteam = time`, filtrando `play_type in (pass, run)` e `epa` não nulo. |
| `def_epa_play` | Média de `epa` nas jogadas com `defteam = time`. Valor menor é melhor. |
| `off_success_rate` | Proporção de jogadas ofensivas com `epa > 0`. |
| `early_down_epa` | `off_epa_play` restrito a `down in (1, 2)`. Menos ruidoso que EPA total, estabiliza mais rápido. |
| `dropback_rate` | Proporção de dropbacks sobre jogadas totais em situação neutra (`wp` entre 0.20 e 0.80). |
| `explosive_play_rate` | Proporção de jogadas com ganho ≥ 20 jardas (passe) ou ≥ 10 jardas (corrida). |
| Janela móvel | Toda métrica é exposta em três janelas: temporada completa, últimas 4 semanas, últimas 6 semanas. |

**Filtros obrigatórios** aplicados antes de qualquer agregação: excluir jogadas de tempo esgotado, penalidades sem jogada, kneel downs e spikes. Documentar o filtro exato em `docs/data-dictionary.md`.

### 7.1 Probabilidade implícita e vig

```
Se moneyline < 0:  p_raw = (-ml) / ((-ml) + 100)
Se moneyline > 0:  p_raw = 100 / (ml + 100)

overround = p_raw_home + p_raw_away
p_fair    = p_raw / overround
vig_pct   = overround - 1
```

Método de remoção de vig: **normalização proporcional**. É o mais simples e o menos correto em favoritos extremos. Documentar essa limitação; não trocar por shin ou power method sem ADR.

---

## 8. Contrato da API

Base: `/api/v1`

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Liveness e versão do build. |
| GET | `/teams` | Lista de times. |
| GET | `/teams/{abbr}/metrics?season=&window=` | Série temporal de métricas do time. `window ∈ {season, l4, l6}`. |
| GET | `/games?season=&week=` | Jogos da semana com linhas de mercado. |
| GET | `/games/{gameId}` | Detalhe do jogo com métricas de ambos os times. |
| GET | `/games/{gameId}/market` | Probabilidades implícitas bruta e fair, vig. |
| POST | `/analysis/matchup` | Corpo: `{ gameId, analysisType }`. Dispara pipeline RAG. Retorna do cache quando o hash bate. |

Erros seguem RFC 7807 (`application/problem+json`). Timeout de chamada ao Gemini: 30s. Falha de LLM retorna 503 com os números crus disponíveis — **a API nunca degrada silenciosamente para uma resposta inventada**.

---

## 9. Pipeline RAG e Regras Anti-Alucinação

Fluxo de `POST /analysis/matchup`:

1. Buscar no Postgres as métricas de ambos os times (três janelas) e as linhas de mercado do jogo.
2. Serializar esses números em `context_json`. Este objeto é a **única** fonte factual.
3. Montar o prompt blindado: instrução de sistema + `context_json` + pergunta.
4. Calcular `prompt_hash`. Se existir no `analysis_cache`, retornar sem chamar o LLM.
5. Chamar o Gemini via `LLMProvider`.
6. **Validar a resposta antes de entregar.** Extrair todo número citado no texto e conferir contra `context_json`. Divergência acima da tolerância de arredondamento (0.01) invalida a resposta.
7. Persistir e retornar.

Regras rígidas do prompt de sistema:

- O modelo **não** pode introduzir estatística que não esteja no contexto injetado.
- O modelo **não** pode citar lesões, escalações, clima ou histórico de confronto — nada disso está no contexto.
- O modelo **não** emite recomendação de aposta, stake ou nível de confiança numérico próprio.
- Se o contexto for insuficiente para a pergunta, o modelo deve declarar a insuficiência, não preencher a lacuna.
- Saída em português, estruturada em três blocos: **Panorama**, **Análise**, **Fechamento**.

---

## 10. Automação e Agendamento

`.github/workflows/etl-weekly.yml`:

- **Cron:** `0 8 * * 2` (UTC) → terça-feira, 05:00 BRT. Janela segura: cobre jogos de domingo e o Monday Night, e o nflverse já publicou o lote.
- Etapas: instalar dependências → autenticar na AWS via credenciais em secret → executar ingestão da semana corrente → escrever Parquet no S3 → registrar linha em `ingestion_runs`.
- Falha deve abrir issue automática no repositório, não morrer em silêncio.
- Backfill histórico: temporadas 2020 a 2026, executado uma única vez, manualmente, via `workflow_dispatch`.

Secrets necessários: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `SUPABASE_DB_URL`, `GEMINI_API_KEY`.

---

## 11. Milestones

| Fase | Entrega | Gate de saída |
|---|---|---|
| **1 — ETL local** *(atual)* | Script Python baixa pbp e schedules reais, calcula métricas, salva Parquet local. | Arquivos válidos em disco, testes passando, métricas conferidas manualmente contra fonte pública. |
| **2 — Infraestrutura** *(pausa manual)* | Bucket S3, projeto Supabase, credenciais AWS, chave Gemini, secrets no GitHub. | Conexão testada de ponta a ponta. |
| **3 — ETL em nuvem** | Upload para S3 integrado, workflow cron ativo. | Duas execuções semanais consecutivas bem-sucedidas sem intervenção. |
| **4 — Backend e persistência** | Spring Boot com entidades, repositórios, sincronização S3→Postgres, endpoints de leitura. | Todos os endpoints de `/teams` e `/games` respondendo com dados reais. |
| **5 — Orquestração LLM** | Pipeline RAG, cache, validação numérica. | Dez análises geradas, zero divergência numérica na validação. |
| **6 — Frontend** | Dashboards React consumindo a API, deploy na Vercel. | Aplicação pública acessível, séries temporais renderizando. |

Cada fase termina com um commit de tag (`v0.1-etl`, `v0.2-cloud`, ...) e uma entrada em `docs/adr/` se alguma decisão foi tomada no caminho.

---

## 12. Regras para o Agente de IA (Cursor / Claude Code)

1. **Spec-driven.** Consultar este arquivo antes de qualquer tarefa. Nunca alterar arquitetura sem atualizar a spec no mesmo commit.
2. **Teste antes de implementação.** Escrever o teste que falha, depois o código que passa. Vale para o ETL Python e para os services Java.
3. **Código é autoridade sobre números.** Nenhuma métrica é reportada de memória ou estimada. Se o valor não saiu de uma execução real, ele não entra em documento, README ou resposta.
4. **Resultado negativo é resultado.** Se uma métrica não separa sinal, se o EPA não prediz nada útil, se o cache não reduz custo — documentar como está. Não maquiar.
5. **Modularidade estrita.** Python não chama LLM. Python não escreve no Postgres. Java não calcula métrica. Frontend não faz regra de negócio.
6. **Resiliência.** Tratar timeout de rede, arquivo ausente no S3, coluna nula em DataFrame e resposta malformada do LLM. Falha explícita é aceitável; falha silenciosa não.
7. **Commits cirúrgicos.** Uma preocupação por commit, mensagem descrevendo o porquê e não o quê.
8. **Pré-registro.** Filtros de jogada, janelas móveis e limiares (ex.: 20 jardas para explosive play) são fixados aqui antes de rodar. Mudar limiar depois de ver o resultado exige ADR justificando.

---

## 13. Riscos e Questões Abertas

| # | Item | Estado |
|---|---|---|
| R-1 | `nflreadpy` ainda é marcado como experimental pelo nflverse. API pode mudar. | Pinar versão exata no `pyproject.toml`. Revisar a cada temporada. |
| R-2 | Odds do nflverse são linhas de fechamento em lote, não linha viva. Limita o uso a análise pré-jogo com linha estática. | Aceito e declarado como não-objetivo. |
| R-3 | Cold start do Cloud Run com `min-instances=0` pode chegar a 10s na primeira requisição. | Aceito na v1. Frontend deve exibir estado de carregamento honesto. |
| R-4 | Camada gratuita do Supabase pausa projetos ociosos. | Monitorar. Um ping semanal do workflow de ETL mantém ativo. |
| R-5 | Java/Spring Boot é a parte menos familiar da stack. Fase 4 é a de maior risco de cronograma. | Reservar folga. A fase 5 depende inteiramente dela. |
| Q-1 | Validação numérica da resposta do LLM: regex sobre o texto é frágil. Alternativa é exigir saída em JSON estruturado com campos numéricos separados da narrativa. | **Aberto.** Decidir antes da Fase 5. |
| Q-2 | Ajuste por oponente (opponent adjustment) nas métricas de EPA. Melhora muito a leitura, custa complexidade. | **Aberto.** Candidato a v2. |

---

## 14. Glossário

- **EPA (Expected Points Added):** variação no valor esperado de pontos da posse, entre o início e o fim da jogada. Métrica-base da análise moderna de NFL.
- **Success rate:** proporção de jogadas com EPA positivo. Mede consistência; EPA médio mede magnitude.
- **Spread line:** handicap de pontos. Positivo significa mandante favorito por aquela margem.
- **Moneyline:** odds americanas para vitória direta.
- **Vig / overround:** margem embutida da casa; a soma das probabilidades implícitas excede 1.
- **RAG:** Retrieval-Augmented Generation. Aqui, recuperação determinística de números do Postgres injetados como contexto no prompt.
- **Play-by-play (pbp):** dataset com uma linha por jogada, ~400 colunas, incluindo EPA e win probability já calculados pelo nflfastR.
