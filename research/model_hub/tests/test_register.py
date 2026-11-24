import json

import mlflow
import numpy as np
import pytest
from mlflow import MlflowClient

import backtest as B
import hubtrack
import register
from toy_models import CODE, FEATURES, FreqModel, LogitModel, synth

CLASSES = ("a", "b", "c")


def _backtest(data, kind="multiclass", min_improvement=0.0):
    if kind == "multiclass":
        task = B.Task("toyreg3", "y3", "multiclass", "log_loss", ("log_loss",), CLASSES)
        cand, base = LogitModel("y3", CLASSES), FreqModel("y3", CLASSES)
    else:
        task = B.Task("toyregb", "yb", "binary", "log_loss", ("log_loss",))
        cand, base = LogitModel("yb"), FreqModel("yb")
    res = B.run_backtest(task, [cand], [base], B.walk_forward_seasons([2022], 2019), data,
                         B.SelectionRule(min_improvement=min_improvement), "synth-v1", 7, model_code_paths=[CODE])
    return task, cand, res


def _reg(key, code, params, example, run_id, **kw):
    """register_json_model com os argumentos de prova do modelo `logit` do backtest-brinquedo."""
    lm = LogitModel("yb") if key == "toyregb" else LogitModel("y3", CLASSES)
    kw = {"model_name": lm.name, "hyperparams": lm.params(), "train_data_sha256": "fp-train", **kw}
    return register.register_json_model(key, code, params, example, run_id, **kw)


@pytest.mark.parametrize("kind", ["multiclass", "binary"])
def test_register_load_predict_equal(kind):
    data = synth()
    task, cand, res = _backtest(data, kind)
    fitted = cand.fit(data[data.season <= 2021])
    params = fitted.to_json()
    example = data[FEATURES].head(5)
    out = _reg(task.key, CODE, params, example, res.parent_run_id)
    name = f"hub-{task.key}"
    assert out["name"] == name and out["version"] == "1"
    model = mlflow.pyfunc.load_model(f"models:/{name}@champion")
    test = data[data.season == 2022]
    np.testing.assert_allclose(model.predict(test[FEATURES]), fitted.predict(test), rtol=0, atol=1e-12)
    client = MlflowClient()
    mv = client.get_model_version_by_alias(name, "champion")
    assert mv.tags["params_sha256"] == hubtrack.sha256_json(params)
    assert mv.tags["model_code_sha256"] == hubtrack.sha256_file(CODE)
    assert mv.tags["source_run_id"] == res.parent_run_id
    assert mv.tags["selected_model"] == "logit" and mv.tags["train_data_sha256"] == "fp-train"
    assert mv.tags["hyperparams_sha256"] == hubtrack.sha256_json(cand.params())
    run = client.get_run(out["run_id"])
    assert run.info.status == "FINISHED" and run.data.tags["role"] == "final"
    assert run.data.tags["config_sha256"] == res.config_sha256
    # experimento do registro é hub-*
    assert client.get_experiment(run.info.experiment_id).name == name


def test_no_pickle_in_model_folder(tmp_path):
    data = synth()
    task, cand, res = _backtest(data)
    out = _reg(task.key, CODE, cand.fit(data).to_json(), data[FEATURES].head(3),
                                       res.parent_run_id)
    local = mlflow.artifacts.download_artifacts(f"models:/{out['name']}/{out['version']}", dst_path=str(tmp_path / "m"))
    files = [p.name for p in (tmp_path / "m").rglob("*") if p.is_file()]
    assert not [f for f in files if f.endswith(register.BAD_SUFFIXES)]
    assert {"params.json", "params.sha256", "MLmodel", CODE.name} <= set(files)
    register.check_no_pickle(f"models:/{out['name']}/{out['version']}")
    # um pickle plantado é detectado
    (tmp_path / "m" / "x.pkl").write_bytes(b"x")
    with pytest.raises(register.RegisterError, match="pickle"):
        register.check_no_pickle(str(tmp_path / "m"))


def test_tampered_params_refused_on_load(tmp_path):
    data = synth()
    task, cand, res = _backtest(data)
    out = _reg(task.key, CODE, cand.fit(data).to_json(), data[FEATURES].head(3),
                                       res.parent_run_id)
    local = mlflow.artifacts.download_artifacts(f"models:/{out['name']}/{out['version']}", dst_path=str(tmp_path / "m"))
    p = next((tmp_path / "m").rglob("params.json"))
    obj = json.loads(p.read_text())
    obj["intercept"][0] += 1.0
    p.write_text(json.dumps(obj))
    with pytest.raises(Exception, match="adulterado|sha256"):
        mlflow.pyfunc.load_model(str(tmp_path / "m"))


def test_refuses_model_that_did_not_beat_baselines():
    data = synth()
    task, cand, res = _backtest(data, min_improvement=10.0)
    assert res.selected_model == "none"
    with pytest.raises(register.RegisterError, match="baselines"):
        _reg(task.key, CODE, cand.fit(data).to_json(), data[FEATURES].head(3),
                                     res.parent_run_id)
    client = MlflowClient()
    assert client.search_model_versions(f"name = 'hub-{task.key}'") == []


def test_refuses_wrong_experiment_and_non_json_params():
    data = synth()
    task, cand, res = _backtest(data)
    with pytest.raises(register.RegisterError, match="esperado"):
        _reg("outro", CODE, {}, data[FEATURES].head(3), res.parent_run_id)
    with pytest.raises(TypeError):
        _reg(task.key, CODE, {"w": np.array([1.0])}, data[FEATURES].head(3), res.parent_run_id)


def test_reregistration_moves_alias_to_new_version():
    data = synth()
    task, cand, res = _backtest(data)
    a = _reg(task.key, CODE, cand.fit(data[data.season <= 2020]).to_json(),
                                     data[FEATURES].head(3), res.parent_run_id)
    b = _reg(task.key, CODE, cand.fit(data).to_json(), data[FEATURES].head(3),
                                     res.parent_run_id)
    assert (a["version"], b["version"]) == ("1", "2")
    assert str(MlflowClient().get_model_version_by_alias(f"hub-{task.key}", "champion").version) == "2"


def test_refuses_params_that_do_not_belong_to_the_selected_model():
    data = synth()
    task, cand, res = _backtest(data)
    params, ex = cand.fit(data).to_json(), data[FEATURES].head(3)
    # nome de outro modelo (o baseline `freq` não foi o selecionado)
    with pytest.raises(register.RegisterError, match="selecionou 'logit'"):
        _reg(task.key, CODE, params, ex, res.parent_run_id, model_name="freq", hyperparams=FreqModel("y3", CLASSES).params())
    # nome inexistente
    with pytest.raises(register.RegisterError, match="selecionou"):
        _reg(task.key, CODE, params, ex, res.parent_run_id, model_name="outro")
    # hiperparâmetros diferentes dos gravados no config.json do pai
    with pytest.raises(register.RegisterError, match="hiperparâmetros"):
        _reg(task.key, CODE, params, ex, res.parent_run_id, hyperparams=LogitModel("y3", CLASSES, C=0.5).params())
    # sem require_beats, o nome ainda precisa ser candidato do pai
    with pytest.raises(register.RegisterError, match="candidato"):
        _reg(task.key, CODE, params, ex, res.parent_run_id, model_name="freq",
             hyperparams=FreqModel("y3", CLASSES).params(), require_beats_baselines=False)
    assert MlflowClient().search_model_versions(f"name = 'hub-{task.key}'") == []
