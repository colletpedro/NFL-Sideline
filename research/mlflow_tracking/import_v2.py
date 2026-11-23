"""Importador da calibração temporal QB risk v2 para o MLflow (somente leitura no store).

Lê apenas `experiment-verified/` e `figures-reviewed/` (canônicos), mais `v1-lineage.json`, confere a cadeia de
hashes do congelamento ANTES de criar qualquer execução e cria:

    1 pai (role=parent) + 12 filhas candidate (ano x M0..M3) + 1 selection

Métricas são copiadas dos arquivos, nunca recalculadas. Valores nulos viram a tag `null_metrics`.
Parquets (predictions/splits, linhas reais) nunca viram artefato; só entram no `source_files.json`.
Usa a base comum `importer_base` (hash, guardas, criação de execuções, limpeza).
"""
from __future__ import annotations

import csv
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from mlflow import MlflowClient

import importer_base as base
import tracking
from importer_base import Bag as _Bag, compact as _compact, mtime_ms as _mtime_ms, sha256_file

STORE_NAME = "qb-risk-temporal-calibration-v2/20261104-v2"
CANONICAL_DIRS = ("experiment-verified", "figures-reviewed")
ROOT_FILES = ("v1-lineage.json",)
FAMILY = "qb-risk-temporal-v2"
V1_EXPERIMENT = "qb-iw-baseline-v1"
FIGURE_ARTIFACTS_SUBDIR = "figures"
_FROZEN_FILES = ("freeze.json", "M0.json", "M1.json", "M3.json", "reserved_schedule.csv")

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_REL = "research/qb_risk_lab/pipeline.py"
EVIDENCE_M3_REL = "docs/plans/qb-risk-temporal-calibration-v2/evidence/frozen/M3.json"
PROTOCOL_REL = "research/qb_risk_temporal_v2/protocol.json"
CONTRACTS_DIR_REL = "docs/plans/qb-risk-temporal-calibration-v2"  # EXPERIMENT-PROTOCOL.md, RESERVED-EVALUATION.md
_MODEL_SHA_RE = re.compile(r"""MODEL_SHA\s*=\s*['"]([0-9a-f]{64})['"]""")


