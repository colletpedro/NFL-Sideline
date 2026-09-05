"""Carrega o calendário (games) e as probabilidades implícitas (market_implied) no Supabase.

Lê os schedules.parquet sob data/raw/schedules/*/, filtra estritamente as temporadas
2025 (histórico recente) e 2026 (calendário futuro) excluindo pré-temporada, e faz
upsert em duas tabelas (spec §6.2):

1. `games` — mapeia game_id, season, week, game_type, gameday, home_team, away_team,
   spread_line, total_line, home_moneyline e away_moneyline. Jogos sem cotação
   (moneyline ou spread nulos — cancelados/sem linha) são descartados.
2. `market_implied` — converte a moneyline americana em probabilidade implícita bruta,
   calcula o overround (vig) e remove o vig por normalização proporcional (spec §7.1),
   gravando raw, fair e vig_pct por game.

As conversões matemáticas são validadas antes do INSERT: probabilidades fora de (0, 1),
overround <= 1 ou fair values que não somam 1 (tolerância 1e-9) abortam a carga com
erro explícito — falha silenciosa nunca é aceitável (spec §13).

Conexão: reutiliza os helpers de load_metrics.py (SUPABASE_DB_URL + user/password
do ambiente ou do .env na raiz do projeto).
"""

import logging
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import polars as pl
from psycopg2.extensions import connection as PgConnection

from load_metrics import _read_db_config, connect

LOGGER = logging.getLogger("load_games")

#: Temporadas-alvo desta carga (2025 = histórico recente; 2026 = calendário futuro).
SEASONS: tuple[int, ...] = (2025, 2026)
#: Tipos de jogo que entram na carga (pré-temporada fica fora).
#: Nesta versão do nflverse os playoffs chegam granularizados (WC/DIV/CON/SB) em vez
#: de "POST" — por isso a lista cobre as duas vocabulários; "PRE"/"HOF" ficam fora.
VALID_GAME_TYPES = ("REG", "POST", "WC", "DIV", "CON", "SB")
#: Colunas persistidas em `games`, na ordem exata do SQL de INSERT abaixo.
GAMES_COLUMNS = [
    "game_id", "season", "week", "game_type", "gameday",
    "home_team", "away_team", "spread_line", "total_line",
    "home_moneyline", "away_moneyline",
]
#: Colunas NUMERIC do games que exigem conversão exata para Decimal.
GAMES_DECIMAL_COLUMNS = ("spread_line", "total_line")

UPSERT_GAMES_SQL = """
INSERT INTO games
    (game_id, season, week, game_type, gameday,
     home_team, away_team, spread_line, total_line,
     home_moneyline, away_moneyline)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (game_id) DO UPDATE SET
    season          = EXCLUDED.season,
    week            = EXCLUDED.week,
    game_type       = EXCLUDED.game_type,
    gameday         = EXCLUDED.gameday,
    home_team       = EXCLUDED.home_team,
    away_team       = EXCLUDED.away_team,
    spread_line     = EXCLUDED.spread_line,
    total_line      = EXCLUDED.total_line,
    home_moneyline  = EXCLUDED.home_moneyline,
    away_moneyline  = EXCLUDED.away_moneyline;
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
    vig_pct           = EXCLUDED.vig_pct;
"""

#: Tolerância para a soma das probabilidades fair (arredondamento do contexto Decimal).
FAIR_SUM_TOLERANCE = Decimal("1e-9")


def load_schedules(data_dir: Path) -> pl.DataFrame:
    """Lê todos os schedules.parquet locais e filtra a temporada-alvo, sem pré-temporada."""
    files = sorted(data_dir.glob("raw/schedules/*/schedules.parquet"))
    if not files:
        raise FileNotFoundError(
            f"Nenhum schedules.parquet em {data_dir / 'raw' / 'schedules'}: "
            "execute run_local.py antes."
        )
    LOGGER.info("Arquivos de schedules encontrados: %s", ", ".join(str(f) for f in files))

    frames = [pl.scan_parquet(f) for f in files]
    schedules = pl.concat(frames).collect()

    season_df = schedules.filter(
        pl.col("season").is_in(SEASONS) & pl.col("game_type").is_in(VALID_GAME_TYPES)
    )
    LOGGER.info(
        "Schedules %s: %d jogos REG/POST (descartados %d de outras temporadas/tipos)",
        SEASONS, season_df.height, schedules.height - season_df.height,
    )
    return season_df


