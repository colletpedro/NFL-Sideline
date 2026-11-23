"""Auxiliar de testes: `import --rebuild` de verdade (via `importer_base.execute`) sobre um home sintético."""
from pathlib import Path

from mlflow import MlflowClient

import importer_base as base
import tracking


def real_rebuild(home, exp_key: str, old_parent_id: str) -> str:
    """Substitui o pai `old_parent_id` por um pai novo com as mesmas tags, pelo mesmo caminho de `--rebuild`
    dos importadores (nova importação primeiro, antiga apagada depois). Devolve o run_id do pai novo."""
    client = MlflowClient()
    exp_id = tracking.ensure_experiment(exp_key, home)
    tags = client.get_run(old_parent_id).data.tags
    ctx = {"freeze_sha": tags["source_freeze_sha256"]}

    class Imp(base.BaseImporter):
        module_file = Path(__file__)

        def tags(self, role, extra=None):
            return {**self.base_tags(tags["dataset_sha256"], tags["design_sha256"], tags["seed"], role),
                    **(extra or {})}

        def run_all(self):
            return self.new_run("parent", "parent", Path(__file__), base.Bag(), {})

    res = base.execute(client, exp_id, Path(home), ctx["freeze_sha"], {}, True, exp_key, base.ImporterError,
                       lambda: Imp(Path(tags["source_store"]), client, exp_id, ctx, Path(home)), Path(__file__))
    assert res["created"] is True
    return res["parent_run_id"]
