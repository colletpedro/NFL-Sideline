"""Testes do importador do xINT: store sintético em tmp_path (offline) e, marcado, o store real."""
import csv
import hashlib
import json
from pathlib import Path

import pytest
from mlflow import MlflowClient

import import_xint
import integrity
import tracking

STORE_REL = "qb-expected-interceptions-v1/20261105-v1"
COLS = ["model", "group", "n", "observed_interceptions", "expected_interceptions", "observed_expected_ratio",
        "prevalence", "mean_prediction", "log_loss", "brier", "average_precision", "roc_auc"]
GROUPS = ("all", "ftn_1", "ftn_0")
MODELS = import_xint.MODELS
CAL_COLS = ["model", "group", "bin", "n", "observed_interceptions", "expected_interceptions", "mean_prediction",
            "observed_rate", "support_sufficient"]
CONFIG = {"version": "1.0.0", "model_family": "fam", "target": "interception", "risk_input": "worthy",
          "development_years": [2023, 2024], "evaluation_year": 2025, "application_year": 2026,
          "C_grid": [0.1, 1.0], "solver": "lbfgs", "max_iter": 2000, "tol": 1e-9, "seed": 20261105,
          "bootstrap_replicates": 2000, "calibration_edges": [0, 0.5, 1.0000001], "selection": "regra congelada",
          "scope": "retro"}
TRAIN = {"B0": {2023: [2022], 2024: [2022, 2023]}, "B1": {2023: [2022], 2024: [2022, 2023]},
         "B2": {2023: [2022], 2024: [2023]}, "C": {2023: [2022], 2024: [2022, 2023]}}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def wjson(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1))


