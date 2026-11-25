"""H7 - WP pré-jogo: probabilidade de o mandante vencer (`home_win`) antes do kickoff.

Tarefa binária (log_loss primária; brier, ece, auc; acerto como métrica extra). Jogos completos REG+POST de 2011+, EMPATES
FORA (contados). Splits semanais 2018..última, os mesmos de `models/ratings.py` (H-D13). Toda a matemática (Elo online,
features, previsão, mercado) mora em `model_code/wp_pregame_pyfunc.py`.

VAZAMENTO: o rating Elo de CADA jogo, inclusive os de treino, é o rating ANTES daquele jogo, calculado online em ordem
de kickoff (`elo_online`): só depende de jogos anteriores. As features são pré-calculadas uma vez para todos os jogos
porque cada valor só depende do passado (testado: mudar o resultado do jogo X não muda nenhuma feature de jogo com
kickoff <= X). O `team_asof` já é, por construção do feature store, o estado antes do próprio jogo.

Candidatos (logística sklearn sem intercepto, hiperparâmetros fixos; `elo_direct` não ajusta nada): `logit_elo`,
`logit_elo_ctx`, `logit_asof`, `logit_combo`, `elo_direct`. Hiperparâmetros do Elo = os do `hub-ratings` (fixados em
piloto 2013-2017). Baselines: `coin` e `home_rate`. Referência (FORA da regra, H-D12): `market` = probabilidade justa do
moneyline de fechamento. Regra fixada antes: menor log_loss pooled entre os candidatos, precisando bater o melhor baseline.
"""
from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow import MlflowClient
from sklearn.linear_model import LogisticRegression

import backtest as B
import hubtrack
import metrics as M
from models import ratings as RT

MODEL_KEY = "wp_pregame"  # chave do CLI
MODULE_PATH = Path(__file__).resolve()
CODE_PATH = MODULE_PATH.parent.parent / "model_code" / "wp_pregame_pyfunc.py"
_spec = importlib.util.spec_from_file_location("hub_wp_pregame_pyfunc", CODE_PATH)
pf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pf)

# Chave do experimento/registro: `hub-wp-pregame` (hífen). O CLI continua `wp_pregame`.
TASK = B.Task(key="wp-pregame", target="home_win", kind="binary", primary_metric="log_loss",
              metrics=("log_loss", "brier", "ece", "auc"))
EXP_KEY = TASK.key
SEED = 0
FIRST_TRAIN_SEASON = RT.FIRST_TRAIN_SEASON
ELO = dict(RT.ELO)  # mesmos hiperparâmetros do hub-ratings (piloto walk-forward 2013-2017)
LOGIT_C = 1.0
SIGMA = 13.5  # elo_direct: desvio-padrão fixo da margem em pontos (sem ajuste)
FEATURE_SETS = {
    "logit_elo": ["elo_diff", "home_field"],
    "logit_elo_ctx": ["elo_diff", "home_field", "rest_diff", "div_game"],
    "logit_asof": ["home_field", *pf.ASOF_DIFF_COLUMNS],
    "logit_combo": ["elo_diff", "home_field", "rest_diff", "div_game", *pf.ASOF_DIFF_COLUMNS],
}
SCHEDULE_COLUMNS = ["game_id", "season", "week", "kickoff_utc", "home_team", "away_team", "result", "neutral",
                    "home_rest", "away_rest", "div_game", "home_moneyline", "away_moneyline", *pf.asof_columns()]
FEATURE_STORE_COLUMNS = ["elo_home", "elo_away", "elo_diff", "home_field", "rest_diff", *pf.ASOF_DIFF_COLUMNS]
DATA_COLUMNS = ["game_id", "season", "week", "kickoff_utc", "home_team", "away_team", "home_win", "neutral",
                "home_rest", "away_rest", "div_game", "home_moneyline", "away_moneyline",
                *FEATURE_STORE_COLUMNS, *pf.asof_columns()]
EXTRA_COLUMNS = ["home_win", "game_id"]  # lidas pelas métricas extras e pelos artefatos


class WpError(RuntimeError):
    pass


# ------------------------------------------------------------------ dados

