"""WP pré-jogo (pyfunc, *models from code*): probabilidade de o MANDANTE vencer, só com informação anterior ao jogo.

Este arquivo é a ÚNICA fonte da matemática do WP pré-jogo: o treino (`models/wp_pregame.py`) o importa por caminho, o
MLflow o copia para dentro do modelo registrado. É autocontido (só numpy e pandas; o ajuste logístico usa o
scikit-learn no módulo de treino e entrega um JSON, aqui só se calcula a previsão).

Features (todas ANTES do jogo; `home_field` = 1 - campo neutro):
  elo_diff    rating Elo (em pontos de margem) do mandante menos o do visitante ANTES do jogo. `elo_online` percorre os
              jogos em ordem de kickoff e guarda o rating de cada time ANTES de cada jogo; só depois aplica o
              resultado. Logo a feature de um jogo só depende de jogos com kickoff anterior (testado), inclusive nos
              jogos de TREINO: ajustar o rating com o treino todo e aplicá-lo aos próprios jogos de treino vazaria o
              resultado do jogo para a feature. Hiperparâmetros do Elo iguais aos do `hub-ratings`.
  rest_diff   descanso do mandante menos o do visitante (dias, limitado a ±REST_CLIP), do calendário.
  div_game    1 se jogo de divisão (calendário).
  asof_*_diff diferença mandante - visitante de `team_asof` ewm4 (EPA ofensivo, EPA defensivo sofrido, saldo de pontos).
Sem intercepto: campo neutro e times iguais dão exatamente 0,5. As features entram divididas pelo desvio-padrão do
treino (sem centralizar), por isso o `params` guarda `scale`.

`params` (JSON puro): {"format": "hub-wp-pregame-v1", "kind": "logit"|"elo_direct", ...}. O modelo FINAL registrado traz
também `elo_state` (ratings do Elo depois do último jogo completo) para calcular `elo_diff` de jogos futuros a partir
de times, temporada e campo neutro.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow.models import set_model
from mlflow.pyfunc import PythonModel
from mlflow.types.type_hints import TypeFromExample

FORMAT = "hub-wp-pregame-v1"
KINDS = ("logit", "elo_direct")
ASOF_FEATURES = ("ewm4_off_epa", "ewm4_def_epa", "ewm4_point_diff")
ASOF_DIFF_COLUMNS = ("asof_off_epa_diff", "asof_def_epa_diff", "asof_point_diff_diff")
REST_CLIP = 7.0
FEATURE_COLUMNS = ("elo_diff", "home_field", "rest_diff", "div_game", *ASOF_DIFF_COLUMNS)
ELO_GAME_COLUMNS = ["game_id", "season", "kickoff_utc", "home_team", "away_team", "result", "neutral"]


# ------------------------------------------------------------------ Elo online (rating ANTES de cada jogo)

def elo_online(games: pd.DataFrame, k: float, hfa: float, cap: float, reversion: float) -> tuple:
    """(elo_home, elo_away, estado). Percorre `games` em ordem de (kickoff_utc, game_id) e devolve, ALINHADOS às
    linhas de entrada, o rating de cada lado ANTES do jogo. Jogos sem `result` (futuros) recebem o rating atual e
    não atualizam nada. A regressão à média (`reversion`) vale no primeiro jogo de cada temporada nova. Mesma
    matemática de `ratings_pyfunc.elo_fit` (testado: o estado final coincide).

    `estado` = {"ratings", "last_season", "k", "hfa", "cap", "reversion"} depois de percorrer tudo."""
    miss = [c for c in ELO_GAME_COLUMNS if c not in games.columns]
    if miss:
        raise ValueError(f"colunas ausentes: {miss}")
    n = len(games)
    order = (games.assign(_pos=np.arange(n), _k=pd.to_datetime(games["kickoff_utc"], utc=True))
             .sort_values(["_k", "game_id"], kind="mergesort")["_pos"].to_numpy())
    home, away = games["home_team"].to_numpy(), games["away_team"].to_numpy()
    season = games["season"].to_numpy()
    result = games["result"].to_numpy(dtype="float64")
    nn = (~games["neutral"].astype(bool)).to_numpy(dtype="float64")
    margin = np.clip(result, -cap, cap)
    eh, ea = np.zeros(n), np.zeros(n)
    r: dict = {}
    prev = None
    for i in order:
        if prev is not None and season[i] != prev:
            for t in r:
                r[t] *= 1.0 - reversion
        prev = season[i]
        rh, ra = r.get(home[i], 0.0), r.get(away[i], 0.0)
        eh[i], ea[i] = rh, ra
        if np.isfinite(result[i]):
            err = margin[i] - (hfa * nn[i] + rh - ra)
            r[home[i]], r[away[i]] = rh + k * err, ra - k * err
    state = {"ratings": {t: float(v) for t, v in sorted(r.items())},
             "last_season": None if prev is None else int(prev),
             "k": float(k), "hfa": float(hfa), "cap": float(cap), "reversion": float(reversion)}
    return eh, ea, state


def state_elo_diff(state: dict, home, away, season) -> np.ndarray:
    """elo_diff de jogos FUTUROS a partir do `elo_state`: ratings atuais, com a regressão de início de temporada
    (uma vez por temporada de diferença) se a temporada do jogo for maior que `last_season`. Time desconhecido
    levanta ValueError."""
    r = state["ratings"]
    out = np.empty(len(home))
    for i, (h, a) in enumerate(zip(home, away)):
        for t in (h, a):
            if t not in r:
                raise ValueError(f"time sem rating Elo: {t!r}")
        out[i] = r[h] - r[a]
    gap = np.maximum(np.asarray(season, dtype="float64") - state["last_season"], 0.0)
    return out * (1.0 - state["reversion"]) ** gap


# ------------------------------------------------------------------ features de contexto (calendário e team_asof)

def asof_columns() -> list:
    return [f"{s}_{f}" for f in ASOF_FEATURES for s in ("home", "away")]


def context_features(df: pd.DataFrame, need=("home_field", "rest_diff", "div_game", *ASOF_DIFF_COLUMNS)) -> pd.DataFrame:
    """Features do calendário e do `team_asof` do PRÓPRIO jogo. `df`: neutral, home_rest, away_rest, div_game, e
    `home_<f>`/`away_<f>` (f em ASOF_FEATURES). Só exige as colunas das features pedidas em `need`."""
    out = pd.DataFrame(index=df.index)
    if "home_field" in need:
        out["home_field"] = 1.0 - df["neutral"].astype(bool).to_numpy(dtype="float64")
    if "rest_diff" in need:
        out["rest_diff"] = np.clip(df["home_rest"].to_numpy(dtype="float64") - df["away_rest"].to_numpy(dtype="float64"),
                                   -REST_CLIP, REST_CLIP)
    if "div_game" in need:
        out["div_game"] = df["div_game"].to_numpy(dtype="float64")
    for f, col in zip(ASOF_FEATURES, ASOF_DIFF_COLUMNS):
        if col in need:
            out[col] = df[f"home_{f}"].to_numpy(dtype="float64") - df[f"away_{f}"].to_numpy(dtype="float64")
    return out


def make_features(games: pd.DataFrame, elo: dict) -> pd.DataFrame:
    """Todas as features pré-jogo de TODOS os jogos de `games` (completos e futuros) de uma vez, mais `elo_home`,
    `elo_away` e o estado final do Elo em `.attrs["elo_state"]`. Cada valor só depende de jogos anteriores."""
    eh, ea, state = elo_online(games, elo["k"], elo["hfa"], elo["cap"], elo["reversion"])
    out = context_features(games)
    out.insert(0, "elo_diff", eh - ea)
    out.insert(0, "elo_away", ea)
    out.insert(0, "elo_home", eh)
    out.attrs["elo_state"] = state
    return out


# ------------------------------------------------------------------ previsão

def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.asarray(z, dtype="float64")))


def normal_cdf(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + np.vectorize(math.erf)(np.asarray(x, dtype="float64") / math.sqrt(2.0)))


def predict_features(params: dict, feats: pd.DataFrame) -> np.ndarray:
    """P(mandante vence) a partir das features já calculadas (`elo_diff`, `home_field`, ...). Feature nula levanta
    ValueError: não se imputa."""
    if params.get("format") != FORMAT or params.get("kind") not in KINDS:
        raise ValueError(f"params inesperado (format={params.get('format')!r}, kind={params.get('kind')!r})")
    if params["kind"] == "elo_direct":
        x = feats[["elo_diff", "home_field"]].to_numpy(dtype="float64")
        if not np.isfinite(x).all():
            raise ValueError("feature nula em jogo a prever")
        return normal_cdf((x[:, 0] + params["hfa"] * x[:, 1]) / params["sigma"])
    names = params["features"]
    X = feats[names].to_numpy(dtype="float64")
    if not np.isfinite(X).all():
        raise ValueError("feature nula em jogo a prever (team_asof ausente?)")
    z = (X / np.asarray(params["scale"], dtype="float64")) @ np.asarray(params["coef"], dtype="float64")
    return sigmoid(z + params.get("intercept", 0.0))


def raw_columns(params: dict) -> list:
    """Colunas BRUTAS que o pyfunc exige para este modelo."""
    names = ["elo_diff", "home_field"] if params["kind"] == "elo_direct" else list(params["features"])
    cols = ["home_team", "away_team", "season", "neutral"]
    if "rest_diff" in names:
        cols += ["home_rest", "away_rest"]
    if "div_game" in names:
        cols += ["div_game"]
    if any(c in names for c in ASOF_DIFF_COLUMNS):
        cols += asof_columns()
    return cols


def predict_raw(params: dict, raw: pd.DataFrame) -> pd.DataFrame:
    """P(mandante vence) e `elo_diff` a partir de times, temporada, campo neutro e (conforme o modelo) descanso,
    divisão e `team_asof`. Usa `params["elo_state"]` (só o modelo final o tem)."""
    if "elo_state" not in params:
        raise ValueError("params sem `elo_state`: só o modelo final registrado prevê a partir de times")
    missing = [c for c in raw_columns(params) if c not in raw.columns]
    if missing:
        raise ValueError(f"colunas ausentes na entrada: {missing}")
    if raw[raw_columns(params)].isna().any().any():
        raise ValueError("entrada com nulos")
    names = ["elo_diff", "home_field"] if params["kind"] == "elo_direct" else list(params["features"])
    feats = context_features(raw, [c for c in names if c != "elo_diff"])
    feats["elo_diff"] = state_elo_diff(params["elo_state"], raw["home_team"], raw["away_team"], raw["season"])
    return pd.DataFrame({"p_home": predict_features(params, feats), "elo_diff": feats["elo_diff"].to_numpy()}, index=raw.index)


def input_frame(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Entrada do pyfunc com tipos estáveis para o schema do MLflow: times em texto, o resto em float64."""
    out = pd.DataFrame(index=df.index)
    for c in raw_columns(params):
        out[c] = df[c].astype(object) if c in ("home_team", "away_team") else df[c].astype("float64")
    return out


# ------------------------------------------------------------------ mercado (referência fora da regra)

def implied_prob(ml) -> np.ndarray:
    """Probabilidade implícita (com margem da casa) de uma moneyline americana: 100/(ml+100) se ml > 0 e
    -ml/(-ml+100) se ml < 0. Moneyline nula, ausente ou entre -100 e +100 (não existe) -> NaN."""
    ml = np.asarray(ml, dtype="float64")
    out = np.full(ml.shape, np.nan)
    pos, neg = ml >= 100, ml <= -100
    out[pos] = 100.0 / (ml[pos] + 100.0)
    out[neg] = -ml[neg] / (-ml[neg] + 100.0)
    return out


def market_prob(ml_home, ml_away) -> np.ndarray:
    """Probabilidade justa de o mandante vencer: remoção PROPORCIONAL da margem da casa,
    p = imp(home) / (imp(home) + imp(away)). Sem par válido -> NaN."""
    ph, pa = implied_prob(ml_home), implied_prob(ml_away)
    return ph / (ph + pa)


class WpPregameModel(PythonModel):
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
        return predict_raw(self.params, pd.DataFrame(model_input))


set_model(WpPregameModel())
