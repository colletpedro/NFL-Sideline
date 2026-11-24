"""Tabela de comparação e conferência da seleção, lendo SÓ do MLflow (nunca dos stores científicos).

`build_table()` lê os três experimentos importados (execuções ativas e FINISHED), `verify()` reaplica as regras
de seleção originais sobre os números que estão no MLflow e confronta o resultado com os params/tags gravados,
e `render_markdown()` produz as tabelas em pt-BR com os run_ids de origem de cada linha.

Regras reaplicadas (somente conferência; nada é treinado nem selecionado de novo):
- v1: `pipeline.develop` -> argmin do log loss agregado de validação por C, empate vai ao menor C.
- v2: `experiment.select` -> por ano (2024, 2025) LL < M1, Brier <= M1, AP > M1; IC estratificado agregado
  `ll.high < 0`; menor LL agregado entre elegíveis; empate de 1e-10 prefere M2; senão nenhuma promoção.
- xINT: `run.develop` -> C = argmin do log loss agregado (empate menor C); `useful` exige O/E em [0.8, 1.25] em
  ftn_1 e ftn_0 e, contra B1 e B2, paired log_loss.high < 0 e brier.delta <= 0.0001; referência = B1/B2 de menor
  log loss agregado (empate B1).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from mlflow import MlflowClient
from mlflow.entities import ViewType

import tracking

KEYS = ("v1", "v2", "xint")
TIE_V2 = 1e-10
V1_FOLD_TOL = 1e-9
SCORE_COLS = ("log_loss", "brier", "pr_auc_average_precision", "roc_auc")
XINT_COLS = ("log_loss", "brier", "average_precision", "roc_auc", "observed_expected_ratio", "n")
XINT_MODELS = ("B0", "B1", "B2", "C")
XINT_GROUPS = ("all", "ftn_1", "ftn_0")
V2_YEARS = (2024, 2025)
V2_CANDIDATES = ("M2", "M3")


# ---------------------------------------------------------------- leitura do MLflow

def _pack(run) -> dict:
    """Resumo serializável de uma execução (tags internas `mlflow.*` ficam de fora)."""
    return {
        "run_id": run.info.run_id,
        "name": run.info.run_name,
        "start_time": run.info.start_time,
        "metrics": dict(run.data.metrics),
        "params": dict(run.data.params),
        "tags": {k: v for k, v in run.data.tags.items() if not k.startswith("mlflow.")},
    }


def _search(client: MlflowClient, exp_id: str, filter_string: str) -> list:
    flt = f"{filter_string} and attributes.status = 'FINISHED'"
    return client.search_runs([exp_id], filter_string=flt, run_view_type=ViewType.ACTIVE_ONLY,
                              max_results=5000, order_by=["attributes.start_time DESC"])


def _num(value):
    """Valor -> float, ou None quando ausente ou não finito."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _grid(metrics: dict, prefix: str) -> dict:
    """{C: valor} a partir de chaves `<prefix>C_<valor>`."""
    out = {}
    for key, val in metrics.items():
        if key.startswith(prefix + "C_"):
            try:
                out[float(key[len(prefix) + 2:])] = float(val)
            except ValueError:
                continue
    return dict(sorted(out.items()))


def _by_tag(runs: list[dict], tag: str, role: str | None = None) -> dict:
    out = {}
    for r in runs:
        if role is not None and r["tags"].get("role") != role:
            continue
        out.setdefault(r["tags"].get(tag), []).append(r)
    return out


def _latest_parent(parents: list) -> tuple[dict | None, list[dict]]:
    """Pai mais recente por `imported_at_utc` (ou start_time) e a lista dos freezes existentes."""
    packed = [_pack(p) for p in parents]
    packed.sort(key=lambda r: (r["tags"].get("imported_at_utc", ""), r["start_time"] or 0, r["run_id"]),
                reverse=True)
    freezes = [{"run_id": r["run_id"], "source_freeze_sha256": r["tags"].get("source_freeze_sha256"),
                "imported_at_utc": r["tags"].get("imported_at_utc"), "start_time": r["start_time"],
                "used": i == 0} for i, r in enumerate(packed)]
    return (packed[0] if packed else None), freezes


# ---------------------------------------------------------------- construção da tabela

