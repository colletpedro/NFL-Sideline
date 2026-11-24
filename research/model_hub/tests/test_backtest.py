import sys

import numpy as np
import pandas as pd
import pytest
from mlflow import MlflowClient

import backtest as B
import hubtrack
from toy_models import FreqModel, LogitModel, MeanModel, synth

CLASSES = ("a", "b", "c")
RULE = B.SelectionRule()


@pytest.fixture
def data():
    return synth()


def mc_task():
    return B.Task("toymc", "y3", "multiclass", "log_loss", ("log_loss", "brier"), CLASSES)


def run_mc(data, force=False, candidates=None, **kw):
    return B.run_backtest(
        mc_task(), candidates or [LogitModel("y3", CLASSES)], [FreqModel("y3", CLASSES, "freq")],
        B.walk_forward_seasons([2021, 2022], 2019), data, RULE, "synth-v1", 7, force=force, **kw)


# ---------------------------------------------------------------- splits e vazamento

def test_walk_forward_constructors():
    s = B.walk_forward_seasons([2022, 2021], 2019)
    assert [x.name for x in s] == ["s2021", "s2022"] and s[0].train_until == (2020, B.LAST_WEEK)
    w = B.walk_forward_weeks(2022, [1, 3], 2019)
    assert w[0].train_until == (2021, B.LAST_WEEK) and w[0].test == (2022, 1, 1)
    assert w[1].train_until == (2022, 2)
    with pytest.raises(B.BacktestError):
        B.walk_forward_seasons([2019], 2019)


def test_split_frames_are_strictly_before(data):
    for split in B.walk_forward_seasons([2021, 2022], 2019) + B.walk_forward_weeks(2022, [1, 4, 8], 2019):
        tr, te = B.split_frames(data, split)
        assert (tr.season * 100 + tr.week).max() < (te.season * 100 + te.week).min()
        assert tr.kickoff_utc.max() < te.kickoff_utc.min()


def test_leaked_split_is_refused_before_training(data):
    class Boom(LogitModel):
        def fit(self, train):
            raise AssertionError("não deveria treinar")
    same_season = B.Split("vaza", (2021, B.LAST_WEEK), [2021], 2019)
    with pytest.raises(B.LeakageError):
        B.run_backtest(mc_task(), [Boom("y3", CLASSES)], [FreqModel("y3", CLASSES)], [same_season], data, RULE, "d", 1)
    overlapping_weeks = B.Split("sobrepoe", (2022, 5), (2022, 5, 6), 2019)
    with pytest.raises(B.LeakageError):
        B.split_frames(data, overlapping_weeks)
    # nada foi escrito: nenhum experimento criado
    assert MlflowClient().get_experiment_by_name("hub-toymc") is None


def test_leak_detected_by_kickoff_even_if_week_order_is_ok(data):
    bad = data.copy()
    bad.loc[(bad.season == 2020) & (bad.week == 8), "kickoff_utc"] = pd.Timestamp("2022-12-01", tz="UTC")
    with pytest.raises(B.LeakageError, match="kickoff_utc"):
        B.split_frames(bad, B.walk_forward_seasons([2021], 2019)[0])


def test_empty_split_and_missing_columns(data):
    with pytest.raises(B.BacktestError):
        B.split_frames(data, B.Split("vazio", (2030, 1), [2031], 2019))
    with pytest.raises(B.BacktestError):
        B.split_frames(data.drop(columns="week"), B.walk_forward_seasons([2021], 2019)[0])


# ---------------------------------------------------------------- execução

def test_multiclass_end_to_end(data):
    res = run_mc(data)
    assert not res.reused and res.selected_model == "logit" and res.beats_baselines
    client = MlflowClient()
    parent = client.get_run(res.parent_run_id)
    assert parent.info.status == "FINISHED" and parent.data.tags["selected_model"] == "logit"
    assert parent.info.experiment_id == client.get_experiment_by_name("hub-toymc").experiment_id
    kids = client.search_runs([parent.info.experiment_id], f"tags.mlflow.parentRunId = '{res.parent_run_id}'")
    assert len(kids) == 4  # 2 modelos × 2 splits
    assert {k.data.tags["role"] for k in kids} == {"candidate", "baseline"}
    for k in kids:
        assert set(hubtrack.REQUIRED_TAGS) <= set(k.data.tags) and k.info.status == "FINISHED"
        assert k.data.metrics["n"] == 12 * 8 and "log_loss" in k.data.metrics
    # pooled == métrica sobre a concatenação (e não a média das médias)
    n = sum(k.data.metrics["n"] for k in kids if k.data.tags["model_name"] == "logit")
    assert parent.data.metrics["logit.n"] == n
    assert set(parent.data.metrics) >= {"logit.log_loss", "freq.brier", "freq.n"}
    assert res.pooled["logit"]["log_loss"] == parent.data.metrics["logit.log_loss"]
    assert res.pooled["logit"]["log_loss"] < res.pooled["freq"]["log_loss"]
    # artefatos
    assert client.download_artifacts(res.parent_run_id, "config.json")


