"""H6 - Ratings de times: ordem recuperada, ausência de vazamento, campo neutro, regressão entre temporadas,
sinal do spread, pyfunc = ajuste em memória, backtest semanal e referência fora da regra."""
import json
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import pytest
from mlflow import MlflowClient

import backtest as B
import cli
from models import ratings as R

pf = R.pf
TEAMS = [f"T{i}" for i in range(8)]
TRUE = dict(zip(TEAMS, [8.0, 5.0, 2.0, 0.5, -0.5, -2.0, -5.0, -8.0]))
HFA = 2.5


def synth_games(seasons=range(2011, 2019), weeks=8, noise=7.0, seed=5):
    """Liga de brinquedo: 8 times com forças conhecidas, 4 jogos por semana, vantagem de casa 2,5, 1 jogo neutro
    por temporada. `team_asof` sintético = força verdadeira + ruído (estado do time, fixo por jogo)."""
    rng = np.random.default_rng(seed)
    rows = []
    t0 = pd.Timestamp("2011-09-10", tz="UTC")
    for s in seasons:
        for w in range(1, weeks + 1):
            order = rng.permutation(TEAMS)
            for g in range(4):
                h, a = order[2 * g], order[2 * g + 1]
                neutral = (w == 3 and g == 0)
                margin = np.round((0 if neutral else HFA) + TRUE[h] - TRUE[a] + rng.normal(0, noise))
                k = t0 + pd.Timedelta(days=365 * (s - 2011) + 7 * (w - 1), hours=g)
                row = {"game_id": f"{s}_{w:02d}_{a}_{h}", "season": s, "week": w, "kickoff_utc": k, "home_team": h,
                       "away_team": a, "result": float(margin), "neutral": bool(neutral),
                       "spread_line": float(np.round((0 if neutral else HFA) + TRUE[h] - TRUE[a]))}
                for side, team in (("home", h), ("away", a)):
                    row[f"{side}_ewm4_off_epa"] = 0.02 * TRUE[team] + rng.normal(0, 0.02)
                    row[f"{side}_ewm4_def_epa"] = -0.02 * TRUE[team] + rng.normal(0, 0.02)
                    row[f"{side}_ewm4_point_diff"] = TRUE[team] + rng.normal(0, 2.0)
                rows.append(row)
    return pd.DataFrame(rows).sort_values(["kickoff_utc", "game_id"]).reset_index(drop=True)


def synth_asof(df):
    """team_asof longo (game_id, team, kickoff_utc, 3 features) a partir das colunas dos jogos, mais UM jogo futuro por
    time (estado 'de agora') depois do último jogo de `df`."""
    rows = []
    for _, g in df.iterrows():
        for side, team in (("home", g.home_team), ("away", g.away_team)):
            rows.append({"game_id": g.game_id, "team": team, "kickoff_utc": g.kickoff_utc,
                         **{f: g[f"{side}_{f}"] for f in pf.ASOF_FEATURES}})
    last = df["kickoff_utc"].max()
    for i, team in enumerate(TEAMS):
        rows.append({"game_id": f"futuro_{team}", "team": team, "kickoff_utc": last + pd.Timedelta(days=7),
                     **{f: [0.02 * TRUE[team], -0.02 * TRUE[team], TRUE[team]][j] for j, f in enumerate(pf.ASOF_FEATURES)}})
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def games():
    return synth_games()


def rank_corr(a: dict, b: dict) -> float:
    ks = sorted(a)
    return float(pd.Series([a[k] for k in ks]).corr(pd.Series([b[k] for k in ks]), method="spearman"))


# ------------------------------------------------------------------ ratings recuperam a ordem