def load_games(build_id: str | None = None, home=None) -> tuple[pd.DataFrame, dict]:
    """(todos os jogos 2011+ com features pré-jogo, info). Cada linha tem `completed`, `tie`, `home_win` (nulo em jogo
    futuro e em empate) e as features de `pf.make_features` (Elo online ANTES do jogo, descanso, divisão, asof).
    O `team_asof` entra pelo par (game_id, time) do PRÓPRIO jogo."""
    import features
    from hubpaths import hub_home
    home = Path(home) if home else hub_home()
    bdir = features.resolve_build(build_id, home)
    tables = features.load_tables(bdir.name, home)
    games = tables["games"].to_pandas()
    asof = tables["team_asof"].to_pandas()
    g = games[games["season"] >= FIRST_TRAIN_SEASON].copy()
    g["completed"] = g["completed"].astype(bool) & g["result"].notna()
    g["result"] = g["result"].where(g["completed"])
    g["neutral"] = g["location"].eq("Neutral")
    for side in ("home", "away"):
        a = asof[["game_id", "team", *pf.ASOF_FEATURES]].rename(
            columns={"team": f"{side}_team", **{f: f"{side}_{f}" for f in pf.ASOF_FEATURES}})
        g = g.merge(a, on=["game_id", f"{side}_team"], how="left", validate="one_to_one")
    g = g.sort_values(["kickoff_utc", "game_id"], kind="mergesort").reset_index(drop=True)
    return with_features(g, bdir.name)


def with_features(g: pd.DataFrame, build_id: str) -> tuple[pd.DataFrame, dict]:
    """Acrescenta features pré-jogo, `tie` e `home_win` a `g` (jogos 2011+ ordenados) e monta `info`."""
    feats = pf.make_features(g, ELO)
    state = feats.attrs["elo_state"]
    out = pd.concat([g.drop(columns=[c for c in feats.columns if c in g.columns]), feats], axis=1)  # sem nomes duplicados
    assert out.columns.is_unique, "colunas duplicadas nos jogos com features"
    out["tie"] = out["completed"] & (out["result"] == 0)
    out["home_win"] = np.where(out["completed"] & ~out["tie"], (out["result"] > 0).astype(float), np.nan)
    pend = out[~out["completed"]]
    next_week = None
    if len(pend):
        nxt = pend.sort_values(["season", "week"]).iloc[0]
        next_week = [int(nxt["season"]), int(nxt["week"])]
    df = out[out["completed"] & ~out["tie"]]
    mk = pf.market_prob(df["home_moneyline"], df["away_moneyline"])
    test_rows = df["season"] >= RT.TEST_SEASONS_FROM
    info = {"build_id": build_id, "games_total": int(len(out)), "games_completed": int(out["completed"].sum()),
            "ties_excluded": int(out["tie"].sum()), "games_modeled": int(len(df)),
            "seasons": [int(df["season"].min()), int(df["season"].max())],
            "neutral_games": int(df["neutral"].sum()), "pending_games": int(len(pend)), "next_week": next_week,
            "games_null_asof": int(df[list(pf.ASOF_DIFF_COLUMNS)].isna().any(axis=1).sum()),
            "games_null_asof_test": int(df.loc[test_rows, list(pf.ASOF_DIFF_COLUMNS)].isna().any(axis=1).sum()),
            "market_no_valid_pair": int(np.isnan(mk).sum()),
            "market_no_valid_pair_test": int(np.isnan(mk[test_rows.to_numpy()]).sum()),
            "market_no_valid_pair_pending": int(np.isnan(pf.market_prob(pend["home_moneyline"], pend["away_moneyline"])).sum()),
            "elo_state": state}
    return out, info


def modeled(allg: pd.DataFrame) -> pd.DataFrame:
    """Jogos do backtest: completos e sem empate."""
    df = allg[allg["completed"] & ~allg["tie"]].copy()
    df["home_win"] = df["home_win"].astype("int64")
    return df.reset_index(drop=True)


# ------------------------------------------------------------------ modelos

class _Fitted:
    def __init__(self, fn, js):
        self._fn, self._js = fn, js

    def predict(self, df):
        return self._fn(df)

    def to_json(self):
        return self._js


class CoinBaseline:
    """Baseline `coin`: 0,5 sempre."""
    name = "coin"

    def params(self):
        return {"p": 0.5}

    def columns(self):
        return []

    def fit(self, train):
        return _Fitted(lambda df: np.full(len(df), 0.5), {"p": 0.5})


class HomeRateBaseline:
    """Baseline `home_rate`: taxa de vitória do mandante nos jogos de campo NÃO neutro do treino; 0,5 em campo neutro."""
    name = "home_rate"

    def params(self):
        return {"estimate": "média de home_win nos jogos não neutros do treino", "neutral": 0.5}

    def columns(self):
        return ["home_win", "neutral"]

    def fit(self, train):
        nn = ~train["neutral"].to_numpy(dtype=bool)
        if not nn.any():
            raise WpError("treino sem jogo em campo não neutro")
        h = float(train["home_win"].to_numpy(dtype="float64")[nn].mean())
        return _Fitted(lambda df: np.where(df["neutral"].to_numpy(dtype=bool), 0.5, h), {"home_rate": h, "n": int(nn.sum())})


