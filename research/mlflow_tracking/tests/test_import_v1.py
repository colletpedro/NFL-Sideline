"""Testes do importador da v1: store sintético em tmp_path (offline) e, marcado, o store real."""
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from mlflow import MlflowClient

import cli
import import_v1
import integrity
import tracking

DESIGN_BYTES = b"design.json sintetico"
CONTRACT_BYTES = b"RESEARCH-CONTRACT sintetico"
REAL_REFS = (import_v1.DESIGN_PATH, import_v1.CONTRACT_PATH)  # antes do monkeypatch autouse
VARIANTS = ("context", "depth")
C_GRID = [0.1, 1.0]
STORE_REL = "qb-interception-risk-baseline-v1/20261104-v1"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def wjson(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1))


def block(seed: float, n: int, with_auc=True) -> dict:
    return {"log_loss": 0.1 + seed, "brier": 0.03 + seed / 7, "pr_auc_average_precision": 0.05 + seed / 3,
            "roc_auc": (0.55 + seed / 5) if with_auc else None, "prevalence": 0.04 + seed / 11,
            "expected": 10.5 + seed, "mean_probability": 0.041 + seed / 13, "n": n, "positives": 3}


def make_store(root: Path, chosen=None, null_auc=False) -> Path:
    """Store v1 falso com os mesmos nomes/esquemas e hashes coerentes (valores pequenos)."""
    store = root / STORE_REL
    for d in import_v1.CANONICAL_DIRS:
        (store / d).mkdir(parents=True, exist_ok=True)
    dataset = b"fake-parquet-bytes"
    (store / "build-v2" / "dataset.parquet").write_bytes(dataset)
    wjson(store / "build-v2" / "build_manifest.json", {"dataset_sha256": sha(dataset), "rows": 123, "gate": "PASS"})
    design = {
        "C_grid": C_GRID, "application": {"season": 2026, "weeks": [1, 7]}, "application_train": [2022, 2023, 2024, 2025],
        "bootstrap_replicates": 2000, "calibration_edges": [0, 0.5, 1],
        "folds": [{"train": [2022], "validation": 2023}, {"train": [2022, 2023], "validation": 2024}],
        "final_test": 2025, "final_train": [2022, 2023, 2024], "max_iter": 2000, "posthoc_calibration": False,
        "seed": 20261104, "selection": "pooled log loss, ties prefer smaller C", "solver": "lbfgs", "tol": 1e-9,
        "variants": list(VARIANTS), "version": "qb-iw-research-v1",
    }
    history = []
    for vi, v in enumerate(VARIANTS):
        for ci, c in enumerate(C_GRID):
            for fi, fold in enumerate(design["folds"]):
                seed = 0.01 * (1 + vi + 3 * ci + 5 * fi) + (0.0 if ci == 0 else 0.02 * (vi + 1))
                history.append({"variant": v, "C": c, "train_years": fold["train"], "validation": fold["validation"],
                                "model": block(seed, 100 + 10 * fi, with_auc=not (null_auc and vi == 0 and ci == 0 and fi == 0)),
                                "constant": block(0.2, 100 + 10 * fi)})
    wjson(store / "development-v3" / "development_metrics.json", history)
    pooled = import_v1.pooled_selection(history, design)
    chosen = chosen or {v: min((s, c) for c, s in pooled[v].items())[1] for v in VARIANTS}
    models = {}
    for v in VARIANTS:
        b = f"model-{v}".encode()
        (store / "development-v3" / f"model_{v}_2022_2024.json").write_bytes(b)
        models[v] = sha(b)
    frozen = {"chosen_C": chosen, "constant_prevalence": 0.042, "contract_sha256": sha(CONTRACT_BYTES),
              "dataset_sha256": sha(dataset), "design": design, "design_sha256": sha(DESIGN_BYTES), "models": models,
              "notice": "n", "version": 1}
    fp = store / "development-v3" / "frozen_config.json"
    wjson(fp, frozen)
    fsha = sha(fp.read_bytes())
    wjson(store / "evaluation-v1" / "evaluation_receipt.json", {"frozen_config_sha256": fsha, "test_year": 2025})
    wjson(store / "application-v1" / "application_receipt.json",
          {"expected_sum": 28.5, "frozen_config_sha256": fsha, "games": 7, "observed": 9, "passers": 6, "passes": 99,
           "weeks": [1, 2, 3, 4, 5, 6, 7]})
    ev = {}
    for vi, v in enumerate(VARIANTS):
        ev[v] = {"constant": block(0.2, 500), "model": block(0.1 + vi / 50, 500),
                 "paired_game_bootstrap": {"brier": {"delta": -0.001 * (vi + 1), "low": -0.002, "high": 0.0001},
                                           "log_loss": {"delta": -0.01 * (vi + 1), "low": -0.02, "high": -0.001}}}
        wjson(store / "evaluation-v1" / f"calibration_{v}.json", [{"bin": "[0.0, 1.0)", "n": 1}])
        wjson(store / "evaluation-v1" / f"groups_{v}.json", [{"group": "down", "value": "1.0"}])
        (store / "evaluation-v1" / f"coefficients_{v}.csv").write_text("feature,coefficient\na,1\n")
        (store / "evaluation-v1" / f"test_predictions_{v}.parquet").write_bytes(b"pq" + v.encode())
        wjson(store / "application-v1" / f"application_diagnostics_{v}.json",
              {"calibration": [], "metrics_descriptive_only": block(0.3 + vi / 9, 99)})
        (store / "application-v1" / f"model_{v}_2022_2025.json").write_bytes(b"{}")
        (store / "application-v1" / f"qb_{v}.csv").write_text("passer\nx\n")
        (store / "application-v1" / f"application_predictions_{v}.parquet").write_bytes(b"pq2")
    wjson(store / "evaluation-v1" / "metrics.json", ev)
    (store / "application-v1" / "qb_sensitivity.csv").write_text("passer\nx\n")
    for name in ("calibration_2025.png", "calibration_2025.svg", "depth_sensitivity_2026.png",
                 "depth_sensitivity_2026.svg", "difference_per100_2026.png", "difference_per100_2026.svg",
                 "observed_expected_2026.png", "observed_expected_2026.svg", "calibration_support.csv",
                 "plot_passers.csv"):
        (store / "figures-v4" / name).write_bytes(b"fig")
    wjson(store / "sources.json", {"version": 1, "files": []})
    wjson(store / "reproduction-check.json", {"passed": True, "files": 0})
    return store


