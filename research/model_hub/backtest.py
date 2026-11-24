"""Backtest temporal com baselines obrigatórios, registrado no MLflow (experimento `hub-<task.key>`).

Estrutura no MLflow: uma execução PAI (role=parent) e uma FILHA por (modelo, split) (role=candidate|baseline)
com as métricas do split e `n`. As métricas AGREGADAS por modelo são "pooled": as previsões de todos os splits de
teste são concatenadas e a métrica é calculada UMA vez sobre o conjunto todo (não é média das médias dos splits;
splits maiores pesam mais). Ficam no pai como `<modelo>.<métrica>` e `<modelo>.n`.

Regras que tornam o resultado auditável:
- splits declarados como dados (`Split`) e guarda de vazamento (`LeakageError`) antes de qualquer `fit`;
- `SelectionRule` fixada antes e gravada no pai; um candidato só é selecionado se bater o melhor baseline;
- `config_sha256` identifica a configuração; reexecutar a mesma configuração devolve o pai FINISHED existente.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
import traceback
import warnings
from pathlib import Path
from dataclasses import dataclass, field
from typing import Protocol, Sequence

import numpy as np
import pandas as pd
from mlflow import MlflowClient

import hubtrack
import metrics as M

LAST_WEEK = 99  # semana-sentinela: "até o fim da temporada"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
PROB_TOL = 1e-6
#: Código do próprio harness que define o resultado (métricas, split/seleção, rastreio): entra SEMPRE no hash de
#: código do config (L-2), para que mudar ``metrics.py`` ou ``backtest.py`` reexecute os backtests.
HARNESS_FILES = (Path(__file__).resolve(), Path(M.__file__).resolve(), Path(hubtrack.__file__).resolve())


class LeakageError(ValueError):
    """O treino de um split não é estritamente anterior ao teste."""


class BacktestError(RuntimeError):
    """Configuração ou previsão inválida no backtest."""


# ------------------------------------------------------------------ tarefa e protocolo de modelo

@dataclass(frozen=True)
class Task:
    """Tarefa de previsão. `classes` (multiclasse): rótulos na ordem das colunas de `predict`."""
    key: str
    target: str
    kind: str  # binary | multiclass | regression
    primary_metric: str
    metrics: tuple = ()
    classes: tuple | None = None

    def __post_init__(self):
        object.__setattr__(self, "metrics", tuple(self.metrics) or (self.primary_metric,))
        if self.classes is not None:
            object.__setattr__(self, "classes", tuple(self.classes))
        if self.kind not in ("binary", "multiclass", "regression"):
            raise BacktestError(f"kind inválido: {self.kind!r}")
        if self.kind == "multiclass" and (not self.classes or len(self.classes) < 2):
            raise BacktestError("tarefa multiclasse exige `classes`")
        if self.kind != "multiclass" and self.classes is not None:
            raise BacktestError("`classes` só vale para tarefas multiclasse")
        if self.primary_metric not in self.metrics:
            raise BacktestError("primary_metric deve estar em metrics")
        for m in self.metrics:
            if not M.applicable(m, self.kind):
                raise BacktestError(f"métrica {m!r} não se aplica a tarefas {self.kind!r}")

    def to_dict(self) -> dict:
        return {"key": self.key, "target": self.target, "kind": self.kind, "classes": list(self.classes or []),
                "primary_metric": self.primary_metric, "metrics": list(self.metrics)}


class FittedModel(Protocol):
    def predict(self, df: pd.DataFrame) -> np.ndarray: ...  # n (binário/regressão) ou n×k (multiclasse)
    def to_json(self) -> dict: ...  # parâmetros aprendidos, JSON puro


class Model(Protocol):
    name: str
    def params(self) -> dict: ...  # hiperparâmetros, JSON puro
    def fit(self, train_df: pd.DataFrame) -> FittedModel: ...
    # Opcional: def columns(self) -> list[str]  # colunas dos dados que o modelo usa (fit e predict). Sem ele, a
    # impressão digital dos dados cobre TODAS as colunas (mais conservador: qualquer mudança reexecuta).


# ------------------------------------------------------------------ splits

@dataclass(frozen=True)
class Split:
    """Split temporal. Treino: `first_train_season <= season` e (season, week) <= `train_until` (inclusive).

    `test`: lista de temporadas (`[2023, 2024]`) OU janela de semanas `(season, week_from, week_to)` (tupla de 3)."""
    name: str
    train_until: tuple
    test: tuple | list
    first_train_season: int = 0

    def __post_init__(self):
        object.__setattr__(self, "train_until", tuple(self.train_until))
        if isinstance(self.test, list):
            object.__setattr__(self, "test", tuple(self.test))
            object.__setattr__(self, "_window", False)
        elif isinstance(self.test, tuple) and len(self.test) == 3:
            object.__setattr__(self, "_window", True)
        else:
            raise BacktestError("test deve ser lista de temporadas ou tupla (season, week_from, week_to)")
        if not NAME_RE.match(self.name):
            raise BacktestError(f"nome de split inválido: {self.name!r}")

    @property
    def is_window(self) -> bool:
        return self._window

    def test_start(self) -> tuple:
        return (self.test[0], self.test[1]) if self.is_window else (min(self.test), 0)

    def to_dict(self) -> dict:
        return {"name": self.name, "train_until": list(self.train_until), "first_train_season": self.first_train_season,
                "test": list(self.test), "test_kind": "weeks" if self.is_window else "seasons"}


def walk_forward_seasons(test_seasons: Sequence[int], first_train_season: int) -> list[Split]:
    """Um split por temporada de teste: treina em [first_train_season, s-1] e testa em s."""
    out = []
    for s in sorted(test_seasons):
        if s - 1 < first_train_season:
            raise BacktestError(f"temporada de teste {s} não tem treino desde {first_train_season}")
        out.append(Split(f"s{s}", (s - 1, LAST_WEEK), [s], first_train_season))
    return out


def walk_forward_weeks(season: int, weeks: Sequence[int], first_train_season: int) -> list[Split]:
    """Um split por semana `w` de `season`: treina até a semana w-1 (ou até a temporada anterior, se w=1)."""
    out = []
    for w in sorted(weeks):
        until = (season, w - 1) if w > 1 else (season - 1, LAST_WEEK)
        out.append(Split(f"s{season}w{w:02d}", until, (season, w, w), first_train_season))
    return out


def _require_columns(df: pd.DataFrame, cols) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise BacktestError(f"colunas ausentes nos dados: {missing}")


def split_masks(data: pd.DataFrame, split: Split) -> tuple[np.ndarray, np.ndarray]:
    """Máscaras booleanas (treino, teste) do split sobre `data`, depois da guarda de ordem das fronteiras."""
    _require_columns(data, ("season", "week"))
    if not split.train_until < split.test_start():
        raise LeakageError(
            f"split {split.name}: treino até {split.train_until} não é anterior ao início do teste {split.test_start()}")
    s, w = data["season"], data["week"]
    tu_s, tu_w = split.train_until
    train_mask = (s >= split.first_train_season) & ((s < tu_s) | ((s == tu_s) & (w <= tu_w)))
    if split.is_window:
        ts, wf, wt = split.test
        test_mask = (s == ts) & (w >= wf) & (w <= wt)
    else:
        test_mask = s.isin(list(split.test))
    return train_mask.to_numpy(), test_mask.to_numpy()


def split_frames(data: pd.DataFrame, split: Split) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Treino e teste do split, depois da guarda de vazamento. Levanta LeakageError ou BacktestError (vazio)."""
    train_mask, test_mask = split_masks(data, split)
    train, test = data[train_mask].reset_index(drop=True), data[test_mask].reset_index(drop=True)
    if train.empty or test.empty:
        raise BacktestError(f"split {split.name}: treino ({len(train)}) ou teste ({len(test)}) vazio")
    key = lambda d: d["season"].astype("int64") * 1000 + d["week"].astype("int64")  # noqa: E731
    if key(train).max() >= key(test).min():
        raise LeakageError(f"split {split.name}: há linha de treino não anterior ao teste por (season, week)")
    if "kickoff_utc" in data.columns:
        k_tr, k_te = pd.to_datetime(train["kickoff_utc"]).max(), pd.to_datetime(test["kickoff_utc"]).min()
        if pd.notna(k_tr) and pd.notna(k_te) and k_tr >= k_te:
            raise LeakageError(f"split {split.name}: kickoff_utc do treino ({k_tr}) não é anterior ao do teste ({k_te})")
    return train, test


