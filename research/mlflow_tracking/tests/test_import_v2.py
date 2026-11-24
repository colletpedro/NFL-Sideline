"""Testes do importador da v2: store sintético em tmp_path (offline) e, marcado, o store real."""
import hashlib
import json
from pathlib import Path

import pytest
from mlflow import MlflowClient

import import_v1
import import_v2
import integrity
import tracking

STORE_REL = import_v2.STORE_NAME
YEARS = (2024, 2025, 2026)
CANDS = ("M0", "M1", "M2", "M3")
V1_SHA = "3add5c6113c91f720ae7dfde759617f114daf66f700b4ce7229c2efa21f3e90a"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def wjson(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1))


def block(seed: float, n: int = 100, auc=True) -> dict:
    return {"brier": 0.03 + seed / 7, "expected": 10.5 + seed, "log_loss": 0.1 + seed, "mean_probability": 0.04 + seed / 13,
            "n": n, "observed_expected": 0.9 + seed / 17, "positives": 3, "pr_auc_average_precision": 0.05 + seed / 3,
            "prevalence": 0.03 + seed / 11, "roc_auc": (0.55 + seed / 5) if auc else None}


def diff(seed: float) -> dict:
    return {"brier": {"delta": -seed / 9, "high": seed / 100, "low": -seed / 5},
            "log_loss": {"delta": -seed / 3, "high": seed / 50, "low": -seed / 2}}


PROTOCOL = {
    "version": "qb-risk-temporal-v2.0", "seed": 20261104, "bootstrap_replicates": 2000, "C": 0.1,
    "known_evaluation_years": [2024, 2025, 2026], "selection_years": [2024, 2025], "known_2026_weeks": [1, 7],
    "reserved": {"season": 2026, "weeks": [9, 13], "maturity_days_after_latest_kickoff": 8},
    "candidates": list(CANDS), "selection_rule": "regra sintética de seleção",
    "standardization": {"reference_years": [2023, 2024, 2025], "min_cell_per_year": 30, "max_weight": 5},
    "passer_intervals": "omit",
}
# 2026-11-05 e semana 13 em 2026-12-07 20:15 NY (EST, UTC-5) => 2026-12-08T01:15Z; +8 dias
SCHEDULE = ("game_id,season,game_type,week,gameday,gametime\n"
            + "".join(f"2026_{w:02d}_A_B,2026,REG,{w},2026-11-{4 + w:02d},13:00\n" for w in (9, 10, 11, 12))
            + "2026_13_A_B,2026,REG,13,2026-12-07,20:15\n")
NOT_BEFORE = "2026-12-16T01:15:00+00:00"


DOCS = ("EXPERIMENT-PROTOCOL.md", "RESERVED-EVALUATION.md")


def make_repo(root: Path) -> dict:
    """Mini-worktree com pipeline.py (MODEL_SHA), M3 de evidência, protocol.json e um arquivo de código."""
    m3 = json.dumps({"kind": "context", "offset": -0.15, "structure_sha256": "ab" * 32}, indent=1).encode()
    (root / "research/qb_risk_lab").mkdir(parents=True)
    (root / "research/qb_risk_lab/pipeline.py").write_text(f"MODEL='x'\nMODEL_SHA='{sha(m3)}'\n")
    ev = root / "docs/plans/qb-risk-temporal-calibration-v2/evidence/frozen/M3.json"
    ev.parent.mkdir(parents=True)
    ev.write_bytes(m3)
    (root / "research/qb_risk_temporal_v2").mkdir(parents=True)
    pbytes = json.dumps(PROTOCOL, indent=1).encode()
    (root / "research/qb_risk_temporal_v2/protocol.json").write_bytes(pbytes)
    (root / "research/qb_risk_temporal_v2/experiment.py").write_text("# codigo sintetico\n")
    docs = root / import_v2.CONTRACTS_DIR_REL
    for name in DOCS:
        (docs / name).write_bytes(f"# {name} sintetico\n".encode())
    return {"m3": m3, "protocol_sha": sha(pbytes), "code": sha(b"# codigo sintetico\n"),
            "docs": {n: sha((docs / n).read_bytes()) for n in DOCS}}


