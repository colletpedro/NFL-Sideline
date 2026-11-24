import pytest
from mlflow import MlflowClient

import hubtrack
import hubpaths


def _tags(**over):
    t = hubtrack.build_tags("toy", "parent", "c" * 64, "data-1", "f" * 64, "regra", 7)
    t.update(over)
    return t


def test_experiment_prefix_and_artifact_location(tmp_path):
    home = hubtrack.configure()
    assert home == (tmp_path / "_mlflow").resolve()
    exp_id = hubtrack.experiment("toy")
    exp = MlflowClient().get_experiment(exp_id)
    assert exp.name == "hub-toy"
    assert exp.artifact_location == (home / "artifacts" / "hub-toy").as_uri()
    assert hubtrack.experiment("toy") == exp_id  # idempotente


def test_refuses_non_hub_experiment():
    hubtrack.configure()
    other = MlflowClient().create_experiment("qb-outro")
    with pytest.raises(hubtrack.HubTrackError, match="hub-"):
        hubtrack.assert_hub_experiment(other)
    run = MlflowClient().create_run(other)
    with pytest.raises(hubtrack.HubTrackError):
        hubtrack.log_metrics(run.info.run_id, {"x": 1.0})
    with pytest.raises(hubtrack.HubTrackError):
        hubtrack.finish_run(run.info.run_id)
    with pytest.raises(hubtrack.HubTrackError):
        hubtrack.experiment_name("../x")


def test_required_tags_and_git_fields():
    t = _tags()
    assert set(hubtrack.REQUIRED_TAGS) <= set(t)
    assert t["git_dirty"] in ("true", "false", "unknown") and t["harness_version"] == hubtrack.HARNESS_VERSION
    hubtrack.validate_tags(t)
    for k in hubtrack.REQUIRED_TAGS:
        bad = {a: b for a, b in t.items() if a != k}
        with pytest.raises(hubtrack.HubTrackError, match=k):
            hubtrack.validate_tags(bad)
    with pytest.raises(hubtrack.HubTrackError):
        hubtrack.validate_tags(_tags(role="qualquer"))
    with pytest.raises(hubtrack.HubTrackError):
        hubtrack.validate_tags(_tags(data_id=""))


def test_finish_validates_tags_before_closing():
    run_id = hubtrack.start_run("toy", {"role": "parent"})
    with pytest.raises(hubtrack.HubTrackError):
        hubtrack.finish_run(run_id)
    assert MlflowClient().get_run(run_id).info.status == "FAILED"
    ok = hubtrack.start_run("toy", _tags())
    hubtrack.finish_run(ok)
    assert MlflowClient().get_run(ok).info.status == "FINISHED"


def test_parent_child_and_json_artifact():
    parent = hubtrack.start_run("toy", _tags())
    child = hubtrack.start_run("toy", _tags(role="candidate"), parent_run_id=parent)
    hubtrack.log_json(child, {"a": 1}, "fitted.json")
    with pytest.raises(ValueError):
        hubtrack.log_json(child, {"a": float("nan")}, "bad.json")
    assert MlflowClient().get_run(child).data.tags["mlflow.parentRunId"] == parent


def test_canonical_json_rejects_non_json():
    import numpy as np
    assert hubtrack.sha256_json({"b": 1, "a": 2}) == hubtrack.sha256_json({"a": 2, "b": 1})
    with pytest.raises(TypeError):
        hubtrack.canonical_json({"a": np.float64(1.0), "b": np.array([1])})


def test_uses_main_checkout_default_when_env_missing(monkeypatch):
    monkeypatch.delenv("NFL_MLFLOW_HOME")
    assert hubpaths.mlflow_home().parts[-3:] == ("editorial", "local-artifacts", "mlflow")