def test_pooled_is_not_mean_of_means():
    d = synth(n_per_week=5, weeks=range(1, 4))
    d2 = pd.concat([d, synth(seasons=(2023,), n_per_week=40, weeks=range(1, 9), seed=1)], ignore_index=True)
    task = B.Task("toypool", "yb", "binary", "log_loss", ("log_loss",))
    res = B.run_backtest(task, [LogitModel("yb")], [FreqModel("yb")], B.walk_forward_seasons([2022, 2023], 2019), d2,
                         RULE, "d", 1)
    kids = MlflowClient().search_runs(
        [MlflowClient().get_run(res.parent_run_id).info.experiment_id],
        f"tags.mlflow.parentRunId = '{res.parent_run_id}' and tags.model_name = 'logit'")
    mean_of_means = np.mean([k.data.metrics["log_loss"] for k in kids])
    assert res.pooled["logit"]["log_loss"] != pytest.approx(mean_of_means, abs=1e-9)


def test_binary_and_regression_tasks(data):
    tb = B.Task("toybin", "yb", "binary", "log_loss", ("log_loss", "brier", "ece", "auc"))
    rb = B.run_backtest(tb, [LogitModel("yb")], [FreqModel("yb")], B.walk_forward_seasons([2022], 2019), data, RULE,
                        "d", 1)
    assert rb.selected_model == "logit" and rb.pooled["logit"]["auc"] > 0.6
    tr = B.Task("toyreg", "yr", "regression", "rmse", ("rmse", "mae"))

    class Lin:  # candidato de regressão simples via mínimos quadrados
        name = "ols"

        def params(self):
            return {}

        def fit(self, train):
            X = np.column_stack([np.ones(len(train)), train[["x1", "x2"]].to_numpy()])
            b = np.linalg.lstsq(X, train["yr"].to_numpy(), rcond=None)[0]
            return type("F", (), {"predict": lambda s, df: np.column_stack(
                [np.ones(len(df)), df[["x1", "x2"]].to_numpy()]) @ b, "to_json": lambda s: {"b": b.tolist()}})()

    rr = B.run_backtest(tr, [Lin()], [MeanModel()], B.walk_forward_seasons([2022], 2019), data, RULE, "d", 1)
    assert rr.selected_model == "ols" and rr.pooled["ols"]["rmse"] < 0.7 < rr.pooled["mean"]["rmse"]


def test_deterministic_and_idempotent(data, tmp_path, monkeypatch):
    r1 = run_mc(data)
    r2 = run_mc(data)
    assert r2.reused and r2.parent_run_id == r1.parent_run_id and r2.pooled == r1.pooled
    assert r2.roles == r1.roles == {"freq": "baseline", "logit": "candidate"}
    r3 = run_mc(data, force=True)
    assert not r3.reused and r3.parent_run_id != r1.parent_run_id
    assert r3.config_sha256 == r1.config_sha256 and r3.pooled == r1.pooled  # mesmas entradas, mesmas métricas
    # outra configuração (C diferente) -> outro hash, executa
    r4 = run_mc(data, candidates=[LogitModel("y3", CLASSES, C=0.01)])
    assert r4.config_sha256 != r1.config_sha256 and not r4.reused


def test_deterministic_across_independent_stores(data, tmp_path, monkeypatch):
    a = run_mc(data)
    monkeypatch.setenv("NFL_MLFLOW_HOME", str(tmp_path / "_outro"))
    b = run_mc(data)
    assert a.pooled == b.pooled and a.config_sha256 == b.config_sha256 and a.parent_run_id != b.parent_run_id


def test_rule_not_satisfied_is_finished_none(data):
    res = run_mc(data, candidates=[LogitModel("y3", CLASSES)])  # sanity
    assert res.selected_model == "logit"
    strict = B.SelectionRule(min_improvement=10.0)
    r = B.run_backtest(mc_task(), [LogitModel("y3", CLASSES)], [FreqModel("y3", CLASSES)],
                       B.walk_forward_seasons([2021, 2022], 2019), data, strict, "synth-v1", 7)
    assert r.selected_model == "none" and not r.beats_baselines
    run = MlflowClient().get_run(r.parent_run_id)
    assert run.info.status == "FINISHED" and run.data.tags["selected_model"] == "none"
    assert run.data.tags["beats_baselines"] == "false"