def make_store(stores: Path, repo: Path, null_auc=False, code_hash=None) -> Path:
    r = make_repo(repo)
    store = stores / STORE_REL
    exp = store / "experiment-verified"
    fr = exp / "frozen"
    fr.mkdir(parents=True)
    (fr / "M3.json").write_bytes(r["m3"])
    (fr / "M0.json").write_text('{"kind":"context"}')
    (fr / "M1.json").write_text('{"kind":"constant","probability":0.03,"train_years":[2025]}')
    (fr / "reserved_schedule.csv").write_text(SCHEDULE)
    files = {n: sha((fr / n).read_bytes()) for n in ("M0.json", "M1.json", "M3.json", "reserved_schedule.csv")}
    freeze = {"code_hashes": {"research/qb_risk_temporal_v2/experiment.py": code_hash or r["code"]},
              "contracts": {"protocol.json": r["protocol_sha"], **r["docs"]}, "dataset_sha256": "e" * 64, "files": files,
              "references": ["M0", "M1"], "reserved": PROTOCOL["reserved"], "selected": "M3", "status": "awaiting",
              "version": 2}
    wjson(fr / "freeze.json", freeze)
    metrics, bins = [], {}
    for yi, y in enumerate(YEARS):
        for ci, c in enumerate(CANDS):
            seed = 0.01 * (1 + yi + 4 * ci)
            rec = {"year": y, "candidate": c, "period_status": "known_retrospective_diagnostic",
                   "model": block(seed, 100 + yi, auc=not (null_auc and y == 2024 and c == "M0")),
                   "M1": block(0.2, 100 + yi), "difference_vs_M1": diff(seed),
                   "calibration_diagnostic": {
                       "bootstrap_requested": 2000, "bootstrap_valid_joint": 0 if c == "M1" else 1999,
                       "bootstrap_valid_offset": 2000, "joint_intercept": None if c == "M1" else -0.5 - seed,
                       "joint_intercept_ci": [None, None] if c == "M1" else [-0.9, -0.1],
                       "method": "game bootstrap; diagnostic MLE", "offset_intercept": -0.2 - seed,
                       "offset_intercept_ci": [-0.4, -0.1], "slope": None if c == "M1" else 0.9 + seed,
                       "slope_ci": [None, None] if c == "M1" else [0.7, 1.1],
                       "status": "constant_slope_unidentifiable" if c == "M1" else "diagnostic_only"}}
            if c == "M3":
                rec["same_structure_before_offset_diagnostic"] = block(seed + 0.5, 100 + yi)
            metrics.append(rec)
            bins[f"{y}_{c}"] = [{"bin": "[0.0, 1.0)", "n": 100 + yi, "observed_rate": 0.03, "positives": 3}]
            if c == "M1":
                wjson(exp / "models" / f"M1_{y}.json", {"kind": "constant", "probability": 0.04, "train_years": [y - 1]})
            elif c != "M0":
                wjson(exp / "models" / f"{c}_{y}.json",
                      {"kind": "context", "offset": 0.0 if c == "M2" else -0.2,
                       "calibration_year": None if c == "M2" else y - 1, "calibration_n": 0,
                       "structure": {"train_years": [y - 2, y - 1], "C": 0.1}, "structure_sha256": sha(f"{c}{y}".encode())})
    wjson(exp / "metrics.json", metrics)
    wjson(exp / "calibration_bins.json", bins)
    pooled = lambda s: {**block(s, 1000), "n": 1000}
    wjson(exp / "selection.json", {
        "decision": "candidate_for_reserved_evaluation_only", "reference_if_none": "M1",
        "results": {c: {"difference_vs_M1": {"brier": {"delta": -0.0001 * i, "high": -0.00002, "low": -0.0002},
                                             "ll": {"delta": -0.001 * i, "high": -0.0004, "low": -0.002}},
                        "eligible": True, "per_year_conditions_pass": i == 2, "pooled": pooled(0.01 * i)}
                    for i, c in ((1, "M2"), (2, "M3"))},
        "selected_contextual_candidate": "M3", "selection_years": [2024, 2025]})
    (exp / "groups.csv").write_text("year,candidate\n2024,M0\n")
    wjson(exp / "environment.json", {"python": "3.11"})
    (exp / "predictions.parquet").write_bytes(b"pq-pred")
    (exp / "splits.parquet").write_bytes(b"pq-splits")
    (exp / "drift").mkdir()
    (exp / "drift" / "composition.csv").write_text("a,b\n1,2\n")
    wjson(exp / "drift" / "schema_comparison.json", {"ok": True})
    fig = store / "figures-reviewed"
    fig.mkdir()
    for n in ("calibration_diagnostics.png", "calibration_diagnostics.svg", "calibration_support.csv"):
        (fig / n).write_bytes(b"fig")
    wjson(store / "v1-lineage.json", {"v1_freeze_sha256": V1_SHA, "v1_head": "abc"})
    return store


