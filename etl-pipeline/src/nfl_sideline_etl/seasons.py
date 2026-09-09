"""Política compartilhada de seleção e validação de temporadas NFL."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Sequence


# O play-by-play do nflverse/nflreadpy começa em 1999. O limite superior móvel
# admite a próxima temporada, cujos schedules podem ser publicados antecipadamente.
MIN_SEASON = 1999


def current_nfl_season(today: date | None = None) -> int:
    """Retorna a temporada NFL corrente; janeiro/fevereiro pertencem ao ano anterior."""
    reference = today or date.today()
    return reference.year if reference.month >= 3 else reference.year - 1


def plausible_season_range(today: date | None = None) -> tuple[int, int]:
    """Faixa suportada: 1999 até a temporada seguinte à corrente."""
    return MIN_SEASON, current_nfl_season(today) + 1


def normalize_seasons(
    seasons: Sequence[int] | None,
    *,
    today: date | None = None,
) -> tuple[int, ...]:
    """Aplica default, valida, remove duplicatas e ordena temporadas."""
    selected = list(seasons) if seasons else [current_nfl_season(today)]
    minimum, maximum = plausible_season_range(today)
    invalid = sorted({season for season in selected if not minimum <= season <= maximum})
    if invalid:
        raise ValueError(
            f"Temporada(s) fora da faixa suportada {minimum}..{maximum}: "
            + ", ".join(str(season) for season in invalid)
        )
    return tuple(sorted(set(selected)))


def add_season_arguments(parser: argparse.ArgumentParser) -> None:
    """Adiciona o contrato comum ``--season`` e ``--data-dir`` a uma CLI."""
    parser.add_argument(
        "--season",
        type=int,
        action="append",
        dest="seasons",
        metavar="YEAR",
        help="Temporada NFL; repita a opção para selecionar mais de uma.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Raiz local que contém raw/schedules e raw/pbp.",
    )


def seasons_from_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    *,
    today: date | None = None,
) -> tuple[int, ...]:
    """Normaliza temporadas da CLI e reporta erros pela interface do argparse."""
    try:
        return normalize_seasons(args.seasons, today=today)
    except ValueError as exc:
        parser.error(str(exc))
        raise AssertionError("argparse encerra a execução") from exc
