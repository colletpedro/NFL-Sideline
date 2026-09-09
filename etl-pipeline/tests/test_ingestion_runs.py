from __future__ import annotations

import pytest

from nfl_sideline_etl import ingestion_runs


class RecordingCursor:
    def __init__(self, connection: "RecordingConnection") -> None:
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql: str, params: tuple[object, ...]) -> None:
        self.connection.executed.append((sql, params))
        if self.connection.fail_execute:
            raise RuntimeError("status write failed")

    def fetchone(self) -> tuple[int]:
        return (self.connection.run_id,)


class RecordingConnection:
    def __init__(self, *, run_id: int = 41, fail_execute: bool = False) -> None:
        self.run_id = run_id
        self.fail_execute = fail_execute
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_start_run_records_running_with_database_timestamp_and_parameters() -> None:
    conn = RecordingConnection(run_id=77)
    assert ingestion_runs.start_run(conn, 2025) == 77
    sql, params = conn.executed[0]
    assert params == (2025, "RUNNING")
    assert "%s" in sql
    assert "VALUES (%s, NULL, %s" in " ".join(sql.split())
    assert "now()" in sql
    assert conn.commits == 1


def test_finish_run_succeeded_records_counts_timestamp_and_null_error() -> None:
    conn = RecordingConnection()
    ingestion_runs.finish_run_succeeded(conn, 41, rows_pbp=123, rows_games=18)
    sql, params = conn.executed[0]
    assert params == ("SUCCEEDED", 123, 18, 41)
    assert "error_message = NULL" in sql
    assert "finished_at = now()" in sql
    assert conn.commits == 1


def test_finish_run_failed_rolls_back_stage_then_records_failure() -> None:
    conn = RecordingConnection()
    ingestion_runs.finish_run_failed(
        conn,
        41,
        rows_pbp=9,
        rows_games=2,
        error_message="stage=metrics exception=ValueError: bad data",
    )
    _, params = conn.executed[0]
    assert params == (
        "FAILED",
        9,
        2,
        "stage=metrics exception=ValueError: bad data",
        41,
    )
    assert conn.rollbacks == 1
    assert conn.commits == 1


def test_failed_status_write_rolls_back_and_raises() -> None:
    conn = RecordingConnection(fail_execute=True)
    with pytest.raises(RuntimeError, match="status write failed"):
        ingestion_runs.finish_run_failed(
            conn,
            41,
            rows_pbp=0,
            rows_games=0,
            error_message="safe",
        )
    assert conn.rollbacks == 2


def test_error_sanitization_redacts_credentials_and_removes_newlines() -> None:
    url_secret = "super-" + "secret"
    password = "hunter" + "2"
    token = "a" + "bc"
    api_key = "qwert" + "y"
    url_token = "url-" + "secret"
    database_url = "postgresql" + "://admin:" + url_secret + "@localhost/db"
    error = RuntimeError(
        f"failed {database_url}\n"
        f"password={password} token={token} API_KEY={api_key} "
        "SUPABASE_DB_USER=postgres SUPABASE_DB_URL=jdbc:postgresql://localhost/db "
        f"https://example.test/path?token={url_token}&ok=1"
    )
    message = ingestion_runs.sanitize_error_message("games_market", error)
    assert message.startswith("stage=games_market exception=RuntimeError:")
    assert "\n" not in message
    for secret in (
        url_secret, password, token, api_key, url_token, "SUPABASE_DB_USER=postgres",
        "SUPABASE_DB_URL=jdbc:postgresql://localhost/db",
    ):
        assert secret not in message
    assert "[REDACTED]" in message


def test_error_sanitization_is_limited_to_one_thousand_characters() -> None:
    message = ingestion_runs.sanitize_error_message("metrics", ValueError("x" * 2_000))
    assert len(message) == ingestion_runs.MAX_ERROR_MESSAGE_LENGTH == 1_000
