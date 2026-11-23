"""Testes de compare.py: tabela, conferência da seleção e markdown, tudo lido só do MLflow.

Os testes offline criam execuções sintéticas direto com MlflowClient num home temporário (sem stores).
O teste `real_store` importa os três stores reais num home temporário (nunca no home real).
"""
from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest
from mlflow import MlflowClient

import compare
import tracking



# ---------------------------------------------------------------- construtores sintéticos

def mk_run(client, exp_id, name, role, tags=None, params=None, metrics=None, parent=None, freeze="f" * 64,
           status="FINISHED"):
    t = {"role": role, "source_freeze_sha256": freeze, "mlflow.runName": name, **(tags or {})}
    if parent:
        t["mlflow.parentRunId"] = parent
    run = client.create_run(exp_id, start_time=1_000, tags=t, run_name=name)
    rid = run.info.run_id
    from mlflow.entities import Metric, Param
    client.log_batch(rid, metrics=[Metric(k, v, 1_000, 0) for k, v in (metrics or {}).items()],
                     params=[Param(k, str(v)) for k, v in (params or {}).items()])
    client.set_terminated(rid, status, end_time=2_000)
    return rid


def block(ll, br, ap, auc=0.7, oe=1.0):
    return {"log_loss": ll, "brier": br, "pr_auc_average_precision": ap, "roc_auc": auc, "observed_expected": oe}


def v1_spec():
    return {"C": [0.01, 0.1, 1.0, 10.0],
            # (ll, n) por fold; o agregado sai de soma(ll*n)/soma(n)
            "folds": {"context": {0.01: [(0.20, 100), (0.22, 100)], 0.1: [(0.18, 100), (0.20, 100)],
                                  1.0: [(0.19, 100), (0.21, 100)], 10.0: [(0.25, 100), (0.27, 100)]},
                      "depth": {0.01: [(0.21, 100), (0.23, 100)], 0.1: [(0.17, 100), (0.19, 100)],
                                1.0: [(0.18, 100), (0.20, 100)], 10.0: [(0.26, 100), (0.28, 100)]}},
            "chosen": {"context": 0.1, "depth": 0.1}}


def build_v1(home, spec=None, freeze="a" * 64, imported=None):
    spec = spec or v1_spec()
    client = MlflowClient()
    exp = tracking.ensure_experiment("v1", home)
    ptags = {"imported_at_utc": imported} if imported else {}
    parent = mk_run(client, exp, "v1 pai", "parent", ptags, {f"chosen_C.{v}": c for v, c in spec["chosen"].items()},
                    freeze=freeze)
    for v, grid in spec["folds"].items():
        pooled = {}
        for c, recs in grid.items():
            for i, (ll, n) in enumerate(recs):
                mk_run(client, exp, f"fold {v} {c} {i}", "fold", {"variant": v},
                       {"variant": v, "C": c, "validation_year": 2023 + i}, {"log_loss": ll, "n": n},
                       parent=parent, freeze=freeze)
            pooled[c] = sum(ll * n for ll, n in recs) / sum(n for _, n in recs)
        mk_run(client, exp, f"selection {v}", "selection", {"variant": v},
               {"variant": v, "chosen_C": spec["chosen"][v]},
               {f"pooled_validation_log_loss.C_{c}": ll for c, ll in pooled.items()}, parent=parent, freeze=freeze)
        m = {"log_loss": 0.15, "brier": 0.04, "pr_auc_average_precision": 0.08, "roc_auc": 0.62,
             "constant.log_loss": 0.16, "constant.brier": 0.041, "constant.pr_auc_average_precision": 0.05,
             "constant.roc_auc": 0.5, "bootstrap.log_loss.delta": -0.01, "bootstrap.log_loss.low": -0.02,
             "bootstrap.log_loss.high": -0.001, "bootstrap.brier.delta": -0.001, "bootstrap.brier.low": -0.002,
             "bootstrap.brier.high": 0.0001}
        mk_run(client, exp, f"evaluation {v}", "evaluation", {"variant": v},
               {"variant": v, "C": spec["chosen"][v]}, m, parent=parent, freeze=freeze)
    return parent


