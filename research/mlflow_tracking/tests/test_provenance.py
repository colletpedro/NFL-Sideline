"""Testes da proveniência do laboratório: home sintético em tmp (offline) e contra os stores reais (`real_store`)."""
import csv
import json
from pathlib import Path

import mlflow
import pytest
from mlflow import MlflowClient

import cli
import provenance
import tracking
from rebuild_helper import real_rebuild

SHA_B2 = "b" * 64
SHA_M3 = "a" * 64
B2_GROUP_VALUES = {"all": {"observed_interceptions": 380.0, "expected_interceptions": 364.50562063822224,
                           "log_loss": 0.04985274183852961, "brier": 0.012187694142121633,
                           "average_precision": 0.4470018440457666, "roc_auc": 0.8940122201486754},
                   "ftn_0": {"observed_interceptions": 75.0, "expected_interceptions": 52.916788150912595},
                   "ftn_1": {"observed_interceptions": 305.0, "expected_interceptions": 311.58883248730956}}


def _tags(role, store, **extra):
    base = {"source_store": store, "source_freeze_sha256": "f" * 64, "dataset_sha256": "d" * 64,
            "design_sha256": "e" * 64, "seed": "1", "git_commit": "c" * 40, "git_dirty": "false",
            "importer_version": "0.1.0", "importer_code_sha256": "9" * 64,
            "imported_at_utc": "2026-01-01T00:00:00+00:00", "role": role}
    base.update(extra)
    return base


def _run(exp_id, name, tags, metrics=None, params=None):
    with mlflow.start_run(experiment_id=exp_id, run_name=name, tags=tags) as r:
        for k, v in (params or {}).items():
            mlflow.log_param(k, v)
        for k, v in (metrics or {}).items():
            mlflow.log_metric(k, v)
    return r.info.run_id


def _champion(client, name, version_tags, run_id):
    client.create_registered_model(name)
    run = client.get_run(run_id)
    mv = client.create_model_version(name, source=f"{run.info.artifact_uri}/model", run_id=run_id,
                                     tags=version_tags)
    client.set_registered_model_alias(name, "champion", mv.version)


def build_home(home: Path, *, skip_alias=None, drop_metric=None, bootstrap_reps="2000", bump=0.0):
    """Home MLflow sintético com o mesmo desenho dos importadores (experimentos, pais, filhos, execuções de modelo)."""
    tracking.configure(home)
    client = MlflowClient()
    x = tracking.ensure_experiment("xint", home)
    parent = _run(x, "parent", _tags("parent", "xint/store"))
    for model, vals, extra in (("B2", B2_GROUP_VALUES, {}), ("B1", {"all": {"log_loss": 0.05029813324690858}}, {}),
                               ("C", {"all": {"log_loss": 0.050521123265684885}}, {})):
        metrics = {f"{g}.{m}": v + (bump if (model, g, m) == ("B2", "all", "log_loss") else 0.0)
                   for g, ms in vals.items() for m, v in ms.items()}
        if drop_metric and model == "B2":
            metrics.pop(drop_metric, None)
        params = {"model": model, "paired.all.B2-B1.log_loss.reps": bootstrap_reps} if model == "B2" else {}
        _run(x, f"eval {model}", _tags("evaluation", "xint/store", model=model, **{"mlflow.parentRunId": parent}),
             metrics, params)
    b2_run = _run(x, "xint-ftn · modelo", _tags("model", "xint/store", source_parent_run_id=parent,
                                                model_name="xint-ftn", model_sha256=SHA_B2))
    v = tracking.ensure_experiment("v2", home)
    vparent = _run(v, "parent", _tags("parent", "v2/store"))
    for year, base in (("2026", 0.136), ("2025", 0.139)):
        metrics = {"log_loss": base, "brier": base / 4, "pr_auc_average_precision": 0.05, "roc_auc": 0.57,
                   "observed_expected": 0.96}
        _run(v, f"v2 · {year} · M3", _tags("candidate", "v2/store", year=year, candidate="M3",
                                           **{"mlflow.parentRunId": vparent}), metrics)
    m3_run = _run(v, "qb-iw-m3 · modelo", _tags("model", "v2/store", source_parent_run_id=vparent,
                                                model_name="qb-iw-m3", model_sha256=SHA_M3))
    if skip_alias != "xint-ftn":
        _champion(client, "xint-ftn", {"model_sha256": SHA_B2}, b2_run)
    if skip_alias != "qb-iw-m3":
        _champion(client, "qb-iw-m3", {"model_sha256": SHA_M3}, m3_run)
    return home


