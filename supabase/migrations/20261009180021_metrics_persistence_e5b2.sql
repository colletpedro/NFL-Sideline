-- E5b-2: immutable offline metrics, private SQL only. No legacy changes.
create role metric_persistence_writer nologin nosuperuser nocreatedb nocreaterole
    noinherit noreplication nobypassrls;
create schema metrics_private;
revoke all on schema metrics_private from public, anon, authenticated, service_role;
grant usage on schema metrics_private to metric_persistence_writer;

create domain metrics_private.sha256_id as text
    check (value ~ '^sha256:[0-9a-f]{64}$');
create domain metrics_private.byte_hash as text
    check (value ~ '^[0-9a-f]{64}$');

revoke all on domain metrics_private.sha256_id, metrics_private.byte_hash
    from public, anon, authenticated, service_role;
grant usage on domain metrics_private.sha256_id, metrics_private.byte_hash to metric_persistence_writer;

create table metrics_private.metric_archive_blob (
    sha256 metrics_private.byte_hash primary key,
    byte_length bigint not null check (byte_length >= 0),
    persisted_at timestamptz not null default clock_timestamp()
);
create table metrics_private.metric_source_revision (
    revision_id metrics_private.sha256_id primary key,
    sha256 metrics_private.byte_hash not null unique references metrics_private.metric_archive_blob,
    check (revision_id = 'sha256:' || sha256)
);
create table metrics_private.metric_source_set (
    revision_id metrics_private.sha256_id not null,
    kind text not null check (kind in ('calendar','pbp')),
    members_json jsonb not null check (jsonb_typeof(members_json) = 'array'),
    primary key (revision_id, kind)
);
create table metrics_private.metric_source_member (
    set_id metrics_private.sha256_id not null,
    kind text not null,
    ordinal bigint not null check (ordinal >= 0),
    source_id metrics_private.sha256_id not null references metrics_private.metric_source_revision,
    raw_rows bigint not null check (raw_rows >= 0),
    descriptor_json jsonb not null check (jsonb_typeof(descriptor_json) = 'object'),
    primary key (set_id, kind, ordinal),
    foreign key (set_id, kind) references metrics_private.metric_source_set
);
create index metric_source_member_source_idx on metrics_private.metric_source_member(source_id);

create table metrics_private.metric_calculation (
    calculation_id metrics_private.sha256_id primary key,
    artifact_version text not null check (artifact_version = 'metrics-offline-v1'),
    adapter_version text not null,
    definition_version text not null,
    population_version text not null,
    calendar_set_id metrics_private.sha256_id not null,
    calendar_kind text not null default 'calendar' check (calendar_kind = 'calendar'),
    pbp_set_id metrics_private.sha256_id not null,
    pbp_kind text not null default 'pbp' check (pbp_kind = 'pbp'),
    manifest_json jsonb not null check (jsonb_typeof(manifest_json) = 'object'),
    persisted_at timestamptz not null default clock_timestamp(),
    foreign key (calendar_set_id, calendar_kind) references metrics_private.metric_source_set,
    foreign key (pbp_set_id, pbp_kind) references metrics_private.metric_source_set
);
create index metric_calculation_calendar_idx on metrics_private.metric_calculation(calendar_set_id,calendar_kind);
create index metric_calculation_pbp_idx on metrics_private.metric_calculation(pbp_set_id,pbp_kind);

