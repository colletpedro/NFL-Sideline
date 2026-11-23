"""Importador da baseline QB interception risk v1 para o MLflow (somente leitura no store).

Lê apenas os diretórios canônicos (build-v2, development-v3, evaluation-v1, application-v1, figures-v4, mais
sources.json e reproduction-check.json na raiz), confere a cadeia de hashes do congelamento e cria:

    1 pai (role=parent) + 16 filhas fold + 2 selection + 2 evaluation + 2 application

Métricas são copiadas dos arquivos, nunca recalculadas; a única exceção é o log loss agregado da seleção,
calculado como em `pipeline.develop` (soma log_loss*n / soma n) e conferido contra `chosen_C`.
Parquets (dados FTN linha a linha) nunca são enviados como artefato; só entram no `source_files.json`.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from mlflow import MlflowClient

import importer_base as base
import tracking
from importer_base import METRIC_KEYS, Bag as _Bag, compact as _compact, is_null as _is_null  # noqa: F401
from importer_base import mtime_ms as _mtime_ms, sha256_file  # noqa: F401

STORE_NAME = "qb-interception-risk-baseline-v1/20261104-v1"
CANONICAL_DIRS = ("build-v2", "development-v3", "evaluation-v1", "application-v1", "figures-v4")
ROOT_FILES = ("sources.json", "reproduction-check.json")
FAMILY = "qb-iw-baseline-v1"

# Fonte: docs/plans/mlflow-tracking-v1/facts/v1-store.md §4 (commits que produziram cada saída):
#   build-v2 -> 05c18ed; development-v3 (freeze pré-teste) -> 35ac931; evaluation-v1/application-v1 -> 910dfae.
# O store não grava commits; a proveniência vem do CHECKPOINTS.md e dos hashes de código do environment.json.
SOURCE_COMMITS = {
    "source_code_commit_build": "05c18ed",
    "source_code_commit_development": "35ac931",
    "source_code_commit_evaluation": "910dfae",
}

BOOTSTRAP_PARTS = ("delta", "low", "high")

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = REPO_ROOT / "research" / "qb_interception_risk" / "design.json"
CONTRACT_PATH = REPO_ROOT / "docs" / "plans" / "qb-interception-risk-baseline-v1" / "RESEARCH-CONTRACT.md"


class V1ImportError(base.ImporterError):
    """Falha de verificação ou de importação (mensagem em português, pensada para o usuário)."""


def _jload(path: Path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise V1ImportError(f"Não foi possível ler JSON {path}: {exc}") from exc


def _fmt_c(c) -> str:
    return f"{c:g}"


# ---------------------------------------------------------------- verificação

def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise V1ImportError(msg)


def verify_chain(store: Path, design_path: Path | None = None, contract_path: Path | None = None) -> dict:
    """Confere diretórios e a cadeia de hashes. Devolve os JSONs principais já carregados.

    `design_path`/`contract_path` (padrão: design.json e RESEARCH-CONTRACT.md da worktree) são obrigatórios:
    arquivo de referência ausente é erro (nunca pulado em silêncio)."""
    design_path = DESIGN_PATH if design_path is None else Path(design_path)
    contract_path = CONTRACT_PATH if contract_path is None else Path(contract_path)
    for d in CANONICAL_DIRS:
        _require((store / d).is_dir(), f"Diretório canônico ausente: {store / d}")
    for f in ROOT_FILES:
        _require((store / f).is_file(), f"Arquivo ausente: {store / f}")
    frozen_path = store / "development-v3" / "frozen_config.json"
    frozen = _jload(frozen_path)
    manifest = _jload(store / "build-v2" / "build_manifest.json")
    ev_receipt = _jload(store / "evaluation-v1" / "evaluation_receipt.json")
    app_receipt = _jload(store / "application-v1" / "application_receipt.json")
    repro = _jload(store / "reproduction-check.json")

    dataset_sha = sha256_file(store / "build-v2" / "dataset.parquet")
    _require(dataset_sha == manifest.get("dataset_sha256"),
             f"sha256(dataset.parquet)={dataset_sha} difere de build_manifest.dataset_sha256="
             f"{manifest.get('dataset_sha256')}")
    _require(dataset_sha == frozen.get("dataset_sha256"),
             f"sha256(dataset.parquet)={dataset_sha} difere de frozen_config.dataset_sha256="
             f"{frozen.get('dataset_sha256')}")
    for variant, expected in frozen["models"].items():
        got = sha256_file(store / "development-v3" / f"model_{variant}_2022_2024.json")
        _require(got == expected, f"sha256(model_{variant}_2022_2024.json)={got} difere de "
                                  f"frozen_config.models[{variant}]={expected}")
    freeze_sha = sha256_file(frozen_path)
    for name, receipt in (("evaluation_receipt", ev_receipt), ("application_receipt", app_receipt)):
        _require(freeze_sha == receipt.get("frozen_config_sha256"),
                 f"sha256(frozen_config.json)={freeze_sha} difere de {name}.frozen_config_sha256="
                 f"{receipt.get('frozen_config_sha256')}")
    _require(repro.get("passed") is True, "reproduction-check.json não tem passed == true")
    for label, path, field in (("design.json", design_path, "design_sha256"),
                               ("RESEARCH-CONTRACT.md", contract_path, "contract_sha256")):
        _require(path.is_file(), f"Arquivo de referência ausente: {path} ({label}, conferido contra frozen_config.{field})")
        got = sha256_file(path)
        _require(got == frozen.get(field),
                 f"sha256({label})={got} difere de frozen_config.{field}={frozen.get(field)}")
    return {"frozen": frozen, "manifest": manifest, "ev_receipt": ev_receipt,
            "app_receipt": app_receipt, "freeze_sha": freeze_sha, "dataset_sha": dataset_sha}


def source_file_records(store: Path) -> list[dict]:
    """Caminho relativo, bytes e sha256 de cada arquivo canônico (inclusive parquets)."""
    paths = [store / f for f in ROOT_FILES]
    for d in CANONICAL_DIRS:
        for dirpath, _dirs, files in os.walk(store / d):
            paths += [Path(dirpath) / f for f in files]
    return [
        {"path": p.relative_to(store).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
        for p in sorted(paths)
    ]


def pooled_selection(history: list[dict], design: dict) -> dict:
    """{variant: {C: log loss agregado}} como em `pipeline.develop`: soma(log_loss*n)/soma(n) por C."""
    index = {}
    for rec in history:
        key = (rec["variant"], rec["C"], rec["validation"])
        _require(key not in index, f"development_metrics.json repete {key}")
        index[key] = rec
    out: dict = {}
    for variant in design["variants"]:
        out[variant] = {}
        for c in design["C_grid"]:
            loss, n = 0.0, 0
            for fold in design["folds"]:
                rec = index.get((variant, c, fold["validation"]))
                _require(rec is not None, f"development_metrics.json sem registro ({variant}, C={c}, "
                                          f"validação {fold['validation']})")
                loss += rec["model"]["log_loss"] * rec["model"]["n"]
                n += rec["model"]["n"]
            out[variant][c] = loss / n
    _require(len(index) == len(design["variants"]) * len(design["C_grid"]) * len(design["folds"]),
             "development_metrics.json tem registros além do desenho congelado")
    return out


def check_chosen(pooled: dict, frozen: dict) -> None:
    chosen = frozen.get("chosen_C", {})
    for variant, scores in pooled.items():
        _require(variant in chosen, f"frozen_config.chosen_C não tem a variante {variant!r}")
        best = min((score, c) for c, score in scores.items())[1]  # empate -> menor C
        _require(best == chosen[variant],
                 f"chosen_C[{variant}]={chosen[variant]} difere do argmin recalculado {best}")


# ---------------------------------------------------------------- métricas

# ---------------------------------------------------------------- importação

class _Importer(base.BaseImporter):
    error_cls = V1ImportError
    module_file = Path(__file__)

    def __init__(self, store: Path, client: MlflowClient, exp_id: str, ctx: dict, home: Path) -> None:
        super().__init__(store, client, exp_id, ctx, home)
        self.frozen, self.design = ctx["frozen"], ctx["frozen"]["design"]

    def tags(self, role: str, extra: dict | None = None) -> dict:
        t = self.base_tags(self.ctx["dataset_sha"], self.frozen["design_sha256"], self.design["seed"], role)
        t.update({
            "experiment_family": FAMILY,
            "contract_sha256": self.frozen["contract_sha256"],
            "canonical_dirs": ",".join(CANONICAL_DIRS),
            **SOURCE_COMMITS,
        })
        t.update(extra or {})
        return t

    # -- execuções ----------------------------------------------------------
    def run_all(self) -> str:
        s, d = self.store, self.design
        dev, ev, app, fig = (s / "development-v3", s / "evaluation-v1", s / "application-v1", s / "figures-v4")
        history = _jload(dev / "development_metrics.json")
        pooled = pooled_selection(history, d)
        check_chosen(pooled, self.frozen)
        parent = self.parent_run()
        for rec in history:
            self.fold_run(rec, parent, dev / "development_metrics.json")
        for variant in d["variants"]:
            self.selection_run(variant, pooled[variant], parent, dev / "development_metrics.json")
        eval_metrics = _jload(ev / "metrics.json")
        for variant in d["variants"]:
            self.evaluation_run(variant, eval_metrics[variant], parent)
        for variant in d["variants"]:
            self.application_run(variant, parent)
        self.client.set_terminated(parent, "FINISHED", end_time=_mtime_ms(dev / "frozen_config.json"))
        return parent

    def parent_run(self) -> str:
        s, d, f = self.store, self.design, self.frozen
        bag = _Bag()
        bag.add("build_rows", self.ctx["manifest"]["rows"])
        ar = self.ctx["app_receipt"]
        for k in ("passes", "games", "passers", "observed", "expected_sum"):
            bag.add(f"application_{k}", ar[k])
        bag.add("constant_prevalence", f["constant_prevalence"])
        params = {
            "C_grid": _compact(d["C_grid"]), "folds": _compact(d["folds"]),
            "final_train": _compact(d["final_train"]), "final_test": d["final_test"],
            "application_train": _compact(d["application_train"]),
            "application.season": d["application"]["season"],
            "application.weeks": _compact(d["application"]["weeks"]),
            "bootstrap_replicates": d["bootstrap_replicates"],
            "calibration_edges": _compact(d["calibration_edges"]),
            "variants": _compact(d["variants"]), "solver": d["solver"], "max_iter": d["max_iter"],
            "tol": d["tol"], "posthoc_calibration": d["posthoc_calibration"], "version": d["version"],
            "chosen_C.context": f["chosen_C"]["context"], "chosen_C.depth": f["chosen_C"]["depth"],
            "constant_prevalence": repr(f["constant_prevalence"]),
        }
        # Qualquer chave de chosen_C além de context/depth (variantes futuras) também entra.
        for v, c in f["chosen_C"].items():
            params.setdefault(f"chosen_C.{v}", c)
        arts = [(s / "development-v3" / "frozen_config.json", None),
                (s / "build-v2" / "build_manifest.json", None),
                (s / "evaluation-v1" / "evaluation_receipt.json", None),
                (s / "application-v1" / "application_receipt.json", None),
                (s / "reproduction-check.json", None),
                (s / "application-v1" / "qb_sensitivity.csv", "application")]
        for name in ("calibration_support.csv", "plot_passers.csv", "depth_sensitivity_2026.png",
                     "depth_sensitivity_2026.svg", "difference_per100_2026.png",
                     "difference_per100_2026.svg", "observed_expected_2026.png", "observed_expected_2026.svg"):
            arts.append((s / "figures-v4" / name, "figures"))
        with tempfile.TemporaryDirectory() as tmp:
            arts.append((base.temp_json(tmp, "source_files.json", self.ctx["source_files"]), None))
            return self.new_run("v1 · baseline QB interception risk · 20261104", "parent",
                                s / "development-v3" / "frozen_config.json", bag, params,
                                extra_tags={"selection_rule": self.design["selection"]}, artifacts=arts,
                                finish=False)

    def fold_run(self, rec: dict, parent: str, source: Path) -> str:
        bag = _Bag()
        bag.add_block(rec["model"])
        bag.add_block(rec["constant"], "constant.")
        # Derivada (não vem do arquivo): log loss do modelo menos o da constante.
        if not _is_null(rec["model"].get("log_loss")) and not _is_null(rec["constant"].get("log_loss")):
            bag.add("delta_log_loss_vs_constant", rec["model"]["log_loss"] - rec["constant"]["log_loss"])
        params = {"variant": rec["variant"], "C": rec["C"], "train_years": _compact(rec["train_years"]),
                  "validation_year": rec["validation"]}
        name = f"v1 · fold {rec['validation']} · {rec['variant']} · C={_fmt_c(rec['C'])}"
        return self.new_run(name, "fold", source, bag, params, parent=parent,
                            extra_tags={"variant": rec["variant"],
                                        "derived_metrics": "delta_log_loss_vs_constant"})

    def selection_run(self, variant: str, scores: dict, parent: str, source: Path) -> str:
        bag = _Bag()
        for c, score in scores.items():
            bag.add(f"pooled_validation_log_loss.C_{c}", score)
        params = {"variant": variant, "chosen_C": self.frozen["chosen_C"][variant]}
        return self.new_run(f"v1 · selection · {variant}", "selection", source, bag, params, parent=parent,
                            extra_tags={"variant": variant,
                                        "derived_metrics": "pooled_validation_log_loss.*"})

    def evaluation_run(self, variant: str, m: dict, parent: str) -> str:
        s, d = self.store, self.design
        ev = s / "evaluation-v1"
        bag = _Bag()
        bag.add_block(m["model"])
        bag.add_block(m["constant"], "constant.")
        for met, vals in m["paired_game_bootstrap"].items():
            for part in BOOTSTRAP_PARTS:
                bag.add(f"bootstrap.{met}.{part}", vals.get(part))
        params = {"variant": variant, "C": self.frozen["chosen_C"][variant],
                  "train_years": _compact(d["final_train"]), "test_year": d["final_test"]}
        # calibration_2025.* cobre as duas variantes; vai nas duas execuções de avaliação.
        arts = [(ev / f"calibration_{variant}.json", None), (ev / f"groups_{variant}.json", None),
                (ev / f"coefficients_{variant}.csv", None),
                (s / "development-v3" / f"model_{variant}_2022_2024.json", None),
                (s / "figures-v4" / "calibration_2025.png", "figures"),
                (s / "figures-v4" / "calibration_2025.svg", "figures")]
        return self.new_run(f"v1 · evaluation {d['final_test']} · {variant}", "evaluation", ev / "metrics.json",
                            bag, params, parent=parent, extra_tags={"variant": variant}, artifacts=arts)

    def application_run(self, variant: str, parent: str) -> str:
        s, d = self.store, self.design
        app = s / "application-v1"
        diag_path = app / f"application_diagnostics_{variant}.json"
        diag = _jload(diag_path)
        bag = _Bag()
        bag.add_block(diag["metrics_descriptive_only"], "descriptive_only.")
        weeks = d["application"]["weeks"]
        params = {"variant": variant, "C": self.frozen["chosen_C"][variant],
                  "train_years": _compact(d["application_train"]),
                  "season": d["application"]["season"], "weeks": f"{weeks[0]}-{weeks[1]}"}
        arts = [(diag_path, None), (app / f"model_{variant}_2022_2025.json", None),
                (app / f"qb_{variant}.csv", None)]
        return self.new_run(f"v1 · application {d['application']['season']} W{weeks[0]}-{weeks[1]} · {variant}",
                            "application", diag_path, bag, params, parent=parent,
                            extra_tags={"variant": variant, "metrics_scope": "descriptive_only"},
                            artifacts=arts)


def default_store() -> Path:
    return tracking.stores_root() / STORE_NAME


def expected_counts(ctx: dict) -> dict[str, int]:
    """Filhas esperadas por role, derivadas do desenho congelado."""
    d = ctx["frozen"]["design"]
    nv = len(d["variants"])
    return {"fold": nv * len(d["C_grid"]) * len(d["folds"]), "selection": nv, "evaluation": nv, "application": nv}


@base.wrap_errors(V1ImportError, "importação v1")
def import_v1(store: Path | None = None, home: Path | None = None, *, rebuild: bool = False,
              design_path: Path | None = None, contract_path: Path | None = None) -> dict:
    """Importa a v1. Devolve {parent_run_id, created, counts}. Idempotente por sha256(frozen_config.json).

    Pai interrompido (RUNNING/FAILED/KILLED) é limpo antes de importar; `rebuild=True` importa de novo e só
    então apaga a importação antiga (ver `importer_base.execute`)."""
    store = Path(store) if store is not None else default_store()
    home = tracking.configure(home)
    ctx = verify_chain(store, design_path, contract_path)
    ctx["source_files"] = source_file_records(store)
    exp_id = tracking.ensure_experiment("v1", home)
    client = MlflowClient()
    expected = expected_counts(ctx)
    return base.execute(client, exp_id, home, ctx["freeze_sha"], expected, rebuild, "v1", V1ImportError,
                        lambda: _Importer(store, client, exp_id, ctx, home), Path(__file__))
