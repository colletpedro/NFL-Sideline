"""Calendário independente de mercado: suíte padrão sem rede/banco."""
from copy import deepcopy
from pathlib import Path
import sqlite3

import polars as pl
import pytest

import load_games
import run_pipeline as pipeline
from test_etl import schedule_frame, write_partition
from test_run_pipeline import install_success_stages


def source(home=None, away=None, spread=None, total=None, game_id="game-1"):
    return schedule_frame(2026, game_id=game_id).with_columns(
        pl.lit(home).alias("home_moneyline"), pl.lit(away).alias("away_moneyline"),
        pl.lit(spread).alias("spread_line"), pl.lit(total).alias("total_line"),
    )


@pytest.mark.parametrize("home,away,spread,count", [
    (None, None, None, 0), (-150, None, -3, 0), (None, 130, None, 0),
    (-150, 130, None, 1), (-150, 130, -3, 1),
])
def test_calendar_survives_independently_of_market(home, away, spread, count):
    games = load_games.prepare_games(source(home, away, spread))
    assert games.height == 1
    assert len(load_games.build_market_rows(games)) == count
    pair = games.select("home_moneyline", "away_moneyline").row(0)
    assert pair == ((home, away) if count else (None, None))
    assert games.select("home_score", "away_score", "result").row(0) == (None, None, None)


@pytest.mark.parametrize("home,away", [(0, None), (None, 0), (0, 130), (float('nan'), 130),
                                               (float('inf'), 130), (-150.5, 130), (200, 200)])
def test_invalid_moneylines_remain_explicit_errors(home, away):
    with pytest.raises(ValueError):
        load_games.build_market_rows(load_games.prepare_games(source(home, away)))


class TransactionConnection:
    """Captura limites transacionais e simula falha após escrita de games."""
    def __init__(self, fail_market=False):
        self.pending = []
        self.committed = []
        self.commits = 0
        self.rollbacks = 0
        self.fail_market = fail_market

    def cursor(self): return self
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params):
        if self.fail_market and sql == load_games.UPSERT_MARKET_SQL:
            raise RuntimeError("injected market failure")
        self.pending.append((sql, params))
    def commit(self):
        self.committed.extend(deepcopy(self.pending))
        self.pending.clear()
        self.commits += 1
    def rollback(self):
        self.pending.clear()
        self.rollbacks += 1


def test_different_counts_and_single_transaction(tmp_path: Path):
    frame = pl.concat([source(-150, 130), source(game_id="no-market")], how="diagonal_relaxed")
    write_partition(frame, tmp_path, "schedules", 2026)
    conn = TransactionConnection()
    result = load_games.load_games_and_market(conn, tmp_path, (2026,))
    assert (result.rows_games, result.rows_market) == (2, 1)
    assert conn.commits == 1 and conn.rollbacks == 0
    assert len(conn.committed) == 3


def test_market_failure_rolls_back_games(tmp_path: Path):
    write_partition(source(-150, 130), tmp_path, "schedules", 2026)
    conn = TransactionConnection(fail_market=True)
    with pytest.raises(RuntimeError, match="injected"):
        load_games.load_games_and_market(conn, tmp_path, (2026,))
    assert conn.commits == 0 and conn.rollbacks > 0
    assert conn.committed == conn.pending == []


def test_partial_observations_are_never_serialized_as_a_mixed_pair():
    for frame in (source(-200, None), source(None, 170), source()):
        row = load_games._rows_for_games(load_games.prepare_games(frame))[0]
        assert row[12:14] == (None, None)
    sql = " ".join(load_games.UPSERT_GAMES_SQL.split())
    for side in ("home", "away"):
        assert (f"{side}_moneyline = CASE WHEN EXCLUDED.home_moneyline IS NOT NULL "
                f"AND EXCLUDED.away_moneyline IS NOT NULL THEN EXCLUDED.{side}_moneyline "
                f"ELSE games.{side}_moneyline END") in sql
    for line in ("spread_line", "total_line"):
        assert f"{line} = COALESCE(EXCLUDED.{line}, games.{line})" in sql


def test_ingestion_run_counts_all_games_not_only_quoted(tmp_path, monkeypatch):
    events = []
    install_success_stages(monkeypatch, events)
    monkeypatch.setattr(pipeline.load_games, "load_games_and_market",
                        lambda *_: load_games.GamesLoadResult(272, 112))
    result = pipeline.process_season(2026, data_dir=tmp_path,
                                     allow_missing_pbp=True, skip_acquire=False)
    assert (result.rows_games, result.rows_market) == (272, 112)
    assert events[-1][2]["rows_games"] == 272


def test_missing_market_warning_is_aggregated(tmp_path, caplog):
    frame = pl.concat([source(game_id=f"g-{i}") for i in range(30)])
    load_games.prepare_games(frame)
    warnings = [r for r in caplog.records if "games_without_complete_moneyline_pair" in r.message]
    assert len(warnings) == 1
    assert "season=2026" in warnings[0].message and "=30" in warnings[0].message


def test_real_upsert_expressions_preserve_quotes_and_are_idempotent_offline():
    # SQLite executes the same ON CONFLICT/CASE/COALESCE expressions offline.
    # PostgreSQL FKs and transaction semantics are additionally exercised by validate_local_calendar.py.
    conn = sqlite3.connect(":memory:")
    conn.create_function("now", 0, lambda: "2026-09-13")
    columns = ",".join(f"{name} {'TEXT PRIMARY KEY' if name == 'game_id' else ''}" for name in load_games.GAMES_COLUMNS)
    conn.execute(f"CREATE TABLE games ({columns}, updated_at TEXT)")
    sql = load_games.UPSERT_GAMES_SQL.replace("%s", "?")
    def apply(frame):
        for row in load_games._rows_for_games(load_games.prepare_games(frame)):
            conn.execute(sql, tuple(str(v) if v is not None else None for v in row))
        return conn.execute("SELECT home_moneyline,away_moneyline,spread_line,total_line,home_score,away_score,result FROM games").fetchone()
    assert apply(source(-150, None))[:2] == (None, None)
    assert apply(source(None, 130))[:2] == (None, None)
    complete = apply(source(-150, 130, -3.5, 44.5))
    for partial in (source(-200, None), source(None, 170), source()):
        assert apply(partial) == complete
    revised = source(-200, 170, -4.5, 46).with_columns(
        pl.lit(27).alias("home_score"), pl.lit(20).alias("away_score"), pl.lit(7).alias("result"))
    expected = apply(revised)
    assert expected[:2] == ("-200", "170") and expected[-3:] == ("27", "20", "7")
    assert apply(revised) == expected
    assert apply(source()) == expected
    assert conn.execute("SELECT count(*) FROM games").fetchone()[0] == 1
    conn.close()