@pytest.fixture
def env(tmp_path, monkeypatch):
    stores = tmp_path / "stores"
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(stores))
    repo = tmp_path / "repo"
    store = make_store(stores, repo)
    return {"store": store, "home": tmp_path / "mlflow home", "stores": stores, "repo": repo}


def imp(env, **kw):
    return import_v2.import_v2(env["store"], env["home"], repo_root=env["repo"], **kw)


def active_runs(home, role=None):
    tracking.configure(home)
    exp_id = tracking.ensure_experiment("v2", home)
    q = f"tags.role = '{role}'" if role else ""
    return MlflowClient().search_runs([exp_id], filter_string=q, max_results=1000)


def expected_candidate_metrics(rec: dict) -> dict:
    """Mapa esperado escrito à mão, independente do código do importador."""
    out = {}
    for k, v in rec["model"].items():
        out[k] = v
    for k, v in rec["M1"].items():
        out["M1." + k] = v
    for met in ("brier", "log_loss"):
        for part in ("delta", "low", "high"):
            out[f"vs_M1.{met}.{part}"] = rec["difference_vs_M1"][met][part]
    d = rec["calibration_diagnostic"]
    for k in ("bootstrap_requested", "bootstrap_valid_joint", "bootstrap_valid_offset", "joint_intercept",
              "offset_intercept", "slope"):
        out["calibration." + k] = d[k]
    for k in ("joint_intercept_ci", "offset_intercept_ci", "slope_ci"):
        if d[k] is None:
            continue  # IC ausente inteiro: vira null_metrics, sem métrica
        out[f"calibration.{k}.low"], out[f"calibration.{k}.high"] = d[k]
    if "same_structure_before_offset_diagnostic" in rec:
        for k, v in rec["same_structure_before_offset_diagnostic"].items():
            out["before_offset." + k] = v
    return {k: v for k, v in out.items() if v is not None}


def check_exact(home, store):
    metrics = json.loads((store / "experiment-verified" / "metrics.json").read_text())
    runs = {(r.data.params["year"], r.data.params["candidate"]): r for r in active_runs(home, "candidate")}
    assert len(runs) == len(metrics) == 12
    for rec in metrics:
        r = runs[(str(rec["year"]), rec["candidate"])]
        exp = expected_candidate_metrics(rec)
        assert r.data.metrics == {k: float(v) for k, v in exp.items()}
        nulls = {k for k in ("joint_intercept", "slope") if rec["calibration_diagnostic"][k] is None}
        if nulls or rec["model"]["roc_auc"] is None:
            assert r.data.tags["null_metrics"]
        assert r.data.tags["calibration_status"] == rec["calibration_diagnostic"]["status"]
        assert r.data.tags["year"] == str(rec["year"]) and r.data.tags["candidate"] == rec["candidate"]
    sel = json.loads((store / "experiment-verified" / "selection.json").read_text())
    s = active_runs(home, "selection")[0]
    want = {}
    for c, res in sel["results"].items():
        for k, v in res["pooled"].items():
            want[f"{c}.pooled.{k}"] = v
        for met, parts in res["difference_vs_M1"].items():
            for part, v in parts.items():
                want[f"{c}.vs_M1.{met}.{part}"] = v
        assert s.data.tags[f"{c}.eligible"] == "true"
    assert s.data.metrics == {k: float(v) for k, v in want.items()}


