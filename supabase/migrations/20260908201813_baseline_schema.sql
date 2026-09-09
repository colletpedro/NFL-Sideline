-- Baseline do schema observado no Supabase/PostgreSQL em 2026-09-08.
-- Apenas estrutura: sem dados, seeds, credenciais, políticas ou grants.

create table public.teams (
    team_abbr text not null,
    team_name text not null,
    conference text,
    division text,
    logo_url text,
    constraint teams_pkey primary key (team_abbr)
);

create table public.games (
    game_id text not null,
    season integer not null,
    week integer not null,
    game_type text not null,
    gameday date,
    home_team text,
    away_team text,
    home_score integer,
    away_score integer,
    result integer,
    spread_line numeric,
    total_line numeric,
    home_moneyline integer,
    away_moneyline integer,
    home_spread_odds integer,
    away_spread_odds integer,
    over_odds integer,
    under_odds integer,
    roof text,
    surface text,
    div_game boolean,
    updated_at timestamp with time zone not null default now(),
    constraint games_pkey primary key (game_id),
    constraint games_home_team_fkey foreign key (home_team)
        references public.teams (team_abbr),
    constraint games_away_team_fkey foreign key (away_team)
        references public.teams (team_abbr)
);

create table public.team_week_metrics (
    season integer not null,
    week integer not null,
    team_abbr text not null,
    off_epa_play numeric,
    def_epa_play numeric,
    off_epa_pass numeric,
    off_epa_rush numeric,
    def_epa_pass numeric,
    def_epa_rush numeric,
    off_success_rate numeric,
    def_success_rate numeric,
    early_down_epa numeric,
    dropback_rate numeric,
    explosive_play_rate numeric,
    plays_offense integer,
    plays_defense integer,
    constraint team_week_metrics_pkey primary key (season, week, team_abbr),
    constraint team_week_metrics_team_abbr_fkey foreign key (team_abbr)
        references public.teams (team_abbr)
);

create table public.market_implied (
    game_id text not null,
    home_implied_raw numeric,
    away_implied_raw numeric,
    home_implied_fair numeric,
    away_implied_fair numeric,
    vig_pct numeric,
    computed_at timestamp with time zone not null default now(),
    constraint market_implied_pkey primary key (game_id),
    constraint market_implied_game_id_fkey foreign key (game_id)
        references public.games (game_id)
);

create table public.analysis_cache (
    id bigserial not null,
    game_id text,
    analysis_type text not null,
    prompt_hash text not null,
    context_json jsonb not null,
    response_text text not null,
    model_name text not null,
    created_at timestamp with time zone not null default now(),
    constraint analysis_cache_pkey primary key (id),
    constraint analysis_cache_game_id_fkey foreign key (game_id)
        references public.games (game_id),
    constraint analysis_cache_game_id_analysis_type_prompt_hash_key
        unique (game_id, analysis_type, prompt_hash)
);

create table public.ingestion_runs (
    id bigserial not null,
    season integer,
    week integer,
    status text not null,
    rows_pbp integer,
    rows_games integer,
    error_message text,
    started_at timestamp with time zone not null,
    finished_at timestamp with time zone,
    constraint ingestion_runs_pkey primary key (id)
);

-- O banco remoto observado tem RLS desabilitado e nenhuma policy nessas tabelas.
-- A baseline não altera acesso à Data API: RLS, policies e grants exigem uma
-- decisão de segurança posterior, separada da reprodução do contrato atual.
