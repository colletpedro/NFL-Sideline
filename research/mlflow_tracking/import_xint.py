"""Importador do xINT (observed-interception-given-ftn-v1) para o MLflow (somente leitura no store).

Lê só os caminhos canônicos (development/, evaluation/, final/, application-complete/, figures-reviewed/,
build/manifest.json, build/coverage.json, mais config.json, output-fix.json e o recibo de reproduction-offline),
confere a cadeia de hashes ANTES de criar execuções e cria:

    1 pai (role=parent) + 8 fold + 1 selection + 4 evaluation + 1 final + 1 application

Métricas são copiadas dos arquivos, nunca recalculadas; vazio/NaN vira a tag `null_metrics`. Nenhum parquet,
`consumer/`, `cases/` ou `pass_predictions` vai como artefato (linhas por jogada ficam fora do MLflow); os
parquets só entram no `source_files.json` com bytes e sha256.
"""
from __future__ import annotations

import csv
import json
import os
import re
import tempfile
from pathlib import Path

from mlflow import MlflowClient

import importer_base as base
import tracking
from importer_base import Bag as _Bag, compact as _compact, is_null as _is_null, mtime_ms as _mtime_ms, sha256_file

STORE_NAME = "qb-expected-interceptions-v1/20261105-v1"
FAMILY = "xint-ftn-v1"
MODELS = ("B0", "B1", "B2", "C")
DEV_YEARS = (2023, 2024)
CANONICAL_DIRS = ("development", "evaluation", "final", "application-complete", "figures-reviewed")
CANONICAL_FILES = ("build/manifest.json", "build/coverage.json", "build/dataset.parquet", "config.json",
                   "output-fix.json", "reproduction-offline/reproduction.json")
PARTS = ("delta", "low", "high")

_REPO = Path(__file__).resolve().parents[2]
CODE_DIR = _REPO / "research" / "qb_expected_interceptions"
PACKAGE_PY = _REPO / "research" / "qb_risk_outcomes_lab" / "package.py"
CONTRACT_PATH = _REPO / "docs" / "plans" / "qb-expected-interceptions-v1" / "RESEARCH-CONTRACT.md"
DEV_BOOTSTRAP_GROUPS = ("ftn_0", "ftn_1")  # além de `all` (que já vem de selection.json)