def v2_spec():
    # (ll, brier, ap) do candidato e do M1 por ano; M3 melhor que M2 no agregado.
    return {"M1": {2024: (0.1468, 0.0400, 0.060), 2025: (0.1412, 0.0390, 0.058), 2026: (0.1376, 0.0380, 0.057)},
            "M2": {2024: (0.1456, 0.0399, 0.062), 2025: (0.1403, 0.0389, 0.059), 2026: (0.1371, 0.0379, 0.058)},
            "M3": {2024: (0.1454, 0.0398, 0.063), 2025: (0.1397, 0.0388, 0.060), 2026: (0.1363, 0.0378, 0.059)},
            "M0": {2024: (0.1468, 0.0401, 0.059), 2025: (0.1412, 0.0391, 0.057), 2026: (0.1373, 0.0381, 0.056)},
            "pooled": {"M2": 0.1430, "M3": 0.1425}, "ci_high": {"M2": -0.0001, "M3": -0.0002},
            "selected": "M3", "decision": "candidate_for_reserved_evaluation_only"}


def build_v2(home, spec=None, freeze="b" * 64):
    spec = spec or v2_spec()
    client = MlflowClient()
    exp = tracking.ensure_experiment("v2", home)
    parent = mk_run(client, exp, "v2 pai", "parent",
                    {"selected_contextual_candidate": spec["selected"],
                     "reserved_status": "awaiting_mature_reserved_window",
                     "reserved_not_before_utc": "2026-12-16T01:15:00+00:00"}, {}, freeze=freeze)
    for year in (2024, 2025, 2026):
        for cand in ("M0", "M1", "M2", "M3"):
            ll, br, ap = spec[cand][year]
            m1 = spec["M1"][year]
            met = {**block(ll, br, ap), "M1.log_loss": m1[0], "M1.brier": m1[1],
                   "M1.pr_auc_average_precision": m1[2], "vs_M1.log_loss.delta": ll - m1[0],
                   "vs_M1.log_loss.low": ll - m1[0] - 0.001, "vs_M1.log_loss.high": ll - m1[0] + 0.001,
                   "vs_M1.brier.delta": br - m1[1], "vs_M1.brier.low": -0.001, "vs_M1.brier.high": 0.001}
            mk_run(client, exp, f"v2 {year} {cand}", "candidate", {"year": year, "candidate": cand},
                   {"year": year, "candidate": cand, "period_status": "known"}, met, parent=parent, freeze=freeze)
    met, tags = {}, {"selected_contextual_candidate": spec["selected"], "decision": spec["decision"]}
    for cand in ("M2", "M3"):
        met[f"{cand}.pooled.log_loss"] = spec["pooled"][cand]
        met[f"{cand}.vs_M1.ll.high"] = spec["ci_high"][cand]
        ok = all(spec[cand][y][0] < spec["M1"][y][0] and spec[cand][y][1] <= spec["M1"][y][1]
                 and spec[cand][y][2] > spec["M1"][y][2] for y in (2024, 2025))
        tags[f"{cand}.per_year_conditions_pass"] = str(ok).lower()
        tags[f"{cand}.eligible"] = str(ok and spec["ci_high"][cand] < 0).lower()
    mk_run(client, exp, "v2 selection", "selection", tags, {"selection_years": "[2024,2025]"}, met, parent=parent,
           freeze=freeze)
    return parent


def xint_spec():
    return {"C_grid": {0.01: 0.04733, 0.1: 0.04702, 1.0: 0.04704}, "chosen": 0.1,
            "pool_ll": {"B0": 0.1088, "B1": 0.0470, "B2": 0.04698, "C": 0.04702},
            "oe_C": {"ftn_1": 1.01, "ftn_0": 0.98},
            "paired": {"B1": {"high": 0.000318, "brier": 0.00004}, "B2": {"high": 0.000753, "brier": 0.00021}},
            "selected": "B2", "useful": "false", "gate": "true"}