def test_elo_and_ridge_recover_order_and_hfa(games):
    big = synth_games(seasons=range(2011, 2024), weeks=12, noise=5.0, seed=9)
    elo = pf.elo_fit(big, 0.07, 2.5, 28.0, 1 / 3)
    assert rank_corr(elo["ratings"], TRUE) > 0.9
    for hl in (17.0, 34.0):
        rd = pf.ridge_fit(big, hl, 5.0)
        assert rank_corr(rd["ratings"], TRUE) > 0.95
        assert rd["hfa"] == pytest.approx(HFA, abs=1.0)
    order = sorted(elo["ratings"], key=elo["ratings"].get)  # o Elo é ruidoso: extremos nos dois últimos lugares
    assert order[-1] in ("T0", "T1") and order[0] in ("T6", "T7")
    assert sum(elo["ratings"].values()) == pytest.approx(0.0, abs=1e-9)  # atualização de soma zero


def test_asof_linear_recovers_signal_and_ratings_from_state(games):
    asof = synth_asof(games)
    state = R.asof_state(asof, games["kickoff_utc"].max())
    assert set(state.index) == set(TEAMS)  # estado antes do próximo jogo (o "futuro_*")
    p = pf.asof_fit(games, state)
    assert p["n_games"] == len(games) and p["n_dropped_null"] == 0
    assert rank_corr(p["ratings"], TRUE) > 0.95
    # consistência: margem por ratings (estado do próximo jogo) = margem por diferenças do próprio jogo
    row = pd.DataFrame([{"home_team": "T0", "away_team": "T7", "neutral": False,
                         **{f"home_{f}": state.loc["T0", f] for f in pf.ASOF_FEATURES},
                         **{f"away_{f}": state.loc["T7", f] for f in pf.ASOF_FEATURES}}])
    by_ratings = pf.predict_margin(p, ["T0"], ["T7"], [False])
    np.testing.assert_allclose(by_ratings, pf.predict_asof(p, row), atol=1e-9)


def test_asof_state_is_next_game_strictly_after_cutoff(games):
    asof = synth_asof(games)
    cutoff = games["kickoff_utc"].iloc[40]
    st = R.asof_state(asof, cutoff)
    nxt = asof[asof["kickoff_utc"] > cutoff].sort_values("kickoff_utc").drop_duplicates("team").set_index("team")
    for team in st.index:
        assert (nxt.loc[team, list(pf.ASOF_FEATURES)].to_numpy(dtype=float) == st.loc[team].to_numpy(dtype=float)).all()
    # um jogo no instante exato do corte NÃO é o 'próximo'
    at = asof[asof["kickoff_utc"] == cutoff]
    assert not at["game_id"].isin(nxt["game_id"]).any()


# ------------------------------------------------------------------ vazamento temporal

@pytest.mark.parametrize("make", [
    lambda a: R.EloModel(), lambda a: R.RidgeDecayModel("r17", 17.0), lambda a: R.AsofLinearModel(a)])
def test_history_ignores_future_results(games, make):
    """Mudar resultado (ou team_asof) de jogos de (s, w) em diante não muda o rating de ANTES da semana (s, w)."""
    asof = synth_asof(games)
    model = make(asof)
    s, w = 2015, 5
    pairs = [(2015, 5), (2015, 6)]
    base = R.ratings_history(games, model, pairs)
    future = (games.season > s) | ((games.season == s) & (games.week >= w))
    g2 = games.copy()
    g2.loc[future, "result"] = g2.loc[future, "result"] + 40.0
    asof2 = asof.copy()
    # team_asof de jogos DEPOIS da semana (s, w) (o de (s, w) é o estado legítimo "antes do próximo jogo")
    after = (games.season > s) | ((games.season == s) & (games.week > w))
    asof2.loc[asof2["kickoff_utc"] >= games.loc[after, "kickoff_utc"].min(), pf.ASOF_FEATURES[2]] += 99.0
    pert = R.ratings_history(g2, make(asof2), pairs)
    a = base[(base.season == s) & (base.week == w)].set_index("team")["rating"]
    b = pert[(pert.season == s) & (pert.week == w)].set_index("team")["rating"]
    pd.testing.assert_series_equal(a, b)
    # e a semana seguinte, que já vê a semana (s, w) real, muda: o teste é sensível
    a6 = base[base.week == 6].set_index("team")["rating"]
    b6 = pert[pert.week == 6].set_index("team")["rating"]
    assert not np.allclose(a6.to_numpy(), b6.to_numpy())


