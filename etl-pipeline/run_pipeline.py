"""Orquestra uma execução observável e fail-fast do ETL por temporada."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from psycopg2.extensions import connection as PgConnection

import load_games
import load_metrics
import run_local
import seed_teams
from nfl_sideline_etl.ingestion_runs import (
    finish_run_failed,
    finish_run_succeeded,
    sanitize_error_message,
    start_run,
)
from nfl_sideline_etl.seasons import add_season_arguments, seasons_from_args

LOGGER = logging.getLogger("run_pipeline")
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = SCRIPT_DIR / "data"


@dataclass(frozen=True)
class PipelineSeasonResult:
    """Resumo verificável de uma execução sazonal concluída."""

    season: int
    run_id: int
    rows_schedules: int
    rows_teams: int
    rows_games: int
    rows_market: int
    rows_pbp: int
    rows_metrics: int


def _open_checked_connection() -> PgConnection:
    """Abre e confere a conexão PostgreSQL adotada pelo restante do ETL."""
    conn = load_metrics.connect(load_metrics._read_db_config(PROJECT_ROOT))
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        conn.close()
        raise
    return conn


def _validate_local_inputs(
    season: int,
    data_dir: Path,
    *,
    allow_missing_pbp: bool,
) -> run_local.AcquisitionResult:
    """Valida fixtures/Parquets existentes sem chamar nflverse ou S3."""
    schedules = load_games.load_schedules(data_dir, (season,))
    rows_pbp = 0
    try:
        rows_pbp = load_metrics.load_pbp(data_dir, (season,)).height
    except load_metrics.PbpUnavailable:
        if not allow_missing_pbp:
            raise
        LOGGER.warning("season=%d PBP local ausente; permitido explicitamente", season)
    return run_local.AcquisitionResult(
        season=season,
        rows_schedules=schedules.height,
        rows_pbp=rows_pbp,
    )


def process_season(
    season: int,
    *,
    data_dir: Path,
    allow_missing_pbp: bool,
    skip_acquire: bool,
    connection_factory: Callable[[], PgConnection] | None = None,
) -> PipelineSeasonResult:
    """Executa uma temporada; depois de RUNNING, toda falha é registrada e propagada."""
    factory = connection_factory or _open_checked_connection
    conn = factory()
    run_id: int | None = None
    stage = "start_run"
    rows_schedules = 0
    rows_teams = 0
    rows_games = 0
    rows_market = 0
    rows_pbp = 0
    rows_metrics = 0
    try:
        run_id = start_run(conn, season)

        stage = "acquire"
        if skip_acquire:
            acquired = _validate_local_inputs(
                season,
                data_dir,
                allow_missing_pbp=allow_missing_pbp,
            )
        else:
            acquired = run_local.acquire_season(
                season,
                data_dir=data_dir,
                schedules=True,
                pbp=True,
                allow_missing_pbp=allow_missing_pbp,
                upload_s3=False,
            )
        rows_schedules = acquired.rows_schedules
        rows_pbp = acquired.rows_pbp

        stage = "seed_teams"
        rows_teams = seed_teams.seed_teams(
            conn,
            data_dir,
            (season,),
            local_only=skip_acquire,
        )

        stage = "games_market"
        games_result = load_games.load_games_and_market(conn, data_dir, (season,))
        rows_games = games_result.rows_games
        rows_market = games_result.rows_market

        stage = "metrics"
        metrics_result = load_metrics.load_and_persist_metrics(
            conn,
            data_dir,
            (season,),
            allow_empty=allow_missing_pbp,
        )
        rows_pbp = metrics_result.rows_pbp
        rows_metrics = metrics_result.rows_metrics

        stage = "finish_success"
        finish_run_succeeded(conn, run_id, rows_pbp=rows_pbp, rows_games=rows_games)
        result = PipelineSeasonResult(
            season=season,
            run_id=run_id,
            rows_schedules=rows_schedules,
            rows_teams=rows_teams,
            rows_games=rows_games,
            rows_market=rows_market,
            rows_pbp=rows_pbp,
            rows_metrics=rows_metrics,
        )
        LOGGER.info(
            "season=%d run_id=%d status=SUCCEEDED rows_teams=%d rows_games=%d "
            "rows_market=%d rows_pbp=%d rows_metrics=%d",
            season,
            run_id,
            rows_teams,
            rows_games,
            rows_market,
            rows_pbp,
            rows_metrics,
        )
        return result
    except Exception as original_error:
        if run_id is not None:
            try:
                finish_run_failed(
                    conn,
                    run_id,
                    rows_pbp=rows_pbp,
                    rows_games=rows_games,
                    error_message=sanitize_error_message(stage, original_error),
                )
            except Exception as status_error:
                LOGGER.error(
                    "Falha secundária ao registrar FAILED: %s",
                    sanitize_error_message("finish_failed", status_error),
                )
        raise
    finally:
        conn.close()


def run_pipeline(
    seasons: tuple[int, ...],
    *,
    data_dir: Path,
    allow_missing_pbp: bool,
    skip_acquire: bool,
    connection_factory: Callable[[], PgConnection] | None = None,
) -> tuple[PipelineSeasonResult, ...]:
    """Processa temporadas sequencialmente e para na primeira falha."""
    results: list[PipelineSeasonResult] = []
    for season in seasons:
        results.append(
            process_season(
                season,
                data_dir=data_dir,
                allow_missing_pbp=allow_missing_pbp,
                skip_acquire=skip_acquire,
                connection_factory=connection_factory,
            )
        )
    return tuple(results)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    add_season_arguments(parser)
    parser.add_argument(
        "--allow-missing-pbp",
        action="store_true",
        help="Permite sucesso com rows_pbp=0 quando PBP não estiver disponível.",
    )
    parser.add_argument(
        "--skip-acquire",
        action="store_true",
        help="Usa somente Parquets locais existentes, sem nflverse e sem S3.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    seasons = seasons_from_args(parser, args)
    data_dir = args.data_dir or DEFAULT_DATA_DIR
    try:
        run_pipeline(
            seasons,
            data_dir=data_dir,
            allow_missing_pbp=args.allow_missing_pbp,
            skip_acquire=args.skip_acquire,
        )
    except Exception as exc:
        LOGGER.error("Pipeline abortado: %s", sanitize_error_message("cli", exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
