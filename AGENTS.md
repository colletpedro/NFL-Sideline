# AGENTS.md

This file provides repository guidance for contributors and coding agents.

NFL Sideline is a tactical-first NFL matchup analysis prototype. Project docs (`README.md`, `Spec.md`, `docs/`) are written in Portuguese; `Spec.md` is the authoritative spec, `docs/static-snapshot-contract.md` is the public JSON contract, and `docs/current-state.md` summarizes the current local state. `Handoff.md` is a stale 2026-09-08 local audit, not a normative source.

## Commands

All commands run from the repo root.

```bash
# ETL (Python 3.11+)
python3.11 -m venv etl-pipeline/.venv && source etl-pipeline/.venv/bin/activate
pip install -e "etl-pipeline[test]"
python -m pytest etl-pipeline                                   # all ETL tests (offline)
python -m pytest etl-pipeline/tests/test_scores.py -k <name>    # single test
python etl-pipeline/run_pipeline.py --allow-missing-pbp         # full pipeline, current season
python etl-pipeline/run_pipeline.py --season 2025 --data-dir /tmp/fixture --skip-acquire

# core-api (Java 21, Maven). Load .env only for commands that need the database:
set -a; source .env; set +a
mvn -f core-api/pom.xml test
mvn -f core-api/pom.xml test -Dtest=SnapshotExporterTest        # single test class
mvn -f core-api/pom.xml spring-boot:run                          # API on http://localhost:8080/api/v1
(cd core-api && mvn -o clean verify)   # reproducible gate (what CI runs); plain `mvn test` over an old target/ isn't evidence

# Static snapshot export (after `mvn -f core-api/pom.xml package`, with .env loaded)
java -jar core-api/target/core-api-0.1.0.jar snapshot-export --season 2026 --as-of 2026-09-15 --output /tmp/nfl-sideline-snapshot-review

# web-ui (React 18 + Vite + Vitest)
npm --prefix web-ui ci
npm --prefix web-ui test                                          # vitest run
npm --prefix web-ui test -- src/services/calendar.test.ts         # single file
npm --prefix web-ui run lint
npm --prefix web-ui run build                                     # tsc -b && vite build
npm --prefix web-ui run dev                                       # http://localhost:5173

# Local database (Docker required; only on an EMPTY local stack)
npx --yes supabase@2.117.0 start
npx --yes supabase@2.117.0 db reset --local
```

