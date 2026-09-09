"""Adquire schedules e play-by-play do nflverse para Parquet local."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import polars as pl

from nfl_sideline_etl.extract import (
    SourceDataNotPublishedError,
    download_pbp,
    download_schedules,
)
from nfl_sideline_etl.seasons import (
    add_season_arguments,
    current_nfl_season,
    seasons_from_args,
)

LOGGER = logging.getLogger("run_local")
S3_BUCKET = "nfl-sideline-lake"
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"


class MissingPbpError(RuntimeError):
    """Indica ausência esperada de PBP para uma temporada ainda sem jogadas."""


@dataclass(frozen=True)
class AcquisitionResult:
    """Contagens dos dados brutos efetivamente gravados para uma temporada."""

    season: int
    rows_schedules: int
    rows_pbp: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    add_season_arguments(parser)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--schedules-only", action="store_true")
    source.add_argument("--pbp-only", action="store_true")
    parser.add_argument(
        "--allow-missing-pbp",
        action="store_true",
        help="Tolera somente PBP vazio, futuro ou HTTP 404 ainda não publicado.",
    )
    parser.add_argument(
        "--upload-s3",
        action="store_true",
        help="Envia explicitamente schedules ao caminho S3 legado.",
    )
    return parser


def _write_nonempty_parquet(
    frame: pl.DataFrame,
    *,
    season: int,
    source: str,
    data_dir: Path,
) -> Path:
    if frame.is_empty():
        if source == "pbp":
            raise MissingPbpError(f"PBP {season} sem jogadas")
        raise RuntimeError(f"Schedules {season} retornou zero linhas")
    path = data_dir / "raw" / source / f"season={season}" / f"{source}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path)
    LOGGER.info("season=%d source=%s rows=%d path=%s", season, source, frame.height, path)
    return path


def acquire_season(
    season: int,
    *,
    data_dir: Path,
    schedules: bool,
    pbp: bool,
    allow_missing_pbp: bool,
    upload_s3: bool,
    schedules_loader: Callable[[int], pl.DataFrame] = download_schedules,
    pbp_loader: Callable[[int], pl.DataFrame] = download_pbp,
    s3_uploader: Callable[[str, str, str], None] | None = None,
) -> AcquisitionResult:
    """Adquire uma temporada, validando vazio e mantendo S3 estritamente opt-in."""
    rows_schedules = 0
    rows_pbp = 0
    if schedules:
        schedules_frame = schedules_loader(season)
        schedules_path = _write_nonempty_parquet(
            schedules_frame, season=season, source="schedules", data_dir=data_dir
        )
        rows_schedules = schedules_frame.height
        if upload_s3:
            if s3_uploader is None:
                from nfl_sideline_etl.load import upload_parquet_to_s3

                s3_uploader = upload_parquet_to_s3
            s3_key = f"raw/schedules/season={season}/schedules.parquet"
            s3_uploader(str(schedules_path), S3_BUCKET, s3_key)
            LOGGER.info("season=%d source=schedules uploaded=s3://%s/%s", season, S3_BUCKET, s3_key)

    if pbp:
        try:
            if season > current_nfl_season():
                raise MissingPbpError(
                    f"PBP {season} ainda não é suportado; temporada NFL corrente é "
                    f"{current_nfl_season()}"
                )
            pbp_frame = pbp_loader(season)
            _write_nonempty_parquet(pbp_frame, season=season, source="pbp", data_dir=data_dir)
            rows_pbp = pbp_frame.height
        except (MissingPbpError, SourceDataNotPublishedError) as exc:
            if not allow_missing_pbp:
                raise
            LOGGER.warning("season=%d source=pbp not_published_or_empty=%s", season, exc)
    return AcquisitionResult(
        season=season,
        rows_schedules=rows_schedules,
        rows_pbp=rows_pbp,
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    seasons = seasons_from_args(parser, args)
    data_dir = args.data_dir or DEFAULT_DATA_DIR
    if args.pbp_only and args.upload_s3:
        parser.error("--upload-s3 só se aplica a schedules e não pode ser usado com --pbp-only")

    for season in seasons:
        acquire_season(
            season,
            data_dir=data_dir,
            schedules=not args.pbp_only,
            pbp=not args.schedules_only,
            allow_missing_pbp=args.allow_missing_pbp,
            upload_s3=args.upload_s3,
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        LOGGER.exception("[ERRO DE EXTRAÇÃO] %s", exc)
        sys.exit(1)
