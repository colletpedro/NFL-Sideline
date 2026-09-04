"""Popula a tabela de referência `teams` a partir do nflreadpy (nfl.load_teams()).

Preenche team_abbr (PK), team_name, conference, division e logo_url com upsert
idempotente (ON CONFLICT DO UPDATE). Apenas os times que aparecem nos schedules
locais (data/raw/schedules/*/schedules.parquet) são inseridos — evita registrar
siglas históricas/defuntas (ex.: STL, SD, OAK) na tabela servida pela API.

Sem esta tabela populada, a FK `team_week_metrics.team_abbr -> teams` impede a
carga das métricas semanais.
"""

import logging
import sys
from pathlib import Path

import nflreadpy as nfl
import polars as pl

from load_metrics import _read_db_config, connect

LOGGER = logging.getLogger("seed_teams")

TEAMS_SQL = """
INSERT INTO teams (team_abbr, team_name, conference, division, logo_url)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (team_abbr) DO UPDATE SET
    team_name  = EXCLUDED.team_name,
    conference = EXCLUDED.conference,
    division   = EXCLUDED.division,
    logo_url   = EXCLUDED.logo_url;
"""


def load_teams_reference() -> pl.DataFrame:
    """Baixa a referência de times do nflverse, convertida para Polars (ADR-005)."""
    df = nfl.load_teams()
    if not isinstance(df, pl.DataFrame):
        df = pl.from_pandas(df)
    return df.select(
        pl.col("team_abbr").alias("team_abbr"),
        pl.col("team_name").alias("team_name"),
        pl.col("team_conf").alias("conference"),
        pl.col("team_division").alias("division"),
        pl.col("team_logo_espn").alias("logo_url"),
    )


def teams_present_in_schedules(data_dir: Path) -> set[str]:
    """Conjunto de siglas presentes nos schedules locais (fonte dos times ativos)."""
    files = sorted(data_dir.glob("raw/schedules/*/schedules.parquet"))
    if not files:
        raise FileNotFoundError(
            f"Nenhum schedules.parquet em {data_dir / 'raw' / 'schedules'}: "
            "execute run_local.py antes."
        )
    frames = [pl.scan_parquet(f).select(["home_team", "away_team"]) for f in files]
    df = pl.concat(frames).collect()
    teams = set(df["home_team"].drop_nulls()) | set(df["away_team"].drop_nulls())
    return teams


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


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    LOGGER.info("Iniciando seed da tabela teams")
    reference = load_teams_reference()
    active = teams_present_in_schedules(script_dir / "data")
    teams = reference.filter(pl.col("team_abbr").is_in(active)).sort("team_abbr")
    LOGGER.info(
        "Times ativos identificados nos schedules: %d de %d na referência",
        teams.height, reference.height,
    )
    if teams.is_empty():
        LOGGER.warning("Nenhum time a persistir — aborte.")
        return

    conn = connect(_read_db_config(project_root))
    try:
        upsert_teams(conn, teams)
    finally:
        conn.close()
    LOGGER.info("Seed concluído: %d times em teams", teams.height)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        LOGGER.exception("[ERRO SEED TEAMS] %s", exc)
        sys.exit(1)