# ------------------------------------------------------------------ regra de seleção

@dataclass(frozen=True)
class SelectionRule:
    """Regra fixada antes do backtest: o candidato com a melhor métrica pooled (`metric`, padrão a primária da
    tarefa; direção vem de `metrics.METRICS`), desde que seja melhor que o melhor baseline por mais de
    `min_improvement` (em unidades da métrica). Empates: nome em ordem alfabética."""
    metric: str | None = None
    min_improvement: float = 0.0

    def resolve(self, task: Task) -> dict:
        metric = self.metric or task.primary_metric
        if metric not in task.metrics:
            raise BacktestError(f"métrica da regra {metric!r} não está em task.metrics")
        d = M.direction(metric)
        text = (f"{'min' if d == 'min' else 'max'} pooled {metric} entre candidatos; precisa ser melhor que o melhor "
                f"baseline por mais de {self.min_improvement:g}")
        return {"metric": metric, "direction": d, "min_improvement": self.min_improvement, "text": text}


def apply_rule(rule: dict, pooled: dict, candidates: Sequence[str], baselines: Sequence[str]) -> tuple[str, bool]:
    """(modelo selecionado ou "none", bate_baselines)."""
    metric = rule["metric"]
    sign = 1.0 if rule["direction"] == "min" else -1.0  # normaliza para "menor é melhor"
    absent = [m for m in (*candidates, *baselines) if metric not in pooled[m]]
    if absent:
        raise BacktestError(f"métrica da regra {metric!r} indefinida no pooled de {absent}")
    score = lambda m: sign * pooled[m][metric]  # noqa: E731
    best_cand = sorted(candidates, key=lambda m: (score(m), m))[0]
    best_base = min(score(b) for b in baselines)
    beats = bool(score(best_cand) < best_base - rule["min_improvement"])
    return (best_cand if beats else "none"), beats