def build_xint(home, spec=None, freeze="c" * 64):
    spec = spec or xint_spec()
    client = MlflowClient()
    exp = tracking.ensure_experiment("xint", home)
    parent = mk_run(client, exp, "xint pai", "parent", {"selected": spec["selected"], "chosen_C": str(spec["chosen"])},
                    {}, freeze=freeze)
    cols = ("log_loss", "brier", "average_precision", "roc_auc", "observed_expected_ratio", "n")

    def metrics(ll, groups=("all", "ftn_1", "ftn_0")):
        return {f"{g}.{c}": v for g in groups for c, v in zip(cols, (ll, 0.04, 0.1, 0.7, 1.0, 100.0))}

    for year in (2023, 2024):
        for model in compare.XINT_MODELS:
            mk_run(client, exp, f"fold {year} {model}", "fold", {"model": model},
                   {"year": year, "model": model}, metrics(spec["pool_ll"][model]), parent=parent, freeze=freeze)
    met = {f"pooled_log_loss.C_{c}": v for c, v in spec["C_grid"].items()}
    for model, ll in spec["pool_ll"].items():
        for g in compare.XINT_GROUPS:
            met[f"pooled.{model}.{g}.log_loss"] = ll
            met[f"pooled.{model}.{g}.observed_expected_ratio"] = spec["oe_C"].get(g, 1.0) if model == "C" else 1.0
    for b, p in spec["paired"].items():
        met[f"paired.C-{b}.log_loss.high"] = p["high"]
        met[f"paired.C-{b}.brier.delta"] = p["brier"]
    mk_run(client, exp, "xint selection", "selection",
           {"selected": spec["selected"], "chosen_C": str(spec["chosen"]), "context_useful": spec["useful"],
            "context_calibration_gate": spec["gate"]}, {"chosen_C": spec["chosen"]}, met, parent=parent, freeze=freeze)
    for model in compare.XINT_MODELS:
        mk_run(client, exp, f"eval {model}", "evaluation",
               {"model": model, "selected": str(model == spec["selected"]).lower()}, {"model": model},
               metrics(spec["pool_ll"][model]), parent=parent, freeze=freeze)
    return parent


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("NFL_MLFLOW_HOME", str(tmp_path / "h"))
    h = tracking.configure(tmp_path / "h")
    return h


@pytest.fixture
def full(home):
    build_v1(home)
    build_v2(home)
    build_xint(home)
    return home


def sel_run(home, exp_key, role="selection", variant=None):
    tracking.configure(home)
    client = MlflowClient()
    exp = client.get_experiment_by_name(tracking.EXPERIMENTS[exp_key])
    flt = f"tags.role = '{role}'" + (f" and tags.variant = '{variant}'" if variant else "")
    return client.search_runs([exp.experiment_id], filter_string=flt)[0].info.run_id


# ---------------------------------------------------------------- testes offline

def test_all_consistent_verify_is_empty(full):
    table = compare.build_table(full)
    assert compare.verify(table) == []
    assert table["v1"]["variants"]["context"]["chosen_C_selection"] == 0.1
    assert compare.v2_rule(table["v2"])["chosen"] == "M3"
    x = compare.xint_rule(table["xint"])
    assert (x["selected"], x["chosen_C"], x["context_useful"]) == ("B2", 0.1, False)
    md = compare.render_markdown(table)
    assert "## Verificação" in md and "| FAIL |" not in md and "PASS" in md
    assert "0.046980" in md  # 6 casas decimais
    assert table["v2"]["selection"]["run_id"] in md  # run_id de origem na tabela


def test_xint_useful_branch_selects_c(home):
    spec = copy.deepcopy(xint_spec())
    spec["paired"] = {"B1": {"high": -0.001, "brier": 0.00005}, "B2": {"high": -0.002, "brier": 0.00002}}
    spec.update(selected="C", useful="true")
    build_v1(home), build_v2(home), build_xint(home, spec)
    table = compare.build_table(home)
    assert compare.verify(table) == []
    assert compare.xint_rule(table["xint"])["selected"] == "C"


