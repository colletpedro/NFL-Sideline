from __future__ import annotations

from pathlib import Path

import pytest

import load_games
import load_metrics
import run_local
import run_pipeline as pipeline
from test_etl import pbp_frame, schedule_frame, write_partition


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False
        self.rollbacks = 0

    def close(self) -> None:
        self.closed = True

    def rollback(self) -> None:
        self.rollbacks += 1


def install_success_stages(monkeypatch: pytest.MonkeyPatch, events: list[object]) -> None:
    monkeypatch.setattr(pipeline, "_open_checked_connection", lambda: FakeConnection())

    def start(_conn, season: int) -> int:
        events.append(("start", season))
        return 100 + season

    def acquire(season: int, **kwargs) -> run_local.AcquisitionResult:
        events.append(("acquire", season, kwargs["upload_s3"]))
        return run_local.AcquisitionResult(season, 16, 120)

    def seed(_conn, _data_dir, seasons, *, local_only: bool) -> int:
        events.append(("seed", seasons[0], local_only))
        return 2

    def games(_conn, _data_dir, seasons) -> load_games.GamesLoadResult:
        events.append(("games", seasons[0]))
        return load_games.GamesLoadResult(rows_games=8, rows_market=8)

    def metrics(_conn, _data_dir, seasons, *, allow_empty: bool):
        events.append(("metrics", seasons[0], allow_empty))
        return load_metrics.MetricsLoadResult(rows_pbp=120, rows_metrics=12)

    def succeeded(_conn, run_id: int, **counts) -> None:
        events.append(("succeeded", run_id, counts))

    def failed(_conn, run_id: int, **details) -> None:
        events.append(("failed", run_id, details))

    monkeypatch.setattr(pipeline, "start_run", start)
    monkeypatch.setattr(pipeline.run_local, "acquire_season", acquire)
    monkeypatch.setattr(pipeline.seed_teams, "seed_teams", seed)
    monkeypatch.setattr(pipeline.load_games, "load_games_and_market", games)
    monkeypatch.setattr(pipeline.load_metrics, "load_and_persist_metrics", metrics)
    monkeypatch.setattr(pipeline, "finish_run_succeeded", succeeded)
    monkeypatch.setattr(pipeline, "finish_run_failed", failed)


def test_orchestrator_runs_stages_in_exact_order_and_records_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []
    install_success_stages(monkeypatch, events)
    result = pipeline.process_season(
        2025,
        data_dir=tmp_path,
        allow_missing_pbp=False,
        skip_acquire=False,
    )
    assert [event[0] for event in events] == [
        "start",
        "acquire",
        "seed",
        "games",
        "metrics",
        "succeeded",
    ]
    assert events[-1][2] == {"rows_pbp": 120, "rows_games": 8}
    assert result.rows_schedules == 16
    assert result.rows_teams == 2
    assert result.rows_games == result.rows_market == 8
    assert result.rows_pbp == 120
    assert result.rows_metrics == 12


def test_missing_pbp_can_succeed_with_zero_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []
    install_success_stages(monkeypatch, events)
    monkeypatch.setattr(
        pipeline.load_metrics,
        "load_and_persist_metrics",
        lambda *_args, **_kwargs: load_metrics.MetricsLoadResult(0, 0),
    )
    result = pipeline.process_season(
        2025,
        data_dir=tmp_path,
        allow_missing_pbp=True,
        skip_acquire=False,
    )
    assert result.rows_pbp == 0
    assert events[-1][0] == "succeeded"
    assert events[-1][2]["rows_pbp"] == 0


