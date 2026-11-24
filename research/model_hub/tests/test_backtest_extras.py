"""Extensões do harness (H4): `references=` (fora da regra) e hook de métricas/artefatos extras."""
import numpy as np
import pytest
from mlflow import MlflowClient

import backtest as B
from toy_models import CODE, FreqModel, LogitModel, synth

CLASSES = ("a", "b", "c")
TASK = B.Task("toyx", "y3", "multiclass", "log_loss", ("log_loss",), CLASSES)


class Oracle:
    """Referência que vaza o alvo: melhor que tudo, mas fora da regra."""
    name = "oracle"

    def params(self):
        return {}

    def fit(self, train):
        class F:
            def predict(self, df):
                P = np.full((len(df), 3), 0.01)
                P[np.arange(len(df)), df["y3"].map({c: i for i, c in enumerate(CLASSES)}).to_numpy()] = 0.98
                return P

            def to_json(self):
                return {}
        return F()


def _run(data, **kw):
    return B.run_backtest(TASK, [LogitModel("y3", CLASSES)], [FreqModel("y3", CLASSES)],
                          B.walk_forward_seasons([2022], 2019), data, B.SelectionRule(), "synth-v1", 7,
                          model_code_paths=[CODE], **kw)


def test_reference_is_reported_but_never_selected_nor_a_baseline():
    data = synth()
    res = _run(data, references=[Oracle()])
    assert res.roles["oracle"] == "reference" and res.selected_model == "logit"
    assert res.pooled["oracle"]["log_loss"] < res.pooled["logit"]["log_loss"]
    runs = MlflowClient().search_runs([MlflowClient().get_experiment_by_name("hub-toyx").experiment_id],
                                      filter_string="tags.role = 'reference'")
    assert len(runs) == 1 and runs[0].data.tags["model_name"] == "oracle"


def test_reference_does_not_change_selection_but_changes_config_hash():
    data = synth()
    a, b = _run(data), _run(data, references=[Oracle()])
    assert a.selected_model == b.selected_model and a.config_sha256 != b.config_sha256
    assert _run(data).reused  # sem extras o hash é o de antes


def test_reference_name_must_be_unique():
    class Dup(Oracle):
        name = "freq"
    with pytest.raises(B.BacktestError, match="repetidos"):
        _run(synth(), references=[Dup()])


def test_extra_metrics_and_artifacts_pooled_and_per_split():
    data = synth()
    seen = []

    def mean_x1(test, pred):
        seen.append(len(test))
        return float(test["x1"].mean())

    def art(test, pred):
        return {"n.json": {"n": len(test)}}

    res = _run(data, extra_metrics={"mean_x1": mean_x1}, extra_artifacts=art)
    test = data[data.season == 2022]
    assert res.pooled["logit"]["mean_x1"] == pytest.approx(test["x1"].mean())
    client = MlflowClient()
    import json
    from pathlib import Path
    obj = json.loads(Path(client.download_artifacts(res.parent_run_id, "extras/logit/n.json")).read_text())
    assert obj == {"n": len(test)}
    # configuração com extras tem outro hash e lista os nomes
    cfg = json.loads(Path(client.download_artifacts(res.parent_run_id, "config.json")).read_text())
    assert cfg["extras"] == {"metrics": ["mean_x1"], "artifacts": True}


# ------------------------------------------------------------------ L-2: código do harness no hash
def test_harness_files_are_always_in_code_hash(tmp_path, monkeypatch):
    names = {p.name for p in B.HARNESS_FILES}
    assert {"backtest.py", "metrics.py", "hubtrack.py"} <= names
    data = synth()
    base = _run(data).config_sha256
    fake = tmp_path / "metrics_fake.py"
    fake.write_text("# v1")
    monkeypatch.setattr(B, "HARNESS_FILES", (*B.HARNESS_FILES, fake))
    a = _run(data)
    assert a.config_sha256 != base  # o conjunto de arquivos do harness entra no hash
    fake.write_text("# v2 (mudou uma métrica)")
    b = _run(data)
    assert not b.reused and b.config_sha256 != a.config_sha256
