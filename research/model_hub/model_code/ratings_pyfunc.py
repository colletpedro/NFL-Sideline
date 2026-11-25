"""Ratings de times (pyfunc, *models from code*): funções PURAS sobre o histórico de jogos completos, sem pickle.

Este arquivo é a ÚNICA fonte da matemática dos ratings: o treino (`models/ratings.py`) o importa por caminho, o MLflow
o copia para dentro do modelo registrado e a H7 (WP pré-jogo) pode reutilizá-lo. É autocontido.

Convenção de tudo aqui: margem = pontos do MANDANTE - pontos do visitante (`result` do nflverse). A previsão é
    margem_prevista = hfa * (1 - neutro) + rating(mandante) - rating(visitante)
em pontos; campo neutro não tem vantagem de casa. Os três ajustes (`elo_fit`, `ridge_fit`, `asof_fit`) devolvem um
dict JSON puro com a mesma forma, e `predict_margin` o consome:
  {"format": "hub-ratings-v1", "kind": "elo"|"ridge_decay"|"asof_linear", "hfa": float, "ratings": {time: float},
   "last_season": int, "n_games": int, ...hiperparâmetros e metadados}

Entrada de `hist` (DataFrame de jogos COMPLETOS, qualquer ordem): game_id, season, kickoff_utc, home_team, away_team,
result, neutral (bool). Quem chama garante que `hist` só tem jogos anteriores ao instante da previsão (os splits do
backtest e o histórico semanal fazem isso); as funções não olham o relógio. Time desconhecido em `predict_margin`
levanta ValueError (não há rating a inventar).

Elo (em pontos de margem): a cada jogo, em ordem de `kickoff_utc`, erro = margem_real_limitada(±cap) - margem_prevista;
rating(mandante) += k * erro; rating(visitante) -= k * erro (soma zero). Na primeira partida de cada temporada nova os
ratings regridem à média 0 por `reversion` (1/3: r <- r * 2/3). Em `predict_margin`, se a temporada do jogo for maior
que `last_season`, a mesma regressão é aplicada (uma vez por temporada de diferença). A vantagem de casa `hfa` é um
hiperparâmetro FIXO.

Ridge com decaimento: mínimos quadrados ponderados de margem = hfa*nn + r_mandante - r_visitante, com penalidade
lambda*||r||^2 (hfa sem penalidade) e peso 0.5^(idade/meia_vida), idade em semanas de calendário entre o jogo e o
último jogo do histórico. `hfa` é estimado.

asof_linear: margem = hfa*nn + b . (x_mandante - x_visitante), x = (ewm4_off_epa, ewm4_def_epa, ewm4_point_diff) do
`team_asof` (estado ANTES de cada jogo). O rating de um time é b . x do estado antes do seu PRÓXIMO jogo.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow.models import set_model
from mlflow.pyfunc import PythonModel
from mlflow.types.type_hints import TypeFromExample

FORMAT = "hub-ratings-v1"
KINDS = ("elo", "ridge_decay", "asof_linear")
ASOF_FEATURES = ("ewm4_off_epa", "ewm4_def_epa", "ewm4_point_diff")
GAME_COLUMNS = ["game_id", "season", "kickoff_utc", "home_team", "away_team", "result", "neutral"]
INPUT_COLUMNS = ["home_team", "away_team", "neutral"]
OUTPUT_COLUMNS = ["pred_margin", "home_rating", "away_rating"]


def _check_hist(hist: pd.DataFrame, extra=()) -> pd.DataFrame:
    need = [*GAME_COLUMNS, *extra]
    missing = [c for c in need if c not in hist.columns]
    if missing:
        raise ValueError(f"colunas ausentes no histórico: {missing}")
    if len(hist) == 0:
        raise ValueError("histórico vazio")
    if hist["result"].isna().any():
        raise ValueError("histórico com `result` nulo: só jogos completos")
    out = hist.copy()
    out["kickoff_utc"] = pd.to_datetime(out["kickoff_utc"], utc=True)
    return out.sort_values(["kickoff_utc", "game_id"], kind="mergesort").reset_index(drop=True)


def _base(kind: str, hist: pd.DataFrame, hfa: float, ratings: dict, **extra) -> dict:
    return {"format": FORMAT, "kind": kind, "hfa": float(hfa),
            "ratings": {t: float(v) for t, v in sorted(ratings.items())},
            "last_season": int(hist["season"].max()), "n_games": int(len(hist)),
            "as_of": hist["kickoff_utc"].max().isoformat(), **extra}


# ------------------------------------------------------------------ Elo em pontos

def elo_fit(hist: pd.DataFrame, k: float, hfa: float, cap: float, reversion: float) -> dict:
    """Percorre `hist` em ordem de kickoff e devolve os ratings DEPOIS do último jogo (sem regressão pendente)."""
    h = _check_hist(hist)
    r: dict = {}
    prev_season = None
    nn = (~h["neutral"].astype(bool)).to_numpy(dtype="float64")
    margin = np.clip(h["result"].to_numpy(dtype="float64"), -cap, cap)
    for i, (home, away, season) in enumerate(zip(h["home_team"], h["away_team"], h["season"])):
        if prev_season is not None and season != prev_season:
            for t in r:
                r[t] *= 1.0 - reversion
        prev_season = season
        rh, ra = r.get(home, 0.0), r.get(away, 0.0)
        err = margin[i] - (hfa * nn[i] + rh - ra)
        r[home], r[away] = rh + k * err, ra - k * err
    return _base("elo", h, hfa, r, k=float(k), cap=float(cap), reversion=float(reversion))


# ------------------------------------------------------------------ ridge com decaimento temporal

def decay_weights(kickoff: pd.Series, halflife_weeks: float) -> np.ndarray:
    """0.5 ** (idade / meia_vida); idade = semanas de calendário até o último kickoff de `kickoff` (o mais novo pesa 1)."""
    k = pd.to_datetime(kickoff, utc=True)
    age = (k.max() - k).dt.total_seconds().to_numpy(dtype="float64") / (7 * 86400.0)
    return 0.5 ** (age / halflife_weeks)


def ridge_fit(hist: pd.DataFrame, halflife_weeks: float, lam: float) -> dict:
    h = _check_hist(hist)
    teams = sorted(set(h["home_team"]) | set(h["away_team"]))
    idx = {t: i for i, t in enumerate(teams)}
    n, p = len(h), len(teams)
    X = np.zeros((n, p + 1))
    rows = np.arange(n)
    X[rows, h["home_team"].map(idx).to_numpy()] += 1.0
    X[rows, h["away_team"].map(idx).to_numpy()] -= 1.0
    X[:, p] = (~h["neutral"].astype(bool)).to_numpy(dtype="float64")
    if not X[:, p].any():
        raise ValueError("histórico sem jogo em campo não neutro: hfa não identificável")
    y = h["result"].to_numpy(dtype="float64")
    w = decay_weights(h["kickoff_utc"], halflife_weeks)
    A = X.T @ (X * w[:, None])
    A[np.arange(p), np.arange(p)] += lam  # só os ratings são penalizados; hfa (última coluna) não
    beta = np.linalg.solve(A, X.T @ (w * y))
    return _base("ridge_decay", h, beta[p], dict(zip(teams, beta[:p])),
                 halflife_weeks=float(halflife_weeks), lam=float(lam))


# ------------------------------------------------------------------ regressão linear sobre team_asof

def asof_diffs(df: pd.DataFrame) -> np.ndarray:
    """Matriz n x 3 de (home_<f> - away_<f>) para f em ASOF_FEATURES; nulo permanece NaN."""
    miss = [f"{s}_{f}" for f in ASOF_FEATURES for s in ("home", "away") if f"{s}_{f}" not in df.columns]
    if miss:
        raise ValueError(f"colunas ausentes: {miss}")
    return np.column_stack([df[f"home_{f}"].to_numpy(dtype="float64") - df[f"away_{f}"].to_numpy(dtype="float64")
                            for f in ASOF_FEATURES])


def asof_fit(hist: pd.DataFrame, state: pd.DataFrame | None = None) -> dict:
    """OLS sem intercepto de `result` em [nn, diferenças asof]. Linhas com asof nulo (só o 1º jogo de cada time na
    história) saem do ajuste e são contadas em `n_dropped_null`. `state`: índice = time, colunas ASOF_FEATURES (o
    estado antes do próximo jogo de cada time); com ele, os ratings são b . estado, sem ele ficam vazios."""
    h = _check_hist(hist, [f"{s}_{f}" for f in ASOF_FEATURES for s in ("home", "away")])
    D = asof_diffs(h)
    ok = np.isfinite(D).all(axis=1)
    if ok.sum() < 10:
        raise ValueError("poucos jogos com team_asof para ajustar")
    X = np.column_stack([(~h["neutral"].astype(bool)).to_numpy(dtype="float64"), D])[ok]
    y = h["result"].to_numpy(dtype="float64")[ok]
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    coef = dict(zip(ASOF_FEATURES, beta[1:]))
    ratings = {}
    if state is not None:
        for team, row in state.iterrows():
            ratings[team] = float(sum(coef[f] * float(row[f]) for f in ASOF_FEATURES))
    return _base("asof_linear", h, beta[0], ratings, coef={f: float(v) for f, v in coef.items()},
                 n_dropped_null=int((~ok).sum()))


# ------------------------------------------------------------------ previsão

def _rating_lookup(params: dict, teams) -> np.ndarray:
    r = params["ratings"]
    out = np.empty(len(teams))
    for i, t in enumerate(teams):
        if t not in r:
            raise ValueError(f"time sem rating: {t!r}")
        out[i] = r[t]
    return out


def season_scale(params: dict, season) -> np.ndarray | float:
    """Fator de regressão à média do Elo para jogos de temporada maior que `last_season` (1 em qualquer outro caso)."""
    rev = params.get("reversion", 0.0) if params.get("kind") == "elo" else 0.0
    if season is None or not rev:
        return 1.0
    gap = np.maximum(np.asarray(season, dtype="float64") - params["last_season"], 0.0)
    return (1.0 - rev) ** gap


def team_ratings(params: dict, season=None) -> dict:
    """Ratings por time; com `season` (int) maior que `last_season`, o Elo aplica a regressão do início de temporada."""
    s = float(season_scale(params, season))
    return {t: v * s for t, v in params["ratings"].items()}


def predict_ratings(params: dict, home, away, neutral, season=None) -> tuple:
    """(rating_mandante, rating_visitante) por jogo, já com a regressão de temporada do Elo quando houver `season`."""
    if params.get("format") != FORMAT or params.get("kind") not in KINDS:
        raise ValueError(f"params inesperado (format={params.get('format')!r}, kind={params.get('kind')!r})")
    sc = season_scale(params, season)
    return _rating_lookup(params, list(home)) * sc, _rating_lookup(params, list(away)) * sc


def predict_margin(params: dict, home, away, neutral, season=None) -> np.ndarray:
    """Margem prevista do mandante: hfa * (1 - neutro) + rating(mandante) - rating(visitante)."""
    rh, ra = predict_ratings(params, home, away, neutral, season)
    nn = 1.0 - np.asarray(neutral, dtype="float64")
    return params["hfa"] * nn + rh - ra


def predict_asof(params: dict, df: pd.DataFrame) -> np.ndarray:
    """Margem do `asof_linear` a partir das diferenças do PRÓPRIO jogo (nulo levanta ValueError, sem imputar)."""
    if params.get("kind") != "asof_linear":
        raise ValueError("predict_asof só vale para kind=asof_linear")
    D = asof_diffs(df)
    if not np.isfinite(D).all():
        raise ValueError("team_asof nulo em jogo a prever")
    b = np.array([params["coef"][f] for f in ASOF_FEATURES])
    return params["hfa"] * (~df["neutral"].astype(bool)).to_numpy(dtype="float64") + D @ b


def input_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Entrada do pyfunc com tipos estáveis para o schema do MLflow: times em texto, `neutral` em float64 (0/1)."""
    out = pd.DataFrame(index=df.index)
    out["home_team"] = df["home_team"].astype(object)
    out["away_team"] = df["away_team"].astype(object)
    out["neutral"] = df["neutral"].astype("float64")
    return out