@pytest.fixture(autouse=True)
def no_repo_refs(tmp_path, monkeypatch):
    """Aponta design.json e RESEARCH-CONTRACT.md para cópias sintéticas (os hashes do store sintético as citam)."""
    refs = tmp_path / "refs"
    refs.mkdir()
    (refs / "design.json").write_bytes(DESIGN_BYTES)
    (refs / "RESEARCH-CONTRACT.md").write_bytes(CONTRACT_BYTES)
    monkeypatch.setattr(import_v1, "DESIGN_PATH", refs / "design.json")
    monkeypatch.setattr(import_v1, "CONTRACT_PATH", refs / "RESEARCH-CONTRACT.md")
    return refs


@pytest.fixture
def env(tmp_path, monkeypatch):
    stores = tmp_path / "stores"
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(stores))
    return {"store": make_store(stores), "home": tmp_path / "mlflow home", "stores": stores}


def active_runs(home, role=None):
    exp_id = tracking.ensure_experiment("v1", home)
    q = f"tags.role = '{role}'" if role else ""
    return MlflowClient().search_runs([exp_id], filter_string=q, max_results=1000)


def test_structure_tags_and_exact_metrics(env):
    res = import_v1.import_v1(env["store"], env["home"])
    assert res["created"] and res["counts"] == {"parent": 1, "fold": 8, "selection": 2, "evaluation": 2, "application": 2}
    runs = active_runs(env["home"])
    assert len(runs) == 15
    parent = [r for r in runs if r.data.tags["role"] == "parent"][0]
    assert parent.info.run_id == res["parent_run_id"] and parent.info.status == "FINISHED"
    frozen = json.loads((env["store"] / "development-v3" / "frozen_config.json").read_text())
    fsha = sha((env["store"] / "development-v3" / "frozen_config.json").read_bytes())
    for r in runs:
        t = r.data.tags
        tracking.validate_tags(t)
        assert t["source_store"] == STORE_REL and t["source_freeze_sha256"] == fsha
        assert t["dataset_sha256"] == frozen["dataset_sha256"] and t["design_sha256"] == sha(DESIGN_BYTES)
        assert t["seed"] == "20261104" and t["experiment_family"] == "qb-iw-baseline-v1"
        assert t["source_code_commit_development"] == "35ac931" and r.info.status == "FINISHED"
        if t["role"] != "parent":
            assert t["mlflow.parentRunId"] == parent.info.run_id
    assert parent.data.tags["selection_rule"] == frozen["design"]["selection"]
    assert parent.data.params["chosen_C.context"] == "0.1" or parent.data.params["chosen_C.context"] == "1.0"
    assert parent.data.metrics["build_rows"] == 123 and parent.data.metrics["application_expected_sum"] == 28.5

    # folds: igualdade exata com development_metrics.json
    history = json.loads((env["store"] / "development-v3" / "development_metrics.json").read_text())
    folds = {(r.data.params["variant"], r.data.params["C"], r.data.params["validation_year"]): r
             for r in active_runs(env["home"], "fold")}
    assert len(folds) == 8
    for rec in history:
        r = folds[(rec["variant"], str(rec["C"]), str(rec["validation"]))]
        for k, v in rec["model"].items():
            assert r.data.metrics[k] == v
        for k, v in rec["constant"].items():
            assert r.data.metrics["constant." + k] == v
        assert r.data.metrics["delta_log_loss_vs_constant"] == rec["model"]["log_loss"] - rec["constant"]["log_loss"]
        assert r.data.params["train_years"] == json.dumps(rec["train_years"], separators=(",", ":"))

    # avaliação e aplicação
    ev = json.loads((env["store"] / "evaluation-v1" / "metrics.json").read_text())
    for r in active_runs(env["home"], "evaluation"):
        v = r.data.params["variant"]
        for k, x in ev[v]["model"].items():
            assert r.data.metrics[k] == x
        for k, x in ev[v]["constant"].items():
            assert r.data.metrics["constant." + k] == x
        for met, vals in ev[v]["paired_game_bootstrap"].items():
            for part, x in vals.items():
                assert r.data.metrics[f"bootstrap.{met}.{part}"] == x
        assert r.data.params["test_year"] == "2025"
    for r in active_runs(env["home"], "application"):
        v = r.data.params["variant"]
        diag = json.loads((env["store"] / "application-v1" / f"application_diagnostics_{v}.json").read_text())
        for k, x in diag["metrics_descriptive_only"].items():
            assert r.data.metrics["descriptive_only." + k] == x
        assert r.data.tags["metrics_scope"] == "descriptive_only" and r.data.params["weeks"] == "1-7"
    # seleção: pooled calculado e chosen_C
    for r in active_runs(env["home"], "selection"):
        assert r.data.params["chosen_C"] == str(frozen["chosen_C"][r.data.params["variant"]])
        assert set(k.split("C_")[1] for k in r.data.metrics) == {"0.1", "1.0"}

    # artefatos: nenhum parquet; parent traz source_files.json
    client = MlflowClient()

    def all_artifacts(rid, path=None):
        out = []
        for a in client.list_artifacts(rid, path):
            out += all_artifacts(rid, a.path) if a.is_dir else [a.path]
        return out
    names = set()
    for r in runs:
        arts = all_artifacts(r.info.run_id)
        assert not [a for a in arts if a.endswith(".parquet")]
        names.update(arts)
    assert "source_files.json" in all_artifacts(parent.info.run_id)
    sf = json.loads(Path(client.download_artifacts(parent.info.run_id, "source_files.json")).read_text())
    assert any(x["path"] == "build-v2/dataset.parquet" for x in sf) and all(len(x["sha256"]) == 64 for x in sf)
    assert "figures/calibration_2025.png" in names


