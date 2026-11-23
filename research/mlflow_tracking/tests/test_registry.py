"""Testes do registro de modelos: sintéticos (offline, home em tmp) e contra os stores reais (`real_store`)."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import pytest
from mlflow import MlflowClient
from scipy.special import expit, logit

import registry
import tracking
from rebuild_helper import real_rebuild

REPO = Path(__file__).resolve().parents[3]
FROZEN_V1 = REPO / "research" / "qb_interception_risk"
XINT_CODE = REPO / "research" / "qb_expected_interceptions"


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _load_by_path(name: str, path: Path):
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # nunca gravar __pycache__ em diretórios congelados
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.dont_write_bytecode = old


# ------------------------------------------------------------------ fixtures sintéticas

B2_MODEL = {
    "format": "xint-ftn-reference-v1", "kind": "B2", "target": "interception", "risk_input": "is_interception_worthy",
    "model_id": "SYNTH", "train_years": [2025],
    "global_rate": {"probability": 0.05, "n": 100, "events": 5, "boundary_adjusted": False},
    "groups": {"0": {"probability": 0.01, "n": 90, "events": 1, "group_n": 90, "fallback_global": False,
                     "boundary_adjusted": False},
               "1": {"probability": 0.4, "n": 10, "events": 4, "group_n": 10, "fallback_global": False,
                     "boundary_adjusted": False}},
}


def _synthetic_features(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "down": rng.integers(1, 5, n).astype(float), "qtr": rng.integers(1, 5, n).astype(float),
        "ydstogo": rng.integers(1, 20, n).astype(float), "yardline_100": rng.integers(1, 99, n).astype(float),
        "quarter_seconds_remaining": rng.integers(0, 900, n).astype(float),
        "score_differential": rng.integers(-21, 21, n).astype(float)})


def _m3_artifact() -> dict:
    fm = _load_by_path("synthetic_frozen_model", FROZEN_V1 / "model.py")
    d = _synthetic_features(600, 1)
    d["is_interception_worthy"] = (np.random.default_rng(2).random(600) < 0.1).astype(int)
    pipe = fm.fit(d, "context", 0.1, {"solver": "lbfgs", "max_iter": 500, "tol": 1e-8, "seed": 1})
    return {"kind": "context", "offset": -0.1593395890254225, "structure": fm.export_model(pipe, "context", 0.1, [2023])}


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Stores sintéticos mínimos + pais importados + hashes de teste no módulo `registry`."""
    stores = tmp_path / "stores"
    v2 = stores / registry.V2_STORE
    xint = stores / registry.XINT_STORE
    (v2 / "experiment-verified" / "frozen").mkdir(parents=True)
    (xint / "final").mkdir(parents=True)
    (xint / "development").mkdir(parents=True)
    (stores / registry.V1_STORE / "build-v2").mkdir(parents=True)
    (xint / "application-complete").mkdir(parents=True)
    m3 = _m3_artifact()
    (v2 / "experiment-verified" / "frozen" / "M3.json").write_text(json.dumps(m3, indent=1))
    (v2 / "experiment-verified" / "frozen" / "freeze.json").write_text('{"synthetic": "v2"}')
    (xint / "final" / "model.json").write_text(json.dumps(B2_MODEL, indent=1))
    (xint / "development" / "freeze.json").write_text('{"synthetic": "xint"}')
    feats = _synthetic_features(40, 3)
    ids = pd.DataFrame({"game_id": "2026_01_A_B", "play_id": np.arange(40, dtype=float)})
    pd.concat([ids, feats], axis=1).to_parquet(stores / registry.V1_STORE / "build-v2" / "dataset.parquet")
    fm = _load_by_path("synthetic_frozen_model2", FROZEN_V1 / "model.py")
    p3 = expit(logit(fm.predict_json(m3["structure"], feats)) + m3["offset"])
    pred = ids.assign(season=2026, M3=p3)
    pred.to_parquet(v2 / "experiment-verified" / "predictions.parquet")
    worthy = (np.arange(40) % 4 == 0).astype(int)
    pd.DataFrame({"is_interception_worthy": worthy, "interception": (np.arange(40) % 8 == 0).astype(int),
                  "p_interception_given_ftn": np.where(worthy == 1, 0.4, 0.01)}).to_parquet(
        xint / "application-complete" / "pass_predictions.parquet")
    monkeypatch.setattr(registry, "M3_JSON_SHA", _sha(v2 / "experiment-verified" / "frozen" / "M3.json"))
    monkeypatch.setattr(registry, "B2_JSON_SHA", _sha(xint / "final" / "model.json"))
    home = tmp_path / "mlflow home"
    tracking.configure(home)
    client = MlflowClient()
    for exp, store, freeze in (("v2", registry.V2_STORE, v2 / "experiment-verified" / "frozen" / "freeze.json"),
                               ("xint", registry.XINT_STORE, xint / "development" / "freeze.json")):
        exp_id = tracking.ensure_experiment(exp, home)
        tags = tracking.base_tags(store, _sha(freeze), "d" * 64, "e" * 64, 7, "parent", registry.MODULE_DIR)
        with mlflow.start_run(experiment_id=exp_id, tags=tags):
            pass
    return {"home": home, "stores": stores, "m3": m3, "feats": feats, "p3": p3, "v2": v2, "xint": xint}