@pytest.mark.parametrize(
    "failing_stage,expected_stage",
    [
        ("acquire", "acquire"),
        ("seed", "seed_teams"),
        ("games", "games_market"),
        ("metrics", "metrics"),
    ],
)
def test_each_intermediate_failure_records_failed_and_never_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_stage: str,
    expected_stage: str,
) -> None:
    events: list[object] = []
    install_success_stages(monkeypatch, events)

    if failing_stage == "acquire":
        monkeypatch.setattr(
            pipeline.run_local,
            "acquire_season",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )
    elif failing_stage == "seed":
        monkeypatch.setattr(
            pipeline.seed_teams,
            "seed_teams",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )
    elif failing_stage == "games":
        monkeypatch.setattr(
            pipeline.load_games,
            "load_games_and_market",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )
    else:
        monkeypatch.setattr(
            pipeline.load_metrics,
            "load_and_persist_metrics",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )

    with pytest.raises(RuntimeError, match="boom"):
        pipeline.process_season(
            2025,
            data_dir=tmp_path,
            allow_missing_pbp=False,
            skip_acquire=False,
        )
    failed = [event for event in events if event[0] == "failed"]
    assert len(failed) == 1
    assert f"stage={expected_stage}" in failed[0][2]["error_message"]
    assert not [event for event in events if event[0] == "succeeded"]


def test_one_independent_run_is_created_per_season(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []
    install_success_stages(monkeypatch, events)
    results = pipeline.run_pipeline(
        (2024, 2025),
        data_dir=tmp_path,
        allow_missing_pbp=False,
        skip_acquire=False,
    )
    assert [event for event in events if event[0] == "start"] == [
        ("start", 2024),
        ("start", 2025),
    ]
    assert [result.season for result in results] == [2024, 2025]


def test_multiple_seasons_are_fail_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    processed: list[int] = []

    def fail_first(season: int, **_kwargs):
        processed.append(season)
        raise RuntimeError("stop")

    monkeypatch.setattr(pipeline, "process_season", fail_first)
    with pytest.raises(RuntimeError, match="stop"):
        pipeline.run_pipeline(
            (2024, 2025),
            data_dir=tmp_path,
            allow_missing_pbp=False,
            skip_acquire=False,
        )
    assert processed == [2024]


def test_skip_acquire_uses_only_local_validation_and_local_seed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []
    install_success_stages(monkeypatch, events)
    monkeypatch.setattr(
        pipeline.run_local,
        "acquire_season",
        lambda *_args, **_kwargs: pytest.fail("nflverse acquisition must not run"),
    )
    monkeypatch.setattr(
        pipeline,
        "_validate_local_inputs",
        lambda season, *_args, **_kwargs: run_local.AcquisitionResult(season, 4, 10),
    )
    pipeline.process_season(
        2025,
        data_dir=tmp_path,
        allow_missing_pbp=False,
        skip_acquire=True,
    )
    seed_event = next(event for event in events if event[0] == "seed")
    assert seed_event[2] is True
    assert not [event for event in events if event[0] == "acquire"]


def test_skip_acquire_validates_real_local_inputs(tmp_path: Path) -> None:
    write_partition(schedule_frame(2025), tmp_path, "schedules", 2025)
    write_partition(pbp_frame(2025), tmp_path, "pbp", 2025)
    result = pipeline._validate_local_inputs(2025, tmp_path, allow_missing_pbp=False)
    assert (result.rows_schedules, result.rows_pbp) == (1, 4)


def test_skip_acquire_requires_schedules_and_controls_missing_pbp(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        pipeline._validate_local_inputs(2025, tmp_path, allow_missing_pbp=True)
    write_partition(schedule_frame(2025), tmp_path, "schedules", 2025)
    with pytest.raises(load_metrics.PbpUnavailable):
        pipeline._validate_local_inputs(2025, tmp_path, allow_missing_pbp=False)
    result = pipeline._validate_local_inputs(2025, tmp_path, allow_missing_pbp=True)
    assert result.rows_pbp == 0


def test_secondary_failed_write_does_not_replace_original_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []
    install_success_stages(monkeypatch, events)
    original = ValueError("original failure")
    monkeypatch.setattr(
        pipeline.seed_teams,
        "seed_teams",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(original),
    )
    monkeypatch.setattr(
        pipeline,
        "finish_run_failed",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("secondary failure")),
    )
    with pytest.raises(ValueError) as caught:
        pipeline.process_season(
            2025,
            data_dir=tmp_path,
            allow_missing_pbp=False,
            skip_acquire=False,
        )
    assert caught.value is original
