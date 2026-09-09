from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import load_games


def schedule(
    *,
    game_id: str = "score-game",
    home_score: object = None,
    away_score: object = None,
    result: object = None,
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": [game_id],
            "season": [2025],
            "week": [1],
            "game_type": ["REG"],
            "gameday": ["2025-09-01"],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_score": [home_score],
            "away_score": [away_score],
            "result": [result],
            "spread_line": [-3.5],
            "total_line": [44.5],
            "home_moneyline": [-150],
            "away_moneyline": [130],
        },
        strict=False,
    )


def test_future_game_without_scores_is_valid() -> None:
    game = load_games.prepare_games(schedule()).row(0, named=True)
    assert game["home_score"] is None
    assert game["away_score"] is None
    assert game["result"] is None


def test_completed_game_with_valid_score_is_preserved() -> None:
    game = load_games.prepare_games(schedule(home_score=27, away_score=20, result=7)).row(
        0, named=True
    )
    assert (game["home_score"], game["away_score"], game["result"]) == (27, 20, 7)


def test_tie_with_zero_result_is_valid() -> None:
    game = load_games.prepare_games(schedule(home_score=20, away_score=20, result=0)).row(
        0, named=True
    )
    assert game["result"] == 0


@pytest.mark.parametrize(
    ("home_score", "away_score", "result"),
    [
        (20, None, None),
        (None, 20, None),
        (None, None, 1),
        (20, 17, None),
        (20, None, 20),
        (None, 17, -17),
    ],
)
def test_every_partial_score_trio_is_rejected(
    home_score: object,
    away_score: object,
    result: object,
) -> None:
    with pytest.raises(ValueError, match="game_id=partial") as caught:
        load_games.prepare_games(
            schedule(
                game_id="partial",
                home_score=home_score,
                away_score=away_score,
                result=result,
            )
        )
    assert "home_team" not in str(caught.value)


@pytest.mark.parametrize("home_score,away_score", [(-1, 3), (3, -1)])
def test_negative_score_is_rejected(home_score: int, away_score: int) -> None:
    with pytest.raises(ValueError, match="game_id=negative"):
        load_games.prepare_games(
            schedule(game_id="negative", home_score=home_score, away_score=away_score)
        )


def test_inconsistent_result_is_rejected() -> None:
    with pytest.raises(ValueError, match="game_id=inconsistent"):
        load_games.prepare_games(
            schedule(game_id="inconsistent", home_score=24, away_score=17, result=6)
        )


@pytest.mark.parametrize("field", ["home_score", "away_score", "result"])
def test_fractional_score_fields_are_rejected(field: str) -> None:
    values = {"home_score": 24, "away_score": 17, "result": 7}
    values[field] = 7.5
    with pytest.raises(ValueError, match=r"game_id=fractional.*não é inteiro"):
        load_games.prepare_games(schedule(game_id="fractional", **values))


def test_new_score_columns_are_serialized_in_insert_order() -> None:
    games = load_games.prepare_games(schedule(home_score=24, away_score=17, result=7))
    row = load_games._rows_for_games(games)[0]
    assert row[7:10] == (24, 17, 7)
    assert len(row) == len(load_games.GAMES_COLUMNS) == 14


def test_upsert_preserves_or_replaces_the_entire_trio_and_updates_timestamp() -> None:
    sql = " ".join(load_games.UPSERT_GAMES_SQL.split())
    assert "home_score = CASE WHEN EXCLUDED.home_score IS NULL THEN games.home_score ELSE EXCLUDED.home_score END" in sql
    assert "away_score = CASE WHEN EXCLUDED.home_score IS NULL THEN games.away_score ELSE EXCLUDED.away_score END" in sql
    assert "result = CASE WHEN EXCLUDED.home_score IS NULL THEN games.result ELSE EXCLUDED.result END" in sql
    assert "updated_at = now()" in sql


def test_non_null_score_correction_is_sent_to_postgres() -> None:
    executed: list[tuple[str, tuple[object, ...]]] = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, sql: str, params: tuple[object, ...]) -> None:
            executed.append((sql, params))

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

    games = load_games.prepare_games(schedule(home_score=31, away_score=28, result=3))
    assert load_games.upsert_games(Connection(), games) == 1
    assert executed[0][1][7:10] == (31, 28, 3)
