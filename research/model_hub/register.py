"""Registro de modelos do hub no MLflow Model Registry como pyfunc *models from code*, sem pickle.

O modelo é só (código em `model_code/` + `params.json` + `params.sha256`); o código confere o hash ao carregar.
Só entra no registry o que veio de um backtest FINISHED que bateu os baselines (`beats_baselines=true`).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import mlflow
import yaml
from mlflow import MlflowClient

import hubtrack

ALIAS = "champion"
BAD_SUFFIXES = (".pkl", ".pickle", ".joblib", ".cloudpickle")
MODULE_DIR = Path(__file__).resolve().parent


class RegisterError(RuntimeError):
    """Falha de registro (mensagem em português)."""


def pinned_requirements() -> list[str]:
    """Pins exatos de numpy, pandas e scikit-learn lidos de requirements.txt."""
    out = []
    for line in (MODULE_DIR / "requirements.txt").read_text().splitlines():
        if line.split("==")[0].strip() in ("numpy", "pandas", "scikit-learn"):
            out.append(line.strip())
    return out


def registered_name(model_key: str) -> str:
    return hubtrack.experiment_name(model_key)


def _check_source(client: MlflowClient, model_key: str, source_run_id: str, require_beats: bool):
    run = client.get_run(source_run_id)
    exp = client.get_experiment(run.info.experiment_id).name
    if exp != registered_name(model_key):
        raise RegisterError(f"execução de origem está em {exp!r}, esperado {registered_name(model_key)!r}")
    t = run.data.tags
    if t.get("role") != "parent" or run.info.status != "FINISHED":
        raise RegisterError("source_run_id deve ser um pai de backtest FINISHED")
    if require_beats and t.get("beats_baselines") != "true":
        raise RegisterError("o backtest de origem não bateu os baselines: modelo não vai para o registry")
    return run


def check_no_pickle(model_uri: str) -> None:
    """Baixa o modelo e confere: sem arquivo de pickle e MLmodel do tipo *models from code*."""
    with tempfile.TemporaryDirectory(prefix="hub-model-") as tmp:
        local = mlflow.artifacts.download_artifacts(artifact_uri=model_uri, dst_path=tmp)
        bad = [os.path.join(r, f) for r, _d, fs in os.walk(local) for f in fs if f.lower().endswith(BAD_SUFFIXES)]
        if bad:
            raise RegisterError(f"arquivo de pickle no modelo: {bad}")
        conf = yaml.safe_load((Path(local) / "MLmodel").read_text())["flavors"]["python_function"]
        if conf.get("loader_module") != "mlflow.pyfunc.loaders.code_model" or "python_model" in conf:
            raise RegisterError(f"MLmodel não é models-from-code (loader_module={conf.get('loader_module')!r})")


def _check_selected(client: MlflowClient, source, source_run_id: str, model_name: str, hyperparams: dict,
                    require_beats: bool) -> None:
    """Prova que `model_name` e `hyperparams` são os do pai: (1) `model_name == selected_model` do pai (com
    `require_beats=False`, basta ser um candidato do pai); (2) `hyperparams` idênticos aos gravados no `config.json`."""
    selected = source.data.tags.get("selected_model", "none")
    if require_beats and selected != model_name:
        raise RegisterError(f"o pai selecionou {selected!r}, não {model_name!r}: só o modelo selecionado é registrado")
    try:
        cfg = json.loads(Path(client.download_artifacts(source_run_id, "config.json")).read_text())
    except Exception as exc:
        raise RegisterError(f"config.json do pai ilegível: {exc}") from exc
    entries = [m for m in cfg.get("models", []) if m["name"] == model_name and m["role"] == "candidate"]
    if len(entries) != 1:
        raise RegisterError(f"{model_name!r} não é um candidato do backtest de origem")
    if hubtrack.canonical_json(entries[0]["params"]) != hubtrack.canonical_json(hyperparams):
        raise RegisterError(f"hiperparâmetros de {model_name!r} diferem dos gravados no config.json do pai")


def register_json_model(model_key: str, code_path, params: dict, input_example, source_run_id: str, *,
                        model_name: str, hyperparams: dict, train_data_sha256: str,
                        alias: str = ALIAS, require_beats_baselines: bool = True) -> dict:
    """Registra `hub-<model_key>` e aponta `alias`. Devolve {name, version, run_id, params_sha256, ...}.

    `params` é o JSON do modelo AJUSTADO (artefato `params.json`); `code_path` é o arquivo de pyfunc (com
    `set_model`), cujo sha256 vira `model_code_sha256`. As tags obrigatórias do hub são copiadas do pai de origem
    (role=final).

    Prova de correspondência com o backtest: `model_name` deve ser o `selected_model` do pai e `hyperparams`
    (o `params()` do modelo) idênticos aos gravados no `config.json` do pai para esse modelo. NÃO se exige igualdade
    de `params` com os `fitted.json` das dobras: o modelo final é reajustado com todos os dados, então os
    parâmetros aprendidos diferem por construção. O run final grava `selected_model`, `hyperparams_sha256`,
    `source_run_id` e `train_data_sha256` (impressão digital dos dados do ajuste final, `backtest.data_fingerprint`)."""
    hubtrack.configure()
    exp_id = hubtrack.experiment(model_key)
    client = MlflowClient()
    source = _check_source(client, model_key, source_run_id, require_beats_baselines)
    _check_selected(client, source, source_run_id, model_name, hyperparams, require_beats_baselines)
    code_path = Path(code_path)
    params_text = hubtrack.canonical_json(params)  # levanta se não for JSON puro
    params_sha = hubtrack.sha256_json(params)
    code_sha = hubtrack.sha256_file(code_path)
    name = registered_name(model_key)
    tags = {k: v for k, v in source.data.tags.items() if k in hubtrack.REQUIRED_TAGS}
    tags.update({"role": "final", "model_code_sha256": code_sha, "source_run_id": source_run_id,
                 "params_sha256": params_sha, "model_name": name, "selected_model": model_name,
                 "hyperparams_sha256": hubtrack.sha256_json(hyperparams), "train_data_sha256": train_data_sha256})
    hubtrack.validate_tags(tags)
    run_id = hubtrack.start_run(model_key, tags, run_name=f"{name} · modelo registrado")
    with tempfile.TemporaryDirectory(prefix="hub-register-") as tmp:
        pj, ps = Path(tmp) / "params.json", Path(tmp) / "params.sha256"
        pj.write_text(params_text)
        ps.write_text(hubtrack.sha256_file(pj))
        version = None
        try:
            with mlflow.start_run(run_id=run_id):
                mlflow.pyfunc.log_model(
                    name=name, python_model=str(code_path),
                    artifacts={"params_json": str(pj), "params_sha256": str(ps)},
                    input_example=input_example, pip_requirements=pinned_requirements(), registered_model_name=name)
            found = [v for v in client.search_model_versions(f"name = '{name}'") if v.run_id == run_id]
            if len(found) != 1:
                raise RegisterError("versão do modelo não encontrada após log_model")
            version = str(found[0].version)
            check_no_pickle(f"models:/{name}/{version}")
            for k, v in {"params_sha256": params_sha, "model_code_sha256": code_sha,
                         "source_run_id": source_run_id, "selected_model": model_name,
                         "hyperparams_sha256": tags["hyperparams_sha256"],
                         "train_data_sha256": train_data_sha256}.items():
                client.set_model_version_tag(name, version, k, v)
            client.set_registered_model_alias(name, alias, version)
            hubtrack.finish_run(run_id)
        except BaseException:
            if version is not None:
                try:
                    client.delete_model_version(name, version)
                except Exception:
                    pass
            hubtrack.finish_run(run_id, "FAILED")
            raise
    return {"name": name, "version": version, "run_id": run_id, "params_sha256": params_sha, "experiment_id": exp_id}

