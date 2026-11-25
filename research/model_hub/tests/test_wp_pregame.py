"""H7 - WP pré-jogo: features pré-jogo sem vazamento, Elo online = elo_fit, fórmula do mercado, empates fora, campo
neutro, logística = pyfunc, backtest semanal, previsões fora da amostra e registro."""
import json
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import pytest
from mlflow import MlflowClient
from sklearn.linear_model import LogisticRegression

import backtest as B
import cli
from models import ratings as RT
from models import wp_pregame as W

pf = W.pf
TEAMS = [f"T{i}" for i in range(8)]
TRUE = dict(zip(TEAMS, [8.0, 5.0, 2.0, 0.5, -0.5, -2.0, -5.0, -8.0]))
HFA = 2.5


def american(imp: float) -> float:
    return float(np.round(-100 * imp / (1 - imp) if imp >= 0.5 else 100 * (1 - imp) / imp))


def synth_schedule(seasons=range(2011, 2019), weeks=8, noise=9.0, seed=5, pending_from=(2018, 7)):
    """Calendário de brinquedo: 8 times, 4 jogos por semana, mando 2,5, 1 jogo neutro por temporada, alguns empates, e
    jogos sem resultado a partir de `pending_from` (o último, semana 8, sem moneyline). Colunas como no feature store."""
    rng = np.random.default_rng(seed)
    rows = []
    t0 = pd.Timestamp("2011-09-10", tz="UTC")
    for s in seasons:
        for w in range(1, weeks + 1):
            order = rng.permutation(TEAMS)
            for g in range(4):
                h, a = order[2 * g], order[2 * g + 1]
                neutral = (w == 3 and g == 0)
                mu = (0 if neutral else HFA) + TRUE[h] - TRUE[a]
                margin = float(np.round(mu + rng.normal(0, noise)))
                if rng.random() < 0.02:
                    margin = 0.0
                pend = (s, w) >= pending_from
                p = 1 / (1 + np.exp(-mu / 6.5))
                ml_h, ml_a = american(min(p * 1.045, 0.99)), american(min((1 - p) * 1.045, 0.99))
                k = t0 + pd.Timedelta(days=365 * (s - 2011) + 7 * (w - 1), hours=2 * (g // 2))  # 2 jogos por horário
                row = {"game_id": f"{s}_{w:02d}_{a}_{h}", "season": s, "week": w, "kickoff_utc": k, "home_team": h,
                       "away_team": a, "result": np.nan if pend else margin, "completed": not pend, "neutral": bool(neutral),
                       "home_rest": int(rng.choice([6, 7, 7, 10])), "away_rest": int(rng.choice([6, 7, 7, 10])),
                       "div_game": int(rng.random() < 0.3), "home_moneyline": ml_h, "away_moneyline": ml_a}
                if (s, w) == (2018, 8):
                    row["home_moneyline"] = row["away_moneyline"] = np.nan
                for side, team in (("home", h), ("away", a)):
                    row[f"{side}_ewm4_off_epa"] = 0.02 * TRUE[team] + rng.normal(0, 0.02)
                    row[f"{side}_ewm4_def_epa"] = -0.02 * TRUE[team] + rng.normal(0, 0.02)
                    row[f"{side}_ewm4_point_diff"] = TRUE[team] + rng.normal(0, 2.0)
                rows.append(row)
    return pd.DataFrame(rows).sort_values(["kickoff_utc", "game_id"]).reset_index(drop=True)


@pytest.fixture(scope="module")
def synth():
    allg, info = W.with_features(synth_schedule(), "synth-build")
    return allg, W.modeled(allg), info


# ------------------------------------------------------------------ constantes e Elo online

def test_hyperparameters_are_the_ratings_ones_and_asof_features_match():
    assert W.ELO == RT.ELO and W.RT.FIRST_TRAIN_SEASON == 2011
    assert tuple(pf.ASOF_FEATURES) == tuple(RT.pf.ASOF_FEATURES)
    assert W.TASK.key == "wp-pregame" and W.TASK.primary_metric == "log_loss"
    assert W.TASK.metrics == ("log_loss", "brier", "ece", "auc") and W.TASK.target == "home_win"


def _mini(rows):
    return pd.DataFrame([{"game_id": f"g{i}", "kickoff_utc": pd.Timestamp("2020-09-01", tz="UTC") + pd.Timedelta(days=7 * i),
                          "season": s, "week": i + 1, "home_team": h, "away_team": a, "result": r, "neutral": n}
                         for i, (s, h, a, r, n) in enumerate(rows)])


def test_elo_online_by_hand_pre_game_ratings_and_future_game():
    h = _mini([(2020, "A", "B", 10.0, False), (2020, "A", "B", 0.0, False), (2021, "A", "B", np.nan, False)])
    eh, ea, st = pf.elo_online(h, k=0.1, hfa=0.0, cap=28.0, reversion=1 / 3)
    # jogo 1: ratings ANTES = 0; erro 10 -> A=+1, B=-1. Jogo 2: antes A=1, B=-1; erro = 0 - 2 = -2 -> A=0.8, B=-0.8.
    assert (eh[0], ea[0]) == (0.0, 0.0) and (eh[1], ea[1]) == (1.0, -1.0)
    # jogo 3 (futuro, temporada nova): regressão 2/3 antes de usar; não atualiza nada
    assert eh[2] == pytest.approx(0.8 * 2 / 3) and ea[2] == pytest.approx(-0.8 * 2 / 3)
    assert st["last_season"] == 2021 and st["ratings"]["A"] == pytest.approx(0.8 * 2 / 3)
    # campo neutro: sem hfa no erro; margem limitada ao teto
    _, _, st2 = pf.elo_online(_mini([(2020, "A", "B", 60.0, True)]), 0.1, 3.0, 28.0, 1 / 3)
    assert st2["ratings"]["A"] == pytest.approx(2.8)
    _, _, st3 = pf.elo_online(_mini([(2020, "A", "B", 10.0, False)]), 0.1, 3.0, 28.0, 1 / 3)
    assert st3["ratings"]["A"] == pytest.approx(0.7)


def test_elo_online_final_state_equals_ratings_elo_fit_and_ignores_row_order():
    g = synth_schedule(pending_from=(2030, 1))
    g["neutral"] = g["neutral"].astype(bool)
    eh, ea, st = pf.elo_online(g, **{k: W.ELO[k] for k in ("k", "hfa", "cap", "reversion")})
    ref = RT.pf.elo_fit(g, W.ELO["k"], W.ELO["hfa"], W.ELO["cap"], W.ELO["reversion"])
    assert st["ratings"] == pytest.approx(ref["ratings"]) and st["last_season"] == ref["last_season"]
    shuffled = g.sample(frac=1.0, random_state=1)
    eh2, ea2, _ = pf.elo_online(shuffled, **{k: W.ELO[k] for k in ("k", "hfa", "cap", "reversion")})
    np.testing.assert_allclose(eh[shuffled.index], eh2)  # alinhado às linhas de entrada, não à ordem de kickoff
    np.testing.assert_allclose(ea[shuffled.index], ea2)


# ------------------------------------------------------------------ vazamento

def test_features_of_games_up_to_x_do_not_depend_on_the_result_of_x():
    """Mudar o resultado do jogo X não muda NENHUMA feature de jogo com kickoff <= X (inclusive jogos de treino); as
    features de jogos depois de X mudam (o teste é sensível)."""
    g = synth_schedule()
    base, _ = W.with_features(g, "b")
    for pos in (40, 123, 200):
        x = g.iloc[pos]
        g2 = g.copy()
        g2.loc[pos, "result"] = x["result"] + 40.0
        pert, _ = W.with_features(g2, "b")
        upto = (g["kickoff_utc"] <= x["kickoff_utc"]).to_numpy()
        cols = ["elo_home", "elo_away", "elo_diff", "home_field", "rest_diff", "div_game", *pf.ASOF_DIFF_COLUMNS]
        pd.testing.assert_frame_equal(base.loc[upto, cols], pert.loc[upto, cols])
        later = ~upto
        assert not np.allclose(base.loc[later, "elo_diff"].to_numpy(), pert.loc[later, "elo_diff"].to_numpy())
    # a feature de rating de um jogo de treino NÃO é o rating final (que já viu o próprio jogo): prova direta
    eh, ea, st = pf.elo_online(g.assign(neutral=g["neutral"].astype(bool)), **{k: W.ELO[k] for k in ("k", "hfa", "cap", "reversion")})
    first_team_game = g[(g.home_team == "T0")].index[0]
    assert base.loc[first_team_game, "elo_home"] != pytest.approx(st["ratings"]["T0"])


def test_pending_and_tie_rows_never_update_ratings_but_ties_do_count_in_elo(synth):
    allg, df, info = synth
    pend = allg[~allg["completed"]]
    assert len(pend) == 8 and pend["elo_diff"].notna().all() and info["pending_games"] == 8
    # os jogos futuros veem o estado FINAL do Elo (nenhum jogo futuro atualizou nada)
    st = info["elo_state"]["ratings"]
    np.testing.assert_allclose(pend["elo_diff"].to_numpy(), [st[h] - st[a] for h, a in zip(pend.home_team, pend.away_team)])
    ties = allg[allg["tie"]]
    assert len(ties) > 0
    t = ties.iloc[0]
    nxt = allg[(allg.kickoff_utc > t.kickoff_utc) & ((allg.home_team == t.home_team) | (allg.away_team == t.home_team))].iloc[0]
    # o empate moveu o rating do mandante (diferente de zero, ratings antes ≠ depois quando os times eram desiguais)
    assert nxt["elo_home" if nxt.home_team == t.home_team else "elo_away"] != t["elo_home"] or t["elo_home"] != t["elo_away"]


# ------------------------------------------------------------------ empates, alvo

def test_ties_are_excluded_from_the_target_and_counted(synth):
    allg, df, info = synth
    n_tie = int(((allg["result"] == 0) & allg["completed"]).sum())
    assert n_tie > 0 and info["ties_excluded"] == n_tie
    assert (df["result"] != 0).all() and df["completed"].all() and not df["tie"].any()
    assert info["games_modeled"] == len(df) == info["games_completed"] - n_tie
    assert df["home_win"].isin([0, 1]).all() and (df["home_win"] == (df["result"] > 0).astype(int)).all()
    assert allg.loc[allg["tie"], "home_win"].isna().all() and allg.loc[~allg["completed"], "home_win"].isna().all()
    assert info["next_week"] == [2018, 7]
    assert allg.columns.is_unique and allg["div_game"].dtype == float  # sem coluna duplicada (feature x calendário)


# ------------------------------------------------------------------ mercado

def test_market_formula_numeric_example_and_invalid_pairs():
    # -150 / +130: imp = 150/250 = 0.6 e 100/230 = 0.434783; justa = 0.6 / 1.034783 = 0.579832
    p = pf.market_prob([-150.0], [130.0])
    assert p[0] == pytest.approx(0.6 / (0.6 + 100 / 230)) and p[0] == pytest.approx(0.579832, abs=1e-6)
    np.testing.assert_allclose(pf.implied_prob([-150, 130, 100, -100]), [0.6, 100 / 230, 0.5, 0.5])
    assert pf.market_prob([-110.0], [-110.0])[0] == pytest.approx(0.5)  # remoção proporcional: pick'em com vig = 0,5
    assert pf.market_prob([200.0], [-250.0])[0] < 0.5  # mandante azarão
    # a probabilidade justa soma 1 com a do visitante (mesma fórmula trocando os lados)
    assert pf.market_prob([-150.0], [130.0])[0] + pf.market_prob([130.0], [-150.0])[0] == pytest.approx(1.0)
    bad = pf.market_prob([0.0, np.nan, 50.0, -150.0, -150.0], [100.0, 100.0, 100.0, np.nan, 130.0])
    assert np.isnan(bad[:4]).all() and np.isfinite(bad[4])


def test_market_reference_matches_formula_and_refuses_missing_pairs(synth):
    allg, df, info = synth
    te = df[df.season == 2018].head(10)
    got = W.MarketReference().fit(df).predict(te)
    np.testing.assert_allclose(got, pf.market_prob(te["home_moneyline"], te["away_moneyline"]))
    assert info["market_no_valid_pair"] == 0 and info["market_no_valid_pair_pending"] == 4
    with pytest.raises(W.WpError, match="moneyline"):
        W.MarketReference().fit(df).predict(te.assign(home_moneyline=np.nan))


# ------------------------------------------------------------------ campo neutro, baselines, modelos

def test_neutral_field_means_even_probability_and_no_home_advantage(synth):
    allg, df, info = synth
    neutral = df[df["neutral"]]
    assert len(neutral) > 0 and (neutral["home_field"] == 0).all()
    f = W.HomeRateBaseline().fit(df)
    assert (f.predict(neutral) == 0.5).all()
    nn = ~df["neutral"].to_numpy()
    assert f.to_json()["home_rate"] == pytest.approx(df["home_win"].to_numpy()[nn].mean())
    assert (W.CoinBaseline().fit(df).predict(df.head(5)) == 0.5).all()
    # logística sem intercepto: campo neutro e Elo igual = exatamente 0,5
    probe = df.head(3).assign(elo_diff=0.0, home_field=0.0)
    for name in ("logit_elo", "logit_elo_ctx"):
        p = W.LogitModel(name).fit(df)
        pr = probe.assign(rest_diff=0.0, div_game=0.0)
        np.testing.assert_allclose(p.predict(pr), 0.5)
    ed = W.EloDirect().fit(df)
    np.testing.assert_allclose(ed.predict(probe), 0.5)  # Φ(0) = 0,5
    home = probe.assign(home_field=1.0)
    from math import erf, sqrt
    assert ed.predict(home)[0] == pytest.approx(0.5 * (1 + erf(W.ELO["hfa"] / W.SIGMA / sqrt(2))))


def test_logit_equals_sklearn_and_pyfunc_prediction(synth):
    allg, df, info = synth
    names = W.FEATURE_SETS["logit_combo"]
    fitted = W.LogitModel("logit_combo").fit(df)
    p = fitted.to_json()
    ok = df[names].notna().all(axis=1)
    X = df.loc[ok, names].to_numpy(dtype=float)
    scale = X.std(axis=0)
    ref = LogisticRegression(C=1.0, fit_intercept=False, max_iter=1000).fit(X / scale, df.loc[ok, "home_win"])
    np.testing.assert_allclose(p["coef"], ref.coef_[0], atol=1e-8)
    np.testing.assert_allclose(p["scale"], scale)
    probe = df[df.season == 2018].head(12)
    want = ref.predict_proba(probe[names].to_numpy(dtype=float) / scale)[:, 1]
    np.testing.assert_allclose(fitted.predict(probe), want, atol=1e-10)
    np.testing.assert_allclose(pf.predict_features(p, probe), want, atol=1e-10)
    assert p["intercept"] == 0.0 and p["n_train"] == int(ok.sum()) and W.LogitModel("logit_elo").fit(df).to_json()["coef_per_unit"]["elo_diff"] > 0
    json.dumps(p)  # JSON puro
    with pytest.raises(ValueError, match="nula"):
        fitted.predict(probe.assign(asof_off_epa_diff=np.nan))


def test_candidates_use_only_their_features(synth):
    allg, df, info = synth
    assert W.LogitModel("logit_elo").columns() == ["elo_diff", "home_field"]
    assert "elo_diff" not in W.LogitModel("logit_asof").columns()
    assert set(W.LogitModel("logit_combo").columns()) == set(pf.FEATURE_COLUMNS)
    # mudar uma coluna que o modelo não usa não muda a previsão
    tr, te = df[df.season < 2018], df[df.season == 2018].head(20)
    a = W.LogitModel("logit_elo").fit(tr).predict(te)
    b = W.LogitModel("logit_elo").fit(tr.assign(rest_diff=99.0, div_game=1.0)).predict(te.assign(rest_diff=-9.0))
    np.testing.assert_allclose(a, b)


# ------------------------------------------------------------------ extras

def test_accuracy_and_artifacts_by_hand():
    test = pd.DataFrame({"home_win": [1, 0, 1, 0, 1], "season": [2018, 2018, 2018, 2019, 2019],
                         "game_id": list("abcde")})
    pred = np.array([0.7, 0.8, 0.5, 0.2, 0.4])
    # acertos: sim, não, 0,5 (p = 0,5), sim, não -> 2,5 / 5
    assert W.accuracy(test, pred) == pytest.approx(0.5)
    art = W.wp_artifacts(test, pred)
    rows = art["by_season.json"]["rows"]
    assert [r["season"] for r in rows] == [2018, 2019] and [r["n"] for r in rows] == [3, 2]
    assert rows[1]["accuracy"] == pytest.approx(0.5) and rows[1]["log_loss"] == pytest.approx(-(np.log(0.8) + np.log(0.4)) / 2)
    assert art["oos_pred.json"] == {"game_id": list("abcde"), "p": pred.tolist()}
    assert sum(r["n"] for r in art["calibration.json"]["rows"]) == 5


# ------------------------------------------------------------------ backtest, registro, previsão

@pytest.fixture
def bt(synth):
    allg, df, info = synth
    res = W.run(df, "synth-build")
    return allg, df, info, res


def test_splits_are_the_ratings_splits(synth):
    allg, df, info = synth
    assert [s.to_dict() for s in RT.splits_for(df)] == [s.to_dict() for s in RT.splits_for(df)]
    sp = RT.splits_for(df)
    assert sp[0].name == "s2018w01" and sp[0].train_until == (2017, B.LAST_WEEK) and len(sp) == 6


def test_backtest_selects_by_log_loss_and_market_is_outside_the_rule(bt):
    allg, df, info, res = bt
    cands = {"logit_elo", "logit_elo_ctx", "logit_asof", "logit_combo", "elo_direct"}
    assert res.roles["market"] == "reference" and res.roles["coin"] == res.roles["home_rate"] == "baseline"
    assert set(res.roles) == cands | {"coin", "home_rate", "market"}
    assert res.selected_model in cands
    assert res.pooled[res.selected_model]["log_loss"] == min(res.pooled[m]["log_loss"] for m in cands)
    best_base = min(res.pooled[m]["log_loss"] for m in ("coin", "home_rate"))
    assert res.beats_baselines == (res.pooled[res.selected_model]["log_loss"] < best_base)
    for m in res.pooled:
        assert {"log_loss", "brier", "ece", "auc", "accuracy", "n"} <= set(res.pooled[m])
    assert res.pooled["coin"]["log_loss"] == pytest.approx(np.log(2)) and res.pooled["coin"]["auc"] == pytest.approx(0.5)
    assert np.isfinite(res.pooled["market"]["log_loss"]) and "market" != res.selected_model
    n_test = int((df.season >= 2018).sum())
    assert all(res.pooled[m]["n"] == n_test for m in res.pooled)


def test_out_of_sample_predictions_are_the_fold_predictions(bt):
    allg, df, info, res = bt
    sel = res.selected_model
    oos = W.oos_predictions(res.parent_run_id, sel)
    test = df[df.season >= 2018]
    assert set(oos) == set(test["game_id"]) and len(oos) == len(test)
    # recomputa uma dobra à mão: treino estritamente anterior, previsão da semana
    sp = RT.splits_for(df)[5]
    tr, te = B.split_frames(df, sp)
    want = W.selected_model(sel).fit(tr).predict(te)
    np.testing.assert_allclose([oos[g] for g in te["game_id"]], want, atol=1e-12)


def test_register_pyfunc_equals_fit_and_predict_all_marks_out_of_sample(bt, tmp_path):
    allg, df, info, res = bt
    out = W.register(df, info, res.parent_run_id) if res.beats_baselines else None
    if out is None:  # o conjunto sintético sempre deve bater os baselines
        pytest.fail("o modelo sintético não bateu os baselines")
    assert out["name"] == "hub-wp-pregame" and out["version"] == "1"
    model = mlflow.pyfunc.load_model("models:/hub-wp-pregame@champion")
    params, mv = W.champion_params()
    assert params["elo_state"] == info["elo_state"] and mv.tags["selected_model"] == res.selected_model
    pend = allg[~allg["completed"]]
    raw = pf.input_frame(pend, params)
    got = model.predict(raw)
    np.testing.assert_allclose(got["p_home"], W.predict_rows(params, allg)[~allg["completed"].to_numpy()], atol=1e-12)
    np.testing.assert_allclose(got["p_home"], pf.predict_features(params, pend), atol=1e-12)
    with pytest.raises(Exception, match="sem rating"):
        model.predict(raw.assign(home_team="XXX"))
    # temporada seguinte: o Elo regride 1/3 antes de prever
    nxt = pf.state_elo_diff(params["elo_state"], pend["home_team"], pend["away_team"], pend["season"] + 1)
    np.testing.assert_allclose(nxt, pend["elo_diff"].to_numpy() * (1 - W.ELO["reversion"]))
    # previsões em lote
    path = W.predict_all(allg, df, info, tmp_path / "home")
    gw = pd.read_parquet(path)
    assert len(gw) == len(allg) and gw["game_id"].is_unique
    test = df[df.season >= 2018]
    assert set(gw.loc[gw.out_of_sample, "game_id"]) == set(test["game_id"])
    assert not gw.loc[~gw.completed, "out_of_sample"].any() and not gw.loc[gw.tie, "out_of_sample"].any()
    oos = W.oos_predictions(res.parent_run_id, res.selected_model)
    m = gw[gw.out_of_sample]
    np.testing.assert_allclose(m["p_home_model"].to_numpy(), m["game_id"].map(oos).to_numpy())
    assert set(gw.loc[gw.out_of_sample, "p_source"]) == {"walk_forward"}
    assert set(gw.loc[~gw.completed, "p_source"]) == {"champion_future"}
    np.testing.assert_allclose(gw["diff_model_market"].to_numpy(), (gw["p_home_model"] - gw["p_home_market"]).to_numpy())
    # mercado: presente nos completos, ausente nos jogos da semana 8 de 2018 (sem moneyline)
    assert gw.loc[gw.completed, "p_home_market"].notna().all() and gw.loc[~gw.completed & (gw.week == 8), "p_home_market"].isna().all()
    d = path.parent
    up = json.loads((d / "upcoming.json").read_text())
    assert (up["season"], up["week"]) == (2018, 7) and len(up["games"]) == 4
    assert {"p_home_model", "p_home_market"} <= set(up["games"][0]) and "semana 7" in (d / "upcoming.md").read_text()
    meta = json.loads((d / "meta.json").read_text())
    assert meta["model"] == "hub-wp-pregame@1" and meta["stale"] is False and meta["oos_rows"] == len(test)
    # dados mudaram depois do ajuste: marcado como atrasado
    W.predict_all(allg, df.iloc[:-5], info, tmp_path / "home2")
    assert json.loads((tmp_path / "home2/predictions/wp_pregame/synth-build/meta.json").read_text())["stale"] is True


def test_register_refuses_stale_data_id(bt):
    allg, df, info, res = bt
    with pytest.raises(W.WpError, match="data_id"):
        W.register(df, {**info, "build_id": "outro-build"}, res.parent_run_id)


def test_card_has_market_warning_calibration_and_coefficients(bt, tmp_path):
    allg, df, info, res = bt
    W.register(df, info, res.parent_run_id)
    W.predict_all(allg, df, info, tmp_path / "home")
    text = W.card_text(res.parent_run_id, info, tmp_path / "home")
    assert "reference (fora da regra)" in text and "REFERÊNCIA fora da regra" in text and "lesões" in text
    assert "Calibração por decis" in text and "`market`" in text and "| 2018 |" in text
    assert "hub-wp-pregame@champion" in text and "Próxima semana" in text and "accuracy" in text
    assert "Um split por semana" in text and "Hiperparâmetros fixos" in text


def test_cli_registers_wp_pregame_commands():
    from models import MODELS
    assert MODELS["wp_pregame"] == "models.wp_pregame"
    with pytest.raises(SystemExit) as e:
        cli.main(["backtest", "wp_pregame", "--help"])
    assert e.value.code == 0


# ------------------------------------------------------------------ dados reais

@pytest.mark.real_data
def test_real_data_counts_and_no_future_features():
    try:
        allg, info = W.load_games()
    except Exception as exc:
        pytest.skip(f"sem dados reais: {exc}")
    assert info["ties_excluded"] > 0 and info["games_modeled"] == info["games_completed"] - info["ties_excluded"]
    assert info["market_no_valid_pair_test"] == 0 and info["games_null_asof_test"] == 0
    df = W.modeled(allg)
    nulls = df[df[list(pf.ASOF_DIFF_COLUMNS)].isna().any(axis=1)]
    assert set(zip(nulls["season"], nulls["week"])) == {(2011, 1)}