def test_xint_calibration_gate_blocks_useful(home):
    spec = copy.deepcopy(xint_spec())
    spec["paired"] = {"B1": {"high": -0.001, "brier": 0.0}, "B2": {"high": -0.002, "brier": 0.0}}
    spec["oe_C"] = {"ftn_1": 1.3, "ftn_0": 1.0}  # fora de [0.8, 1.25]
    spec.update(selected="B2", useful="false", gate="false")
    build_v1(home), build_v2(home), build_xint(home, spec)
    assert compare.verify(compare.build_table(home)) == []


def test_v1_tampered_metric_changes_winner(full):
    client = MlflowClient()
    rid = sel_run(full, "v1", variant="context")
    client.log_metric(rid, "pooled_validation_log_loss.C_1.0", 0.01)  # vira o argmin
    problems = compare.verify(compare.build_table(full))
    assert any("v1/context" in p and "chosen_C" in p for p in problems)
    assert any("fold" in p for p in problems)


def test_v1_tie_goes_to_smaller_c(home):
    spec = copy.deepcopy(v1_spec())
    spec["folds"]["context"][1.0] = spec["folds"]["context"][0.1]  # empate exato entre 0.1 e 1.0
    build_v1(home, spec), build_v2(home), build_xint(home)
    table = compare.build_table(home)
    assert compare.v1_argmin(table["v1"]["variants"]["context"]["pooled"]) == 0.1
    assert compare.verify(table) == []


def test_v1_parent_chosen_c_diverges(tmp_path, monkeypatch):
    # params são imutáveis: constrói um v1 cujo pai diz chosen_C.depth=1.0 mas o argmin é 0.1
    home = tracking.configure(tmp_path / "h2")
    spec = copy.deepcopy(v1_spec())
    spec["chosen"]["depth"] = 1.0
    build_v1(home, spec), build_v2(home), build_xint(home)
    problems = compare.verify(compare.build_table(home))
    assert any("v1/depth" in p for p in problems)


def test_v2_tampered_metric_changes_winner(full):
    client = MlflowClient()
    exp = client.get_experiment_by_name(tracking.EXPERIMENTS["v2"])
    m3_2025 = client.search_runs(
        [exp.experiment_id], filter_string="tags.role = 'candidate' and tags.year = '2025' and tags.candidate = 'M3'"
    )[0].info.run_id
    client.log_metric(m3_2025, "log_loss", 0.20)  # M3 deixa de bater M1 em 2025
    problems = compare.verify(compare.build_table(full))
    assert any("v2" in p and "M3" in p for p in problems)
    table = compare.build_table(full)
    assert compare.v2_rule(table["v2"])["chosen"] == "M2"


def test_v2_tampered_tag_selected(full):
    client = MlflowClient()
    client.set_tag(sel_run(full, "v2"), "selected_contextual_candidate", "M2")
    problems = compare.verify(compare.build_table(full))
    assert any("tag" in p and "M3" in p and "M2" in p for p in problems)


def test_v2_no_promotion_when_ci_not_negative(home):
    spec = copy.deepcopy(v2_spec())
    spec["ci_high"] = {"M2": 0.001, "M3": 0.002}
    spec.update(selected="None", decision="no_contextual_promotion")
    build_v1(home), build_v2(home, spec), build_xint(home)
    table = compare.build_table(home)
    assert compare.v2_rule(table["v2"])["chosen"] is None
    assert compare.verify(table) == []


def test_v2_tie_prefers_m2(home):
    spec = copy.deepcopy(v2_spec())
    spec["pooled"] = {"M2": 0.1430, "M3": 0.1430 - 5e-11}
    spec.update(selected="M2")
    build_v1(home), build_v2(home, spec), build_xint(home)
    table = compare.build_table(home)
    assert compare.v2_rule(table["v2"])["chosen"] == "M2"
    assert compare.verify(table) == []


