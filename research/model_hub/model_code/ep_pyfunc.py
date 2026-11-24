"""Expected Points v1 (pyfunc, *models from code*): regressão logística multinomial em JSON, sem pickle.

Este arquivo é a ÚNICA fonte da receita de features: o treino (`models/ep.py`) o importa por caminho e o MLflow o
copia para dentro do modelo registrado, então treino e serviço usam exatamente o mesmo código. É autocontido.

`params.json` (formato `hub-ep-logit-v1`):
  {"format", "recipe_version", "features": [nomes], "classes": [7 rótulos], "points": [7,3,2,-7,-3,-2,0],
   "intercept": [7], "coef": [[d] * 7], "mean": [d], "scale": [d], ...metadados de treino}
O pyfunc recebe as colunas BRUTAS (`RAW_COLUMNS`) e devolve um DataFrame com `p_<classe>` (7 colunas, na ordem
de `classes`, somando 1) e `ep` = soma(p * pontos).

Receita de features (nome -> valor), com y = yardline_100, t = half_seconds_remaining:
  yardline_100, half_seconds_remaining, goal_to_go, posteam_timeouts_remaining, defteam_timeouts_remaining,
  posteam_is_home (0/1), down_2|down_3|down_4 (indicador), log_ydstogo = ln(ydstogo), is_overtime = (half == 3),
  is_dome = roof em {dome, closed}, relu_yl_k<K> = max(y - K, 0), relu_t_<K> = max(K - t, 0),
  down<d>_x_yardline_100 = (down == d) * y, t_x_yardline_100 = t * y, relu_t_300_x_yardline_100 = max(300 - t, 0) * y.
O schema do MLflow é `double` (texto em `roof`): passe a entrada por `raw_frame(df)`.
Valores nulos nas colunas necessárias NÃO são imputados: levantam ValueError (o treino exclui essas linhas e conta).
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow.models import set_model
from mlflow.pyfunc import PythonModel
from mlflow.types.type_hints import TypeFromExample

FORMAT = "hub-ep-logit-v1"
RECIPE_VERSION = 1
CLASSES = ["TD", "FG", "SAFETY", "OPP_TD", "OPP_FG", "OPP_SAFETY", "NO_SCORE"]
POINTS = [7, 3, 2, -7, -3, -2, 0]
PROB_COLUMNS = [f"p_{c}" for c in CLASSES]
RAW_COLUMNS = ["yardline_100", "down", "ydstogo", "goal_to_go", "half_seconds_remaining",
               "posteam_timeouts_remaining", "defteam_timeouts_remaining", "posteam_is_home", "half", "roof"]
DOME_ROOFS = ("dome", "closed")

_PLAIN = {"yardline_100": ("yardline_100",), "half_seconds_remaining": ("half_seconds_remaining",),
          "goal_to_go": ("goal_to_go",), "posteam_timeouts_remaining": ("posteam_timeouts_remaining",),
          "defteam_timeouts_remaining": ("defteam_timeouts_remaining",), "posteam_is_home": ("posteam_is_home",),
          "log_ydstogo": ("ydstogo",), "is_overtime": ("half",), "is_dome": ("roof",),
          "t_x_yardline_100": ("half_seconds_remaining", "yardline_100"),
          "relu_t_300_x_yardline_100": ("half_seconds_remaining", "yardline_100")}
_RE_DOWN = re.compile(r"^down_([234])$")
_RE_DOWN_X = re.compile(r"^down([234])_x_yardline_100$")
_RE_RELU_YL = re.compile(r"^relu_yl_k(\d+)$")
_RE_RELU_T = re.compile(r"^relu_t_(\d+)$")


def _needs(name: str) -> tuple:
    if name in _PLAIN:
        return _PLAIN[name]
    if _RE_DOWN.match(name):
        return ("down",)
    if _RE_DOWN_X.match(name):
        return ("down", "yardline_100")
    if _RE_RELU_YL.match(name):
        return ("yardline_100",)
    if _RE_RELU_T.match(name):
        return ("half_seconds_remaining",)
    raise ValueError(f"feature desconhecida: {name!r}")


def required_columns(features) -> list:
    """Colunas brutas necessárias para as features (ordem de RAW_COLUMNS)."""
    need = {c for f in features for c in _needs(f)}
    return [c for c in RAW_COLUMNS if c in need]


def raw_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Colunas brutas com tipos estáveis (numéricas em float64, `roof` texto): serve ao exemplo de entrada do
    MLflow, cujo schema então aceita int/float/bool vindos de qualquer fonte."""
    out = pd.DataFrame(index=df.index)
    for c in RAW_COLUMNS:
        out[c] = df[c].astype(object).where(df[c].notna(), None) if c == "roof" else df[c].astype("float64")
    return out