def test_history_week_uses_only_strictly_earlier_games(games):
    h = R.ratings_history(games, R.EloModel(), [(2014, 1)])
    prior = games[games.season < 2014]
    assert (h["n_games_train"] == len(prior)).all()
    direct = pf.team_ratings(pf.elo_fit(prior, 0.07, 2.0, 28.0, 1 / 3), 2014)
    got = h.set_index("team")["rating"].to_dict()
    assert got == pytest.approx(direct)
    assert len(h) == 8


def test_split_train_is_strictly_before_test(games):
    for sp in R.splits_for(games)[:6]:
        tr, te = B.split_frames(games, sp)
        assert (tr["season"] * 100 + tr["week"]).max() < (te["season"] * 100 + te["week"]).min()
        assert tr["kickoff_utc"].max() < te["kickoff_utc"].min()


# ------------------------------------------------------------------ Elo à mão, neutro, regressão entre temporadas

def _mini(rows):
    return pd.DataFrame([{"game_id": f"g{i}", "kickoff_utc": pd.Timestamp("2020-09-01", tz="UTC") + pd.Timedelta(days=7 * i),
                          "season": s, "week": i + 1, "home_team": h, "away_team": a, "result": r, "neutral": n}
                         for i, (s, h, a, r, n) in enumerate(rows)])


def test_elo_by_hand_with_cap_and_reversion():
    h = _mini([(2020, "A", "B", 10.0, False), (2021, "A", "B", 0.0, False)])
    p = pf.elo_fit(h, k=0.1, hfa=0.0, cap=28.0, reversion=1 / 3)
    # jogo 1: erro 10 -> A=+1, B=-1. Virada de temporada: x 2/3 -> A=0.6667, B=-0.6667. Jogo 2: previsto 1.3333,
    # erro -1.3333 -> A = 0.6667 - 0.13333, B = -0.6667 + 0.13333
    assert p["ratings"]["A"] == pytest.approx(2 / 3 - 0.2 / 1.5)
    assert p["ratings"]["B"] == pytest.approx(-(2 / 3 - 0.2 / 1.5))
    capped = pf.elo_fit(_mini([(2020, "A", "B", 60.0, False)]), 0.1, 0.0, 28.0, 1 / 3)
    assert capped["ratings"]["A"] == pytest.approx(2.8)


def test_elo_reversion_applies_to_new_season_only():
    h = _mini([(2020, "A", "B", 10.0, False), (2020, "B", "A", -4.0, False)])
    p = pf.elo_fit(h, 0.1, 2.0, 28.0, 1 / 3)
    r = p["ratings"]
    same = pf.predict_margin(p, ["A"], ["B"], [False], season=[2020])
    nxt = pf.predict_margin(p, ["A"], ["B"], [False], season=[2021])
    two = pf.predict_margin(p, ["A"], ["B"], [False], season=[2022])
    assert same[0] == pytest.approx(2.0 + r["A"] - r["B"])
    assert nxt[0] == pytest.approx(2.0 + (2 / 3) * (r["A"] - r["B"]))
    assert two[0] == pytest.approx(2.0 + (4 / 9) * (r["A"] - r["B"]))
    assert pf.team_ratings(p, 2021)["A"] == pytest.approx(r["A"] * 2 / 3)
    assert pf.team_ratings(p)["A"] == pytest.approx(r["A"])
    # sem season (pyfunc, 'de agora') não regride; e ridge/asof nunca regridem
    assert pf.predict_margin(p, ["A"], ["B"], [False])[0] == pytest.approx(same[0])
    rd = pf.ridge_fit(synth_games(), 17.0, 5.0)
    assert pf.team_ratings(rd, 2030) == rd["ratings"]