def test_xint_tampered_metric_changes_chosen_c(full):
    client = MlflowClient()
    client.log_metric(sel_run(full, "xint"), "pooled_log_loss.C_1.0", 0.001)
    problems = compare.verify(compare.build_table(full))
    assert any("xINT" in p and "chosen_C" in p for p in problems)


def test_xint_tampered_tag_selected(full):
    client = MlflowClient()
    client.set_tag(sel_run(full, "xint"), "selected", "C")
    problems = compare.verify(compare.build_table(full))
    assert any("xINT" in p and "selected" in p for p in problems)


def test_xint_tampered_pairing_changes_useful(full):
    client = MlflowClient()
    rid = sel_run(full, "xint")
    client.log_metric(rid, "paired.C-B1.log_loss.high", -1.0)
    client.log_metric(rid, "paired.C-B2.log_loss.high", -1.0)
    client.log_metric(rid, "paired.C-B2.brier.delta", 0.0)
    problems = compare.verify(compare.build_table(full))
    assert any("recalculado=True" in p and "tag=false" in p for p in problems)


def test_missing_experiment_is_reported(home):
    build_v1(home), build_v2(home)
    table = compare.build_table(home)
    assert table["xint"]["present"] is False
    problems = compare.verify(table)
    assert any("experimento ausente" in p and "xint-ftn-v1" in p for p in problems)
    md = compare.render_markdown(table)
    assert "ausente" in md and "| FAIL |" in md


def test_failed_run_ignored(full):
    client = MlflowClient()
    rid = sel_run(full, "v1", variant="depth")
    client.set_terminated(rid, "FAILED")
    table = compare.build_table(full)
    assert "depth" not in table["v1"]["variants"]


def test_deleted_run_ignored(full):
    client = MlflowClient()
    client.delete_run(sel_run(full, "v2"))
    table = compare.build_table(full)
    assert table["v2"]["selection"] is None
    assert any("seleção ausente" in p for p in compare.verify(table))


def test_latest_freeze_used_and_listed(home):
    build_v1(home, freeze="a" * 64, imported="2026-01-01T00:00:00+00:00")
    spec = copy.deepcopy(v1_spec())
    spec["chosen"] = {"context": 0.1, "depth": 0.1}
    newer = build_v1(home, spec, freeze="9" * 64, imported="2026-06-01T00:00:00+00:00")
    build_v2(home), build_xint(home)
    table = compare.build_table(home)
    fr = table["v1"]["freezes"]
    assert len(fr) == 2 and fr[0]["used"] and fr[0]["run_id"] == newer
    assert table["v1"]["parent"]["run_id"] == newer
    assert compare.verify(table) == []
    assert "2 freezes" in compare.render_markdown(table)


def test_table_is_json_serializable(full):
    import json
    json.dumps(compare.build_table(full))


# ---------------------------------------------------------------- fronteiras (lógica ORIGINAL x compare.py)
# Os testes abaixo executam de verdade `experiment.select` (v2) e `run.develop` (xINT), importados dos diretórios
# congelados sem gravar bytecode, com só as dependências de dados/ajuste substituídas por monkeypatch (veja
# `_frozen_module`), e comparam a decisão original com `compare.v2_rule` / `compare.xint_rule` sobre os mesmos
# números nos mesmos casos de fronteira.
# Original v2: ll estritamente menor, brier <= , ap estritamente maior, IC high < 0 (estrito); empate de 1e-10 -> M2.
# Original xINT: .8 <= O/E <= 1.25 em ftn_1 e ftn_0, paired log_loss.high < 0 e brier.delta <= .0001 contra B1 e B2.

RESEARCH = Path(__file__).resolve().parents[2]


def _frozen_module(dirname: str, module: str):
    """Importa `research/<dirname>/<module>.py` sem gravar `__pycache__` e sem deixar rastro em `sys.modules`
    (os diretórios congelados têm módulos com nomes iguais, como `common`)."""
    import importlib
    import sys

    d = RESEARCH / dirname
    names = {f.stem for f in d.glob("*.py")}
    stash = {n: sys.modules.pop(n) for n in names if n in sys.modules}
    before, flag = set(sys.modules), sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(d))
    try:
        return importlib.import_module(module)
    finally:
        sys.path.remove(str(d))
        sys.dont_write_bytecode = flag
        for k in set(sys.modules) - before:
            f = getattr(sys.modules[k], "__file__", None)
            if f and Path(f).resolve().is_relative_to(d):
                sys.modules.pop(k)
        sys.modules.update(stash)


