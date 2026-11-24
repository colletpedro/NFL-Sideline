"""Proveniência dos números do laboratório de desfechos, lida só do MLflow (aliases `champion`).

Gera `web-ui/broadcast-journey/risk-outcomes/provenance.json`: para cada modelo em uso (B2 `xint-ftn` e M3
`qb-iw-m3`), a execução registrada e, para cada número que o laboratório exibe, o valor com o `run_id` e a chave
de métrica (ou de parâmetro) de onde veio. Conteúdo determinístico: chaves ordenadas, sem horário de importação,
floats como o Python os serializa. O MLflow é só um índice; se divergir dos stores, o MLflow está errado.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from mlflow import MlflowClient
from mlflow.entities import ViewType

import tracking

SCHEMA_VERSION = 1
ALIAS = "champion"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT = REPO_ROOT / "web-ui" / "broadcast-journey" / "risk-outcomes" / "provenance.json"

B2_NAME = "xint-ftn"
M3_NAME = "qb-iw-m3"
B2_ALL = ("observed_interceptions", "expected_interceptions", "log_loss", "brier", "average_precision", "roc_auc")
B2_GROUPS = ("observed_interceptions", "expected_interceptions")
M3_METRICS = ("log_loss", "brier", "pr_auc_average_precision", "roc_auc", "observed_expected")
BOOTSTRAP_PARAM = "paired.all.B2-B1.log_loss.reps"


class ProvenanceError(RuntimeError):
    """Alias, execução ou métrica ausente/inválida (mensagem em português)."""


def _model_run(client: MlflowClient, name: str) -> tuple[dict, object]:
    """Versão `champion` de `name` e a execução role=model dela."""
    try:
        mv = client.get_model_version_by_alias(name, ALIAS)
    except Exception as exc:
        raise ProvenanceError(f"Modelo '{name}' sem o alias '{ALIAS}' no MLflow; rode `cli.py register`.") from exc
    try:
        run = client.get_run(mv.run_id)
    except Exception as exc:
        raise ProvenanceError(f"Execução {mv.run_id} do modelo '{name}' não encontrada.") from exc
    tags = run.data.tags
    if tags.get("role") != "model":
        raise ProvenanceError(f"Execução {run.info.run_id} de '{name}' não tem role=model.")
    for key in ("model_sha256", "source_freeze_sha256", "source_store", "git_commit", "source_parent_run_id"):
        if not tags.get(key):
            raise ProvenanceError(f"Execução {run.info.run_id} de '{name}' sem a tag '{key}'.")
    target = {B2_NAME: "b2", M3_NAME: "m3"}.get(name, "all")
    parent_id = tags["source_parent_run_id"]
    try:
        parent_active = client.get_run(parent_id).info.lifecycle_stage == "active"
    except Exception:
        parent_active = False
    if run.info.lifecycle_stage != "active" or not parent_active:
        raise ProvenanceError(
            f"A execução de origem de '{name}' (execução do modelo {run.info.run_id} ou pai importado {parent_id}) "
            f"não está ativa (p.ex. depois de `import --rebuild`); rode `cli.py register {target}`.")
    sha = tags["model_sha256"]
    if mv.tags.get("model_sha256") not in (None, sha):
        raise ProvenanceError(f"Versão {mv.version} de '{name}': model_sha256 difere entre versão e execução.")
    return {"sha": sha, "version": str(mv.version)}, run


def _find_run(client: MlflowClient, run_model, flt: str, what: str):
    """Exatamente uma execução FINISHED, filha do pai importado, que casa com `flt`."""
    parent = run_model.data.tags["source_parent_run_id"]
    full = f"{flt} and tags.`mlflow.parentRunId` = '{parent}' and attributes.status = 'FINISHED'"
    runs = client.search_runs([run_model.info.experiment_id], filter_string=full,
                              run_view_type=ViewType.ACTIVE_ONLY, max_results=5)
    if len(runs) != 1:
        raise ProvenanceError(f"Esperava 1 execução para {what}, encontrei {len(runs)}.")
    return runs[0]


def _metric(run, key: str) -> dict:
    metrics = run.data.metrics
    if key not in metrics:
        raise ProvenanceError(f"Execução {run.info.run_id} sem a métrica '{key}'.")
    value = float(metrics[key])
    if not math.isfinite(value):
        raise ProvenanceError(f"Métrica '{key}' da execução {run.info.run_id} não é finita.")
    return {"value": value, "runId": run.info.run_id, "metricKey": key}


def _reps(run) -> dict:
    raw = run.data.params.get(BOOTSTRAP_PARAM)
    if raw is None:
        raise ProvenanceError(f"Execução {run.info.run_id} sem o parâmetro '{BOOTSTRAP_PARAM}'.")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ProvenanceError(f"Parâmetro '{BOOTSTRAP_PARAM}' inválido: {raw!r}.") from exc
    if value <= 0:
        raise ProvenanceError(f"Parâmetro '{BOOTSTRAP_PARAM}' deve ser positivo: {value}.")
    return {"value": value, "runId": run.info.run_id, "paramKey": BOOTSTRAP_PARAM}


def _identity(client: MlflowClient, info: dict, run, name: str) -> dict:
    tags = run.data.tags
    return {
        "name": name,
        "alias": ALIAS,
        "version": info["version"],
        "runId": run.info.run_id,
        "sourceParentRunId": tags["source_parent_run_id"],
        "experiment": client.get_experiment(run.info.experiment_id).name,
        "sourceFreezeSha256": tags["source_freeze_sha256"],
        "sourceStore": tags["source_store"],
        "importerGitCommit": tags["git_commit"],
    }


def _b2_numbers(client: MlflowClient, run_model) -> dict:
    def ev(model: str):
        return _find_run(client, run_model, f"tags.role = 'evaluation' and tags.model = '{model}'",
                         f"avaliação 2025 de {model}")

    b2, b1, c = ev("B2"), ev("B1"), ev("C")
    nums: dict[str, dict] = {}
    for m in B2_ALL:
        nums[f"evaluation2025.B2.all.{m}"] = _metric(b2, f"all.{m}")
    for g in ("ftn_0", "ftn_1"):
        for m in B2_GROUPS:
            nums[f"evaluation2025.B2.{g}.{m}"] = _metric(b2, f"{g}.{m}")
    nums["evaluation2025.B1.all.log_loss"] = _metric(b1, "all.log_loss")
    nums["evaluation2025.C.all.log_loss"] = _metric(c, "all.log_loss")
    nums["evaluation2025.bootstrap.replicates"] = _reps(b2)
    return nums


def _m3_numbers(client: MlflowClient, run_model) -> dict:
    nums: dict[str, dict] = {}
    for year in ("2026", "2025"):
        run = _find_run(client, run_model,
                        f"tags.role = 'candidate' and tags.candidate = 'M3' and tags.year = '{year}'",
                        f"candidata {year}·M3")
        for m in M3_METRICS:
            nums[f"candidate{year}.M3.{m}"] = _metric(run, m)
    return nums


def build_provenance(home=None) -> dict:
    """Lê o MLflow em `home` (padrão: NFL_MLFLOW_HOME) e devolve a proveniência (dict serializável em JSON)."""
    tracking.configure(Path(home) if home is not None else None)
    client = MlflowClient()
    models: dict[str, dict] = {}
    for name, numbers in ((B2_NAME, _b2_numbers), (M3_NAME, _m3_numbers)):
        info, run = _model_run(client, name)
        entry = _identity(client, info, run, name)
        entry["numbers"] = numbers(client, run)
        if info["sha"] in models:
            raise ProvenanceError(f"sha256 de modelo repetido: {info['sha']}.")
        models[info["sha"]] = entry
    return {"schemaVersion": SCHEMA_VERSION, "models": models}


def render(data: dict) -> str:
    """Texto canônico do arquivo: JSON com indent 2, chaves ordenadas, newline final."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_provenance(path=None, home=None) -> tuple[Path, bool]:
    """Grava a proveniência; só reescreve se o conteúdo mudar. Devolve (caminho, mudou)."""
    out = Path(path) if path is not None else DEFAULT_OUT
    text = render(build_provenance(home))
    if out.is_file() and out.read_text(encoding="utf-8") == text:
        return out, False
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out, True


def check_provenance(path=None, home=None) -> list[str]:
    """Problemas entre o arquivo versionado e o que seria gerado (lista vazia = igual)."""
    out = Path(path) if path is not None else DEFAULT_OUT
    if not out.is_file():
        return [f"arquivo ausente: {out}"]
    if out.read_text(encoding="utf-8") != render(build_provenance(home)):
        return [f"{out} difere da proveniência gerada a partir do MLflow"]
    return []