def wcsv(path: Path, cols, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        w.writerows(rows)


def metric_rows(seed: float, models=MODELS, empty_auc_first=False):
    rows = []
    for mi, m in enumerate(models):
        for gi, g in enumerate(GROUPS):
            x = seed + 0.01 * mi + 0.003 * gi
            auc = "" if (empty_auc_first and mi == 0 and gi == 0) else repr(0.5 + x / 3)
            rows.append([m, g, 100 + gi, 5 + mi, repr(4.5 + x), repr(1.1 + x), repr(0.02 + x / 9), repr(0.021 + x / 7),
                         repr(0.05 + x), repr(0.012 + x / 5), repr(0.4 + x / 2), auc])
    return rows


def pair_block(seed):
    return {"brier": {"delta": -seed, "games": 50, "high": seed / 3, "low": -2 * seed, "reps": 2000, "seed": 20261105},
            "log_loss": {"delta": -2 * seed, "games": 50, "high": seed / 5, "low": -3 * seed, "reps": 2000,
                         "seed": 20261105}}


CONTRACT_BYTES = b"RESEARCH-CONTRACT xint sintetico"
PAIRS = ("B1-B0", "B2-B1", "C-B0", "C-B1", "C-B2")


def make_store(root: Path, scores=None, chosen=0.1, amend=True, null_auc=False):
    """Store xINT falso (mesmos nomes/esquemas, hashes coerentes) + referências (código, config, MODEL_SHA)."""
    store = root / "stores" / STORE_REL
    code = root / "code"
    code.mkdir(parents=True, exist_ok=True)
    cfg_bytes = json.dumps(CONFIG, indent=2).encode()
    (code / "config.json").write_bytes(cfg_bytes)
    wjson(store / "config.json", CONFIG)  # json.dumps(indent=1) difere em bytes; igualdade vale por conteúdo
    code_hashes = {}
    for name in ("common.py", "data.py", "evaluate.py", "risk_model.py"):
        (code / name).write_bytes(f"# {name}\n".encode())
        code_hashes[name] = sha((code / name).read_bytes())
    original_run = b"# run original\n"
    code_hashes["run.py"] = sha(original_run)
    (code / "run.py").write_bytes(b"# run emendado\n" if amend else original_run)

    dev = store / "development"
    ev = store / "evaluation"
    # modelos
    model_bytes = {}
    for k in MODELS:
        b = json.dumps({"kind": k, "train_years": [2022, 2023, 2024]}).encode()
        (dev / "evaluation_models").mkdir(parents=True, exist_ok=True)
        (dev / "evaluation_models" / f"{k}.json").write_bytes(b)
        model_bytes[k] = sha(b)
        for y in (2023, 2024):
            name = f"C_{chosen!r}_{y}.json" if k == "C" else f"{k}_{y}.json"
            wjson(dev / "models" / name, {"kind": k, "train_years": TRAIN[k][y]})
    for y, seed in ((2023, 0.01), (2024, 0.02)):
        wcsv(dev / f"metrics_{y}.csv", COLS, metric_rows(seed, empty_auc_first=null_auc and y == 2023))
    wcsv(dev / "development" / "metrics.csv", COLS, metric_rows(0.03))
    wjson(dev / "development" / "paired_bootstrap.json",
          {g: {p: pair_block(0.0005 * (i + 1) + 0.0002 * gi) for i, p in enumerate(PAIRS)}
           for gi, g in enumerate(GROUPS)})
    (dev / "development" / "pass_predictions.parquet").write_bytes(b"pq")
    scores = scores or [{"C": 0.1, "pooled_log_loss": 0.047}, {"C": 1.0, "pooled_log_loss": 0.0471}]
    selection = {"C_grid_scores": scores, "chosen_C": chosen, "context_calibration_gate": False,
                 "context_useful": False, "decision_data_years": [2023, 2024], "no_2025_or_2026_selection": True,
                 "paired": {p: pair_block(0.001 * (i + 1)) for i, p in enumerate(PAIRS)}, "rule": "regra", "selected": "B2"}
    wjson(dev / "selection.json", selection)
    model_json = b'{"format":"xint-ftn-reference-v1"}'
    (store / "final").mkdir(parents=True, exist_ok=True)
    (store / "final" / "model.json").write_bytes(model_json)
    model_sha = sha(model_json)
    contract = root / "RESEARCH-CONTRACT.md"
    contract.write_bytes(CONTRACT_BYTES)
    freeze = {"code_sha256": code_hashes, "config": CONFIG, "config_sha256": sha((code / "config.json").read_bytes()),
              "contract_sha256": sha(CONTRACT_BYTES), "evaluation_model_hashes": model_bytes, "format": "xint-research-freeze-v1",
              "not_M3": True, "retrospective_temporal": True, "selection": selection, "target": "interception"}
    wjson(dev / "freeze.json", freeze)
    fsha = sha((dev / "freeze.json").read_bytes())
    wjson(ev / "receipt.json", {"evaluation_year": 2025, "freeze_sha256": fsha, "selected": "B2"})
    wcsv(ev / "metrics.csv", COLS, metric_rows(0.05))
    cal_rows = [[m, g, f"[{b}, {b + 1})", 10 + b, 1, repr(0.5 + b), "" if b == 0 else repr(0.1 * b), "", "False"]
                for m in MODELS for g in GROUPS for b in range(3)]
    wcsv(ev / "calibration.csv", CAL_COLS, cal_rows)
    wjson(ev / "paired_bootstrap.json", {g: {p: pair_block(0.002 * (i + 1) + 0.0001 * gi) for i, p in enumerate(PAIRS)}
                                         for gi, g in enumerate(GROUPS)})
    (ev / "pass_predictions.parquet").write_bytes(b"pq-ev")
    wjson(store / "final" / "fixed.json", {"development_freeze_sha256": fsha, "fit_years": [2025],
                                           "model_id": "XINT-B2", "model_sha256": model_sha, "selected": "B2"})
    app = store / "application-complete"
    wcsv(app / "metrics.csv", COLS, metric_rows(0.07, models=("B2",)))
    wjson(app / "coverage.json", {"completed_games": 3})
    wcsv(app / "players.csv", ["gsis_id", "name"], [["00-1", "A"]])
    wjson(app / "fixed.json", {"fit_years": [2025], "model_id": "XINT-B2", "model_sha256": model_sha, "selected": "B2"})
    (app / "cases").mkdir(parents=True, exist_ok=True)
    (app / "cases" / "c.csv").write_text("x\n")
    (app / "consumer").mkdir(parents=True, exist_ok=True)
    (app / "consumer" / "index.json").write_text("{}")
    (app / "pass_predictions.parquet").write_bytes(b"pq-app")
    fig = store / "figures-reviewed"
    fig.mkdir(parents=True, exist_ok=True)
    (fig / "calibration.png").write_bytes(b"png")
    (fig / "support.csv").write_text("a\n1\n")
    (store / "build").mkdir(parents=True, exist_ok=True)
    dataset = b"fake-parquet"
    (store / "build" / "dataset.parquet").write_bytes(dataset)
    wjson(store / "build" / "manifest.json", {"dataset_sha256": sha(dataset), "rows": 321})
    wjson(store / "build" / "coverage.json", {"completed_games": 3})
    wjson(store / "reproduction-offline" / "reproduction.json", {"byte_equal_files": 156})
    wjson(store / "output-fix.json", {"after": sha(b"# run emendado\n"), "before": sha(original_run),
                                      "original_freeze_sha256": fsha, "reason": "r"})
    return {"store": store, "stores": root / "stores", "code": code, "model_sha": model_sha, "fsha": fsha,
            "contract": contract}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(tmp_path / "stores"))
    e = make_store(tmp_path)
    e["home"] = tmp_path / "mlflow home"
    return e