def test_max_direction_rule(data):
    tb = B.Task("toyauc", "yb", "binary", "auc", ("auc", "log_loss"))
    res = B.run_backtest(tb, [LogitModel("yb")], [FreqModel("yb")], B.walk_forward_seasons([2022], 2019), data,
                         RULE, "d", 1)
    assert res.selected_model == "logit"  # AUC maior é melhor; baseline constante tem AUC 0.5


def test_baseline_is_mandatory_and_names_unique(data):
    with pytest.raises(B.BacktestError, match="baseline"):
        B.run_backtest(mc_task(), [LogitModel("y3", CLASSES)], [], B.walk_forward_seasons([2022], 2019), data, RULE,
                       "d", 1)
    with pytest.raises(B.BacktestError, match="repetidos"):
        B.run_backtest(mc_task(), [LogitModel("y3", CLASSES, name="x")], [FreqModel("y3", CLASSES, "x")],
                       B.walk_forward_seasons([2022], 2019), data, RULE, "d", 1)


def test_failure_marks_parent_and_children_failed(data):
    class Bad(LogitModel):
        def fit(self, train):
            f = super().fit(train)
            f.predict = lambda df: np.full((len(df), 3), 0.9)  # não soma 1
            return f
    with pytest.raises(B.BacktestError, match="somam 1"):
        run_mc(data, candidates=[Bad("y3", CLASSES, name="bad")])
    c = MlflowClient()
    exp = c.get_experiment_by_name("hub-toymc").experiment_id
    parents = c.search_runs([exp], "tags.role = 'parent'")
    assert [p.info.status for p in parents] == ["FAILED"] and "error" in parents[0].data.tags
    assert all(k.info.status != "RUNNING" for k in c.search_runs([exp]))
    # um FAILED não é reaproveitado: a próxima execução correta roda de novo
    assert not run_mc(data).reused


def test_prediction_validation(data):
    class Wrong(LogitModel):
        def fit(self, train):
            f = super().fit(train)
            f.predict = lambda df: np.zeros((len(df), 2))
            return f
    with pytest.raises(B.BacktestError, match="forma"):
        run_mc(data, candidates=[Wrong("y3", CLASSES, name="w")])


def test_unknown_class_in_target(data):
    d = data.copy()
    d.loc[d.season.eq(2022).idxmax(), "y3"] = "z"
    with pytest.raises(B.BacktestError, match="fora de task.classes"):
        run_mc(d)


def test_task_validation():
    with pytest.raises(B.BacktestError):
        B.Task("t", "y", "multiclass", "log_loss")  # sem classes
    with pytest.raises(B.BacktestError):
        B.Task("t", "y", "binary", "rmse")
    with pytest.raises(B.BacktestError):
        B.Task("t", "y", "binary", "log_loss", ("brier",))


def test_model_code_hash_enters_config(data, tmp_path):
    f = tmp_path / "m.py"
    f.write_text("a = 1\n")
    r1 = run_mc(data, model_code_paths=[f])
    f.write_text("a = 2\n")
    r2 = run_mc(data, model_code_paths=[f])
    assert r1.config_sha256 != r2.config_sha256 and not r2.reused
    tags = MlflowClient().get_run(r2.parent_run_id).data.tags
    paths = B.collect_code_paths([FreqModel("y3", CLASSES), LogitModel("y3", CLASSES)], [f, *B.HARNESS_FILES])
    assert f.resolve() in paths and len(paths) == 2 + len(B.HARNESS_FILES)  # toy_models.py + m.py + harness
    assert tags["model_code_sha256"] == hubtrack.sha256_files(paths)


# ---------------------------------------------------------------- impressão digital dos dados e do código (M4)

