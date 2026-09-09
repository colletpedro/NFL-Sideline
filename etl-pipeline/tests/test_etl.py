from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import polars as pl
import pytest

import load_games
import load_metrics
import run_local
import seed_teams
from nfl_sideline_etl import extract
from nfl_sideline_etl.extract import SourceDataNotPublishedError
from nfl_sideline_etl.parquet import NoSeasonDataError, ParquetSchemaError
from nfl_sideline_etl.seasons import (
    add_season_arguments,
    current_nfl_season,
    normalize_seasons,
    seasons_from_args,
)


def schedule_frame(season: int, *, game_id: str = "game-1") -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": [game_id],
            "season": [season],
            "week": [1],
            "game_type": ["REG"],
            "gameday": [f"{season}-09-01"],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_score": [None],
            "away_score": [None],
            "result": [None],
            "spread_line": [-3.5],
            "total_line": [44.5],
            "home_moneyline": [-150],
            "away_moneyline": [130],
        }
    )


def pbp_frame(season: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [season, season, season, season],
            "week": [1, 1, 1, 1],
            "posteam": ["AAA", "AAA", "BBB", "BBB"],
            "defteam": ["BBB", "BBB", "AAA", "AAA"],
            "epa": [1.0, -0.5, 0.5, -1.0],
            "play_type": ["pass", "run", "pass", "run"],
            "qb_kneel": [0, 0, 0, 0],
            "qb_spike": [0, 0, 0, 0],
        }
    )