# ------------------------------------------------------------------ testes sintéticos

def test_register_creates_model_run_versions_and_alias(world):
    res = registry.register("all", world["home"], world["stores"])
    client = MlflowClient()
    for key, name in (("m3", "qb-iw-m3"), ("b2", "xint-ftn")):
        r = res[key]
        assert r["created"] and r["model"] == name and r["version"] == "1"
        mv = client.get_model_version_by_alias(name, "champion")
        assert str(mv.version) == r["version"]
        for t in ("model_sha256", "model_code_sha256", "source_store", "source_run_id"):
            assert mv.tags[t]
        run = client.get_run(r["run_id"])
        tracking.validate_tags(run.data.tags)
        assert run.data.tags["role"] == "model"
        assert "mlflow.parentRunId" not in run.data.tags
        parent = client.get_run(run.data.tags["source_parent_run_id"])
        assert parent.data.tags["role"] == "parent"
        assert run.data.tags["source_freeze_sha256"] == parent.data.tags["source_freeze_sha256"]
        assert run.info.experiment_id == parent.info.experiment_id
    m3 = client.get_model_version_by_alias("qb-iw-m3", "champion")
    assert m3.tags["v1_model_py_sha256"] == registry.V1_MODEL_PY_SHA
    assert m3.tags["model_code_sha256"] == _sha(registry.CODE_DIR / "m3_pyfunc.py")


def test_register_is_idempotent_and_restores_alias(world):
    first = registry.register("all", world["home"], world["stores"])
    client = MlflowClient()
    client.delete_registered_model_alias("qb-iw-m3", "champion")
    second = registry.register("all", world["home"], world["stores"])
    for k in ("m3", "b2"):
        assert second[k]["created"] is False
        assert second[k]["version"] == first[k]["version"] and second[k]["run_id"] == first[k]["run_id"]
    assert str(client.get_model_version_by_alias("qb-iw-m3", "champion").version) == "1"
    assert len(client.search_model_versions("name = 'qb-iw-m3'")) == 1
    exp_id = tracking.ensure_experiment("v2", world["home"])
    assert len(client.search_runs([exp_id], filter_string="tags.role = 'model'")) == 1


def _replace_parents(world, keys):
    """Simula `import --rebuild`: apaga o pai FINISHED do freeze e cria outro com as mesmas tags. {exp: novo_pai}."""
    client, out = MlflowClient(), {}
    for exp in keys:
        exp_id = tracking.ensure_experiment(exp, world["home"])
        (old,) = client.search_runs([exp_id], filter_string="tags.role = 'parent'")
        tags = {k: v for k, v in old.data.tags.items() if not k.startswith("mlflow.")}
        client.delete_run(old.info.run_id)
        with mlflow.start_run(experiment_id=exp_id, tags=tags) as new:
            pass
        out[exp] = new.info.run_id
    return out


