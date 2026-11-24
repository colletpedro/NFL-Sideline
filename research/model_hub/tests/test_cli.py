import json

import cli
from fixtures_data import FakeLoader, synthetic_league


def test_status_empty(tmp_path, capsys):
    assert cli.main(["status", "--home", str(tmp_path)]) == 0
    assert "nenhuma" in capsys.readouterr().out


def test_errors_go_to_stderr_exit_2(tmp_path, capsys):
    assert cli.main(["build", "--home", str(tmp_path)]) == 2
    out = capsys.readouterr()
    assert "erro:" in out.err and out.out == ""


def test_acquire_build_status_flow(tmp_path, capsys, monkeypatch):
    import acquire
    league = synthetic_league([2023, 2024])
    monkeypatch.setattr(acquire, "nflreadpy_loader", FakeLoader(league))
    assert cli.main(["acquire", "--season", "2023", "--season", "2024", "--home", str(tmp_path)]) == 0
    assert cli.main(["build", "--allow-partial", "--home", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    bid = [l for l in out.splitlines() if l.startswith("build_id")][0].split()[1]
    assert cli.main(["status", "--home", str(tmp_path)]) == 0
    status = capsys.readouterr().out
    assert bid in status and "2024: pbp" in status and "semanas 1..4" in status


def test_commands_are_extensible(tmp_path):
    @cli.register_command("ping")
    def add_ping(sub):
        sub.add_parser("ping").set_defaults(func=lambda a: print("pong"))
    try:
        assert cli.main(["ping"]) == 0
    finally:
        cli.COMMANDS.pop("ping")


def test_migrate_command_and_allow_shrink(tmp_path, capsys, monkeypatch):
    import acquire
    from test_acquire import legacy_home
    league = synthetic_league([2023, 2024])
    old_id, _ = legacy_home(tmp_path / "h", league, [2023])
    assert cli.main(["migrate", "--home", str(tmp_path / "h")]) == 0
    out = capsys.readouterr().out
    assert f"manifesto {old_id} ->" in out and "arquivos 2" in out
    assert cli.main(["migrate", "--home", str(tmp_path / "h")]) == 0 and "manifesto" not in capsys.readouterr().out
    shrunk = {2024: {"pbp": league[2024]["pbp"].head(10), "schedules": league[2024]["schedules"]}}
    home = str(tmp_path / "s")
    monkeypatch.setattr(acquire, "nflreadpy_loader", FakeLoader(league))
    assert cli.main(["acquire", "--season", "2024", "--home", home]) == 0
    monkeypatch.setattr(acquire, "nflreadpy_loader", FakeLoader(shrunk))
    assert cli.main(["acquire", "--season", "2024", "--refresh", "--home", home]) == 2
    assert "allow-shrink" in capsys.readouterr().err
    assert cli.main(["acquire", "--season", "2024", "--refresh", "--home", home, "--allow-shrink"]) == 0