class MarketReference:
    """Referência `market`: probabilidade justa do moneyline de fechamento (remoção proporcional da margem da casa).
    Fora da regra de seleção. Moneyline sem par válido em jogo a prever é erro explícito (não se inventa)."""
    name = "market"

    def params(self):
        return {"source": "home_moneyline/away_moneyline de fechamento",
                "formula": "p = imp(home)/(imp(home)+imp(away)); imp(ml)=100/(ml+100) se ml>0, -ml/(-ml+100) se ml<0"}

    def columns(self):
        return ["home_moneyline", "away_moneyline"]

    def fit(self, train):
        def predict(df):
            p = pf.market_prob(df["home_moneyline"], df["away_moneyline"])
            if not np.isfinite(p).all():
                raise WpError(f"{int((~np.isfinite(p)).sum())} jogo(s) sem par válido de moneyline na referência `market`")
            return p
        return _Fitted(predict, {"note": "sem ajuste"})


def fit_logit(feats: pd.DataFrame, y, names: list, c: float = LOGIT_C) -> dict:
    """Logística sklearn sem intercepto sobre `names`, com cada coluna dividida pelo desvio-padrão do treino (sem
    centralizar, para que campo neutro e times iguais deem 0,5). Linhas com feature nula saem. JSON puro."""
    X = feats[names].to_numpy(dtype="float64")
    if X.shape[1] != len(names):
        raise WpError("colunas de features duplicadas ou ausentes")
    y = np.asarray(y, dtype="int64")
    ok = np.isfinite(X).all(axis=1)
    if ok.sum() < 20 or len(np.unique(y[ok])) < 2:
        raise WpError("poucos jogos (ou uma só classe) para ajustar")
    X, y = X[ok], y[ok]
    scale = X.std(axis=0)
    scale = np.where(scale > 0, scale, 1.0)
    lr = LogisticRegression(C=c, fit_intercept=False, solver="lbfgs", max_iter=1000).fit(X / scale, y)
    coef = lr.coef_[0]
    return {"format": pf.FORMAT, "kind": "logit", "features": list(names), "scale": [float(s) for s in scale],
            "coef": [float(v) for v in coef], "coef_per_unit": {n: float(v / s) for n, v, s in zip(names, coef, scale)},
            "intercept": 0.0, "n_train": int(ok.sum()), "n_dropped_null": int((~ok).sum()), "C": float(c)}


class LogitModel:
    """Candidato logístico sobre as features `FEATURE_SETS[name]`; ver `fit_logit`."""

    def __init__(self, name: str):
        self.name, self.names = name, FEATURE_SETS[name]

    def params(self):
        return {"kind": "logit", "features": self.names, "C": LOGIT_C, "fit_intercept": False,
                "scaling": "divide pelo desvio-padrão do treino, sem centralizar", "rest_clip": pf.REST_CLIP,
                "elo": ELO, "nulls": "linhas de treino com feature nula saem; jogo a prever com feature nula levanta erro"}

    def columns(self):
        return list(self.names)

    def fit(self, train):
        p = fit_logit(train, train["home_win"], self.names)
        return _Fitted(lambda df: pf.predict_features(p, df), p)


class EloDirect:
    """Candidato `elo_direct`: P = Φ((elo_diff + hfa * campo_não_neutro) / σ), σ e hfa FIXOS, sem ajuste."""
    name = "elo_direct"

    def params(self):
        return {"kind": "elo_direct", "sigma": SIGMA, "hfa": ELO["hfa"], "elo": ELO}

    def columns(self):
        return ["elo_diff", "home_field"]

    def fit(self, train):
        p = {"format": pf.FORMAT, "kind": "elo_direct", "sigma": SIGMA, "hfa": ELO["hfa"]}
        return _Fitted(lambda df: pf.predict_features(p, df), p)


def make_models():
    candidates = [LogitModel(n) for n in FEATURE_SETS] + [EloDirect()]
    return candidates, [CoinBaseline(), HomeRateBaseline()], [MarketReference()]


# ------------------------------------------------------------------ métricas extras e artefatos