def _build_v1(children: list[dict], parent: dict) -> dict:
    sel = _by_tag(children, "variant", "selection")
    evals = _by_tag(children, "variant", "evaluation")
    folds = _by_tag(children, "variant", "fold")
    variants = {}
    for v in sorted(k for k in sel if k):
        s = sel[v][0]
        fold_pooled = {}
        acc: dict[float, list] = {}
        for f in folds.get(v, []):
            c, ll, n = _num(f["params"].get("C")), _num(f["metrics"].get("log_loss")), _num(f["metrics"].get("n"))
            if c is not None and ll is not None and n is not None:
                acc.setdefault(c, []).append((ll, n))
        for c, items in sorted(acc.items()):
            fold_pooled[c] = sum(ll * n for ll, n in items) / sum(n for _, n in items)
        e = evals.get(v, [None])[0]
        variants[v] = {
            "selection_run_id": s["run_id"],
            "pooled": _grid(s["metrics"], "pooled_validation_log_loss."),
            "chosen_C_selection": _num(s["params"].get("chosen_C")),
            "chosen_C_parent": _num(parent["params"].get(f"chosen_C.{v}")),
            "fold_run_ids": [f["run_id"] for f in folds.get(v, [])],
            "fold_pooled": fold_pooled,
            "evaluation": None if e is None else {
                "run_id": e["run_id"], "C": _num(e["params"].get("C")), "metrics": e["metrics"]},
        }
    return {"variants": variants}


def _build_v2(children: list[dict], parent: dict) -> dict:
    cands: dict[str, dict] = {}
    for r in children:
        if r["tags"].get("role") != "candidate":
            continue
        year, cand = r["tags"].get("year"), r["tags"].get("candidate")
        cands.setdefault(str(year), {})[cand] = {
            "run_id": r["run_id"], "metrics": r["metrics"],
            "period_status": r["params"].get("period_status")}
    sel = next((r for r in children if r["tags"].get("role") == "selection"), None)
    return {
        "candidates": cands,
        "selection": None if sel is None else {
            "run_id": sel["run_id"], "metrics": sel["metrics"], "tags": sel["tags"]},
        "parent_tags": {k: parent["tags"].get(k) for k in
                        ("selected_contextual_candidate", "reserved_status", "reserved_not_before_utc")},
    }


def _build_xint(children: list[dict], parent: dict) -> dict:
    folds: dict[str, dict] = {}
    evals: dict[str, dict] = {}
    sel = None
    for r in children:
        role = r["tags"].get("role")
        if role == "fold":
            folds.setdefault(str(r["params"].get("year")), {})[r["tags"].get("model")] = {
                "run_id": r["run_id"], "metrics": r["metrics"]}
        elif role == "evaluation":
            evals[r["tags"].get("model")] = {"run_id": r["run_id"], "metrics": r["metrics"],
                                             "selected": r["tags"].get("selected")}
        elif role == "selection":
            sel = r
    return {
        "folds": folds, "evaluation": evals,
        "selection": None if sel is None else {
            "run_id": sel["run_id"], "metrics": sel["metrics"], "params": sel["params"], "tags": sel["tags"],
            "C_grid": _grid(sel["metrics"], "pooled_log_loss.")},
        "parent_tags": {k: parent["tags"].get(k) for k in ("selected", "chosen_C")},
    }


_BUILDERS = {"v1": _build_v1, "v2": _build_v2, "xint": _build_xint}


def build_table(home=None) -> dict:
    """Lê os três experimentos do MLflow em `home` e devolve a tabela (dicts/listas serializáveis em JSON)."""
    home = tracking.configure(Path(home) if home is not None else None)
    client = MlflowClient()
    table: dict = {"home": str(home), "tracking_uri": tracking.tracking_uri(home)}
    for key in KEYS:
        name = tracking.EXPERIMENTS[key]
        exp = client.get_experiment_by_name(name)
        if exp is None or exp.lifecycle_stage != "active":
            table[key] = {"experiment": name, "present": False, "parent": None, "freezes": []}
            continue
        parent, freezes = _latest_parent(_search(client, exp.experiment_id, "tags.role = 'parent'"))
        sec = {"experiment": name, "present": True, "freezes": freezes, "parent": None}
        if parent is not None:
            children = [_pack(r) for r in _search(
                client, exp.experiment_id, f"tags.`mlflow.parentRunId` = '{parent['run_id']}'")]
            sec["parent"] = {"run_id": parent["run_id"], "name": parent["name"], "params": parent["params"],
                             "tags": parent["tags"]}
            sec.update(_BUILDERS[key](children, parent))
        table[key] = sec
    table["warnings"] = _warnings(client, table)
    return table


