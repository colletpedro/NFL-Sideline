"""Rastreamento local com MLflow: caminhos, URI, experimentos e convenção de tags.

Nada aqui escreve em stores científicos; o MLflow é só um índice (ver docs/plans/mlflow-tracking-v1).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import mlflow
from mlflow import MlflowClient

IMPORTER_VERSION = "0.1.0"

EXPERIMENTS = {
    "v1": "qb-iw-baseline-v1",
    "v2": "qb-risk-temporal-v2",
    "xint": "xint-ftn-v1",
    "smoke": "mlflow-tracking-smoke",
}
MODELS = {"m3": "qb-iw-m3", "b2": "xint-ftn"}

REQUIRED_TAGS = (
    "source_store",
    "source_freeze_sha256",
    "dataset_sha256",
    "design_sha256",
    "seed",
    "git_commit",
    "git_dirty",
    "importer_version",
    "importer_code_sha256",
    "imported_at_utc",
    "role",
)

MODULE_DIR = Path(__file__).resolve().parent
MODULE_PATHSPEC = ":/research/mlflow_tracking"  # relativo à raiz do repositório


def _git(path: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(path), *args], check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


def main_checkout(start: Path | None = None) -> Path:
    """Checkout principal (pai do diretório Git comum), mesmo quando chamado de dentro de uma worktree."""
    start = Path(start) if start is not None else Path(__file__).resolve().parent
    common = Path(_git(start, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = start / common
    return common.resolve().parent


def mlflow_home() -> Path:
    env = os.environ.get("NFL_MLFLOW_HOME")
    if env:
        return Path(env)
    return main_checkout() / "editorial" / "local-artifacts" / "mlflow"


def stores_root() -> Path:
    env = os.environ.get("NFL_RESEARCH_STORES")
    if env:
        return Path(env)
    return main_checkout() / "editorial" / "local-artifacts"


def tracking_uri(home: Path) -> str:
    """URI SQLite com caminho absoluto (`sqlite:////abs/path/mlflow.db`)."""
    return f"sqlite:///{(Path(home).resolve() / 'mlflow.db').as_posix()}"


def configure(home: Path | None = None) -> Path:
    """Cria o home e aponta tracking e registry para o mesmo SQLite. Devolve o home."""
    home = Path(home) if home is not None else mlflow_home()
    home = home.resolve()
    (home / "artifacts").mkdir(parents=True, exist_ok=True)
    uri = tracking_uri(home)
    mlflow.set_tracking_uri(uri)
    mlflow.set_registry_uri(uri)
    _retire_default_experiment(home)
    return home


def _local_path(location: str) -> Path | None:
    if location.startswith("file:"):
        return Path(unquote(urlparse(location).path))
    return Path(location) if os.path.isabs(location) else None


def _retire_default_experiment(home: Path) -> None:
    """O experimento Default (id 0) do SQLite aponta para `<cwd>/mlruns`; se estiver fora do home, apaga-o
    (soft delete) para que `start_run` sem experimento falhe alto em vez de escrever no cwd."""
    client = MlflowClient()
    try:
        exp = client.get_experiment("0")
    except Exception:
        return
    if exp.lifecycle_stage != "active":
        return
    loc = _local_path(exp.artifact_location)
    if loc is None or not loc.resolve().is_relative_to(Path(home) / "artifacts"):
        client.delete_experiment("0")


def ensure_experiment(key_or_name: str, home: Path) -> str:
    """Cria (ou confere) o experimento com `artifact_location` explícito dentro do home.

    Experimento deletado com o mesmo `artifact_location` é restaurado; com outro, levanta RuntimeError."""
    name = EXPERIMENTS.get(key_or_name, key_or_name)
    location = (Path(home).resolve() / "artifacts" / name).as_uri()
    client = MlflowClient()
    exp = client.get_experiment_by_name(name)
    if exp is None:
        return client.create_experiment(name, artifact_location=location)
    if exp.artifact_location != location:
        raise RuntimeError(
            f"Experimento '{name}' já existe com artifact_location "
            f"{exp.artifact_location!r}, esperado {location!r}."
        )
    if exp.lifecycle_stage == "deleted":
        # O nome de um experimento deletado continua reservado; restaura (o artifact_location já confere).
        client.restore_experiment(exp.experiment_id)
    return exp.experiment_id


def git_info(path: Path) -> dict:
    """commit/branch/dirty; `dirty` olha só o pathspec do módulo. Fora de um repositório: "unknown"."""
    path = Path(path)
    try:
        return {
            "commit": _git(path, "rev-parse", "HEAD"),
            "branch": _git(path, "rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(_git(path, "status", "--porcelain", "--", MODULE_PATHSPEC)),
        }
    except (subprocess.CalledProcessError, OSError):
        return {"commit": "unknown", "branch": "unknown", "dirty": "unknown"}


def importer_code_sha256(importer_file=None) -> str:
    """SHA-256 determinístico de tracking.py + importer_base.py + o módulo do importador (se houver)."""
    files = [MODULE_DIR / "tracking.py", MODULE_DIR / "importer_base.py"]
    if importer_file is not None:
        files.append(Path(importer_file))
    h = hashlib.sha256()
    for f in files:
        h.update(f.name.encode() + b"\0" + hashlib.sha256(f.read_bytes()).hexdigest().encode() + b"\n")
    return h.hexdigest()


def validate_tags(tags: dict) -> None:
    missing = [t for t in REQUIRED_TAGS if t not in tags]
    if missing:
        raise ValueError(f"Tags obrigatórias ausentes: {', '.join(missing)}")


def base_tags(
    source_store,
    source_freeze_sha256,
    dataset_sha256,
    design_sha256,
    seed,
    role,
    repo_path,
    importer_file=None,
    imported_at=None,
) -> dict:
    """Monta as tags obrigatórias (valores sempre texto) preenchendo git e importador."""
    git = git_info(Path(repo_path))
    tags = {
        "source_store": str(source_store),
        "source_freeze_sha256": str(source_freeze_sha256),
        "dataset_sha256": str(dataset_sha256),
        "design_sha256": str(design_sha256),
        "seed": str(seed),
        "git_commit": git["commit"],
        "git_dirty": str(git["dirty"]).lower(),
        "importer_version": IMPORTER_VERSION,
        "importer_code_sha256": importer_code_sha256(importer_file),
        "imported_at_utc": imported_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "role": str(role),
    }
    validate_tags(tags)
    return tags


def find_parents(experiment_id: str, source_freeze_sha256: str, client: MlflowClient | None = None) -> list:
    """Todos os pais FINISHED deste freeze, em ordem determinística (mais recente primeiro).

    Normalmente há um; dois só aparecem se um `--rebuild` foi interrompido entre "nova importação pronta" e
    "antiga apagada". A ordem é (`imported_at_utc`, `start_time`, `run_id`) decrescente."""
    client = client or MlflowClient()
    runs = client.search_runs(
        [experiment_id],
        filter_string=(
            f"tags.source_freeze_sha256 = '{source_freeze_sha256}' and tags.role = 'parent' "
            "and attributes.status = 'FINISHED'"
        ),
        max_results=1000,
    )
    return sorted(runs, key=lambda r: (r.data.tags.get("imported_at_utc", ""), r.info.start_time or 0,
                                       r.info.run_id), reverse=True)


def find_parent(experiment_id: str, source_freeze_sha256: str):
    """Execução-pai FINISHED já importada para este freeze (a mais recente, de forma determinística), ou None.

    Pais RUNNING/FAILED/KILLED (importação interrompida) não contam como importados."""
    runs = find_parents(experiment_id, source_freeze_sha256)
    return runs[0] if runs else None