# ------------------------------------------------------------------ execução

@dataclass
class BacktestResult:
    parent_run_id: str
    config_sha256: str
    selected_model: str
    beats_baselines: bool
    pooled: dict = field(default_factory=dict)  # modelo -> {métrica: valor, "n": n}
    roles: dict = field(default_factory=dict)  # modelo -> "candidate" | "baseline"
    reused: bool = False


def _targets(task: Task, df: pd.DataFrame) -> np.ndarray:
    col = df[task.target]
    if col.isna().any():
        raise BacktestError(f"alvo {task.target!r} com valores ausentes")
    if task.kind == "regression":
        return col.to_numpy(dtype="float64")
    if task.kind == "binary":
        if not col.isin([0, 1]).all():
            raise BacktestError("alvo binário deve conter só 0 e 1")
        return col.to_numpy(dtype="int64")
    index = {c: i for i, c in enumerate(task.classes)}
    unknown = set(col.unique()) - set(index)
    if unknown:
        raise BacktestError(f"alvo com classes fora de task.classes: {sorted(map(str, unknown))}")
    return col.map(index).to_numpy(dtype="int64")


def _check_pred(task: Task, pred, n: int, who: str) -> np.ndarray:
    pred = np.asarray(pred, dtype="float64")
    shape = (n, len(task.classes)) if task.kind == "multiclass" else (n,)
    if pred.shape != shape:
        raise BacktestError(f"{who}: previsão com forma {pred.shape}, esperado {shape}")
    if not np.isfinite(pred).all():
        raise BacktestError(f"{who}: previsão com valores não finitos")
    if task.kind != "regression" and (pred.min() < 0 or pred.max() > 1):
        raise BacktestError(f"{who}: probabilidade fora de [0, 1]")
    if task.kind == "multiclass" and not np.allclose(pred.sum(axis=1), 1.0, atol=PROB_TOL):
        raise BacktestError(f"{who}: linhas de probabilidade não somam 1")
    return pred


def _metrics_for(task: Task, y, pred, test=None, extra_metrics=None, where: str = "") -> dict:
    """Métricas do conjunto. Métrica indefinida (`M.UndefinedMetric`, p. ex. AUC com classe única no alvo) é OMITIDA
    do resultado com um `warnings.warn` (não derruba o backtest); métrica ausente no pooled da regra de seleção é
    erro explícito em `apply_rule`."""
    out = {}
    for m in task.metrics:
        try:
            out[m] = M.compute(m, task.kind, y, pred)
        except M.UndefinedMetric as exc:
            warnings.warn(f"{where}: métrica {m!r} omitida ({exc})", stacklevel=2)
    for name, fn in (extra_metrics or {}).items():
        out[name] = float(fn(test, pred))
    return out