def _warnings(client: MlflowClient, table: dict) -> list[str]:
    """Avisos que não reprovam a conferência (hoje: elo `upstream_v1_parent_run_id` do pai v2 quebrado)."""
    out: list[str] = []
    parent = (table.get("v2") or {}).get("parent")
    up = ((parent or {}).get("tags") or {}).get("upstream_v1_parent_run_id")
    if up and up != "not_imported":
        try:
            run = client.get_run(up)
            alive = run.info.lifecycle_stage == "active" and run.info.status == "FINISHED"
        except Exception:
            alive = False
        if not alive:
            out.append(
                f"O pai v2 {parent['run_id']} aponta (tag `upstream_v1_parent_run_id`) para o pai v1 {up}, que não "
                "está mais ativo (p.ex. depois de `import v1 --rebuild`). Para refazer o elo: rode "
                "`cli.py import v2 --rebuild` e depois `cli.py register m3` (o M3 nasce no experimento v2).")
    return out


# ---------------------------------------------------------------- regras reaplicadas

def v1_argmin(pooled: dict) -> float | None:
    """argmin do log loss agregado; empate vai ao menor C (como `min((score, C))`)."""
    return min((score, c) for c, score in pooled.items())[1] if pooled else None


def v2_rule(table_v2: dict) -> dict:
    """Reaplica `experiment.select` sobre as métricas do MLflow. Devolve resultado e chaves ausentes."""
    missing: list[str] = []
    cands = table_v2["candidates"]
    sel_metrics = (table_v2["selection"] or {}).get("metrics", {})

    def get(metrics, key, where):
        v = _num(metrics.get(key))
        if v is None:
            missing.append(f"{where}: {key}")
        return v

    result: dict = {}
    for cand in V2_CANDIDATES:
        passes = []
        for year in V2_YEARS:
            row = (cands.get(str(year)) or {}).get(cand)
            if row is None:
                missing.append(f"execução {year}/{cand}")
                passes.append(False)
                continue
            m, w = row["metrics"], f"{year}/{cand}"
            ll, br, ap = (get(m, "log_loss", w), get(m, "brier", w), get(m, "pr_auc_average_precision", w))
            ll1, br1, ap1 = (get(m, "M1.log_loss", w), get(m, "M1.brier", w),
                             get(m, "M1.pr_auc_average_precision", w))
            vals = (ll, br, ap, ll1, br1, ap1)
            passes.append(None not in vals and ll < ll1 and br <= br1 and ap > ap1)
        high = get(sel_metrics, f"{cand}.vs_M1.ll.high", "seleção")
        pooled = get(sel_metrics, f"{cand}.pooled.log_loss", "seleção")
        per_year = len(passes) == 2 and all(passes)
        ci_ok = high is not None and high < 0
        result[cand] = {"per_year_conditions_pass": per_year, "ci_high": high, "ci_ok": ci_ok,
                        "pooled_log_loss": pooled, "eligible": bool(per_year and ci_ok and pooled is not None)}
    eligible = [c for c in V2_CANDIDATES if result[c]["eligible"]]
    chosen = None
    if eligible:
        pooled = {c: result[c]["pooled_log_loss"] for c in eligible}
        best = min(pooled.values())
        chosen = "M2" if "M2" in eligible and pooled["M2"] <= best + TIE_V2 else min(eligible, key=lambda c: pooled[c])
    return {"candidates": result, "chosen": chosen, "missing": missing,
            "decision": "candidate_for_reserved_evaluation_only" if chosen else "no_contextual_promotion"}