@pytest.fixture
def home(tmp_path):
    return build_home(tmp_path / "home")


def test_build_content_and_provenance_of_each_number(home):
    data = provenance.build_provenance(home)
    assert data["schemaVersion"] == 1
    assert set(data["models"]) == {SHA_B2, SHA_M3}
    b2 = data["models"][SHA_B2]
    assert (b2["name"], b2["version"], b2["experiment"]) == ("xint-ftn", "1", "xint-ftn-v1")
    assert b2["importerGitCommit"] == "c" * 40 and b2["sourceStore"] == "xint/store"
    assert b2["sourceFreezeSha256"] == "f" * 64
    nums = b2["numbers"]
    assert nums["evaluation2025.B2.all.log_loss"]["value"] == 0.04985274183852961
    assert nums["evaluation2025.B2.ftn_0.expected_interceptions"]["value"] == 52.916788150912595
    assert nums["evaluation2025.B1.all.log_loss"]["value"] == 0.05029813324690858
    assert nums["evaluation2025.C.all.log_loss"]["value"] == 0.050521123265684885
    rep = nums["evaluation2025.bootstrap.replicates"]
    assert rep["value"] == 2000 and rep["paramKey"] == "paired.all.B2-B1.log_loss.reps"
    client = MlflowClient()
    for n in nums.values():
        run = client.get_run(n["runId"])
        if "metricKey" in n:
            assert run.data.metrics[n["metricKey"]] == n["value"]
        else:
            assert int(run.data.params[n["paramKey"]]) == n["value"]
    m3 = data["models"][SHA_M3]["numbers"]
    assert {"candidate2026.M3.log_loss", "candidate2025.M3.roc_auc"} <= set(m3)
    assert len(b2["runId"]) == 32 and b2["sourceParentRunId"]


def test_error_suggests_register_when_champion_source_inactive_after_real_rebuild(home):
    assert provenance.build_provenance(home)  # antes: ok
    v = tracking.ensure_experiment("v2", home)
    (parent,) = MlflowClient().search_runs([v], filter_string="tags.role = 'parent'")
    real_rebuild(home, "v2", parent.info.run_id)  # `import v2 --rebuild` de verdade
    with pytest.raises(provenance.ProvenanceError, match=r"cli\.py register m3"):
        provenance.build_provenance(home)


def test_deterministic_and_no_rewrite(home, tmp_path):
    out = tmp_path / "out" / "provenance.json"
    p, changed = provenance.write_provenance(out, home)
    assert p == out and changed is True
    first = out.read_bytes()
    assert first.endswith(b"\n") and b"imported_at" not in first and b"importedAt" not in first
    assert json.loads(first)["schemaVersion"] == 1
    mtime = out.stat().st_mtime_ns
    _, changed2 = provenance.write_provenance(out, home)
    assert changed2 is False and out.read_bytes() == first and out.stat().st_mtime_ns == mtime
    assert provenance.render(provenance.build_provenance(home)).encode() == first


def test_rewrites_when_content_changes(home, tmp_path):
    out = tmp_path / "p.json"
    provenance.write_provenance(out, home)
    out.write_text("{}\n")
    assert provenance.write_provenance(out, home)[1] is True