def test_neutral_field_has_no_home_advantage(games):
    for p in (pf.elo_fit(games, 0.07, 2.0, 28.0, 1 / 3), pf.ridge_fit(games, 17.0, 5.0)):
        r = p["ratings"]
        neutral = pf.predict_margin(p, ["T1"], ["T4"], [True])[0]
        home = pf.predict_margin(p, ["T1"], ["T4"], [False])[0]
        assert neutral == pytest.approx(r["T1"] - r["T4"])
        assert home - neutral == pytest.approx(p["hfa"])
    # no ajuste: um jogo neutro não treina o hfa (só ratings): histórico só de jogos neutros é recusado
    only_neutral = games.assign(neutral=True)
    with pytest.raises(ValueError, match="hfa"):
        pf.ridge_fit(only_neutral, 17.0, 5.0)
    # Elo: neutro não recebe hfa no erro: A vence por 10 em campo neutro (hfa 3): erro = 10, não 7
    p = pf.elo_fit(_mini([(2020, "A", "B", 10.0, True)]), 0.1, 3.0, 28.0, 1 / 3)
    assert p["ratings"]["A"] == pytest.approx(1.0)
    p = pf.elo_fit(_mini([(2020, "A", "B", 10.0, False)]), 0.1, 3.0, 28.0, 1 / 3)
    assert p["ratings"]["A"] == pytest.approx(0.7)


def test_unknown_team_and_bad_history_are_explicit(games):
    p = pf.elo_fit(games, 0.07, 2.0, 28.0, 1 / 3)
    with pytest.raises(ValueError, match="sem rating"):
        pf.predict_margin(p, ["XXX"], ["T1"], [False])
    with pytest.raises(ValueError, match="nulo"):
        pf.elo_fit(games.assign(result=np.nan), 0.07, 2.0, 28.0, 1 / 3)
    with pytest.raises(ValueError, match="ausentes"):
        pf.elo_fit(games.drop(columns=["neutral"]), 0.07, 2.0, 28.0, 1 / 3)
    with pytest.raises(ValueError, match="vazio"):
        pf.elo_fit(games.head(0), 0.07, 2.0, 28.0, 1 / 3)
    with pytest.raises(ValueError, match="nulo"):
        pf.predict_asof(pf.asof_fit(games), games.head(2).assign(home_ewm4_off_epa=np.nan))


def test_ridge_decay_gives_more_weight_to_recent_games(games):
    k = games["kickoff_utc"]
    w = pf.decay_weights(k, 17.0)
    assert w[k.argmax()] == pytest.approx(1.0) and (np.diff(w[np.argsort(k.to_numpy())]) >= 0).all()
    age_weeks = (k.max() - k.iloc[0]).total_seconds() / (7 * 86400)
    assert w[0] == pytest.approx(0.5 ** (age_weeks / 17.0))
    # sem decaimento relevante (meia-vida enorme) os ratings ficam próximos de uma regressão estática
    flat = pf.ridge_fit(games, 1e9, 5.0)
    assert all(np.isfinite(v) for v in flat["ratings"].values())


# ------------------------------------------------------------------ baselines, mercado, métricas

def test_baselines_and_market_sign(games):
    tr, te = games[games.season < 2017], games[games.season == 2017]
    assert np.all(R.ZeroBaseline().fit(tr).predict(te) == 0)
    f = R.HfaBaseline().fit(tr)
    nn = ~tr["neutral"].to_numpy()
    assert f.to_json()["hfa"] == pytest.approx(tr["result"].to_numpy()[nn].mean())
    got = f.predict(te)
    assert (got[te["neutral"].to_numpy()] == 0).all() and (got[~te["neutral"].to_numpy()] == f.to_json()["hfa"]).all()
    # mercado: spread_line positiva = mandante favorito = margem esperada do mandante (mesmo sinal da margem)
    mk = R.MarketReference().fit(tr).predict(te)
    np.testing.assert_array_equal(mk, te["spread_line"].to_numpy())
    assert np.corrcoef(mk, te["result"])[0, 1] > 0.5
    with pytest.raises(R.RatingsError, match="spread_line"):
        R.MarketReference().fit(tr).predict(te.assign(spread_line=np.nan))


