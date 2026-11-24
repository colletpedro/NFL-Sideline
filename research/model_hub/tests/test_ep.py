"""H4 - Expected Points: receita de features única, ordem das classes, baselines, referência, registro."""
import json

import mlflow
import numpy as np
import pandas as pd
import pytest
from mlflow import MlflowClient

import backtest as B
import cli
import hubtrack
import register as R
from models import ep

pf = ep.pf
CLASSES = list(ep.CLASSES)


def synth_ep(n_per_season=2500, seasons=range(2011, 2018), seed=3):
    """Jogadas sintéticas com as colunas brutas reais; alvo gerado por um modelo multinomial conhecido."""
    rng = np.random.default_rng(seed)
    parts = []
    for s in seasons:
        n = n_per_season
        yl = rng.integers(1, 100, n).astype(float)
        down = rng.integers(1, 5, n)
        hsr = rng.uniform(0, 1800, n)
        df = pd.DataFrame({
            "game_id": [f"{s}_{i % 200}" for i in range(n)], "play_id": np.arange(n), "season": s,
            "week": rng.integers(1, 18, n), "season_type": "REG", "yardline_100": yl, "down": down,
            "ydstogo": rng.integers(1, 16, n), "half_seconds_remaining": hsr,
            "posteam_timeouts_remaining": rng.integers(0, 4, n), "defteam_timeouts_remaining": rng.integers(0, 4, n),
            "posteam_is_home": rng.random(n) < 0.5, "half": rng.choice([1, 2, 3], n, p=[0.48, 0.48, 0.04]),
            "roof": rng.choice(["outdoors", "dome", "closed", "open"], n)})
        df["goal_to_go"] = ((yl <= 10) & (rng.random(n) < 0.8)).astype(int)
        z = np.column_stack([
            1.5 - 0.03 * yl, 0.6 - 0.02 * yl + 0.3 * (down == 4), -4.0 + 0 * yl, 0.5 + 0.02 * yl - 0.5 * (down == 4),
            0.2 + 0.01 * yl, -4.2 + 0 * yl, 0.8 + 0.0 * yl - 0.0004 * hsr])
        P = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
        idx = (rng.random(n)[:, None] > np.cumsum(P, axis=1)).sum(axis=1).clip(0, 6)
        df["next_score_type"] = np.array(CLASSES)[idx]
        df["next_score_points"] = np.array(pf.POINTS)[idx]
        for c, col in enumerate(ep.NFLVERSE_COLUMNS):
            # "oráculo" que vaza o alvo: claramente melhor que qualquer candidato; NÃO soma 1 (a referência renormaliza)
            df[col] = (0.7 * (idx == c) + 0.3 * P[:, c]) * 0.5
        df["ep"] = P @ np.array(pf.POINTS)
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


@pytest.fixture(scope="module")
def data():
    return synth_ep()


# ------------------------------------------------------------------ receita de features

def test_recipe_values_by_hand():
    df = pd.DataFrame({"yardline_100": [25.0], "down": [3], "ydstogo": [8], "goal_to_go": [0],
                       "half_seconds_remaining": [100.0], "posteam_timeouts_remaining": [2],
                       "defteam_timeouts_remaining": [1], "posteam_is_home": [True], "half": [3], "roof": ["closed"]})
    names = ["yardline_100", "down_2", "down_3", "down_4", "log_ydstogo", "is_overtime", "is_dome", "posteam_is_home",
             "relu_yl_k10", "relu_yl_k30", "relu_t_120", "relu_t_300", "down3_x_yardline_100", "down2_x_yardline_100",
             "t_x_yardline_100", "relu_t_300_x_yardline_100"]
    got = dict(zip(names, pf.feature_matrix(df, names)[0]))
    assert got == pytest.approx({
        "yardline_100": 25, "down_2": 0, "down_3": 1, "down_4": 0, "log_ydstogo": np.log(8), "is_overtime": 1,
        "is_dome": 1, "posteam_is_home": 1, "relu_yl_k10": 15, "relu_yl_k30": 0, "relu_t_120": 20, "relu_t_300": 200,
        "down3_x_yardline_100": 25, "down2_x_yardline_100": 0, "t_x_yardline_100": 2500,
        "relu_t_300_x_yardline_100": 5000})