def xint_rule(table_x: dict) -> dict:
    """Reaplica `run.develop` sobre as métricas do MLflow. Devolve resultado e chaves ausentes."""
    missing: list[str] = []
    sel = table_x["selection"] or {"metrics": {}, "C_grid": {}}
    m = sel["metrics"]

    def get(key):
        v = _num(m.get(key))
        if v is None:
            missing.append(key)
        return v

    chosen_c = v1_argmin(sel["C_grid"])
    if chosen_c is None:
        missing.append("pooled_log_loss.C_*")
    oe = {g: get(f"pooled.C.{g}.observed_expected_ratio") for g in ("ftn_1", "ftn_0")}
    calibration = all(v is not None and 0.8 <= v <= 1.25 for v in oe.values())
    pair: dict = {}
    for b in ("B1", "B2"):
        pair[b] = {"log_loss_high": get(f"paired.C-{b}.log_loss.high"), "brier_delta": get(f"paired.C-{b}.brier.delta")}
    beats = all(p["log_loss_high"] is not None and p["log_loss_high"] < 0 and p["brier_delta"] is not None
                and p["brier_delta"] <= 0.0001 for p in pair.values())
    useful = bool(calibration and beats)
    ref_ll = {b: get(f"pooled.{b}.all.log_loss") for b in ("B1", "B2")}
    reference = None
    if all(v is not None for v in ref_ll.values()):
        reference = min(("B1", "B2"), key=lambda b: (ref_ll[b], b))
    selected = "C" if useful else reference
    return {"chosen_C": chosen_c, "oe": oe, "context_calibration": calibration, "paired": pair,
            "context_useful": useful, "reference_ll": ref_ll, "reference": reference, "selected": selected,
            "missing": missing}


# ---------------------------------------------------------------- verificação

def _same_float(a, b) -> bool:
    return a is not None and b is not None and math.isclose(a, b, rel_tol=0, abs_tol=1e-12)