def run_import(e, **kw):
    return import_xint.import_xint(e["store"], e["home"], code_dir=e["code"], config_path=e["code"] / "config.json",
                                   model_sha=kw.pop("model_sha", e["model_sha"]),
                                   contract_path=kw.pop("contract_path", e["contract"]), **kw)


def active_runs(home, role=None):
    exp_id = tracking.ensure_experiment("xint", home)
    q = f"tags.role = '{role}'" if role else ""
    return MlflowClient().search_runs([exp_id], filter_string=q, max_results=1000)


def all_artifacts(client, rid, path=None):
    out = []
    for a in client.list_artifacts(rid, path):
        out += all_artifacts(client, rid, a.path) if a.is_dir else [a.path]
    return out


def csv_expected(path, model=None, prefix=""):
    """{chave: valor} copiado do CSV; ignora vazios (que viram null_metrics)."""
    out, nulls = {}, []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if model is not None and r["model"] != model:
                continue
            for c, v in r.items():
                if c in ("model", "group"):
                    continue
                key = f"{prefix}{r['group']}.{c}"
                if v == "":
                    nulls.append(key)
                else:
                    out[key] = float(v)
    return out, nulls


def check_exact(store: Path, home: Path):
    """Compara TODAS as métricas copiadas com os CSV/JSON de origem."""
    jl = lambda p: json.loads((store / p).read_text())  # noqa: E731
    sel = jl("development/selection.json")
    chosen = sel["chosen_C"]
    folds = {(r.data.params["year"], r.data.params["model"]): r for r in active_runs(home, "fold")}
    assert len(folds) == 8
    for y in (2023, 2024):
        for m in MODELS:
            r = folds[(str(y), m)]
            exp, nulls = csv_expected(store / "development" / f"metrics_{y}.csv", m)
            assert r.data.metrics == exp
            assert json.loads(r.data.tags.get("null_metrics", "[]")) == nulls
            fname = f"C_{chosen!r}_{y}.json" if m == "C" else f"{m}_{y}.json"
            mf = jl(f"development/models/{fname}")
            assert r.data.params["train_years"] == json.dumps(mf["train_years"], separators=(",", ":"))
            assert (r.data.params.get("C") == str(chosen)) == (m == "C")
    (s,) = active_runs(home, "selection")
    exp = {f"pooled_log_loss.C_{x['C']}": x["pooled_log_loss"] for x in sel["C_grid_scores"]}
    for pair, mets in sel["paired"].items():
        for met, v in mets.items():
            for part in ("delta", "low", "high"):
                exp[f"paired.{pair}.{met}.{part}"] = v[part]
    boot = jl("development/development/paired_bootstrap.json")
    for g in ("ftn_0", "ftn_1"):  # grupos do bootstrap de desenvolvimento (`all` já vem de selection.json)
        for pair, mets in boot[g].items():
            for met, v in mets.items():
                for part in ("delta", "low", "high"):
                    exp[f"paired.{g}.{pair}.{met}.{part}"] = v[part]
    assert not [k for k in exp if k.startswith("paired.all.")]
    pooled, _ = csv_expected(store / "development" / "development" / "metrics.csv")
    with open(store / "development" / "development" / "metrics.csv", newline="") as f:
        for r in csv.DictReader(f):
            for c, v in r.items():
                if c not in ("model", "group") and v != "":
                    exp[f"pooled.{r['model']}.{r['group']}.{c}"] = float(v)
    assert s.data.metrics == exp
    for g in ("ftn_0", "ftn_1"):
        for pair, mets in boot[g].items():
            for met, v in mets.items():
                for part in ("games", "reps", "seed"):
                    assert s.data.params[f"paired.{g}.{pair}.{met}.{part}"] == str(v[part])
    assert s.data.tags["selected"] == sel["selected"] and s.data.tags["chosen_C"] == str(chosen)
    assert s.data.tags["rule"] == sel["rule"] and s.data.tags["context_useful"] == "false"
    pe = jl("evaluation/paired_bootstrap.json")
    evs = {r.data.params["model"]: r for r in active_runs(home, "evaluation")}
    assert set(evs) == set(MODELS)
    for m, r in evs.items():
        exp, _ = csv_expected(store / "evaluation" / "metrics.csv", m)
        for g, pairs in pe.items():
            for pair, mets in pairs.items():
                if pair.split("-")[0] == m:
                    for met, v in mets.items():
                        for part in ("delta", "low", "high"):
                            exp[f"paired.{g}.{pair}.{met}.{part}"] = v[part]
                        assert r.data.params[f"paired.{g}.{pair}.{met}.games"] == str(v["games"])
        assert r.data.metrics == exp
        assert r.data.tags["selected"] == ("true" if m == sel["selected"] else "false")
    (a,) = active_runs(home, "application")
    exp, _ = csv_expected(store / "application-complete" / "metrics.csv", prefix="descriptive_only.")
    assert a.data.metrics == exp and a.data.tags["metrics_scope"] == "descriptive_only"
    (fin,) = active_runs(home, "final")
    fixed = jl("final/fixed.json")
    assert fin.data.params["model_id"] == fixed["model_id"] and fin.data.tags["model_sha256"] == fixed["model_sha256"]
    (p,) = active_runs(home, "parent")
    assert p.data.tags["upstream_m3_note"] == "not_M3" and p.data.tags["selection_rule"] == jl("config.json")["selection"]