def accuracy(test: pd.DataFrame, pred) -> float:
    """Acerto: (p > 0,5) = vitória do mandante; p exatamente 0,5 vale 0,5."""
    y = test["home_win"].to_numpy(dtype="float64")
    p = np.asarray(pred, dtype="float64")
    hit = np.where(p == 0.5, 0.5, ((p > 0.5) == (y == 1)).astype(float))
    return float(hit.mean())


EXTRA_METRICS = {"accuracy": accuracy}


def wp_artifacts(test: pd.DataFrame, pred) -> dict:
    """Por modelo, sobre os testes concatenados: `by_season.json` (métricas por temporada), `calibration.json`
    (decis de probabilidade prevista) e `oos_pred.json` (previsão walk-forward de cada jogo de teste, por game_id)."""
    pred = np.asarray(pred, dtype="float64")
    rows = []
    for s in sorted(test["season"].unique()):
        m = (test["season"] == s).to_numpy()
        y = test.loc[m, "home_win"].to_numpy()
        t = test.loc[m]
        rows.append({"season": int(s), "n": int(m.sum()), "log_loss": M.log_loss_binary(y, pred[m]),
                     "brier": M.brier_binary(y, pred[m]), "accuracy": accuracy(t, pred[m])})
    cal = M.calibration_table(pred, test["home_win"].to_numpy(dtype="float64"), bins=10, strategy="quantile")
    return {"by_season.json": {"rows": rows}, "calibration.json": {"rows": cal.to_dict("records")},
            "oos_pred.json": {"game_id": test["game_id"].tolist(), "p": [float(v) for v in pred]}}


# ------------------------------------------------------------------ backtest

def code_paths() -> list:
    return [CODE_PATH, MODULE_PATH, RT.MODULE_PATH]


def run(df: pd.DataFrame, data_id: str, force: bool = False, splits=None) -> B.BacktestResult:
    candidates, baselines, references = make_models()
    return B.run_backtest(TASK, candidates, baselines, splits or RT.splits_for(df), df,
                          B.SelectionRule(metric="log_loss", min_improvement=0.0), data_id, SEED, code_paths(),
                          force=force, references=references, extra_metrics=EXTRA_METRICS,
                          extra_artifacts=wp_artifacts, data_columns=EXTRA_COLUMNS)


def latest_parent(only_beating: bool = False, data_id: str | None = None):
    hubtrack.configure()
    exp_id = hubtrack.experiment(EXP_KEY)
    flt = "tags.role = 'parent' and attributes.status = 'FINISHED'"
    if only_beating:
        flt += " and tags.beats_baselines = 'true'"
    if data_id is not None:
        flt += f" and tags.data_id = '{data_id}'"
    runs = MlflowClient().search_runs([exp_id], filter_string=flt, order_by=["attributes.start_time DESC"], max_results=1)
    if not runs:
        raise WpError("nenhum backtest FINISHED" + (" que bateu os baselines" if only_beating else "")
                      + (f" para o build {data_id[:12]}" if data_id else "") + " em hub-wp-pregame"
                      + ("; rode `backtest wp_pregame` (ou passe --run-id)" if data_id else ""))
    return runs[0]


# ------------------------------------------------------------------ registro e previsão

def selected_model(selected: str):
    candidates, _b, _r = make_models()
    match = [c for c in candidates if c.name == selected]
    if not match:
        raise WpError(f"modelo selecionado {selected!r} não é um candidato")
    return match[0]


def final_params(df: pd.DataFrame, selected: str, elo_state: dict) -> dict:
    """Ajusta o selecionado em todos os jogos completos (sem empate) de `df` e junta o estado final do Elo, com o qual
    o pyfunc prevê jogos futuros a partir de times, temporada e campo neutro."""
    p = dict(selected_model(selected).fit(df).to_json())
    p["elo_state"] = elo_state
    return p


def register(df: pd.DataFrame, info: dict, source_run_id: str | None = None) -> dict:
    import register as R
    src = source_run_id or latest_parent(only_beating=True).info.run_id
    run_ = MlflowClient().get_run(src)
    if run_.data.tags.get("data_id") != info["build_id"]:
        raise WpError(f"o backtest {src[:8]} usou data_id {run_.data.tags.get('data_id')!r}, o build atual é "
                      f"{info['build_id']!r}: rode `backtest wp_pregame` de novo")
    selected = run_.data.tags.get("selected_model")
    model = selected_model(selected)
    params = final_params(df, selected, info["elo_state"])
    cols = pf.raw_columns(params)
    example = df[df[cols].notna().all(axis=1)].tail(5)  # linhas completas (a 1ª semana de 2011 não tem team_asof)
    out = R.register_json_model(EXP_KEY, CODE_PATH, params, pf.input_frame(example, params), src, model_name=selected,
                                hyperparams=model.params(), train_data_sha256=B.data_fingerprint(df, DATA_COLUMNS))
    out["selected_model"] = selected
    return out