def _check_models(candidates, baselines, references=()) -> None:
    if not candidates:
        raise BacktestError("é preciso ao menos um candidato")
    if not baselines:
        raise BacktestError("baseline é obrigatório: nenhum candidato é avaliado sem ao menos um baseline")
    names = [m.name for m in (*baselines, *references, *candidates)]
    if len(set(names)) != len(names):
        raise BacktestError(f"nomes de modelo repetidos: {names}")
    for n in names:
        if not NAME_RE.match(n):
            raise BacktestError(f"nome de modelo inválido: {n!r} (use letras, dígitos, _ e -)")


def data_fingerprint(data: pd.DataFrame, columns=None) -> str:
    """sha256 do CONTEÚDO de `data` nas `columns` (todas, se None), independente da ordem das linhas e do índice.

    Cada linha vira um hash (`pd.util.hash_pandas_object(index=False)`, colunas em ordem alfabética); os hashes são
    ordenados (preserva duplicatas) e entram no sha256 junto com os nomes das colunas."""
    cols = sorted(data.columns) if columns is None else sorted(set(columns))
    _require_columns(data, cols)
    sub = data[cols]
    try:
        h = pd.util.hash_pandas_object(sub, index=False)
    except TypeError:  # células não hasheáveis (listas): usa a representação textual
        h = pd.util.hash_pandas_object(sub.astype(str), index=False)
    d = hashlib.sha256()
    d.update(json.dumps(cols).encode())
    d.update(np.sort(h.to_numpy(dtype="uint64")).tobytes())
    return d.hexdigest()


def _model_columns(models, base_cols, extra_cols) -> list | None:
    """União das colunas usadas, ou None (= todas) se algum modelo não declara `columns()` ou há extras sem colunas."""
    cols = set(base_cols) | set(extra_cols or ())
    for m in models:
        fn = getattr(m, "columns", None)
        if not callable(fn):
            return None
        cols |= set(fn())
    return sorted(cols)


def used_data_fingerprint(data: pd.DataFrame, splits, task: Task, models, data_columns=None) -> str:
    """Impressão digital das linhas usadas por QUALQUER split (treino ou teste) e das colunas season, week,
    kickoff_utc (se existir), alvo e as declaradas pelos modelos (`columns()`; `data_columns` cobre as métricas
    extras). Alguma sem `columns()` (ou `data_columns=None` com extras) -> todas as colunas."""
    used = np.zeros(len(data), dtype=bool)
    for s in splits:
        tr, te = split_masks(data, s)
        used |= tr | te
    base = ["season", "week", task.target] + (["kickoff_utc"] if "kickoff_utc" in data.columns else [])
    cols = _model_columns(models, base, data_columns)
    return data_fingerprint(data[used], cols)


def collect_code_paths(models, extra_paths=()) -> list[Path]:
    """Arquivos-fonte das classes dos modelos (`inspect.getsourcefile`) mais `extra_paths`, sem duplicatas.

    Só o arquivo da classe: código auxiliar em outros módulos deve ir em `model_code_paths`. Classe sem arquivo
    localizável (módulo fora de `sys.modules`, `exec`) levanta `BacktestError` em vez de ficar fora do hash."""
    out: dict = {}
    for m in models:
        try:
            f = inspect.getsourcefile(type(m))
        except TypeError:
            f = None
        if not f:  # não pode haver buraco silencioso no hash do código
            raise BacktestError(f"não achei o arquivo-fonte do modelo {getattr(m, 'name', m)!r} "
                                f"({type(m).__module__}.{type(m).__qualname__}); o módulo precisa estar em sys.modules")
        out[Path(f).resolve()] = None
    for p in extra_paths:
        out[Path(p).resolve()] = None
    return list(out)


def make_config(task, candidates, baselines, splits, data_id, seed, rule, model_code_sha256,
                references=(), extra_metrics=None, has_artifacts=False, data_sha256=None) -> dict:
    """Configuração canônica que define o `config_sha256` (qualquer mudança aqui reexecuta o backtest).

    `data_sha256` é a impressão digital dos dados usados (`used_data_fingerprint`); `data_id` é só o rótulo.
    `references` (papel "reference") e `extras` só entram na configuração quando existem, para não mudar o hash
    de backtests sem eles."""
    models = [{"name": m.name, "role": role, "params": m.params()}
              for role, group in (("baseline", baselines), ("candidate", candidates), ("reference", references))
              for m in group]
    cfg = {"task": task.to_dict(), "models": sorted(models, key=lambda d: (d["role"], d["name"])),
           "splits": [s.to_dict() for s in splits], "data_id": str(data_id), "data_sha256": data_sha256, "seed": seed,
           "selection_rule": rule, "model_code_sha256": model_code_sha256,
           "harness_version": hubtrack.HARNESS_VERSION}
    if extra_metrics or has_artifacts:
        cfg["extras"] = {"metrics": sorted(extra_metrics or {}), "artifacts": bool(has_artifacts)}
    return cfg