def test_winner_acc_by_hand_ties_out_and_zero_is_half():
    test = pd.DataFrame({"result": [3.0, -7.0, 0.0, 10.0, -1.0]})
    pred = np.array([2.0, 4.0, 5.0, 0.0, -3.0])
    # decididos: (+,+) acerta, (-,+) erra, (10, 0) = 0.5, (-,-) acerta -> (1 + 0 + 0.5 + 1) / 4
    assert R.winner_acc(test, pred) == pytest.approx(2.5 / 4)


def test_by_season_artifact_matches_metrics():
    test = pd.DataFrame({"season": [2018, 2018, 2019], "result": [3.0, -7.0, 10.0]})
    art = R.by_season_artifacts(test, np.array([1.0, -3.0, 4.0]))["by_season.json"]["rows"]
    assert [r["season"] for r in art] == [2018, 2019] and [r["n"] for r in art] == [2, 1]
    assert art[0]["rmse"] == pytest.approx(np.sqrt((4 + 16) / 2)) and art[1]["winner_acc"] == 1.0


# ------------------------------------------------------------------ backtest semanal e registro

def test_splits_weekly_blocks_and_unique_windows(games):
    sp = R.splits_for(games)
    assert [s.name for s in sp] == [f"s2018w{w:02d}" for w in range(1, 9)]
    assert sp[0].train_until == (2017, B.LAST_WEEK) and sp[3].train_until == (2018, 3)
    blocks = R.splits_for(games, block=3)
    assert [s.test for s in blocks] == [(2018, 1, 3), (2018, 4, 6), (2018, 7, 8)]
    assert blocks[1].train_until == (2018, 3)
    sp_all = R.splits_for(pd.DataFrame({"season": [2018, 2019, 2019], "week": [1, 1, 2]}))
    assert [s.name for s in sp_all] == ["s2018w01", "s2019w01", "s2019w02"]


@pytest.fixture
def bt(games):
    games = games.assign(spread_line=games["result"] * 0.8)  # "oráculo": o mercado vence todos e não é selecionado
    asof = synth_asof(games)
    res = R.run(games, "synth-build", asof=asof)
    return games, asof, res


def test_backtest_selects_by_rmse_and_market_is_outside_the_rule(bt):
    games, asof, res = bt
    assert res.roles["market"] == "reference" and res.roles["zero"] == res.roles["hfa"] == "baseline"
    cands = {"elo", "ridge_decay_hl17", "ridge_decay_hl34", "asof_linear"}
    assert set(res.roles) == cands | {"zero", "hfa", "market"}
    assert res.selected_model in cands and res.beats_baselines
    assert res.pooled[res.selected_model]["rmse"] == min(res.pooled[m]["rmse"] for m in cands)
    # o mercado sintético (verdade sem o ruído) é melhor que todos e MESMO ASSIM não é selecionado
    assert res.pooled["market"]["rmse"] < res.pooled[res.selected_model]["rmse"]
    for m in res.pooled:
        assert {"rmse", "mae", "winner_acc", "n"} <= set(res.pooled[m])
    assert res.pooled["zero"]["winner_acc"] == pytest.approx(0.5)
    n_test = int((games.season == 2018).sum())
    assert all(res.pooled[m]["n"] == n_test for m in res.pooled)
    art = json.loads(Path(MlflowClient().download_artifacts(res.parent_run_id, f"extras/{res.selected_model}/by_season.json")).read_text())
    assert [r["season"] for r in art["rows"]] == [2018] and art["rows"][0]["n"] == n_test