def champion_params():
    """(params.json do champion, versão do modelo registrado)."""
    import tempfile

    import mlflow
    hubtrack.configure()
    name = hubtrack.experiment_name(EXP_KEY)
    mv = MlflowClient().get_model_version_by_alias(name, "champion")
    with tempfile.TemporaryDirectory(prefix="hub-wp-") as tmp:
        local = mlflow.artifacts.download_artifacts(artifact_uri=f"models:/{name}@champion", dst_path=tmp)
        found = [Path(r) / f for r, _d, fs in os.walk(local) for f in fs if f == "params.json"]
        if len(found) != 1:
            raise WpError(f"params.json do champion: {len(found)} arquivos")
        return json.loads(found[0].read_text()), mv


def oos_predictions(parent_run_id: str, model: str) -> dict:
    """{game_id: p} das previsões walk-forward de `model` no backtest `parent_run_id`."""
    path = MlflowClient().download_artifacts(parent_run_id, f"extras/{model}/oos_pred.json")
    d = json.loads(Path(path).read_text())
    return dict(zip(d["game_id"], d["p"]))


def predict_rows(params: dict, allg: pd.DataFrame) -> np.ndarray:
    """P(mandante) do `params` para todas as linhas de `allg`; NaN onde faltar feature (1ª semana de 2011 no asof)."""
    names = ["elo_diff", "home_field"] if params["kind"] == "elo_direct" else params["features"]
    ok = np.isfinite(allg[names].to_numpy(dtype="float64")).all(axis=1)
    out = np.full(len(allg), np.nan)
    if ok.any():
        out[ok] = pf.predict_features(params, allg.loc[ok])
    return out


def games_wp(allg: pd.DataFrame, params: dict, oos: dict) -> pd.DataFrame:
    """Uma linha por jogo (completo, empate ou futuro): p do modelo, p do mercado e a diferença. Jogos de teste do
    backtest levam a previsão da dobra correspondente (`out_of_sample` = true, `p_source` = walk_forward); os demais
    usam o champion (completos: `champion_in_sample`; futuros: `champion_future`)."""
    champ = predict_rows(params, allg)
    p = champ.copy()
    is_oos = allg["game_id"].isin(oos).to_numpy()
    p[is_oos] = allg.loc[is_oos, "game_id"].map(oos).to_numpy(dtype="float64")
    market = pf.market_prob(allg["home_moneyline"], allg["away_moneyline"])
    source = np.where(is_oos, "walk_forward", np.where(allg["completed"], "champion_in_sample", "champion_future"))
    out = pd.DataFrame({
        "game_id": allg["game_id"], "season": allg["season"], "week": allg["week"], "kickoff_utc": allg["kickoff_utc"],
        "home_team": allg["home_team"], "away_team": allg["away_team"], "neutral": allg["neutral"],
        "completed": allg["completed"], "tie": allg["tie"], "result": allg["result"], "home_win": allg["home_win"],
        "elo_diff": allg["elo_diff"], "p_home_model": p, "p_home_market": market,
        "diff_model_market": p - market, "out_of_sample": is_oos, "p_source": source})
    return out.reset_index(drop=True)


def upcoming_table(gw: pd.DataFrame, next_week) -> pd.DataFrame:
    if next_week is None:
        return gw.head(0)
    s, w = next_week
    u = gw[(gw["season"] == s) & (gw["week"] == w) & ~gw["completed"]]
    return u.sort_values(["kickoff_utc", "game_id"]).reset_index(drop=True)


def _pct(v) -> str:
    return "—" if v is None or not np.isfinite(v) else f"{100 * v:.1f}%"


def upcoming_markdown(u: pd.DataFrame, next_week, model: str) -> str:
    s, w = next_week
    L = [f"# WP pré-jogo: temporada {s}, semana {w}", "",
         f"Modelo `{model}` (probabilidade de o MANDANTE vencer, só com informação anterior ao jogo, sem lesões) × "
         "mercado (probabilidade justa do moneyline de fechamento; \"—\" quando o moneyline ainda não saiu). "
         "A diferença é modelo − mercado em pontos percentuais.", "",
         "| kickoff (UTC) | visitante | mandante | modelo | mercado | diferença |", "|---|---|---|---|---|---|"]
    for r in u.itertuples():
        d = "—" if not np.isfinite(r.diff_model_market) else f"{100 * r.diff_model_market:+.1f}"
        k = pd.Timestamp(r.kickoff_utc).strftime("%Y-%m-%d %H:%M")
        neutral = " (neutro)" if r.neutral else ""
        L.append(f"| {k} | {r.away_team} | {r.home_team}{neutral} | {_pct(r.p_home_model)} | {_pct(r.p_home_market)} | {d} |")
    return "\n".join(L) + "\n"


