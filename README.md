# NFL Sideline

NFL Sideline é um protótipo funcional para análise tática de confrontos da NFL. O sistema combina métricas semanais de eficiência, contexto de calendário e mercado e uma análise textual estruturada gerada pelo Gemini.

A prioridade do produto é explicar o confronto entre ataques e defesas. Uma previsão pode aparecer como conclusão secundária da análise, mas ainda não existe um modelo preditivo quantitativo independente. As probabilidades de mercado na interface são probabilidades implícitas sem vig. Sem par válido, o jogo permanece visível sem favorito, probabilidade, confiança ou edge.

## Arquitetura atual

```text
nflverse / nflreadpy
  -> Parquet local
  -> ETL Python + Polars + psycopg2
  -> PostgreSQL no Supabase
  -> Java 21 / Spring Boot / JPA
     -> API REST local + Gemini/cache quando solicitado
     -> exportador batch read-only -> snapshots JSON públicos
  -> React 18 / TypeScript / Vite
     -> API local em desenvolvimento
     -> /data/*.json em Production estática
```

- `etl-pipeline/`: `run_pipeline.py` orquestra aquisição, times, jogos/mercado, métricas e auditoria de cada temporada diretamente no PostgreSQL do Supabase.
- `core-api/`: expõe a API REST local, orquestra Gemini/cache quando solicitado e exporta snapshots sem servidor HTTP.
- `web-ui/`: dashboard Vite; em desenvolvimento usa o Spring local e em Production usa obrigatoriamente `/data/manifest.json` e o snapshot da temporada.
- `supabase/config.toml` e `supabase/migrations/`: configuração local e baseline versionadas para reconstruir o schema em um banco vazio.
- `.github/workflows/`: CI Java e ETL semanal existentes; a confiabilidade do workflow semanal ainda não foi comprovada.

S3 permanece apenas como caminho opcional/legado em `run_local.py`; nenhum upload ocorre sem `--upload-s3`. Ele não participa da publicação estática.

O frontend de Production não usa Supabase nem backend. O Java batch e os loaders Python acessam o PostgreSQL diretamente por JDBC e psycopg2; a Data API permanece desativada.

### Production estática atual