def test_structure_tags_and_exact_metrics(env):
    res = imp(env)
    assert res["created"] and res["counts"] == {"parent": 1, "candidate": 12, "selection": 1}
    runs = active_runs(env["home"])
    assert len(runs) == 14
    parent = [r for r in runs if r.data.tags["role"] == "parent"][0]
    assert parent.info.run_id == res["parent_run_id"] and parent.info.status == "FINISHED"
    freeze_path = env["store"] / "experiment-verified" / "frozen" / "freeze.json"
    freeze = json.loads(freeze_path.read_text())
    for r in runs:
        t = r.data.tags
        tracking.validate_tags(t)
        assert t["source_store"] == STORE_REL and t["source_freeze_sha256"] == sha(freeze_path.read_bytes())
        assert t["dataset_sha256"] == "e" * 64 and t["design_sha256"] == freeze["contracts"]["protocol.json"]
        assert t["seed"] == "20261104" and t["experiment_family"] == "qb-risk-temporal-v2"
        assert r.info.status == "FINISHED"
        if t["role"] != "parent":
            assert t["mlflow.parentRunId"] == parent.info.run_id
    t = parent.data.tags
    assert t["selection_rule"] == PROTOCOL["selection_rule"] and t["v1_freeze_sha256"] == V1_SHA
    assert t["upstream_v1_parent_run_id"] == "not_imported"
    assert t["reserved_status"] == "awaiting_mature_reserved_window" and t["reserved_not_before_utc"] == NOT_BEFORE
    assert t["selected_contextual_candidate"] == "M3" and "code_hash_mismatch" not in t
    p = parent.data.params
    assert p["C"] == "0.1" and p["reserved.weeks"] == "[9,13]" and p["standardization.max_weight"] == "5"
    assert p["candidates"] == '["M0","M1","M2","M3"]' and p["bootstrap_replicates"] == "2000"
    check_exact(env["home"], env["store"])

    cand = {(r.data.params["year"], r.data.params["candidate"]): r for r in active_runs(env["home"], "candidate")}
    m3 = cand[("2025", "M3")]
    assert m3.info.run_name == "v2 · 2025 · M3"
    assert m3.data.params["kind"] == "context" and m3.data.params["calibration_year"] == "2024"
    assert m3.data.params["train_years"] == "[2023,2024]"
    assert "kind" not in cand[("2025", "M0")].data.params
    assert cand[("2025", "M2")].data.params["calibration_year"] == "null"
    assert cand[("2025", "M1")].data.params["probability"] == "0.04"

    client = MlflowClient()

    def walk(rid, path=None):
        out = []
        for a in client.list_artifacts(rid, path):
            out += walk(rid, a.path) if a.is_dir else [a.path]
        return out
    for r in runs:
        assert not [a for a in walk(r.info.run_id) if a.endswith(".parquet")]
    arts = walk(parent.info.run_id)
    for a in ("frozen/freeze.json", "frozen/M3.json", "frozen/reserved_schedule.csv", "selection.json",
              "groups.csv", "environment.json", "source_files.json", "figures/calibration_diagnostics.png",
              "drift/composition.csv"):
        assert a in arts
    sf = json.loads(Path(client.download_artifacts(parent.info.run_id, "source_files.json")).read_text())
    assert any(x["path"] == "experiment-verified/predictions.parquet" for x in sf)
    assert all(len(x["sha256"]) == 64 for x in sf)
    a = walk(m3.info.run_id)
    assert set(a) == {"M3_2025.json", "calibration_bins_2025_M3.json"}
    assert walk(cand[("2025", "M0")].info.run_id) == ["calibration_bins_2025_M0.json"]