def test_structure_tags_and_exact_metrics(env):
    res = run_import(env)
    assert res["created"] and res["counts"] == {"parent": 1, "fold": 8, "selection": 1, "evaluation": 4,
                                                "final": 1, "application": 1}
    runs = active_runs(env["home"])
    assert len(runs) == 16
    (parent,) = [r for r in runs if r.data.tags["role"] == "parent"]
    assert parent.info.run_id == res["parent_run_id"] and parent.info.status == "FINISHED"
    for r in runs:
        t = r.data.tags
        tracking.validate_tags(t)
        assert t["source_store"] == STORE_REL and t["source_freeze_sha256"] == env["fsha"]
        assert t["design_sha256"] == sha((env["code"] / "config.json").read_bytes()) and t["seed"] == "20261105"
        assert t["dataset_sha256"] == sha(b"fake-parquet") and t["experiment_family"] == "xint-ftn-v1"
        assert r.info.status == "FINISHED"
        if t["role"] != "parent":
            assert t["mlflow.parentRunId"] == parent.info.run_id
    pt = parent.data.tags
    assert pt["selected"] == "B2" and pt["chosen_C"] == "0.1" and pt["model_id"] == "XINT-B2"
    assert pt["model_sha256"] == env["model_sha"] and pt["code_amendment"] == "output-fix run.py"
    assert parent.data.params["C_grid"] == "[0.1,1.0]"
    assert parent.data.metrics["build_rows"] == 321
    check_exact(env["store"], env["home"])
    # start_time pelo mtime da origem
    fold = [r for r in runs if r.data.tags["role"] == "fold"][0]
    src = env["store"] / "development" / f"metrics_{fold.data.params['year']}.csv"
    assert fold.info.start_time == int(src.stat().st_mtime * 1000)


