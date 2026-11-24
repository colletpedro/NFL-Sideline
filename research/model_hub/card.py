"""Cartão de modelo em Markdown, gerado só a partir do MLflow (pai do backtest, filhas e artefatos)."""
from __future__ import annotations

import json
from pathlib import Path

from mlflow import MlflowClient

import metrics as M


def _fmt(v) -> str:
    return "—" if v is None else f"{v:.5f}"


def _config(client: MlflowClient, run_id: str) -> dict:
    return json.loads(Path(client.download_artifacts(run_id, "config.json")).read_text())


def render_card(parent_run_id: str, purpose: str, limitations, extra_sections: str = "") -> str:
    """Markdown com objetivo, dados, tarefa, splits, tabela modelos × métricas (pooled), regra e selecionado,
    versões e limitações. `limitations`: texto ou lista de textos. Modelos de papel "reference" aparecem na tabela
    marcados como fora da regra; métricas extras da configuração viram colunas. `extra_sections`: Markdown
    acrescentado antes das limitações (p. ex. tabela de calibração)."""
    client = MlflowClient()
    run = client.get_run(parent_run_id)
    t = run.data.tags
    if t.get("role") != "parent":
        raise ValueError("render_card exige o pai de um backtest")
    cfg = _config(client, parent_run_id)
    task = cfg["task"]
    rule = cfg["selection_rule"]
    models = {m["name"]: m for m in cfg["models"]}
    pooled: dict = {}
    for k, v in run.data.metrics.items():
        name, metric = k.split(".", 1)
        pooled.setdefault(name, {})[metric] = v
    children = client.search_runs([run.info.experiment_id], filter_string=f"tags.mlflow.parentRunId = '{parent_run_id}'",
                                  max_results=5000)
    n_children = len(children)

    L = [f"# Cartão do modelo `{task['key']}`", ""]
    L += ["## Objetivo", "", purpose.strip(), ""]
    L += ["## Dados", "", f"- data_id: `{t['data_id']}`", f"- Alvo: `{task['target']}`", ""]
    cls = f" (classes: {', '.join(map(str, task['classes']))})" if task["classes"] else ""
    L += ["## Tarefa", "", f"- Tipo: {task['kind']}{cls}", f"- Métrica primária: `{task['primary_metric']}` "
          f"({'menor' if M.direction(task['primary_metric']) == 'min' else 'maior'} é melhor)",
          f"- Métricas: {', '.join(f'`{m}`' for m in task['metrics'])}", ""]
    L += ["## Splits", "", "| split | treino até (season, week) | teste |", "|---|---|---|"]
    for s in cfg["splits"]:
        test = f"{s['test']} (temporadas)" if s["test_kind"] == "seasons" else \
            f"temporada {s['test'][0]}, semanas {s['test'][1]}–{s['test'][2]}"
        L.append(f"| {s['name']} | {tuple(s['train_until'])}, desde {s['first_train_season']} | {test} |")
    L += ["", f"Execuções filhas registradas: {n_children}. Métricas agregadas são *pooled*: previsões de todos os "
          "splits concatenadas e a métrica calculada uma vez.", ""]
    metrics_cols = list(task["metrics"]) + list(cfg.get("extras", {}).get("metrics", []))
    L += ["## Resultados (pooled)", "", "| modelo | papel | n | " + " | ".join(metrics_cols) + " |",
          "|---|---|---|" + "---|" * len(metrics_cols)]
    rank = {"baseline": 0, "reference": 1, "candidate": 2}
    order = sorted(models.values(), key=lambda m: (rank.get(m["role"], 3), m["name"]))
    for m in order:
        row = pooled.get(m["name"], {})
        mark = " **(selecionado)**" if m["name"] == t.get("selected_model") else ""
        role = "reference (fora da regra)" if m["role"] == "reference" else m["role"]
        L.append(f"| `{m['name']}`{mark} | {role} | {int(row.get('n', 0))} | "
                 + " | ".join(_fmt(row.get(c)) for c in metrics_cols) + " |")
    L += ["", "## Regra de seleção e resultado", "", f"- Regra (fixada antes do backtest): {rule['text']}.",
          f"- Modelo selecionado: `{t.get('selected_model', 'none')}`",
          f"- Bate os baselines: {'sim' if t.get('beats_baselines') == 'true' else 'não'}", ""]
    L += ["## Versões", "", f"- git_commit: `{t['git_commit']}` (git_dirty: {t['git_dirty']})",
          f"- harness_version: `{t['harness_version']}`", f"- model_code_sha256: `{t['model_code_sha256']}`",
          f"- config_sha256: `{t['config_sha256']}`", f"- seed: {t['seed']}", f"- Execução pai MLflow: `{parent_run_id}`", ""]
    if extra_sections.strip():
        L += [extra_sections.strip(), ""]
    lims = [limitations] if isinstance(limitations, str) else list(limitations)
    L += ["## Limitações", ""] + [f"- {x.strip()}" for x in lims] + [""]
    return "\n".join(L)