def test_unknown_feature_and_nulls_are_explicit(data):
    with pytest.raises(ValueError, match="desconhecida"):
        pf.feature_matrix(data.head(3), ["nao_existe"])
    bad = data.head(4).copy()
    bad.loc[1, "posteam_timeouts_remaining"] = np.nan
    with pytest.raises(ValueError, match="nulos"):
        pf.feature_matrix(bad, ["posteam_timeouts_remaining"])
    assert pf.usable_mask(bad).tolist() == [True, False, True, True]
    assert not pf.usable_mask(data.head(2).assign(ydstogo=0)).any()


def test_hinge_feature_set_shape():
    assert len(ep.HINGE) == len(set(ep.HINGE))
    assert {f"relu_yl_k{k}" for k in range(10, 100, 10)} <= set(ep.HINGE)
    assert set(ep.STATE) < set(ep.HINGE) and set(ep.BASIC) < set(ep.STATE)


# ------------------------------------------------------------------ modelos

@pytest.mark.parametrize("name", list(ep.FEATURE_SETS))
def test_logit_train_matches_pyfunc_code_and_class_order(data, name):
    train = data[data.season < 2017]
    test = data[data.season == 2017]
    model = ep.LogitEP(name, ep.FEATURE_SETS[name])
    fitted = model.fit(train)
    js = fitted.to_json()
    assert js["classes"] == CLASSES and js["format"] == pf.FORMAT and js["n_iter"] < js["max_iter"]
    P = fitted.predict(test)
    assert P.shape == (len(test), 7) and np.allclose(P.sum(axis=1), 1.0)
    out = pf.predict_frame(json.loads(json.dumps(js)), test)  # após viagem por JSON
    assert list(out.columns) == pf.PROB_COLUMNS + ["ep"]
    np.testing.assert_allclose(out[pf.PROB_COLUMNS].to_numpy(), P, atol=1e-12)
    np.testing.assert_allclose(out["ep"], P @ np.array(pf.POINTS), atol=1e-12)
    # o ajuste é bom o bastante: bate a frequência global no teste
    y = np.array([CLASSES.index(c) for c in test["next_score_type"]])
    base = ep.FreqBaseline().fit(train).predict(test)
    import metrics as M
    assert M.log_loss_multiclass(y, P) < M.log_loss_multiclass(y, base)


@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
def test_logit_refuses_to_run_without_convergence(data):
    with pytest.raises(ep.EPError, match="convergiu"):
        ep.LogitEP("x", ep.BASIC, max_iter=1).fit(data[data.season < 2017])


def test_logit_requires_all_classes(data):
    only = data[data.next_score_type.isin(["TD", "FG"])]
    with pytest.raises(ep.EPError, match="7 classes"):
        ep.LogitEP("x", ep.BASIC).fit(only)


def test_freq_field_down_fallbacks():
    # faixa 5 (yl 50..59): 300 jogadas na descida 1, 10 na descida 2; faixa 9: 5 jogadas no total
    rows = ([(55.0, 1, "TD")] * 150 + [(55.0, 1, "NO_SCORE")] * 150 + [(55.0, 2, "FG")] * 10
            + [(95.0, 1, "SAFETY")] * 5)
    train = pd.DataFrame(rows, columns=["yardline_100", "down", "next_score_type"])
    fitted = ep.FreqFieldDownBaseline(min_cell=200).fit(train)
    probe = pd.DataFrame({"yardline_100": [55.0, 55.0, 95.0, 5.0], "down": [1, 2, 1, 4]})
    P = fitted.predict(probe)
    assert np.allclose(P.sum(axis=1), 1) and (P > 0).all()
    td, fg, no = CLASSES.index("TD"), CLASSES.index("FG"), CLASSES.index("NO_SCORE")
    n_cell = 300
    assert P[0, td] == pytest.approx((150 + 1) / (n_cell + 7))                 # célula própria
    assert P[1, fg] == pytest.approx((10 + 1) / (310 + 7))                      # fallback para a faixa 5 (310 jogadas)
    assert P[1, td] == pytest.approx((150 + 1) / (310 + 7))
    assert P[2, no] == pytest.approx((150 + 1) / (315 + 7))                     # faixa 9 pequena: global
    assert P[3, no] == pytest.approx((150 + 1) / (315 + 7))                     # faixa 0 vazia: global
    js = fitted.to_json()
    assert js["cells_fallback_band"] >= 1 and js["cells_fallback_global"] >= 1


