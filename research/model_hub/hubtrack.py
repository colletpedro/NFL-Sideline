"""Rastreamento do hub no MLflow: experimentos `hub-<model_key>`, tags obrigatórias e escrita protegida.

Só experimentos cujo nome começa com `hub-` aceitam escrita por aqui; os demais (qb-*, xint-*) são recusados.
Usa `research/mlflow_tracking/tracking.py` (via `hubpaths.tracking`) para home, URI e criação do experimento.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import mlflow
from mlflow import MlflowClient

import hubpaths

tracking = hubpaths.tracking

HARNESS_VERSION = "0.2.0"
EXPERIMENT_PREFIX = "hub-"
ROLES = ("parent", "candidate", "baseline", "reference", "final")
REQUIRED_TAGS = (
    "model_key",
    "role",
    "harness_version",
    "model_code_sha256",
    "data_id",
    "config_sha256",
    "selection_rule",
    "seed",
    "git_commit",
    "git_dirty",
)
PATHSPEC = ":/research/model_hub"  # relativo à raiz do repositório
MODULE_DIR = Path(__file__).resolve().parent


class HubTrackError(RuntimeError):
    """Violação das regras de rastreamento do hub (mensagem em português)."""


# ------------------------------------------------------------------ JSON canônico e hashes

def canonical_json(obj) -> str:
    """JSON canônico (chaves ordenadas, sem espaços, sem NaN/Inf). Levanta TypeError/ValueError se não for JSON puro."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=True)


def sha256_json(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode()).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_files(paths) -> str:
    """Hash determinístico de um conjunto de arquivos (nome + sha256 de cada, em ordem de nome). Vazio -> hash de vazio."""
    items = sorted((Path(p).name, sha256_file(p)) for p in paths)
    return hashlib.sha256(canonical_json(items).encode()).hexdigest()


# ------------------------------------------------------------------ configuração e experimentos

def configure(home=None) -> Path:
    """Aponta tracking e registry para o SQLite do home do MLflow (`NFL_MLFLOW_HOME` ou padrão). Devolve o home."""
    return tracking.configure(Path(home) if home is not None else hubpaths.mlflow_home())


def experiment_name(model_key: str) -> str:
    if not model_key or not all(c.isalnum() or c in "_-" for c in model_key):
        raise HubTrackError(f"model_key inválido: {model_key!r} (use letras, dígitos, _ e -)")
    return f"{EXPERIMENT_PREFIX}{model_key}"


def experiment(model_key: str, home=None) -> str:
    """Cria (ou confere) `hub-<model_key>` com artifact_location `<mlflow_home>/artifacts/hub-<model_key>`.

    Devolve o experiment_id."""
    home = Path(home) if home is not None else hubpaths.mlflow_home()
    if mlflow.get_tracking_uri() != tracking.tracking_uri(home):
        configure(home)
    return tracking.ensure_experiment(experiment_name(model_key), home)


def assert_hub_experiment(experiment_id: str, client: MlflowClient | None = None) -> str:
    """Levanta HubTrackError se o experimento não começar com `hub-`. Devolve o nome."""
    client = client or MlflowClient()
    name = client.get_experiment(str(experiment_id)).name
    if not name.startswith(EXPERIMENT_PREFIX):
        raise HubTrackError(f"recusado: o hub só escreve em experimentos 'hub-*', não em {name!r}")
    return name


# ------------------------------------------------------------------ tags

def git_state(path: Path | None = None) -> dict:
    """commit e `dirty` (somente `research/model_hub`); fora de um repositório: "unknown"."""
    path = Path(path) if path is not None else MODULE_DIR
    try:
        return {
            "commit": tracking._git(path, "rev-parse", "HEAD"),
            "dirty": bool(tracking._git(path, "status", "--porcelain", "--", PATHSPEC)),
        }
    except (subprocess.CalledProcessError, OSError):
        return {"commit": "unknown", "dirty": "unknown"}


def validate_tags(tags: dict) -> None:
    missing = [t for t in REQUIRED_TAGS if t not in tags or str(tags[t]) == ""]
    if missing:
        raise HubTrackError(f"tags obrigatórias ausentes ou vazias: {', '.join(missing)}")
    if tags["role"] not in ROLES:
        raise HubTrackError(f"role inválido: {tags['role']!r}; use um de {ROLES}")


def build_tags(model_key, role, model_code_sha256, data_id, config_sha256, selection_rule, seed, **extra) -> dict:
    """Monta as tags obrigatórias (sempre texto) preenchendo harness_version e git; `extra` entra como tags adicionais."""
    git = git_state()
    tags = {
        "model_key": str(model_key),
        "role": str(role),
        "harness_version": HARNESS_VERSION,
        "model_code_sha256": str(model_code_sha256),
        "data_id": str(data_id),
        "config_sha256": str(config_sha256),
        "selection_rule": str(selection_rule),
        "seed": str(seed),
        "git_commit": git["commit"],
        "git_dirty": str(git["dirty"]).lower(),
    }
    tags.update({k: str(v) for k, v in extra.items()})
    validate_tags(tags)
    return tags


# ------------------------------------------------------------------ execuções (todas protegidas por `hub-`)

_checked: dict[str, bool] = {}


def _check_run(run_id: str) -> None:
    client = MlflowClient()
    key = f"{mlflow.get_tracking_uri()}|{run_id}"
    if key not in _checked:
        assert_hub_experiment(client.get_run(run_id).info.experiment_id, client)
        _checked[key] = True


def start_run(model_key: str, tags: dict, run_name: str | None = None, parent_run_id: str | None = None,
              home=None) -> str:
    """Cria uma execução em `hub-<model_key>` (filha de `parent_run_id` se dado). Não usa o estado global do MLflow."""
    exp_id = experiment(model_key, home)
    full = dict(tags)
    if parent_run_id:
        full["mlflow.parentRunId"] = parent_run_id
    run = MlflowClient().create_run(exp_id, tags=full, run_name=run_name)
    return run.info.run_id


def log_params(run_id: str, params: dict) -> None:
    _check_run(run_id)
    client = MlflowClient()
    for k, v in params.items():
        client.log_param(run_id, k, v)


def log_metrics(run_id: str, metrics: dict) -> None:
    _check_run(run_id)
    client = MlflowClient()
    for k, v in metrics.items():
        client.log_metric(run_id, k, float(v))


def set_tags(run_id: str, tags: dict) -> None:
    _check_run(run_id)
    client = MlflowClient()
    for k, v in tags.items():
        client.set_tag(run_id, k, str(v))


def log_json(run_id: str, obj, artifact_file: str) -> None:
    """Grava `obj` (JSON puro) como artefato de texto."""
    _check_run(run_id)
    MlflowClient().log_text(run_id, json.dumps(obj, sort_keys=True, indent=2, allow_nan=False), artifact_file)


def finish_run(run_id: str, status: str = "FINISHED") -> None:
    """Fecha a execução. Para FINISHED, valida as tags obrigatórias; se faltarem, marca FAILED e levanta."""
    _check_run(run_id)
    client = MlflowClient()
    if status == "FINISHED":
        try:
            validate_tags(client.get_run(run_id).data.tags)
        except HubTrackError:
            client.set_terminated(run_id, "FAILED")
            raise
    client.set_terminated(run_id, status)
