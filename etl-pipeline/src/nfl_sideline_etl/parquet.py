"""Seleção pequena e explícita de Parquets particionados por temporada."""

from pathlib import Path
from typing import Sequence


class NoSeasonDataError(FileNotFoundError):
    """Há ausência de arquivos para as temporadas solicitadas."""


class ParquetSchemaError(ValueError):
    """O Parquet existe, mas não satisfaz o contrato de colunas."""


def season_partition_files(
    data_dir: Path,
    source: str,
    filename: str,
    seasons: Sequence[int],
) -> list[Path]:
    """Retorna somente arquivos das partições pedidas, com erro contextual."""
    root = data_dir / "raw" / source
    all_files = sorted(root.glob(f"season=*/{filename}"))
    if not all_files:
        raise NoSeasonDataError(f"Nenhum {filename} em {root}: execute run_local.py antes.")
    selected = [root / f"season={season}" / filename for season in seasons]
    existing = [path for path in selected if path.is_file()]
    if not existing:
        raise NoSeasonDataError(
            f"Há Parquets locais em {root}, mas nenhum pertence às temporadas "
            f"solicitadas {tuple(seasons)}."
        )
    return existing
