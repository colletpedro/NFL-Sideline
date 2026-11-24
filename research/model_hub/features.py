"""H2 - Feature store: constrói ``HUB/features/<build_id>/{plays,games,team_game,team_asof}.parquet``.

Entrada: só os arquivos listados no manifesto de aquisição (sha256 conferido antes de ler). Saída determinística.
``build_id`` = sha256(acquisition_id, sha256 deste arquivo, parâmetros).

SIGLAS (H-D9): o PBP traz sempre as siglas atuais (LV, LAC, LA) e os schedules as históricas (OAK 2011-2019, SD
2011-2016, STL 2011-2015). Todas as colunas de time de ``plays``, ``games``, ``team_game`` e ``team_asof`` usam a
franquia atual (``FRANCHISE_ALIASES``, único lugar da normalização); ``games`` guarda a sigla do schedule em
``home_team_raw``/``away_team_raw``. ``game_id`` NÃO é alterado (``2011_01_PHI_STL``). Assim o histórico (EWM)
atravessa a mudança de cidade.

REGRAS DO ALVO ``next_score`` (tabela ``plays``)
  * Evento de pontuação (PAT e conversão de 2 pontos NÃO são eventos):
      touchdown == 1            -> time que pontuou = ``td_team``; 7 pontos; tipo TD
      field_goal_result=='made' -> ``posteam`` da jogada; 3 pontos; tipo FG
      safety == 1               -> normalmente ``defteam``; 2 pontos; tipo SAFETY. Exceção real (punt cujo
                                   retornador recua para o próprio end zone, 5 casos em 2011-2026): quem pontua é o
                                   ``posteam`` (chutador). Regra: se o placar do ``posteam`` subiu 2 na jogada
                                   (``posteam_score_post - posteam_score == 2``) o time é o ``posteam``; senão (inclusive
                                   quando a variação não é observável) o ``defteam``.
    (nessa ordem de precedência se uma jogada marcar mais de um; ``touchdown==1`` sem ``td_team`` é erro.)
  * Para cada jogada: o primeiro evento na mesma (game_id, half), a partir da jogada atual INCLUSIVE.
    ``half``: 1 = qtr 1-2, 2 = qtr 3-4, 3 = prorrogação (qtr >= 5).
  * Perspectiva do ``posteam`` da jogada atual: time do evento == posteam -> TD/FG/SAFETY (+7/+3/+2), senão
    OPP_TD/OPP_FG/OPP_SAFETY (-7/-3/-2). Sem evento até o fim da metade -> NO_SCORE (0).
  * Jogada sem ``posteam`` ou sem ``qtr``: alvos nulos.
  * ``ep_eligible``: posteam e yardline_100 não nulos, down em 1..4, play_type não nulo e fora de
    {kickoff, extra_point}, e sem two_point_attempt.

``team_game`` (jogadas que entram): play_type in {pass, run}, epa não nulo, posteam e defteam não nulos
  e ``two_point_attempt != 1`` (exclui no_play, qb_kneel, qb_spike, punt, field_goal, kickoff, conversões de 2
  pontos...). off_* agrupa por posteam, def_* por defteam
  (o que o time sofreu). Taxas e médias por jogada (não ponderadas por jogo). ``off_pass_rate`` = pass/(pass+run).
  ``success`` nulo é ignorado na média. Pontos vêm do schedule.

``team_asof`` (uma linha por jogo e time, de ``games``, inclusive futuros): só usa linhas de ``team_game`` do
  mesmo time com kickoff_utc ESTRITAMENTE anterior. Para cada métrica m em {off_epa, def_epa, off_success,
  def_success, pass_rate, point_diff} (média de valores por jogo, ignorando nulos):
    season_m = média dos jogos anteriores da mesma temporada (REG+POST);
    last3_m  = média dos 3 jogos anteriores mais recentes (atravessa temporadas; menos de 3 usa os que houver);
    ewm4_m   = média exponencial com meia-vida de 4 jogos (peso 0.5**(idade/4), idade 0 = jogo mais recente),
               atravessa temporadas, sem reinício na virada.
  ``games_prior_season`` / ``games_prior_total`` contam jogos anteriores. Sem jogo anterior -> nulo (nunca zero).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import numpy as np
import polars as pl

import acquire as acq

CODE_PATH = Path(__file__).resolve()
#: Franquias que mudaram de sigla: a atual vale para todas as temporadas (mesma franquia e elenco).
FRANCHISE_ALIASES = {"OAK": "LV", "SD": "LAC", "STL": "LA"}
PARAMS = {"franchise_aliases": FRANCHISE_ALIASES, "season_types": ["REG", "POST"], "last_n": 3, "ewm_half_life_games": 4,
          "team_game_play_types": ["pass", "run"], "kickoff_tz": "America/New_York"}
#: Colunas de time do PBP que passam por ``FRANCHISE_ALIASES``.
TEAM_COLUMNS = ("posteam", "defteam", "home_team", "away_team", "td_team")
TABLES = ("plays", "games", "team_game", "team_asof")
METRICS = ("off_epa", "def_epa", "off_success", "def_success", "pass_rate", "point_diff")

PROBS = ["no_score_prob", "opp_fg_prob", "opp_safety_prob", "opp_td_prob", "fg_prob", "safety_prob", "td_prob"]
PLAY_SCHEMA = {
    "game_id": pl.String, "play_id": pl.Int64, "season": pl.Int32, "week": pl.Int32, "season_type": pl.String,
    "game_date": pl.String, "posteam": pl.String, "defteam": pl.String, "home_team": pl.String,
    "away_team": pl.String, "qtr": pl.Int8, "down": pl.Int8, "ydstogo": pl.Int16, "yardline_100": pl.Float64,
    "half_seconds_remaining": pl.Float64, "game_seconds_remaining": pl.Float64, "goal_to_go": pl.Int8,
    "score_differential": pl.Float64, "posteam_timeouts_remaining": pl.Int8,
    "defteam_timeouts_remaining": pl.Int8, "roof": pl.String, "play_type": pl.String, "pass": pl.Int8,
    "rush": pl.Int8, "epa": pl.Float64, "ep": pl.Float64, "wp": pl.Float64, "success": pl.Float64,
    **{p: pl.Float64 for p in PROBS},
}
RAW_EXTRA = {"touchdown": pl.Float64, "td_team": pl.String, "field_goal_result": pl.String,
             "safety": pl.Float64, "two_point_attempt": pl.Float64, "posteam_score": pl.Float64,
             "posteam_score_post": pl.Float64}
GAME_COLUMNS = ["game_id", "season", "week", "game_type", "kickoff_utc", "home_team", "away_team",
                "home_team_raw", "away_team_raw", "home_score",
                "away_score", "result", "total", "completed", "spread_line", "total_line", "home_moneyline",
                "away_moneyline", "roof", "surface", "temp", "wind", "div_game", "home_rest", "away_rest",
                "location"]


class FeatureError(RuntimeError):
    pass


def normalize_team(col: str | pl.Expr) -> pl.Expr:
    """Expressão que troca siglas históricas pela franquia atual (``FRANCHISE_ALIASES``); nulo continua nulo."""
    e = pl.col(col) if isinstance(col, str) else col
    return e.replace(FRANCHISE_ALIASES)


def code_sha256() -> str:
    return hashlib.sha256(CODE_PATH.read_bytes()).hexdigest()


def compute_build_id(acquisition_id: str, params: dict | None = None) -> str:
    payload = {"acquisition_id": acquisition_id, "features_code_sha256": code_sha256(), "params": params or PARAMS}
    return hashlib.sha256(acq.canonical(payload)).hexdigest()


# ---------------------------------------------------------------- leitura verificada
def cast_pbp(df: pl.DataFrame) -> pl.DataFrame:
    """Seleciona as colunas usadas e aplica os dtypes do hub (o raw traz quase tudo como Float64)."""
    return df.select([pl.col(c).cast(t, strict=False) for c, t in {**PLAY_SCHEMA, **RAW_EXTRA}.items()])



def _verify_sources(manifest: dict, home: Path) -> None:
    """Confere existência e sha256 de todos os arquivos listados no manifesto."""
    for entries in manifest["seasons"].values():
        for e in entries.values():
            if not e:
                continue
            path = home / e["path"]
            if not path.exists():
                raise FeatureError(f"arquivo do manifesto ausente: {e['path']}")
            if acq.sha256_file(path) != e["sha256"]:
                raise FeatureError(f"sha256 divergente do manifesto: {e['path']} (rode `cli.py acquire`)")


def _read_sources(manifest: dict, home: Path) -> tuple[pl.DataFrame, pl.DataFrame]:
    pbp_parts, sched_parts = [], []
    for season, entries in sorted(manifest["seasons"].items()):
        for kind, e in entries.items():
            if not e:
                continue
            path = home / e["path"]
            if kind == "pbp":
                cols = list(PLAY_SCHEMA) + list(RAW_EXTRA)
                pbp_parts.append(cast_pbp(pl.read_parquet(path, columns=cols)))
            else:
                sched_parts.append(pl.read_parquet(path, columns=list(acq.REQUIRED_SCHEDULE_COLUMNS)))
    if not sched_parts:
        raise FeatureError("manifesto sem schedules")
    return (pl.concat(pbp_parts) if pbp_parts else pl.DataFrame(schema={**PLAY_SCHEMA, **RAW_EXTRA})), \
        pl.concat(sched_parts, how="vertical_relaxed")


# ---------------------------------------------------------------- plays
def safety_scorer() -> pl.Expr:
    """Time que pontua num safety: ``posteam`` se o placar dele subiu 2 na jogada (punt com recuo do retornador no
    próprio end zone), senão ``defteam`` (caso comum e fallback quando a variação não é observável/nula)."""
    gained = (pl.col("posteam_score_post") - pl.col("posteam_score")) == 2
    return pl.when(gained).then(pl.col("posteam")).otherwise(pl.col("defteam"))


def add_next_score(df: pl.DataFrame) -> pl.DataFrame:
    """Acrescenta ``next_score_type`` e ``next_score_points`` (ver docstring do módulo). Exige ordem
    cronológica por jogo (game_id, play_id) e a coluna ``half``."""
    bad = df.filter((pl.col("touchdown") == 1) & pl.col("td_team").is_null())
    if bad.height:
        raise FeatureError(f"{bad.height} jogadas com touchdown==1 e td_team nulo")
    is_td, is_fg, is_sf = pl.col("touchdown") == 1, pl.col("field_goal_result") == "made", pl.col("safety") == 1
    ev_team = pl.when(is_td).then(pl.col("td_team")).when(is_fg).then(pl.col("posteam")) \
        .when(is_sf).then(safety_scorer())
    ev_kind = pl.when(is_td).then(pl.lit("TD")).when(is_fg).then(pl.lit("FG")).when(is_sf).then(pl.lit("SAFETY"))
    keys = ["game_id", "half"]
    d = df.with_columns(ev_team.alias("_ev_team"), ev_kind.alias("_ev_kind")).with_columns(
        pl.col("_ev_team").fill_null(strategy="backward").over(keys),
        pl.col("_ev_kind").fill_null(strategy="backward").over(keys))
    own = pl.col("_ev_team") == pl.col("posteam")
    kind = pl.when(pl.col("_ev_kind").is_null()).then(pl.lit("NO_SCORE")) \
        .when(own).then(pl.col("_ev_kind")).otherwise(pl.lit("OPP_") + pl.col("_ev_kind"))
    valid = pl.col("posteam").is_not_null() & pl.col("half").is_not_null()
    pts = pl.when(pl.col("_ev_kind") == "TD").then(7).when(pl.col("_ev_kind") == "FG").then(3) \
        .when(pl.col("_ev_kind") == "SAFETY").then(2).otherwise(0)
    return d.with_columns(
        pl.when(valid).then(kind).alias("next_score_type"),
        pl.when(valid).then(pl.when(own).then(pts).otherwise(-pts)).cast(pl.Int8).alias("next_score_points"),
    ).drop("_ev_team", "_ev_kind")


def build_plays(pbp: pl.DataFrame) -> pl.DataFrame:
    d = pbp.filter(pl.col("season_type").is_in(PARAMS["season_types"])).sort(["game_id", "play_id"]) \
        .with_columns([normalize_team(c) for c in TEAM_COLUMNS])
    dups = d.select(pl.struct("game_id", "play_id").is_duplicated().sum()).item()
    if dups:
        raise FeatureError(f"{dups} jogadas com (game_id, play_id) duplicado")
    d = d.with_columns(
        pl.when(pl.col("qtr").is_null()).then(None).when(pl.col("qtr") <= 2).then(1)
        .when(pl.col("qtr") <= 4).then(2).otherwise(3).cast(pl.Int8).alias("half"),
        pl.when(pl.col("posteam").is_null()).then(None).otherwise(pl.col("posteam") == pl.col("home_team"))
        .alias("posteam_is_home"))
    d = add_next_score(d)
    elig = (pl.col("posteam").is_not_null() & pl.col("yardline_100").is_not_null()
            & pl.col("down").is_between(1, 4) & pl.col("play_type").is_not_null()
            & ~pl.col("play_type").is_in(["kickoff", "extra_point"])
            & (pl.col("two_point_attempt").fill_null(0) != 1))
    d = d.with_columns(elig.fill_null(False).alias("ep_eligible"))
    order = ["game_id", "play_id", "season", "week", "season_type", "game_date", "posteam", "defteam", "home_team",
             "away_team", "posteam_is_home", "qtr", "half", "down", "ydstogo", "yardline_100",
             "half_seconds_remaining", "game_seconds_remaining", "goal_to_go", "score_differential",
             "posteam_timeouts_remaining", "defteam_timeouts_remaining", "roof", "play_type", "pass", "rush",
             "epa", "ep", "wp", "success", *PROBS, "touchdown", "td_team", "field_goal_result", "safety",
             "two_point_attempt", "next_score_type", "next_score_points", "ep_eligible"]
    return d.select(order)


# ---------------------------------------------------------------- games
def build_games(sched: pl.DataFrame) -> pl.DataFrame:
    kick = (pl.col("gameday") + pl.lit(" ") + pl.col("gametime")).str.to_datetime(
        "%Y-%m-%d %H:%M", strict=False, time_unit="us").dt.replace_time_zone(
        PARAMS["kickoff_tz"], ambiguous="earliest", non_existent="null").dt.convert_time_zone("UTC")
    d = sched.with_columns(kick.alias("kickoff_utc"),
                           pl.col("home_team").alias("home_team_raw"), pl.col("away_team").alias("away_team_raw"),
                           normalize_team("home_team").alias("home_team"),
                           normalize_team("away_team").alias("away_team"),
                           (pl.col("home_score").is_not_null() & pl.col("away_score").is_not_null())
                           .alias("completed"))
    dup = d["game_id"].is_duplicated().sum()
    if dup:
        raise FeatureError(f"{dup} game_id duplicados em schedules")
    return d.select(GAME_COLUMNS).sort(["kickoff_utc", "game_id"], nulls_last=True)


# ---------------------------------------------------------------- team_game
def build_team_game(plays: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    d = plays.filter(pl.col("play_type").is_in(PARAMS["team_game_play_types"]) & pl.col("epa").is_not_null()
                     & pl.col("posteam").is_not_null() & pl.col("defteam").is_not_null()
                     & (pl.col("two_point_attempt").fill_null(0) != 1))
    d = d.with_columns((pl.col("play_type") == "pass").cast(pl.Float64).alias("_pass"))
    off = d.group_by(["game_id", "posteam"]).agg(
        pl.len().alias("off_plays"), pl.col("epa").mean().alias("off_epa_per_play"),
        pl.col("success").mean().alias("off_success_rate"), pl.col("_pass").mean().alias("off_pass_rate")
    ).rename({"posteam": "team"})
    dfn = d.group_by(["game_id", "defteam"]).agg(
        pl.len().alias("def_plays"), pl.col("epa").mean().alias("def_epa_per_play"),
        pl.col("success").mean().alias("def_success_rate")).rename({"defteam": "team"})
    tg = off.join(dfn, on=["game_id", "team"], how="full", coalesce=True)
    g = games.select("game_id", "kickoff_utc", "season", "week", "home_team", "away_team", "home_score",
                     "away_score")
    tg = tg.join(g, on="game_id", how="inner")
    stray = tg.filter((pl.col("team") != pl.col("home_team")) & (pl.col("team") != pl.col("away_team")))
    if stray.height:
        raise FeatureError(f"{stray.height} linhas de team_game com time fora do jogo (siglas?): "
                           f"{sorted(stray['team'].unique().to_list())}")
    is_home = pl.col("team") == pl.col("home_team")
    tg = tg.with_columns(
        pl.when(is_home).then(pl.col("away_team")).otherwise(pl.col("home_team")).alias("opponent"),
        is_home.alias("is_home"),
        pl.when(is_home).then(pl.col("home_score")).otherwise(pl.col("away_score")).alias("points_for"),
        pl.when(is_home).then(pl.col("away_score")).otherwise(pl.col("home_score")).alias("points_against"))
    return tg.select(["game_id", "team", "kickoff_utc", "season", "week", "opponent", "is_home", "points_for",
                      "points_against", "off_plays", "off_epa_per_play", "off_success_rate", "off_pass_rate",
                      "def_plays", "def_epa_per_play", "def_success_rate"]).sort(["kickoff_utc", "game_id", "team"])


# ---------------------------------------------------------------- team_asof
def _wmean(vals: np.ndarray, w: np.ndarray) -> float | None:
    ok = ~np.isnan(vals)
    if not ok.any():
        return None
    return float(np.sum(vals[ok] * w[ok]) / np.sum(w[ok]))


def build_team_asof(games: pl.DataFrame, team_game: pl.DataFrame) -> pl.DataFrame:
    last_n, half_life = PARAMS["last_n"], PARAMS["ewm_half_life_games"]
    games_rows = pl.concat([
        games.select("game_id", "season", "week", "kickoff_utc", pl.col("home_team").alias("team"),
                     pl.col("away_team").alias("opponent"), pl.lit(True).alias("is_home")),
        games.select("game_id", "season", "week", "kickoff_utc", pl.col("away_team").alias("team"),
                     pl.col("home_team").alias("opponent"), pl.lit(False).alias("is_home"))
    ]).sort(["kickoff_utc", "game_id", "team"], nulls_last=True)
    tg = team_game.with_columns((pl.col("points_for") - pl.col("points_against")).alias("point_diff"))
    per_team: dict[str, dict] = {}
    for team, sub in tg.sort(["kickoff_utc", "game_id"]).group_by("team", maintain_order=True):
        t = team[0]
        arr = lambda c: np.array(sub[c].fill_null(float("nan")).cast(pl.Float64).to_list(), dtype=float)
        per_team[t] = {
            "kick": np.array([k.timestamp() * 1e6 for k in sub["kickoff_utc"].to_list()], dtype=float),
            "season": np.array(sub["season"].to_list()),
            "m": {"off_epa": arr("off_epa_per_play"), "def_epa": arr("def_epa_per_play"),
                  "off_success": arr("off_success_rate"), "def_success": arr("def_success_rate"),
                  "pass_rate": arr("off_pass_rate"), "point_diff": arr("point_diff")}}
    out = {c: [] for c in ("games_prior_season", "games_prior_total")}
    for pre in ("season", "last3", "ewm4"):
        for m in METRICS:
            out[f"{pre}_{m}"] = []
    for r in games_rows.iter_rows(named=True):
        info = per_team.get(r["team"])
        idx = 0
        if info is not None and r["kickoff_utc"] is not None:
            idx = int(np.searchsorted(info["kick"], r["kickoff_utc"].timestamp() * 1e6, side="left"))
        if r["kickoff_utc"] is None or idx == 0:
            count = None if r["kickoff_utc"] is None else 0
            for c in out:
                out[c].append(count if c.startswith("games_") else None)
            continue
        same = info["season"][:idx] == r["season"]
        age = np.arange(idx - 1, -1, -1)  # 0 = jogo mais recente
        ew = 0.5 ** (age / half_life)
        out["games_prior_season"].append(int(same.sum()))
        out["games_prior_total"].append(idx)
        for m in METRICS:
            v = info["m"][m][:idx]
            out[f"season_{m}"].append(_wmean(v[same], np.ones(int(same.sum()))) if same.any() else None)
            out[f"last3_{m}"].append(_wmean(v[-last_n:], np.ones(min(idx, last_n))))
            out[f"ewm4_{m}"].append(_wmean(v, ew))
    base = games_rows.select("game_id", "team", "opponent", "is_home", "season", "week", "kickoff_utc")
    cols = [pl.Series(k, v, dtype=pl.Int32 if k.startswith("games_") else pl.Float64) for k, v in out.items()]
    return base.with_columns(cols)


# ---------------------------------------------------------------- qualidade
def count_out_of_order_games(plays: pl.DataFrame) -> int:
    """Nº de jogos em que ``qtr`` diminui ao percorrer as jogadas por ``play_id`` (o nflverse numera algumas jogadas
    fora de ordem cronológica). Não muda ``half``: ele sai do ``qtr`` de cada jogada e coincide com o ``game_half``
    do nflverse (testado nos dados reais); só importa porque o alvo percorre as jogadas em ordem de ``play_id``."""
    d = plays.sort(["game_id", "play_id"]).filter(pl.col("qtr") < pl.col("qtr").shift(1).over("game_id"))
    return d["game_id"].n_unique()


# ---------------------------------------------------------------- build
def _write_parquet(df: pl.DataFrame, path: Path) -> None:
    df.write_parquet(path, compression="zstd", statistics=True, row_group_size=200_000)


def _build_is_valid(bdir: Path) -> bool:
    try:
        man = json.loads((bdir / "manifest.json").read_text())
        return all(acq.sha256_file(bdir / f"{t}.parquet") == man["tables"][t]["sha256"] for t in TABLES)
    except (OSError, ValueError, KeyError):
        return False


def check_coverage(manifest: dict, first_season: int = acq.FIRST_SEASON, last_season: int | None = None) -> None:
    """M-1: recusa um manifesto que não cubra ``first_season..last_season`` (padrão: 2011..temporada corrente)
    de forma contínua: toda temporada precisa de ``schedules`` e, exceto a última (que pode ainda não ter PBP),
    de ``pbp``. Um subconjunto silencioso produziria uma feature store (e um EP) treinados em poucas temporadas."""
    last = acq.current_season() if last_season is None else last_season
    have = {int(k): v for k, v in manifest["seasons"].items()}
    problems = []
    for s in range(first_season, last + 1):
        e = have.get(s)
        if not e or not e.get("schedules"):
            problems.append(f"{s}: sem schedules")
        elif s < last and not e.get("pbp"):
            problems.append(f"{s}: sem pbp")
    if problems:
        raise FeatureError(f"o manifesto não cobre {first_season}..{last} de forma contínua ({'; '.join(problems[:6])}"
                           f"{'...' if len(problems) > 6 else ''}); rode `cli.py acquire` sem --season, ou use "
                           "--allow-partial se for de propósito")


def build(acquisition_id: str | None = None, home: Path | None = None, allow_partial: bool = False,
          first_season: int = acq.FIRST_SEASON, last_season: int | None = None) -> str:
    """Constrói (ou reutiliza, se idêntico e íntegro) o feature store e devolve o ``build_id``.

    Recusa manifestos que não cubram ``first_season..last_season`` (ver ``check_coverage``), salvo ``allow_partial``."""
    from hubpaths import hub_home
    home = Path(home) if home else hub_home()
    acq.migrate_legacy(home)
    acq.clean_orphans(home / "features")
    manifest = acq.resolve_acquisition(acquisition_id, home)
    if not allow_partial:
        check_coverage(manifest, first_season, last_season)
    build_id = compute_build_id(manifest["acquisition_id"])
    final = home / "features" / build_id
    _verify_sources(manifest, home)
    if final.exists() and _build_is_valid(final):
        _set_current(home, build_id)
        return build_id
    pbp, sched = _read_sources(manifest, home)
    plays = build_plays(pbp)
    games = build_games(sched)
    team_game = build_team_game(plays, games)
    team_asof = build_team_asof(games, team_game)
    tmp = home / "features" / f".{build_id}.tmp-{os.getpid()}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        tables = {}
        for name, df in zip(TABLES, (plays, games, team_game, team_asof)):
            _write_parquet(df, tmp / f"{name}.parquet")
            tables[name] = {"sha256": acq.sha256_file(tmp / f"{name}.parquet"), "rows": df.height,
                            "columns": df.columns}
        bm = {"format": 1, "build_id": build_id, "acquisition_id": manifest["acquisition_id"],
              "features_code_sha256": code_sha256(), "params": PARAMS, "tables": tables,
              "qa": {"partial": bool(allow_partial), "games_qtr_out_of_order": count_out_of_order_games(plays)}}
        (tmp / "manifest.json").write_text(json.dumps(bm, indent=2, sort_keys=True))
        if final.exists():
            shutil.rmtree(final)  # build corrompido
        os.replace(tmp, final)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    _set_current(home, build_id)
    return build_id


def _set_current(home: Path, build_id: str) -> None:
    acq._atomic_write_bytes(home / "features" / "current.json", json.dumps({"build_id": build_id}).encode())


def resolve_build(build_id: str | None, home: Path) -> Path:
    """Diretório de um build (id completo, prefixo único, ou o mais recente)."""
    fdir = Path(home) / "features"
    if build_id is None:
        cur = fdir / "current.json"
        if not cur.exists():
            raise FeatureError("nenhum build; rode `cli.py build`")
        build_id = json.loads(cur.read_text())["build_id"]
    m = [p for p in fdir.iterdir() if p.is_dir() and p.name.startswith(build_id)] if fdir.exists() else []
    if len(m) != 1:
        raise FeatureError(f"build {build_id!r}: {len(m)} correspondências")
    return m[0]


def load_tables(build_id: str | None = None, home: Path | None = None) -> dict[str, pl.DataFrame]:
    """Lê as 4 tabelas de um build (conferindo sha256)."""
    from hubpaths import hub_home
    bdir = resolve_build(build_id, Path(home) if home else hub_home())
    if not _build_is_valid(bdir):
        raise FeatureError(f"build {bdir.name} corrompido")
    return {t: pl.read_parquet(bdir / f"{t}.parquet") for t in TABLES}