def test_idempotent(env):
    a = import_v1.import_v1(env["store"], env["home"])
    b = import_v1.import_v1(env["store"], env["home"])
    assert not b["created"] and b["parent_run_id"] == a["parent_run_id"]
    assert len(active_runs(env["home"])) == 15


def test_store_untouched(env):
    before = integrity.snapshot(env["stores"])
    import_v1.import_v1(env["store"], env["home"])
    assert integrity.compare(before, integrity.snapshot(env["stores"])) == {"added": [], "removed": [], "changed": []}


def test_rollback_on_midway_failure(env):
    # JSON corrompido lido só ao criar a execução de aplicação (depois do pai, folds e avaliações)
    (env["store"] / "application-v1" / "application_diagnostics_depth.json").write_text("{corrompido")
    with pytest.raises(import_v1.V1ImportError, match="application_diagnostics_depth"):
        import_v1.import_v1(env["store"], env["home"])
    assert active_runs(env["home"]) == []
    deleted = MlflowClient().search_runs([tracking.ensure_experiment("v1", env["home"])],
                                         run_view_type=2, max_results=1000)
    assert len(deleted) > 5  # houve criação parcial, desfeita


CHAIN_MATCH = {"dataset": r"sha256\(dataset.parquet\).*build_manifest.dataset_sha256",
               "manifest": r"sha256\(dataset.parquet\).*build_manifest.dataset_sha256",
               "model": r"sha256\(model_depth_2022_2024.json\).*frozen_config.models\[depth\]",
               "receipt": r"sha256\(frozen_config.json\).*application_receipt.frozen_config_sha256",
               "repro": "passed == true",
               "design": r"sha256\(design.json\).*frozen_config.design_sha256",
               "contract": r"sha256\(RESEARCH-CONTRACT.md\).*frozen_config.contract_sha256",
               "design_missing": r"Arquivo de referência ausente.*design.json",
               "contract_missing": r"Arquivo de referência ausente.*RESEARCH-CONTRACT.md"}


