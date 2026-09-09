"""Persistência explícita do ciclo de vida de uma execução sazonal do ETL."""

from __future__ import annotations

import re
from typing import Final

from psycopg2.extensions import connection as PgConnection

RUNNING: Final = "RUNNING"
SUCCEEDED: Final = "SUCCEEDED"
FAILED: Final = "FAILED"
MAX_ERROR_MESSAGE_LENGTH: Final = 1_000

START_RUN_SQL = """
INSERT INTO ingestion_runs
    (season, week, status, rows_pbp, rows_games, error_message, started_at, finished_at)
VALUES (%s, NULL, %s, NULL, NULL, NULL, now(), NULL)
RETURNING id;
"""

SUCCEED_RUN_SQL = """
UPDATE ingestion_runs
SET status = %s,
    rows_pbp = %s,
    rows_games = %s,
    error_message = NULL,
    finished_at = now()
WHERE id = %s;
"""

FAIL_RUN_SQL = """
UPDATE ingestion_runs
SET status = %s,
    rows_pbp = %s,
    rows_games = %s,
    error_message = %s,
    finished_at = now()
WHERE id = %s;
"""

_URL_CREDENTIALS = re.compile(
    r"(?P<scheme>[a-z][a-z0-9+.-]*://)(?P<user>[^\s/:@]+):(?P<secret>[^\s/@]+)@",
    re.IGNORECASE,
)
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(?P<key>"
    r"supabase_db_(?:url|user|password)|gemini_api_key"
    r"|(?:supabase_db_)?(?:password|passwd|pwd|token|api[_ -]?key|secret)"
    r"|aws_access_key_id|aws_secret_access_key|connection[_ -]?string"
    r")\b\s*(?P<sep>[:=])\s*(?P<value>[^\s,;]+)"
)
_URL_QUERY_SECRET = re.compile(
    r"(?i)(?P<prefix>[?&](?:password|token|api[_-]?key|secret)=)[^&#\s]+"
)


def sanitize_error_message(stage: str, exc: BaseException) -> str:
    """Produz mensagem de auditoria sem quebras, credenciais ou payloads extensos."""
    message = " ".join(str(exc).splitlines()).strip()
    message = _URL_CREDENTIALS.sub(r"\g<scheme>***:***@", message)
    message = _URL_QUERY_SECRET.sub(r"\g<prefix>[REDACTED]", message)
    message = _SENSITIVE_ASSIGNMENT.sub(
        lambda match: f"{match.group('key')}{match.group('sep')}[REDACTED]",
        message,
    )
    sanitized = f"stage={stage} exception={type(exc).__name__}:"
    if message:
        sanitized += f" {message}"
    return sanitized[:MAX_ERROR_MESSAGE_LENGTH]


def start_run(conn: PgConnection, season: int) -> int:
    """Insere RUNNING com timestamp do banco e commita antes do pipeline."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(START_RUN_SQL, (season, RUNNING))
            row = cursor.fetchone()
        if not row:
            raise RuntimeError("INSERT de ingestion_runs não retornou id")
        run_id = int(row[0])
        conn.commit()
        return run_id
    except Exception:
        conn.rollback()
        raise


def finish_run_succeeded(
    conn: PgConnection,
    run_id: int,
    *,
    rows_pbp: int,
    rows_games: int,
) -> None:
    """Fecha a execução com SUCCEEDED e contagens finais."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(SUCCEED_RUN_SQL, (SUCCEEDED, rows_pbp, rows_games, run_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def finish_run_failed(
    conn: PgConnection,
    run_id: int,
    *,
    rows_pbp: int,
    rows_games: int,
    error_message: str,
) -> None:
    """Faz rollback da etapa e fecha a execução com FAILED."""
    conn.rollback()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                FAIL_RUN_SQL,
                (FAILED, rows_pbp, rows_games, error_message, run_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# Nomes curtos mantidos como aliases internos convenientes.
succeed_run = finish_run_succeeded


def fail_run(
    conn: PgConnection,
    run_id: int,
    *,
    stage: str,
    error: BaseException,
    rows_pbp: int,
    rows_games: int,
) -> None:
    finish_run_failed(
        conn,
        run_id,
        rows_pbp=rows_pbp,
        rows_games=rows_games,
        error_message=sanitize_error_message(stage, error),
    )