O rollout oficial foi concluído em 2026-09-14. Os endereços canônicos são [nfl-sideline.vercel.app](https://nfl-sideline.vercel.app/) e [nfl-sideline-git-main-colletpedros-projects.vercel.app](https://nfl-sideline-git-main-colletpedros-projects.vercel.app/); ambos servem o build Vite estático e leem somente `/data/manifest.json` e `/data/seasons/2026.json`. Não há backend Java, Cloud Run, `/api/v1`, localhost, Supabase ou Gemini no caminho público.

O projeto Vercel `web-ui`, acessível em `web-ui-khaki.vercel.app`, é mantido apenas como ambiente temporário de segurança/rollback e não é endereço canônico.

O snapshot público atual tem temporada 2026, 272 jogos nas semanas 1–18, 32 times, 112 jogos com mercado e 160 sem mercado. Há quatro métricas da semana 1 (LA, NE, SEA e SF), oito análises públicas e dois resultados completos: `NE 10 @ SEA 13` (`Final · SEA won by 3`) e `SF 27 @ LA 7` (`Final · SF won by 20`). Jogos futuros sem mercado permanecem visíveis em estado neutro; em jogos concluídos, os placares são primários e as probabilidades ficam na área de mercado.

A publicação de novos snapshots continua manual: o workflow semanal atualiza o PostgreSQL, mas não executa o exportador Java, não atualiza os JSONs versionados, não cria commit e não publica a Vercel automaticamente. Sua confiabilidade contínua também ainda não foi comprovada por execuções observadas.

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

Preencha `SUPABASE_DB_URL`, `SUPABASE_DB_USER` e `SUPABASE_DB_PASSWORD`. `GEMINI_API_KEY` só é necessária quando a API local for explicitamente usada para gerar análise. `PORT` usa `8080` por default. O `.env` contém segredos e não deve ser commitado. Variáveis AWS, quando presentes, não disparam upload: o fluxo S3 legado exige também `--upload-s3`.

`VITE_API_BASE_URL` é pública e só vale em development/test local. Não a cadastre na Vercel: builds de Production usam obrigatoriamente snapshots `/data` e não podem ser desviados por variável Vite. Toda variável `VITE_*` é visível no browser e nunca deve conter secrets.

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

`load_games.py` persiste diretamente `home_score`, `away_score` e `result` do schedule como um snapshot atômico. Os três campos devem ser todos nulos ou todos preenchidos; valores preenchidos são inteiros, scores são não negativos e `result` deve ser a diferença acima, incluindo empate com zero. Não há derivação nem preenchimento de campo ausente. Em conflito, um trio integralmente nulo preserva integralmente o resultado conhecido; um trio completo e válido o substitui integralmente. Qualquer combinação parcial falha antes do banco. Todo upsert define `games.updated_at = now()`.

Calendário independe de cotação: todos os jogos REG/POST estruturalmente válidos são preparados, inclusive sem spread, total ou moneylines. `rows_games` conta todos esses jogos; `rows_market` conta apenas os pares completos e válidos calculados/upsertados nessa execução. O mercado não exige spread. Moneylines são atômicas: um par completo substitui o anterior junto com `market_implied`; uma observação ausente/parcial preserva o último par completo e seu mercado, sem combinar fontes. Para um jogo novo, par incompleto vira `null/null` e não cria mercado. Spread e total ausentes preservam individualmente linhas conhecidas. Jogos e mercados permanecem na mesma transação; warnings são agregados por temporada.

`ingestion_runs` tem uma linha por execução/temporada: `week` fica NULL porque a temporada inteira é reprocessada; `status` usa exatamente `RUNNING`, `SUCCEEDED` ou `FAILED`; `rows_pbp` conta o PBP bruto selecionado antes do filtro de jogadas válidas; `rows_games` conta todos os jogos preparados, cotados ou não; `rows_market` é informado no resumo da etapa/pipeline, sem nova coluna no banco; `started_at` e `finished_at` vêm do banco; sucesso deixa `error_message` NULL e falha grava mensagem sanitizada de até 1.000 caracteres. Uma interrupção abrupta pode deixar `RUNNING`; ainda não há tratamento automático desses runs.

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

Para o gate Java reproduzível, confirme primeiro com `mvn -version` que o Maven está usando Java 21 e execute, dentro de `core-api`, `mvn -o clean verify`. Um simples `mvn test` sobre um `target` já existente não é evidência final, pois relatórios antigos podem permanecer no diretório descartável.

A API é destinada a desenvolvimento e demonstração locais. CORS é centralizado e, por default, permite somente `http://localhost:5173` e `http://127.0.0.1:5173`.

Para exportar a temporada 2026 sem iniciar servidor, após `mvn -f core-api/pom.xml package`, carregue as credenciais no processo. O Java não carrega `.env` sozinho:

```bash
set -a
source .env
set +a
java -jar core-api/target/core-api-0.1.0.jar snapshot-export \
  --season 2026 \
  --as-of 2026-09-15 \
  --output web-ui/public/data
```

Consulte o [contrato de snapshots](docs/static-snapshot-contract.md) para formato, atomicidade e opções.

### Fast track editorial manual

O núcleo Java resolve rodadas pela cronologia real dos gamedays, incluindo as fases de postseason, com data UTC
explícita. Como o schema atual das métricas não registra fase nem data, o contexto de postseason não presume que
o número da week prove cronologia: usa apenas referência histórica e declara a limitação.
A rodada operacional atual recebe `matchup_full_v0`, a rodada real seguinte recebe `matchup_basic_v0` e as demais
ficam sem candidato. O comando é seguro por padrão e apenas planeja:

```bash
java -jar core-api/target/core-api-0.1.0.jar editorial-generate \
  --season 2026 --as-of 2026-09-15 --revision-key first-review --max-analyses 32 --dry-run
```

Uma geração local exige trocar `--dry-run` por `--execute` e fornecer `GEMINI_API_KEY`. O planejamento completo e
o teto são calculados antes da primeira chamada. Geração não publica: a seleção humana fica no manifesto
versionado [`editorial/analysis-selections.json`](editorial/analysis-selections.json), cujo contrato está em
[`editorial/README.md`](editorial/README.md). O exportador continua read-only, sem Gemini, e projeta BASIC/FULL
aprovadas como `analysisType: "matchup"` no schema público v1.

Este fast track editorial v0 está implementado localmente e validado offline. Ele ainda não foi integrado a uma
execução autorizada com banco/Gemini nem publicado. O manifesto permanece vazio; nenhuma aprovação real foi
criada nesta etapa. O `snapshot-export` exige `--as-of YYYY-MM-DD`, separado do timestamp real `generatedAt`.

### 6. Frontend

```bash
npm --prefix web-ui ci
npm --prefix web-ui test
npm --prefix web-ui run dev
```

A interface ficará em `http://localhost:5173`.

Para trocar a API apenas no desenvolvimento/teste local, copie `web-ui/.env.example` para `web-ui/.env.local` e ajuste `VITE_API_BASE_URL`. Production ignora qualquer valor dessa variável, lê o manifesto e a temporada, mantém cache em memória e nunca executa POST.

O contexto de publicação usa `manifest.defaultSeason` e `manifest.generatedAt` em Production; a API local oferece `/api/v1/publication` com a temporada NFL corrente e a última atualização dos jogos. Home, header e footer compartilham esse contexto. A semana inicial é escolhida pelas datas UTC: semana cujo intervalo contém hoje; entre semanas, a próxima; antes da temporada, a primeira; depois do último jogo, a última. A seleção manual permanece disponível e independe de odds/análises. PBP ausente significa métricas ausentes, sem substituir dados por outra temporada.

A integração opt-in `python etl-pipeline/validate_local_calendar.py`, após reaplicar as migrations no Supabase **local**, usa exclusivamente `127.0.0.1:54322` e não lê `.env`. Em 2026-09-13 validou 272 jogos/112 mercados em duas execuções e PBP local com 323 linhas/quatro métricas da semana 1. O snapshot público publicado em 2026-09-14 contém o calendário completo de 272 jogos; seus 112 mercados são apenas o subconjunto com cotação válida.

## Deploy seguro

O [runbook de publicação estática](docs/runbooks/deploy-recovery.md) descreve geração, inspeção, build, validação e rollback. Este fluxo não exige Cloud Run nem servidor permanente.

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
- A política editorial de profundidade semanal e postgame está somente registrada no ADR-010; ainda não foi implementada.
- O ETL semanal usa o orquestrador único e é autossuficiente quanto à ordem, mas ainda não possui evidência de execuções reais suficientes para afirmar confiabilidade contínua em produção.
- A Data API remota está desativada. Qualquer reativação ou nova migration remota exige revisão de segurança e o fluxo versionado documentado no runbook; a baseline histórica não deve ser executada novamente.

Consulte [`Spec.md`](Spec.md) para contratos, schema, métricas, decisões e roadmap completos.
