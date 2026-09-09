-- Hardening da Data API: o aplicativo usa somente PostgreSQL direto.
-- Não há policies porque anon/authenticated não possuem consumidores nestas tabelas.

alter table public.teams enable row level security;
alter table public.games enable row level security;
alter table public.team_week_metrics enable row level security;
alter table public.market_implied enable row level security;
alter table public.analysis_cache enable row level security;
alter table public.ingestion_runs enable row level security;

revoke all privileges on table
    public.teams,
    public.games,
    public.team_week_metrics,
    public.market_implied,
    public.analysis_cache,
    public.ingestion_runs
from anon, authenticated, public;

revoke all privileges on sequence
    public.analysis_cache_id_seq,
    public.ingestion_runs_id_seq
from anon, authenticated, public;

-- Mantém a credencial administrativa server-side da plataforma. Nunca a exponha ao frontend.
grant all privileges on table
    public.teams,
    public.games,
    public.team_week_metrics,
    public.market_implied,
    public.analysis_cache,
    public.ingestion_runs
to service_role;

grant all privileges on sequence
    public.analysis_cache_id_seq,
    public.ingestion_runs_id_seq
to service_role;

-- Objetos futuros em public exigem grants explícitos e revisados.
alter default privileges for role postgres in schema public
    revoke select, insert, update, delete on tables
    from anon, authenticated, service_role;

-- Os defaults da plataforma também podem conter D, x e t; remova-os igualmente.
alter default privileges for role postgres in schema public
    revoke all privileges on tables
    from anon, authenticated, service_role;

alter default privileges for role postgres in schema public
    revoke usage, select on sequences
    from anon, authenticated, service_role;

-- Inclui UPDATE de sequences quando presente nos defaults da plataforma.
alter default privileges for role postgres in schema public
    revoke all privileges on sequences
    from anon, authenticated, service_role;

alter default privileges for role postgres in schema public
    revoke execute on functions
    from anon, authenticated, service_role;

alter default privileges for role postgres in schema public
    revoke execute on functions
    from public;

-- Funções recebem EXECUTE para PUBLIC por default do PostgreSQL; a revogação
-- global do criador é necessária para que esse default implícito seja substituído.
alter default privileges for role postgres
    revoke execute on functions
    from anon, authenticated, service_role, public;
