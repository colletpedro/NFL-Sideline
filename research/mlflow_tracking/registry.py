"""Registro dos modelos em uso no laboratório (M3 e B2) no MLflow, como pyfunc *models from code*, sem pickle.

Cada modelo vira UMA execução `role=model` no experimento do seu freeze (não é filha do pai importado; só
guarda `source_parent_run_id`) e UMA versão do modelo registrado, com o alias `champion`. O artefato é o JSON
congelado do store; os arquivos de código estão em `model_code/`. `verify_models` recarrega `models:/<nome>@champion`
e confere previsões, métricas e hashes contra os stores e os pacotes do laboratório. O MLflow é só um índice:
se divergir dos arquivos, o MLflow está errado.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
import pandas as pd
import mlflow
from mlflow import MlflowClient
from mlflow.models import ModelSignature
from mlflow.types import ColSpec, Schema, TensorSpec

import importer_base
import tracking

ALIAS = "champion"
MODULE_DIR = Path(__file__).resolve().parent
CODE_DIR = MODULE_DIR / "model_code"
REPO_ROOT = MODULE_DIR.parent.parent
FROZEN_V1_MODEL_PY = REPO_ROOT / "research" / "qb_interception_risk" / "model.py"

M3_JSON_SHA = "38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6"
V1_MODEL_PY_SHA = "39a18d8ffe504f9bab87ccbb0dc87d3407d0f85bba3fb5dbd7c1308533fc5d80"
B2_JSON_SHA = "ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8"

V2_STORE = "qb-risk-temporal-calibration-v2/20261104-v2"
V1_STORE = "qb-interception-risk-baseline-v1/20261104-v1"
XINT_STORE = "qb-expected-interceptions-v1/20261105-v1"
M3_COLUMNS = ["down", "qtr", "ydstogo", "yardline_100", "quarter_seconds_remaining", "score_differential"]
PINNED = ("numpy", "pandas", "scipy", "scikit-learn")
BAD_SUFFIXES = (".pkl", ".pickle", ".joblib")


class RegistryError(RuntimeError):
    """Falha de verificação ou de registro (mensagem em português)."""


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise RegistryError(msg)


def pinned_requirements(lock: Path | None = None) -> list[str]:
    """Pins exatos de numpy, pandas, scipy e scikit-learn lidos do requirements.lock."""
    text = (lock or MODULE_DIR / "requirements.lock").read_text()
    out = []
    for name in PINNED:
        m = re.search(rf"^{re.escape(name)}==(\S+)$", text, re.M)
        _require(m is not None, f"{name} ausente do requirements.lock")
        out.append(f"{name}=={m.group(1)}")
    return out


# ------------------------------------------------------------------ especificações

def _specs(stores: Path) -> dict:
    """Parâmetros fixos de cada modelo. `stores` = raiz dos stores científicos."""
    v2 = stores / V2_STORE
    xint = stores / XINT_STORE
    return {
        "m3": dict(
            model_name=tracking.MODELS["m3"], experiment="v2", store=V2_STORE,
            json_path=v2 / "experiment-verified" / "frozen" / "M3.json", json_sha=M3_JSON_SHA,
            freeze_path=v2 / "experiment-verified" / "frozen" / "freeze.json",
            code=CODE_DIR / "m3_pyfunc.py", code_paths=[FROZEN_V1_MODEL_PY],
            extra_tags={"v1_model_py_sha256": V1_MODEL_PY_SHA}, input_columns=M3_COLUMNS),
        "b2": dict(
            model_name=tracking.MODELS["b2"], experiment="xint", store=XINT_STORE,
            json_path=xint / "final" / "model.json", json_sha=B2_JSON_SHA,
            freeze_path=xint / "development" / "freeze.json",
            code=CODE_DIR / "b2_pyfunc.py", code_paths=[],
            extra_tags={}, input_columns=["is_interception_worthy"]),
    }


def _signature(key: str) -> ModelSignature:
    if key == "m3":
        ins = Schema([ColSpec("double", c) for c in M3_COLUMNS])
    else:
        ins = Schema([ColSpec("long", "is_interception_worthy")])
    return ModelSignature(inputs=ins, outputs=Schema([TensorSpec(np.dtype("float64"), (-1,))]))


def _frame(key: str, df: pd.DataFrame) -> pd.DataFrame:
    """Só as colunas de entrada, com os dtypes da assinatura."""
    if key == "m3":
        return df[M3_COLUMNS].astype("float64").reset_index(drop=True)
    return pd.DataFrame({"is_interception_worthy": df["is_interception_worthy"].astype("int64").to_numpy()})


def _m3_2026(stores: Path) -> pd.DataFrame:
    """Linhas 2026 de predictions.parquet com as features do dataset da v1 (join por game_id, play_id)."""
    pred = pd.read_parquet(stores / V2_STORE / "experiment-verified" / "predictions.parquet")
    pred = pred[pred.season.eq(2026)]
    ds = pd.read_parquet(stores / V1_STORE / "build-v2" / "dataset.parquet",
                         columns=["game_id", "play_id", *M3_COLUMNS])
    df = pred.merge(ds, on=["game_id", "play_id"], how="left", validate="one_to_one")
    _require(len(df) == len(pred) and not df[M3_COLUMNS[0]].isna().all(), "join com o dataset da v1 falhou")
    return df.reset_index(drop=True)


def _b2_2026(stores: Path) -> pd.DataFrame:
    return pd.read_parquet(stores / XINT_STORE / "application-complete" / "pass_predictions.parquet")


def _input_example(key: str, stores: Path) -> pd.DataFrame:
    if key == "m3":
        df = _m3_2026(stores)
        df = df[df[M3_COLUMNS].notna().all(axis=1)].head(5)
    else:
        d = _b2_2026(stores)
        df = pd.concat([d[d.is_interception_worthy.eq(0)].head(3), d[d.is_interception_worthy.eq(1)].head(2)])
    return _frame(key, df)


# ------------------------------------------------------------------ registro

def _find_version(client: MlflowClient, name: str, tags: dict):
    """Versão registrada cujas tags batem com `tags` (as mais recentes primeiro), ou None."""
    try:
        versions = client.search_model_versions(f"name = '{name}'")
    except Exception:
        return None
    for v in sorted(versions, key=lambda v: int(v.version), reverse=True):
        if all(v.tags.get(k) == val for k, val in tags.items()):
            return v
    return None


def _run_active(client: MlflowClient, run_id: str | None) -> bool:
    """A execução existe e não foi deletada (um `--rebuild` apaga o pai de origem e invalida versões antigas)."""
    if not run_id:
        return False
    try:
        return client.get_run(run_id).info.lifecycle_stage == "active"
    except Exception:
        return False


def _version_source_is_live(client: MlflowClient, version) -> bool:
    """A execução do modelo e o pai importado de origem (`source_parent_run_id`) da versão ainda existem e estão ativos.

    Versões antigas sem a tag `source_parent_run_id` caem para a tag da execução do modelo."""
    run_id = version.tags.get("source_run_id")
    if not _run_active(client, run_id):
        return False
    parent_id = version.tags.get("source_parent_run_id") or client.get_run(run_id).data.tags.get("source_parent_run_id")
    return _run_active(client, parent_id)


def _local_dir(location: str) -> Path | None:
    return Path(unquote(urlparse(location).path)) if location and location.startswith("file:") else None


def discard_model_run(client: MlflowClient, name: str, run_id: str, home: Path) -> list[str]:
    """Apaga de verdade (não só soft delete) uma tentativa de registro: as versões de `name` criadas pela execução,
    seus modelos logados, a execução e os diretórios de artefatos (sempre dentro de `<home>/artifacts`).
    Devolve a lista de erros; não os engole."""
    errors: list[str] = []

    def step(what: str, fn) -> None:
        try:
            fn()
        except Exception as exc:  # cada passo é independente: tenta todos e reporta o que falhou
            errors.append(f"{what}: {exc!r}")

    model_ids: set[str] = set()
    versions: list[str] = []
    try:
        for v in client.search_model_versions(f"name = '{name}'"):
            if v.run_id == run_id:
                versions.append(str(v.version))
                if v.model_id:
                    model_ids.add(v.model_id)
    except Exception as exc:
        errors.append(f"{name}: ao listar versões: {exc!r}")
    try:
        exp_id = client.get_run(run_id).info.experiment_id
        model_ids |= {lm.model_id for lm in client.search_logged_models([exp_id]) if lm.source_run_id == run_id}
    except Exception as exc:
        errors.append(f"{run_id}: ao procurar modelos logados: {exc!r}")
    dirs: list[Path] = []
    for mid in sorted(model_ids):
        try:
            loc = _local_dir(client.get_logged_model(mid).artifact_location)
            if loc is not None:
                dirs.append(loc.parent if loc.name == "artifacts" and loc.parent.name == mid else loc)
        except Exception as exc:
            errors.append(f"{mid}: ao ler o modelo logado: {exc!r}")
    try:
        run_dir, _ = importer_base._artifact_paths(client, run_id)
        if run_dir is not None:
            dirs.append(run_dir)
    except Exception as exc:
        errors.append(f"{run_id}: diretório da execução: {exc!r}")
    for ver in versions:
        step(f"delete_model_version {name} v{ver}", lambda ver=ver: client.delete_model_version(name, ver))
    for mid in sorted(model_ids):
        step(f"delete_logged_model {mid}", lambda mid=mid: client.delete_logged_model(mid))
    step(f"delete_run {run_id}", lambda: client.delete_run(run_id))
    for d in dirs:
        step(f"diretório {d}", lambda d=d: importer_base.remove_run_dir(d, home))
    return errors


def _purge_orphans(client: MlflowClient, name: str, exp_id: str, home: Path) -> list[str]:
    """Limpa restos de um `register` interrompido: versões de `name` sem a tag `model_sha256` (e que não sejam o
    champion) com suas execuções role=model e diretórios, e execuções role=model deste modelo que nunca terminaram.
    Devolve os run_ids apagados. Falhas de limpeza viram RegistryError."""
    try:
        champion = str(client.get_model_version_by_alias(name, ALIAS).version)
    except Exception:
        champion = None
    try:
        versions = client.search_model_versions(f"name = '{name}'")
    except Exception:
        versions = []
    removed: list[str] = []
    errors: list[str] = []
    for v in versions:
        if v.tags.get("model_sha256") or str(v.version) == champion:
            continue
        run_id = v.run_id
        if run_id and _is_model_run(client, run_id):
            errors += discard_model_run(client, name, run_id, home)
            removed.append(run_id)
        else:  # versão órfã sem execução role=model reconhecível: só a versão
            try:
                client.delete_model_version(name, str(v.version))
            except Exception as exc:
                errors.append(f"{name} v{v.version}: {exc!r}")
    for r in client.search_runs([exp_id], filter_string=(
            f"tags.role = 'model' and tags.model_name = '{name}' and attributes.status != 'FINISHED'"),
            max_results=1000):
        errors += discard_model_run(client, name, r.info.run_id, home)
        removed.append(r.info.run_id)
    if errors:
        raise RegistryError("Falha ao limpar restos de um registro interrompido:\n  " + "\n  ".join(errors))
    return removed


def _is_model_run(client: MlflowClient, run_id: str) -> bool:
    try:
        return client.get_run(run_id).data.tags.get("role") == "model"
    except Exception:
        return False


def _set_alias(client: MlflowClient, name: str, version: str) -> None:
    try:
        cur = str(client.get_model_version_by_alias(name, ALIAS).version)
    except Exception:
        cur = None
    if cur != str(version):
        client.set_registered_model_alias(name, ALIAS, str(version))


def register_one(key: str, home: Path | None = None, stores: Path | None = None) -> dict:
    """Registra (ou reaproveita) o modelo `key` ('m3' ou 'b2'). Devolve nome, versão, run_id e `created`."""
    home = tracking.configure(home)
    stores = Path(stores) if stores is not None else tracking.stores_root()
    spec = _specs(stores)[key]
    _require(spec["json_path"].is_file(), f"Artefato ausente: {spec['json_path']}")
    _require(sha256_file(spec["json_path"]) == spec["json_sha"],
             f"sha256 de {spec['json_path'].name} difere do valor congelado {spec['json_sha']}")
    for cp in spec["code_paths"]:
        _require(sha256_file(cp) == V1_MODEL_PY_SHA, f"{cp} difere do arquivo congelado (sha256 {V1_MODEL_PY_SHA})")
    code_sha = sha256_file(spec["code"])
    vtags = {"model_sha256": spec["json_sha"], "model_code_sha256": code_sha, "source_store": spec["store"],
             **spec["extra_tags"]}

    client = MlflowClient()
    name = spec["model_name"]
    exp_id = tracking.ensure_experiment(spec["experiment"], home)
    _purge_orphans(client, name, exp_id, home)
    existing = _find_version(client, name, {k: vtags[k] for k in ("model_sha256", "model_code_sha256")})
    if existing is not None and not _version_source_is_live(client, existing):
        existing = None  # origem apagada (p.ex. `import --rebuild`): cria nova execução/versão e move o alias
    if existing is not None:
        _set_alias(client, name, existing.version)
        return {"model": name, "version": str(existing.version), "run_id": existing.tags.get("source_run_id"),
                "created": False}

    freeze_sha = sha256_file(spec["freeze_path"])
    parent = tracking.find_parent(exp_id, freeze_sha)
    _require(parent is not None, f"Execução-pai do freeze {freeze_sha} não importada; rode `cli.py import` antes")
    pt = parent.data.tags
    tags = tracking.base_tags(
        spec["store"], freeze_sha, pt["dataset_sha256"], pt["design_sha256"], pt["seed"], "model",
        MODULE_DIR, importer_file=Path(__file__).resolve())
    tags.update({"source_parent_run_id": parent.info.run_id, "model_name": name, "model_sha256": spec["json_sha"],
                 "model_code_sha256": code_sha})
    example = _input_example(key, stores)
    run = mlflow.start_run(experiment_id=exp_id, run_name=f"{name} · modelo registrado", tags=tags)
    run_id = run.info.run_id
    version = None
    try:
        mlflow.pyfunc.log_model(
            name=name, python_model=str(spec["code"]), artifacts={"model_json": str(spec["json_path"])},
            code_paths=[str(p) for p in spec["code_paths"]] or None, signature=_signature(key),
            input_example=example, pip_requirements=pinned_requirements(), registered_model_name=name)
        mlflow.end_run("FINISHED")
        found = [v for v in client.search_model_versions(f"name = '{name}'") if v.run_id == run_id]
        _require(len(found) == 1, "versão do modelo não encontrada após log_model")
        version = str(found[0].version)
        for k, v in {**vtags, "source_run_id": run_id, "source_parent_run_id": parent.info.run_id}.items():
            client.set_model_version_tag(name, version, k, v)
        _set_alias(client, name, version)
    except BaseException as exc:
        if mlflow.active_run() is not None:
            mlflow.end_run("FAILED")
        errors = discard_model_run(client, name, run_id, home)
        if errors:
            exc.add_note("Erros ao desfazer o registro parcial:\n  " + "\n  ".join(errors))
        raise
    return {"model": name, "version": version, "run_id": run_id, "created": True}


def register(which: str = "all", home: Path | None = None, stores: Path | None = None) -> dict[str, dict]:
    keys = ("m3", "b2") if which == "all" else (which,)
    return {k: register_one(k, home, stores) for k in keys}


# ------------------------------------------------------------------ verificação

def _log_loss(y, p) -> float:
    from sklearn.metrics import log_loss
    return float(log_loss(np.asarray(y), np.asarray(p), labels=[0, 1]))


def _clock_seconds(clock: str) -> float:
    m, s = clock.split(":")
    return float(int(m) * 60 + int(s))


def _lab_plays(store: Path) -> list[dict]:
    """Jogadas do pacote ativo (`current.json` -> `packages/<id>/players/*.json`)."""
    cur = json.loads((store / "current.json").read_text())
    plays: list[dict] = []
    for f in sorted((store / "packages" / cur["packageId"] / "players").glob("*.json")):
        plays += json.loads(f.read_text())["plays"]
    return plays


def _metric(client: MlflowClient, exp_id: str, flt: str, key: str) -> float | None:
    runs = client.search_runs([exp_id], filter_string=flt, max_results=5)
    if len(runs) != 1:
        return None
    return runs[0].data.metrics.get(key)


def _max_diff(a, b) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)))) if len(a) else 0.0


def _check_download(key: str, uri: str, spec: dict, problems: list[str], report: dict) -> None:
    tmp = tempfile.mkdtemp(prefix="nfl-model-")
    try:
        local = mlflow.artifacts.download_artifacts(artifact_uri=uri, dst_path=tmp)
        bad, jsons = [], []
        for root, _dirs, files in os.walk(local):
            for f in files:
                if f.lower().endswith(BAD_SUFFIXES):
                    bad.append(os.path.join(root, f))
                if f == spec["json_path"].name:
                    jsons.append(os.path.join(root, f))
        if bad:
            problems.append(f"{key}: arquivo de pickle no modelo: {bad}")
        import yaml
        conf = yaml.safe_load((Path(local) / "MLmodel").read_text())["flavors"]["python_function"]
        # `cloudpickle_version` é só metadado; o que importa é o carregador de código e a ausência de python_model.pkl
        if conf.get("loader_module") != "mlflow.pyfunc.loaders.code_model" or "python_model" in conf:
            problems.append(f"{key}: MLmodel não é do tipo models-from-code (loader_module={conf.get('loader_module')!r})")
        copies = [os.path.join(local, spec["code"].name)]
        if copies and (not os.path.isfile(copies[0]) or sha256_file(copies[0]) != sha256_file(spec["code"])):
            problems.append(f"{key}: cópia do código dentro do modelo ausente ou diferente de model_code/{spec['code'].name}")
        for cp in spec["code_paths"]:
            inner = os.path.join(local, "code", cp.name)
            if not os.path.isfile(inner) or sha256_file(inner) != sha256_file(cp):
                problems.append(f"{key}: code/{cp.name} dentro do modelo ausente ou diferente do arquivo congelado")
        if len(jsons) != 1 or sha256_file(jsons[0]) != spec["json_sha"]:
            problems.append(f"{key}: sha256 do JSON dentro do modelo difere do congelado")
        report["no_pickle"] = not bad
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def verify_models(home: Path | None = None, stores: Path | None = None) -> list[str]:
    """Confere os modelos `champion` contra os stores e os laboratórios. Lista vazia = tudo certo.

    Também guarda as diferenças máximas observadas em `verify_models.report`."""
    home = tracking.configure(home)
    stores = Path(stores) if stores is not None else tracking.stores_root()
    specs = _specs(stores)
    client = MlflowClient()
    problems: list[str] = []
    report: dict = {}
    verify_models.report = report

    for key in ("m3", "b2"):
        spec, name = specs[key], specs[key]["model_name"]
        rep = report.setdefault(key, {})
        uri = f"models:/{name}@{ALIAS}"
        try:
            model = mlflow.pyfunc.load_model(uri)
            ver = client.get_model_version_by_alias(name, ALIAS)
        except Exception as exc:
            problems.append(f"{key}: não foi possível carregar {uri}: {exc!r}")
            continue
        rep["version"] = str(ver.version)
        if not _version_source_is_live(client, ver):
            problems.append(
                f"{key}: a execução de origem do champion (versão {ver.version}: execução do modelo "
                f"{ver.tags.get('source_run_id')!r} ou pai importado {ver.tags.get('source_parent_run_id')!r}) não "
                f"está ativa (p.ex. depois de `import --rebuild`); rode `cli.py register {key}`")
        if ver.tags.get("model_sha256") != spec["json_sha"]:
            problems.append(f"{key}: tag model_sha256 da versão {ver.version} difere do congelado")
        try:
            _check_download(key, uri, spec, problems, rep)
        except Exception as exc:
            problems.append(f"{key}: falha ao inspecionar o modelo baixado: {exc!r}")

        def pred(df):
            return np.asarray(model.predict(_frame(key, df)), dtype="float64")

        if key == "m3":
            df = _m3_2026(stores)
            p = pred(df)
            rep["n_2026"] = len(df)
            rep["max_diff_predictions_parquet"] = _max_diff(p, df["M3"])
            if rep["max_diff_predictions_parquet"] > 1e-12:
                problems.append(f"m3: previsões diferem de predictions.parquet (máx {rep['max_diff_predictions_parquet']:.3e})")
            plays = _lab_plays(stores / "qb-risk-lab-v1")
            lab = pd.DataFrame({
                "down": [x["down"] for x in plays], "ydstogo": [x["distance"] for x in plays],
                "yardline_100": [x["fieldPosition"] for x in plays], "qtr": [x["quarter"] for x in plays],
                "quarter_seconds_remaining": [_clock_seconds(x["clock"]) for x in plays],
                "score_differential": [x["scoreDifferential"] for x in plays]})
            lp = pred(lab)
            rep["n_lab"] = len(plays)
            rep["max_diff_lab"] = _max_diff(lp, [x["probability"] for x in plays])
            if len(plays) != 7970 or rep["max_diff_lab"] > 1e-12:
                problems.append(f"m3: pacote do laboratório: n={len(plays)}, diferença máx {rep['max_diff_lab']:.3e}")
            ll = _log_loss(df["is_interception_worthy"], p)
            exp_id = client.get_experiment_by_name(tracking.EXPERIMENTS["v2"]).experiment_id
            ref = _metric(client, exp_id, "tags.role = 'candidate' and tags.year = '2026' and tags.candidate = 'M3'", "log_loss")
        else:
            d = _b2_2026(stores)
            p = pred(d)
            rep["n_2026"] = len(d)
            rep["max_diff_predictions_parquet"] = _max_diff(p, d["p_interception_given_ftn"])
            if rep["max_diff_predictions_parquet"] > 1e-12:
                problems.append(f"b2: previsões diferem de pass_predictions.parquet (máx {rep['max_diff_predictions_parquet']:.3e})")
            plays = _lab_plays(stores / "qb-risk-outcomes-lab-v1")
            lab = pd.DataFrame({"is_interception_worthy": [x["ftnInterceptionWorthy"] for x in plays]})
            lp = pred(lab)
            rep["n_lab"] = len(plays)
            rep["max_diff_lab"] = _max_diff(lp, [x["pInterceptionGivenFtn"] for x in plays])
            if len(plays) != 7970 or rep["max_diff_lab"] > 1e-12:
                problems.append(f"b2: pacote do laboratório: n={len(plays)}, diferença máx {rep['max_diff_lab']:.3e}")
            ll = _log_loss(d["interception"], p)
            exp_id = client.get_experiment_by_name(tracking.EXPERIMENTS["xint"]).experiment_id
            ref = _metric(client, exp_id, "tags.role = 'application'", "descriptive_only.all.log_loss")
        rep["log_loss"] = ll
        rep["log_loss_mlflow"] = ref
        if ref is None:
            problems.append(f"{key}: métrica de referência não encontrada no MLflow")
        else:
            rep["log_loss_rel_diff"] = abs(ll - ref) / abs(ref)
            if not math.isclose(ll, ref, rel_tol=1e-12, abs_tol=0.0):
                problems.append(f"{key}: log loss recalculado {ll!r} difere da métrica do MLflow {ref!r}")
    return problems
