"""Base comum dos importadores (v1, v2, xINT): hash, acumulador de métricas, criação de execuções,
guarda de tamanho, limpeza de importações incompletas e rollback.

Nada aqui lê ou escreve nos stores científicos; só o MLflow e o home (`<home>/artifacts`).
Concorrência: não rode duas importações ao mesmo tempo no mesmo home (a limpeza de execuções RUNNING
apagaria a importação da outra).

O índice do MLflow (SQLite) NÃO é fonte de verdade: a idempotência confere o pai FINISHED e as contagens de
filhas por role, mas não detecta adulteração direta no SQLite (métricas/tags alteradas à mão). Os stores
científicos e seus hashes é que mandam; `cli.py compare` e `verify-models` reconferem o índice contra eles e
`import --rebuild` reconstrói tudo a partir dos arquivos.
"""
from __future__ import annotations

import hashlib
import json
import math
import functools
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from mlflow import MlflowClient
from mlflow.entities import Metric, Param

import tracking

BATCH = 90  # limite do MLflow é 100 por tipo em log_batch
MAX_PARAM_CHARS = 6000
MAX_TAG_CHARS = 8000
KEY_RE = re.compile(r"^[A-Za-z0-9_\-. :/]+$")
INCOMPLETE_STATUSES = ("RUNNING", "FAILED", "KILLED")
METRIC_KEYS = (
    "log_loss", "brier", "pr_auc_average_precision", "roc_auc",
    "prevalence", "expected", "mean_probability", "n", "positives",
)


class ImporterError(RuntimeError):
    """Falha de verificação ou de importação (mensagem em português, pensada para o usuário)."""


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compact(value) -> str:
    return json.dumps(value, separators=(",", ":"))


def mtime_ms(path) -> int:
    return int(Path(path).stat().st_mtime * 1000)