def test_artifacts_scope(env):
    run_import(env)
    client = MlflowClient()
    runs = {(r.data.tags["role"], r.data.tags.get("model")): r for r in active_runs(env["home"])}
    for r in active_runs(env["home"]):
        arts = all_artifacts(client, r.info.run_id)
        assert not [a for a in arts if a.endswith((".parquet", ".pkl"))]
        assert not [a for a in arts if "consumer" in a or "cases" in a or "pass_predictions" in a]
    parent = [r for r in active_runs(env["home"]) if r.data.tags["role"] == "parent"][0]
    pa = set(all_artifacts(client, parent.info.run_id))
    assert {"freeze.json", "selection.json", "config.json", "manifest.json", "coverage.json", "output-fix.json",
            "source_files.json", "reproduction-offline/reproduction.json", "figures-reviewed/calibration.png"} <= pa
    sf = json.loads(Path(client.download_artifacts(parent.info.run_id, "source_files.json")).read_text())
    paths = {x["path"] for x in sf}
    assert "build/dataset.parquet" in paths and "evaluation/pass_predictions.parquet" in paths
    assert all(len(x["sha256"]) == 64 for x in sf)
    ev_b2 = runs[("evaluation", "B2")]
    assert set(all_artifacts(client, ev_b2.info.run_id)) == {"B2.json", "calibration_B2.csv"}
    cal = Path(client.download_artifacts(ev_b2.info.run_id, "calibration_B2.csv")).read_text().splitlines()
    assert len(cal) == 1 + 3 * 3 and all(line.startswith("B2,") for line in cal[1:])
    assert set(all_artifacts(client, runs[("final", None)].info.run_id)) == {"fixed.json", "model.json"}
    assert set(all_artifacts(client, runs[("application", None)].info.run_id)) == {"coverage.json", "players.csv",
                                                                                    "fixed.json"}
    assert set(all_artifacts(client, runs[("fold", "C")].info.run_id)) <= {"C_0.1_2023.json", "C_0.1_2024.json"}


def test_idempotent(env):
    a = run_import(env)
    b = run_import(env)
    assert not b["created"] and b["parent_run_id"] == a["parent_run_id"]
    assert len(active_runs(env["home"])) == 16


def test_store_untouched(env):
    before = integrity.snapshot(env["stores"])
    run_import(env)
    assert integrity.compare(before, integrity.snapshot(env["stores"])) == {"added": [], "removed": [], "changed": []}


def test_rollback_on_midway_failure(env):
    # CSV de aplicação inválido: lido só ao criar a última execução (depois do pai, folds, seleção e avaliações)
    (env["store"] / "application-complete" / "metrics.csv").write_text("model,group,log_loss\nB2,all,abc\n")
    with pytest.raises(import_xint.XintImportError, match="ValueError"):
        run_import(env)
    assert active_runs(env["home"]) == []
    deleted = MlflowClient().search_runs([tracking.ensure_experiment("xint", env["home"])],
                                         run_view_type=2, max_results=1000)
    assert len(deleted) > 10