@pytest.fixture(scope="module")
def v2_original():
    return _frozen_module("qb_risk_temporal_v2", "experiment")


@pytest.fixture(scope="module")
def xint_original():
    return _frozen_module("qb_expected_interceptions", "run")


def _run_v2_select(exp, spec, monkeypatch):
    """`experiment.select` original sobre as métricas de `spec`; só `known_only`, `protocol`, `scores` e
    `stratified_paired` (bootstrap e pontuação, que dependem de dados reais) são substituídos."""
    import pandas as pd

    retro = [{"candidate": c, "year": y,
              "model": dict(zip(("log_loss", "brier", "pr_auc_average_precision"), spec[c][y])),
              "M1": dict(zip(("log_loss", "brier", "pr_auc_average_precision"), spec["M1"][y]))}
             for c in ("M2", "M3") for y in (2024, 2025)]
    pred = pd.DataFrame({"season": [2024, 2025], "is_interception_worthy": [0, 1], "M1": [0.1, 0.2],
                         "M2": [0.1, 0.2], "M3": [0.1, 0.2]})
    monkeypatch.setattr(exp, "known_only", lambda d: None)
    monkeypatch.setattr(exp, "protocol", lambda: {"selection_years": [2024, 2025], "bootstrap_replicates": 1, "seed": 0})
    monkeypatch.setattr(exp, "stratified_paired", lambda z, p, base, reps, seed: {"ll": {"high": spec["ci_high"][p.name]}})
    monkeypatch.setattr(exp, "scores", lambda y, p: {"log_loss": spec["pooled"][p.name]})
    return exp.select(retro, pred)


def _v2_case(m3_year, ci_high):
    spec = copy.deepcopy(v2_spec())
    for y in (2024, 2025):
        spec["M3"][y] = m3_year(spec["M1"][y])
    spec["ci_high"]["M3"] = ci_high
    return spec


def _assert_v2_matches_original(home, spec, v2_original, monkeypatch, name):
    original = _run_v2_select(v2_original, spec, monkeypatch)
    spec.update(selected=original["selected_contextual_candidate"] or "none", decision=original["decision"])
    build_v1(home), build_v2(home, spec), build_xint(home)
    table = compare.build_table(home)
    rule = compare.v2_rule(table["v2"])
    for cand in ("M2", "M3"):
        assert rule["candidates"][cand]["eligible"] is original["results"][cand]["eligible"], (name, cand)
        assert (rule["candidates"][cand]["per_year_conditions_pass"]
                is original["results"][cand]["per_year_conditions_pass"]), (name, cand)
    assert rule["chosen"] == original["selected_contextual_candidate"], name
    assert rule["decision"] == original["decision"], name
    assert compare.verify(table) == [], name
    return original


@pytest.mark.parametrize("name,m3_year,ci_high,eligible", [
    ("brier igual (<= passa)", lambda m1: (m1[0] - 1e-4, m1[1], m1[2] + 1e-3), -0.0002, True),
    ("brier acima por 1e-9 (reprova)", lambda m1: (m1[0] - 1e-4, m1[1] + 1e-9, m1[2] + 1e-3), -0.0002, False),
    ("log loss igual (< estrito reprova)", lambda m1: (m1[0], m1[1] - 1e-4, m1[2] + 1e-3), -0.0002, False),
    ("AP igual (> estrito reprova)", lambda m1: (m1[0] - 1e-4, m1[1] - 1e-4, m1[2]), -0.0002, False),
    ("IC high == 0 (< estrito reprova)", lambda m1: (m1[0] - 1e-4, m1[1] - 1e-4, m1[2] + 1e-3), 0.0, False),
    ("IC high -1e-12 (passa)", lambda m1: (m1[0] - 1e-4, m1[1] - 1e-4, m1[2] + 1e-3), -1e-12, True),
])
def test_v2_selection_boundaries_match_original(home, v2_original, monkeypatch, name, m3_year, ci_high, eligible):
    original = _assert_v2_matches_original(home, _v2_case(m3_year, ci_high), v2_original, monkeypatch, name)
    assert original["results"]["M3"]["eligible"] is eligible, name  # o original é quem decide
    assert original["selected_contextual_candidate"] == ("M3" if eligible else "M2")


