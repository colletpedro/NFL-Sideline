"""Põe esta pasta no sys.path e isola o estado global do MLflow/ambiente a cada teste."""
import os
import sys
from pathlib import Path

import mlflow
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")


def pytest_configure(config):
    config.addinivalue_line("markers", "real_store: usa o store real da v1 (pulado quando ausente)")
    # Único aviso restante, vindo do MLflow 3.17.2 (sqlalchemy_store.configure_mappers): o código do MLflow usa a
    # estratégia `noload` do SQLAlchemy, já descontinuada. Conhecido e inofensivo; não vem do nosso código.
    config.addinivalue_line(
        "filterwarnings", "ignore:The ``noload`` loader strategy is deprecated:sqlalchemy.exc.SADeprecationWarning")


@pytest.fixture(autouse=True)
def isolated_mlflow(tmp_path, monkeypatch):
    """Cada teste ganha NFL_MLFLOW_HOME, tracking URI e registry URI próprios (em tmp_path) e roda num cwd
    vazio; ao final encerra execuções ativas e restaura o estado global do mlflow e do ambiente."""
    home = tmp_path / "_autouse_home"
    cwd = tmp_path / "_autouse_cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("NFL_MLFLOW_HOME", str(home))
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "")  # registra para restauração
    monkeypatch.setenv("MLFLOW_REGISTRY_URI", "")
    monkeypatch.delenv("MLFLOW_TRACKING_URI")
    monkeypatch.delenv("MLFLOW_REGISTRY_URI")
    import tracking
    tracking.configure(home)
    yield home
    while mlflow.active_run() is not None:
        mlflow.end_run()
    mlflow.set_tracking_uri(None)
    mlflow.set_registry_uri(None)
    os.environ.pop("MLFLOW_TRACKING_URI", None)
    os.environ.pop("MLFLOW_REGISTRY_URI", None)
    mlflow.tracking.fluent._active_experiment_id = None
