"""Modelo MLflow (pyfunc, *models from code*) do M3 congelado da v2: sem pickle.

O artefato `model_json` é o `M3.json` congelado (estrutura logística + offset de intercepto). A inferência da
estrutura é a `predict_json` do arquivo congelado `research/qb_interception_risk/model.py`, empacotado em
`code_paths` sem nenhuma edição. Como o nome genérico `model` pode colidir com qualquer outro módulo do
ambiente, o arquivo é carregado por caminho, sob o nome único `qb_iw_frozen_model`, e só depois de conferir o
sha256 contra o valor congelado.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow.models import set_model
from mlflow.pyfunc import PythonModel
from mlflow.types.type_hints import TypeFromExample
from scipy.special import expit, logit

FROZEN_MODEL_PY_SHA256 = "39a18d8ffe504f9bab87ccbb0dc87d3407d0f85bba3fb5dbd7c1308533fc5d80"
INPUT_COLUMNS = ["down", "qtr", "ydstogo", "yardline_100", "quarter_seconds_remaining", "score_differential"]
_UNIQUE_NAME = "qb_iw_frozen_model"


def _sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _find_frozen_model_py(model_json_path: str) -> Path:
    """`<modelo>/code/model.py` (copiado por `code_paths`); procura também no sys.path como reserva."""
    candidates = [Path(model_json_path).resolve().parent.parent / "code" / "model.py"]
    candidates += [Path(p) / "model.py" for p in sys.path if p]
    for c in candidates:
        if c.is_file() and _sha256(c) == FROZEN_MODEL_PY_SHA256:
            return c
    raise RuntimeError("model.py congelado (sha256 esperado " + FROZEN_MODEL_PY_SHA256 + ") não encontrado no modelo")


def _load_frozen_module(path: Path):
    mod = sys.modules.get(_UNIQUE_NAME)
    if mod is not None and Path(mod.__file__).resolve() == path.resolve():
        return mod
    spec = importlib.util.spec_from_file_location(_UNIQUE_NAME, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_UNIQUE_NAME] = mod
    spec.loader.exec_module(mod)
    return mod


class M3Model(PythonModel):
    """`expit(logit(predict_json(structure, df)) + offset)`, igual a `experiment.predict` da v2."""

    def load_context(self, context):
        path = context.artifacts["model_json"]
        self.artifact = json.loads(Path(path).read_text())
        if self.artifact.get("kind") != "context" or "structure" not in self.artifact:
            raise ValueError("M3.json inesperado (kind/structure)")
        self.frozen = _load_frozen_module(_find_frozen_model_py(path))

    def predict(self, context, model_input: TypeFromExample, params=None):
        df = pd.DataFrame(model_input)[INPUT_COLUMNS].astype(float)
        p = self.frozen.predict_json(self.artifact["structure"], df)
        return np.asarray(expit(logit(p) + self.artifact.get("offset", 0.0)), dtype="float64")


set_model(M3Model())