def test_register_after_rebuild_creates_new_version_and_moves_alias(world):
    first = registry.register("all", world["home"], world["stores"])
    client = MlflowClient()
    old_parent = client.get_run(first["m3"]["run_id"]).data.tags["source_parent_run_id"]
    assert client.get_model_version("qb-iw-m3", first["m3"]["version"]).tags["source_parent_run_id"] == old_parent
    new_parents = _replace_parents(world, ("v2", "xint"))
    second = registry.register("all", world["home"], world["stores"])
    for key, exp, name in (("m3", "v2", "qb-iw-m3"), ("b2", "xint", "xint-ftn")):
        r = second[key]
        assert r["created"] is True and r["version"] == "2" and r["run_id"] != first[key]["run_id"]
        assert client.get_run(r["run_id"]).data.tags["source_parent_run_id"] == new_parents[exp]
        mv = client.get_model_version_by_alias(name, "champion")
        assert str(mv.version) == "2" and mv.tags["source_parent_run_id"] == new_parents[exp]
        assert len(client.search_model_versions(f"name = '{name}'")) == 2
    third = registry.register("all", world["home"], world["stores"])  # agora volta a ser idempotente
    assert all(third[k]["created"] is False and third[k]["version"] == "2" for k in ("m3", "b2"))


def test_register_legacy_version_without_parent_tag_uses_model_run_tag(world):
    first = registry.register("m3", world["home"], world["stores"])
    client = MlflowClient()
    client.delete_model_version_tag("qb-iw-m3", first["m3"]["version"], "source_parent_run_id")
    again = registry.register("m3", world["home"], world["stores"])
    assert again["m3"]["created"] is False  # pai ainda ativo (tag da execução do modelo)
    _replace_parents(world, ("v2",))
    assert registry.register("m3", world["home"], world["stores"])["m3"]["created"] is True


def test_register_recreates_when_model_run_deleted(world):
    first = registry.register("b2", world["home"], world["stores"])
    MlflowClient().delete_run(first["b2"]["run_id"])
    second = registry.register("b2", world["home"], world["stores"])
    assert second["b2"]["created"] is True and second["b2"]["run_id"] != first["b2"]["run_id"]


def _parent_id(world, exp):
    exp_id = tracking.ensure_experiment(exp, world["home"])
    (p,) = MlflowClient().search_runs([exp_id], filter_string="tags.role = 'parent'")
    return p.info.run_id


def _fake_lab(monkeypatch, world):
    """`verify_models` lê o pacote do laboratório e as linhas 2026; aqui só interessa a checagem da origem."""
    df = world["feats"].assign(M3=world["p3"], is_interception_worthy=(np.arange(len(world["feats"])) % 4 == 0))
    monkeypatch.setattr(registry, "_m3_2026", lambda stores: df)
    plays = [{"down": 1, "distance": 10, "fieldPosition": 50, "quarter": 1, "clock": "10:00",
              "scoreDifferential": 0, "probability": 0.1, "ftnInterceptionWorthy": 0, "pInterceptionGivenFtn": 0.01}]
    monkeypatch.setattr(registry, "_lab_plays", lambda store: plays)


def test_verify_models_flags_champion_whose_source_is_inactive_after_real_rebuild(world, monkeypatch):
    _fake_lab(monkeypatch, world)
    registry.register("m3", world["home"], world["stores"])
    before = registry.verify_models(world["home"], world["stores"])
    assert not [p for p in before if "execução de origem" in p]
    real_rebuild(world["home"], "v2", _parent_id(world, "v2"))  # `import v2 --rebuild` de verdade
    after = registry.verify_models(world["home"], world["stores"])
    msgs = [p for p in after if p.startswith("m3:") and "execução de origem" in p]
    assert len(msgs) == 1 and "`cli.py register m3`" in msgs[0]
    registry.register("m3", world["home"], world["stores"])  # resolve
    fixed = registry.verify_models(world["home"], world["stores"])
    assert not [p for p in fixed if "execução de origem" in p]


KILL_REGISTER = """
import os, sys
sys.path[:0] = [{module!r}]
from pathlib import Path
from mlflow import MlflowClient
import registry
registry.M3_JSON_SHA, registry.B2_JSON_SHA = sys.argv[3], sys.argv[4]
def boom(*a, **k):
    os._exit(9)
MlflowClient.set_model_version_tag = boom
registry.register("m3", Path(sys.argv[1]), Path(sys.argv[2]))
"""


def _model_dirs(home):
    base = Path(home).resolve() / "artifacts" / "qb-risk-temporal-v2"
    runs = sorted(p.name for p in base.iterdir() if p.name != "models") if base.exists() else []
    models = sorted(p.name for p in (base / "models").iterdir()) if (base / "models").exists() else []
    return runs, models