@pytest.mark.parametrize("delta,chosen", [(1e-10, "M2"), (2e-10, "M3"), (0.0, "M2"), (-1e-9, "M2")])
def test_v2_tie_break_matches_original(home, v2_original, monkeypatch, delta, chosen):
    """M2 vence o empate quando pooled(M2) <= melhor + 1e-10 (aqui, M2 = M3 + delta)."""
    spec = copy.deepcopy(v2_spec())
    spec["pooled"] = {"M3": 0.1425, "M2": 0.1425 + delta}
    original = _assert_v2_matches_original(home, spec, v2_original, monkeypatch, f"delta={delta}")
    assert original["selected_contextual_candidate"] == chosen


def _run_xint_develop(run, spec, tmp_path, monkeypatch):
    """`run.develop` original com ajuste/avaliação substituídos por funções que devolvem os números de `spec`.
    Cada modelo é identificado por um marcador numérico nas previsões; `performance` e `comparisons` traduzem o
    marcador nos valores do caso. Devolve o `selection.json` que o original gravaria."""
    import numpy as np
    import pandas as pd

    cfg = {"development_years": [2023, 2024], "C_grid": list(spec["C_grid"]), "selection": "regra sintética"}
    marker = {"B0": -1.0, "B1": -2.0, "B2": -3.0}
    written: dict = {}

    def performance(ev, preds):
        rows = []
        for k, v in preds.items():
            m = float(v[0])
            ll = spec["C_grid"][m] if k == "C" else spec["pool_ll"][k]
            for g in ("all", "ftn_1", "ftn_0"):
                oe = spec["oe_C"].get(g, 1.0) if k == "C" else 1.0
                rows.append({"model": k, "group": g, "log_loss": ll, "observed_expected_ratio": oe})
        return pd.DataFrame(rows)

    def comparisons(ev, preds):
        return {"all": {f"C-{b}": {"log_loss": {"high": p["high"]}, "brier": {"delta": p["brier"]}}
                        for b, p in spec["paired"].items()}}

    def new_dir(out):
        Path(out).mkdir(parents=True)
        return Path(out)

    monkeypatch.setattr(run, "config", lambda: cfg)
    monkeypatch.setattr(run, "new_dir", new_dir)
    monkeypatch.setattr(run, "dataset", lambda build: pd.DataFrame({"season": [2022, 2023, 2023, 2024, 2024, 2025]}))
    monkeypatch.setattr(run, "blocks", lambda d, year: (d, pd.DataFrame({"season": [year, year]})))
    monkeypatch.setattr(run, "fit_reference", lambda train, k, year: {"kind": k})
    monkeypatch.setattr(run, "fit_context", lambda train, c, year: {"C": c})
    monkeypatch.setattr(run, "predict", lambda m, ev: np.full(len(ev), m["C"] if "C" in m else marker[m["kind"]]))
    monkeypatch.setattr(run, "fit_set", lambda train, c, year: {k: {"kind": k} for k in ("B0", "B1", "B2", "C")})
    monkeypatch.setattr(run, "performance", performance)
    monkeypatch.setattr(run, "comparisons", comparisons)
    monkeypatch.setattr(run, "save_eval", lambda *a, **k: None)
    monkeypatch.setattr(run, "environment", lambda out: None)
    monkeypatch.setattr(run, "sha", lambda p: "0" * 64)
    monkeypatch.setattr(run, "write", lambda path, obj: written.__setitem__(Path(path).name, obj))
    run.develop("build-ignorado", tmp_path / "saida")
    return written["selection.json"]