def predict_all(allg: pd.DataFrame, df: pd.DataFrame, info: dict, home) -> Path:
    """Grava `HUB/predictions/wp_pregame/<build_id>/{games_wp.parquet,upcoming.json,upcoming.md,meta.json}`."""
    params, mv = champion_params()
    name = hubtrack.experiment_name(EXP_KEY)
    selected = mv.tags.get("selected_model")
    model = selected_model(selected)
    if hubtrack.sha256_json(model.params()) != mv.tags.get("hyperparams_sha256"):
        raise WpError("hiperparâmetros do código diferem dos do champion: rode `register wp_pregame` de novo")
    src = mv.tags.get("source_run_id")
    oos = oos_predictions(src, selected)
    gw = games_wp(allg, params, oos)
    fp = B.data_fingerprint(df, DATA_COLUMNS)
    stale = mv.tags.get("train_data_sha256") != fp
    missing_oos = [g for g in oos if g not in set(gw["game_id"])]
    if missing_oos:
        raise WpError(f"{len(missing_oos)} jogo(s) do backtest ausentes dos dados atuais: rode `backtest` de novo")
    d = Path(home) / "predictions" / MODEL_KEY / info["build_id"]
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "games_wp.parquet.tmp"
    gw.to_parquet(tmp, index=False)
    os.replace(tmp, d / "games_wp.parquet")
    nw = info["next_week"]
    up = upcoming_table(gw, nw)
    model_ref = f"{name}@{mv.version}"
    cols = ["game_id", "kickoff_utc", "home_team", "away_team", "neutral", "p_home_model", "p_home_market", "diff_model_market"]
    rows = json.loads(up[cols].assign(kickoff_utc=up["kickoff_utc"].astype(str)).to_json(orient="records"))
    (d / "upcoming.json").write_text(json.dumps({"build_id": info["build_id"], "model": model_ref, "selected_model": selected,
                                                 "season": nw[0] if nw else None, "week": nw[1] if nw else None,
                                                 "games": rows}, indent=2))
    if nw:
        (d / "upcoming.md").write_text(upcoming_markdown(up, nw, model_ref))
    meta = {"build_id": info["build_id"], "model": model_ref, "champion_version": str(mv.version), "selected_model": selected,
            "source_run_id": src, "rows": int(len(gw)), "oos_rows": int(gw["out_of_sample"].sum()),
            "pending_rows": int((~gw["completed"]).sum()), "ties": int(gw["tie"].sum()),
            "model_params_sha256": mv.tags.get("params_sha256"), "predicted_data_sha256": fp,
            "train_data_sha256": mv.tags.get("train_data_sha256"), "stale": bool(stale),
            "market_missing_rows": int(gw["p_home_market"].isna().sum())}
    if stale:
        meta["stale_note"] = ("os dados atuais diferem dos usados no ajuste do champion: previsões de jogos futuros usam o "
                              "champion, mas o Elo atual é recalculado; rode `register wp_pregame`")
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    return d / "games_wp.parquet"


# ------------------------------------------------------------------ cartão

PURPOSE = ("Estimar, antes do kickoff, a probabilidade de o MANDANTE vencer cada jogo da NFL (empates fora) a partir só "
           "do histórico de resultados (Elo em pontos de margem calculado ANTES de cada jogo), do calendário (campo "
           "neutro, descanso, jogo de divisão) e do `team_asof`. Serve de ponto de comparação 'modelo × mercado': o "
           "mercado (moneyline de fechamento) é referência, nunca feature (H-D12).")