def check_inputs(df: pd.DataFrame, cols) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"colunas ausentes na entrada: {missing}")
    bad = [c for c in cols if df[c].isna().any()]
    if bad:
        raise ValueError(f"valores nulos em {bad}: o modelo não imputa; remova essas linhas antes")


def usable_mask(df: pd.DataFrame) -> np.ndarray:
    """Linhas sem nulos em NENHUMA coluna bruta (e com ydstogo > 0): as únicas que o treino usa."""
    ok = df[RAW_COLUMNS].notna().all(axis=1).to_numpy()
    with np.errstate(invalid="ignore"):
        ok &= (pd.to_numeric(df["ydstogo"], errors="coerce") > 0).to_numpy()
    return ok


def feature_matrix(df: pd.DataFrame, features) -> np.ndarray:
    """Matriz n×d (float64) das features na ordem dada, calculada das colunas brutas."""
    check_inputs(df, required_columns(features))
    num = lambda c: df[c].to_numpy(dtype="float64")  # noqa: E731  (bool/int/float -> float64)
    cols = []
    for f in features:
        if f in ("yardline_100", "half_seconds_remaining", "goal_to_go", "posteam_timeouts_remaining",
                 "defteam_timeouts_remaining", "posteam_is_home"):
            v = num(f)
        elif f == "log_ydstogo":
            yd = num("ydstogo")
            if (yd <= 0).any():
                raise ValueError("ydstogo deve ser > 0")
            v = np.log(yd)
        elif f == "is_overtime":
            v = (num("half") == 3).astype("float64")
        elif f == "is_dome":
            v = df["roof"].isin(DOME_ROOFS).to_numpy().astype("float64")
        elif f == "t_x_yardline_100":
            v = num("half_seconds_remaining") * num("yardline_100")
        elif f == "relu_t_300_x_yardline_100":
            v = np.maximum(300.0 - num("half_seconds_remaining"), 0.0) * num("yardline_100")
        elif (m := _RE_DOWN.match(f)):
            v = (num("down") == int(m.group(1))).astype("float64")
        elif (m := _RE_DOWN_X.match(f)):
            v = (num("down") == int(m.group(1))).astype("float64") * num("yardline_100")
        elif (m := _RE_RELU_YL.match(f)):
            v = np.maximum(num("yardline_100") - int(m.group(1)), 0.0)
        elif (m := _RE_RELU_T.match(f)):
            v = np.maximum(int(m.group(1)) - num("half_seconds_remaining"), 0.0)
        else:
            raise ValueError(f"feature desconhecida: {f!r}")
        cols.append(v)
    return np.column_stack(cols) if cols else np.empty((len(df), 0))


def probs_from_params(params: dict, df: pd.DataFrame) -> np.ndarray:
    """Probabilidades n×7 (ordem de `params["classes"]`), softmax estável; usada pelo treino e pelo pyfunc."""
    X = feature_matrix(df, params["features"])
    X = (X - np.asarray(params["mean"], dtype="float64")) / np.asarray(params["scale"], dtype="float64")
    z = X @ np.asarray(params["coef"], dtype="float64").T + np.asarray(params["intercept"], dtype="float64")
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def expected_points(P: np.ndarray, points=POINTS) -> np.ndarray:
    return np.asarray(P, dtype="float64") @ np.asarray(points, dtype="float64")


def predict_frame(params: dict, df: pd.DataFrame) -> pd.DataFrame:
    P = probs_from_params(params, df)
    out = pd.DataFrame(P, columns=[f"p_{c}" for c in params["classes"]], index=df.index)
    out["ep"] = expected_points(P, params["points"])
    return out


class EPModel(PythonModel):
    def load_context(self, context):
        path = Path(context.artifacts["params_json"])
        expected = Path(context.artifacts["params_sha256"]).read_text().strip()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"params.json adulterado: sha256 {actual} difere do registrado {expected}")
        params = json.loads(path.read_text())
        if params.get("format") != FORMAT or params.get("classes") != CLASSES:
            raise ValueError(f"params.json inesperado (format={params.get('format')!r})")
        self.params = params

    def predict(self, context, model_input: TypeFromExample, params=None):
        return predict_frame(self.params, pd.DataFrame(model_input))


set_model(EPModel())