def find_finished_parent(experiment_id: str, config_sha256: str):
    runs = MlflowClient().search_runs(
        [experiment_id],
        filter_string=f"tags.role = 'parent' and tags.config_sha256 = '{config_sha256}' "
                      "and attributes.status = 'FINISHED'",
        order_by=["attributes.start_time DESC"], max_results=1)
    return runs[0] if runs else None


def load_result(parent_run_id: str, reused: bool = False) -> BacktestResult:
    """Reconstrói o resultado a partir do pai no MLflow."""
    client = MlflowClient()
    run = client.get_run(parent_run_id)
    pooled: dict = {}
    for k, v in run.data.metrics.items():
        if "." in k:
            model, metric = k.split(".", 1)
            pooled.setdefault(model, {})[metric] = v
    roles = {}
    for r in client.search_runs([run.info.experiment_id], filter_string=f"tags.mlflow.parentRunId = '{parent_run_id}'",
                                max_results=5000):
        roles[r.data.tags["model_name"]] = r.data.tags["role"]
    t = run.data.tags
    return BacktestResult(parent_run_id, t["config_sha256"], t.get("selected_model", "none"),
                          t.get("beats_baselines") == "true", pooled, roles, reused)


def run_backtest(task: Task, candidates: Sequence, baselines: Sequence, splits: Sequence[Split], data: pd.DataFrame,
                 selection_rule: SelectionRule, data_id: str, seed: int, model_code_paths: Sequence = (),
                 force: bool = False, references: Sequence = (), extra_metrics: dict | None = None,
                 extra_artifacts=None, data_columns: Sequence | None = None) -> BacktestResult:
    """Roda o backtest e registra no MLflow. Regra não satisfeita -> pai FINISHED com `selected_model=none`.

    `references`: modelos avaliados e reportados (papel "reference") mas FORA da regra de seleção e do teste de
    baseline. `extra_metrics`: {nome: fn(test_df, pred) -> float}, calculadas por split (filhas) e pooled (pai,
    sobre os testes concatenados). `extra_artifacts`: fn(test_df, pred) -> {arquivo: JSON puro}, chamada por
    modelo sobre os testes concatenados; grava `extras/<modelo>/<arquivo>` no pai. O código dessas funções deve
    estar em `model_code_paths` (entra no hash); `data_columns` lista as colunas que elas leem (sem isso, a
    impressão digital dos dados cobre todas as colunas).

    Idempotência: `config_sha256` cobre a configuração, o CONTEÚDO dos dados usados (`data_sha256`) e o código dos
    modelos (arquivos das classes, derivados por `inspect`, mais `model_code_paths`). Os testes de splits não podem
    compartilhar linhas (o pooled contaria em dobro): `BacktestError`.

    Se já existe pai FINISHED com o mesmo `config_sha256` e `force=False`, devolve-o sem reexecutar
    (`reused=True`). Erro no meio -> pai (e filhas abertas) FAILED e a exceção sobe."""
    references = tuple(references)
    _check_models(candidates, baselines, references)
    if not splits:
        raise BacktestError("nenhum split declarado")
    _require_columns(data, ("season", "week", task.target))
    rule = selection_rule.resolve(task)
    # Guarda de vazamento ANTES de qualquer fit ou escrita no MLflow.
    frames = [(s, *split_frames(data, s)) for s in splits]
    test_hits = np.zeros(len(data), dtype=int)
    for s in splits:
        test_hits += split_masks(data, s)[1]
    if (test_hits > 1).any():
        raise BacktestError(f"splits com testes sobrepostos: {int((test_hits > 1).sum())} linhas em mais de um teste "
                            "(o pooled contaria em dobro)")

    all_models = (*baselines, *references, *candidates)
    if (extra_metrics or extra_artifacts is not None) and data_columns is None:
        fp_models = [object()]  # sem columns(): impressão digital sobre todas as colunas
    else:
        fp_models = all_models
    data_sha = used_data_fingerprint(data, splits, task, fp_models, data_columns)
    code_sha = hubtrack.sha256_files(collect_code_paths(all_models, [*model_code_paths, *HARNESS_FILES]))
    config = make_config(task, candidates, baselines, splits, data_id, seed, rule, code_sha, references, extra_metrics,
                         extra_artifacts is not None, data_sha)
    keep_test = bool(extra_metrics) or extra_artifacts is not None
    config_sha = hubtrack.sha256_json(config)
    hubtrack.configure()
    exp_id = hubtrack.experiment(task.key)
    if not force:
        existing = find_finished_parent(exp_id, config_sha)
        if existing is not None:
            return load_result(existing.info.run_id, reused=True)

    def tags_for(role, **extra):
        return hubtrack.build_tags(task.key, role, code_sha, data_id, config_sha, rule["text"], seed, **extra)

    parent_id = hubtrack.start_run(task.key, tags_for("parent"), run_name=f"{task.key} backtest {config_sha[:8]}")
    open_children: list[str] = []
    try:
        hubtrack.log_params(parent_id, {
            "task_key": task.key, "target": task.target, "kind": task.kind, "classes": ",".join(map(str, task.classes or ())),
            "primary_metric": task.primary_metric, "metrics": ",".join(task.metrics), "data_id": data_id, "data_sha256": data_sha, "seed": seed,
            "n_splits": len(splits), "candidates": ",".join(m.name for m in candidates),
            "baselines": ",".join(m.name for m in baselines), "selection_rule": rule["text"],
            "references": ",".join(m.name for m in references), "extra_metrics": ",".join(sorted(extra_metrics or {}))})
        hubtrack.log_json(parent_id, config, "config.json")
        pooled_parts: dict[str, list] = {}
        roles = ({m.name: "baseline" for m in baselines} | {m.name: "candidate" for m in candidates}
                 | {m.name: "reference" for m in references})
        for model in (*baselines, *references, *candidates):
            role = roles[model.name]
            params = model.params()
            for split, train, test in frames:
                y = _targets(task, test)
                child = hubtrack.start_run(
                    task.key, tags_for(role, model_name=model.name, split_name=split.name),
                    run_name=f"{model.name} | {split.name}", parent_run_id=parent_id)
                open_children.append(child)
                fitted = model.fit(train)
                pred = _check_pred(task, fitted.predict(test), len(test), f"{model.name}/{split.name}")
                pooled_parts.setdefault(model.name, []).append((y, pred, test if keep_test else None))
                hubtrack.log_params(child, {"train_until": str(split.train_until), "test": str(split.test),
                                            "params_sha256": hubtrack.sha256_json(params)})
                hubtrack.log_metrics(child, {"n": len(test), "n_train": len(train),
                                             **_metrics_for(task, y, pred, test, extra_metrics, f"{model.name}/{split.name}")})
                hubtrack.log_json(child, params, "params.json")
                hubtrack.log_json(child, fitted.to_json(), "fitted.json")
                hubtrack.finish_run(child)
                open_children.remove(child)
        pooled: dict = {}
        for name, parts in pooled_parts.items():
            y = np.concatenate([p[0] for p in parts])
            pred = np.concatenate([p[1] for p in parts], axis=0)
            test_all = pd.concat([p[2] for p in parts], ignore_index=True) if keep_test else None
            pooled[name] = {"n": len(y), **_metrics_for(task, y, pred, test_all, extra_metrics, f"{name}/pooled")}
            if extra_artifacts is not None:
                for fname, obj in extra_artifacts(test_all, pred).items():
                    hubtrack.log_json(parent_id, obj, f"extras/{name}/{fname}")
        hubtrack.log_metrics(parent_id, {f"{n}.{k}": v for n, d in pooled.items() for k, v in d.items()})
        selected, beats = apply_rule(rule, pooled, [m.name for m in candidates], [m.name for m in baselines])
        hubtrack.set_tags(parent_id, {"selected_model": selected, "beats_baselines": str(beats).lower()})
        hubtrack.finish_run(parent_id)
        return BacktestResult(parent_id, config_sha, selected, beats, pooled, roles, False)
    except BaseException as exc:
        for c in open_children:
            hubtrack.finish_run(c, "FAILED")
        hubtrack.set_tags(parent_id, {"error": "".join(traceback.format_exception_only(type(exc), exc))[:1000]})
        hubtrack.finish_run(parent_id, "FAILED")
        raise
