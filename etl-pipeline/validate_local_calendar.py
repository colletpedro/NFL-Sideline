"""Integração opt-in: somente Supabase local em 127.0.0.1:54322, nunca lê .env.

Executar após `supabase db reset --local --no-seed`. Usa Parquet real e
referência pública de times existente; não baixa dados nem aciona S3/Gemini.
Não integra a suíte pytest offline padrão.
"""
import json
from pathlib import Path

import polars as pl
import psycopg2

import load_games
import run_pipeline
import seed_teams

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "etl-pipeline/data"


def local_connection():
    conn = psycopg2.connect(host="127.0.0.1", hostaddr="127.0.0.1", port=54322, dbname="postgres",
                            user="postgres", password="postgres", connect_timeout=5)
    with conn.cursor() as cursor:
        cursor.execute("SELECT inet_server_addr()::text, current_database()")
        address, database = cursor.fetchone()
        assert database == "postgres" and address is not None
    return conn


def counts(conn):
    with conn.cursor() as c:
        c.execute("SELECT count(*), count(DISTINCT game_id), min(week), max(week) FROM games WHERE season=2026")
        games = c.fetchone()
        c.execute("SELECT count(*) FROM market_implied m JOIN games g USING(game_id) WHERE g.season=2026")
        markets = c.fetchone()[0]
        c.execute("SELECT count(*) FROM games g LEFT JOIN teams h ON h.team_abbr=g.home_team "
                  "LEFT JOIN teams a ON a.team_abbr=g.away_team WHERE h.team_abbr IS NULL OR a.team_abbr IS NULL")
        assert c.fetchone()[0] == 0
        c.execute("SELECT count(*) FROM market_implied m LEFT JOIN games g USING(game_id) WHERE g.game_id IS NULL")
        assert c.fetchone()[0] == 0
        c.execute("SELECT count(*) FROM team_week_metrics m LEFT JOIN teams t USING(team_abbr) WHERE t.team_abbr IS NULL")
        assert c.fetchone()[0] == 0
    return (*games, markets)


def verify_quote_updates(conn, source):
    quoted = source.filter(pl.col("home_moneyline").is_not_null() & pl.col("away_moneyline").is_not_null()).head(1)
    game_id = quoted["game_id"][0]
    def read():
        with conn.cursor() as c:
            c.execute("SELECT home_moneyline,away_moneyline,spread_line,total_line,home_score,away_score,result "
                      "FROM games WHERE game_id=%s", (game_id,))
            game = c.fetchone()
            c.execute("SELECT home_implied_fair,away_implied_fair FROM market_implied WHERE game_id=%s", (game_id,))
            return game, c.fetchone()
    original = read()
    # All absent, home-only and away-only observations must preserve the complete pair.
    for home, away in [(None, None), (-230, None), (None, 190)]:
        observation = quoted.with_columns(pl.lit(home).alias("home_moneyline"),
            pl.lit(away).alias("away_moneyline"), pl.lit(None).alias("spread_line"),
            pl.lit(None).alias("total_line"))
        prepared = load_games.prepare_games(observation)
        load_games.upsert_games(conn, prepared, commit=False)
        assert load_games.build_market_rows(prepared) == []
        assert read() == original
    complete = quoted.with_columns(pl.lit(-200).alias("home_moneyline"),
        pl.lit(170).alias("away_moneyline"), pl.lit(27).alias("home_score"),
        pl.lit(20).alias("away_score"), pl.lit(7).alias("result"))
    prepared = load_games.prepare_games(complete)
    load_games.upsert_games(conn, prepared, commit=False)
    load_games.upsert_market(conn, load_games.build_market_rows(prepared), commit=False)
    changed = read()
    assert changed[0][:2] == (-200, 170) and changed[0][4:] == (27, 20, 7)
    assert changed[1] != original[1]
    no_quote = load_games.prepare_games(quoted.with_columns(
        pl.lit(None).alias("home_moneyline"), pl.lit(None).alias("away_moneyline")))
    load_games.upsert_games(conn, no_quote, commit=False)
    assert read() == changed  # nullable score trio and odds preserve known complete values
    conn.rollback()
    assert read() == original
    # An actual PostgreSQL FK failure in market rolls back the preceding games update.
    load_games.upsert_games(conn, prepared, commit=False)
    invalid_market = load_games.build_market_rows(prepared)
    invalid_market[0]["game_id"] = "local-nonexistent-fk-test"
    try:
        load_games.upsert_market(conn, invalid_market, commit=False)
        raise AssertionError("expected FK failure")
    except psycopg2.IntegrityError:
        assert read() == original
    conn.rollback()


def main():
    source = load_games.load_schedules(DATA, (2026,))
    prepared = load_games.prepare_games(source)
    expected_markets = len(load_games.build_market_rows(prepared))
    with local_connection() as conn:
        # Reuse public team metadata, preserving the authoritative local schedule.
        public = json.loads((ROOT / "web-ui/public/data/seasons/2026.json").read_text())
        seed_teams.upsert_teams(conn, pl.DataFrame([{
            "team_abbr": t["teamAbbr"], "team_name": t["teamName"],
            "conference": t["conference"], "division": t["division"], "logo_url": t["logoUrl"],
        } for t in public["teams"]]))
    observed = []
    for attempt in (1, 2):
        result = run_pipeline.process_season(2026, data_dir=DATA, allow_missing_pbp=True,
                                            skip_acquire=True, connection_factory=local_connection)
        with local_connection() as conn:
            actual = counts(conn)
            assert actual == (prepared.height, prepared["game_id"].n_unique(), 1, 18, expected_markets)
            with conn.cursor() as c:
                c.execute("SELECT status,rows_games,rows_pbp FROM ingestion_runs WHERE id=%s", (result.run_id,))
                assert c.fetchone() == ("SUCCEEDED", prepared.height, result.rows_pbp)
            observed.append(actual)
        print(f"attempt={attempt} games={result.rows_games} markets={result.rows_market} "
              f"pbp={result.rows_pbp} metrics={result.rows_metrics} ingestion_rows_games={result.rows_games}")
    assert observed[0] == observed[1]
    with local_connection() as conn:
        verify_quote_updates(conn, source)
        with conn.cursor() as c:
            c.execute("SELECT g.week,count(*),count(m.game_id) FROM games g "
                      "LEFT JOIN market_implied m USING(game_id) WHERE season=2026 GROUP BY g.week ORDER BY g.week")
            print("week,games,markets")
            for row in c.fetchall(): print(",".join(map(str, row)))
    print("orphans=0 idempotency=PASS quote_preservation=PASS score_atomicity=PASS rollback=PASS")


if __name__ == "__main__":
    main()