def test_nflverse_reference_renormalizes(data):
    ref = ep.NflverseReference().fit(data)
    P = ref.predict(data.head(50))
    assert np.allclose(P.sum(axis=1), 1.0)
    assert np.allclose(P, data.head(50)[ep.NFLVERSE_COLUMNS].to_numpy() / data.head(50)[ep.NFLVERSE_COLUMNS].sum(axis=1).to_numpy()[:, None])
    with pytest.raises(ep.EPError):
        ep.NflverseReference().fit(data).predict(data.head(3).assign(td_prob=np.nan))


# ------------------------------------------------------------------ backtest, referência fora da regra, registro

@pytest.fixture
def bt(data):
    splits = B.walk_forward_seasons([2016, 2017], 2011)
    res = ep.run(data, "synth-build", splits=splits)
    return data, res


def test_backtest_selects_candidate_and_reference_is_outside_the_rule(bt):
    data, res = bt
    assert res.roles["nflverse"] == "reference" and res.roles["freq"] == "baseline"
    assert set(res.roles) == {"freq", "freq_field_down", "nflverse", "logit_basic", "logit_state", "logit_hinge"}
    assert res.selected_model in {"logit_basic", "logit_state", "logit_hinge"} and res.beats_baselines
    best = min(res.pooled[m]["log_loss"] for m in ("logit_basic", "logit_state", "logit_hinge"))
    assert res.pooled[res.selected_model]["log_loss"] == best
    # a referência é melhor que todos (sintético: usa os dados verdadeiros) e MESMO ASSIM não é selecionada
    assert res.pooled["nflverse"]["log_loss"] < best
    for m in res.pooled:
        assert {"log_loss", "brier", "ep_mae", "ep_rmse", "n"} <= set(res.pooled[m])
    run = MlflowClient().get_run(res.parent_run_id)
    assert "nflverse" in run.data.params["references"]
    art = Path_artifact(res.parent_run_id, f"extras/{res.selected_model}/ep_calibration.json")
    assert len(art["rows"]) == 10 and sum(r["n"] for r in art["rows"]) == res.pooled[res.selected_model]["n"]


def Path_artifact(run_id, rel):
    from pathlib import Path
    return json.loads(Path(MlflowClient().download_artifacts(run_id, rel)).read_text())


def test_ep_metrics_by_hand():
    test = pd.DataFrame({"next_score_points": [7.0, -3.0]})
    P = np.zeros((2, 7)); P[0, 0] = 1.0; P[1, 6] = 1.0     # EP = 7 e 0
    assert ep.ep_mae(test, P) == pytest.approx(1.5) and ep.ep_rmse(test, P) == pytest.approx(np.sqrt(4.5))


def test_register_load_champion_and_predict_equal(bt, tmp_path):
    data, res = bt
    out = ep.register(data, "synth-build", res.parent_run_id)
    assert out["name"] == "hub-ep" and out["version"] == "1"
    model = mlflow.pyfunc.load_model("models:/hub-ep@champion")
    params = ep.fit_selected(data, res.selected_model)
    sample = data.sample(500, random_state=1)
    got = model.predict(pf.raw_frame(sample))
    want = pf.predict_frame(params, sample)
    assert list(got.columns) == pf.PROB_COLUMNS + ["ep"]
    np.testing.assert_allclose(got.to_numpy(), want.to_numpy(), atol=1e-12)
    assert np.allclose(got[pf.PROB_COLUMNS].sum(axis=1), 1.0)
    # o schema do MLflow é double: entradas inteiras precisam passar por `raw_frame` (documentado)
    got2 = model.predict(pf.raw_frame(sample[pf.RAW_COLUMNS].astype({"down": int, "ydstogo": int, "half": int})))
    np.testing.assert_allclose(got2.to_numpy(), want.to_numpy(), atol=1e-12)
    # previsão em lote para o parquet
    path = ep.predict_all(data.head(1000), "synth-build", tmp_path / "home", chunk=400)
    df = pd.read_parquet(path)
    assert list(df.columns) == ["game_id", "play_id", *pf.PROB_COLUMNS, "ep", "model_version"]
    assert len(df) == 1000 and (df.model_version == "hub-ep@1").all()
    np.testing.assert_allclose(df[pf.PROB_COLUMNS].to_numpy(),
                               pf.predict_frame(params, data.head(1000))[pf.PROB_COLUMNS].to_numpy(), atol=1e-12)
    assert path == tmp_path / "home" / "predictions" / "ep" / "synth-build" / "plays_ep.parquet"