def limitations(info: dict) -> list:
    return [
        "`market` (probabilidade justa do moneyline de FECHAMENTO) é REFERÊNCIA fora da regra: incorpora lesões, clima, "
        "escalações e informação que só existe perto do kickoff e que o modelo não vê. O modelo não usa o mercado como "
        "feature (H-D12); bater os baselines não é bater o mercado.",
        "O modelo NÃO vê lesões, quarterback titular, clima, viagem nem troca de elenco: só placares, descanso, divisão e "
        "o estado `team_asof` (EPA e saldo de pontos). Por isso diferenças modelo − mercado grandes são, muitas vezes, "
        "informação que o mercado tem e o modelo não, não 'valor'.",
        "Elo calculado online em ordem de kickoff: o rating de cada jogo, inclusive de treino, usa só jogos de kickoff "
        "anterior. Jogos da mesma semana já disputados antes (quinta antes de domingo) entram no Elo dos seguintes, como "
        "na prática; o ajuste logístico, porém, só usa jogos de semanas anteriores (H-D13). O rating inicial de 2011 é 0 "
        "para todos (burn-in nas primeiras temporadas de treino).",
        "Hiperparâmetros fixos: os do Elo do `hub-ratings` (piloto 2013-2017), C da logística 1,0, σ de 13,5 do "
        "`elo_direct`, descanso limitado a ±7 dias. Nada foi ajustado em 2018+; ainda assim piloto e teste vêm da mesma liga.",
        f"Empates fora do alvo ({info['ties_excluded']} de {info['games_completed']} jogos completos), mas entram no Elo "
        f"(margem 0). Jogos em campo neutro ({info['neutral_games']} sem empate, incluindo Super Bowls) sem vantagem de casa; a taxa `home_rate` neles é 0,5.",
        "A vantagem de casa estimada vem de 2011 em diante e a taxa de vitória do mandante caiu depois de 2018: a tabela de "
        "calibração mostra o previsto acima do observado em 9 de 10 decis (taxa real do mandante 54,2% em 2018+ contra "
        "previsão média de 56,6%, cerca de +2,5 pp), ou seja, o modelo superestima o mandante de forma global. "
        "Os hiperparâmetros e o ajuste não foram corrigidos para isso (nada foi ajustado em 2018+).",
        "A previsão do modelo para um jogo `out_of_sample` é a da dobra semanal do backtest (treinada só com semanas "
        "anteriores). Os demais jogos completos levam o champion ajustado com TODOS os jogos: são DENTRO da amostra e não "
        "servem para avaliar. Jogos futuros usam o champion e o Elo atual.",
        "Calibração e acerto são pooled sobre 2018+ (poucos jogos por temporada: o erro de amostragem do log loss de uma "
        "temporada é grande, diferenças de ~0,005 entre modelos não são distinguíveis). Jogos futuros sem moneyline "
        "publicado ficam sem `market` e sem diferença.",
        "A seleção não é estatisticamente significativa: os 5 candidatos ficam a ~0,003 de log loss entre si e, num "
        "bootstrap por semana (revisão 4), a vantagem do selecionado sobre `elo_direct` (Elo convertido em probabilidade "
        "sem nenhum ajuste) e `logit_asof` tem IC 95% que inclui zero. Na prática, o Elo puro é equivalente.",
        "`model_code_sha256` deste cartão é o hash do conjunto de códigos do backtest; o do registro do modelo é o hash "
        "do arquivo do pyfunc. São grandezas diferentes.",
    ]


def _artifact(client, parent_run_id: str, model: str, name: str):
    try:
        return json.loads(Path(client.download_artifacts(parent_run_id, f"extras/{model}/{name}")).read_text())["rows"]
    except Exception:
        return None


