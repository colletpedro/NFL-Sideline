import pytest

import backtest as B
import card
from toy_models import FreqModel, LogitModel, synth

CLASSES = ("a", "b", "c")


def _res(min_improvement=0.0):
    data = synth()
    task = B.Task("toycard", "y3", "multiclass", "log_loss", ("log_loss", "brier"), CLASSES)
    return B.run_backtest(task, [LogitModel("y3", CLASSES)], [FreqModel("y3", CLASSES)],
                          B.walk_forward_seasons([2021, 2022], 2019), data, B.SelectionRule(min_improvement=min_improvement),
                          "synth-v1", 7)


def test_card_has_all_sections_from_mlflow():
    res = _res()
    md = card.render_card(res.parent_run_id, "Prever a classe do toy.", ["Dados sintéticos.", "Sem calibração."])
    for h in ("# Cartão do modelo `toycard`", "## Objetivo", "## Dados", "## Tarefa", "## Splits",
              "## Resultados (pooled)", "## Regra de seleção e resultado", "## Versões", "## Limitações"):
        assert h in md
    assert "Prever a classe do toy." in md and "- Sem calibração." in md
    assert "`synth-v1`" in md and "| s2021 |" in md and "| s2022 |" in md
    assert "`freq` | baseline" in md and "`logit` **(selecionado)** | candidate" in md
    assert f"{res.pooled['logit']['log_loss']:.5f}" in md and f"{res.pooled['freq']['brier']:.5f}" in md
    assert "Bate os baselines: sim" in md and res.config_sha256 in md and "git_commit" in md
    assert card.render_card(res.parent_run_id, "Prever a classe do toy.", ["Dados sintéticos.", "Sem calibração."]) == md


def test_card_when_rule_not_met():
    res = _res(min_improvement=10.0)
    md = card.render_card(res.parent_run_id, "x", "única limitação")
    assert "Modelo selecionado: `none`" in md and "Bate os baselines: não" in md and "(selecionado)" not in md
    assert "- única limitação" in md


def test_card_requires_parent():
    res = _res()
    from mlflow import MlflowClient
    child = MlflowClient().search_runs(
        [MlflowClient().get_run(res.parent_run_id).info.experiment_id],
        f"tags.mlflow.parentRunId = '{res.parent_run_id}'")[0]
    with pytest.raises(ValueError):
        card.render_card(child.info.run_id, "x", [])
