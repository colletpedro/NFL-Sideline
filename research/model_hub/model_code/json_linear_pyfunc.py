"""Modelo MLflow (pyfunc, *models from code*) genérico: modelo linear com ligação logística/softmax, sem pickle.

Lê `params.json` (artefato `params_json`) e confere o sha256 dele contra `params.sha256` (artefato `params_sha256`)
no carregamento. Formato de `params.json`:
  {"format": "hub-json-linear-v1", "kind": "binary"|"multiclass", "features": [...], "classes": [...],
   "intercept": [k] , "coef": [[d] * k], "mean": [d]?, "scale": [d]?}
Binário: k = 1, devolve vetor n com P(classe 1). Multiclasse: devolve matriz n×k na ordem de `classes`.
Autocontido de propósito (o arquivo é copiado para dentro do modelo registrado).
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow.models import set_model
from mlflow.pyfunc import PythonModel
from mlflow.types.type_hints import TypeFromExample

FORMAT = "hub-json-linear-v1"


def linear_predict(params: dict, X: np.ndarray) -> np.ndarray:
    """Previsão do formato acima (usada também pelos testes para comparar com o modelo original)."""
    X = np.asarray(X, dtype="float64")
    if "mean" in params:
        X = (X - np.asarray(params["mean"])) / np.asarray(params["scale"])
    z = X @ np.asarray(params["coef"], dtype="float64").T + np.asarray(params["intercept"], dtype="float64")
    if params["kind"] == "binary":
        return 1.0 / (1.0 + np.exp(-z[:, 0]))
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


class JsonLinearModel(PythonModel):
    def load_context(self, context):
        path = Path(context.artifacts["params_json"])
        expected = Path(context.artifacts["params_sha256"]).read_text().strip()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"params.json adulterado: sha256 {actual} difere do registrado {expected}")
        params = json.loads(path.read_text())
        if params.get("format") != FORMAT or params.get("kind") not in ("binary", "multiclass"):
            raise ValueError(f"params.json inesperado (format={params.get('format')!r}, kind={params.get('kind')!r})")
        self.params = params

    def predict(self, context, model_input: TypeFromExample, params=None):
        df = pd.DataFrame(model_input)
        return linear_predict(self.params, df[self.params["features"]].to_numpy(dtype="float64"))


set_model(JsonLinearModel())