def test_register_load_champion_and_predict_equal(bt, tmp_path):
    games, asof, res = bt
    out = R.register(games, "synth-build", res.parent_run_id, asof)
    assert out["name"] == "hub-ratings" and out["version"] == "1"
    model = mlflow.pyfunc.load_model("models:/hub-ratings@champion")
    params = R.fit_selected(games, res.selected_model, asof)
    probe = pd.DataFrame({"home_team": ["T0", "T7", "T3", "T2"], "away_team": ["T7", "T0", "T4", "T6"],
                          "neutral": [False, False, True, False]})
    got = model.predict(pf.input_frame(probe))
    want = pf.predict_frame(params, probe.assign(neutral=probe["neutral"].astype(float)))
    assert list(got.columns) == pf.OUTPUT_COLUMNS
    np.testing.assert_allclose(got.to_numpy(), want.to_numpy(), atol=1e-12)
    np.testing.assert_allclose(got["pred_margin"], got["home_rating"] - got["away_rating"]
                               + params["hfa"] * (1 - probe["neutral"].astype(float)), atol=1e-12)
    assert got["pred_margin"].iloc[0] > got["pred_margin"].iloc[1]  # T0 forte em casa x T7 fraco
    with pytest.raises(Exception, match="sem rating"):
        model.predict(pf.input_frame(probe.assign(home_team="XXX")))
    # histórico walk-forward + ranking atual
    d = R.predict_all(games, "synth-build", tmp_path / "home", next_week=[2019, 1], asof=asof).parent
    hist = pd.read_parquet(d / "ratings_history.parquet")
    assert list(hist.columns) == ["season", "week", "team", "rating", "n_games_train"]
    assert hist["season"].min() == 2012 and len(hist) == 8 * len(R.history_pairs(games, [2019, 1]))
    assert (hist.groupby(["season", "week"]).size() == 8).all() and hist["rating"].notna().all()
    cur = json.loads((d / "current_ratings.json").read_text())
    assert [r["rank"] for r in cur["ratings"]] == list(range(1, 9)) and cur["stale"] is False
    assert cur["ratings"][0]["team"] == "T0" and cur["ratings"][-1]["team"] == "T7"
    assert cur["ratings"][0]["rating"] == pytest.approx(params["ratings"]["T0"])
    meta = json.loads((d / "meta.json").read_text())
    assert meta["model"] == "hub-ratings@1" and meta["history_walk_forward"] is True and meta["stale"] is False
    # dados mudaram depois do ajuste: marca como atrasado
    R.predict_all(games.iloc[:-5], "synth-build", tmp_path / "home2", asof=asof)
    assert json.loads((tmp_path / "home2/predictions/ratings/synth-build/current_ratings.json").read_text())["stale"] is True


def test_register_refuses_stale_data_id(bt):
    games, asof, res = bt
    with pytest.raises(R.RatingsError, match="data_id"):
        R.register(games, "outro-build", res.parent_run_id, asof)


def test_card_has_market_warning_and_tables(bt, tmp_path):
    games, asof, res = bt
    R.register(games, "synth-build", res.parent_run_id, asof)
    R.predict_all(games, "synth-build", tmp_path / "home", asof=asof)
    info = {"build_id": "synth-build", "seasons": [2011, 2018]}
    text = R.card_text(res.parent_run_id, info, tmp_path / "home")
    assert "reference (fora da regra)" in text and "REFERÊNCIA fora da regra" in text
    assert "`market`" in text and "| 2018 |" in text and "Ratings atuais" in text and "hub-ratings@champion" in text
    assert "winner_acc" in text and "piloto walk-forward 2013-2017" in text and "Hiperparâmetros fixos" in text
    assert "| 1 | T0 |" in text
    assert "Um split por semana (8 no total), de s2018w01 a s2018w08" in text and "| s2018w01 |" not in text


def test_cli_registers_ratings_commands():
    from models import MODELS
    assert MODELS["ratings"] == "models.ratings"
    with pytest.raises(SystemExit) as e:
        cli.main(["backtest", "ratings", "--help"])
    assert e.value.code == 0