def _tamper(e, victim):
    s = e["store"]
    kw = {}
    if victim == "receipt":
        r = json.loads((s / "evaluation" / "receipt.json").read_text())
        r["freeze_sha256"] = "0" * 64
        wjson(s / "evaluation" / "receipt.json", r)
    elif victim == "fixed_freeze":
        r = json.loads((s / "final" / "fixed.json").read_text())
        r["development_freeze_sha256"] = "1" * 64
        wjson(s / "final" / "fixed.json", r)
    elif victim == "eval_model":
        (s / "development" / "evaluation_models" / "B1.json").write_bytes(b"alterado")
    elif victim == "final_model":
        (s / "final" / "model.json").write_bytes(b"alterado")
    elif victim == "model_sha_ref":
        kw["model_sha"] = "2" * 64
    elif victim == "dataset":
        (s / "build" / "dataset.parquet").write_bytes(b"outro")
    elif victim == "config_ref":
        (e["code"] / "config.json").write_text("{}")
    elif victim == "code_other":
        (e["code"] / "common.py").write_text("# mudou\n")
    elif victim == "contract":
        e["contract"].write_text("outro contrato")
    elif victim == "contract_missing":
        e["contract"].unlink()
    elif victim == "selection_json":
        sel = json.loads((s / "development" / "selection.json").read_text())
        sel["rule"] = "outra regra"
        wjson(s / "development" / "selection.json", sel)
    elif victim == "no_fix":
        (s / "output-fix.json").unlink()
    elif victim == "fix_before":
        f = json.loads((s / "output-fix.json").read_text())
        f["before"] = "3" * 64
        wjson(s / "output-fix.json", f)
    elif victim == "fix_after":
        f = json.loads((s / "output-fix.json").read_text())
        f["after"] = "4" * 64
        wjson(s / "output-fix.json", f)
    elif victim == "fix_freeze":
        f = json.loads((s / "output-fix.json").read_text())
        f["original_freeze_sha256"] = "5" * 64
        wjson(s / "output-fix.json", f)
    return kw


CHAIN_MATCH = {
    "receipt": r"sha256\(freeze.json\).*receipt.json freeze_sha256",
    "fixed_freeze": r"sha256\(freeze.json\).*fixed.json development_freeze_sha256",
    "eval_model": r"sha256\(evaluation_models/B1.json\).*freeze.evaluation_model_hashes\[B1\]",
    "final_model": r"sha256\(final/model.json\).*fixed.json model_sha256",
    "model_sha_ref": r"sha256\(final/model.json\).*MODEL_SHA do laboratório",
    "dataset": r"sha256\(dataset.parquet\).*manifest.json dataset_sha256",
    "config_ref": r"sha256\(config.json do código\).*freeze.config_sha256",
    "code_other": r"sha256\(common.py\).*freeze.code_sha256\[common.py\]",
    "no_fix": r"Arquivo ausente: .*output-fix.json",
    "fix_before": "output-fix.json não o explica",
    "fix_after": "output-fix.json não o explica",
    "fix_freeze": "output-fix.json não o explica",
    "contract": r"sha256\(RESEARCH-CONTRACT.md\).*freeze.contract_sha256",
    "contract_missing": r"Arquivo de referência ausente.*RESEARCH-CONTRACT.md",
    "selection_json": r"selection.json difere de freeze.selection",
}


@pytest.mark.parametrize("victim", list(CHAIN_MATCH))
def test_hash_chain_failures(env, victim):
    kw = _tamper(env, victim)
    with pytest.raises(import_xint.XintImportError, match=CHAIN_MATCH[victim]):
        run_import(env, **kw)
    exp_id = tracking.ensure_experiment("xint", env["home"])
    assert MlflowClient().search_runs([exp_id], run_view_type=3, max_results=10) == []  # nada criado, nem apagado


