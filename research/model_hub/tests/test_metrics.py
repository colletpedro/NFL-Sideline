import numpy as np
import pandas as pd
import pytest
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, mean_squared_error, roc_auc_score

import metrics as M

rng = np.random.default_rng(3)


def _bin(n=500):
    p = rng.random(n)
    return (rng.random(n) < p).astype(int), p


def test_log_loss_binary_matches_sklearn_and_clips():
    y, p = _bin()
    assert M.log_loss_binary(y, p) == pytest.approx(log_loss(y, p), rel=1e-12)
    # probabilidade exata 0/1 errada não explode: recorte em EPS
    assert M.log_loss_binary([1, 0], [0.0, 1.0]) == pytest.approx(-np.log(M.EPS))


def test_log_loss_multiclass_matches_sklearn():
    P = rng.dirichlet(np.ones(4), size=400)
    y = rng.integers(0, 4, 400)
    assert M.log_loss_multiclass(y, P) == pytest.approx(log_loss(y, P, labels=range(4)), rel=1e-12)


def test_brier():
    y, p = _bin()
    assert M.brier_binary(y, p) == pytest.approx(brier_score_loss(y, p), rel=1e-12)
    P = rng.dirichlet(np.ones(3), size=300)
    yy = rng.integers(0, 3, 300)
    manual = np.mean(((P - np.eye(3)[yy]) ** 2).sum(axis=1))
    assert M.brier_multiclass(yy, P) == pytest.approx(manual)
    # com k=2 é o dobro do Brier binário
    p2 = rng.random(100)
    y2 = (rng.random(100) < p2).astype(int)
    assert M.brier_multiclass(y2, np.column_stack([1 - p2, p2])) == pytest.approx(2 * brier_score_loss(y2, p2))


def test_ece_matches_calibration_curve_weights():
    y, p = _bin(1000)
    p[:5] = 1.0
    frac, mean_p = calibration_curve(y, p, n_bins=10, strategy="uniform")
    idx = np.searchsorted(np.linspace(0, 1, 11)[1:-1], p, side="left")
    counts = np.array([c for c in np.bincount(idx, minlength=10) if c > 0])
    expected = float(np.sum(counts / len(y) * np.abs(frac - mean_p)))
    assert M.ece_binary(y, p, bins=10) == pytest.approx(expected, rel=1e-10)
    assert M.ece_binary([0, 1, 1, 0], [0.0, 1.0, 1.0, 0.0]) == 0.0


def test_auc_matches_sklearn_with_ties():
    y, p = _bin()
    assert M.auc(y, p) == pytest.approx(roc_auc_score(y, p), rel=1e-12)
    pt = np.round(p, 1)  # muitos empates
    assert M.auc(y, pt) == pytest.approx(roc_auc_score(y, pt), rel=1e-12)
    with pytest.raises(ValueError):
        M.auc([1, 1], [0.2, 0.3])


def test_mae_rmse():
    y, p = rng.normal(size=200), rng.normal(size=200)
    assert M.mae(y, p) == pytest.approx(mean_absolute_error(y, p))
    assert M.rmse(y, p) == pytest.approx(mean_squared_error(y, p) ** 0.5)


def test_calibration_table_quantile_and_uniform():
    pred = rng.normal(size=1000)
    actual = pred + rng.normal(scale=0.1, size=1000)
    t = M.calibration_table(pred, actual, bins=5)
    assert t.n.sum() == 1000 and len(t) == 5
    assert t.n.min() >= 190  # faixas de ~mesmo tamanho
    assert (t["diff"].abs() < 0.2).all()
    assert t.pred_mean.is_monotonic_increasing
    u = M.calibration_table(pred, actual, bins=4, strategy="uniform")
    assert u.n.sum() == 1000
    const = M.calibration_table([1.0, 1.0, 1.0], [0.0, 1.0, 2.0], bins=5)
    assert const.n.tolist() == [3] and const.actual_mean.iloc[0] == 1.0


def test_registry_directions_and_dispatch():
    assert M.direction("log_loss") == "min" and M.direction("auc") == "max"
    assert M.is_better("auc", 0.7, 0.6) and M.is_better("brier", 0.1, 0.2)
    assert M.compute("rmse", "regression", [0.0, 2.0], [1.0, 1.0]) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        M.compute("auc", "multiclass", [0], [[1.0]])
    with pytest.raises(KeyError):
        M.compute("nope", "binary", [0], [0.5])


def test_input_validation():
    with pytest.raises(ValueError):
        M.log_loss_binary([0, 2], [0.1, 0.2])
    with pytest.raises(ValueError):
        M.log_loss_multiclass([0, 3], np.full((2, 3), 1 / 3))
    with pytest.raises(ValueError):
        M.mae([1.0], [1.0, 2.0])
    with pytest.raises(ValueError):
        M.mae([], [])


def test_ece_bin_edges_follow_sklearn_right_closed_rule():
    # p exatamente nas bordas: a regra (a, b] manda a borda para a faixa de baixo (como calibration_curve)
    edges = np.linspace(0, 1, 11)
    p = np.concatenate([edges, edges, edges[1:-1], [0.25, 0.55]])
    y = (np.arange(len(p)) % 3 == 0).astype(int)
    frac, mean_p = calibration_curve(y, p, n_bins=10, strategy="uniform")
    ids = np.searchsorted(edges[1:-1], p, side="left")
    counts = np.array([c for c in np.bincount(ids, minlength=10) if c > 0])
    assert M.ece_binary(y, p, 10) == pytest.approx(float(np.sum(counts / len(p) * np.abs(frac - mean_p))), rel=1e-12)
    # à mão: p = 0.1 cai na faixa 0 junto de 0.05 (não na faixa 1 junto de 0.15)
    y2, p2 = [1, 0, 1, 0], [0.05, 0.1, 0.15, 0.15]
    manual = (2 / 4) * abs(0.5 - 0.075) + (2 / 4) * abs(0.5 - 0.15)
    assert M.ece_binary(y2, p2, 10) == pytest.approx(manual)
    assert M.ece_binary([0, 1], [0.0, 1.0]) == 0.0


def test_auc_single_class_raises_undefined_metric():
    with pytest.raises(M.UndefinedMetric):
        M.auc([1, 1, 1], [0.1, 0.2, 0.3])
