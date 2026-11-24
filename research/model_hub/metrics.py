"""Métricas de avaliação em numpy puro (testadas contra scikit-learn em tests/test_metrics.py).

Convenções:
- Binário: `y` em {0, 1}, `p` = probabilidade da classe 1 (vetor de n).
- Multiclasse: `y` = índices inteiros 0..k-1, `P` = matriz n×k (cada linha soma 1).
- Regressão: `y` e `pred` reais.

`EPS` é o recorte das probabilidades no log-loss: `clip(p, EPS, 1 - EPS)`, sem renormalizar depois. É uma
convenção PRÓPRIA do hub: o scikit-learn 1.7 não aceita o parâmetro `eps` em `log_loss` (usa o eps do dtype,
~2.2e-16). Os valores coincidem fora das extremidades (p < 1e-15); aí diferem de propósito, e o recorte aqui é
reproduzível por quem lê o código.

ECE: faixas `(a, b]` com bordas `linspace(0, 1, bins + 1)` (p == 0 na primeira faixa), a mesma regra de
`sklearn.calibration.calibration_curve(strategy="uniform")`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

EPS = 1e-15


class UndefinedMetric(ValueError):
    """Métrica indefinida para estes dados (p. ex. AUC com uma só classe no alvo); o backtest a omite com aviso."""


def _f(x) -> np.ndarray:
    return np.asarray(x, dtype="float64")


def _check_same_length(y, p) -> None:
    if len(y) != len(p):
        raise ValueError(f"y e previsão com tamanhos diferentes: {len(y)} vs {len(p)}")
    if len(y) == 0:
        raise ValueError("métrica sobre conjunto vazio")


def _check_binary(y) -> np.ndarray:
    y = np.asarray(y)
    if not np.isin(y, (0, 1)).all():
        raise ValueError("alvo binário deve conter só 0 e 1")
    return y.astype("float64")


def _check_multiclass(y, P) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y)
    P = _f(P)
    if P.ndim != 2:
        raise ValueError("previsão multiclasse deve ser n×k")
    if y.size and (y.min() < 0 or y.max() >= P.shape[1] or not np.issubdtype(y.dtype, np.integer)):
        raise ValueError("alvo multiclasse deve ser índice inteiro em 0..k-1")
    return y.astype("int64"), P


def log_loss_binary(y, p) -> float:
    y = _check_binary(y)
    p = _f(p)
    _check_same_length(y, p)
    pos, neg = np.clip(p, EPS, 1 - EPS), np.clip(1 - p, EPS, 1 - EPS)  # recorte de cada classe separadamente
    return float(-np.mean(y * np.log(pos) + (1 - y) * np.log(neg)))


def log_loss_multiclass(y, P) -> float:
    y, P = _check_multiclass(y, P)
    _check_same_length(y, P)
    P = np.clip(P, EPS, 1 - EPS)
    return float(-np.mean(np.log(P[np.arange(len(y)), y])))


def brier_binary(y, p) -> float:
    y = _check_binary(y)
    p = _f(p)
    _check_same_length(y, p)
    return float(np.mean((p - y) ** 2))


def brier_multiclass(y, P) -> float:
    """Brier multiclasse: média sobre jogadas da soma dos quadrados dos erros em todas as classes (0..2)."""
    y, P = _check_multiclass(y, P)
    _check_same_length(y, P)
    onehot = np.zeros_like(P)
    onehot[np.arange(len(y)), y] = 1.0
    return float(np.mean(np.sum((P - onehot) ** 2, axis=1)))


def ece_binary(y, p, bins: int = 10) -> float:
    """ECE binário com `bins` faixas iguais `(a, b]` em [0, 1]: soma_b (n_b/n) * |média(y) - média(p)| na faixa b.

    Uma probabilidade exatamente na borda vai para a faixa de BAIXO (p = 0.1 na faixa 0), p == 0 cai na primeira e
    p == 1 na última (`np.searchsorted(bordas_internas, p, side="left")`, como `calibration_curve` uniform)."""
    y = _check_binary(y)
    p = _f(p)
    _check_same_length(y, p)
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.searchsorted(edges[1:-1], p, side="left")
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.sum() / len(y) * abs(y[m].mean() - p[m].mean())
    return float(total)


def auc(y, p) -> float:
    """AUC por postos (Mann-Whitney) com empates tratados pela média dos postos. Exige as duas classes."""
    y = _check_binary(y)
    p = _f(p)
    _check_same_length(y, p)
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        raise UndefinedMetric("AUC exige as duas classes no alvo")
    _, inv, counts = np.unique(p, return_inverse=True, return_counts=True)
    ends = np.cumsum(counts)
    mean_rank = ends - (counts - 1) / 2.0  # posto médio (base 1) de cada valor único
    ranks = mean_rank[inv]
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def mae(y, pred) -> float:
    y, pred = _f(y), _f(pred)
    _check_same_length(y, pred)
    return float(np.mean(np.abs(y - pred)))


def rmse(y, pred) -> float:
    y, pred = _f(y), _f(pred)
    _check_same_length(y, pred)
    return float(np.sqrt(np.mean((y - pred) ** 2)))


def calibration_table(pred, actual, bins: int = 10, strategy: str = "quantile") -> pd.DataFrame:
    """Tabela de calibração para valores contínuos (p. ex. EP previsto vs pontos reais).

    `strategy="quantile"`: faixas com ~mesmo número de jogadas (bordas = quantis de `pred`, repetidas são
    fundidas); `"uniform"`: faixas de mesma largura entre min e max de `pred`. Colunas: bin, lo, hi, n,
    pred_mean, actual_mean, diff (= actual_mean - pred_mean)."""
    pred, actual = _f(pred), _f(actual)
    _check_same_length(pred, actual)
    if strategy == "quantile":
        edges = np.unique(np.quantile(pred, np.linspace(0, 1, bins + 1)))
    elif strategy == "uniform":
        edges = np.linspace(pred.min(), pred.max(), bins + 1)
    else:
        raise ValueError("strategy deve ser 'quantile' ou 'uniform'")
    if len(edges) < 2:
        edges = np.array([pred.min(), pred.min()])
    idx = np.clip(np.searchsorted(edges[1:-1], pred, side="right"), 0, max(len(edges) - 2, 0))
    rows = []
    for b in range(max(len(edges) - 1, 1)):
        m = idx == b
        if not m.any():
            continue
        pm, am = float(pred[m].mean()), float(actual[m].mean())
        rows.append({"bin": len(rows), "lo": float(edges[b]), "hi": float(edges[min(b + 1, len(edges) - 1)]),
                     "n": int(m.sum()), "pred_mean": pm, "actual_mean": am, "diff": am - pm})
    return pd.DataFrame(rows, columns=["bin", "lo", "hi", "n", "pred_mean", "actual_mean", "diff"])


@dataclass(frozen=True)
class Metric:
    """Métrica com nome canônico e direção ("min": menor é melhor; "max": maior é melhor)."""
    name: str
    direction: str
    kinds: dict  # kind -> função(y, pred)


METRICS: dict[str, Metric] = {
    "log_loss": Metric("log_loss", "min", {"binary": log_loss_binary, "multiclass": log_loss_multiclass}),
    "brier": Metric("brier", "min", {"binary": brier_binary, "multiclass": brier_multiclass}),
    "ece": Metric("ece", "min", {"binary": ece_binary}),
    "auc": Metric("auc", "max", {"binary": auc}),
    "mae": Metric("mae", "min", {"regression": mae}),
    "rmse": Metric("rmse", "min", {"regression": rmse}),
}


def direction(name: str) -> str:
    return _metric(name).direction


def is_better(name: str, a: float, b: float) -> bool:
    """`a` é estritamente melhor que `b` segundo a direção da métrica."""
    return a < b if direction(name) == "min" else a > b


def _metric(name: str) -> Metric:
    if name not in METRICS:
        raise KeyError(f"métrica desconhecida: {name!r}; conhecidas: {sorted(METRICS)}")
    return METRICS[name]


def compute(name: str, kind: str, y, pred) -> float:
    """Calcula a métrica `name` para uma tarefa do tipo `kind` (binary | multiclass | regression)."""
    m = _metric(name)
    if kind not in m.kinds:
        raise ValueError(f"métrica {name!r} não se aplica a tarefas {kind!r}")
    return m.kinds[kind](y, pred)


def applicable(name: str, kind: str) -> bool:
    return name in METRICS and kind in METRICS[name].kinds
