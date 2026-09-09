"""Popula a tabela de referência `teams` a partir do nflreadpy (nfl.load_teams()).

Preenche team_abbr (PK), team_name, conference, division e logo_url com upsert
idempotente (ON CONFLICT DO UPDATE). Apenas os times que aparecem nos schedules
locais (data/raw/schedules/*/schedules.parquet) são inseridos — evita registrar
siglas históricas/defuntas (ex.: STL, SD, OAK) na tabela servida pela API.

Sem esta tabela populada, a FK `team_week_metrics.team_abbr -> teams` impede a
carga das métricas semanais.
"""

import argparse
import logging
import sys
from pathlib import Path

import nflreadpy as nfl
import polars as pl

from load_metrics import _read_db_config, connect
from nfl_sideline_etl.extract import to_polars
from nfl_sideline_etl.parquet import ParquetSchemaError, season_partition_files
from nfl_sideline_etl.seasons import add_season_arguments, seasons_from_args

LOGGER = logging.getLogger("seed_teams")

TEAMS_SQL = """
INSERT INTO teams (team_abbr, team_name, conference, division, logo_url)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (team_abbr) DO UPDATE SET
    team_name  = CASE
        WHEN EXCLUDED.team_name = EXCLUDED.team_abbr
        THEN teams.team_name
        ELSE EXCLUDED.team_name
    END,
    conference = COALESCE(EXCLUDED.conference, teams.conference),
    division   = COALESCE(EXCLUDED.division, teams.division),
    logo_url   = COALESCE(EXCLUDED.logo_url, teams.logo_url);
"""


def load_teams_reference() -> pl.DataFrame:
    """Baixa a referência de times do nflverse, convertida para Polars (ADR-005)."""
    return to_polars(nfl.load_teams()).select(
        pl.col("team_abbr").alias("team_abbr"),
        pl.col("team_name").alias("team_name"),
        pl.col("team_conf").alias("conference"),
        pl.col("team_division").alias("division"),
        pl.col("team_logo_espn").alias("logo_url"),
    )


def teams_present_in_schedules(data_dir: Path, seasons: tuple[int, ...]) -> set[str]:
    """Siglas presentes somente nos schedules das temporadas solicitadas."""
    files = season_partition_files(data_dir, "schedules", "schedules.parquet", seasons)
    frames: list[pl.LazyFrame] = []
    required = ("season", "home_team", "away_team")
    for path in files:
        schema = pl.read_parquet_schema(path)
        missing = [column for column in required if column not in schema]
        if missing:
            raise ParquetSchemaError(f"Schema incompatível em {path}: colunas ausentes {missing}")
        frames.append(pl.scan_parquet(path).select(required))
    df = pl.concat(frames).collect()
    df = df.filter(pl.col("season").is_in(seasons))
    teams = set(df["home_team"].drop_nulls()) | set(df["away_team"].drop_nulls())
    return teams


def teams_from_schedules(data_dir: Path, seasons: tuple[int, ...]) -> pl.DataFrame:
    """Cria referência mínima local, sem qualquer chamada ao nflverse."""
    abbreviations = sorted(teams_present_in_schedules(data_dir, seasons))
    return pl.DataFrame(
        {
            "team_abbr": abbreviations,
            "team_name": abbreviations,
            "conference": [None] * len(abbreviations),
            "division": [None] * len(abbreviations),
            "logo_url": [None] * len(abbreviations),
        },
        schema={
            "team_abbr": pl.String,
            "team_name": pl.String,
            "conference": pl.String,
            "division": pl.String,
            "logo_url": pl.String,
        },
    )


def upsert_teams(conn, teams: pl.DataFrame) -> int:
    """Persiste os times com upsert por team_abbr; retorna o total enviado."""
    inserted = 0
    try:
        with conn.cursor() as cursor:
            for row in teams.select(
                ["team_abbr", "team_name", "conference", "division", "logo_url"]
            ).iter_rows():
                cursor.execute(TEAMS_SQL, row)
                inserted += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return inserted


def seed_teams(
    conn,
    data_dir: Path,
    seasons: tuple[int, ...],
    *,
    local_only: bool = False,
) -> int:
    """Seleciona e persiste os times, retornando o total processado."""
    active = teams_present_in_schedules(data_dir, seasons)
    if local_only:
        teams = teams_from_schedules(data_dir, seasons)
    else:
        reference = load_teams_reference()
        teams = reference.filter(pl.col("team_abbr").is_in(active)).sort("team_abbr")
        LOGGER.info(
            "Times ativos identificados nos schedules: %d de %d na referência",
            teams.height,
            reference.height,
        )
    if teams.is_empty():
        raise RuntimeError(f"Nenhum time da referência pertence aos schedules {seasons}.")
    count = upsert_teams(conn, teams)
    LOGGER.info("Seed concluído: %d times em teams", count)
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    add_season_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    parser = build_parser()
    args = parser.parse_args(argv)
    seasons = seasons_from_args(parser, args)
    data_dir = args.data_dir or script_dir / "data"

    LOGGER.info("Iniciando seed da tabela teams")
    conn = connect(_read_db_config(project_root))
    try:
        count = seed_teams(conn, data_dir, seasons)
    finally:
        conn.close()
    LOGGER.info("Seed CLI concluído: %d times", count)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        LOGGER.exception("[ERRO SEED TEAMS] %s", exc)
        sys.exit(1)
