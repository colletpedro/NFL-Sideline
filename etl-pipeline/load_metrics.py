"""Carrega métricas semanais por time (team_week_metrics) do Parquet local para o Supabase.

Lê todos os pbp.parquet sob data/raw/pbp/*/, agrega EPA médio e success rate por
(season, week, team_abbr) — separando ataque (posteam) e defesa (defteam) — e faz
upsert em lote na tabela `team_week_metrics` com INSERT ... ON CONFLICT DO UPDATE.

Filtros de jogada seguem a spec (§7): exclui epa nulo, kneel downs e spikes e
restringe a play_type pass/run. `def_epa_play` usa o mesmo EPA visto pela defesa
(valor menor = defesa melhor); `def_success_rate` espelha a taxa de sucesso
(EPA > 0) do ataque adversário.

Conexão: SUPABASE_DB_URL + SUPABASE_DB_USER/SUPABASE_DB_PASSWORD, lidos do ambiente
ou do .env na raiz do projeto (o prefixo `jdbc:` da URL é removido, se presente).
"""

import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import polars as pl
import psycopg2
from psycopg2.extensions import connection as PgConnection

LOGGER = logging.getLogger("load_metrics")

#: Colunas mínimas exigidas de cada arquivo pbp.
NEEDED_COLUMNS = [
    "season", "week", "posteam", "defteam", "epa",
    "play_type", "qb_kneel", "qb_spike",
]
#: Tipos de jogada que entram nas métricas de eficiência (spec §7).
VALID_PLAY_TYPES = ("pass", "run")
#: Ordem exata das colunas persistidas (deve casar com o SQL de INSERT abaixo).
INSERT_COLUMNS = [
    "season", "week", "team_abbr",
    "off_epa_play", "off_success_rate", "plays_offense",
    "def_epa_play", "def_success_rate", "plays_defense",
]

UPSERT_SQL = """
INSERT INTO team_week_metrics
    (season, week, team_abbr,
     off_epa_play, off_success_rate, plays_offense,
     def_epa_play, def_success_rate, plays_defense)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (season, week, team_abbr) DO UPDATE SET
    off_epa_play     = EXCLUDED.off_epa_play,
    off_success_rate = EXCLUDED.off_success_rate,
    plays_offense    = EXCLUDED.plays_offense,
    def_epa_play     = EXCLUDED.def_epa_play,
    def_success_rate = EXCLUDED.def_success_rate,
    plays_defense    = EXCLUDED.plays_defense;
"""


def _load_env_file(env_path: Path) -> dict[str, str]:
    """Lê um arquivo .env simples (chave=valor, ignorando vazios e comentários)."""
    values: dict[str, str] = {}
    if not env_path.is_file():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _read_db_config(project_root: Path) -> dict[str, str]:
    """Resolve as credenciais do banco do ambiente, com fallback para o .env da raiz."""
    dotenv = _load_env_file(project_root / ".env")

    def get(key: str) -> str:
        return os.environ.get(key) or dotenv.get(key) or ""

    return {
        "url": get("SUPABASE_DB_URL").removeprefix("jdbc:"),
        "user": get("SUPABASE_DB_USER"),
        "password": get("SUPABASE_DB_PASSWORD"),
    }


def connect(config: dict[str, str]) -> PgConnection:
    """Abre a conexão Postgres usando user/password separados ou credenciais na URL."""
    url = config["url"]
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL não definido — exporte a variável ou use o .env da raiz do projeto."
        )

    user, password = config["user"], config["password"]
    if user and password:
        return psycopg2.connect(url, user=user, password=password)

    parsed = urlparse(url)
    if parsed.username and parsed.password:
        return psycopg2.connect(url)

    raise RuntimeError(
        "Credenciais do banco ausentes: defina SUPABASE_DB_USER e SUPABASE_DB_PASSWORD "
        "(ou credenciais embutidas na SUPABASE_DB_URL)."
    )