create table metrics_private.game_metric_coverage_revision (
    coverage_revision_id metrics_private.sha256_id primary key,
    game_id text not null references public.games,
    season integer not null check (season >= 1999),
    week integer not null check (week >= 1),
    phase text not null check (phase in ('REG','POST')),
    round text,
    home_team text not null references public.teams,
    away_team text not null references public.teams,
    calendar_revision_id metrics_private.sha256_id not null,
    calendar_kind text not null default 'calendar' check (calendar_kind = 'calendar'),
    pbp_revision_id metrics_private.sha256_id not null,
    pbp_kind text not null default 'pbp' check (pbp_kind = 'pbp'),
    pbp_content_id metrics_private.sha256_id not null,
    completeness text not null check (completeness in ('UNKNOWN','PARTIAL','COMPLETE')),
    declared_completeness text not null check (declared_completeness in ('UNKNOWN','PARTIAL','COMPLETE')),
    scope text not null check (scope in ('AUDITABLE_SUBSET','FULL_GAME_CONTENT','NO_SOURCE_OBSERVATION')),
    statistics_status text not null check (statistics_status in ('PARTIAL','COMPLETE','SOURCE_UNKNOWN')),
    raw_n bigint not null check (raw_n >= 0),
    unique_n bigint not null check (unique_n >= 0),
    duplicate_rows_ignored bigint not null check (duplicate_rows_ignored >= 0),
    excluded_n bigint not null check (excluded_n >= 0),
    calendar_duplicate_rows_ignored bigint not null check (calendar_duplicate_rows_ignored >= 0),
    outside_pass_run_null_teams_n bigint not null check (outside_pass_run_null_teams_n >= 0 and outside_pass_run_null_teams_n <= unique_n),
    unknown_filter_flags_n bigint not null check (unknown_filter_flags_n >= 0 and unknown_filter_flags_n <= excluded_n),
    eligible_content_n bigint check (eligible_content_n >= 0),
    expected_unique_rows bigint check (expected_unique_rows >= 0),
    audit_json jsonb not null check (jsonb_typeof(audit_json) = 'object'),
    check (home_team <> away_team),
    check ((phase = 'REG' and round is not null and round = 'REG') or
           (phase = 'POST' and (round is null or round in ('WC','DIV','CON','SB')))),
    check (raw_n = unique_n::numeric + duplicate_rows_ignored),
    check (unique_n >= excluded_n),
    check ((scope = 'NO_SOURCE_OBSERVATION' and statistics_status = 'SOURCE_UNKNOWN'
                and completeness <> 'COMPLETE' and unique_n = 0 and eligible_content_n is null) or
           (scope = 'AUDITABLE_SUBSET' and statistics_status = 'PARTIAL' and completeness in ('UNKNOWN','PARTIAL')
                and unique_n > 0 and eligible_content_n is not null and unique_n = excluded_n::numeric + eligible_content_n) or
           (scope = 'FULL_GAME_CONTENT' and statistics_status = 'COMPLETE' and completeness = 'COMPLETE'
                and expected_unique_rows is not null and unique_n = expected_unique_rows
                and eligible_content_n is not null and unique_n = excluded_n::numeric + eligible_content_n)),
    unique (coverage_revision_id,game_id),
    unique (coverage_revision_id,scope,statistics_status,completeness),
    foreign key (calendar_revision_id,calendar_kind) references metrics_private.metric_source_set,
    foreign key (pbp_revision_id,pbp_kind) references metrics_private.metric_source_set
);
create index metric_coverage_game_idx on metrics_private.game_metric_coverage_revision(game_id);
create index metric_coverage_home_idx on metrics_private.game_metric_coverage_revision(home_team);
create index metric_coverage_away_idx on metrics_private.game_metric_coverage_revision(away_team);
create index metric_coverage_calendar_idx on metrics_private.game_metric_coverage_revision(calendar_revision_id,calendar_kind);
create index metric_coverage_pbp_idx on metrics_private.game_metric_coverage_revision(pbp_revision_id,pbp_kind);

create table metrics_private.metric_calculation_coverage (
    calculation_id metrics_private.sha256_id not null references metrics_private.metric_calculation,
    game_id text not null,
    coverage_revision_id metrics_private.sha256_id not null,
    primary key (calculation_id,game_id),
    foreign key (coverage_revision_id,game_id) references metrics_private.game_metric_coverage_revision(coverage_revision_id,game_id)
);
create index metric_calculation_coverage_revision_idx on metrics_private.metric_calculation_coverage(coverage_revision_id,game_id);

