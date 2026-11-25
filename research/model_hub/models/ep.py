"""H4 - Expected Points v1: probabilidade do próximo placar da metade (7 classes), na ótica do time com a posse.

Alvo `next_score_type` (feature store): TD, FG, SAFETY, OPP_TD, OPP_FG, OPP_SAFETY, NO_SCORE. EP = soma(p * pontos).
Linhas: `ep_eligible` (REG+POST), sem nulos nas colunas brutas do modelo (`ep_pyfunc.RAW_COLUMNS`), com alvo e com as
probabilidades do nflverse utilizáveis (para a comparação ser justa, linhas em que a referência não existe saem para
TODOS os modelos); as demais são excluídas e contadas por motivo (`load_data`). A receita de features mora SÓ em `model_code/ep_pyfunc.py`
(importado aqui por caminho), então treino e pyfunc usam o mesmo código.

Regra fixada antes: menor log_loss pooled entre os candidatos, precisando bater o melhor baseline (min_improvement=0).
`nflverse` é REFERÊNCIA (fora da regra): foi treinado com dados que incluem os anos de teste, portanto é otimista.
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

MODEL_KEY = "ep"
MODULE_PATH = Path(__file__).resolve()
CODE_PATH = MODULE_PATH.parent.parent / "model_code" / "ep_pyfunc.py"
_spec = importlib.util.spec_from_file_location("hub_ep_pyfunc", CODE_PATH)
pf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pf)

CLASSES = tuple(pf.CLASSES)
POINTS = np.asarray(pf.POINTS, dtype="float64")
NFLVERSE_COLUMNS = ["td_prob", "fg_prob", "safety_prob", "opp_td_prob", "opp_fg_prob", "opp_safety_prob",
                    "no_score_prob"]  # na ordem de CLASSES
TASK = B.Task(key=MODEL_KEY, target="next_score_type", kind="multiclass", classes=CLASSES,
              primary_metric="log_loss", metrics=("log_loss", "brier"))
TEST_SEASONS_FROM, FIRST_TRAIN_SEASON, SEED = 2018, 2011, 0
MAX_ITER, C = 2000, 1.0
MIN_CELL = 200

BASIC = ["yardline_100", "down_2", "down_3", "down_4", "log_ydstogo", "goal_to_go"]
STATE = BASIC + ["half_seconds_remaining", "posteam_timeouts_remaining", "defteam_timeouts_remaining",
                 "posteam_is_home", "is_overtime", "is_dome"]
HINGE = (STATE + [f"relu_yl_k{k}" for k in range(10, 100, 10)] + ["relu_t_120", "relu_t_300"]
         + [f"down{d}_x_yardline_100" for d in (2, 3, 4)] + ["t_x_yardline_100", "relu_t_300_x_yardline_100"])
FEATURE_SETS = {"logit_basic": BASIC, "logit_state": STATE, "logit_hinge": HINGE}
# v2 (recência): mesma família e features de `logit_hinge`; só muda o peso das amostras no fit (meia-vida em temporadas).
HALF_LIVES = {"logit_hinge_hl2": 2.0, "logit_hinge_hl4": 4.0}

LOAD_COLUMNS = ["game_id", "play_id", "season", "week", "season_type", "next_score_type", "next_score_points",
                *NFLVERSE_COLUMNS, "ep", *pf.RAW_COLUMNS]


class EPError(RuntimeError):
    pass


# ------------------------------------------------------------------ dados

def nflverse_valid_mask(df: pd.DataFrame) -> np.ndarray:
    """L-5: linhas em que a referência nflverse é utilizável (7 probabilidades finitas, >= 0, soma > 0). Linhas sem
    isso saem do conjunto de avaliação de TODOS os modelos, para a comparação ser sobre as mesmas jogadas."""
    P = df[NFLVERSE_COLUMNS].to_numpy(dtype="float64")
    with np.errstate(invalid="ignore"):
        return np.isfinite(P).all(axis=1) & (P >= 0).all(axis=1) & (P.sum(axis=1) > 0)


def load_data(build_id: str | None = None, home=None) -> tuple[pd.DataFrame, dict]:
    """Jogadas do modelo (pandas) e contagens. Das `ep_eligible`, saem (L-5/L-6, atribuição exclusiva na ordem):
    `null_raw_features` (nulo em coluna bruta ou ydstogo <= 0), `null_target` (sem alvo) e `invalid_nflverse_probs`
    (probabilidades da referência nulas/zero: excluídas de TODOS os modelos, não só da referência). `dropped_invalid_rows`
    é o total e `dropped_by_reason` o detalhamento."""
    import features
    import polars as pl
    from hubpaths import hub_home
    home = Path(home) if home else hub_home()
    bdir = features.resolve_build(build_id, home)
    plays = features.load_tables(bdir.name, home)["plays"]
    elig = plays.filter(pl.col("ep_eligible")).select(LOAD_COLUMNS).to_pandas()
    ok_raw = pf.usable_mask(elig)
    ok_target = elig["next_score_type"].notna().to_numpy()
    ok_nfl = nflverse_valid_mask(elig)
    by_reason = {"null_raw_features": int((~ok_raw).sum()),
                 "null_target": int((ok_raw & ~ok_target).sum()),
                 "invalid_nflverse_probs": int((ok_raw & ok_target & ~ok_nfl).sum())}
    df = elig[ok_raw & ok_target & ok_nfl].reset_index(drop=True)
    info = {"build_id": bdir.name, "ep_eligible": len(elig), "used": len(df),
            "dropped_invalid_rows": len(elig) - len(df), "dropped_by_reason": by_reason,
            "seasons": [int(df["season"].min()), int(df["season"].max())]}
    return df, info


def _target_index(df: pd.DataFrame) -> np.ndarray:
    idx = {c: i for i, c in enumerate(CLASSES)}
    return df["next_score_type"].map(idx).to_numpy(dtype="int64")


# ------------------------------------------------------------------ modelos

class _Fitted:
    def __init__(self, fn, js):
        self._fn, self._js = fn, js

    def predict(self, df):
        return self._fn(df)

    def to_json(self):
        return self._js


def _smoothed(counts: np.ndarray) -> np.ndarray:
    """Frequência com suavização de Laplace (+1 por classe): nenhuma classe recebe probabilidade zero."""
    c = np.asarray(counts, dtype="float64") + 1.0
    return c / c.sum(axis=-1, keepdims=True)


class FreqBaseline:
    """Baseline `freq`: frequência global das classes no treino (suavização de Laplace)."""
    name = "freq"

    def params(self):
        return {"smoothing": "laplace+1"}

    def columns(self):
        return ["next_score_type"]

    def fit(self, train):
        counts = np.bincount(_target_index(train), minlength=len(CLASSES))
        p = _smoothed(counts)
        return _Fitted(lambda df: np.tile(p, (len(df), 1)), {"probs": p.tolist(), "n": int(counts.sum())})


class FreqFieldDownBaseline:
    """Baseline `freq_field_down`: frequência por faixa de 10 jardas de `yardline_100` (0..9) × down (1..4).
    Célula com menos de `min_cell` jogadas usa a frequência da FAIXA; faixa com menos de `min_cell`, a global."""
    name = "freq_field_down"

    def __init__(self, min_cell: int = MIN_CELL):
        self.min_cell = min_cell

    def params(self):
        return {"min_cell": self.min_cell, "band_yards": 10, "smoothing": "laplace+1"}

    def columns(self):
        return ["next_score_type", "yardline_100", "down"]

    @staticmethod
    def _index(df):
        band = np.clip(np.floor(df["yardline_100"].to_numpy(dtype="float64") / 10.0), 0, 9).astype("int64")
        down = df["down"].to_numpy(dtype="float64").astype("int64")
        if ((down < 1) | (down > 4)).any():
            raise EPError("down fora de 1..4")
        return band, down - 1

    def fit(self, train):
        band, down = self._index(train)
        counts = np.zeros((10, 4, len(CLASSES)))
        np.add.at(counts, (band, down, _target_index(train)), 1)
        band_counts, glob = counts.sum(axis=1), counts.sum(axis=(0, 1))
        table = np.empty_like(counts)
        n_band_fb = n_glob_fb = 0
        for b in range(10):
            for d in range(4):
                if counts[b, d].sum() >= self.min_cell:
                    table[b, d] = _smoothed(counts[b, d])
                elif band_counts[b].sum() >= self.min_cell:
                    table[b, d] = _smoothed(band_counts[b]); n_band_fb += 1
                else:
                    table[b, d] = _smoothed(glob); n_glob_fb += 1
        return _Fitted(lambda df: table[self._index(df)], {
            "min_cell": self.min_cell, "cells_fallback_band": n_band_fb, "cells_fallback_global": n_glob_fb,
            "cell_n": counts.sum(axis=2).tolist()})


class NflverseReference:
    """Referência `nflverse`: as 7 probabilidades do PBP renormalizadas. Fora da regra de seleção: foi treinada com
    dados que incluem os anos de teste, portanto é otimista."""
    name = "nflverse"

    def params(self):
        return {"columns": NFLVERSE_COLUMNS, "normalize": "divide pela soma"}

    def columns(self):
        return list(NFLVERSE_COLUMNS)

    def fit(self, train):
        def predict(df):
            P = df[NFLVERSE_COLUMNS].to_numpy(dtype="float64")
            s = P.sum(axis=1, keepdims=True)
            if not np.isfinite(P).all() or (s <= 0).any():
                raise EPError("probabilidades do nflverse ausentes ou nulas")
            return P / s
        return _Fitted(predict, {"note": "sem ajuste"})


def recency_weights(seasons, half_life: float) -> np.ndarray:
    """Peso 0,5^((última temporada do treino - temporada)/meia-vida): a temporada mais recente pesa 1 e o peso
    cai pela metade a cada `half_life` temporadas. Usa só as temporadas do próprio treino (sem olhar o teste)."""
    s = np.asarray(seasons, dtype="float64")
    return np.power(0.5, (s.max() - s) / float(half_life))


class LogitEP:
    """Candidato: logística multinomial (sklearn, lbfgs) sobre as features de `ep_pyfunc`, padronizadas com média e
    desvio do TREINO (sem pesos). Exporta o formato `hub-ep-logit-v1`; a previsão usa `ep_pyfunc.probs_from_params`.

    `half_life` (v2): se dado, as amostras entram no fit com `recency_weights`, normalizados para média 1 (assim `C`
    mantém o mesmo significado do modelo sem pesos). Os pesos só afetam o ajuste: o JSON de parâmetros e o pyfunc
    são idênticos em formato."""

    def __init__(self, name: str, features, C: float = C, max_iter: int = MAX_ITER, half_life: float | None = None):
        self.name, self.features, self.C, self.max_iter = name, list(features), C, max_iter
        self.half_life = half_life

    def params(self):
        p = {"features": self.features, "C": self.C, "max_iter": self.max_iter, "solver": "lbfgs",
             "recipe_version": pf.RECIPE_VERSION}
        if self.half_life is not None:
            p |= {"half_life_seasons": self.half_life, "sample_weight": "0.5^((ultima_temporada_treino-temporada)/meia_vida), media 1"}
        return p

    def columns(self):
        return ["next_score_type", *pf.required_columns(self.features)]

    def fit(self, train):
        X = pf.feature_matrix(train, self.features)
        mean = X.mean(axis=0)
        scale = X.std(axis=0)
        scale[scale == 0] = 1.0
        y = _target_index(train)
        clf = LogisticRegression(C=self.C, solver="lbfgs", max_iter=self.max_iter)
        w = None
        if self.half_life is not None:
            w = recency_weights(train["season"], self.half_life)
            w = w / w.mean()
        clf.fit((X - mean) / scale, y, sample_weight=w)
        if list(clf.classes_) != list(range(len(CLASSES))):
            raise EPError(f"o treino não contém as 7 classes (presentes: {list(clf.classes_)})")
        n_iter = int(np.max(clf.n_iter_))
        if n_iter >= self.max_iter:
            raise EPError(f"{self.name}: lbfgs não convergiu em {self.max_iter} iterações")
        js = {"format": pf.FORMAT, "recipe_version": pf.RECIPE_VERSION, "kind": "multiclass", "model": self.name,
              "features": self.features, "classes": list(CLASSES), "points": pf.POINTS,
              "intercept": clf.intercept_.tolist(), "coef": clf.coef_.tolist(), "mean": mean.tolist(),
              "scale": scale.tolist(), "C": self.C, "max_iter": self.max_iter, "n_iter": n_iter,
              "n_train": int(len(train)), "half_life_seasons": self.half_life, "train_seasons": [int(train["season"].min()), int(train["season"].max())]}
        return _Fitted(lambda df: pf.probs_from_params(js, df), js)


def make_models(min_cell: int = MIN_CELL, max_iter: int = MAX_ITER):
    baselines = [FreqBaseline(), FreqFieldDownBaseline(min_cell)]
    candidates = [LogitEP(n, f, max_iter=max_iter) for n, f in FEATURE_SETS.items()]
    candidates += [LogitEP(n, HINGE, max_iter=max_iter, half_life=hl) for n, hl in HALF_LIVES.items()]
    return candidates, baselines, [NflverseReference()]


# ------------------------------------------------------------------ métricas extras e calibração

def expected_points(pred: np.ndarray) -> np.ndarray:
    return np.asarray(pred, dtype="float64") @ POINTS


def ep_mae(test: pd.DataFrame, pred) -> float:
    return M.mae(test["next_score_points"].to_numpy(dtype="float64"), expected_points(pred))


def ep_rmse(test: pd.DataFrame, pred) -> float:
    return M.rmse(test["next_score_points"].to_numpy(dtype="float64"), expected_points(pred))


def ep_bias(test: pd.DataFrame, pred) -> float:
    """Viés do EP = média(pontos reais - EP previsto), COM sinal (positivo = o modelo subestima). Mais perto de zero é
    melhor. Métrica extra do backtest: por split e pooled, reportada, FORA da regra de seleção."""
    return float(np.mean(test["next_score_points"].to_numpy(dtype="float64") - expected_points(pred)))


EXTRA_METRICS = {"ep_mae": ep_mae, "ep_rmse": ep_rmse, "ep_bias": ep_bias}
EXTRA_COLUMNS = ["next_score_points"]  # lidas pelas métricas extras e pela calibração (entram na impressão digital)


def calibration_artifacts(test: pd.DataFrame, pred) -> dict:
    """Calibração do EP por decis (quantis do EP previsto) sobre o teste pooled do modelo."""
    t = M.calibration_table(expected_points(pred), test["next_score_points"].to_numpy(dtype="float64"), 10, "quantile")
    return {"ep_calibration.json": {"bins": 10, "strategy": "quantile", "rows": t.to_dict("records")}}


# ------------------------------------------------------------------ backtest

def splits_for(df: pd.DataFrame) -> list:
    return B.walk_forward_seasons(range(TEST_SEASONS_FROM, int(df["season"].max()) + 1), FIRST_TRAIN_SEASON)


def code_paths() -> list:
    return [CODE_PATH, MODULE_PATH]


def run(df: pd.DataFrame, data_id: str, force: bool = False, min_cell: int = MIN_CELL,
        max_iter: int = MAX_ITER, splits=None) -> B.BacktestResult:
    candidates, baselines, references = make_models(min_cell, max_iter)
    return B.run_backtest(TASK, candidates, baselines, splits or splits_for(df), df,
                          B.SelectionRule(metric="log_loss", min_improvement=0.0), data_id, SEED, code_paths(),
                          force=force, references=references, extra_metrics=EXTRA_METRICS,
                          extra_artifacts=calibration_artifacts, data_columns=EXTRA_COLUMNS)


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
        raise EPError("nenhum backtest FINISHED" + (" que bateu os baselines" if only_beating else "")
                      + (f" para o build {data_id[:12]}" if data_id else "") + " em hub-ep"
                      + ("; rode `backtest ep` (ou passe --run-id)" if data_id else ""))
    return runs[0]


def per_split_metric(parent_run_id: str, metric: str = "log_loss") -> dict:
    """{modelo: {split: valor}} lido das filhas do pai."""
    client = MlflowClient()
    parent = client.get_run(parent_run_id)
    out: dict = {}
    for r in client.search_runs([parent.info.experiment_id], filter_string=f"tags.mlflow.parentRunId = '{parent_run_id}'",
                                max_results=5000):
        if metric in r.data.metrics:
            out.setdefault(r.data.tags["model_name"], {})[r.data.tags["split_name"]] = r.data.metrics[metric]
    return out


# ------------------------------------------------------------------ registro e previsão

def selected_model(selected: str, max_iter: int = MAX_ITER):
    candidates, _b, _r = make_models(max_iter=max_iter)
    match = [c for c in candidates if c.name == selected]
    if not match:
        raise EPError(f"modelo selecionado {selected!r} não é um candidato")
    return match[0]


def fit_selected(df: pd.DataFrame, selected: str, max_iter: int = MAX_ITER) -> dict:
    """Ajusta o modelo selecionado em todas as jogadas de `df` e devolve o JSON de parâmetros."""
    return selected_model(selected, max_iter).fit(df).to_json()


def register(df: pd.DataFrame, data_id: str, source_run_id: str | None = None) -> dict:
    import register as R
    src = source_run_id or latest_parent(only_beating=True).info.run_id
    run = MlflowClient().get_run(src)
    if run.data.tags.get("data_id") != data_id:
        raise EPError(f"o backtest {src[:8]} usou data_id {run.data.tags.get('data_id')!r}, o build atual é {data_id!r}: "
                      "rode `backtest ep` de novo")
    selected = run.data.tags.get("selected_model")
    model = selected_model(selected)
    params = model.fit(df).to_json()
    example = pf.raw_frame(df.head(5))
    out = R.register_json_model(MODEL_KEY, CODE_PATH, params, example, src, model_name=selected,
                                hyperparams=model.params(), train_data_sha256=B.data_fingerprint(df))
    out["selected_model"] = selected
    return out


def predict_all(df: pd.DataFrame, data_id: str, home, chunk: int = 200_000) -> Path:
    """Carrega `models:/hub-ep@champion`, prevê todas as jogadas de `df` e grava
    `HUB/predictions/ep/<build_id>/plays_ep.parquet` (+ meta.json).

    `in_sample` (L-3) é verdadeiro só se a impressão digital de `df` (`backtest.data_fingerprint`) for IGUAL à
    `train_data_sha256` do champion, isto é, se o champion foi ajustado exatamente com estas jogadas; senão é falso
    (o build mudou depois do ajuste: parte das jogadas pode ou não ter sido vista, e `register ep` refaz o ajuste).
    O meta.json guarda também `champion_version`, `source_run_id` e `build_id`."""
    import mlflow
    hubtrack.configure()
    client = MlflowClient()
    name = hubtrack.experiment_name(MODEL_KEY)
    mv = client.get_model_version_by_alias(name, "champion")
    model = mlflow.pyfunc.load_model(f"models:/{name}@champion")
    raw = pf.raw_frame(df)
    parts = [model.predict(raw.iloc[i:i + chunk]) for i in range(0, len(raw), chunk)]
    pred = pd.concat(parts, ignore_index=True)
    out = pd.concat([df[["game_id", "play_id"]].reset_index(drop=True), pred], axis=1)
    out["model_version"] = f"{name}@{mv.version}"
    fp = B.data_fingerprint(df)
    in_sample = mv.tags.get("train_data_sha256") == fp
    d = Path(home) / "predictions" / MODEL_KEY / data_id
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "plays_ep.parquet.tmp"
    out.to_parquet(tmp, index=False)
    os.replace(tmp, d / "plays_ep.parquet")
    meta = {"build_id": data_id, "model": f"{name}@{mv.version}", "champion_version": str(mv.version),
            "source_run_id": mv.tags.get("source_run_id"), "rows": len(out),
            "model_params_sha256": mv.tags.get("params_sha256"), "predicted_data_sha256": fp,
            "train_data_sha256": mv.tags.get("train_data_sha256"), "in_sample": bool(in_sample)}
    if not in_sample:
        meta["in_sample_note"] = ("os dados atuais diferem dos usados no ajuste do champion: não se pode afirmar "
                                  "que as previsões sejam dentro ou fora da amostra; rode `register ep` de novo")
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    return d / "plays_ep.parquet"


# ------------------------------------------------------------------ cartão

PURPOSE = ("Estimar, para cada jogada de ataque (1ª a 4ª descida), a probabilidade de cada um dos 7 desfechos do "
           "próximo placar da metade (TD, FG, safety do time com a posse; os três do adversário; nenhum) e o "
           "Expected Points (EP) = soma de probabilidade × pontos (+7, +3, +2, -7, -3, -2, 0). É a base de "
           "WP, 4º down e PROE no hub; não prevê o vencedor.")


def _reasons(by_reason: dict) -> str:
    names = {"null_raw_features": "nulo em coluna bruta", "null_target": "sem alvo",
             "invalid_nflverse_probs": "probabilidades do nflverse nulas ou zero"}
    return "; ".join(f"{names.get(k, k)}: {v}" for k, v in by_reason.items()) or "sem detalhe"


def limitations(info: dict, drift: str | None = None) -> list:
    return [
        "A referência `nflverse` foi treinada com dados que incluem as temporadas de teste (inclusive jogadas "
        "futuras ao split), portanto é OTIMISTA: serve de teto de comparação, não de adversário justo. Ela está fora "
        "da regra de seleção.",
        "O backtest é walk-forward por temporada (treino 2011..s-1, teste s, de 2018 até a última temporada); "
        "2026 está incompleta (até a última semana adquirida). As métricas são pooled sobre todos os testes.",
        "O alvo é o próximo evento de pontuação na MESMA metade (prorrogação = metade 3); PAT e conversão de 2 pts "
        "não são eventos. Fim de metade sem pontuação = NO_SCORE.",
        "Entram só jogadas `ep_eligible` (down 1-4, sem kickoff, PAT nem 2 pts). Linhas inválidas são excluídas, não "
        f"imputadas, para TODOS os modelos: {info['dropped_invalid_rows']} de {info['ep_eligible']} "
        f"({_reasons(info.get('dropped_by_reason', {}))}).",
        "Os modelos usam só situação de jogo (campo, descida, distância, tempo, timeouts, mando, prorrogação, teto "
        "fechado); não conhecem placar, força dos times nem clima. EP condicional ao placar fica para o WP.",
        "As previsões em lote (`predict ep`) usam o champion ajustado com TODAS as jogadas: são dentro da amostra. "
        "Para avaliação use o backtest.",
        "Baselines com suavização de Laplace (+1 por classe) para evitar probabilidade zero no log-loss.",
        drift or ("Deriva temporal: a pontuação média por jogada subiu de ~1,58 (2011) para ~2,10 (2026) e o treino "
                  "mistura épocas, o que tende a deixar o EP walk-forward abaixo do real; veja `ep_bias` e os candidatos de ponderação por recência."),
        "A referência `nflverse` pode incluir as temporadas de teste no seu treino (a versão do modelo nflverse não "
        "está fixada), então pode haver vazamento a favor dela, em grau desconhecido.",
        "Há uma descontinuidade de cerca de 0,3 ponto no EP na fronteira goal-to-go (1ª&gol na 10 vs 1ª&10 na 11), "
        "efeito da variável `goal_to_go` e do encaixe linear por partes; não é suavizada.",
    ]


def card_text(parent_run_id: str, info: dict) -> str:
    import card
    client = MlflowClient()
    run = client.get_run(parent_run_id)
    sel = run.data.tags.get("selected_model", "none")
    extra = []
    ps = per_split_metric(parent_run_id)
    base_names = [m for m in ps if m in ("freq", "freq_field_down")]
    best_base = min(base_names, key=lambda m: run.data.metrics[f"{m}.log_loss"]) if base_names else None
    cols = [m for m in (sel if sel != "none" else None, best_base, "nflverse") if m and m in ps]
    if cols:
        seasons = sorted(next(iter(ps.values())))
        extra += ["## Log-loss por temporada de teste", "",
                  "| split | " + " | ".join(f"`{c}`" for c in cols) + " |", "|---|" + "---|" * len(cols)]
        for s in seasons:
            extra.append(f"| {s} | " + " | ".join(f"{ps[c].get(s, float('nan')):.5f}" for c in cols) + " |")
        extra.append("")
    if sel != "none":
        try:
            cal = json.loads(Path(client.download_artifacts(parent_run_id, f"extras/{sel}/ep_calibration.json")).read_text())
            extra += [f"## Calibração do EP por decis (`{sel}`, pooled)", "",
                      "| decil | n | EP previsto (média) | pontos reais (média) | diferença |", "|---|---|---|---|---|"]
            for r in cal["rows"]:
                extra.append(f"| {r['bin'] + 1} | {r['n']} | {r['pred_mean']:.3f} | {r['actual_mean']:.3f} | {r['diff']:+.3f} |")
            extra.append("")
        except Exception as exc:  # artefato ausente em backtests antigos
            extra += [f"(calibração indisponível: {exc})", ""]
    drift = None
    hinge = [m for m in ("logit_hinge", *HALF_LIVES) if f"{m}.ep_bias" in run.data.metrics]
    if hinge:
        extra += ["## Viés do EP (média real - previsto; mais perto de zero é melhor)", "",
                  "| modelo | log_loss pooled | brier pooled | ep_mae pooled | ep_bias pooled |", "|---|---|---|---|---|"]
        for m in hinge:
            g = run.data.metrics.get
            extra.append(f"| `{m}` | {g(f'{m}.log_loss'):.5f} | {g(f'{m}.brier'):.5f} | {g(f'{m}.ep_mae'):.5f} | "
                         f"{g(f'{m}.ep_bias'):+.4f} |")
        extra.append("")
        bias = per_split_metric(parent_run_id, "ep_bias")
        extra += ["## Viés do EP por temporada de teste", "", "| split | " + " | ".join(f"`{m}`" for m in hinge) + " |",
                  "|---|" + "---|" * len(hinge)]
        for sp in sorted(next(iter(bias.values()))):
            extra.append(f"| {sp} | " + " | ".join(f"{bias[m].get(sp, float('nan')):+.4f}" for m in hinge) + " |")
        extra.append("")
        if sel != "none" and f"{sel}.ep_bias" in run.data.metrics:
            g = run.data.metrics
            drift = ("Deriva temporal: a pontuação média por jogada subiu de ~1,58 (2011) para ~2,10 (2026). O `logit_hinge` "
                     f"sem pesos tem viés pooled {g.get('logit_hinge.ep_bias', float('nan')):+.3f} (o EP fica abaixo do real); "
                     f"o selecionado (`{sel}`) tem {g[f'{sel}.ep_bias']:+.3f}, com candidatos de ponderação por recência (meia-vida 2 e 4 "
                     "temporadas) na disputa. O viés é métrica reportada, fora da regra de seleção.")
    try:
        name = hubtrack.experiment_name(MODEL_KEY)
        mv = client.get_model_version_by_alias(name, "champion")
        extra += ["## Registro", "", f"- `{name}@champion` = versão {mv.version} (params_sha256 `{mv.tags.get('params_sha256')}`)", ""]
    except Exception:
        extra += ["## Registro", "", "- nenhuma versão `champion` registrada ainda.", ""]
    return card.render_card(parent_run_id, PURPOSE, limitations(info, drift), "\n".join(extra))


# ------------------------------------------------------------------ comandos do CLI

def _data(args):
    from hubpaths import hub_home
    home = Path(args.home) if args.home else hub_home()
    df, info = load_data(getattr(args, "build", None), home)
    return df, info, home


def cmd_backtest(args):
    t0 = time.time()
    df, info, _ = _data(args)
    print(f"dados: {info} ({time.time() - t0:.1f}s)")
    t1 = time.time()
    res = run(df, info["build_id"], force=args.force)
    print(f"backtest {'REUTILIZADO' if res.reused else 'concluído'} em {time.time() - t1:.1f}s; pai {res.parent_run_id}")
    print(f"selecionado: {res.selected_model}; bate baselines: {res.beats_baselines}")
    for name, d in sorted(res.pooled.items(), key=lambda kv: kv[1]["log_loss"]):
        print(f"  {name:16s} {res.roles[name]:9s} n={int(d['n'])} " + " ".join(f"{k}={v:.5f}" for k, v in d.items() if k != "n"))


def cmd_register(args):
    t0 = time.time()
    df, info, _ = _data(args)
    out = register(df, info["build_id"], args.run_id)
    print(f"registrado {out['name']} versão {out['version']} (modelo {out['selected_model']}, "
          f"params_sha256 {out['params_sha256'][:12]}) em {time.time() - t0:.1f}s")


def cmd_predict(args):
    t0 = time.time()
    df, info, home = _data(args)
    path = predict_all(df, info["build_id"], home)
    print(f"{len(df)} jogadas -> {path} ({time.time() - t0:.1f}s)")


def cmd_card(args):
    df, info, _ = _data(args)
    if getattr(args, "run_id", None):
        parent = MlflowClient().get_run(args.run_id)  # explícito: aceito, o cartão mostra o data_id usado
    else:  # L-3: o pai tem de ser do build atual
        parent = latest_parent(data_id=info["build_id"])
    text = card_text(parent.info.run_id, info)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"cartão em {out} (pai {parent.info.run_id})")