def test_register_killed_between_log_model_and_tags_is_cleaned_on_next_register(world):
    import os
    import subprocess
    code = KILL_REGISTER.format(module=str(Path(registry.__file__).resolve().parent))
    r = subprocess.run([sys.executable, "-c", code, str(world["home"]), str(world["stores"]),
                        registry.M3_JSON_SHA, registry.B2_JSON_SHA], env={**os.environ},
                       capture_output=True, text=True)
    assert r.returncode == 9, r.stderr
    client = MlflowClient()
    (orphan,) = client.search_model_versions("name = 'qb-iw-m3'")
    assert not orphan.tags.get("model_sha256")
    orphan_run = orphan.run_id
    runs, models = _model_dirs(world["home"])
    orphan_models = set(models)
    assert len(orphan_models) == 1  # modelo logado órfão no disco (a execução role=model órfã também existe)
    assert client.get_run(orphan_run).data.tags["role"] == "model"

    res = registry.register("m3", world["home"], world["stores"])
    assert res["m3"]["created"] is True and res["m3"]["run_id"] != orphan_run
    versions = client.search_model_versions("name = 'qb-iw-m3'")
    assert [str(v.version) for v in versions] == [str(res["m3"]["version"])]
    assert versions[0].tags["model_sha256"] == registry.M3_JSON_SHA
    assert client.get_run(orphan_run).info.lifecycle_stage == "deleted"
    runs, models = _model_dirs(world["home"])  # nada do órfão no disco (delete de verdade, não só soft)
    assert len(models) == 1 and not (set(models) & orphan_models)
    exp_id = tracking.ensure_experiment("v2", world["home"])
    assert len(client.search_runs([exp_id], filter_string="tags.role = 'model'")) == 1
    again = registry.register("m3", world["home"], world["stores"])
    assert again["m3"]["created"] is False and again["m3"]["version"] == res["m3"]["version"]


def test_register_failure_after_log_model_leaves_no_version_run_or_directory(world, monkeypatch):
    def boom(self, *a, **k):
        raise RuntimeError("falha simulada nas tags")
    with monkeypatch.context() as mp:
        mp.setattr(MlflowClient, "set_model_version_tag", boom)
        with pytest.raises(RuntimeError, match="falha simulada"):
            registry.register("m3", world["home"], world["stores"])
    client = MlflowClient()
    assert client.search_model_versions("name = 'qb-iw-m3'") == []
    exp_id = tracking.ensure_experiment("v2", world["home"])
    assert client.search_runs([exp_id], filter_string="tags.role = 'model'") == []
    assert _model_dirs(world["home"]) == ([], [])
    assert registry.register("m3", world["home"], world["stores"])["m3"]["created"] is True


def test_purge_keeps_champion_and_other_models_untouched(world):
    first = registry.register("all", world["home"], world["stores"])
    runs_before, models_before = _model_dirs(world["home"])
    registry.register("all", world["home"], world["stores"])
    assert _model_dirs(world["home"]) == (runs_before, models_before)
    client = MlflowClient()
    assert str(client.get_model_version_by_alias("qb-iw-m3", "champion").version) == first["m3"]["version"]
    assert client.get_run(first["b2"]["run_id"]).info.lifecycle_stage == "active"


def test_loads_by_alias_and_predicts(world):
    registry.register("all", world["home"], world["stores"])
    m3 = mlflow.pyfunc.load_model("models:/qb-iw-m3@champion")
    p = np.asarray(m3.predict(registry._frame("m3", world["feats"])))
    np.testing.assert_allclose(p, world["p3"], rtol=0, atol=1e-12)
    # o nome genérico `model` ocupado por outro módulo não atrapalha
    sys.modules["model"] = type(sys)("model")
    try:
        m3b = mlflow.pyfunc.load_model("models:/qb-iw-m3@champion")
        np.testing.assert_allclose(m3b.predict(registry._frame("m3", world["feats"])), world["p3"], rtol=0, atol=1e-12)
    finally:
        del sys.modules["model"]
    b2 = mlflow.pyfunc.load_model("models:/xint-ftn@champion")
    out = b2.predict(pd.DataFrame({"is_interception_worthy": np.array([0, 1, 1, 0], dtype="int64")}))
    np.testing.assert_array_equal(out, [0.01, 0.4, 0.4, 0.01])
    with pytest.raises(Exception):
        b2.predict(pd.DataFrame({"is_interception_worthy": np.array([0, 2], dtype="int64")}))