def card_text(parent_run_id: str, info: dict, home=None) -> str:
    import card
    client = MlflowClient()
    run = client.get_run(parent_run_id)
    sel = run.data.tags.get("selected_model", "none")
    cfg = json.loads(Path(client.download_artifacts(parent_run_id, "config.json")).read_text())
    models = {m["name"]: m for m in cfg["models"]}
    extra = ["## Hiperparâmetros fixos", "", "| modelo | papel | parâmetros |", "|---|---|---|"]
    for n, m in sorted(models.items(), key=lambda kv: (kv[1]["role"], kv[0])):
        extra.append(f"| `{n}` | {m['role']} | `{json.dumps(m['params'], ensure_ascii=False, sort_keys=True)}` |")
    extra.append("")
    cols = [m for m in (sel if sel != "none" else None, "home_rate", "market") if m and m in models]
    series = {c: {r["season"]: r for r in (_artifact(client, parent_run_id, c, "by_season.json") or [])} for c in cols}
    if cols and all(series.values()):
        extra += ["## Log loss, Brier e acerto por temporada de teste", "",
                  "| temporada | n | " + " | ".join(f"`{c}` log loss | `{c}` brier | `{c}` acerto" for c in cols) + " |",
                  "|---|---|" + "---|---|---|" * len(cols)]
        for s in sorted(next(iter(series.values()))):
            n = series[cols[0]][s]["n"]
            extra.append(f"| {s} | {n} | " + " | ".join(
                f"{series[c][s]['log_loss']:.4f} | {series[c][s]['brier']:.4f} | {series[c][s]['accuracy']:.3f}" for c in cols) + " |")
        extra.append("")
    for c in [x for x in (sel if sel != "none" else None, "market") if x and x in models]:
        cal = _artifact(client, parent_run_id, c, "calibration.json")
        if cal:
            extra += [f"## Calibração por decis de probabilidade prevista: `{c}` (pooled, 2018+)", "",
                      "| decil | n | previsto médio | observado (mandante vence) | observado − previsto |", "|---|---|---|---|---|"]
            extra += [f"| {r['bin'] + 1} | {r['n']} | {r['pred_mean']:.3f} | {r['actual_mean']:.3f} | {r['diff']:+.3f} |" for r in cal]
            extra.append("")
    try:
        name = hubtrack.experiment_name(EXP_KEY)
        mv = client.get_model_version_by_alias(name, "champion")
        params, _mv = champion_params()
        if params["kind"] == "logit":
            extra += [f"## Coeficientes do selecionado (`{name}@{mv.version}`, ajustado em todos os jogos completos)", "",
                      "Log-odds de o mandante vencer, sem intercepto. `por unidade` está na unidade original da feature "
                      "(pontos de Elo, dias, 0/1, EPA); `padronizado` = por desvio-padrão do treino.", "",
                      "| feature | por unidade | desvio-padrão | padronizado |", "|---|---|---|---|"]
            extra += [f"| `{f}` | {params['coef_per_unit'][f]:+.4f} | {s:.4f} | {c:+.4f} |"
                      for f, s, c in zip(params["features"], params["scale"], params["coef"])]
            extra += ["", f"Jogos no ajuste: {params['n_train']} (descartados por feature nula: {params['n_dropped_null']}).", ""]
        extra += ["## Registro", "", f"- `{name}@champion` = versão {mv.version} (params_sha256 `{mv.tags.get('params_sha256')}`)", ""]
    except Exception:
        extra += ["## Registro", "", "- nenhuma versão `champion` registrada ainda.", ""]
    if home is not None:
        up = Path(home) / "predictions" / MODEL_KEY / info["build_id"] / "upcoming.md"
        if up.exists():
            extra += ["## Próxima semana", "", up.read_text().split("\n", 2)[2].strip(), ""]
    return RT._compact_splits(card.render_card(parent_run_id, PURPOSE, limitations(info), "\n".join(extra)), cfg["splits"])


# ------------------------------------------------------------------ comandos do CLI

def _data(args):
    from hubpaths import hub_home
    home = Path(args.home) if args.home else hub_home()
    allg, info = load_games(getattr(args, "build", None), home)
    return allg, modeled(allg), info, home


def _public_info(info: dict) -> dict:
    return {k: v for k, v in info.items() if k != "elo_state"}


def cmd_backtest(args):
    t0 = time.time()
    allg, df, info, _ = _data(args)
    print(f"dados: {_public_info(info)} ({time.time() - t0:.1f}s)")
    t1 = time.time()
    res = run(df, info["build_id"], force=args.force)
    print(f"backtest {'REUTILIZADO' if res.reused else 'concluído'} em {time.time() - t1:.1f}s; pai {res.parent_run_id}")
    print(f"selecionado: {res.selected_model}; bate baselines: {res.beats_baselines}")
    for name, d in sorted(res.pooled.items(), key=lambda kv: kv[1]["log_loss"]):
        print(f"  {name:12s} {res.roles[name]:9s} n={int(d['n'])} " + " ".join(f"{k}={v:.5f}" for k, v in d.items() if k != "n"))


def cmd_register(args):
    t0 = time.time()
    allg, df, info, _ = _data(args)
    out = register(df, info, args.run_id)
    print(f"registrado {out['name']} versão {out['version']} (modelo {out['selected_model']}, "
          f"params_sha256 {out['params_sha256'][:12]}) em {time.time() - t0:.1f}s")


def cmd_predict(args):
    t0 = time.time()
    allg, df, info, home = _data(args)
    path = predict_all(allg, df, info, home)
    print(f"{len(allg)} jogos -> {path} ({time.time() - t0:.1f}s)")


def cmd_card(args):
    allg, df, info, home = _data(args)
    if getattr(args, "run_id", None):
        parent = MlflowClient().get_run(args.run_id)
    else:
        parent = latest_parent(data_id=info["build_id"])
    text = card_text(parent.info.run_id, info, home)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"cartão em {out} (pai {parent.info.run_id})")
