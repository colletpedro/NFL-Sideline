"""Gerador sintético de PBP/schedules com as colunas reais mínimas (REQUIRED_* de acquire.py) e loader falso.

Uso: ``league = synthetic_league([2023, 2024], seed=1)``; ``FakeLoader(league)`` serve de ``loader=`` para
``acquire.acquire``. ``pbp_frame(rows)`` monta jogadas à mão (valores padrão neutros) para testes de alvo.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import acquire as acq  # noqa: E402

PBP_DEFAULTS = {
    "game_id": "2024_01_AAA_BBB", "play_id": 1.0, "season": 2024, "week": 1, "season_type": "REG",
    "game_date": "2024-09-08", "posteam": "AAA", "defteam": "BBB", "home_team": "AAA", "away_team": "BBB",
    "qtr": 1.0, "down": 1.0, "ydstogo": 10.0, "yardline_100": 75.0, "half_seconds_remaining": 1500.0,
    "game_seconds_remaining": 3300.0, "goal_to_go": 0.0, "score_differential": 0.0,
    "posteam_timeouts_remaining": 3.0, "defteam_timeouts_remaining": 3.0, "roof": "outdoors",
    "play_type": "run", "pass": 0.0, "rush": 1.0, "epa": 0.1, "ep": 1.0, "wp": 0.5, "success": 1.0,
    "no_score_prob": 0.2, "opp_fg_prob": 0.1, "opp_safety_prob": 0.0, "opp_td_prob": 0.1, "fg_prob": 0.2,
    "safety_prob": 0.0, "td_prob": 0.4, "touchdown": 0.0, "td_team": None, "field_goal_result": None,
    "safety": 0.0, "two_point_attempt": 0.0, "posteam_score": None, "posteam_score_post": None,
}
_STR = {"game_id", "season_type", "game_date", "posteam", "defteam", "home_team", "away_team", "roof",
        "play_type", "td_team", "field_goal_result"}
_INT = {"season", "week"}


def pbp_frame(rows: list[dict]) -> pl.DataFrame:
    """Jogadas com padrões neutros; ``play_id`` sequencial quando omitido."""
    full = []
    for i, r in enumerate(rows, 1):
        d = {**PBP_DEFAULTS, "play_id": float(i), **r}
        full.append(d)
    schema = {c: (pl.String if c in _STR else pl.Int32 if c in _INT else pl.Float64) for c in PBP_DEFAULTS}
    return pl.DataFrame(full, schema=schema)


def _simulate_game(rng: random.Random, season: int, week: int, home: str, away: str, date: str,
                   with_pbp: bool) -> tuple[list[dict], dict]:
    gid = f"{season}_{week:02d}_{away}_{home}"
    rows, score = [], {home: 0, away: 0}
    pid = 1
    for qtr in (1, 2, 3, 4):
        for drive in range(2):
            pos = home if (qtr + drive) % 2 else away
            dfn = away if pos == home else home
            n = rng.randint(3, 6)
            outcome = rng.choice(["td", "fg", "none", "none"])
            for k in range(n):
                last = k == n - 1
                pt = rng.choice(["pass", "run"])
                ev = {"game_id": gid, "play_id": float(pid), "season": season, "week": week, "game_date": date,
                      "home_team": home, "away_team": away, "posteam": pos, "defteam": dfn, "qtr": float(qtr),
                      "down": float(min(k + 1, 4)), "play_type": pt, "pass": float(pt == "pass"),
                      "rush": float(pt == "run"), "epa": round(rng.gauss(0.0, 1.0), 4),
                      "success": float(rng.random() < 0.45),
                      "score_differential": float(score[pos] - score[dfn]),
                      "half_seconds_remaining": float(1800 - 300 * (drive * 3 + k) // 2),
                      "game_seconds_remaining": float(3600 - ((qtr - 1) * 900 + 100 * (drive * 3 + k)))}
                if last and outcome == "td":
                    ev.update(touchdown=1.0, td_team=pos); score[pos] += 7
                elif last and outcome == "fg":
                    ev.update(play_type="field_goal", field_goal_result="made", **{"pass": 0.0, "rush": 0.0})
                    score[pos] += 3
                rows.append(ev); pid += 1
    sched = {"game_id": gid, "season": season, "week": week, "game_type": "REG", "gameday": date,
             "gametime": "13:00", "home_team": home, "away_team": away, "home_score": score[home] if with_pbp else None,
             "away_score": score[away] if with_pbp else None,
             "result": score[home] - score[away] if with_pbp else None,
             "total": score[home] + score[away] if with_pbp else None, "spread_line": -2.5, "total_line": 44.5,
             "home_moneyline": -140, "away_moneyline": 120, "roof": "outdoors", "surface": "grass", "temp": 70,
             "wind": 5, "div_game": 0, "home_rest": 7, "away_rest": 7, "location": "Home"}
    return (rows if with_pbp else []), sched


def synthetic_league(seasons: list[int], teams: int = 6, weeks: int = 4, seed: int = 1,
                     future_weeks: dict[int, int] | None = None,
                     team_names: list[str] | None = None) -> dict[int, dict[str, pl.DataFrame]]:
    """{season: {"pbp": df, "schedules": df}}. ``future_weeks[season]`` = nº de semanas finais SEM placar/PBP.
    ``team_names`` substitui os nomes ``T00..`` (e fixa ``teams``)."""
    names = list(team_names) if team_names else [f"T{i:02d}" for i in range(teams)]
    teams = len(names)
    out = {}
    for season in seasons:
        rng = random.Random(seed * 1000 + season)
        rows, scheds = [], []
        nfuture = (future_weeks or {}).get(season, 0)
        for week in range(1, weeks + 1):
            order = names[:]
            rng.shuffle(order)
            day = 8 + 7 * (week - 1)
            date = f"{season}-{9 + day // 31:02d}-{day % 31 + 1:02d}"
            for i in range(0, teams - 1, 2):
                r, s = _simulate_game(rng, season, week, order[i], order[i + 1], date, week <= weeks - nfuture)
                rows += r
                scheds.append(s)
        out[season] = {"pbp": (_frame_keep_ids(rows) if rows else pbp_frame([{}]).clear()), "schedules": pl.DataFrame(
            scheds, schema={**{c: pl.String for c in ("game_id", "game_type", "gameday", "gametime", "home_team",
                               "away_team", "roof", "surface", "location")},
                            **{c: pl.Int32 for c in ("season", "week", "home_score", "away_score", "result", "total",
                               "home_moneyline", "away_moneyline", "temp", "wind", "div_game", "home_rest",
                               "away_rest")},
                            "spread_line": pl.Float64, "total_line": pl.Float64})}
    return out


def with_historic_codes(league: dict, old_codes: dict[str, str], through: int) -> dict:
    """Reproduz a divergência real: nas temporadas ``<= through`` o ``schedules`` (e o ``game_id``, em ambas as
    tabelas) usa a sigla histórica (``{"LV": "OAK"}``), enquanto as colunas de time do PBP seguem com a atual."""
    def gid(g: str) -> str:
        parts = g.split("_")
        return "_".join(parts[:2] + [old_codes.get(t, t) for t in parts[2:]])
    out = {}
    for season, d in league.items():
        if season > through:
            out[season] = d
            continue
        sched = d["schedules"].with_columns(
            pl.col("game_id").map_elements(gid, return_dtype=pl.String),
            pl.col("home_team").replace(old_codes), pl.col("away_team").replace(old_codes))
        pbp = d["pbp"].with_columns(pl.col("game_id").map_elements(gid, return_dtype=pl.String))
        out[season] = {"pbp": pbp, "schedules": sched}
    return out


def _frame_keep_ids(rows: list[dict]) -> pl.DataFrame:
    full = [{**PBP_DEFAULTS, **r} for r in rows]
    schema = {c: (pl.String if c in _STR else pl.Int32 if c in _INT else pl.Float64) for c in PBP_DEFAULTS}
    return pl.DataFrame(full, schema=schema)


class FakeLoader:
    """Loader injetável: serve ``league`` e registra chamadas. ``fail`` = {(kind, season): exceção}."""

    def __init__(self, league: dict, fail: dict | None = None):
        self.league, self.fail, self.calls = league, fail or {}, []

    def __call__(self, kind: str, season: int):
        self.calls.append((kind, season))
        if (kind, season) in self.fail:
            raise self.fail[(kind, season)]
        if season not in self.league:
            raise acq.SourceNotPublished(f"{kind} {season}")
        return self.league[season][kind]