Required env vars (`.env`, copy from `.env.example`): `SUPABASE_DB_URL`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD` for database commands; `GEMINI_API_KEY` only for explicit Gemini generation.

## Architecture

```
nflverse (nflreadpy) -> local Parquet (etl-pipeline/data/raw/{schedules,pbp}/season=YYYY/)
  -> Python ETL (Polars, psycopg2) -> Supabase PostgreSQL
  -> core-api (Spring Boot 3.3.5 / JPA)
       -> local REST API /api/v1 + Gemini analysis (on request, cached)
       -> separate local rules CLI/loopback HTTP mode (no database or Gemini)
       -> read-only batch exporter -> web-ui/public/data/*.json (versioned in git)
  -> web-ui: dev talks to local Spring; production is a static Vercel build reading only /data
```

### ETL (`etl-pipeline/`)
- `run_pipeline.py` is the single orchestrator (used by `.github/workflows/weekly_etl.yml`). Per season, in-process and in FK order: DB connect → insert `RUNNING` row in `ingestion_runs` → acquire → `seed_teams` → `load_games` (games + `market_implied`) → `load_metrics` → `SUCCEEDED`. Fail-fast: any error rolls back the stage, tries to record `FAILED` (sanitized, ≤1000 chars), and stops before later seasons.
- `seed_teams.py`, `load_games.py`, `load_metrics.py`, `run_local.py` remain standalone CLIs. S3 upload is legacy and only happens via `run_local.py --upload-s3`.
- Season policy lives only in `src/nfl_sideline_etl/seasons.py` (Mar–Dec = current year, Jan/Feb = previous; range 1999..current+1; repeated `--season` deduped/sorted). Reuse it; don't reimplement.
- All loaders use `INSERT ... ON CONFLICT DO UPDATE`. Key data invariants enforced in `load_games.py`:
  - `home_score`, `away_score`, `result` are an atomic trio: all null or all set, `result = home_score - away_score`. A null trio preserves known scores; partial trios fail before touching the DB. Never derive/fill fields.
  - Games are loaded regardless of odds. Moneylines are atomic pairs: a complete valid pair replaces the old pair and its `market_implied` row; missing/partial preserves the last complete pair. Spread/total preserved individually via `COALESCE`.
  - Fair probability = proportional vig removal of American-moneyline implied probabilities.
- `--allow-missing-pbp` tolerates only empty/future/404 PBP; network, auth, 5xx, and schema errors stay fatal.

### core-api (`core-api/`)
- Standard controller → service → JPA repository layering under `com.nflsideline.coreapi`. `ddl-auto: validate` — schema is owned by `supabase/migrations/`, never by Hibernate.
- `CoreApiApplication.main` dispatches explicit `snapshot-export`, `editorial-local`, `editorial-local-serve`, and `editorial-evaluate` commands; without those commands it starts the REST API. Snapshot mode runs `snapshot/SnapshotBatchApplication` without a web server, with a read-only datasource and no Gemini instance.
- `AnalysisService` builds a versioned evidence context, SHA-256 hashes the prompt, caches in `analysis_cache` keyed by `(game_id, analysis_type, prompt_hash)`, and calls `GeminiClient` only on explicit Gemini generation. The Gemini claims v3 response is validated and rendered into the 4-field JSON (`fator_chave`, `vantagem_tatica`, `alerta_vermelho`, `veredito`). The legacy API returns that JSON inside `markdownText`; the frontend parses it. `metricas_citadas` describes an earlier contract, not the current Gemini path.
- The local rules selector 2.0.0, claims v5 and renderer 5.0.2 run through `LocalGenerationService` 1.0.0 and a separate loopback CLI/HTTP mode. This path needs no Gemini key, does not predict a winner, and is not connected to the main frontend. Its internal result artifact is v3.
- Snapshot exporter (`snapshot/`): three domain queries per season, never serializes JPA entities, writes to a sibling temp dir then swaps atomically (restores on failure), and leaves files untouched when only `generatedAt` would change. Public analyses must never expose `context_json`, prompt hashes, model name, or prompts.
- CORS is centralized in `config/LocalCorsConfiguration` (localhost:5173 only by default).

### web-ui (`web-ui/`)
- Routes: `/` (`pages/Home`) and `/game/:id` (`pages/MatchupDashboard`). Pages/components depend only on the `NflDataClient` interface (`services/dataClient.ts`), never on Axios.
- The concrete client is chosen at build time via the `#runtime-client` Vite alias (`build/runtime-client-mode.ts`): `vite build` or production mode → `runtimeClient.production.ts` (`StaticNflDataClient`, GET-only, reads `/data/manifest.json` + `/data/seasons/{season}.json`, in-memory cache, assembles `GameDetail` in memory); otherwise → `runtimeClient.development.ts` (`ApiNflDataClient`, Spring API, honors `VITE_API_BASE_URL`). Production must not be redirectable by any `VITE_*` var.
- Default season/`generatedAt` come from the manifest (or `/api/v1/publication` in dev). Initial week selection is date-based (UTC) in `services/calendar.ts`, independent of odds/analyses.
- UI must never fabricate a favorite, confidence, or edge without a valid fair probability; games without market render in a neutral state; missing PBP means missing metrics (no fallback to another season).

### Schema and deployment
- `supabase/migrations/` is the versioned schema (baseline + Data API hardening: RLS on, no policies, no grants for `anon`/`authenticated`). Add new migrations only; never re-run the baseline against the remote DB. The Supabase Data API is intentionally disabled — all access is JDBC/psycopg2.
- Production = Vercel project `nfl-sideline`, `Root Directory = web-ui`, SPA fallback in `web-ui/vercel.json`. Manual Vercel CLI deploys must be started from the repo root (running inside `web-ui` resolves `web-ui/web-ui`).
- Snapshot publication is manual: the weekly workflow only updates PostgreSQL; exporting, reviewing, committing `web-ui/public/data`, and deploying are separate human steps (see `docs/runbooks/deploy-recovery.md`). Don't overwrite public snapshots with local-validation data.
- `snapshot schemaVersion: 1` — incompatible JSON changes need a new version and explicit client support.
