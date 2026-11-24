import os
import subprocess
from pathlib import Path

import mlflow
import pytest

import cli
import integrity
import tracking


@pytest.fixture
def home(tmp_path):
    h = tmp_path / "home com espaço" / "mlflow"
    tracking.configure(h)
    return h


def test_configure_and_ensure_idempotent(home, tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    a = tracking.ensure_experiment("smoke", home)
    b = tracking.ensure_experiment("mlflow-tracking-smoke", home)
    assert a == b
    exp = mlflow.get_experiment(a)
    assert exp.artifact_location == (home.resolve() / "artifacts" / "mlflow-tracking-smoke").as_uri()
    assert tracking.tracking_uri(home).startswith("sqlite:////")
    with mlflow.start_run(experiment_id=a):
        mlflow.log_metric("m", 1.0)
    assert not (cwd / "mlruns").exists() and not (cwd / "mlartifacts").exists()
    assert list(cwd.iterdir()) == []


def test_ensure_experiment_conflict(home, tmp_path):
    from mlflow import MlflowClient

    MlflowClient().create_experiment("outro", artifact_location=(tmp_path / "x").as_uri())
    with pytest.raises(RuntimeError, match="artifact_location"):
        tracking.ensure_experiment("outro", home)


def test_smoke_has_all_tags_and_is_searchable(tmp_path):
    h = tmp_path / "com espaço" / "mlflow"
    run_id, uri = cli.smoke(h)
    assert uri == tracking.tracking_uri(h)
    exp_id = tracking.ensure_experiment("smoke", h)
    df = mlflow.search_runs([exp_id])
    assert list(df["run_id"]) == [run_id]
    tags = mlflow.get_run(run_id).data.tags
    tracking.validate_tags(tags)
    assert tags["role"] == "smoke" and tags["source_store"] == "synthetic"


def test_validate_tags_missing():
    with pytest.raises(ValueError) as e:
        tracking.validate_tags({"seed": "1", "role": "parent"})
    assert "source_store" in str(e.value) and "git_commit" in str(e.value)


def test_find_parent(home):
    exp = tracking.ensure_experiment("smoke", home)
    with mlflow.start_run(experiment_id=exp) as r1:
        mlflow.set_tags({"source_freeze_sha256": "aaa", "role": "parent"})
    with mlflow.start_run(experiment_id=exp):
        mlflow.set_tags({"source_freeze_sha256": "aaa", "role": "fold"})
    with mlflow.start_run(experiment_id=exp):
        mlflow.set_tags({"source_freeze_sha256": "bbb", "role": "parent"})
    assert tracking.find_parent(exp, "aaa").info.run_id == r1.info.run_id
    assert tracking.find_parent(exp, "ccc") is None


def test_main_checkout_from_worktree(tmp_path):
    repo = tmp_path / "repo com espaço"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    def g(*a, cwd=repo):
        subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, env=env)
    g("init", "-q")
    g("commit", "-q", "--allow-empty", "-m", "x")
    wt = tmp_path / "wt"
    g("worktree", "add", "-q", str(wt), "-b", "feature")
    assert tracking.main_checkout(wt) == repo.resolve()
    assert tracking.main_checkout(repo) == repo.resolve()
    info = tracking.git_info(wt)
    assert info["branch"] == "feature" and info["dirty"] is False and len(info["commit"]) == 40


def test_env_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("NFL_MLFLOW_HOME", str(tmp_path / "h"))
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(tmp_path / "s"))
    assert tracking.mlflow_home() == tmp_path / "h"
    assert tracking.stores_root() == tmp_path / "s"


def test_integrity_detects_changes(tmp_path):
    root = tmp_path / "store"
    (root / "d").mkdir(parents=True)
    (root / "a.txt").write_text("a")
    (root / "d" / "b.txt").write_text("b")
    before = integrity.snapshot(root)
    assert integrity.compare(before, integrity.snapshot(root)) == {"added": [], "removed": [], "changed": []}
    (root / "new.txt").write_text("n")
    (root / "a.txt").write_text("aa")
    (root / "d" / "b.txt").unlink()
    diff = integrity.compare(before, integrity.snapshot(root))
    assert diff["added"] == ["new.txt"] and diff["removed"] == ["d/b.txt"]
    assert "a.txt" in diff["changed"]  # o diretório "d" também muda (mtime), por cobrir diretórios


def test_integrity_cli_exit_code(tmp_path):
    root = tmp_path / "s"
    root.mkdir()
    (root / "f").write_text("1")
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    assert integrity.main(["snapshot", "--root", str(root), "--out", str(a)]) == 0
    assert integrity.main(["snapshot", "--root", str(root), "--out", str(b)]) == 0
    assert integrity.main(["compare", "--before", str(a), "--after", str(b)]) == 0
    (root / "g").write_text("2")
    integrity.main(["snapshot", "--root", str(root), "--out", str(b)])
    assert integrity.main(["compare", "--before", str(a), "--after", str(b)]) == 1
