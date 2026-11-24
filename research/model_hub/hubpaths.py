"""Caminhos do hub de modelos. Reaproveita a resolução do checkout principal e do MLflow de
`research/mlflow_tracking/tracking.py` (importado por caminho, sem alterá-lo)."""
import importlib.util
import os
from pathlib import Path

_TRACKING_PATH = Path(__file__).resolve().parent.parent / "mlflow_tracking" / "tracking.py"
_spec = importlib.util.spec_from_file_location("hub_mlflow_tracking", _TRACKING_PATH)
tracking = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tracking)


def hub_home() -> Path:
    """Home dos dados do hub: `NFL_HUB_HOME` ou `<checkout principal>/editorial/local-artifacts/model-hub`."""
    env = os.environ.get("NFL_HUB_HOME")
    if env:
        return Path(env)
    return tracking.main_checkout() / "editorial" / "local-artifacts" / "model-hub"


def mlflow_home() -> Path:
    return tracking.mlflow_home()