def test_register_refuses_stale_data_id_and_failing_backtest(bt):
    data, res = bt
    with pytest.raises(ep.EPError, match="data_id"):
        ep.register(data, "outro-build", res.parent_run_id)


def test_card_has_reference_warning_and_calibration(bt):
    data, res = bt
    ep.register(data, "synth-build", res.parent_run_id)
    info = {"build_id": "synth-build", "ep_eligible": len(data), "used": len(data), "dropped_invalid_rows": 0,
            "dropped_by_reason": {"null_raw_features": 0, "null_target": 0, "invalid_nflverse_probs": 0}}
    text = ep.card_text(res.parent_run_id, info)
    assert "OTIMISTA" in text and "reference (fora da regra)" in text
    assert "ep_mae" in text and "Calibração do EP por decis" in text and "hub-ep@champion" in text
    assert "`nflverse`" in text and "| s2016 |" in text
    # L-1/L-4: limitações de deriva temporal, vazamento possível da referência e descontinuidade goal-to-go
    assert "Deriva temporal" in text and "~1,58 (2011)" in text and "~2,10 (2026)" in text and "recência" in text
    assert "versão do modelo nflverse não está fixada" in text and "1ª&gol na 10 vs 1ª&10 na 11" in text
    assert "dropped_null" not in text and "nulo em coluna bruta: 0" in text


def test_splits_are_walk_forward(data):
    sp = ep.splits_for(pd.DataFrame({"season": [2026]}))
    assert [s.test for s in sp] == [(s,) for s in range(2018, 2027)]
    assert all(s.train_until == (s.test[0] - 1, B.LAST_WEEK) and s.first_train_season == 2011 for s in sp)


def test_cli_registers_model_commands():
    for cmd in ("backtest", "register", "predict", "card"):
        assert cmd in cli.COMMANDS
    with pytest.raises(SystemExit) as e:
        cli.main(["card", "ep", "--help"])
    assert e.value.code == 0


@pytest.mark.real_data
def test_real_data_counts_consistent():
    try:
        df, info = ep.load_data()
    except Exception as exc:  # sem build real
        pytest.skip(f"sem dados reais: {exc}")
    assert info["used"] == len(df) and info["used"] + info["dropped_invalid_rows"] == info["ep_eligible"]
    assert sum(info["dropped_by_reason"].values()) == info["dropped_invalid_rows"]
    assert set(df["next_score_type"].unique()) == set(CLASSES)


# ------------------------------------------------------------------ L-5/L-6: exclusões honestas e contadas
def _fake_store(monkeypatch, data):
    import features
    import polars as pl
    plays = pl.from_pandas(data.assign(ep_eligible=True))
    monkeypatch.setattr(features, "resolve_build", lambda b, h: __import__("pathlib").Path("/x/fake-build"))
    monkeypatch.setattr(features, "load_tables", lambda b, h: {"plays": plays})


