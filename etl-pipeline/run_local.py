"""Executa a extração local dos dados brutos da NFL (Fase 1).

Baixa schedules e play-by-play da temporada 2023 e salva em
data/raw/{schedules,pbp}/season=2023/*.parquet, seguindo o GCS Layout da spec.
"""

import sys
from pathlib import Path

from nfl_sideline_etl.extract import download_pbp, download_schedules

SEASON = 2023
DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> None:
    try:
        # 1. Schedules
        schedules = download_schedules(SEASON)
        schedules_dir = DATA_DIR / "raw" / "schedules" / f"season={SEASON}"
        schedules_dir.mkdir(parents=True, exist_ok=True)
        schedules.write_parquet(schedules_dir / "schedules.parquet")

        # 2. Play-by-play
        pbp = download_pbp(SEASON)
        pbp_dir = DATA_DIR / "raw" / "pbp" / f"season={SEASON}"
        pbp_dir.mkdir(parents=True, exist_ok=True)
        pbp.write_parquet(pbp_dir / "pbp.parquet")
    except Exception as exc:
        print(f"[ERRO DE EXTRAÇÃO] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()