create table metrics_private.team_game_metric_sums (
    coverage_revision_id metrics_private.sha256_id not null,
    team text not null references public.teams,
    role text not null check (role in ('off','def')),
    foundation text not null check (foundation in ('general','classified_pass','classified_rush')),
    population_version text not null,
    definition_version text not null,
    scope text not null check (scope in ('AUDITABLE_SUBSET','FULL_GAME_CONTENT')),
    statistics_status text not null check (statistics_status in ('PARTIAL','COMPLETE')),
    completeness text not null check (completeness in ('UNKNOWN','PARTIAL','COMPLETE')),
    eligible_n bigint not null check (eligible_n >= 0),
    epa_n bigint not null check (epa_n >= 0),
    success_n bigint not null check (success_n >= 0 and success_n <= epa_n),
    epa_missing_n bigint not null check (epa_missing_n >= 0),
    epa_nonfinite_n bigint not null check (epa_nonfinite_n >= 0),
    epa_sum numeric,
    record_json jsonb not null check (jsonb_typeof(record_json) = 'object'),
    check (eligible_n::numeric = epa_n::numeric + epa_missing_n::numeric + epa_nonfinite_n::numeric),
    check ((epa_n = 0 and epa_sum is null) or
           (epa_n > 0 and epa_sum is not null and epa_sum not in ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))),
    primary key (coverage_revision_id,team,role,foundation,population_version,definition_version),
    foreign key (coverage_revision_id,scope,statistics_status,completeness)
        references metrics_private.game_metric_coverage_revision(coverage_revision_id,scope,statistics_status,completeness)
);
create index metric_sums_team_idx on metrics_private.team_game_metric_sums(team);

create table metrics_private.metric_artifact (
    artifact_id metrics_private.sha256_id primary key,
    calculation_id metrics_private.sha256_id not null references metrics_private.metric_calculation,
    files_json jsonb not null check (jsonb_typeof(files_json) = 'object')
);
create index metric_artifact_calculation_idx on metrics_private.metric_artifact(calculation_id);
create table metrics_private.metric_artifact_file (
    artifact_id metrics_private.sha256_id not null references metrics_private.metric_artifact,
    filename text not null check (filename in ('COMPLETED.json','manifest.json','game-audit.json','statistics.json','reconciliation.json','limitations.json')),
    sha256 metrics_private.byte_hash not null references metrics_private.metric_archive_blob,
    primary key (artifact_id,filename)
);
create index metric_artifact_file_blob_idx on metrics_private.metric_artifact_file(sha256);

create table metrics_private.metric_archive_receipt (
    receipt_id metrics_private.sha256_id primary key,
    sha256 metrics_private.byte_hash not null references metrics_private.metric_archive_blob,
    archive_id uuid not null,
    archive_root text not null,
    locator text not null,
    observed_at timestamptz not null check (isfinite(observed_at)),
    receipt_json jsonb not null check (jsonb_typeof(receipt_json) = 'object'),
    persisted_at timestamptz not null default clock_timestamp(),
    unique (archive_id,sha256)
);
create index metric_archive_receipt_blob_idx on metrics_private.metric_archive_receipt(sha256);

