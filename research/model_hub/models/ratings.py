"""H6 - Ratings de times: margem prevista do mandante (`result` = pontos do mandante - pontos do visitante).

Tarefa de regressão (rmse primária, mae e acerto do vencedor). Jogos: completos (REG+POST), temporadas 2011+, em
`games` do feature store, com o `team_asof` (ewm4) do mandante e do visitante antes do jogo. Splits: um por SEMANA de
cada temporada de teste (2018..última), cada um treinado com todos os jogos anteriores a ela (H-D13). Toda a matemática
dos ratings mora em `model_code/ratings_pyfunc.py` (funções puras, reutilizáveis pela H7).

Candidatos (hiperparâmetros FIXOS, declarados abaixo; o piloto walk-forward 2013-2017, reproduzível em
`pilots/ratings_pilot.py` e que só lê jogos até 2017, os confirma só em parte, veja o parágrafo seguinte; nada foi
ajustado em 2018+): `elo`, `ridge_decay_hl17`, `ridge_decay_hl34` (meias-vidas em semanas de calendário),
`asof_linear`. Baselines: `zero`, `hfa`. Referência (FORA da regra): `market` = `spread_line` de fechamento
(positiva = mandante favorito, conferida contra a moneyline), conhecida antes do kickoff e usada só para comparar.

O que o piloto mostra (`pilots/ratings_pilot_results.md`): no Elo, k=0,07 é o do ótimo; hfa=2,0 foi fixado a priori
e o ótimo do piloto é 2,5; o ótimo global da grade é k=0,07, hfa=2,5, teto 40, reversão 0,5 (RMSE 13,2399), e a
configuração usada (hfa 2,0, teto 28, reversão 1/3) fica em 9º de 180 (13,2508, diferença de ~0,011, ruído). Com hfa=2,5,
teto 28 e reversão 1/3 é o 2º. No ridge o piloto prefere λ=5 com meia-vida 17 (13,2975); a meia-vida 34 é o 2º (13,3203).
Os hiperparâmetros NÃO foram trocados depois de ver o teste (isso seria escolher pelo teste).

Regra fixada antes: menor RMSE pooled entre os candidatos, precisando bater o melhor baseline (min_improvement=0).
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

import backtest as B
import hubtrack
import metrics as M

MODEL_KEY = "ratings"
MODULE_PATH = Path(__file__).resolve()
CODE_PATH = MODULE_PATH.parent.parent / "model_code" / "ratings_pyfunc.py"
_spec = importlib.util.spec_from_file_location("hub_ratings_pyfunc", CODE_PATH)
pf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pf)

TASK = B.Task(key=MODEL_KEY, target="result", kind="regression", primary_metric="rmse", metrics=("rmse", "mae"))
TEST_SEASONS_FROM, FIRST_TRAIN_SEASON, SEED = 2018, 2011, 0
HISTORY_FROM_SEASON = 2012  # histórico semanal walk-forward: precisa de pelo menos uma temporada anterior

# Hiperparâmetros fixos (comparados com o piloto 2013-2017 em pilots/ratings_pilot.py; ver docstring do módulo).
ELO = {"k": 0.07, "hfa": 2.0, "cap": 28.0, "reversion": 1.0 / 3.0}
RIDGE_LAMBDA = 5.0
RIDGE_HALFLIVES = {"ridge_decay_hl17": 17.0, "ridge_decay_hl34": 34.0}

GAME_COLUMNS = ["game_id", "season", "week", "kickoff_utc", "home_team", "away_team", "result", "neutral"]
ASOF_COLUMNS = [f"{s}_{f}" for f in pf.ASOF_FEATURES for s in ("home", "away")]
LOAD_COLUMNS = [*GAME_COLUMNS, "spread_line", *ASOF_COLUMNS]
EXTRA_COLUMNS = ["result"]  # lidas pelas métricas extras e pelos artefatos (entram na impressão digital)


class RatingsError(RuntimeError):
    pass


# ------------------------------------------------------------------ dados

def load_data(build_id: str | None = None, home=None) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """(jogos, info, team_asof longo). Jogos completos 2011+ (pandas) com o `team_asof` de cada lado, e contagens. O `team_asof` entra pelo par
    (game_id, time) do PRÓPRIO jogo: é o estado antes dele e nunca de outro jogo."""
    import features
    from hubpaths import hub_home
    home = Path(home) if home else hub_home()
    bdir = features.resolve_build(build_id, home)
    tables = features.load_tables(bdir.name, home)
    games = tables["games"].to_pandas()
    asof = tables["team_asof"].to_pandas()
    games = games[games["season"] >= FIRST_TRAIN_SEASON].copy()
    done = games["completed"].astype(bool) & games["result"].notna()
    pending = games[~games["completed"].astype(bool)]
    next_week = None
    if len(pending):
        nxt = pending.sort_values(["season", "week"]).iloc[0]
        next_week = [int(nxt["season"]), int(nxt["week"])]
    g = games[done].copy()
    g["neutral"] = g["location"].eq("Neutral")
    for side in ("home", "away"):
        a = asof[["game_id", "team", *[f for f in pf.ASOF_FEATURES]]].rename(
            columns={"team": f"{side}_team", **{f: f"{side}_{f}" for f in pf.ASOF_FEATURES}})
        g = g.merge(a, on=["game_id", f"{side}_team"], how="left", validate="one_to_one")
    g = g.sort_values(["kickoff_utc", "game_id"], kind="mergesort").reset_index(drop=True)
    info = {"build_id": bdir.name, "games_completed": int(len(g)), "seasons": [int(g["season"].min()), int(g["season"].max())],
            "neutral_games": int(g["neutral"].sum()), "games_null_asof": int(g[ASOF_COLUMNS].isna().any(axis=1).sum()),
            "games_null_spread": int(g["spread_line"].isna().sum()), "next_week": next_week,
            "excluded_not_completed": int((~done).sum())}
    return g[LOAD_COLUMNS], info, asof


def asof_state(asof: pd.DataFrame, cutoff) -> pd.DataFrame:
    """Estado `team_asof` de cada time no seu primeiro jogo com kickoff ESTRITAMENTE depois de `cutoff` (= o estado
    com todos os jogos até `cutoff`). Times sem jogo depois (ou com estado nulo) ficam de fora."""
    a = asof[pd.to_datetime(asof["kickoff_utc"], utc=True) > pd.Timestamp(cutoff)].copy()
    a = a.sort_values(["kickoff_utc", "game_id"], kind="mergesort").drop_duplicates("team", keep="first")
    a = a.dropna(subset=list(pf.ASOF_FEATURES))
    return a.set_index("team")[list(pf.ASOF_FEATURES)]


# ------------------------------------------------------------------ modelos

class _Fitted:
    def __init__(self, fn, js):
        self._fn, self._js = fn, js

    def predict(self, df):
        return self._fn(df)

    def to_json(self):
        return self._js


class ZeroBaseline:
    """Baseline `zero`: margem prevista 0 (sem vantagem de casa)."""
    name = "zero"

    def params(self):
        return {"margin": 0.0}

    def columns(self):
        return ["result"]

    def fit(self, train):
        return _Fitted(lambda df: np.zeros(len(df)), {"margin": 0.0})


class HfaBaseline:
    """Baseline `hfa`: média da margem do mandante nos jogos de campo NÃO neutro do treino; 0 em campo neutro."""
    name = "hfa"

    def params(self):
        return {"estimate": "média de result nos jogos não neutros do treino", "neutral": 0.0}

    def columns(self):
        return ["result", "neutral"]

    def fit(self, train):
        nn = ~train["neutral"].to_numpy(dtype=bool)
        if not nn.any():
            raise RatingsError("treino sem jogo em campo não neutro")
        h = float(train["result"].to_numpy(dtype="float64")[nn].mean())
        return _Fitted(lambda df: np.where(df["neutral"].to_numpy(dtype=bool), 0.0, h), {"hfa": h, "n": int(nn.sum())})


class MarketReference:
    """Referência `market`: `spread_line` de fechamento (positiva = mandante favorito, isto é, margem esperada do
    mandante). Fora da regra de seleção: é informação de mercado, não um modelo do hub."""
    name = "market"

    def params(self):
        return {"column": "spread_line", "sign": "positiva = mandante favorito = margem esperada do mandante"}

    def columns(self):
        return ["spread_line"]

    def fit(self, train):
        def predict(df):
            s = df["spread_line"].to_numpy(dtype="float64")
            if not np.isfinite(s).all():
                raise RatingsError("spread_line ausente em jogo a prever")
            return s
        return _Fitted(predict, {"note": "sem ajuste"})


def _rating_fitted(params: dict) -> _Fitted:
    return _Fitted(lambda df: pf.predict_margin(params, df["home_team"], df["away_team"],
                                                df["neutral"].to_numpy(dtype=bool), df["season"].to_numpy()), params)


class EloModel:
    """Candidato `elo`: Elo em pontos de margem (k, teto da margem, regressão de 1/3 entre temporadas, hfa fixo)."""

    def __init__(self, name: str = "elo", k: float = ELO["k"], hfa: float = ELO["hfa"], cap: float = ELO["cap"],
                 reversion: float = ELO["reversion"]):
        self.name, self.k, self.hfa, self.cap, self.reversion = name, k, hfa, cap, reversion

    def params(self):
        return {"kind": "elo", "k": self.k, "hfa": self.hfa, "cap": self.cap, "reversion": self.reversion,
                "init": 0.0, "order": "kickoff_utc"}

    def columns(self):
        return [c for c in GAME_COLUMNS if c != "week"]

    def fit(self, train):
        return _rating_fitted(pf.elo_fit(train, self.k, self.hfa, self.cap, self.reversion))


class RidgeDecayModel:
    """Candidato `ridge_decay_*`: mínimos quadrados ponderados com ridge e peso 0.5^(idade/meia-vida)."""

    def __init__(self, name: str, halflife_weeks: float, lam: float = RIDGE_LAMBDA):
        self.name, self.halflife, self.lam = name, halflife_weeks, lam

    def params(self):
        return {"kind": "ridge_decay", "halflife_weeks": self.halflife, "lambda": self.lam,
                "age_unit": "semanas de calendário até o último jogo do treino", "hfa": "estimado, sem penalidade"}

    def columns(self):
        return [c for c in GAME_COLUMNS if c != "week"]

    def fit(self, train):
        return _rating_fitted(pf.ridge_fit(train, self.halflife, self.lam))


class AsofLinearModel:
    """Candidato `asof_linear`: OLS da margem nas diferenças do `team_asof` (ewm4 EPA ofensivo, EPA defensivo
    sofrido, saldo de pontos) mais mando. Cada jogo usa só o `team_asof` do próprio jogo (colunas da linha).
    `asof` (tabela team_asof longa) só serve para exportar os ratings 'de agora' (estado antes do próximo jogo)."""
    name = "asof_linear"

    def __init__(self, asof: pd.DataFrame | None = None):
        self.asof = asof

    def params(self):
        return {"kind": "asof_linear", "features": list(pf.ASOF_FEATURES), "intercept": False,
                "terms": "hfa*(1-neutro) + b . (x_mandante - x_visitante)", "nulls": "linhas de treino com asof nulo saem"}

    def columns(self):
        return [*[c for c in GAME_COLUMNS if c != "week"], *ASOF_COLUMNS]

    def fit(self, train):
        state = None
        if self.asof is not None:
            state = asof_state(self.asof, pd.to_datetime(train["kickoff_utc"], utc=True).max())
        p = pf.asof_fit(train, state)
        return _Fitted(lambda df: pf.predict_asof(p, df), p)


def make_models(asof: pd.DataFrame | None = None):
    baselines = [ZeroBaseline(), HfaBaseline()]
    candidates = [EloModel(), *[RidgeDecayModel(n, h) for n, h in RIDGE_HALFLIVES.items()], AsofLinearModel(asof)]
    return candidates, baselines, [MarketReference()]


# ------------------------------------------------------------------ métricas extras e artefatos

def winner_acc(test: pd.DataFrame, pred) -> float:
    """Acerto do vencedor: sinal da margem prevista = sinal da real, EMPATES REAIS FORA; previsão exatamente 0 vale 0,5."""
    y = test["result"].to_numpy(dtype="float64")
    p = np.asarray(pred, dtype="float64")
    keep = y != 0
    if not keep.any():
        raise RatingsError("winner_acc: sem jogos decididos no conjunto")
    hit = np.where(p[keep] == 0, 0.5, (np.sign(p[keep]) == np.sign(y[keep])).astype(float))
    return float(hit.mean())


EXTRA_METRICS = {"winner_acc": winner_acc}


def by_season_artifacts(test: pd.DataFrame, pred) -> dict:
    """Métricas exatas por temporada de teste (pooled das semanas), por modelo, em `by_season.json`."""
    rows = []
    for s, idx in test.groupby("season").groups.items():
        t = test.loc[idx]
        p = np.asarray(pred)[test.index.get_indexer(idx)]
        y = t["result"].to_numpy(dtype="float64")
        rows.append({"season": int(s), "n": int(len(t)), "rmse": M.rmse(y, p), "mae": M.mae(y, p),
                     "winner_acc": winner_acc(t, p)})
    return {"by_season.json": {"rows": rows}}


# ------------------------------------------------------------------ backtest

def splits_for(df: pd.DataFrame, block: int = 1) -> list:
    """Splits semanais 2018..última temporada de `df` (uma semana por split; `block` > 1 agrupa semanas consecutivas
    e é uma saída para backtests lentos). Cada split treina com tudo anterior à sua primeira semana."""
    out = []
    for s in range(TEST_SEASONS_FROM, int(df["season"].max()) + 1):
        weeks = sorted(int(w) for w in df.loc[df["season"] == s, "week"].unique())
        if block == 1:
            out += B.walk_forward_weeks(s, weeks, FIRST_TRAIN_SEASON)
            continue
        for i in range(0, len(weeks), block):
            a, b = weeks[i], weeks[min(i + block, len(weeks)) - 1]
            until = (s, a - 1) if a > 1 else (s - 1, B.LAST_WEEK)
            out.append(B.Split(f"s{s}w{a:02d}-{b:02d}", until, (s, a, b), FIRST_TRAIN_SEASON))
    return out


def code_paths() -> list:
    return [CODE_PATH, MODULE_PATH]


def run(df: pd.DataFrame, data_id: str, force: bool = False, splits=None, asof=None) -> B.BacktestResult:
    candidates, baselines, references = make_models(asof)
    return B.run_backtest(TASK, candidates, baselines, splits or splits_for(df), df,
                          B.SelectionRule(metric="rmse", min_improvement=0.0), data_id, SEED, code_paths(),
                          force=force, references=references, extra_metrics=EXTRA_METRICS,
                          extra_artifacts=by_season_artifacts, data_columns=EXTRA_COLUMNS)


def latest_parent(only_beating: bool = False, data_id: str | None = None):
    hubtrack.configure()
    exp_id = hubtrack.experiment(MODEL_KEY)
    flt = "tags.role = 'parent' and attributes.status = 'FINISHED'"
    if only_beating:
        flt += " and tags.beats_baselines = 'true'"
    if data_id is not None:
        flt += f" and tags.data_id = '{data_id}'"
    runs = MlflowClient().search_runs([exp_id], filter_string=flt, order_by=["attributes.start_time DESC"], max_results=1)
    if not runs:
        raise RatingsError("nenhum backtest FINISHED" + (" que bateu os baselines" if only_beating else "")
                           + (f" para o build {data_id[:12]}" if data_id else "") + " em hub-ratings"
                           + ("; rode `backtest ratings` (ou passe --run-id)" if data_id else ""))
    return runs[0]


# ------------------------------------------------------------------ registro, histórico e previsão

def selected_model(selected: str, asof=None):
    candidates, _b, _r = make_models(asof)
    match = [c for c in candidates if c.name == selected]
    if not match:
        raise RatingsError(f"modelo selecionado {selected!r} não é um candidato")
    return match[0]


def fit_selected(df: pd.DataFrame, selected: str, asof=None) -> dict:
    """Ajusta o modelo selecionado em todos os jogos completos de `df` e devolve o JSON de parâmetros."""
    return selected_model(selected, asof).fit(df).to_json()


def register(df: pd.DataFrame, data_id: str, source_run_id: str | None = None, asof=None) -> dict:
    import register as R
    src = source_run_id or latest_parent(only_beating=True).info.run_id
    run_ = MlflowClient().get_run(src)
    if run_.data.tags.get("data_id") != data_id:
        raise RatingsError(f"o backtest {src[:8]} usou data_id {run_.data.tags.get('data_id')!r}, o build atual é "
                           f"{data_id!r}: rode `backtest ratings` de novo")
    selected = run_.data.tags.get("selected_model")
    model = selected_model(selected, asof)
    params = model.fit(df).to_json()
    out = R.register_json_model(MODEL_KEY, CODE_PATH, params, pf.input_frame(df.head(5)), src, model_name=selected,
                                hyperparams=model.params(), train_data_sha256=B.data_fingerprint(df))
    out["selected_model"] = selected
    return out


def history_pairs(df: pd.DataFrame, next_week=None, first_season: int = HISTORY_FROM_SEASON) -> list:
    """(season, week) de `df` a partir de `first_season`, mais a próxima semana ainda sem resultado (`next_week`)."""
    pairs = {(int(s), int(w)) for s, w in zip(df["season"], df["week"]) if s >= first_season}
    if next_week is not None and next_week[0] >= first_season:
        pairs.add((int(next_week[0]), int(next_week[1])))
    return sorted(pairs)


def ratings_history(df: pd.DataFrame, model, pairs) -> pd.DataFrame:
    """Rating de cada time ANTES de cada semana, walk-forward: para a semana (s, w) o modelo é ajustado só com os jogos
    de `df` estritamente anteriores a (s, w) (a regressão de início de temporada do Elo vale quando s é nova).
    Nunca usa jogo da própria semana nem posterior, então não é dentro da amostra."""
    season, week = df["season"].to_numpy(), df["week"].to_numpy()
    rows = []
    for s, w in pairs:
        hist = df[(season < s) | ((season == s) & (week < w))]
        if hist.empty:
            raise RatingsError(f"sem histórico antes de {(s, w)}")
        params = model.fit(hist).to_json()
        for team, r in sorted(pf.team_ratings(params, s).items()):
            rows.append((s, w, team, r, len(hist)))
    return pd.DataFrame(rows, columns=["season", "week", "team", "rating", "n_games_train"]).astype(
        {"season": "int64", "week": "int64", "rating": "float64", "n_games_train": "int64"})


def champion_params(home=None):
    """(params.json do champion, versão do modelo registrado)."""
    import tempfile

    import mlflow
    hubtrack.configure()
    name = hubtrack.experiment_name(MODEL_KEY)
    mv = MlflowClient().get_model_version_by_alias(name, "champion")
    with tempfile.TemporaryDirectory(prefix="hub-ratings-") as tmp:
        local = mlflow.artifacts.download_artifacts(artifact_uri=f"models:/{name}@champion", dst_path=tmp)
        found = [Path(r) / f for r, _d, fs in os.walk(local) for f in fs if f == "params.json"]
        if len(found) != 1:
            raise RatingsError(f"params.json do champion: {len(found)} arquivos")
        return json.loads(found[0].read_text()), mv


def predict_all(df: pd.DataFrame, data_id: str, home, next_week=None, asof=None) -> Path:
    """Grava `HUB/predictions/ratings/<build_id>/ratings_history.parquet` (rating de cada time ANTES de cada semana,
    walk-forward com o modelo e os hiperparâmetros do champion) e `current_ratings.json` (ranking dos ratings do
    champion registrado). `meta.json` guarda versão, hashes e `stale`: verdadeiro se os dados atuais diferem dos
    usados no ajuste do champion (então `current_ratings.json` pode estar atrasado; rode `register ratings`)."""
    params, mv = champion_params()
    name = hubtrack.experiment_name(MODEL_KEY)
    selected = mv.tags.get("selected_model")
    model = selected_model(selected, asof)
    if hubtrack.sha256_json(model.params()) != mv.tags.get("hyperparams_sha256"):
        raise RatingsError("hiperparâmetros do código diferem dos do champion: rode `register ratings` de novo")
    hist = ratings_history(df, model, history_pairs(df, next_week))
    cur = sorted(params["ratings"].items(), key=lambda kv: (-kv[1], kv[0]))
    fp = B.data_fingerprint(df)
    stale = mv.tags.get("train_data_sha256") != fp
    d = Path(home) / "predictions" / MODEL_KEY / data_id
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "ratings_history.parquet.tmp"
    hist.to_parquet(tmp, index=False)
    os.replace(tmp, d / "ratings_history.parquet")
    current = {"build_id": data_id, "model": f"{name}@{mv.version}", "selected_model": selected, "kind": params["kind"],
               "as_of": params["as_of"], "last_season": params["last_season"], "n_games": params["n_games"],
               "hfa": params["hfa"], "stale": bool(stale),
               "ratings": [{"rank": i + 1, "team": t, "rating": r} for i, (t, r) in enumerate(cur)]}
    (d / "current_ratings.json").write_text(json.dumps(current, indent=2))
    meta = {"build_id": data_id, "model": f"{name}@{mv.version}", "champion_version": str(mv.version),
            "source_run_id": mv.tags.get("source_run_id"), "rows": len(hist), "model_params_sha256": mv.tags.get("params_sha256"),
            "predicted_data_sha256": fp, "train_data_sha256": mv.tags.get("train_data_sha256"), "stale": bool(stale),
            "history_walk_forward": True, "history_from_season": HISTORY_FROM_SEASON}
    if stale:
        meta["stale_note"] = ("os dados atuais diferem dos usados no ajuste do champion; o histórico é recalculado "
                              "walk-forward, mas `current_ratings.json` vem do champion: rode `register ratings`")
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    return d / "ratings_history.parquet"


# ------------------------------------------------------------------ cartão

PURPOSE = ("Estimar a margem do mandante (pontos do mandante menos pontos do visitante) antes de cada jogo a partir "
           "só do histórico de resultados (e, em um candidato, do `team_asof`), e dar a cada time um rating em "
           "pontos: margem prevista = vantagem de casa × (1 - campo neutro) + rating(mandante) - rating(visitante). "
           "Os ratings alimentam o WP pré-jogo (H7) e o ranking de forças; o modelo não usa o mercado.")


def limitations(info: dict) -> list:
    return [
        "`market` (spread de fechamento) é REFERÊNCIA fora da regra: incorpora lesões, clima, informação privada e a "
        "própria decisão do mercado até o fechamento, que nenhum candidato tem. Bater o baseline não é bater o mercado; "
        "o RMSE do mercado é o teto realista de comparação.",
        "A linha de fechamento é conhecida antes do kickoff, mas só no fim da semana; um modelo com ela como feature "
        "viraria cópia dela (H-D12), por isso ela não entra nos candidatos.",
        "Backtest walk-forward SEMANAL (H-D13): cada split treina com todos os jogos anteriores à semana e testa nela, de "
        f"2018 até a última semana completa de {info['seasons'][1]}; a temporada corrente está incompleta. As métricas "
        "são pooled sobre todos os testes. Jogos da mesma semana não treinam uns aos outros (inclusive quinta antes "
        "de domingo).",
        "Hiperparâmetros fixos declarados no cartão; nada foi ajustado em 2018+ nem trocado depois de ver o teste. O piloto "
        "walk-forward 2013-2017 (`pilots/ratings_pilot.py`, só jogos até 2017) confirma só em parte: k=0,07 é o do ótimo; "
        "hfa=2,0 foi fixado a priori e o ótimo do piloto é 2,5 (a configuração usada fica em 9º de 180 no Elo, RMSE ~0,011 "
        "acima do ótimo; teto 40 e reversão 0,5 vencem a combinação 28 e 1/3 no ótimo global); no ridge o piloto prefere "
        "λ=5 com meia-vida 17, e a meia-vida 34 é a 2ª. Piloto e teste vêm da mesma liga: não é validação independente.",
        "Elo e ridge só conhecem placares: não sabem de quarterback lesionado, descanso, clima ou troca de elenco "
        "(a regressão de 1/3 entre temporadas e o decaimento temporal são o único tratamento da entressafra). A vantagem "
        "de casa do Elo é um valor fixo de 2,0 pontos, escolhido a priori (o ótimo do piloto 2013-2017 é 2,5).",
        "Campo neutro vem de `location == 'Neutral'` (83 jogos, incluindo Super Bowls); nele não há vantagem de casa. "
        "Jogos de pós-temporada entram no treino e no teste como os demais.",
        "O `asof_linear` usa o `team_asof` de cada jogo (estado ANTES dele, só jogos com kickoff estritamente anterior); "
        "as linhas de treino com `team_asof` nulo (o primeiro jogo de cada time em 2011) saem do ajuste.",
        "Acerto do vencedor: empates reais saem; previsão exatamente 0 conta 0,5. Time sem rating (fora do histórico) "
        "levanta erro em vez de receber um valor arbitrário.",
        "Os ratings do `asof_linear` são b·estado antes do PRÓXIMO jogo de cada time; só ele os tem com esse "
        "significado. O histórico `ratings_history.parquet` é walk-forward (nunca dentro da amostra), mas o "
        "`current_ratings.json` vem do champion ajustado com todos os jogos completos.",
    ]


def _by_season(client, parent_run_id: str, model: str):
    try:
        return json.loads(Path(client.download_artifacts(parent_run_id, f"extras/{model}/by_season.json")).read_text())["rows"]
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
    base_names = [m for m in models if models[m]["role"] == "baseline"]
    best_base = min(base_names, key=lambda m: run.data.metrics[f"{m}.rmse"]) if base_names else None
    cols = [m for m in (sel if sel != "none" else None, best_base, "market") if m and m in models]
    series = {c: {r["season"]: r for r in (_by_season(client, parent_run_id, c) or [])} for c in cols}
    if cols and all(series.values()):
        seasons = sorted(next(iter(series.values())))
        extra += ["## RMSE e acerto por temporada de teste", "",
                  "| temporada | n | " + " | ".join(f"`{c}` rmse | `{c}` acerto" for c in cols) + " |",
                  "|---|---|" + "---|---|" * len(cols)]
        for s in seasons:
            n = series[cols[0]][s]["n"]
            extra.append(f"| {s} | {n} | " + " | ".join(f"{series[c][s]['rmse']:.3f} | {series[c][s]['winner_acc']:.3f}"
                                                        for c in cols) + " |")
        extra.append("")
    if home is not None:
        cur_path = Path(home) / "predictions" / MODEL_KEY / info["build_id"] / "current_ratings.json"
        if cur_path.exists():
            cur = json.loads(cur_path.read_text())
            rs = cur["ratings"]
            extra += [f"## Ratings atuais (`{cur['model']}`, {cur['selected_model']}, dados até {cur['as_of'][:10]})", "",
                      f"Vantagem de casa estimada/fixa: {cur['hfa']:.2f} pontos. Pontos acima de um time médio (0).", "",
                      "| posição | time | rating |", "|---|---|---|"]
            extra += [f"| {r['rank']} | {r['team']} | {r['rating']:+.2f} |" for r in rs[:5]]
            extra += ["| … | … | … |"] + [f"| {r['rank']} | {r['team']} | {r['rating']:+.2f} |" for r in rs[-5:]]
            extra.append("")
    try:
        name = hubtrack.experiment_name(MODEL_KEY)
        mv = client.get_model_version_by_alias(name, "champion")
        extra += ["## Registro", "", f"- `{name}@champion` = versão {mv.version} (params_sha256 `{mv.tags.get('params_sha256')}`)", ""]
    except Exception:
        extra += ["## Registro", "", "- nenhuma versão `champion` registrada ainda.", ""]
    return _compact_splits(card.render_card(parent_run_id, PURPOSE, limitations(info), "\n".join(extra)), cfg["splits"])


def _compact_splits(text: str, splits: list) -> str:
    """Troca a tabela de uma linha por split (centenas, no backtest semanal) por um resumo: o `card.render_card` é
    genérico e não conhece o tamanho dos splits semanais."""
    head, _, rest = text.partition("## Splits\n")
    _, sep, tail = rest.partition("\nExecuções filhas")
    if not sep:
        return text
    seasons = sorted({s["test"][0] for s in splits if s["test_kind"] == "weeks"})
    summary = (f"\nUm split por semana ({len(splits)} no total), de {splits[0]['name']} a {splits[-1]['name']} "
               f"(temporadas {seasons[0]}-{seasons[-1]}): cada split treina com todos os jogos desde "
               f"{splits[0]['first_train_season']} anteriores à semana testada e testa nessa semana "
               "(H-D13). Os splits completos estão em `config.json` no pai do MLflow.\n")
    return head + "## Splits\n" + summary + "\nExecuções filhas" + tail


# ------------------------------------------------------------------ comandos do CLI

def _data(args):
    from hubpaths import hub_home
    home = Path(args.home) if args.home else hub_home()
    df, info, asof = load_data(getattr(args, "build", None), home)
    return df, info, asof, home


def cmd_backtest(args):
    t0 = time.time()
    df, info, asof, _ = _data(args)
    print(f"dados: {info} ({time.time() - t0:.1f}s)")
    t1 = time.time()
    res = run(df, info["build_id"], force=args.force, asof=asof)
    print(f"backtest {'REUTILIZADO' if res.reused else 'concluído'} em {time.time() - t1:.1f}s; pai {res.parent_run_id}")
    print(f"selecionado: {res.selected_model}; bate baselines: {res.beats_baselines}")
    for name, d in sorted(res.pooled.items(), key=lambda kv: kv[1]["rmse"]):
        print(f"  {name:18s} {res.roles[name]:9s} n={int(d['n'])} " + " ".join(f"{k}={v:.5f}" for k, v in d.items() if k != "n"))


def cmd_register(args):
    t0 = time.time()
    df, info, asof, _ = _data(args)
    out = register(df, info["build_id"], args.run_id, asof)
    print(f"registrado {out['name']} versão {out['version']} (modelo {out['selected_model']}, "
          f"params_sha256 {out['params_sha256'][:12]}) em {time.time() - t0:.1f}s")


def cmd_predict(args):
    t0 = time.time()
    df, info, asof, home = _data(args)
    path = predict_all(df, info["build_id"], home, info["next_week"], asof)
    print(f"{len(df)} jogos -> {path} ({time.time() - t0:.1f}s)")


def cmd_card(args):
    df, info, asof, home = _data(args)
    if getattr(args, "run_id", None):
        parent = MlflowClient().get_run(args.run_id)
    else:
        parent = latest_parent(data_id=info["build_id"])
    text = card_text(parent.info.run_id, info, home)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"cartão em {out} (pai {parent.info.run_id})")
