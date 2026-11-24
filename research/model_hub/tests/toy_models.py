"""Dados sintéticos e modelos-brinquedo compartilhados pelos testes do harness (H3)."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

CODE = Path(__file__).resolve().parent.parent / "model_code" / "json_linear_pyfunc.py"
_spec = importlib.util.spec_from_file_location("json_linear_pyfunc", CODE)
json_linear = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(json_linear)

FEATURES = ["x1", "x2"]


def synth(n_per_week=12, seasons=(2019, 2020, 2021, 2022), weeks=range(1, 9), seed=7, kind="multiclass"):
    """Linhas com season, week, kickoff_utc, x1, x2 e alvos `y3` (3 classes: 'a','b','c'), `yb` (0/1), `yr`."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in seasons:
        for w in weeks:
            kick = pd.Timestamp(f"{s}-09-01", tz="UTC") + pd.Timedelta(days=7 * (w - 1))
            for i in range(n_per_week):
                rows.append((s, w, kick + pd.Timedelta(hours=i), *rng.normal(size=2)))
    df = pd.DataFrame(rows, columns=["season", "week", "kickoff_utc", "x1", "x2"])
    z = np.column_stack([1.5 * df.x1, -1.5 * df.x2, 0.3 + 0 * df.x1])
    p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
    u = rng.random(len(df))[:, None]
    df["y3"] = np.array(["a", "b", "c"])[(u > np.cumsum(p, axis=1)).sum(axis=1).clip(0, 2)]
    pb = 1 / (1 + np.exp(-(1.2 * df.x1 - 0.8 * df.x2)))
    df["yb"] = (rng.random(len(df)) < pb).astype(int)
    df["yr"] = 2.0 * df.x1 - df.x2 + rng.normal(scale=0.5, size=len(df))
    return df


class _Fitted:
    def __init__(self, fn, js):
        self._fn, self._js = fn, js

    def predict(self, df):
        return self._fn(df)

    def to_json(self):
        return self._js


class FreqModel:
    """Baseline: frequência de cada classe no treino (multiclasse) ou taxa (binário)."""

    def __init__(self, target, classes=None, name="freq"):
        self.target, self.classes, self.name = target, classes, name

    def params(self):
        return {"target": self.target}

    def columns(self):
        return [self.target]

    def fit(self, train):
        if self.classes:
            p = np.array([(train[self.target] == c).mean() for c in self.classes])
            return _Fitted(lambda df: np.tile(p, (len(df), 1)), {"probs": p.tolist()})
        r = float(train[self.target].mean())
        return _Fitted(lambda df: np.full(len(df), r), {"rate": r})


class MeanModel:
    """Baseline de regressão: média do treino."""
    name = "mean"

    def params(self):
        return {}

    def columns(self):
        return ["yr"]

    def fit(self, train):
        m = float(train["yr"].mean())
        return _Fitted(lambda df: np.full(len(df), m), {"mean": m})


class LogitModel:
    """Candidato: logística sklearn, parâmetros exportados no formato `hub-json-linear-v1`."""

    def __init__(self, target, classes=None, C=1.0, name="logit"):
        self.target, self.classes, self.C, self.name = target, classes, C, name

    def params(self):
        return {"target": self.target, "C": self.C}

    def columns(self):
        return [*FEATURES, self.target]

    def fit(self, train):
        clf = LogisticRegression(C=self.C, max_iter=500).fit(train[FEATURES], train[self.target])
        kind = "multiclass" if self.classes else "binary"
        js = {"format": "hub-json-linear-v1", "kind": kind, "features": FEATURES,
              "classes": [str(c) for c in clf.classes_], "intercept": clf.intercept_.tolist(),
              "coef": clf.coef_.tolist()}
        return _Fitted(lambda df: json_linear.linear_predict(js, df[FEATURES].to_numpy()), js)