class V2ImportError(base.ImporterError):
    """Falha de verificação ou de importação (mensagem em português, pensada para o usuário)."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise V2ImportError(msg)


def _jload(path: Path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise V2ImportError(f"Não foi possível ler JSON {path}: {exc}") from exc


def read_model_sha(repo_root: Path) -> str:
    """Lê a constante MODEL_SHA de research/qb_risk_lab/pipeline.py por regex (sem importar o módulo)."""
    path = Path(repo_root) / PIPELINE_REL
    try:
        text = path.read_text()
    except OSError as exc:
        raise V2ImportError(f"Não foi possível ler {path}: {exc}") from exc
    m = _MODEL_SHA_RE.search(text)
    _require(m is not None, f"MODEL_SHA não encontrado em {path}")
    return m.group(1)


def reserved_not_before(schedule_csv: Path, reserved: dict) -> str:
    """Como `reserved.maturity`: último kickoff (America/New_York -> UTC) da janela reservada + N dias."""
    season, (w0, w1) = reserved["season"], reserved["weeks"]
    kicks = []
    with open(schedule_csv, newline="") as f:
        for row in csv.DictReader(f):
            if (int(row["season"]) == season and row["game_type"] == "REG"
                    and w0 <= int(row["week"]) <= w1):
                _require(bool(row["gameday"]) and bool(row["gametime"]),
                         f"reserved_schedule.csv sem kickoff em {row['game_id']}")
                local = datetime.fromisoformat(f"{row['gameday']}T{row['gametime']}")
                kicks.append(local.replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc))
    _require(bool(kicks), "reserved_schedule.csv não tem jogos da janela reservada")
    delta = timedelta(days=reserved["maturity_days_after_latest_kickoff"])
    return (max(kicks) + delta).isoformat()


# ---------------------------------------------------------------- verificação

def verify_chain(store: Path, repo_root: Path, model_sha: str | None, evidence_m3: Path | None) -> dict:
    """Confere diretórios e a cadeia de hashes. Devolve os JSONs principais já carregados."""
    for d in CANONICAL_DIRS:
        _require((store / d).is_dir(), f"Diretório canônico ausente: {store / d}")
    for f in ROOT_FILES:
        _require((store / f).is_file(), f"Arquivo ausente: {store / f}")
    exp = store / "experiment-verified"
    frozen_dir = exp / "frozen"
    freeze_path = frozen_dir / "freeze.json"
    freeze = _jload(freeze_path)
    for name, expected in freeze.get("files", {}).items():
        p = frozen_dir / name
        _require(p.is_file(), f"Arquivo congelado ausente: {p}")
        got = sha256_file(p)
        _require(got == expected, f"sha256(frozen/{name})={got} difere de freeze.files[{name}]={expected}")
    _require(set(freeze.get("files", {})) >= {"M3.json"}, "freeze.files não lista M3.json")

    model_sha = model_sha or read_model_sha(repo_root)
    m3 = sha256_file(frozen_dir / "M3.json")
    _require(m3 == model_sha, f"sha256(frozen/M3.json)={m3} difere do MODEL_SHA={model_sha}")
    evidence = Path(evidence_m3) if evidence_m3 is not None else repo_root / EVIDENCE_M3_REL
    _require(evidence.is_file(), f"M3 de evidência ausente: {evidence}")
    ev_sha = sha256_file(evidence)
    _require(ev_sha == m3, f"sha256(frozen/M3.json)={m3} difere de sha256({evidence.name} da evidência)={ev_sha}")

    contracts = freeze.get("contracts", {})
    _require(isinstance(contracts, dict) and "protocol.json" in contracts, "freeze.contracts não lista protocol.json")
    for name, expected in contracts.items():
        cpath = repo_root / (PROTOCOL_REL if name == "protocol.json" else f"{CONTRACTS_DIR_REL}/{name}")
        _require(cpath.is_file(), f"Contrato de referência ausente: {cpath} (freeze.contracts[{name}])")
        got = sha256_file(cpath)
        _require(got == expected, f"sha256({name})={got} difere de freeze.contracts[{name}]={expected}")
    protocol_path = repo_root / PROTOCOL_REL
    proto_sha = contracts["protocol.json"]
    protocol = _jload(protocol_path)

    mismatched = []
    for rel, expected in freeze.get("code_hashes", {}).items():
        p = repo_root / rel
        if not p.is_file() or sha256_file(p) != expected:
            mismatched.append(rel)

    _require(bool(freeze.get("dataset_sha256")), "freeze.json não tem dataset_sha256")
    selection = _jload(exp / "selection.json")
    _require(selection.get("selected_contextual_candidate") == freeze.get("selected"),
             f"selection.selected_contextual_candidate={selection.get('selected_contextual_candidate')!r} "
             f"difere de freeze.selected={freeze.get('selected')!r}")
    metrics = _jload(exp / "metrics.json")
    _require(isinstance(metrics, list) and metrics, "metrics.json deve ser uma lista não vazia")
    keys = [(r["year"], r["candidate"]) for r in metrics]
    _require(len(set(keys)) == len(keys), "metrics.json repete (ano, candidato)")
    bins = _jload(exp / "calibration_bins.json")
    for y, c in keys:
        _require(f"{y}_{c}" in bins, f"calibration_bins.json sem a chave {y}_{c}")
    lineage = _jload(store / "v1-lineage.json")
    _require(bool(lineage.get("v1_freeze_sha256")), "v1-lineage.json sem v1_freeze_sha256")
    return {"freeze": freeze, "freeze_sha": sha256_file(freeze_path), "protocol": protocol,
            "protocol_sha": proto_sha, "selection": selection, "metrics": metrics, "bins": bins,
            "lineage": lineage, "code_mismatch": mismatched}


def source_file_records(store: Path) -> list[dict]:
    """Caminho relativo, bytes e sha256 de cada arquivo canônico (inclusive parquets, só listados)."""
    paths = [store / f for f in ROOT_FILES]
    for d in CANONICAL_DIRS:
        for dirpath, _dirs, files in os.walk(store / d):
            paths += [Path(dirpath) / f for f in files]
    return [
        {"path": p.relative_to(store).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
        for p in sorted(paths)
    ]


# ---------------------------------------------------------------- métricas

def _add_numeric(bag: _Bag, block: dict, prefix: str = "") -> None:
    """Copia todo campo numérico de `block` (dicts aninhados e listas de 2 viram .low/.high)."""
    for k, v in block.items():
        if isinstance(v, dict):
            _add_numeric(bag, v, f"{prefix}{k}.")
        elif isinstance(v, list):
            names = ("low", "high") if len(v) == 2 else [str(i) for i in range(len(v))]
            for name, x in zip(names, v):
                bag.add(f"{prefix}{k}.{name}", x)
        elif isinstance(v, str):
            continue  # status/method são texto: tag/param, não métrica
        else:
            bag.add(f"{prefix}{k}", v)


def _flatten_params(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flatten_params(v, f"{prefix}{k}."))
        elif isinstance(v, (list, tuple)):
            out[f"{prefix}{k}"] = _compact(v)
        else:
            out[f"{prefix}{k}"] = v
    return out


# ---------------------------------------------------------------- importação

class _Importer(base.BaseImporter):
    error_cls = V2ImportError
    module_file = Path(__file__)

    def __init__(self, store: Path, client: MlflowClient, exp_id: str, ctx: dict, home: Path) -> None:
        super().__init__(store, client, exp_id, ctx, home)
        self.exp = store / "experiment-verified"

    def tags(self, role: str, extra: dict | None = None) -> dict:
        f, p = self.ctx["freeze"], self.ctx["protocol"]
        t = self.base_tags(f["dataset_sha256"], f["contracts"]["protocol.json"], p["seed"], role)
        t.update({"experiment_family": FAMILY, "canonical_dirs": ",".join(CANONICAL_DIRS),
                  "selected_contextual_candidate": str(f["selected"])})
        t.update(extra or {})
        return t

    # -- execuções ----------------------------------------------------------
    def run_all(self) -> str:
        parent = self.parent_run()
        for rec in self.ctx["metrics"]:
            self.candidate_run(rec, parent)
        self.selection_run(parent)
        self.client.set_terminated(parent, "FINISHED", end_time=_mtime_ms(self.exp / "frozen" / "freeze.json"))
        return parent

    def parent_run(self) -> str:
        c, f, p = self.ctx, self.ctx["freeze"], self.ctx["protocol"]
        params = _flatten_params({k: v for k, v in p.items() if k not in ("selection_rule",)})
        extra = {
            "selection_rule": p["selection_rule"],
            "v1_freeze_sha256": c["lineage"]["v1_freeze_sha256"],
            "upstream_v1_parent_run_id": self.upstream_v1(c["lineage"]["v1_freeze_sha256"]),
            "reserved_status": "awaiting_mature_reserved_window",
            "reserved_not_before_utc": reserved_not_before(self.exp / "frozen" / "reserved_schedule.csv",
                                                           f["reserved"]),
        }
        if c["code_mismatch"]:
            extra["code_hash_mismatch"] = json.dumps(c["code_mismatch"])
        arts = [(self.exp / "frozen" / n, "frozen") for n in _FROZEN_FILES]
        arts += [(self.exp / "selection.json", None), (self.exp / "groups.csv", None),
                 (self.exp / "environment.json", None)]
        for d in sorted((self.exp / "drift").iterdir()):
            if d.is_file() and d.suffix in (".csv", ".json"):
                arts.append((d, "drift"))
        for d in sorted((self.store / "figures-reviewed").iterdir()):
            if d.is_file():
                arts.append((d, FIGURE_ARTIFACTS_SUBDIR))
        with tempfile.TemporaryDirectory() as tmp:
            arts.append((base.temp_json(tmp, "source_files.json", c["source_files"]), None))
            return self.new_run("v2 · calibração temporal · 20261104", "parent",
                                self.exp / "frozen" / "freeze.json", _Bag(), params, extra_tags=extra,
                                artifacts=arts, finish=False)

    def upstream_v1(self, v1_freeze_sha: str) -> str:
        """Pai importado da v1 com este freeze, ou `not_imported` (nunca cria o experimento da v1)."""
        exp = self.client.get_experiment_by_name(V1_EXPERIMENT)
        if exp is None or exp.lifecycle_stage != "active":
            return "not_imported"
        run = tracking.find_parent(exp.experiment_id, v1_freeze_sha)  # só pai FINISHED
        return run.info.run_id if run else "not_imported"

    def candidate_run(self, rec: dict, parent: str) -> str:
        year, cand = rec["year"], rec["candidate"]
        bag = _Bag()
        _add_numeric(bag, rec["model"])
        _add_numeric(bag, rec["M1"], "M1.")
        _add_numeric(bag, rec["difference_vs_M1"], "vs_M1.")
        diag = rec.get("calibration_diagnostic") or {}
        _add_numeric(bag, diag, "calibration.")
        if "same_structure_before_offset_diagnostic" in rec:
            _add_numeric(bag, rec["same_structure_before_offset_diagnostic"], "before_offset.")
        params = {"year": year, "candidate": cand, "period_status": rec["period_status"]}
        if "method" in diag:
            params["calibration_method"] = diag["method"]
        arts = []
        model_path = self.exp / "models" / f"{cand}_{year}.json"
        if model_path.is_file():
            model = _jload(model_path)
            train = model.get("train_years", (model.get("structure") or {}).get("train_years"))
            for k, v in (("kind", model.get("kind")), ("train_years", train),
                         ("calibration_year", model.get("calibration_year")),
                         ("offset", model.get("offset")), ("structure_sha256", model.get("structure_sha256")),
                         ("probability", model.get("probability"))):
                if k in model or (k == "train_years" and train is not None):
                    params[k] = _compact(v) if isinstance(v, list) else ("null" if v is None else v)
            arts.append((model_path, None))
        extra = {"year": str(year), "candidate": cand}
        if "status" in diag:
            extra["calibration_status"] = str(diag["status"])
        with tempfile.TemporaryDirectory() as tmp:
            bp = Path(tmp) / f"calibration_bins_{year}_{cand}.json"
            bp.write_text(json.dumps(self.ctx["bins"][f"{year}_{cand}"], indent=1))
            arts.append((bp, None))
            return self.new_run(f"v2 · {year} · {cand}", "candidate", self.exp / "metrics.json", bag, params,
                                parent=parent, extra_tags=extra, artifacts=arts)

    def selection_run(self, parent: str) -> str:
        sel = self.ctx["selection"]
        bag = _Bag()
        extra = {"decision": str(sel["decision"]), "selected_contextual_candidate": str(
            sel["selected_contextual_candidate"])}
        for cand, res in sorted(sel["results"].items()):
            _add_numeric(bag, res["pooled"], f"{cand}.pooled.")
            _add_numeric(bag, res["difference_vs_M1"], f"{cand}.vs_M1.")
            extra[f"{cand}.eligible"] = str(res["eligible"]).lower()
            extra[f"{cand}.per_year_conditions_pass"] = str(res["per_year_conditions_pass"]).lower()
        params = {"selection_years": _compact(sel["selection_years"]),
                  "reference_if_none": sel.get("reference_if_none")}
        return self.new_run("v2 · selection", "selection", self.exp / "selection.json", bag, params,
                            parent=parent, extra_tags=extra,
                            artifacts=[(self.exp / "selection.json", None)])


def default_store() -> Path:
    return tracking.stores_root() / STORE_NAME


def expected_counts(ctx: dict) -> dict[str, int]:
    """Filhas esperadas por role: uma `candidate` por (ano, candidato) de metrics.json e 1 `selection`."""
    return {"candidate": len(ctx["metrics"]), "selection": 1}


@base.wrap_errors(V2ImportError, "importação v2")
def import_v2(store: Path | None = None, home: Path | None = None, *, repo_root: Path | None = None,
              model_sha: str | None = None, evidence_m3: Path | None = None, rebuild: bool = False) -> dict:
    """Importa a v2. Devolve {parent_run_id, created, counts}. Idempotente por sha256(freeze.json).

    `repo_root`, `model_sha` e `evidence_m3` são injetáveis para testes (padrão: a worktree real, o MODEL_SHA
    lido de qb_risk_lab/pipeline.py e o M3 de evidência em docs/plans). Todos os contratos de `freeze.contracts`
    (protocol.json, EXPERIMENT-PROTOCOL.md, RESERVED-EVALUATION.md) são conferidos; ausência é erro. Pai
    interrompido é limpo antes de importar; `rebuild=True` importa de novo e só então apaga a antiga."""
    store = Path(store) if store is not None else default_store()
    repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
    ctx = verify_chain(store, repo_root, model_sha, evidence_m3)
    ctx["source_files"] = source_file_records(store)
    home = tracking.configure(home)
    exp_id = tracking.ensure_experiment("v2", home)
    client = MlflowClient()
    expected = expected_counts(ctx)
    return base.execute(client, exp_id, home, ctx["freeze_sha"], expected, rebuild, "v2", V2ImportError,
                        lambda: _Importer(store, client, exp_id, ctx, home), Path(__file__))