@pytest.mark.parametrize("victim", list(CHAIN_MATCH))
def test_hash_chain_failures(env, no_repo_refs, victim):
    s = env["store"]
    if victim == "dataset":
        (s / "build-v2" / "dataset.parquet").write_bytes(b"outro")
    elif victim == "manifest":
        m = json.loads((s / "build-v2" / "build_manifest.json").read_text())
        m["dataset_sha256"] = "0" * 64
        wjson(s / "build-v2" / "build_manifest.json", m)
    elif victim == "model":
        (s / "development-v3" / "model_depth_2022_2024.json").write_bytes(b"alterado")
    elif victim == "receipt":
        r = json.loads((s / "application-v1" / "application_receipt.json").read_text())
        r["frozen_config_sha256"] = "1" * 64
        wjson(s / "application-v1" / "application_receipt.json", r)
    elif victim == "design":
        (no_repo_refs / "design.json").write_text("outro")
    elif victim == "contract":
        (no_repo_refs / "RESEARCH-CONTRACT.md").write_text("outro")
    elif victim == "design_missing":
        (no_repo_refs / "design.json").unlink()
    elif victim == "contract_missing":
        (no_repo_refs / "RESEARCH-CONTRACT.md").unlink()
    else:
        wjson(s / "reproduction-check.json", {"passed": False})
    with pytest.raises(import_v1.V1ImportError, match=CHAIN_MATCH[victim]):
        import_v1.import_v1(s, env["home"])
    assert active_runs(env["home"]) == []


def test_chosen_c_must_be_argmin(tmp_path, monkeypatch):
    stores = tmp_path / "s"
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(stores))
    store = make_store(stores)
    frozen = json.loads((store / "development-v3" / "frozen_config.json").read_text())
    wrong = {v: (1.0 if frozen["chosen_C"][v] == 0.1 else 0.1) for v in VARIANTS}
    store2 = make_store(tmp_path / "s2", chosen=wrong)
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(tmp_path / "s2"))
    with pytest.raises(import_v1.V1ImportError, match=r"chosen_C\[\w+\]=.*difere do argmin"):
        import_v1.import_v1(store2, tmp_path / "home")
    assert active_runs(tmp_path / "home") == []


