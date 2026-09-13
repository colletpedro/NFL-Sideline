"""Carrega o calendário (games) e as probabilidades implícitas (market_implied) no Supabase.

Lê os schedules.parquet das temporadas selecionadas, exclui pré-temporada e faz
upsert em duas tabelas (spec §6.2):

1. `games` — mapeia identidade, times, placares/result fornecidos pelo schedule,
   spread_line, total_line, home_moneyline e away_moneyline. Calendário independe
   de cotação: todos os jogos estruturalmente válidos são preservados.
2. `market_implied` — converte a moneyline americana em probabilidade implícita bruta,
   calcula o overround (vig) e remove o vig por normalização proporcional (spec §7.1),
   gravando raw, fair e vig_pct por game.

As conversões matemáticas são validadas antes do INSERT: probabilidades fora de (0, 1),
overround <= 1 ou fair values que não somam 1 (tolerância 1e-9) abortam a carga com
erro explícito — falha silenciosa nunca é aceitável (spec §13).

Conexão: reutiliza os helpers de load_metrics.py (SUPABASE_DB_URL + user/password
do ambiente ou do .env na raiz do projeto).
"""

import argparse
import logging
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import polars as pl
from psycopg2.extensions import connection as PgConnection

from load_metrics import _read_db_config, connect
from nfl_sideline_etl.parquet import (
    NoSeasonDataError,
    ParquetSchemaError,
    season_partition_files,
)
from nfl_sideline_etl.seasons import add_season_arguments, seasons_from_args

LOGGER = logging.getLogger("load_games")

#: Tipos de jogo que entram na carga (pré-temporada fica fora).
#: Nesta versão do nflverse os playoffs chegam granularizados (WC/DIV/CON/SB) em vez
#: de "POST" — por isso a lista cobre as duas vocabulários; "PRE"/"HOF" ficam fora.
VALID_GAME_TYPES = ("REG", "POST", "WC", "DIV", "CON", "SB")
#: Colunas persistidas em `games`, na ordem exata do SQL de INSERT abaixo.
GAMES_COLUMNS = [
    "game_id", "season", "week", "game_type", "gameday",
    "home_team", "away_team", "home_score", "away_score", "result",
    "spread_line", "total_line",
    "home_moneyline", "away_moneyline",
]
#: Colunas NUMERIC do games que exigem conversão exata para Decimal.
GAMES_DECIMAL_COLUMNS = ("spread_line", "total_line")
SCHEDULE_COLUMNS = tuple(GAMES_COLUMNS)

UPSERT_GAMES_SQL = """
INSERT INTO games
    (game_id, season, week, game_type, gameday,
     home_team, away_team, home_score, away_score, result,
     spread_line, total_line, home_moneyline, away_moneyline)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (game_id) DO UPDATE SET
    season          = EXCLUDED.season,
    week            = EXCLUDED.week,
    game_type       = EXCLUDED.game_type,
    gameday         = EXCLUDED.gameday,
    home_team       = EXCLUDED.home_team,
    away_team       = EXCLUDED.away_team,
    home_score      = CASE
        WHEN EXCLUDED.home_score IS NULL THEN games.home_score
        ELSE EXCLUDED.home_score
    END,
    away_score      = CASE
        WHEN EXCLUDED.home_score IS NULL THEN games.away_score
        ELSE EXCLUDED.away_score
    END,
    result          = CASE
        WHEN EXCLUDED.home_score IS NULL THEN games.result
        ELSE EXCLUDED.result
    END,
    spread_line     = COALESCE(EXCLUDED.spread_line, games.spread_line),
    total_line      = COALESCE(EXCLUDED.total_line, games.total_line),
    home_moneyline  = CASE
        WHEN EXCLUDED.home_moneyline IS NOT NULL AND EXCLUDED.away_moneyline IS NOT NULL
        THEN EXCLUDED.home_moneyline ELSE games.home_moneyline END,
    away_moneyline  = CASE
        WHEN EXCLUDED.home_moneyline IS NOT NULL AND EXCLUDED.away_moneyline IS NOT NULL
        THEN EXCLUDED.away_moneyline ELSE games.away_moneyline END,
    updated_at      = now();
"""