class XintImportError(base.ImporterError):
    """Falha de verificação ou de importação (mensagem em português, pensada para o usuário)."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise XintImportError(msg)


def _jload(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise XintImportError(f"Não foi possível ler JSON {path}: {exc}") from exc


def read_csv(path) -> tuple[list[str], list[dict]]:
    try:
        with open(path, newline="") as f:
            r = csv.DictReader(f)
            return list(r.fieldnames or []), list(r)
    except OSError as exc:
        raise XintImportError(f"Não foi possível ler CSV {path}: {exc}") from exc


def read_model_sha(package_py: Path = PACKAGE_PY) -> str:
    """Lê a constante MODEL_SHA do package.py do laboratório por regex (sem importar o módulo)."""
    m = re.search(r"^MODEL_SHA\s*=\s*['\"]([0-9a-f]{64})['\"]", Path(package_py).read_text(), re.M)
    _require(m is not None, f"MODEL_SHA não encontrado em {package_py}")
    return m.group(1)


def _num(value):
    """Texto de CSV -> float, ou None quando vazio/NaN."""
    if value is None or str(value).strip() == "":
        return None
    v = float(value)
    return None if _is_null(v) else v


def metric_rows(path, key_cols=("model", "group")) -> tuple[list[str], list[dict]]:
    cols, rows = read_csv(path)
    return [c for c in cols if c not in key_cols], rows


def _fmt_c(c) -> str:
    return repr(float(c))


# ---------------------------------------------------------------- verificação

def verify_chain(store: Path, code_dir: Path, config_path: Path, model_sha: str,
                 contract_path: Path | None = None) -> dict:
    """Confere diretórios e a cadeia de hashes. Devolve os JSONs principais já carregados.

    `contract_path` (padrão: RESEARCH-CONTRACT.md da worktree) é obrigatório: ausente é erro."""
    contract_path = CONTRACT_PATH if contract_path is None else Path(contract_path)
    for d in CANONICAL_DIRS:
        _require((store / d).is_dir(), f"Diretório canônico ausente: {store / d}")
    for f in CANONICAL_FILES:
        _require((store / f).is_file(), f"Arquivo ausente: {store / f}")
    freeze_path = store / "development" / "freeze.json"
    freeze = _jload(freeze_path)
    receipt = _jload(store / "evaluation" / "receipt.json")
    fixed = _jload(store / "final" / "fixed.json")
    manifest = _jload(store / "build" / "manifest.json")
    selection = _jload(store / "development" / "selection.json")
    config = _jload(store / "config.json")
    freeze_sha = sha256_file(freeze_path)
    _require(receipt.get("freeze_sha256") == freeze_sha,
             f"sha256(freeze.json)={freeze_sha} difere de evaluation/receipt.json freeze_sha256="
             f"{receipt.get('freeze_sha256')}")
    _require(fixed.get("development_freeze_sha256") == freeze_sha,
             f"sha256(freeze.json)={freeze_sha} difere de final/fixed.json development_freeze_sha256="
             f"{fixed.get('development_freeze_sha256')}")
    hashes = freeze.get("evaluation_model_hashes", {})
    _require(set(hashes) == set(MODELS), f"freeze.evaluation_model_hashes tem modelos {sorted(hashes)}")
    for k, expected in hashes.items():
        got = sha256_file(store / "development" / "evaluation_models" / f"{k}.json")
        _require(got == expected, f"sha256(evaluation_models/{k}.json)={got} difere de "
                                  f"freeze.evaluation_model_hashes[{k}]={expected}")
    final_sha = sha256_file(store / "final" / "model.json")
    _require(final_sha == fixed.get("model_sha256"),
             f"sha256(final/model.json)={final_sha} difere de final/fixed.json model_sha256={fixed.get('model_sha256')}")
    _require(final_sha == model_sha,
             f"sha256(final/model.json)={final_sha} difere de MODEL_SHA do laboratório ({model_sha})")
    dataset_sha = sha256_file(store / "build" / "dataset.parquet")
    _require(dataset_sha == manifest.get("dataset_sha256"),
             f"sha256(dataset.parquet)={dataset_sha} difere de build/manifest.json dataset_sha256="
             f"{manifest.get('dataset_sha256')}")
    config_sha = sha256_file(config_path)
    _require(config_sha == freeze.get("config_sha256"),
             f"sha256(config.json do código)={config_sha} difere de freeze.config_sha256={freeze.get('config_sha256')}")
    _require(config == freeze.get("config"), "config.json do store difere de freeze.config")
    _require(contract_path.is_file(), f"Arquivo de referência ausente: {contract_path} (RESEARCH-CONTRACT.md)")
    contract_sha = sha256_file(contract_path)
    _require(contract_sha == freeze.get("contract_sha256"),
             f"sha256(RESEARCH-CONTRACT.md)={contract_sha} difere de freeze.contract_sha256="
             f"{freeze.get('contract_sha256')}")
    _require(selection == freeze.get("selection"), "development/selection.json difere de freeze.selection")
    amendment = _check_code(store, code_dir, freeze, freeze_sha)
    # Seleção: argmin do log loss agregado (empate -> menor C) deve ser o chosen_C congelado.
    scores = selection["C_grid_scores"]
    best = min((s["pooled_log_loss"], s["C"]) for s in scores)[1]
    _require(best == selection["chosen_C"],
             f"chosen_C={selection['chosen_C']} difere do argmin de C_grid_scores ({best})")
    return {"freeze": freeze, "freeze_sha": freeze_sha, "receipt": receipt, "fixed": fixed, "manifest": manifest,
            "selection": selection, "config": config, "dataset_sha": dataset_sha, "amendment": amendment}


def _check_code(store: Path, code_dir: Path, freeze: dict, freeze_sha: str) -> dict | None:
    """Confere freeze.code_sha256 contra o código atual; só `run.py` pode divergir, e só pela emenda registrada."""
    amendment = None
    for name, expected in freeze["code_sha256"].items():
        p = Path(code_dir) / name
        _require(p.is_file(), f"Arquivo de código ausente: {p}")
        got = sha256_file(p)
        if got == expected:
            continue
        _require(name == "run.py", f"sha256({name})={got} difere de freeze.code_sha256[{name}]={expected}")
        fix_path = store / "output-fix.json"
        _require(fix_path.is_file(), f"run.py diverge do freeze e não há {fix_path}")
        fix = _jload(fix_path)
        _require(fix.get("before") == expected and fix.get("after") == got
                 and fix.get("original_freeze_sha256") == freeze_sha,
                 "run.py diverge do freeze e output-fix.json não o explica "
                 f"(before={fix.get('before')}, after={fix.get('after')}, "
                 f"original_freeze_sha256={fix.get('original_freeze_sha256')}; "
                 f"freeze={expected}, atual={got}, sha(freeze.json)={freeze_sha})")
        amendment = {"before": fix["before"], "after": fix["after"],
                     "original_freeze_sha256": fix["original_freeze_sha256"]}
    return amendment


def source_file_records(store: Path) -> list[dict]:
    """Caminho relativo, bytes e sha256 de cada arquivo canônico (inclusive parquets)."""
    paths = [store / f for f in CANONICAL_FILES]
    for d in CANONICAL_DIRS:
        for dirpath, _dirs, files in os.walk(store / d):
            paths += [Path(dirpath) / f for f in files]
    return [{"path": p.relative_to(store).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
            for p in sorted(set(paths))]


# ---------------------------------------------------------------- importação

class _XintImporter(base.BaseImporter):
    error_cls = XintImportError
    module_file = Path(__file__)

    def __init__(self, store: Path, client: MlflowClient, exp_id: str, ctx: dict, home: Path) -> None:
        super().__init__(store, client, exp_id, ctx, home)
        self.config, self.freeze, self.selection = ctx["config"], ctx["freeze"], ctx["selection"]

    def tags(self, role: str, extra: dict | None = None) -> dict:
        t = self.base_tags(self.ctx["dataset_sha"], self.freeze["config_sha256"], self.config["seed"], role)
        t["experiment_family"] = FAMILY
        t.update(extra or {})
        return t

    def _csv_bag(self, path, prefix: str = "", model: str | None = None) -> _Bag:
        cols, rows = metric_rows(path)
        bag = _Bag()
        for r in rows:
            if model is not None and r["model"] != model:
                continue
            for c in cols:
                bag.add(f"{prefix}{r['group']}.{c}", _num(r[c]))
        return bag

    # -- execuções ----------------------------------------------------------
    def run_all(self) -> str:
        s, cfg = self.store, self.config
        dev, ev = s / "development", s / "evaluation"
        chosen = self.selection["chosen_C"]
        parent = self.parent_run()
        for year in DEV_YEARS:
            for model in MODELS:
                self.fold_run(year, model, chosen, parent)
        self.selection_run(parent)
        paired_eval = _jload(ev / "paired_bootstrap.json")
        for model in MODELS:
            self.evaluation_run(model, paired_eval, parent)
        self.final_run(parent)
        self.application_run(parent)
        self.client.set_terminated(parent, "FINISHED", end_time=_mtime_ms(dev / "freeze.json"))
        return parent

    def parent_run(self) -> str:
        s, f, cfg, fx = self.store, self.freeze, self.config, self.ctx["fixed"]
        bag = _Bag()
        bag.add("build_rows", self.ctx["manifest"]["rows"])
        params = {k: _compact(cfg[k]) if isinstance(cfg[k], (list, dict)) else cfg[k]
                  for k in ("target", "risk_input", "development_years", "evaluation_year", "application_year",
                            "C_grid", "solver", "max_iter", "tol", "bootstrap_replicates", "calibration_edges",
                            "model_family", "version")}
        extra = {"selection_rule": cfg["selection"], "selected": self.selection["selected"],
                 "chosen_C": str(self.selection["chosen_C"]), "model_id": fx["model_id"],
                 "model_sha256": fx["model_sha256"],
                 "upstream_m3_note": "not_M3" if f.get("not_M3") else "unspecified"}
        am = self.ctx["amendment"]
        if am:
            extra.update({"code_amendment": "output-fix run.py", "code_amendment_before": am["before"],
                          "code_amendment_after": am["after"],
                          "code_amendment_original_freeze_sha256": am["original_freeze_sha256"]})
        arts = [(s / "development" / "freeze.json", None), (s / "development" / "selection.json", None),
                (s / "config.json", None), (s / "build" / "manifest.json", None),
                (s / "build" / "coverage.json", None), (s / "output-fix.json", None),
                (s / "reproduction-offline" / "reproduction.json", "reproduction-offline")]
        for p in sorted((s / "figures-reviewed").iterdir()):
            if p.is_file():
                arts.append((p, "figures-reviewed"))
        with tempfile.TemporaryDirectory() as tmp:
            arts.append((base.temp_json(tmp, "source_files.json", self.ctx["source_files"]), None))
            return self.new_run("xINT · observed-interception given FTN · 20261105", "parent",
                                s / "development" / "freeze.json", bag, params, extra_tags=extra,
                                artifacts=arts, finish=False)

    def fold_run(self, year: int, model: str, chosen, parent: str) -> str:
        dev = self.store / "development"
        csv_path = dev / f"metrics_{year}.csv"
        bag = self._csv_bag(csv_path, model=model)
        model_file = dev / "models" / (f"C_{_fmt_c(chosen)}_{year}.json" if model == "C" else f"{model}_{year}.json")
        _require(model_file.is_file(), f"Modelo do fold ausente: {model_file}")
        train_years = _jload(model_file)["train_years"]
        params = {"year": year, "model": model, "train_years": _compact(train_years)}
        if model == "C":
            params["C"] = chosen
        return self.new_run(f"xINT · fold {year} · {model}", "fold", csv_path, bag, params, parent=parent,
                            extra_tags={"model": model}, artifacts=[(model_file, None)])

    def selection_run(self, parent: str) -> str:
        s, sel = self.store, self.selection
        dev = s / "development"
        bag = _Bag()
        for rec in sel["C_grid_scores"]:
            bag.add(f"pooled_log_loss.C_{rec['C']}", rec["pooled_log_loss"])
        params = {"chosen_C": sel["chosen_C"], "decision_data_years": _compact(sel["decision_data_years"])}
        for pair, mets in sel["paired"].items():
            for met, vals in mets.items():
                for part in PARTS:
                    bag.add(f"paired.{pair}.{met}.{part}", vals.get(part))
                for part in ("games", "reps", "seed"):
                    params[f"paired.{pair}.{met}.{part}"] = vals.get(part)
        dev_boot = _jload(dev / "development" / "paired_bootstrap.json")
        for group in DEV_BOOTSTRAP_GROUPS:
            for pair, mets in (dev_boot.get(group) or {}).items():
                for met, vals in mets.items():
                    for part in PARTS:
                        bag.add(f"paired.{group}.{pair}.{met}.{part}", vals.get(part))
                    for part in ("games", "reps", "seed"):
                        params[f"paired.{group}.{pair}.{met}.{part}"] = vals.get(part)
        pooled_path = dev / "development" / "metrics.csv"
        cols, rows = metric_rows(pooled_path)
        for r in rows:
            for c in cols:
                bag.add(f"pooled.{r['model']}.{r['group']}.{c}", _num(r[c]))
        tags = {"context_useful": str(sel["context_useful"]).lower(),
                "context_calibration_gate": str(sel["context_calibration_gate"]).lower(),
                "selected": sel["selected"], "chosen_C": str(sel["chosen_C"]), "rule": sel["rule"]}
        return self.new_run("xINT · selection", "selection", dev / "selection.json", bag, params, parent=parent,
                            extra_tags=tags)

    def evaluation_run(self, model: str, paired_eval: dict, parent: str) -> str:
        s, cfg = self.store, self.config
        ev_csv = s / "evaluation" / "metrics.csv"
        bag = self._csv_bag(ev_csv, model=model)
        params: dict = {"model": model, "test_year": cfg["evaluation_year"]}
        for group, pairs in paired_eval.items():
            for pair, mets in pairs.items():
                if pair.split("-")[0] != model:
                    continue
                for met, vals in mets.items():
                    for part in PARTS:
                        bag.add(f"paired.{group}.{pair}.{met}.{part}", vals.get(part))
                    for part in ("games", "reps", "seed"):
                        params[f"paired.{group}.{pair}.{met}.{part}"] = vals.get(part)
        model_file = s / "development" / "evaluation_models" / f"{model}.json"
        params["train_years"] = _compact(_jload(model_file)["train_years"])
        cols, rows = read_csv(s / "evaluation" / "calibration.csv")
        mine = [r for r in rows if r["model"] == model]
        _require(mine, f"evaluation/calibration.csv sem linhas do modelo {model}")
        selected = model == self.selection["selected"]
        with tempfile.TemporaryDirectory() as tmp:
            cal = Path(tmp) / f"calibration_{model}.csv"
            with open(cal, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
                w.writeheader()
                w.writerows(mine)
            return self.new_run(f"xINT · evaluation {cfg['evaluation_year']} · {model}", "evaluation", ev_csv, bag,
                                params, parent=parent,
                                extra_tags={"model": model, "selected": str(selected).lower()},
                                artifacts=[(model_file, None), (cal, None)])

    def final_run(self, parent: str) -> str:
        fin, fx = self.store / "final", self.ctx["fixed"]
        params = {"model_id": fx["model_id"], "fit_years": _compact(fx["fit_years"]), "selected": fx["selected"]}
        return self.new_run(f"xINT · final · {fx['selected']}", "final", fin / "fixed.json", _Bag(), params,
                            parent=parent, extra_tags={"model_sha256": fx["model_sha256"]},
                            artifacts=[(fin / "fixed.json", None), (fin / "model.json", None)])

    def application_run(self, parent: str) -> str:
        app, cfg = self.store / "application-complete", self.config
        bag = self._csv_bag(app / "metrics.csv", prefix="descriptive_only.")
        fx = _jload(app / "fixed.json")
        params = {"season": cfg["application_year"], "model_id": fx["model_id"],
                  "fit_years": _compact(fx["fit_years"]), "selected": fx["selected"]}
        return self.new_run(f"xINT · application {cfg['application_year']} · {fx['selected']}", "application",
                            app / "metrics.csv", bag, params, parent=parent,
                            extra_tags={"metrics_scope": "descriptive_only", "model_sha256": fx["model_sha256"]},
                            artifacts=[(app / "coverage.json", None), (app / "players.csv", None),
                                       (app / "fixed.json", None)])


def default_store() -> Path:
    return tracking.stores_root() / STORE_NAME


def expected_counts(ctx: dict) -> dict[str, int]:
    return {"fold": len(DEV_YEARS) * len(MODELS), "selection": 1, "evaluation": len(MODELS), "final": 1,
            "application": 1}


@base.wrap_errors(XintImportError, "importação xINT")
def import_xint(store: Path | None = None, home: Path | None = None, *, code_dir: Path | None = None,
                config_path: Path | None = None, model_sha: str | None = None, contract_path: Path | None = None,
                rebuild: bool = False) -> dict:
    """Importa o xINT. Devolve {parent_run_id, created, counts}. Idempotente por sha256(freeze.json).

    `code_dir`, `config_path`, `model_sha` e `contract_path` são as referências a conferir (padrão: código
    congelado da worktree, seu config.json, a constante MODEL_SHA do laboratório e o RESEARCH-CONTRACT.md); testes
    injetam as suas, e referência ausente é erro. Pai interrompido é limpo antes de importar; `rebuild=True`
    importa de novo e só então apaga a importação antiga."""
    store = Path(store) if store is not None else default_store()
    code_dir = Path(code_dir) if code_dir is not None else CODE_DIR
    config_path = Path(config_path) if config_path is not None else code_dir / "config.json"
    model_sha = model_sha if model_sha is not None else read_model_sha()
    home = tracking.configure(home)
    ctx = verify_chain(store, code_dir, config_path, model_sha, contract_path)
    ctx["source_files"] = source_file_records(store)
    exp_id = tracking.ensure_experiment("xint", home)
    client = MlflowClient()
    expected = expected_counts(ctx)
    return base.execute(client, exp_id, home, ctx["freeze_sha"], expected, rebuild, "xINT", XintImportError,
                        lambda: _XintImporter(store, client, exp_id, ctx, home), Path(__file__))