def load_pbp(data_dir: Path) -> pl.DataFrame:
    """Lê todos os pbp.parquet de data/raw/pbp/*/ (uma ou mais temporadas)."""
    files = sorted(data_dir.glob("raw/pbp/*/pbp.parquet"))
    if not files:
        raise FileNotFoundError(
            f"Nenhum pbp.parquet em {data_dir / 'raw' / 'pbp'}: execute run_local.py antes."
        )
    LOGGER.info("Arquivos PBP encontrados: %s", ", ".join(str(f) for f in files))

    frames: list[pl.LazyFrame] = []
    for path in files:
        schema = pl.read_parquet_schema(path)
        missing = [c for c in NEEDED_COLUMNS if c not in schema]
        if missing:
            LOGGER.warning("Ignorando %s: colunas ausentes %s", path.name, missing)
            continue
        frames.append(pl.scan_parquet(path).select(NEEDED_COLUMNS))
    if not frames:
        raise RuntimeError("Nenhum arquivo pbp válido para processar.")

    return pl.concat(frames).collect()


def build_team_week_metrics(pbp: pl.DataFrame) -> pl.DataFrame:
    """Agrega EPA médio e success rate por time e semana (ataque + defesa).

    Filtros de jogada válida (spec §7): epa presente, play_type pass/run,
    sem kneel downs nem spikes, com posteam e defteam definidos.
    """
    valid_plays = pbp.filter(
        pl.col("epa").is_not_null()
        & pl.col("play_type").is_in(VALID_PLAY_TYPES)
        & (pl.col("qb_kneel").fill_null(0.0) == 0)
        & (pl.col("qb_spike").fill_null(0.0) == 0)
        & pl.col("posteam").is_not_null()
        & pl.col("defteam").is_not_null()
    )
    LOGGER.info(
        "Jogadas válidas (pass/run, sem kneel/spike, epa presente): %d de %d",
        valid_plays.height, pbp.height,
    )

    success = (pl.col("epa") > 0).cast(pl.Float64)

    offense = (
        valid_plays
        .group_by(["season", "week", "posteam"])
        .agg(
            pl.col("epa").mean().alias("off_epa_play"),
            success.mean().alias("off_success_rate"),
            pl.len().alias("plays_offense"),
        )
        .rename({"posteam": "team_abbr"})
    )

    defense = (
        valid_plays
        .group_by(["season", "week", "defteam"])
        .agg(
            pl.col("epa").mean().alias("def_epa_play"),
            success.mean().alias("def_success_rate"),
            pl.len().alias("plays_defense"),
        )
        .rename({"defteam": "team_abbr"})
    )

    metrics = offense.join(defense, on=["season", "week", "team_abbr"], how="inner")
    return metrics.select(INSERT_COLUMNS).sort(["season", "week", "team_abbr"])


def upsert_team_week_metrics(conn: PgConnection, metrics: pl.DataFrame) -> int:
    """Persiste as métricas com upsert por (season, week, team_abbr).

    Itera as linhas do DataFrame agregado executando o INSERT ... ON CONFLICT
    DO UPDATE dentro de uma única transação, commitada ao final. Retorna o
    número de linhas persistidas.
    """
    upserted = 0
    try:
        with conn.cursor() as cursor:
            for row in metrics.select(INSERT_COLUMNS).iter_rows():
                cursor.execute(UPSERT_SQL, row)
                upserted += 1
                if upserted % 250 == 0:
                    LOGGER.info("... %d linhas processadas", upserted)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    LOGGER.info("Commit: %d linhas upsertadas em team_week_metrics", upserted)
    return upserted


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    data_dir = script_dir / "data"

    LOGGER.info("Iniciando carga de métricas semanais (team_week_metrics)")
    pbp = load_pbp(data_dir)
    metrics = build_team_week_metrics(pbp)
    if metrics.is_empty():
        LOGGER.warning("Nenhuma métrica agregada — nada a persistir.")
        return
    LOGGER.info("Total a persistir: %d linhas (time-semana)", metrics.height)

    conn = connect(_read_db_config(project_root))
    try:
        upsert_team_week_metrics(conn, metrics)
    finally:
        conn.close()

    LOGGER.info("Carga concluída com sucesso.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # falha explícita, nunca silenciosa (spec §12)
        LOGGER.exception("[ERRO DE CARGA] %s", exc)
        sys.exit(1)