@pytest.mark.parametrize("name", ["xint-ftn", "qb-iw-m3"])
def test_error_without_alias(tmp_path, name):
    h = build_home(tmp_path / "h", skip_alias=name)
    with pytest.raises(provenance.ProvenanceError, match="alias"):
        provenance.build_provenance(h)


def test_error_without_metric(tmp_path):
    h = build_home(tmp_path / "h", drop_metric="all.roc_auc")
    with pytest.raises(provenance.ProvenanceError, match="all.roc_auc"):
        provenance.build_provenance(h)


def test_error_without_or_invalid_reps(tmp_path):
    with pytest.raises(provenance.ProvenanceError, match="reps"):
        provenance.build_provenance(build_home(tmp_path / "h1", bootstrap_reps="abc"))


def test_error_without_evaluation_run(tmp_path):
    h = tmp_path / "empty"
    tracking.configure(h)
    with pytest.raises(provenance.ProvenanceError, match="alias"):
        provenance.build_provenance(h)


def test_cli_check(home, tmp_path, capsys):
    out = tmp_path / "p.json"
    assert cli.main(["provenance", "--home", str(home), "--out", str(out), "--check"]) == 1  # ausente
    assert cli.main(["provenance", "--home", str(home), "--out", str(out)]) == 0
    assert "changed=true" in capsys.readouterr().out
    assert cli.main(["provenance", "--home", str(home), "--out", str(out), "--check"]) == 0
    assert cli.main(["provenance", "--home", str(home), "--out", str(out)]) == 0
    assert "changed=false" in capsys.readouterr().out
    out.write_text(out.read_text().replace("0.04985274183852961", "0.05"))
    assert cli.main(["provenance", "--home", str(home), "--out", str(out), "--check"]) == 1
    assert out.read_text().count("0.05") >= 1  # --check nunca reescreve


def test_cli_error_without_alias(tmp_path, capsys):
    h = build_home(tmp_path / "h", skip_alias="xint-ftn")
    assert cli.main(["provenance", "--home", str(h), "--out", str(tmp_path / "p.json")]) == 2
    assert "alias" in capsys.readouterr().err
    assert not (tmp_path / "p.json").exists()


# ------------------------------------------------------------------ stores reais

@pytest.mark.real_store
def test_real_store_values_match_store_files(tmp_path):
    stores = tracking.stores_root()
    xdirs = sorted((stores / "qb-expected-interceptions-v1").glob("*/evaluation/metrics.csv"))
    vdirs = sorted((stores / "qb-risk-temporal-calibration-v2").glob("*/experiment-verified/metrics.json"))
    if not xdirs or not vdirs:
        pytest.skip("stores reais ausentes")
    import registry

    home = tmp_path / "real_home"
    cli.main(["import", "all", "--home", str(home)])
    registry.register("all", home)
    data = provenance.build_provenance(home)
    rows = {(r["model"], r["group"]): r for r in csv.DictReader(open(xdirs[-1]))}
    b2 = data["models"][registry.B2_JSON_SHA]["numbers"]
    checked = 0
    for key, n in b2.items():
        if "metricKey" not in n:
            continue
        _, model, group, _metric = key.split(".", 3)
        assert float(rows[(model, group)][n["metricKey"].split(".", 1)[1]]) == n["value"], key
        checked += 1
    assert checked == 12
    assert b2["evaluation2025.B2.all.log_loss"]["value"] == 0.04985274183852961
    assert b2["evaluation2025.bootstrap.replicates"]["value"] == 2000
    m3 = data["models"][registry.M3_JSON_SHA]["numbers"]
    entries = json.load(open(vdirs[-1]))
    for e in entries:
        if e["candidate"] == "M3" and e["year"] in (2025, 2026):
            for k in provenance.M3_METRICS:
                assert e["model"][k] == m3[f"candidate{e['year']}.M3.{k}"]["value"], (e["year"], k)