def is_null(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


class Bag:
    """Acumula métricas copiadas e a lista de chaves nulas (não viram métrica)."""

    def __init__(self) -> None:
        self.metrics: dict[str, float] = {}
        self.nulls: list[str] = []

    def add(self, key: str, value) -> None:
        if is_null(value):
            self.nulls.append(key)
        else:
            self.metrics[key] = float(value)

    def add_block(self, block: dict, prefix: str = "") -> None:
        for k in METRIC_KEYS:
            self.add(prefix + k, block.get(k))


# ---------------------------------------------------------------- limpeza

def _artifact_paths(client: MlflowClient, run_id: str) -> tuple[Path | None, Path | None]:
    """(diretório <run_id>, diretório artifacts) a partir do artifact_uri da execução, se for local."""
    uri = client.get_run(run_id).info.artifact_uri
    if not uri.startswith("file:"):
        return None, None
    art = Path(unquote(urlparse(uri).path))
    run_dir = art.parent if art.name == "artifacts" and art.parent.name == run_id else art
    return run_dir, art


def remove_run_dir(run_dir: Path, home: Path) -> None:
    """Apaga `run_dir` só se estiver estritamente dentro de `<home>/artifacts`; senão levanta ImporterError."""
    root = (Path(home).resolve() / "artifacts")
    p = Path(run_dir).resolve()
    if p == root or not p.is_relative_to(root):
        raise ImporterError(f"Recusando apagar {p}: fora de {root}")
    if p.exists():
        shutil.rmtree(p)


def delete_runs(client: MlflowClient, run_ids, home: Path) -> list[str]:
    """Marca as execuções como deletadas e apaga seus diretórios. Devolve a lista de erros (não os engole)."""
    errors: list[str] = []
    for rid in run_ids:
        try:
            run_dir, _ = _artifact_paths(client, rid)
        except Exception as exc:
            errors.append(f"{rid}: ao ler a execução: {exc!r}")
            run_dir = None
        try:
            client.delete_run(rid)
        except Exception as exc:
            errors.append(f"{rid}: delete_run: {exc!r}")
        if run_dir is not None:
            try:
                remove_run_dir(run_dir, home)
            except Exception as exc:
                errors.append(f"{rid}: diretório {run_dir}: {exc!r}")
    return errors


def child_runs(client: MlflowClient, exp_id: str, parent_id: str) -> list:
    return client.search_runs([exp_id], filter_string=f"tags.`mlflow.parentRunId` = '{parent_id}'",
                              max_results=10000)


def purge_import(client: MlflowClient, exp_id: str, home: Path, freeze_sha: str, *,
                 everything: bool = False) -> list[str]:
    """Apaga pais deste freeze (RUNNING/FAILED/KILLED; todos se `everything`) com suas filhas e diretórios.

    Devolve os run_ids apagados. Erros de limpeza viram ImporterError (nada é engolido)."""
    parents = client.search_runs(
        [exp_id], filter_string=f"tags.source_freeze_sha256 = '{freeze_sha}' and tags.role = 'parent'",
        max_results=1000)
    doomed: list[str] = []
    for p in parents:
        if everything or p.info.status in INCOMPLETE_STATUSES:
            doomed += [c.info.run_id for c in child_runs(client, exp_id, p.info.run_id)]
            doomed.append(p.info.run_id)
    errors = delete_runs(client, doomed, home)
    if errors:
        raise ImporterError("Falha ao limpar importação incompleta:\n  " + "\n  ".join(errors))
    return doomed


def role_counts(client: MlflowClient, exp_id: str, parent_id: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in child_runs(client, exp_id, parent_id):
        role = c.data.tags.get("role", "?")
        out[role] = out.get(role, 0) + 1
    return out


def finished_parents(client: MlflowClient, exp_id: str, freeze_sha: str) -> list:
    """Todos os pais FINISHED deste freeze, mais recente primeiro (normalmente um; dois só após um `--rebuild`
    interrompido entre "nova importação pronta" e "antiga apagada")."""
    return tracking.find_parents(exp_id, freeze_sha, client)


def _warn_stale_code(existing, module_file, label: str) -> None:
    """Avisa (stderr, sem falhar) quando o pai existente foi importado com outro código de importador."""
    old = existing.data.tags.get("importer_code_sha256")
    now = tracking.importer_code_sha256(module_file)
    if old != now:
        print(f"aviso ({label}): a importação existente ({existing.info.run_id}) foi feita com outro código do "
              f"importador (importer_code_sha256 {str(old)[:12]} != atual {now[:12]}); "
              "rode com --rebuild para reimportar com o código atual.", file=sys.stderr)


def execute(client: MlflowClient, exp_id: str, home: Path, freeze_sha: str, expected: dict[str, int],
            rebuild: bool, label: str, error_cls, make_importer, module_file) -> dict:
    """Fluxo completo e idempotente de uma importação. Devolve {parent_run_id, created, counts}.

    1. Limpa só importações INCOMPLETAS (RUNNING/FAILED/KILLED) deste freeze. Mais de um pai FINISHED do mesmo
       freeze (rebuild interrompido) sem `rebuild` é erro claro pedindo `--rebuild`.
    2. Pai FINISHED existente e sem `rebuild`: confere as contagens por role (divergência -> erro) e o código do
       importador (divergência -> aviso em stderr) e devolve `created=False`.
    3. Com `rebuild`, a importação nova é feita PRIMEIRO (com rollback próprio em caso de falha) e só depois a
       antiga é apagada; o home nunca fica sem uma importação completa do freeze.
    """
    purge_import(client, exp_id, home, freeze_sha, everything=False)
    parents = finished_parents(client, exp_id, freeze_sha)
    existing = parents[0] if parents else None
    stale: list[str] = []
    if len(parents) > 1 and not rebuild:
        raise error_cls(
            f"Há {len(parents)} importações FINISHED de {label} para o mesmo freeze "
            f"({', '.join(p.info.run_id for p in parents)}): provavelmente um `--rebuild` foi interrompido depois de "
            "concluir a nova importação e antes de apagar a antiga. Rode novamente com --rebuild para ficar com "
            "uma só importação completa.")
    if existing is not None and not rebuild:
        got = role_counts(client, exp_id, existing.info.run_id)
        if got != expected:
            raise error_cls(
                f"Importação {label} existente ({existing.info.run_id}) está incompleta: filhas por role {got}, "
                f"esperado {expected}. Rode novamente com --rebuild.")
        _warn_stale_code(existing, module_file, label)
        return {"parent_run_id": existing.info.run_id, "created": False, "counts": {"parent": 1, **got}}
    if existing is not None:
        for p in parents:
            stale += [c.info.run_id for c in child_runs(client, exp_id, p.info.run_id)]
            stale.append(p.info.run_id)
    result = run_import(make_importer(), expected)
    if stale:
        errors = delete_runs(client, stale, home)
        if errors:
            raise error_cls("A nova importação foi concluída, mas a antiga não pôde ser apagada:\n  "
                            + "\n  ".join(errors))
    return result


# ---------------------------------------------------------------- importador base

class BaseImporter:
    """Cria execuções (new_run), mantém contagens e desfaz tudo em caso de falha (rollback)."""

    error_cls = ImporterError
    module_file: Path = Path(__file__)

    def __init__(self, store: Path, client: MlflowClient, exp_id: str, ctx: dict, home: Path) -> None:
        self.store, self.client, self.exp_id, self.ctx, self.home = store, client, exp_id, ctx, Path(home)
        self.created: list[str] = []
        self.counts: dict[str, int] = {}
        self.imported_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            self.rel_store = Path(store).resolve().relative_to(Path(tracking.stores_root()).resolve()).as_posix()
        except ValueError:
            self.rel_store = Path(store).resolve().as_posix()
        self.repo = Path(__file__).resolve().parent

    def require(self, cond: bool, msg: str) -> None:
        if not cond:
            raise self.error_cls(msg)

    def base_tags(self, dataset_sha, design_sha, seed, role) -> dict:
        return tracking.base_tags(
            self.rel_store, self.ctx["freeze_sha"], dataset_sha, design_sha, seed, role, self.repo,
            importer_file=self.module_file, imported_at=self.imported_at)

    def tags(self, role: str, extra: dict | None = None) -> dict:  # pragma: no cover - sobrescrito
        raise NotImplementedError

    # -- guardas de tamanho / chaves -----------------------------------------
    def check_kv(self, kind: str, key: str, value=None, limit: int | None = None) -> None:
        self.require(isinstance(key, str) and bool(KEY_RE.match(key)),
                     f"Chave de {kind} inválida para o MLflow: {key!r}")
        if limit is not None:
            self.require(len(value) <= limit,
                         f"{kind} '{key}' tem {len(value)} caracteres (limite {limit}); não será truncado")

    def new_run(self, name: str, role: str, source, bag: Bag, params: dict, *, parent=None,
                extra_tags: dict | None = None, artifacts: list | None = None, finish: bool = True) -> str:
        """Cria a execução, registra params/métricas, envia artefatos e (se `finish`) a termina como FINISHED."""
        start = mtime_ms(source)
        tags = self.tags(role, extra_tags)
        tags["mlflow.runName"] = name
        if parent:
            tags["mlflow.parentRunId"] = parent
        if bag.nulls:
            tags["null_metrics"] = json.dumps(bag.nulls)
        tags = {k: str(v) for k, v in tags.items()}
        params = {k: str(v) for k, v in params.items()}
        for k, v in tags.items():
            self.check_kv("tag", k, v, MAX_TAG_CHARS)
        for k, v in params.items():
            self.check_kv("param", k, v, MAX_PARAM_CHARS)
        for k in bag.metrics:
            self.check_kv("métrica", k)
        for path, _sub in artifacts or []:
            self.require(Path(path).suffix != ".parquet", f"parquet não pode virar artefato: {path}")
            self.require(Path(path).is_file(), f"Artefato ausente: {path}")
        run = self.client.create_run(self.exp_id, start_time=start, tags=tags, run_name=name)
        rid = run.info.run_id
        self.created.append(rid)
        mets = [Metric(k, v, start, 0) for k, v in bag.metrics.items()]
        pars = [Param(k, v) for k, v in params.items()]
        for i in range(0, max(len(mets), len(pars)), BATCH):
            self.client.log_batch(rid, metrics=mets[i:i + BATCH], params=pars[i:i + BATCH])
        for path, sub in artifacts or []:
            self.client.log_artifact(rid, str(path), sub)
        if finish:
            self.client.set_terminated(rid, "FINISHED", end_time=start)
        self.counts[role] = self.counts.get(role, 0) + 1
        return rid

    def rollback(self) -> list[str]:
        """Apaga tudo o que a tentativa criou (execuções e diretórios). Devolve os erros de limpeza."""
        return delete_runs(self.client, list(reversed(self.created)), self.home)

    def run_all(self) -> str:  # pragma: no cover - sobrescrito
        raise NotImplementedError


def temp_json(tmp: str, name: str, obj) -> Path:
    p = Path(tmp) / name
    p.write_text(json.dumps(obj, indent=1))
    return p


def wrap_errors(error_cls, where: str):
    """Decorador: qualquer exceção que não seja ImporterError vira `error_cls` com contexto (causa preservada)."""
    def deco(fn):
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except ImporterError:
                raise
            except Exception as exc:
                new = error_cls(f"{where}: {type(exc).__name__}: {exc}")
                for note in getattr(exc, "__notes__", []):
                    new.add_note(note)
                raise new from exc
        return inner
    return deco


def run_import(imp: BaseImporter, expected: dict[str, int]) -> dict:
    """Executa `imp.run_all()`; em qualquer falha faz rollback e relança com os erros de limpeza anexados."""
    try:
        parent = imp.run_all()
        children = {r: n for r, n in imp.counts.items() if r != "parent"}
        imp.require(children == expected,
                    f"Contagens por role {children} diferem do esperado {expected}")
    except BaseException as exc:
        errors = imp.rollback()
        if errors:
            exc.add_note("Erros ao desfazer a importação parcial:\n  " + "\n  ".join(errors))
        raise
    return {"parent_run_id": parent, "created": True, "counts": dict(imp.counts)}