def test_none_metric_becomes_tag(tmp_path, monkeypatch):
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(tmp_path / "s"))
    store = make_store(tmp_path / "s", null_auc=True)
    home = tmp_path / "home"
    import_v1.import_v1(store, home)
    r = [x for x in active_runs(home, "fold")
         if x.data.params["variant"] == "context" and x.data.params["C"] == "0.1"
         and x.data.params["validation_year"] == "2023"][0]
    assert "roc_auc" not in r.data.metrics and json.loads(r.data.tags["null_metrics"]) == ["roc_auc"]


def test_cli_import_v1(env, capsys):
    assert cli.main(["import", "v1", "--store", str(env["store"]), "--home", str(env["home"])]) == 0
    out = capsys.readouterr().out
    assert "created=true" in out and "fold=8" in out
    cli.main(["import", "v1", "--store", str(env["store"]), "--home", str(env["home"])])
    assert "created=false" in capsys.readouterr().out


# ------------------------------------------------------------------ store real
def real_store() -> Path:
    try:
        return import_v1.default_store()
    except Exception:
        return Path("/nonexistent")


@pytest.mark.real_store
@pytest.mark.skipif(not (real_store() / "reproduction-check.json").exists(), reason="store real da v1 ausente")
def test_real_store_exact_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(import_v1, "DESIGN_PATH", REAL_REFS[0])  # o store real é conferido contra os arquivos reais
    monkeypatch.setattr(import_v1, "CONTRACT_PATH", REAL_REFS[1])
    store = real_store()
    before = integrity.snapshot(store)
    home = tmp_path / "home"
    res = import_v1.import_v1(store, home)
    assert res["counts"] == {"parent": 1, "fold": 16, "selection": 2, "evaluation": 2, "application": 2}
    assert integrity.compare(before, integrity.snapshot(store)) == {"added": [], "removed": [], "changed": []}

    def jl(p):
        return json.loads((store / p).read_text())
    hist = jl("development-v3/development_metrics.json")
    folds = {(r.data.params["variant"], r.data.params["C"], r.data.params["validation_year"]): r
             for r in active_runs(home, "fold")}
    assert len(folds) == 16
    for rec in hist:
        r = folds[(rec["variant"], str(rec["C"]), str(rec["validation"]))]
        copied = {k: v for k, v in rec["model"].items() if v is not None}
        assert {k: r.data.metrics[k] for k in copied} == copied
        copied_c = {k: v for k, v in rec["constant"].items() if v is not None}
        assert {k: r.data.metrics["constant." + k] for k in copied_c} == copied_c
        assert r.data.metrics["delta_log_loss_vs_constant"] == rec["model"]["log_loss"] - rec["constant"]["log_loss"]
    ev = jl("evaluation-v1/metrics.json")
    for r in active_runs(home, "evaluation"):
        v = r.data.params["variant"]
        for k, x in ev[v]["model"].items():
            assert r.data.metrics[k] == x
        for k, x in ev[v]["constant"].items():
            assert r.data.metrics["constant." + k] == x
        for met, vals in ev[v]["paired_game_bootstrap"].items():
            for part, x in vals.items():
                assert r.data.metrics[f"bootstrap.{met}.{part}"] == x
    for r in active_runs(home, "application"):
        v = r.data.params["variant"]
        for k, x in jl(f"application-v1/application_diagnostics_{v}.json")["metrics_descriptive_only"].items():
            assert r.data.metrics["descriptive_only." + k] == x
    parent = active_runs(home, "parent")[0]
    rec = jl("application-v1/application_receipt.json")
    assert parent.data.metrics["application_passes"] == rec["passes"]
    assert parent.data.metrics["application_expected_sum"] == rec["expected_sum"]
    assert parent.data.metrics["build_rows"] == jl("build-v2/build_manifest.json")["rows"]
    frozen = jl("development-v3/frozen_config.json")
    for r in active_runs(home, "selection"):
        assert r.data.params["chosen_C"] == str(frozen["chosen_C"][r.data.params["variant"]])
    client = MlflowClient()

    def walk(rid, path=None):
        out = []
        for a in client.list_artifacts(rid, path):
            out += walk(rid, a.path) if a.is_dir else [a.path]
        return out
    for r in active_runs(home):
        arts = walk(r.info.run_id)
        assert (arts or r.data.tags["role"] in ("fold", "selection")) and not [a for a in arts if a.endswith(".parquet")]