UPSERT_MARKET_SQL = """
INSERT INTO market_implied
    (game_id, home_implied_raw, away_implied_raw,
     home_implied_fair, away_implied_fair, vig_pct)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (game_id) DO UPDATE SET
    home_implied_raw  = EXCLUDED.home_implied_raw,
    away_implied_raw  = EXCLUDED.away_implied_raw,
    home_implied_fair = EXCLUDED.home_implied_fair,
    away_implied_fair = EXCLUDED.away_implied_fair,
    vig_pct           = EXCLUDED.vig_pct,
    computed_at       = now();
"""

#: Tolerância para a soma das probabilidades fair (arredondamento do contexto Decimal).
FAIR_SUM_TOLERANCE = Decimal("1e-9")


@dataclass(frozen=True)
class GamesLoadResult:
    """Contagens do DataFrame preparado e do mercado persistido."""

    rows_games: int
    rows_market: int


def _integer_value(value: object, *, field: str, game_id: str) -> int | None:
    """Normaliza inteiro anulável sem truncar valores fracionários."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Placares inválidos para game_id={game_id}: {field} não é inteiro")
    try:
        decimal_value = Decimal(str(value))
    except Exception as exc:
        raise ValueError(
            f"Placares inválidos para game_id={game_id}: {field} não é inteiro"
        ) from exc
    if not decimal_value.is_finite() or decimal_value != decimal_value.to_integral_value():
        raise ValueError(f"Placares inválidos para game_id={game_id}: {field} não é inteiro")
    return int(decimal_value)


def _validate_and_normalize_scores(schedules: pl.DataFrame) -> pl.DataFrame:
    """Valida o trio da fonte e devolve scores/result como inteiros anuláveis."""
    home_values: list[int | None] = []
    away_values: list[int | None] = []
    result_values: list[int | None] = []
    for record in schedules.iter_rows(named=True):
        game_id = str(record["game_id"])
        home_score = _integer_value(record["home_score"], field="home_score", game_id=game_id)
        away_score = _integer_value(record["away_score"], field="away_score", game_id=game_id)
        result = _integer_value(record["result"], field="result", game_id=game_id)

        trio = (home_score, away_score, result)
        has_any_score_field = any(value is not None for value in trio)
        has_complete_score_trio = all(value is not None for value in trio)
        if has_any_score_field and not has_complete_score_trio:
            raise ValueError(
                f"Placares inválidos para game_id={game_id}: home_score, away_score e result "
                "devem ser todos nulos ou todos preenchidos"
            )
        if has_complete_score_trio and (home_score < 0 or away_score < 0):
            raise ValueError(
                f"Placares inválidos para game_id={game_id}: placar não pode ser negativo"
            )
        if has_complete_score_trio and result != home_score - away_score:
            raise ValueError(
                f"Placares inválidos para game_id={game_id}: result é inconsistente"
            )

        home_values.append(home_score)
        away_values.append(away_score)
        result_values.append(result)

    return schedules.with_columns(
        pl.Series("home_score", home_values, dtype=pl.Int64),
        pl.Series("away_score", away_values, dtype=pl.Int64),
        pl.Series("result", result_values, dtype=pl.Int64),
    )


def load_schedules(data_dir: Path, seasons: tuple[int, ...]) -> pl.DataFrame:
    """Lê somente schedules das temporadas explícitas e exclui pré-temporada."""
    files = season_partition_files(data_dir, "schedules", "schedules.parquet", seasons)
    LOGGER.info("Arquivos de schedules encontrados: %s", ", ".join(str(f) for f in files))

    frames: list[pl.LazyFrame] = []
    for path in files:
        schema = pl.read_parquet_schema(path)
        missing = [column for column in SCHEDULE_COLUMNS if column not in schema]
        if missing:
            raise ParquetSchemaError(f"Schema incompatível em {path}: colunas ausentes {missing}")
        frames.append(pl.scan_parquet(path).select(SCHEDULE_COLUMNS))
    schedules = pl.concat(frames).collect()
    if schedules.is_empty():
        raise NoSeasonDataError(f"Schedules vazio para as temporadas solicitadas {seasons}.")

    season_df = schedules.filter(
        pl.col("season").is_in(seasons) & pl.col("game_type").is_in(VALID_GAME_TYPES)
    )
    if season_df.is_empty() and not schedules.is_empty():
        raise NoSeasonDataError(
            f"Os Parquets selecionados não contêm jogos das temporadas solicitadas {seasons}."
        )
    LOGGER.info(
        "Schedules %s: %d jogos REG/POST (descartados %d de outras temporadas/tipos)",
        seasons, season_df.height, schedules.height - season_df.height,
    )
    return season_df


def prepare_games(schedules: pl.DataFrame) -> pl.DataFrame:
    """Prepara o calendário; par parcial vira NULL/NULL, nunca cotação sintética.

    No conflito, o SQL preserva o último par completo e linhas conhecidas.
    Valores presentes inválidos continuam sendo erros, mesmo em pares parciais.
    """
    validated = _validate_and_normalize_scores(
        schedules.filter(pl.col("game_type").is_in(VALID_GAME_TYPES))
    )
    home_values: list[int | None] = []
    away_values: list[int | None] = []
    missing_by_season: dict[int, int] = {}
    for record in validated.iter_rows(named=True):
        pair = [_moneyline_value(record[column]) for column in ("home_moneyline", "away_moneyline")]
        if any(value is None for value in pair):
            pair = [None, None]
            season = int(record["season"])
            missing_by_season[season] = missing_by_season.get(season, 0) + 1
        home_values.append(pair[0])
        away_values.append(pair[1])
    for season, count in sorted(missing_by_season.items()):
        LOGGER.warning("season=%d games_without_complete_moneyline_pair=%d; calendário preservado", season, count)
    games = validated.with_columns(
        pl.Series("home_moneyline", home_values, dtype=pl.Int64),
        pl.Series("away_moneyline", away_values, dtype=pl.Int64),
    ).select(GAMES_COLUMNS).with_columns(
        pl.col("gameday").str.to_date("%Y-%m-%d")
    )
    if games["gameday"].null_count():
        LOGGER.warning("gameday não-parseável em %d jogos (NULL no banco)", games["gameday"].null_count())
    LOGGER.info("Jogos prontos para `games`: %d", games.height)
    return games.sort("game_id")


def _rows_for_games(games: pl.DataFrame) -> list[tuple[object, ...]]:
    """Converte o DataFrame em tuplas na ordem do INSERT, com NUMERIC em Decimal."""
    rows: list[tuple[object, ...]] = []
    for record in games.iter_rows(named=True):
        values: list[object] = []
        for column in GAMES_COLUMNS:
            value = record[column]
            if column in GAMES_DECIMAL_COLUMNS and value is not None:
                value = Decimal(str(value))
            values.append(value)
        rows.append(tuple(values))
    return rows


def upsert_games(conn: PgConnection, games: pl.DataFrame, *, commit: bool = True) -> int:
    """Persiste o calendário com upsert por game_id; retorna o total de linhas."""
    rows = _rows_for_games(games)
    try:
        with conn.cursor() as cursor:
            for position, row in enumerate(rows, start=1):
                cursor.execute(UPSERT_GAMES_SQL, row)
                if position % 100 == 0:
                    LOGGER.info("... %d jogos processados", position)
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    LOGGER.info("Jogos enviados para upsert em games: %d", len(rows))
    return len(rows)


def american_odds_to_implied(odds: int) -> Decimal:
    """Converte moneyline americana em probabilidade implícita bruta (spec §7.1).

    odd < 0: p = |odd| / (|odd| + 100); odd > 0: p = 100 / (odd + 100).
    Moneyline zero é inválida (probabilidade indefinida) e aborta a carga.
    """
    odds_dec = Decimal(str(odds))
    if (not odds_dec.is_finite() or odds_dec == 0
            or odds_dec != odds_dec.to_integral_value() or isinstance(odds, bool)):
        raise ValueError("Moneyline inválida: deve ser um inteiro finito diferente de zero.")
    if odds_dec < 0:
        implied = (-odds_dec) / (-odds_dec + Decimal(100))
    else:
        implied = Decimal(100) / (odds_dec + Decimal(100))

    if not Decimal(0) < implied < Decimal(1):
        raise ValueError(
            f"Conversão de moneyline {odds} produziu probabilidade fora de (0, 1): {implied}"
        )
    return implied


def _moneyline_value(value: object) -> int | None:
    if value is None:
        return None
    american_odds_to_implied(value)
    return int(value)


def _validate_market(
    game_id: str,
    home_raw: Decimal,
    away_raw: Decimal,
    home_fair: Decimal,
    away_fair: Decimal,
    vig_pct: Decimal,
) -> None:
    """Valida as conversões matemáticas antes de persistir (spec §7.1, §13)."""
    problems: list[str] = []
    if not (Decimal(0) < home_raw < Decimal(1)):
        problems.append(f"home_implied_raw={home_raw}")
    if not (Decimal(0) < away_raw < Decimal(1)):
        problems.append(f"away_implied_raw={away_raw}")
    if vig_pct <= 0:
        problems.append(f"vig_pct={vig_pct} (overround deve exceder 1.0)")
    fair_sum = home_fair + away_fair
    if abs(fair_sum - Decimal(1)) > FAIR_SUM_TOLERANCE:
        problems.append(f"home_fair + away_fair = {fair_sum} != 1")
    if problems:
        raise ValueError(f"Validação de mercado falhou para {game_id}: {'; '.join(problems)}")


def build_market_rows(games: pl.DataFrame) -> list[dict[str, object]]:
    """Deriva home/away raw, fair e vig_pct de cada jogo cotado (spec §7.1).

    Retorna lista de dicts já prontos para o INSERT em market_implied, com os
    valores NUMERIC como Decimal. A soma home_fair + away_fair é exatamente 1
    sob normalização proporcional (validação com tolerância de arredondamento).
    """
    rows: list[dict[str, object]] = []
    for record in games.iter_rows(named=True):
        game_id = str(record["game_id"])
        home_ml = _moneyline_value(record["home_moneyline"])
        away_ml = _moneyline_value(record["away_moneyline"])
        if home_ml is None or away_ml is None:
            continue
        home_raw = american_odds_to_implied(home_ml)
        away_raw = american_odds_to_implied(away_ml)

        overround = home_raw + away_raw
        vig_pct = overround - Decimal(1)
        home_fair = home_raw / overround
        away_fair = away_raw / overround

        _validate_market(game_id, home_raw, away_raw, home_fair, away_fair, vig_pct)
        rows.append(
            {
                "game_id": game_id,
                "home_implied_raw": home_raw,
                "away_implied_raw": away_raw,
                "home_implied_fair": home_fair,
                "away_implied_fair": away_fair,
                "vig_pct": vig_pct,
            }
        )
    LOGGER.info("Linhas de mercado calculadas (e validadas): %d", len(rows))
    return rows


def upsert_market(
    conn: PgConnection,
    rows: list[dict[str, object]],
    *,
    commit: bool = True,
) -> int:
    """Persiste market_implied com upsert por game_id; retorna o total de linhas."""
    try:
        with conn.cursor() as cursor:
            for position, row in enumerate(rows, start=1):
                cursor.execute(
                    UPSERT_MARKET_SQL,
                    (
                        row["game_id"],
                        row["home_implied_raw"],
                        row["away_implied_raw"],
                        row["home_implied_fair"],
                        row["away_implied_fair"],
                        row["vig_pct"],
                    ),
                )
                if position % 100 == 0:
                    LOGGER.info("... %d jogos de mercado processados", position)
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    LOGGER.info("Linhas enviadas para upsert em market_implied: %d", len(rows))
    return len(rows)


def load_games_and_market(
    conn: PgConnection,
    data_dir: Path,
    seasons: tuple[int, ...],
) -> GamesLoadResult:
    """Prepara e persiste jogos e mercado na mesma transação."""
    schedules = load_schedules(data_dir, seasons)
    games = prepare_games(schedules)
    market_rows = build_market_rows(games)
    try:
        upsert_games(conn, games, commit=False)
        upsert_market(conn, market_rows, commit=False)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    LOGGER.info(
        "Etapa games concluída: rows_games=%d rows_market=%d",
        games.height,
        len(market_rows),
    )
    return GamesLoadResult(rows_games=games.height, rows_market=len(market_rows))


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

    conn = connect(_read_db_config(project_root))
    try:
        try:
            load_games_and_market(conn, data_dir, seasons)
        except Exception as exc:
            LOGGER.exception("[ERRO CARGA GAMES/MARKET] %s", exc)
            raise
    finally:
        conn.close()

    LOGGER.info("Carga de jogos e mercado concluída com sucesso.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # falha explícita, nunca silenciosa (spec §13)
        LOGGER.exception("[ERRO DE CARGA] %s", exc)
        sys.exit(1)
