"""Extração de dados brutos da NFL via nflreadpy, convertidos para Polars.

Regra de ouro (ADR-005): o retorno do nflreadpy é convertido imediatamente
para Polars DataFrame antes de qualquer uso.
"""

import nflreadpy as nfl
import polars as pl


def download_pbp(season: int) -> pl.DataFrame:
    """Baixa o play-by-play de uma temporada e retorna como Polars DataFrame."""
    df = nfl.load_pbp(seasons=[season])
    if isinstance(df, pl.DataFrame):
        return df  # nflreadpy 0.1.x já retorna Polars nativamente
    return pl.from_pandas(df)


def download_schedules(season: int) -> pl.DataFrame:
    """Baixa os schedules (jogos) de uma temporada e retorna como Polars DataFrame."""
    df = nfl.load_schedules(seasons=[season])
    if isinstance(df, pl.DataFrame):
        return df  # nflreadpy 0.1.x já retorna Polars nativamente
    return pl.from_pandas(df)