@pytest.mark.parametrize("name,oe1,oe0,high,brier,gate,useful", [
    ("O/E 0.8 e 1.25 (inclusivos)", 0.8, 1.25, -0.001, 0.0001, True, True),
    ("O/E ftn_1 logo abaixo de 0.8", 0.7999999, 1.0, -0.001, 0.0, False, False),
    ("O/E ftn_0 logo acima de 1.25", 1.0, 1.2500001, -0.001, 0.0, False, False),
    ("brier.delta 0.0001 (<= passa)", 1.0, 1.0, -0.001, 0.0001, True, True),
    ("brier.delta 0.00010001 reprova", 1.0, 1.0, -0.001, 0.00010001, True, False),
    ("log_loss.high == 0 reprova (< estrito)", 1.0, 1.0, 0.0, 0.0, True, False),
    ("log_loss.high -1e-12 passa", 1.0, 1.0, -1e-12, 0.0, True, True),
])
def test_xint_useful_boundaries_match_original(home, xint_original, tmp_path, monkeypatch,
                                               name, oe1, oe0, high, brier, gate, useful):
    spec = copy.deepcopy(xint_spec())
    spec["oe_C"] = {"ftn_1": oe1, "ftn_0": oe0}
    spec["paired"] = {"B1": {"high": high, "brier": brier}, "B2": {"high": high, "brier": brier}}
    original = _run_xint_develop(xint_original, spec, tmp_path, monkeypatch)
    assert (original["context_calibration_gate"], original["context_useful"]) == (gate, useful), name  # original
    spec.update(selected=original["selected"], useful=str(original["context_useful"]).lower(),
                gate=str(original["context_calibration_gate"]).lower(), chosen=original["chosen_C"])
    build_v1(home), build_v2(home), build_xint(home, spec)
    table = compare.build_table(home)
    rule = compare.xint_rule(table["xint"])
    assert (rule["context_calibration"], rule["context_useful"]) == (gate, useful), name
    assert rule["selected"] == original["selected"] == ("C" if useful else "B2")
    assert rule["chosen_C"] == original["chosen_C"] == 0.1
    assert compare.verify(table) == [], name


# ---------------------------------------------------------------- stores reais

@pytest.mark.real_store
def test_real_stores_all_consistent(tmp_path):
    root = tracking.stores_root()
    stores = [root / "qb-interception-risk-baseline-v1" / "20261104-v1" / "reproduction-check.json",
              root / "qb-risk-temporal-calibration-v2" / "20261104-v2" / "v1-lineage.json",
              root / "qb-expected-interceptions-v1" / "20261105-v1" / "config.json"]
    if not all(p.exists() for p in stores):
        pytest.skip("stores reais ausentes")
    import import_v1
    import import_v2
    import import_xint
    home = tmp_path / "real-home"
    assert import_v1.import_v1(None, home)["created"]
    assert import_v2.import_v2(None, home)["created"]
    assert import_xint.import_xint(None, home)["created"]
    table = compare.build_table(home)
    assert compare.verify(table) == []
    v1 = table["v1"]["variants"]
    assert v1["context"]["chosen_C_selection"] == 0.1 and v1["depth"]["chosen_C_selection"] == 0.1
    assert v1["context"]["chosen_C_parent"] == 0.1 and v1["depth"]["chosen_C_parent"] == 0.1
    assert compare.v2_rule(table["v2"])["chosen"] == "M3"
    assert table["v2"]["parent_tags"]["selected_contextual_candidate"] == "M3"
    assert table["v2"]["parent_tags"]["reserved_status"]
    x = compare.xint_rule(table["xint"])
    assert (x["selected"], x["chosen_C"], x["context_useful"]) == ("B2", 0.1, False)
    md = compare.render_markdown(table)
    assert "| FAIL |" not in md
    out = tmp_path / "compare-real.md"
    out.write_text(md)
    assert os.path.getsize(out) > 0