def prepare_games(schedules: pl.DataFrame) -> pl.DataFrame:
    """Seleciona e tipa as colunas de `games`, descartando jogos sem cotação.

    Remove registros com moneyline (casa ou fora) ou spread nulos — jogos
    cancelados ou sem linha de mercado — e converte gameday (String) em Date.
    """
    quoted = schedules.filter(
        pl.col("home_moneyline").is_not_null()
        & pl.col("away_moneyline").is_not_null()
        & pl.col("spread_line").is_not_null()
    )
    dropped = schedules.height - quoted.height
    if dropped:
        LOGGER.warning(
            "%d jogos sem cotação completa (moneyline/spread nulos) descartados",
            dropped,
        )

    games = quoted.select(GAMES_COLUMNS).with_columns(
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


def upsert_games(conn: PgConnection, games: pl.DataFrame) -> int:
    """Persiste o calendário com upsert por game_id; retorna o total de linhas."""
    rows = _rows_for_games(games)
    try:
        with conn.cursor() as cursor:
            for position, row in enumerate(rows, start=1):
                cursor.execute(UPSERT_GAMES_SQL, row)
                if position % 100 == 0:
                    LOGGER.info("... %d jogos processados", position)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    LOGGER.info("Commit: %d jogos upsertados em games", len(rows))
    return len(rows)


def american_odds_to_implied(odds: int) -> Decimal:
    """Converte moneyline americana em probabilidade implícita bruta (spec §7.1).

    odd < 0: p = |odd| / (|odd| + 100); odd > 0: p = 100 / (odd + 100).
    Moneyline zero é inválida (probabilidade indefinida) e aborta a carga.
    """
    if odds == 0:
        raise ValueError("Moneyline 0 é inválida: sem probabilidade definida.")
    odds_dec = Decimal(odds)
    if odds_dec < 0:
        implied = (-odds_dec) / (-odds_dec + Decimal(100))
    else:
        implied = Decimal(100) / (odds_dec + Decimal(100))

    if not Decimal(0) < implied < Decimal(1):
        raise ValueError(
            f"Conversão de moneyline {odds} produziu probabilidade fora de (0, 1): {implied}"
        )
    return implied


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
        home_raw = american_odds_to_implied(int(record["home_moneyline"]))
        away_raw = american_odds_to_implied(int(record["away_moneyline"]))

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


def upsert_market(conn: PgConnection, rows: list[dict[str, object]]) -> int:
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
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    LOGGER.info("Commit: %d linhas upsertadas em market_implied", len(rows))
    return len(rows)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    data_dir = script_dir / "data"

    conn = connect(_read_db_config(project_root))
    try:
        # Carga 1 — calendário (games)
        try:
            LOGGER.info("Iniciando carga do calendário (games)")
            schedules = load_schedules(data_dir)
            games = prepare_games(schedules)
            if games.is_empty():
                LOGGER.warning("Nenhum jogo cotado para as temporadas %s — nada a persistir.", SEASONS)
            else:
                upsert_games(conn, games)
        except Exception as exc:
            LOGGER.exception("[ERRO CARGA GAMES] %s", exc)
            raise

        # Carga 2 — probabilidades implícitas (market_implied), derivadas do calendário
        try:
            LOGGER.info("Iniciando carga de probabilidades implícitas (market_implied)")
            market_rows = build_market_rows(games)
            if not market_rows:
                LOGGER.warning("Nenhum mercado calculado — nada a persistir.")
            else:
                upsert_market(conn, market_rows)
        except Exception as exc:
            LOGGER.exception("[ERRO CARGA MARKET_IMPLIED] %s", exc)
            raise
    finally:
        conn.close()

    LOGGER.info("Carga de jogos e mercado concluída com sucesso.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # falha explícita, nunca silenciosa (spec §13)
        LOGGER.exception("[ERRO DE CARGA] %s", exc)
        sys.exit(1)
