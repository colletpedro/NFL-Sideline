import hubpaths


def test_hub_home_env(tmp_path, monkeypatch):
    monkeypatch.setenv("NFL_HUB_HOME", str(tmp_path / "x"))
    assert hubpaths.hub_home() == tmp_path / "x"


def test_hub_home_default_under_main_checkout(monkeypatch):
    monkeypatch.delenv("NFL_HUB_HOME")
    home = hubpaths.hub_home()
    assert home.parts[-3:] == ("editorial", "local-artifacts", "model-hub")
    assert ".claude" not in home.parts