def write_partition(frame: pl.DataFrame, root: Path, source: str, season: int) -> Path:
    path = root / "raw" / source / f"season={season}" / f"{source}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path)
    return path


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class FakeHttpError(RuntimeError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.response = FakeResponse(status_code)


def wrapped_connection_error(status_code: int | None = None) -> ConnectionError:
    error = ConnectionError("nflreadpy download failed")
    if status_code is not None:
        error.__cause__ = FakeHttpError(status_code)
    return error


def test_current_season_february_and_march() -> None:
    assert current_nfl_season(date(2026, 2, 28)) == 2025
    assert current_nfl_season(date(2026, 3, 1)) == 2026


def test_parsing_one_and_multiple_season_flags() -> None:
    parser = argparse.ArgumentParser()
    add_season_arguments(parser)
    one = parser.parse_args(["--season", "2025"])
    many = parser.parse_args(["--season", "2026", "--season", "2025"])
    assert seasons_from_args(parser, one, today=date(2026, 9, 1)) == (2025,)
    assert seasons_from_args(parser, many, today=date(2026, 9, 1)) == (2025, 2026)


def test_seasons_are_sorted_deduplicated_and_validated() -> None:
    today = date(2026, 9, 1)
    assert normalize_seasons([2026, 2025, 2026], today=today) == (2025, 2026)
    assert normalize_seasons(None, today=today) == (2026,)
    with pytest.raises(ValueError, match="1999..2027"):
        normalize_seasons([1998], today=today)


def test_extract_accepts_polars_return(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = pl.DataFrame({"season": [2025]})
    monkeypatch.setattr(extract.nfl, "load_schedules", lambda seasons: expected)
    assert extract.download_schedules(2025).equals(expected)


def test_extract_converts_pandas_return(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        extract.nfl, "load_pbp", lambda seasons: pd.DataFrame({"season": [2025], "epa": [0.1]})
    )
    result = extract.download_pbp(2025)
    assert isinstance(result, pl.DataFrame)
    assert result.to_dict(as_series=False) == {"season": [2025], "epa": [0.1]}


def test_acquisition_writes_partitioned_paths_without_implicit_s3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "must-not-trigger-upload")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-trigger-upload")
    uploads: list[tuple[str, str, str]] = []
    run_local.acquire_season(
        2025,
        data_dir=tmp_path,
        schedules=True,
        pbp=True,
        allow_missing_pbp=False,
        upload_s3=False,
        schedules_loader=lambda season: schedule_frame(season),
        pbp_loader=lambda season: pbp_frame(season),
        s3_uploader=lambda *args: uploads.append(args),
    )
    schedules_path = tmp_path / "raw/schedules/season=2025/schedules.parquet"
    pbp_path = tmp_path / "raw/pbp/season=2025/pbp.parquet"
    assert pl.read_parquet(schedules_path).height == 1
    assert pl.read_parquet(pbp_path).height == 4
    assert uploads == []


def test_missing_pbp_fails_by_default_and_is_explicitly_allowed(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    kwargs = dict(
        season=2026,
        data_dir=tmp_path,
        schedules=False,
        pbp=True,
        upload_s3=False,
        pbp_loader=lambda season: pl.DataFrame(),
    )
    with pytest.raises(run_local.MissingPbpError):
        run_local.acquire_season(allow_missing_pbp=False, **kwargs)
    run_local.acquire_season(allow_missing_pbp=True, **kwargs)
    assert not (tmp_path / "raw/pbp/season=2026/pbp.parquet").exists()
    assert "not_published_or_empty" in caplog.text


def test_next_season_pbp_is_not_requested_when_missing_is_allowed(tmp_path: Path) -> None:
    called = False

    def unexpected_loader(season: int) -> pl.DataFrame:
        nonlocal called
        called = True
        return pbp_frame(season)

    next_season = current_nfl_season() + 1
    run_local.acquire_season(
        next_season,
        data_dir=tmp_path,
        schedules=False,
        pbp=True,
        allow_missing_pbp=True,
        upload_s3=False,
        pbp_loader=unexpected_loader,
    )
    assert not called


def test_pbp_http_404_is_classified_and_tolerated_only_with_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing_pbp(seasons: list[int]) -> pl.DataFrame:
        raise wrapped_connection_error(404)

    monkeypatch.setattr(extract.nfl, "load_pbp", missing_pbp)
    with pytest.raises(SourceDataNotPublishedError) as caught:
        extract.download_pbp(2025)
    assert "2025" in str(caught.value)
    assert isinstance(caught.value.__cause__, ConnectionError)

    kwargs = dict(
        season=2025,
        data_dir=tmp_path,
        schedules=False,
        pbp=True,
        upload_s3=False,
        pbp_loader=extract.download_pbp,
    )
    with pytest.raises(SourceDataNotPublishedError):
        run_local.acquire_season(allow_missing_pbp=False, **kwargs)
    run_local.acquire_season(allow_missing_pbp=True, **kwargs)


def test_pbp_http_503_remains_fatal_with_allow_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        extract.nfl, "load_pbp", lambda seasons: (_ for _ in ()).throw(wrapped_connection_error(503))
    )
    with pytest.raises(ConnectionError):
        run_local.acquire_season(
            2025,
            data_dir=tmp_path,
            schedules=False,
            pbp=True,
            allow_missing_pbp=True,
            upload_s3=False,
            pbp_loader=extract.download_pbp,
        )


@pytest.mark.parametrize(
    "pbp_loader, expected",
    [
        (lambda season: (_ for _ in ()).throw(wrapped_connection_error()), ConnectionError),
        (lambda season: (_ for _ in ()).throw(ValueError("parquet inválido")), ValueError),
    ],
)
def test_pbp_transport_and_parsing_errors_remain_fatal_with_allow_missing(
    tmp_path: Path, pbp_loader, expected: type[Exception]
) -> None:
    with pytest.raises(expected):
        run_local.acquire_season(
            2025,
            data_dir=tmp_path,
            schedules=False,
            pbp=True,
            allow_missing_pbp=True,
            upload_s3=False,
            pbp_loader=pbp_loader,
        )


@pytest.mark.parametrize("status_code", [404, 503, None])
def test_schedules_download_errors_are_never_tolerated(
    tmp_path: Path, status_code: int | None
) -> None:
    with pytest.raises(ConnectionError):
        run_local.acquire_season(
            2025,
            data_dir=tmp_path,
            schedules=True,
            pbp=False,
            allow_missing_pbp=True,
            upload_s3=False,
            schedules_loader=lambda season: (_ for _ in ()).throw(
                wrapped_connection_error(status_code)
            ),
        )


def test_schedules_are_limited_to_requested_seasons(tmp_path: Path) -> None:
    write_partition(schedule_frame(2024, game_id="old"), tmp_path, "schedules", 2024)
    write_partition(schedule_frame(2025, game_id="wanted"), tmp_path, "schedules", 2025)
    result = load_games.load_schedules(tmp_path, (2025,))
    assert result["game_id"].to_list() == ["wanted"]
    with pytest.raises(NoSeasonDataError, match="nenhum pertence"):
        load_games.load_schedules(tmp_path, (2026,))


def test_pbp_is_limited_to_requested_seasons(tmp_path: Path) -> None:
    write_partition(pbp_frame(2024), tmp_path, "pbp", 2024)
    write_partition(pbp_frame(2025), tmp_path, "pbp", 2025)
    result = load_metrics.load_pbp(tmp_path, (2025,))
    assert result["season"].unique().to_list() == [2025]


def test_load_metrics_allow_empty_controls_success(tmp_path: Path) -> None:
    with pytest.raises(load_metrics.PbpUnavailable):
        load_metrics.main(["--season", "2025", "--data-dir", str(tmp_path)])
    assert (
        load_metrics.main(
            ["--season", "2025", "--data-dir", str(tmp_path), "--allow-empty"]
        )
        == 0
    )


def test_team_selection_is_limited_to_requested_schedules(tmp_path: Path) -> None:
    write_partition(schedule_frame(2024), tmp_path, "schedules", 2024)
    current = schedule_frame(2025).with_columns(
        pl.lit("CCC").alias("home_team"), pl.lit("DDD").alias("away_team")
    )
    write_partition(current, tmp_path, "schedules", 2025)
    assert seed_teams.teams_present_in_schedules(tmp_path, (2025,)) == {"CCC", "DDD"}


def test_moneyline_and_fair_value_calculation() -> None:
    assert load_games.american_odds_to_implied(-150) == Decimal("0.6")
    assert load_games.american_odds_to_implied(150) == Decimal("0.4")
    games = load_games.prepare_games(schedule_frame(2025))
    market = load_games.build_market_rows(games)[0]
    assert market["home_implied_fair"] + market["away_implied_fair"] == Decimal(1)
    assert market["vig_pct"] > 0


def test_minimal_offense_and_defense_metrics() -> None:
    metrics = load_metrics.build_team_week_metrics(pbp_frame(2025))
    aaa = metrics.filter(pl.col("team_abbr") == "AAA").row(0, named=True)
    assert aaa["off_epa_play"] == pytest.approx(0.25)
    assert aaa["off_epa_pass"] == pytest.approx(1.0)
    assert aaa["off_epa_rush"] == pytest.approx(-0.5)
    assert aaa["dropback_rate"] == pytest.approx(0.5)
    assert aaa["def_epa_play"] == pytest.approx(-0.25)
    assert aaa["plays_offense"] == 2
    assert aaa["plays_defense"] == 2


def test_incompatible_parquet_schema_is_a_real_error_even_when_empty_allowed(
    tmp_path: Path,
) -> None:
    write_partition(pl.DataFrame({"season": [2025]}), tmp_path, "pbp", 2025)
    with pytest.raises(ParquetSchemaError, match="Schema incompatível"):
        load_metrics.main(
            ["--season", "2025", "--data-dir", str(tmp_path), "--allow-empty"]
        )