def _check(checks: list, name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def _checks_v1(sec: dict, checks: list) -> None:
    if not sec["variants"]:
        _check(checks, "v1 · execuções de seleção presentes", False, "v1: nenhuma execução de seleção encontrada")
    for v, d in sec["variants"].items():
        pooled = d["pooled"]
        best = v1_argmin(pooled)
        _check(checks, f"v1 · {v} · grade de C com log loss agregado", bool(pooled),
               f"v1/{v}: seleção sem métricas pooled_validation_log_loss.C_*")
        _check(checks, f"v1 · {v} · argmin recalculado = chosen_C da execução de seleção",
               _same_float(best, d["chosen_C_selection"]),
               f"v1/{v}: argmin do MLflow={best} difere do param chosen_C da seleção={d['chosen_C_selection']}")
        _check(checks, f"v1 · {v} · argmin recalculado = chosen_C.{v} do pai",
               _same_float(best, d["chosen_C_parent"]),
               f"v1/{v}: argmin do MLflow={best} difere do param chosen_C.{v} do pai={d['chosen_C_parent']}")
        fp = d["fold_pooled"]
        diffs = [c for c in pooled if c not in fp or abs(fp[c] - pooled[c]) > V1_FOLD_TOL]
        _check(checks, f"v1 · {v} · log loss agregado = soma ponderada das execuções fold",
               bool(pooled) and not diffs and len(fp) == len(pooled),
               f"v1/{v}: pooled difere das execuções fold (ou fold ausente) para C={diffs}")
        ev = d["evaluation"]
        ok = ev is not None and _same_float(ev["C"], best) and all(
            _num(ev["metrics"].get(k)) is not None for k in SCORE_COLS)
        _check(checks, f"v1 · {v} · avaliação 2025 usa o C escolhido e tem as métricas",
               ok, f"v1/{v}: execução de avaliação ausente, C diferente do argmin ou métricas faltando")


def _checks_v2(sec: dict, checks: list) -> None:
    rule = v2_rule(sec)
    sel = sec["selection"]
    _check(checks, "v2 · execução de seleção presente", sel is not None, "v2: execução de seleção ausente")
    _check(checks, "v2 · métricas necessárias à regra presentes", not rule["missing"],
           "v2: faltam " + "; ".join(rule["missing"]))
    tags = (sel or {}).get("tags", {})
    ptags = sec["parent_tags"]
    _check(checks, "v2 · candidato recalculado = tag selected_contextual_candidate da seleção",
           (rule["chosen"] or "None") == tags.get("selected_contextual_candidate"),
           f"v2: regra reaplicada={rule['chosen']} difere da tag da seleção={tags.get('selected_contextual_candidate')}")
    _check(checks, "v2 · candidato recalculado = tag selected_contextual_candidate do pai",
           (rule["chosen"] or "None") == ptags.get("selected_contextual_candidate"),
           f"v2: regra reaplicada={rule['chosen']} difere da tag do pai={ptags.get('selected_contextual_candidate')}")
    _check(checks, "v2 · decisão recalculada = tag decision",
           rule["decision"] == tags.get("decision"),
           f"v2: decisão reaplicada={rule['decision']} difere da tag={tags.get('decision')}")
    for cand, r in rule["candidates"].items():
        _check(checks, f"v2 · {cand} · elegibilidade e condições por ano = tags da seleção",
               str(r["eligible"]).lower() == tags.get(f"{cand}.eligible")
               and str(r["per_year_conditions_pass"]).lower() == tags.get(f"{cand}.per_year_conditions_pass"),
               f"v2/{cand}: recalculado eligible={r['eligible']}, por ano={r['per_year_conditions_pass']}; "
               f"tags eligible={tags.get(f'{cand}.eligible')}, por ano={tags.get(f'{cand}.per_year_conditions_pass')}")
    _check(checks, "v2 · reserved_status e reserved_not_before_utc presentes",
           bool(ptags.get("reserved_status")) and bool(ptags.get("reserved_not_before_utc")),
           "v2: pai sem reserved_status/reserved_not_before_utc")


def _checks_xint(sec: dict, checks: list) -> None:
    rule = xint_rule(sec)
    sel = sec["selection"]
    _check(checks, "xINT · execução de seleção presente", sel is not None, "xINT: execução de seleção ausente")
    _check(checks, "xINT · métricas necessárias à regra presentes", not rule["missing"],
           "xINT: faltam " + "; ".join(rule["missing"]))
    tags = (sel or {}).get("tags", {})
    params = (sel or {}).get("params", {})
    ptags = sec["parent_tags"]
    c = rule["chosen_C"]
    _check(checks, "xINT · argmin de C recalculado = param chosen_C da seleção",
           _same_float(c, _num(params.get("chosen_C"))),
           f"xINT: argmin={c} difere do param chosen_C={params.get('chosen_C')}")
    _check(checks, "xINT · argmin de C recalculado = tag chosen_C da seleção",
           _same_float(c, _num(tags.get("chosen_C"))),
           f"xINT: argmin={c} difere da tag chosen_C={tags.get('chosen_C')}")
    _check(checks, "xINT · argmin de C recalculado = tag chosen_C do pai",
           _same_float(c, _num(ptags.get("chosen_C"))),
           f"xINT: argmin={c} difere da tag chosen_C do pai={ptags.get('chosen_C')}")
    _check(checks, "xINT · calibração do contexto (O/E em [0.8, 1.25]) = tag context_calibration_gate",
           str(rule["context_calibration"]).lower() == tags.get("context_calibration_gate"),
           f"xINT: recalculado={rule['context_calibration']} difere da tag={tags.get('context_calibration_gate')}")
    _check(checks, "xINT · context_useful recalculado = tag context_useful",
           str(rule["context_useful"]).lower() == tags.get("context_useful"),
           f"xINT: recalculado={rule['context_useful']} difere da tag={tags.get('context_useful')}")
    _check(checks, "xINT · selecionado recalculado = tag selected da seleção",
           rule["selected"] == tags.get("selected"),
           f"xINT: recalculado={rule['selected']} difere da tag selected={tags.get('selected')}")
    _check(checks, "xINT · selecionado recalculado = tag selected do pai",
           rule["selected"] == ptags.get("selected"),
           f"xINT: recalculado={rule['selected']} difere da tag selected do pai={ptags.get('selected')}")
    flagged = [m for m, e in sec["evaluation"].items() if e["selected"] == "true"]
    _check(checks, "xINT · modelo marcado selected na avaliação 2025 = selecionado recalculado",
           flagged == [rule["selected"]],
           f"xINT: avaliação marca {flagged}, regra reaplicada={rule['selected']}")


_CHECKERS = {"v1": _checks_v1, "v2": _checks_v2, "xint": _checks_xint}


def run_checks(table: dict) -> list[dict]:
    """Todas as conferências, cada uma com `name`, `ok` e `detail` (mensagem do problema)."""
    checks: list[dict] = []
    for key in KEYS:
        sec = table.get(key)
        name = tracking.EXPERIMENTS[key]
        if not sec or not sec.get("present"):
            _check(checks, f"{key} · experimento {name} presente", False, f"experimento ausente: {name}")
            continue
        if sec.get("parent") is None:
            _check(checks, f"{key} · execução-pai FINISHED em {name}", False,
                   f"{name}: nenhuma execução-pai ativa e FINISHED")
            continue
        _check(checks, f"{key} · experimento {name} e execução-pai presentes", True)
        dup: dict[str, int] = {}
        for f in sec["freezes"]:
            dup[f["source_freeze_sha256"]] = dup.get(f["source_freeze_sha256"], 0) + 1
        dups = {sha: n for sha, n in dup.items() if n > 1}
        _check(checks, f"{key} · um só pai FINISHED por freeze", not dups,
               f"{name}: mais de um pai FINISHED para o mesmo freeze "
               f"({', '.join(f'{str(sha)[:12]} ×{n}' for sha, n in dups.items())}); importação duplicada "
               f"(rebuild interrompido?). Rode `cli.py import {key} --rebuild`")
        _CHECKERS[key](sec, checks)
    return checks


def verify(table: dict) -> list[str]:
    """Problemas encontrados (lista vazia = tudo confere)."""
    return [c["detail"] for c in run_checks(table) if not c["ok"]]


# ---------------------------------------------------------------- markdown

def _f(v) -> str:
    v = _num(v)
    return "—" if v is None else f"{v:.6f}"


def _i(v) -> str:
    v = _num(v)
    return "—" if v is None else f"{v:.0f}"


def _c(c) -> str:
    return "—" if c is None else f"{c:g}"


def _id(run_id) -> str:
    return f"`{run_id}`" if run_id else "—"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out + [""]


def _md_header(table: dict) -> list[str]:
    lines = ["# Comparação dos experimentos MLflow", "",
             f"Fonte: `{table['tracking_uri']}` (somente execuções ativas e FINISHED; nenhum store científico é lido).", "",
             "## Experimentos e freezes", ""]
    rows = []
    for key in KEYS:
        sec = table[key]
        used = next((f for f in sec["freezes"] if f["used"]), None)
        rows.append([f"`{sec['experiment']}`", "sim" if sec["present"] else "NÃO", str(len(sec["freezes"])),
                     _id(used["run_id"] if used else None),
                     f"`{used['source_freeze_sha256'][:12]}`" if used and used["source_freeze_sha256"] else "—"])
    lines += _table(["Experimento", "Presente", "Freezes", "Pai usado (run_id)", "Freeze (sha256, 12)"], rows)
    for key in KEYS:
        sec = table[key]
        if len(sec["freezes"]) > 1:
            lines.append(f"Atenção: `{sec['experiment']}` tem {len(sec['freezes'])} freezes; usado o mais recente. "
                         "Freezes: " + ", ".join(f"{_id(f['run_id'])} (sha {str(f['source_freeze_sha256'])[:12]})"
                                                 for f in sec["freezes"]) + ".")
            lines.append("")
    return lines


def _md_v1(sec: dict) -> list[str]:
    lines = ["## v1 · baseline QB interception risk", ""]
    if not sec.get("variants"):
        return lines + ["Sem dados no MLflow.", ""]
    for v, d in sec["variants"].items():
        best = v1_argmin(d["pooled"])
        lines += [f"### Variante `{v}`: log loss agregado de validação por C", ""]
        lines += _table(["C", "Log loss agregado", "Escolhido", "run_id (seleção)"],
                        [[_c(c), _f(ll), "sim" if c == best else "", _id(d["selection_run_id"])]
                         for c, ll in d["pooled"].items()])
        lines.append(f"chosen_C no MLflow: seleção `{_c(d['chosen_C_selection'])}`, pai `{_c(d['chosen_C_parent'])}`; "
                     f"argmin recalculado `{_c(best)}`.")
        lines.append("")
    lines += ["### Avaliação 2025 (modelo contra constante)", ""]
    rows = []
    for v, d in sec["variants"].items():
        ev = d["evaluation"]
        if ev is None:
            continue
        m = ev["metrics"]
        for label, prefix in (("modelo", ""), ("constante", "constant.")):
            rows.append([v, label] + [_f(m.get(prefix + k)) for k in SCORE_COLS] + [_id(ev["run_id"])])
    lines += _table(["Variante", "Linha", "log_loss", "brier", "pr_auc (AP)", "roc_auc", "run_id"], rows)
    lines += ["### Bootstrap pareado por jogo (modelo - constante, avaliação 2025)", ""]
    rows = []
    for v, d in sec["variants"].items():
        ev = d["evaluation"]
        if ev is None:
            continue
        m = ev["metrics"]
        for met in ("log_loss", "brier"):
            rows.append([v, met] + [_f(m.get(f"bootstrap.{met}.{p}")) for p in ("delta", "low", "high")]
                        + [_id(ev["run_id"])])
    lines += _table(["Variante", "Métrica", "delta", "IC low", "IC high", "run_id"], rows)
    return lines


def _md_v2(sec: dict) -> list[str]:
    lines = ["## v2 · calibração temporal", ""]
    cands = sec.get("candidates")
    if not cands:
        return lines + ["Sem dados no MLflow.", ""]
    cols = ["log_loss", "brier", "pr_auc_average_precision", "roc_auc", "observed_expected"]
    vs = ["vs_M1.log_loss.delta", "vs_M1.log_loss.low", "vs_M1.log_loss.high",
          "vs_M1.brier.delta", "vs_M1.brier.low", "vs_M1.brier.high"]
    rows = []
    for year in sorted(cands, key=lambda y: int(y)):
        for cand in sorted(cands[year]):
            r = cands[year][cand]
            m = r["metrics"]
            rows.append([year, cand] + [_f(m.get(k)) for k in cols + vs] + [_id(r["run_id"])])
    lines += _table(["Ano", "Candidato", "LL", "Brier", "AP", "ROC AUC", "O/E",
                     "vs M1 LL delta", "LL low", "LL high", "vs M1 Brier delta", "Brier low", "Brier high",
                     "run_id"], rows)
    rule = v2_rule(sec)
    sel = sec["selection"] or {"run_id": None, "tags": {}}
    lines += ["### Seleção (2024 e 2025)", ""]
    lines += _table(["Candidato", "Condições por ano", "IC agregado LL.high", "LL agregado", "Elegível",
                     "run_id (seleção)"],
                    [[c, "sim" if r["per_year_conditions_pass"] else "não", _f(r["ci_high"]),
                      _f(r["pooled_log_loss"]), "sim" if r["eligible"] else "não", _id(sel["run_id"])]
                     for c, r in rule["candidates"].items()])
    pt = sec["parent_tags"]
    lines += [f"Regra reaplicada: `{rule['chosen']}`; tag `selected_contextual_candidate` da seleção: "
              f"`{sel['tags'].get('selected_contextual_candidate')}`; decisão `{sel['tags'].get('decision')}`.", "",
              f"Avaliação reservada: `reserved_status` = `{pt.get('reserved_status')}`, "
              f"`reserved_not_before_utc` = `{pt.get('reserved_not_before_utc')}`.", ""]
    return lines


def _md_xint(sec: dict) -> list[str]:
    lines = ["## xINT · interceptação observada dado FTN", ""]
    if sec.get("selection") is None:
        return lines + ["Sem dados no MLflow.", ""]
    lines += ["### Folds de desenvolvimento (grupo `all`)", ""]
    rows = []
    for year in sorted(sec["folds"]):
        for model in XINT_MODELS:
            r = sec["folds"][year].get(model)
            if r:
                rows.append([year, model] + [_f(r["metrics"].get(f"all.{k}")) if k != "n" else _i(
                    r["metrics"].get("all.n")) for k in XINT_COLS] + [_id(r["run_id"])])
    lines += _table(["Ano", "Modelo", "log_loss", "brier", "AP", "roc_auc", "O/E", "n", "run_id"], rows)
    sel = sec["selection"]
    lines += ["### Grade de C (log loss agregado de desenvolvimento)", ""]
    rule = xint_rule(sec)
    lines += _table(["C", "Log loss agregado", "Escolhido", "run_id (seleção)"],
                    [[_c(c), _f(ll), "sim" if c == rule["chosen_C"] else "", _id(sel["run_id"])]
                     for c, ll in sel["C_grid"].items()])
    lines += ["### Desenvolvimento agregado por modelo e grupo", ""]
    rows = []
    for model in XINT_MODELS:
        for g in XINT_GROUPS:
            rows.append([model, g, _f(sel["metrics"].get(f"pooled.{model}.{g}.log_loss")),
                         _f(sel["metrics"].get(f"pooled.{model}.{g}.observed_expected_ratio")), _id(sel["run_id"])])
    lines += _table(["Modelo", "Grupo", "log_loss", "O/E", "run_id (seleção)"], rows)
    lines += ["### Bootstrap pareado de desenvolvimento (grupo `all`)", ""]
    rows = []
    for pair in ("C-B0", "C-B1", "C-B2", "B1-B0", "B2-B1"):
        for met in ("log_loss", "brier"):
            rows.append([pair, met] + [_f(sel["metrics"].get(f"paired.{pair}.{met}.{p}"))
                                       for p in ("delta", "low", "high")] + [_id(sel["run_id"])])
    lines += _table(["Par", "Métrica", "delta", "IC low", "IC high", "run_id (seleção)"], rows)
    lines += ["### Avaliação 2025 por modelo e grupo", ""]
    rows = []
    for model in XINT_MODELS:
        e = sec["evaluation"].get(model)
        if not e:
            continue
        for g in XINT_GROUPS:
            rows.append([model, g] + [_f(e["metrics"].get(f"{g}.{k}")) if k != "n" else _i(
                e["metrics"].get(f"{g}.n")) for k in XINT_COLS] + [_id(e["run_id"])])
    lines += _table(["Modelo", "Grupo", "log_loss", "brier", "AP", "roc_auc", "O/E", "n", "run_id"], rows)
    lines += ["### Regra reaplicada", "",
              f"- C escolhido: `{_c(rule['chosen_C'])}` (tag: `{sel['tags'].get('chosen_C')}`).",
              f"- O/E do C em ftn_1 / ftn_0: `{_f(rule['oe']['ftn_1'])}` / `{_f(rule['oe']['ftn_0'])}` "
              f"-> calibração do contexto `{str(rule['context_calibration']).lower()}`.",
              f"- context_useful: `{str(rule['context_useful']).lower()}`; referência `{rule['reference']}`; "
              f"selecionado `{rule['selected']}` (tag: `{sel['tags'].get('selected')}`).", ""]
    return lines


def _md_checks(checks: list[dict]) -> list[str]:
    lines = ["## Verificação", ""]
    lines += _table(["Conferência", "Resultado", "Detalhe"],
                    [[c["name"], "PASS" if c["ok"] else "FAIL", "" if c["ok"] else c["detail"]] for c in checks])
    fails = sum(1 for c in checks if not c["ok"])
    lines.append(f"Resumo: {len(checks) - fails} PASS, {fails} FAIL.")
    return lines + [""]


def _md_warnings(table: dict) -> list[str]:
    lines = ["## Avisos", ""]
    warns = table.get("warnings") or []
    lines += [f"- {w}" for w in warns] if warns else ["Nenhum aviso."]
    return lines + [""]


def render_markdown(table: dict) -> str:
    """Relatório em pt-BR (seis casas decimais; cada linha traz o run_id de origem)."""
    lines = _md_header(table)
    for key, fn in (("v1", _md_v1), ("v2", _md_v2), ("xint", _md_xint)):
        sec = table[key]
        if not sec.get("present") or sec.get("parent") is None:
            lines += [f"## {key}", "", f"Experimento `{sec['experiment']}` ausente ou sem execução-pai FINISHED.", ""]
        else:
            lines += fn(sec)
    lines += _md_warnings(table)
    lines += _md_checks(run_checks(table))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", default=None, help="padrão: NFL_MLFLOW_HOME ou M/editorial/local-artifacts/mlflow")
    ap.add_argument("--json", action="store_true", help="imprime a tabela em JSON em vez de markdown")
    args = ap.parse_args(argv)
    table = build_table(Path(args.home) if args.home else None)
    print(json.dumps(table, indent=1, default=str) if args.json else render_markdown(table))
    return 1 if verify(table) else 0


if __name__ == "__main__":
    raise SystemExit(main())