revoke all on type metrics_private.metric_archive_blob from public, anon, authenticated, service_role;
alter table metrics_private.metric_archive_blob enable row level security;
alter table metrics_private.metric_archive_blob force row level security;
revoke all on metrics_private.metric_archive_blob from public, anon, authenticated, service_role;
grant select, insert on metrics_private.metric_archive_blob to metric_persistence_writer;
create policy writer_select on metrics_private.metric_archive_blob for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.metric_archive_blob for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.metric_source_revision from public, anon, authenticated, service_role;
alter table metrics_private.metric_source_revision enable row level security;
alter table metrics_private.metric_source_revision force row level security;
revoke all on metrics_private.metric_source_revision from public, anon, authenticated, service_role;
grant select, insert on metrics_private.metric_source_revision to metric_persistence_writer;
create policy writer_select on metrics_private.metric_source_revision for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.metric_source_revision for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.metric_source_set from public, anon, authenticated, service_role;
alter table metrics_private.metric_source_set enable row level security;
alter table metrics_private.metric_source_set force row level security;
revoke all on metrics_private.metric_source_set from public, anon, authenticated, service_role;
grant select, insert on metrics_private.metric_source_set to metric_persistence_writer;
create policy writer_select on metrics_private.metric_source_set for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.metric_source_set for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.metric_source_member from public, anon, authenticated, service_role;
alter table metrics_private.metric_source_member enable row level security;
alter table metrics_private.metric_source_member force row level security;
revoke all on metrics_private.metric_source_member from public, anon, authenticated, service_role;
grant select, insert on metrics_private.metric_source_member to metric_persistence_writer;
create policy writer_select on metrics_private.metric_source_member for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.metric_source_member for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.metric_calculation from public, anon, authenticated, service_role;
alter table metrics_private.metric_calculation enable row level security;
alter table metrics_private.metric_calculation force row level security;
revoke all on metrics_private.metric_calculation from public, anon, authenticated, service_role;
grant select, insert on metrics_private.metric_calculation to metric_persistence_writer;
create policy writer_select on metrics_private.metric_calculation for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.metric_calculation for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.game_metric_coverage_revision from public, anon, authenticated, service_role;
alter table metrics_private.game_metric_coverage_revision enable row level security;
alter table metrics_private.game_metric_coverage_revision force row level security;
revoke all on metrics_private.game_metric_coverage_revision from public, anon, authenticated, service_role;
grant select, insert on metrics_private.game_metric_coverage_revision to metric_persistence_writer;
create policy writer_select on metrics_private.game_metric_coverage_revision for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.game_metric_coverage_revision for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.metric_calculation_coverage from public, anon, authenticated, service_role;
alter table metrics_private.metric_calculation_coverage enable row level security;
alter table metrics_private.metric_calculation_coverage force row level security;
revoke all on metrics_private.metric_calculation_coverage from public, anon, authenticated, service_role;
grant select, insert on metrics_private.metric_calculation_coverage to metric_persistence_writer;
create policy writer_select on metrics_private.metric_calculation_coverage for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.metric_calculation_coverage for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.team_game_metric_sums from public, anon, authenticated, service_role;
alter table metrics_private.team_game_metric_sums enable row level security;
alter table metrics_private.team_game_metric_sums force row level security;
revoke all on metrics_private.team_game_metric_sums from public, anon, authenticated, service_role;
grant select, insert on metrics_private.team_game_metric_sums to metric_persistence_writer;
create policy writer_select on metrics_private.team_game_metric_sums for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.team_game_metric_sums for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.metric_artifact from public, anon, authenticated, service_role;
alter table metrics_private.metric_artifact enable row level security;
alter table metrics_private.metric_artifact force row level security;
revoke all on metrics_private.metric_artifact from public, anon, authenticated, service_role;
grant select, insert on metrics_private.metric_artifact to metric_persistence_writer;
create policy writer_select on metrics_private.metric_artifact for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.metric_artifact for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.metric_artifact_file from public, anon, authenticated, service_role;
alter table metrics_private.metric_artifact_file enable row level security;
alter table metrics_private.metric_artifact_file force row level security;
revoke all on metrics_private.metric_artifact_file from public, anon, authenticated, service_role;
grant select, insert on metrics_private.metric_artifact_file to metric_persistence_writer;
create policy writer_select on metrics_private.metric_artifact_file for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.metric_artifact_file for insert to metric_persistence_writer with check (true);

revoke all on type metrics_private.metric_archive_receipt from public, anon, authenticated, service_role;
alter table metrics_private.metric_archive_receipt enable row level security;
alter table metrics_private.metric_archive_receipt force row level security;
revoke all on metrics_private.metric_archive_receipt from public, anon, authenticated, service_role;
grant select, insert on metrics_private.metric_archive_receipt to metric_persistence_writer;
create policy writer_select on metrics_private.metric_archive_receipt for select to metric_persistence_writer using (true);
create policy writer_insert on metrics_private.metric_archive_receipt for insert to metric_persistence_writer with check (true);
