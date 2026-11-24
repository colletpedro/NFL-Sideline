"""Modelo MLflow (pyfunc, *models from code*) do B2 do xINT: sem pickle.

Reimplementação mínima de `research/qb_expected_interceptions/risk_model.predict` para o formato
`xint-ftn-reference-v1` (kind B2): a probabilidade é a taxa do grupo FTN `is_interception_worthy` (0 ou 1). O
original não é importável aqui (importa `common.py` com caminhos absolutos); `tests/test_registry.py` prova
igualdade exata contra ele.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow.models import set_model
from mlflow.pyfunc import PythonModel
from mlflow.types.type_hints import TypeFromExample

INPUT_COLUMNS = ["is_interception_worthy"]


class B2Model(PythonModel):
    def load_context(self, context):
        m = json.loads(Path(context.artifacts["model_json"]).read_text())
        expected = {"format": "xint-ftn-reference-v1", "kind": "B2", "target": "interception",
                    "risk_input": "is_interception_worthy"}
        for k, v in expected.items():
            if m.get(k) != v:
                raise ValueError(f"model.json inesperado: {k}={m.get(k)!r}, esperado {v!r}")
        groups = m.get("groups", {})
        if sorted(groups) != ["0", "1"]:
            raise ValueError("model.json deve ter exatamente os grupos '0' e '1'")
        self.prob = {k: float(groups[k]["probability"]) for k in groups}

    def predict(self, context, model_input: TypeFromExample, params=None):
        x = pd.DataFrame(model_input)["is_interception_worthy"]
        if not x.isin([0, 1, True, False]).all():
            raise ValueError("is_interception_worthy ausente ou não binário")
        return np.array([self.prob[str(int(v))] for v in x], dtype="float64")


set_model(B2Model())