def predict_frame(params: dict, df: pd.DataFrame) -> pd.DataFrame:
    """pred_margin, home_rating e away_rating para (home_team, away_team, neutral); sem `season` (ratings 'de agora')."""
    missing = [c for c in INPUT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"colunas ausentes na entrada: {missing}")
    if df[INPUT_COLUMNS].isna().any().any():
        raise ValueError("entrada com nulos")
    neutral = df["neutral"].to_numpy(dtype="float64") > 0.5
    rh, ra = predict_ratings(params, df["home_team"], df["away_team"], neutral)
    margin = predict_margin(params, df["home_team"], df["away_team"], neutral)
    return pd.DataFrame({"pred_margin": margin, "home_rating": rh, "away_rating": ra}, index=df.index)


class RatingsModel(PythonModel):
    def load_context(self, context):
        path = Path(context.artifacts["params_json"])
        expected = Path(context.artifacts["params_sha256"]).read_text().strip()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"params.json adulterado: sha256 {actual} difere do registrado {expected}")
        params = json.loads(path.read_text())
        if params.get("format") != FORMAT or params.get("kind") not in KINDS:
            raise ValueError(f"params.json inesperado (format={params.get('format')!r}, kind={params.get('kind')!r})")
        self.params = params

    def predict(self, context, model_input: TypeFromExample, params=None):
        return predict_frame(self.params, pd.DataFrame(model_input))


set_model(RatingsModel())