def test_config_changes_with_data_content_but_not_row_order_or_unused_data():
    d = synth(seasons=(2018, 2019, 2020, 2021, 2022))  # 2018 fica fora de first_train_season=2019
    base = run_mc(d)
    assert run_mc(d.sample(frac=1, random_state=3).reset_index(drop=True)).reused  # ordem das linhas não importa
    assert run_mc(d.assign(junk=1.0)).reused  # coluna não declarada pelos modelos
    d_unused = d.copy()
    d_unused.loc[d_unused.season == 2018, "x1"] += 5.0  # linha que nenhum split usa
    assert run_mc(d_unused).reused
    d_used = d.copy()
    i = d_used.index[(d_used.season == 2020) & (d_used.week == 3)][0]
    d_used.loc[i, "x1"] += 0.001  # MESMO data_id, conteúdo usado diferente
    r = run_mc(d_used)
    assert not r.reused and r.config_sha256 != base.config_sha256
    d_lab = d.copy()
    j = d_lab.index[d_lab.season == 2022][0]
    d_lab.loc[j, "y3"] = "c" if d_lab.loc[j, "y3"] != "c" else "a"
    assert not run_mc(d_lab).reused  # alvo
    assert B.data_fingerprint(d) == B.data_fingerprint(d.iloc[::-1])
    assert B.data_fingerprint(d, ["x1"]) != B.data_fingerprint(d, ["x2"])


def test_model_without_columns_fingerprints_all_columns():
    class NoCols(FreqModel):
        columns = None

    d = synth()

    def run(df):
        return B.run_backtest(mc_task(), [NoCols("y3", CLASSES)], [FreqModel("y3", CLASSES, "freq2")],
                              B.walk_forward_seasons([2022], 2019), df, RULE, "v", 1)
    assert not run(d).reused
    assert not run(d.assign(junk=1.0)).reused  # coluna nova entra: sem columns() vale tudo


def test_changing_fit_without_params_reruns(tmp_path):
    import importlib.util
    src = '''
import numpy as np
class Fit:
    def predict(self, df): return np.tile([0.2, 0.3, 0.5], (len(df), 1))
    def to_json(self): return {}
class Mod:
    name = "mod"
    def params(self): return {}
    def columns(self): return ["y3"]
    def fit(self, train): return Fit()
'''
    f = tmp_path / "mod_under_test.py"

    def load(text):
        f.write_text(text)
        spec = importlib.util.spec_from_file_location("mod_under_test", f)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["mod_under_test"] = mod
        spec.loader.exec_module(mod)
        return mod.Mod()

    d = synth()

    def go(m):
        return B.run_backtest(mc_task(), [m], [FreqModel("y3", CLASSES)], B.walk_forward_seasons([2022], 2019), d,
                              RULE, "v", 1)
    r1 = go(load(src))
    assert go(load(src)).reused
    r3 = go(load(src.replace("0.2, 0.3, 0.5", "0.5, 0.3, 0.2")))  # fit mudou, params() igual
    assert not r3.reused and r3.config_sha256 != r1.config_sha256


def test_overlapping_test_splits_are_refused(data):
    s = [B.Split("a", (2020, B.LAST_WEEK), [2021, 2022], 2019), B.Split("b", (2021, B.LAST_WEEK), [2022], 2019)]
    with pytest.raises(B.BacktestError, match="sobrepostos"):
        B.run_backtest(mc_task(), [LogitModel("y3", CLASSES)], [FreqModel("y3", CLASSES)], s, data, RULE, "v", 1)


def test_auc_single_class_split_is_omitted_with_warning():
    d = synth(seasons=(2019, 2020, 2021))
    d.loc[d.season == 2021, "yb"] = 1  # teste com classe única
    task = B.Task("toyauc", "yb", "binary", "log_loss", ("log_loss", "auc"))
    with pytest.warns(UserWarning, match="auc"):
        res = B.run_backtest(task, [LogitModel("yb")], [FreqModel("yb")], B.walk_forward_seasons([2021], 2019), d,
                             B.SelectionRule(metric="log_loss"), "v", 1)
    assert "auc" not in res.pooled["logit"] and "log_loss" in res.pooled["logit"]
    exp = MlflowClient().get_run(res.parent_run_id).info.experiment_id
    child = MlflowClient().search_runs([exp], filter_string="tags.role = 'candidate'")[0]
    assert "auc" not in child.data.metrics
    # se a regra depende da métrica indefinida, o erro é explícito
    with pytest.warns(UserWarning), pytest.raises(B.BacktestError, match="indefinida"):
        B.run_backtest(task, [LogitModel("yb", name="l2")], [FreqModel("yb")], B.walk_forward_seasons([2021], 2019), d,
                       B.SelectionRule(metric="auc"), "v", 1)


def test_model_without_locatable_source_is_refused(data):
    ns: dict = {}
    exec("class Ghost:\n    name = 'ghost'\n    def params(self): return {}\n"
         "    def fit(self, t): raise RuntimeError\n", ns)
    with pytest.raises(B.BacktestError, match="arquivo-fonte"):
        B.run_backtest(mc_task(), [ns["Ghost"]()], [FreqModel("y3", CLASSES)], B.walk_forward_seasons([2022], 2019),
                       data, RULE, "v", 1)