def test_null_metrics_tag(tmp_path, monkeypatch):
    stores = tmp_path / "stores"
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(stores))
    repo = tmp_path / "repo"
    store = make_store(stores, repo, null_auc=True)
    import_v2.import_v2(store, tmp_path / "h", repo_root=repo)
    cand = {(r.data.params["year"], r.data.params["candidate"]): r for r in active_runs(tmp_path / "h", "candidate")}
    r = cand[("2024", "M0")]
    assert json.loads(r.data.tags["null_metrics"]) == ["roc_auc"] and "roc_auc" not in r.data.metrics
    m1 = cand[("2024", "M1")]
    assert set(json.loads(m1.data.tags["null_metrics"])) >= {"calibration.slope", "calibration.joint_intercept"}


def test_code_hash_mismatch_is_tag_not_failure(tmp_path, monkeypatch):
    stores = tmp_path / "stores"
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(stores))
    repo = tmp_path / "repo"
    store = make_store(stores, repo, code_hash="0" * 64)
    import_v2.import_v2(store, tmp_path / "h", repo_root=repo)
    parent = active_runs(tmp_path / "h", "parent")[0]
    assert json.loads(parent.data.tags["code_hash_mismatch"]) == ["research/qb_risk_temporal_v2/experiment.py"]


def test_upstream_v1_link(env):
    # cria um pai v1 falso com o mesmo freeze
    home = tracking.configure(env["home"])
    v1 = tracking.ensure_experiment("v1", home)
    c = MlflowClient()
    run = c.create_run(v1, tags={"source_freeze_sha256": V1_SHA, "role": "parent"})
    imp(env, rebuild=True)  # pai v1 RUNNING (interrompido) não conta como upstream
    assert active_runs(env["home"], "parent")[0].data.tags["upstream_v1_parent_run_id"] == "not_imported"
    c.set_terminated(run.info.run_id, "FINISHED")
    imp(env, rebuild=True)
    parent = active_runs(env["home"], "parent")[0]
    assert parent.data.tags["upstream_v1_parent_run_id"] == run.info.run_id


def test_idempotent(env):
    a = imp(env)
    b = imp(env)
    assert not b["created"] and b["parent_run_id"] == a["parent_run_id"]
    assert len(active_runs(env["home"])) == 14


def test_store_untouched(env):
    before = integrity.snapshot(env["stores"])
    imp(env)
    assert integrity.compare(before, integrity.snapshot(env["stores"])) == {"added": [], "removed": [], "changed": []}


def test_rollback_on_midway_failure(env):
    (env["store"] / "experiment-verified" / "models" / "M3_2026.json").write_text("{corrompido")
    with pytest.raises(import_v2.V2ImportError, match="M3_2026"):
        imp(env)
    assert active_runs(env["home"]) == []
    deleted = MlflowClient().search_runs([tracking.ensure_experiment("v2", env["home"])],
                                         run_view_type=2, max_results=1000)
    assert len(deleted) > 5


def _bump(path: Path, fn):
    obj = json.loads(path.read_text())
    fn(obj)
    wjson(path, obj)


CHAIN_MATCH = {
    "frozen_file": r"sha256\(frozen/M0.json\).*freeze.files\[M0.json\]",
    "model_sha": r"sha256\(frozen/M3.json\).*difere do MODEL_SHA",
    "evidence": r"sha256\(frozen/M3.json\).*da evidência",
    "protocol": r"sha256\(protocol.json\).*freeze.contracts\[protocol.json\]",
    "protocol_doc": r"sha256\(EXPERIMENT-PROTOCOL.md\).*freeze.contracts\[EXPERIMENT-PROTOCOL.md\]",
    "reserved_doc": r"sha256\(RESERVED-EVALUATION.md\).*freeze.contracts\[RESERVED-EVALUATION.md\]",
    "protocol_missing": r"Contrato de referência ausente.*protocol.json",
    "reserved_doc_missing": r"Contrato de referência ausente.*RESERVED-EVALUATION.md",
    "selection": r"selected_contextual_candidate='M2'.*freeze.selected='M3'",
    "dataset": "freeze.json não tem dataset_sha256",
}