def test_run_py_unchanged_needs_no_amendment(tmp_path, monkeypatch):
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(tmp_path / "stores"))
    e = make_store(tmp_path, amend=False)
    e["home"] = tmp_path / "home"
    (e["store"] / "output-fix.json").write_text("{}")  # irrelevante quando run.py bate com o freeze
    run_import(e)
    (parent,) = active_runs(e["home"], "parent")
    assert "code_amendment" not in parent.data.tags


def test_amendment_tag_has_hashes(env):
    run_import(env)
    (parent,) = active_runs(env["home"], "parent")
    fix = json.loads((env["store"] / "output-fix.json").read_text())
    assert parent.data.tags["code_amendment_before"] == fix["before"]
    assert parent.data.tags["code_amendment_after"] == fix["after"]
    assert parent.data.tags["code_amendment_original_freeze_sha256"] == env["fsha"]


def test_chosen_c_must_be_argmin(tmp_path, monkeypatch):
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(tmp_path / "stores"))
    e = make_store(tmp_path, chosen=1.0)  # scores favorecem 0.1
    with pytest.raises(import_xint.XintImportError, match=r"chosen_C=1.0 difere do argmin"):
        run_import({**e, "home": tmp_path / "home"})


def test_argmin_tie_prefers_smaller_c(tmp_path, monkeypatch):
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(tmp_path / "stores"))
    tie = [{"C": 0.1, "pooled_log_loss": 0.05}, {"C": 1.0, "pooled_log_loss": 0.05}]
    e = make_store(tmp_path, scores=tie, chosen=0.1)
    e["home"] = tmp_path / "home"
    assert run_import(e)["created"]


def test_empty_metric_becomes_tag(tmp_path, monkeypatch):
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(tmp_path / "stores"))
    e = make_store(tmp_path, null_auc=True)
    e["home"] = tmp_path / "home"
    run_import(e)
    r = [x for x in active_runs(e["home"], "fold") if x.data.params["year"] == "2023" and x.data.params["model"] == "B0"][0]
    assert "all.roc_auc" not in r.data.metrics and json.loads(r.data.tags["null_metrics"]) == ["all.roc_auc"]
    check_exact(e["store"], e["home"])


def test_read_model_sha_by_regex(tmp_path):
    p = tmp_path / "package.py"
    p.write_text("X=1\nMODEL_SHA='" + "a" * 64 + "'\n")
    assert import_xint.read_model_sha(p) == "a" * 64
    p.write_text("nada\n")
    with pytest.raises(import_xint.XintImportError, match="MODEL_SHA não encontrado"):
        import_xint.read_model_sha(p)


# ------------------------------------------------------------------ store real
def real_store() -> Path:
    try:
        return import_xint.default_store()
    except Exception:
        return Path("/nonexistent")


@pytest.mark.real_store
@pytest.mark.skipif(not (real_store() / "output-fix.json").exists(), reason="store real do xINT ausente")
def test_real_store_exact_copy(tmp_path):
    store = real_store()
    before = integrity.snapshot(store)
    home = tmp_path / "home"
    res = import_xint.import_xint(store, home)
    assert res["counts"] == {"parent": 1, "fold": 8, "selection": 1, "evaluation": 4, "final": 1, "application": 1}
    assert integrity.compare(before, integrity.snapshot(store)) == {"added": [], "removed": [], "changed": []}
    check_exact(store, home)
    (parent,) = active_runs(home, "parent")
    assert parent.data.tags["code_amendment"] == "output-fix run.py"
    assert parent.data.tags["seed"] == "20261105" and parent.data.tags["selected"] == "B2"
    client = MlflowClient()
    for r in active_runs(home):
        arts = all_artifacts(client, r.info.run_id)
        assert not [a for a in arts if a.endswith((".parquet", ".pkl"))]
        assert not [a for a in arts if "consumer" in a or "cases" in a or "pass_predictions" in a]
    again = import_xint.import_xint(store, home)
    assert not again["created"] and again["parent_run_id"] == res["parent_run_id"]
