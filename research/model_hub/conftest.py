"""Põe esta pasta no sys.path, isola HUB/MLflow por teste e bloqueia rede."""
import os
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")


def pytest_configure(config):
    config.addinivalue_line("markers", "real_data: usa o cache real do hub (pulado quando ausente)")
    config.addinivalue_line("markers", "network: pode usar rede (nunca no CI)")
    config.addinivalue_line(
        "filterwarnings", "ignore:The ``noload`` loader strategy is deprecated:sqlalchemy.exc.SADeprecationWarning")


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch, request):
    """NFL_HUB_HOME e NFL_MLFLOW_HOME em tmp_path, cwd vazio, socket bloqueado (exceto `network`/`real_data`
    não liberam rede: só `network`)."""
    import mlflow
    cwd = tmp_path / "_cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    if "real_data" not in request.keywords:
        monkeypatch.setenv("NFL_HUB_HOME", str(tmp_path / "_hub"))
    monkeypatch.setenv("NFL_MLFLOW_HOME", str(tmp_path / "_mlflow"))
    for var in ("MLFLOW_TRACKING_URI", "MLFLOW_REGISTRY_URI"):
        monkeypatch.setenv(var, "")
        monkeypatch.delenv(var)
    if "network" not in request.keywords:
        def _blocked(*a, **k):
            raise RuntimeError("rede bloqueada nos testes")
        monkeypatch.setattr(socket.socket, "connect", _blocked)
    yield
    while mlflow.active_run() is not None:
        mlflow.end_run()
    mlflow.set_tracking_uri(None)
    mlflow.set_registry_uri(None)
    os.environ.pop("MLFLOW_TRACKING_URI", None)
    os.environ.pop("MLFLOW_REGISTRY_URI", None)
    mlflow.tracking.fluent._active_experiment_id = None