def test_no_pickle_and_code_inside_model(world, tmp_path):
    registry.register("all", world["home"], world["stores"])
    specs = registry._specs(world["stores"])
    for key in ("m3", "b2"):
        problems, report = [], {}
        registry._check_download(key, f"models:/{specs[key]['model_name']}@champion", specs[key], problems, report)
        assert problems == [] and report["no_pickle"] is True


def test_rejects_wrong_sha(world, monkeypatch):
    monkeypatch.setattr(registry, "B2_JSON_SHA", "0" * 64)
    with pytest.raises(registry.RegistryError, match="sha256"):
        registry.register("b2", world["home"], world["stores"])
    assert MlflowClient().search_registered_models() == []
    p = world["v2"] / "experiment-verified" / "frozen" / "M3.json"
    monkeypatch.setattr(registry, "M3_JSON_SHA", _sha(p))
    p.write_text(p.read_text() + " ")
    with pytest.raises(registry.RegistryError, match="sha256"):
        registry.register("m3", world["home"], world["stores"])


def test_requires_imported_parent(world):
    exp_id = tracking.ensure_experiment("xint", world["home"])
    c = MlflowClient()
    for r in c.search_runs([exp_id]):
        c.delete_run(r.info.run_id)
    with pytest.raises(registry.RegistryError, match="não importada"):
        registry.register("b2", world["home"], world["stores"])


def test_b2_code_equals_original_on_synthetic(world):
    sys.path.insert(0, str(XINT_CODE))
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        import risk_model
    finally:
        sys.dont_write_bytecode = old
        sys.path.remove(str(XINT_CODE))
    registry.register("b2", world["home"], world["stores"])
    b2 = mlflow.pyfunc.load_model("models:/xint-ftn@champion")
    d = pd.DataFrame({"is_interception_worthy": np.array([0, 1] * 20, dtype="int64")})
    np.testing.assert_array_equal(b2.predict(d), risk_model.predict(B2_MODEL, d))


def test_pinned_requirements():
    assert registry.pinned_requirements() == ["numpy==2.3.4", "pandas==2.3.3", "scipy==1.16.3", "scikit-learn==1.7.2"]
    assert _sha(registry.FROZEN_V1_MODEL_PY) == registry.V1_MODEL_PY_SHA


# ------------------------------------------------------------------ stores reais

@pytest.mark.real_store
def test_real_stores_register_and_verify(tmp_path):
    stores = tracking.stores_root()
    if not (stores / registry.V2_STORE).is_dir() or not (stores / registry.XINT_STORE).is_dir():
        pytest.skip("stores reais ausentes")
    for needed in (stores / "qb-risk-lab-v1" / "current.json", stores / "qb-risk-outcomes-lab-v1" / "current.json",
                   stores / registry.V1_STORE / "build-v2" / "dataset.parquet"):
        if not needed.exists():
            pytest.skip(f"ausente: {needed}")
    import cli
    home = tmp_path / "real home"
    assert cli.main(["import", "all", "--home", str(home)]) == 0
    res = registry.register("all", home)
    assert all(r["created"] for r in res.values())
    assert registry.verify_models(home) == []
    again = registry.register("all", home)
    assert not any(r["created"] for r in again.values())
    rep = registry.verify_models.report
    assert rep["m3"]["max_diff_predictions_parquet"] <= 1e-12 and rep["b2"]["max_diff_lab"] <= 1e-12


@pytest.mark.real_store
def test_real_b2_equals_original_risk_model_on_all_2026_rows():
    stores = tracking.stores_root()
    path = stores / registry.XINT_STORE / "application-complete" / "pass_predictions.parquet"
    if not path.is_file():
        pytest.skip("store xINT ausente")
    sys.path.insert(0, str(XINT_CODE))
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        import risk_model
    finally:
        sys.dont_write_bytecode = old
        sys.path.remove(str(XINT_CODE))
    d = pd.read_parquet(path)
    model_json = json.loads((stores / registry.XINT_STORE / "final" / "model.json").read_text())
    ref = risk_model.predict(model_json, d)
    spec = importlib.util.spec_from_file_location("b2_pyfunc_test", registry.CODE_DIR / "b2_pyfunc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class Ctx:
        artifacts = {"model_json": str(stores / registry.XINT_STORE / "final" / "model.json")}

    m = mod.B2Model()
    m.load_context(Ctx)
    out = m.predict(None, d[["is_interception_worthy"]])
    assert len(out) == len(d) == 7970
    np.testing.assert_array_equal(out, ref)