def test_load_data_drops_invalid_nflverse_rows_for_all_models_l5(data, monkeypatch, tmp_path):
    d = data.head(60).copy().reset_index(drop=True)
    d.loc[3, ep.NFLVERSE_COLUMNS] = 0.0                      # todas zero
    d.loc[4, ep.NFLVERSE_COLUMNS] = np.nan                   # todas nulas
    d.loc[5, "yardline_100"] = np.nan                        # nulo em coluna bruta (motivo mais antigo)
    d.loc[5, ep.NFLVERSE_COLUMNS] = 0.0                      # também zero: conta só uma vez (atribuição exclusiva)
    d.loc[6, "next_score_type"] = None
    _fake_store(monkeypatch, d)
    df, info = ep.load_data("b", tmp_path)
    assert info["dropped_by_reason"] == {
        "null_raw_features": 1, "null_target": 1, "invalid_nflverse_probs": 2}
    assert info["ep_eligible"] == 60 and info["used"] == 56 == len(df) and info["dropped_invalid_rows"] == 4
    assert ep.nflverse_valid_mask(df).all() and "dropped_null_features" not in info
    # a referência não aborta no conjunto filtrado e todos os modelos veem as mesmas 56 linhas
    ep.NflverseReference().fit(df).predict(df)
    assert not ep.nflverse_valid_mask(d.iloc[[3, 4]]).any()
    assert ep.nflverse_valid_mask(d.iloc[[0, 1]]).all()


def test_pyfunc_integer_columns_need_raw_frame_l6(bt):
    """O schema do MLflow é `double`: int64/bool cru é recusado pela camada do MLflow ANTES do pyfunc (limite do
    MLflow, documentado no README); `raw_frame` converte e funciona."""
    data, res = bt
    ep.register(data, "synth-build", res.parent_run_id)
    model = mlflow.pyfunc.load_model("models:/hub-ep@champion")
    s = data.head(5)[pf.RAW_COLUMNS].astype({"down": "int64", "ydstogo": "int64", "half": "int64"})
    with pytest.raises(Exception, match="enforce schema"):
        model.predict(s)
    out = model.predict(pf.raw_frame(s))
    assert len(out) == 5 and np.allclose(out[pf.PROB_COLUMNS].sum(axis=1), 1.0)


# ------------------------------------------------------------------ L-3: previsão em lote e cartão amarrados ao build
def test_predict_meta_in_sample_follows_training_data_l3(bt, tmp_path):
    data, res = bt
    out = ep.register(data, "synth-build", res.parent_run_id)
    home = tmp_path / "home"
    p = ep.predict_all(data, "synth-build", home, chunk=3000)
    meta = json.loads((p.parent / "meta.json").read_text())
    assert meta["in_sample"] is True and meta["champion_version"] == out["version"] == "1"
    assert meta["source_run_id"] == res.parent_run_id and meta["build_id"] == "synth-build"
    assert meta["predicted_data_sha256"] == meta["train_data_sha256"] and "in_sample_note" not in meta
    # dados diferentes dos do ajuste: não se pode afirmar dentro da amostra
    p2 = ep.predict_all(data.iloc[:-1], "synth-build-2", home)
    m2 = json.loads((p2.parent / "meta.json").read_text())
    assert m2["in_sample"] is False and m2["predicted_data_sha256"] != m2["train_data_sha256"] and "in_sample_note" in m2


def test_card_requires_parent_from_current_build_l3(bt, tmp_path, monkeypatch):
    data, res = bt  # pai com data_id "synth-build"
    _fake_store(monkeypatch, data.head(50))
    monkeypatch.setattr(ep, "load_data", lambda b, h: (data.head(50), {
        "build_id": "outro-build", "ep_eligible": 50, "used": 50, "dropped_invalid_rows": 0,
        "dropped_by_reason": {}}))
    out = tmp_path / "card.md"
    args = type("A", (), {"build": None, "home": str(tmp_path), "out": str(out), "run_id": None})()
    with pytest.raises(ep.EPError, match="rode `backtest ep`"):
        ep.cmd_card(args)
    assert not out.exists()
    args.run_id = res.parent_run_id  # explícito: aceito
    ep.cmd_card(args)
    assert "Cartão do modelo `ep`" in out.read_text()
    monkeypatch.setattr(ep, "load_data", lambda b, h: (data.head(50), {
        "build_id": "synth-build", "ep_eligible": 50, "used": 50, "dropped_invalid_rows": 0, "dropped_by_reason": {}}))
    args.run_id = None
    ep.cmd_card(args)
