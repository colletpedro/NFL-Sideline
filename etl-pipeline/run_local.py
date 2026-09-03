"""Executa a extração local dos dados brutos da NFL (Fase 1).

Baixa schedules e play-by-play da temporada 2023 e salva em
data/raw/{schedules,pbp}/season=2023/*.parquet, seguindo o layout do
data lake da spec (s3://nfl-sideline-lake/raw/...). Se as credenciais
AWS (AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY) estiverem no ambiente,
também envia o schedules.parquet para o bucket S3.
"""

import os
import sys
from pathlib import Path

from nfl_sideline_etl.extract import download_pbp, download_schedules
from nfl_sideline_etl.load import upload_parquet_to_s3

SEASON = 2023
S3_BUCKET = "nfl-sideline-lake"
DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> None:
    try:
        # 1. Schedules
        schedules = download_schedules(SEASON)
        schedules_dir = DATA_DIR / "raw" / "schedules" / f"season={SEASON}"
        schedules_dir.mkdir(parents=True, exist_ok=True)
        schedules_path = schedules_dir / "schedules.parquet"
        schedules.write_parquet(schedules_path)

        # 2. Upload opcional para o S3 (apenas com credenciais AWS no ambiente)
        if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
            s3_key = f"raw/schedules/season={SEASON}/schedules.parquet"
            upload_parquet_to_s3(str(schedules_path), S3_BUCKET, s3_key)
            print(f"[S3 OK] {s3_key}")

        # 3. Play-by-play
        pbp = download_pbp(SEASON)
        pbp_dir = DATA_DIR / "raw" / "pbp" / f"season={SEASON}"
        pbp_dir.mkdir(parents=True, exist_ok=True)
        pbp.write_parquet(pbp_dir / "pbp.parquet")
    except Exception as exc:
        print(f"[ERRO DE EXTRAÇÃO] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()