# ------------------------------------------------------------------ dados reais

def _real():
    try:
        return R.load_data()
    except Exception as exc:
        pytest.skip(f"sem dados reais: {exc}")


@pytest.mark.real_data
def test_real_spread_sign_matches_moneyline_and_asof_alignment():
    import features
    df, info, asof = _real()
    g = features.load_tables(info["build_id"])["games"].to_pandas()
    g = g[g["completed"] & g["home_moneyline"].notna() & (g["spread_line"] != 0)]
    agree = np.mean(np.sign(g["spread_line"]) == -np.sign(g["home_moneyline"] - g["away_moneyline"]))
    assert agree > 0.97  # spread positivo = mandante favorito = moneyline do mandante menor (mais negativa)
    assert info["games_null_spread"] == 0 and info["games_completed"] == len(df)
    # asof alinhado ao PRÓPRIO jogo: kickoff igual e time certo; nulos só nas 16 partidas da semana 1 de 2011
    m = df.merge(asof[["game_id", "team", "kickoff_utc"]], left_on=["game_id", "home_team"], right_on=["game_id", "team"])
    assert len(m) == len(df) and (m["kickoff_utc_x"] == m["kickoff_utc_y"]).all()
    nulls = df[df[R.ASOF_COLUMNS].isna().any(axis=1)]
    assert set(zip(nulls["season"], nulls["week"])) == {(2011, 1)}
    assert (df["result"] == df["result"].round()).all() and df["neutral"].sum() == info["neutral_games"]


# ------------------------------------------------------------------ piloto 2013-2017

def _pilot():
    import sys
    d = str(Path(R.__file__).resolve().parent.parent / "pilots")
    if d not in sys.path:
        sys.path.insert(0, d)
    import ratings_pilot
    return ratings_pilot


def test_pilot_restrict_drops_2018_plus_and_refuses_them():
    P = _pilot()
    g = synth_games(seasons=range(2011, 2020), weeks=3)
    r = P.restrict(g)
    assert r["season"].max() == 2017 and len(r) < len(g)
    with pytest.raises(RuntimeError, match="2017"):
        P.pilot_splits(g)
    # os splits do piloto só treinam com jogos estritamente anteriores à semana testada
    for s, w, tr, te in P.pilot_splits(r):
        assert (r.iloc[tr]["season"] * 100 + r.iloc[tr]["week"]).max() < s * 100 + w
        assert len(te) and (r.iloc[te]["season"] == s).all() and s >= 2013


def test_pilot_results_ignore_future_rows_and_are_aggregate(monkeypatch):
    P = _pilot()
    monkeypatch.setattr(P, "ELO_GRID", {"k": [0.07], "hfa": [2.0, 2.5], "cap": [28.0], "reversion": [1.0 / 3.0]})
    monkeypatch.setattr(P, "RIDGE_GRID", {"lam": [5.0], "halflife": [17.0, 34.0]})
    g = synth_games(seasons=range(2011, 2018), weeks=3)
    junk = synth_games(seasons=range(2018, 2020), weeks=3, seed=99)
    a = P.run_pilot(P.restrict(g))
    b = P.run_pilot(P.restrict(pd.concat([g, junk], ignore_index=True)))
    assert a == b and a["period"]["max_season_read"] == 2017
    assert a["elo"]["n_configs"] == 2 and a["ridge"]["n_configs"] == 2
    assert "home_team" not in json.dumps(a) and "game_id" not in P.to_markdown(a)


def test_committed_pilot_results_read_nothing_after_2017():
    f = Path(R.__file__).resolve().parent.parent / "pilots" / "ratings_pilot_results.json"
    if not f.exists():
        pytest.skip("resultados do piloto não gerados")
    res = json.loads(f.read_text())
    assert res["period"]["max_season_read"] <= 2017 and res["period"]["test_seasons"] == [2013, 2017]
    assert res["elo"]["n_configs"] == 180 and res["ridge"]["n_configs"] == 9
