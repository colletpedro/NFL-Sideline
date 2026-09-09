"""Extração de dados brutos da NFL via nflreadpy, convertidos para Polars.

Regra de ouro (ADR-005): o retorno do nflreadpy é convertido imediatamente
para Polars DataFrame antes de qualquer uso.
"""

import nflreadpy as nfl
import polars as pl


class SourceDataNotPublishedError(RuntimeError):
    """O arquivo-fonte solicitado ainda não foi publicado pelo nflverse."""


def _http_status_from_exception_chain(exc: BaseException) -> int | None:
    """Obtém status HTTP da cadeia pública de exceções, quando disponível."""
    pending = [exc]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))

        response = getattr(current, "response", None)
        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int):
            return status_code

        for related in (current.__cause__, current.__context__):
            if related is not None:
                pending.append(related)
    return None


def to_polars(df: object) -> pl.DataFrame:
    """Normaliza retornos Polars ou Pandas do nflreadpy para Polars."""
    if isinstance(df, pl.DataFrame):
        return df
    try:
        return pl.from_pandas(df)  # type: ignore[arg-type]
    except (ImportError, TypeError, ValueError) as exc:
        raise TypeError(
            f"Retorno incompatível do nflreadpy: {type(df).__name__}; esperado Polars ou Pandas."
        ) from exc


def download_pbp(season: int) -> pl.DataFrame:
    """Baixa o play-by-play de uma temporada e retorna como Polars DataFrame."""
    try:
        return to_polars(nfl.load_pbp(seasons=[season]))
    except ConnectionError as exc:
        if _http_status_from_exception_chain(exc) == 404:
            raise SourceDataNotPublishedError(
                f"PBP da temporada {season} ainda não foi publicado pela fonte."
            ) from exc
        raise


def download_schedules(season: int) -> pl.DataFrame:
    """Baixa os schedules (jogos) de uma temporada e retorna como Polars DataFrame."""
    return to_polars(nfl.load_schedules(seasons=[season]))