@pytest.mark.parametrize("victim", list(CHAIN_MATCH))
def test_hash_chain_failures(env, victim):
    s, repo = env["store"], env["repo"]
    exp = s / "experiment-verified"
    docs = repo / import_v2.CONTRACTS_DIR_REL
    kw = {}
    if victim == "frozen_file":
        (exp / "frozen" / "M0.json").write_text('{"kind":"alterado"}')
    elif victim == "model_sha":
        kw["model_sha"] = "0" * 64
    elif victim == "evidence":
        (repo / "docs/plans/qb-risk-temporal-calibration-v2/evidence/frozen/M3.json").write_text("{}")
    elif victim == "protocol":
        (repo / "research/qb_risk_temporal_v2/protocol.json").write_text('{"seed": 1}')
    elif victim == "protocol_doc":
        (docs / "EXPERIMENT-PROTOCOL.md").write_text("alterado")
    elif victim == "reserved_doc":
        (docs / "RESERVED-EVALUATION.md").write_text("alterado")
    elif victim == "protocol_missing":
        (repo / "research/qb_risk_temporal_v2/protocol.json").unlink()
    elif victim == "reserved_doc_missing":
        (docs / "RESERVED-EVALUATION.md").unlink()
    elif victim == "selection":
        _bump(exp / "selection.json", lambda o: o.update(selected_contextual_candidate="M2"))
    else:
        def drop(o):
            del o["dataset_sha256"]
        _bump(exp / "frozen" / "freeze.json", drop)
    with pytest.raises(import_v2.V2ImportError, match=CHAIN_MATCH[victim]):
        imp(env, **kw)
    assert active_runs(env["home"]) == []


def test_model_sha_read_by_regex(env):
    assert import_v2.read_model_sha(env["repo"]) == sha(
        (env["repo"] / "docs/plans/qb-risk-temporal-calibration-v2/evidence/frozen/M3.json").read_bytes())


# ------------------------------------------------------------------ store real
def real_store() -> Path:
    try:
        return import_v2.default_store()
    except Exception:
        return Path("/nonexistent")


@pytest.mark.real_store
@pytest.mark.skipif(not (real_store() / "v1-lineage.json").exists(), reason="store real da v2 ausente")
def test_real_store_exact_copy(tmp_path):
    store = real_store()
    before = integrity.snapshot(store)
    home = tmp_path / "home"
    res = import_v2.import_v2(store, home)
    assert res["counts"] == {"parent": 1, "candidate": 12, "selection": 1}
    assert integrity.compare(before, integrity.snapshot(store)) == {"added": [], "removed": [], "changed": []}
    exp = store / "experiment-verified"
    check_exact(home, store)
    parent = active_runs(home, "parent")[0]
    t = parent.data.tags
    assert t["reserved_not_before_utc"] == NOT_BEFORE
    assert t["design_sha256"] == "342d0d8a9a4df65df9b303467d76be086ca9dded0697fb4dc62723962070b34a"
    assert t["selected_contextual_candidate"] == "M3" and t["seed"] == "20261104"
    assert t["dataset_sha256"] == json.loads((exp / "frozen" / "freeze.json").read_text())["dataset_sha256"]
    assert import_v2.read_model_sha(import_v2.REPO_ROOT) == (
        "38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6")
    assert "code_hash_mismatch" not in t
    client = MlflowClient()

    def walk(rid, path=None):
        out = []
        for a in client.list_artifacts(rid, path):
            out += walk(rid, a.path) if a.is_dir else [a.path]
        return out
    for r in active_runs(home):
        arts = walk(r.info.run_id)
        assert arts and not [a for a in arts if a.endswith((".parquet", ".pkl"))]
