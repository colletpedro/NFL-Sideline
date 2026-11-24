import json
import os
from datetime import date

import polars as pl
import pytest

import acquire as acq
from fixtures_data import FakeLoader, synthetic_league

TODAY = date(2024, 11, 24)  # temporada corrente = 2024


def test_current_season():
    assert acq.current_season(date(2026, 11, 24)) == 2026
    assert acq.current_season(date(2027, 1, 15)) == 2026
    assert acq.current_season(date(2027, 2, 28)) == 2026
    assert acq.current_season(date(2027, 3, 1)) == 2027
    assert acq.default_seasons(date(2026, 11, 24)) == list(range(2011, 2027))


@pytest.fixture
def league():
    return synthetic_league([2022, 2023, 2024], future_weeks={2024: 1})


def raw_files(home):
    return sorted(str(p.relative_to(home)) for p in (home / "raw").rglob("*.parquet"))


def test_acquire_layout_and_manifest(tmp_path, league):
    loader = FakeLoader(league)
    aid = acq.acquire([2022, 2023, 2024], tmp_path, loader=loader, today=TODAY)
    man = json.loads((tmp_path / "acquisitions" / f"{aid}.json").read_text())
    assert man["format"] == 2 and man["acquisition_id"] == aid
    assert json.loads((tmp_path / "acquisitions/current.json").read_text())["acquisition_id"] == aid
    for s in (2022, 2023, 2024):
        for kind in acq.KINDS:
            e = man["seasons"][str(s)][kind]
            assert e["path"] == f"raw/{kind}/season={s}/{e['sha256']}.parquet"  # H-D10: endereço = sha256
            assert e["sha256"] == acq.sha256_file(tmp_path / e["path"])
    e = man["seasons"]["2024"]["pbp"]
    assert e["rows"] == league[2024]["pbp"].height and e["weeks_with_pbp"] == [1, 2, 3]
    assert e["max_game_date"] == league[2024]["pbp"]["game_date"].max()
    assert "game_id" in e["columns"] and e["fetched_at_utc"].endswith("Z")
    assert len(raw_files(tmp_path)) == 6
    assert not list(tmp_path.rglob("*.tmp-*")) and not list((tmp_path / "raw").glob(".staging-*"))


def test_past_reused_current_refreshed(tmp_path, league):
    acq.acquire([2023, 2024], tmp_path, loader=FakeLoader(league), today=TODAY)
    second = FakeLoader(league)
    aid2 = acq.acquire([2023, 2024], tmp_path, loader=second, today=TODAY)
    assert sorted(second.calls) == [("pbp", 2024), ("schedules", 2024)]
    man = json.loads((tmp_path / "acquisitions" / f"{aid2}.json").read_text())
    assert man["seasons"]["2023"]["pbp"]["fetched_at_utc"].endswith("Z")  # data original preservada
    assert len(raw_files(tmp_path)) == 4  # bytes idênticos: nenhum arquivo novo
    third = FakeLoader(league)
    acq.acquire([2023, 2024], tmp_path, loader=third, today=TODAY, refresh_current=False)
    assert third.calls == []
    fourth = FakeLoader(league)
    acq.acquire([2023], tmp_path, loader=fourth, today=TODAY, refresh=True)
    assert len(fourth.calls) == 2
    # reuso também depois de uma aquisição com outro conjunto de temporadas
    fifth = FakeLoader(league)
    acq.acquire([2022, 2023], tmp_path, loader=fifth, today=TODAY)
    assert sorted(fifth.calls) == [("pbp", 2022), ("schedules", 2022)]


def test_same_files_same_id(tmp_path, league):
    a = acq.acquire([2023], tmp_path / "a", loader=FakeLoader(league), today=TODAY)
    b = acq.acquire([2023], tmp_path / "b", loader=FakeLoader(league), today=TODAY)
    assert a == b
    other = synthetic_league([2023], seed=2)
    assert acq.acquire([2023], tmp_path / "c", loader=FakeLoader(other), today=TODAY) != a


def test_current_pbp_not_published_is_tolerated(tmp_path, league):
    loader = FakeLoader(league, fail={("pbp", 2024): acq.SourceNotPublished("404")})
    aid = acq.acquire([2024], tmp_path, loader=loader, today=TODAY)
    man = acq.resolve_acquisition(aid, tmp_path)
    assert man["seasons"]["2024"]["pbp"] is None and man["seasons"]["2024"]["schedules"]["rows"] > 0
    # existente é mantido quando o rebaixamento falha
    acq.acquire([2024], tmp_path, loader=FakeLoader(league), today=TODAY)
    aid3 = acq.acquire([2024], tmp_path, loader=loader, today=TODAY)
    assert acq.resolve_acquisition(aid3, tmp_path)["seasons"]["2024"]["pbp"]["rows"] > 0


def test_empty_current_pbp_tolerated_but_past_fatal(tmp_path, league):
    empty = {**league, 2024: {"pbp": league[2024]["pbp"].clear(), "schedules": league[2024]["schedules"]}}
    acq.acquire([2024], tmp_path / "a", loader=FakeLoader(empty), today=TODAY)
    empty[2023] = {"pbp": league[2023]["pbp"].clear(), "schedules": league[2023]["schedules"]}
    with pytest.raises(acq.AcquireError, match="pbp 2023"):
        acq.acquire([2023], tmp_path / "b", loader=FakeLoader(empty), today=TODAY)


def test_current_schedules_not_published_is_tolerated_b4(tmp_path, league):
    """B4: março-maio, antes da publicação do calendário, schedules 404/vazio da temporada corrente não é fatal."""
    for failure in (acq.SourceNotPublished("404"), None):
        home = tmp_path / ("a" if failure else "b")
        if failure:
            loader = FakeLoader(league, fail={("schedules", 2024): failure, ("pbp", 2024): failure})
        else:
            empty = {**league, 2024: {"pbp": league[2024]["pbp"].clear(), "schedules": league[2024]["schedules"].clear()}}
            loader = FakeLoader(empty)
        aid = acq.acquire([2023, 2024], home, loader=loader, today=TODAY)
        man = acq.resolve_acquisition(aid, home)
        assert man["seasons"]["2024"] == {"pbp": None, "schedules": None}
        assert man["seasons"]["2023"]["schedules"]["rows"] > 0
    # existente é mantido
    acq.acquire([2024], tmp_path / "c", loader=FakeLoader(league), today=TODAY)
    aid = acq.acquire([2024], tmp_path / "c", loader=FakeLoader(league, fail={("schedules", 2024): acq.SourceNotPublished("404")}),
                      today=TODAY)
    assert acq.resolve_acquisition(aid, tmp_path / "c")["seasons"]["2024"]["schedules"]["rows"] > 0
    # temporada passada continua fatal (404 e vazio)
    with pytest.raises(acq.AcquireError, match="schedules 2023"):
        acq.acquire([2023], tmp_path / "d", loader=FakeLoader(league, fail={("schedules", 2023): acq.SourceNotPublished("404")}),
                    today=TODAY)
    empty = {**league, 2023: {"pbp": league[2023]["pbp"], "schedules": league[2023]["schedules"].clear()}}
    with pytest.raises(acq.AcquireError, match="schedules 2023"):
        acq.acquire([2023], tmp_path / "e", loader=FakeLoader(empty), today=TODAY)


def test_other_errors_are_fatal(tmp_path, league):
    for exc in (ConnectionError("500"), ValueError("esquema")):
        loader = FakeLoader(league, fail={("pbp", 2024): exc})
        with pytest.raises(acq.AcquireError, match="falha ao baixar"):
            acq.acquire([2024], tmp_path / type(exc).__name__, loader=loader, today=TODAY)
    loader = FakeLoader(league, fail={("schedules", 2024): ConnectionError("500")})
    with pytest.raises(acq.AcquireError, match="falha ao baixar"):
        acq.acquire([2024], tmp_path / "s", loader=loader, today=TODAY)


def test_missing_required_column_is_clear_error(tmp_path, league):
    bad = {2023: {"pbp": league[2023]["pbp"].drop("epa"), "schedules": league[2023]["schedules"]}}
    with pytest.raises(acq.AcquireError, match="pbp 2023.*epa"):
        acq.acquire([2023], tmp_path, loader=FakeLoader(bad), today=TODAY)
    assert raw_files(tmp_path) == []
    bad = {2023: {"pbp": league[2023]["pbp"].drop("posteam_score_post"), "schedules": league[2023]["schedules"]}}
    with pytest.raises(acq.AcquireError, match="posteam_score_post"):
        acq.acquire([2023], tmp_path, loader=FakeLoader(bad), today=TODAY)


def snapshot(home):
    """Estado observável: arquivos de raw/acquisitions com sha."""
    return {str(p.relative_to(home)): acq.sha256_file(p) for p in sorted(home.rglob("*")) if p.is_file()}


def test_failure_midway_leaves_everything_untouched(tmp_path, league):
    """M3: falha depois de baixar parte das temporadas não deixa arquivo definitivo nem manifesto novo."""
    acq.acquire([2023, 2024], tmp_path, loader=FakeLoader(league), today=TODAY)
    before = snapshot(tmp_path)
    changed = {**league, 2024: {"pbp": league[2024]["pbp"].with_columns(epa=pl.col("epa") + 1),
                                "schedules": league[2024]["schedules"]}}
    loader = FakeLoader(changed, fail={("schedules", 2024): ConnectionError("boom")})
    with pytest.raises(acq.AcquireError, match="schedules 2024"):
        acq.acquire([2023, 2024], tmp_path, loader=loader, today=TODAY, refresh=True)
    assert ("pbp", 2024) in loader.calls  # o pbp novo chegou a ser baixado
    assert snapshot(tmp_path) == before and not list((tmp_path / "raw").glob(".staging-*"))
    # falha de escrita do parquet: idem
    def boom(self, p, **k):
        open(p, "wb").write(b"parcial")
        raise OSError("disco cheio")
    import pytest as _p
    mp = _p.MonkeyPatch()
    mp.setattr(pl.DataFrame, "write_parquet", boom)
    try:
        with pytest.raises(OSError):
            acq.acquire([2023, 2024], tmp_path, loader=FakeLoader(changed), today=TODAY, refresh=True)
    finally:
        mp.undo()
    assert snapshot(tmp_path) == before and not list(tmp_path.rglob("*.tmp-*"))


def test_old_manifest_stays_reconstructable_after_refresh_m2(tmp_path, league):
    """M2: refresh que muda os dados cria arquivos novos; os do manifesto antigo continuam lá e batem o sha."""
    aid1 = acq.acquire([2023, 2024], tmp_path, loader=FakeLoader(league), today=TODAY)
    changed = {**league, 2024: {"pbp": league[2024]["pbp"].with_columns(epa=pl.col("epa") + 1),
                                "schedules": league[2024]["schedules"]}}
    aid2 = acq.acquire([2023, 2024], tmp_path, loader=FakeLoader(changed), today=TODAY)
    assert aid1 != aid2
    for aid in (aid1, aid2):
        man = acq.resolve_acquisition(aid, tmp_path)
        for entries in man["seasons"].values():
            for e in entries.values():
                assert acq.sha256_file(tmp_path / e["path"]) == e["sha256"]
    old = acq.resolve_acquisition(aid1, tmp_path)["seasons"]["2024"]["pbp"]
    new = acq.resolve_acquisition(aid2, tmp_path)["seasons"]["2024"]["pbp"]
    assert old["path"] != new["path"] and old["sha256"] != new["sha256"]
    assert acq.resolve_acquisition(None, tmp_path)["acquisition_id"] == aid2


def test_orphan_temporaries_are_cleaned(tmp_path, league):
    (tmp_path / "raw/.staging-999999999-ab").mkdir(parents=True)
    (tmp_path / "raw/.staging-999999999-ab/pbp-2023.parquet").write_bytes(b"x")
    (tmp_path / "raw/pbp/season=2023").mkdir(parents=True)
    (tmp_path / "raw/pbp/season=2023/.abc.parquet.tmp-999999999").write_bytes(b"x")
    (tmp_path / "acquisitions").mkdir()
    (tmp_path / "acquisitions/.current.json.tmp-999999999").write_bytes(b"x")
    live = tmp_path / f"raw/.staging-{os.getpid()}-live"
    live.mkdir()  # processo vivo (este): não pode ser removido
    acq.acquire([2023], tmp_path, loader=FakeLoader(league), today=TODAY)
    assert not list(tmp_path.rglob("*999999999*")) and live.exists()


def test_shrink_fails_unless_allowed_b5(tmp_path, league):
    acq.acquire([2024], tmp_path, loader=FakeLoader(league), today=TODAY)
    cut = int(league[2024]["pbp"].height * 0.05)
    shrunk = {**league, 2024: {"pbp": league[2024]["pbp"].head(league[2024]["pbp"].height - cut),
                               "schedules": league[2024]["schedules"]}}
    before = snapshot(tmp_path)
    with pytest.raises(acq.AcquireError, match="allow-shrink"):
        acq.acquire([2024], tmp_path, loader=FakeLoader(shrunk), today=TODAY)
    assert snapshot(tmp_path) == before
    aid = acq.acquire([2024], tmp_path, loader=FakeLoader(shrunk), today=TODAY, allow_shrink=True)
    assert acq.resolve_acquisition(aid, tmp_path)["seasons"]["2024"]["pbp"]["rows"] == shrunk[2024]["pbp"].height
    # queda de <= 1% passa (e crescer sempre passa)
    tiny = {**league, 2024: {"pbp": league[2024]["pbp"].head(league[2024]["pbp"].height - 1), "schedules": league[2024]["schedules"]}}
    acq.acquire([2024], tmp_path / "t", loader=FakeLoader(league), today=TODAY)
    acq.acquire([2024], tmp_path / "t", loader=FakeLoader(tiny), today=TODAY)


def legacy_home(home, league, seasons, today=TODAY):
    """Reproduz o layout antigo: raw/<tipo>/season=Y/<tipo>.parquet e manifesto ``format`` 1 (id antigo)."""
    aid = acq.acquire(seasons, home, loader=FakeLoader(league), today=today)
    man = acq.resolve_acquisition(aid, home)
    old = json.loads(json.dumps(man))
    for season, entries in old["seasons"].items():
        for kind, e in entries.items():
            new_path = home / e["path"]
            e["path"] = f"raw/{kind}/season={season}/{kind}.parquet"
            new_path.rename(home / e["path"])
    old["format"] = 1
    old.pop("acquisition_id")
    old.pop("migrated_from", None)
    old_id = acq.compute_acquisition_id(old)
    old["acquisition_id"] = old_id
    for p in (home / "acquisitions").glob("*.json"):
        p.unlink()
    (home / "acquisitions" / f"{old_id}.json").write_text(json.dumps(old, indent=2, sort_keys=True))
    (home / "acquisitions" / "current.json").write_text(json.dumps({"acquisition_id": old_id}))
    return old_id, old


def test_migrate_legacy_layout_is_idempotent(tmp_path, league):
    home = tmp_path / "h"
    old_id, old = legacy_home(home, league, [2023, 2024])
    with pytest.raises(acq.AcquireError, match="migrate"):
        acq.resolve_acquisition(old_id, home)
    rep = acq.migrate_legacy(home)
    assert rep["files"] == 4 and list(rep["manifests"]) == [old_id] and rep["unrecoverable"] == []
    new_id = rep["manifests"][old_id]
    assert new_id != old_id  # o id muda: path/format fazem parte do conteúdo
    man = acq.resolve_acquisition(None, home)
    assert man["acquisition_id"] == new_id and man["migrated_from"] == old_id and man["format"] == 2
    assert acq.resolve_acquisition(old_id[:10], home)["acquisition_id"] == new_id  # id antigo ainda resolve
    for entries in man["seasons"].values():
        for e in entries.values():
            assert e["path"] == f"raw/{'pbp' if 'pbp' in e['path'] else 'schedules'}/season=" + e["path"].split("season=")[1]
            assert acq.sha256_file(home / e["path"]) == e["sha256"]
    assert not list((home / "raw").rglob("pbp.parquet")) and not list((home / "raw").rglob("schedules.parquet"))
    assert [p.stem for p in (home / "acquisitions").glob("*.json") if p.stem != "current"] == [new_id]
    before = snapshot(home)
    assert acq.migrate_legacy(home) == {"files": 0, "manifests": {}, "unrecoverable": []}
    assert snapshot(home) == before
    # um acquire seguinte reaproveita as temporadas passadas migradas
    loader = FakeLoader(league)
    acq.acquire([2023, 2024], home, loader=loader, today=TODAY)
    assert sorted(loader.calls) == [("pbp", 2024), ("schedules", 2024)]


def test_migrate_marks_unrecoverable_when_file_changed(tmp_path, league):
    home = tmp_path / "h"
    old_id, old = legacy_home(home, league, [2023])
    (home / old["seasons"]["2023"]["pbp"]["path"]).write_bytes(b"outro conteudo")
    rep = acq.migrate_legacy(home)
    assert rep["unrecoverable"] == [old_id] and rep["manifests"] == {}
    assert (home / "acquisitions" / f"{old_id}.json").exists()


def test_subset_acquire_inherits_other_seasons_m1(tmp_path, league):
    """M-1: `acquire --season N` não pode fazer o current.json apontar para um manifesto só com N."""
    aid1 = acq.acquire([2022, 2023, 2024], tmp_path, loader=FakeLoader(league), today=TODAY)
    m1 = acq.resolve_acquisition(aid1, tmp_path)
    loader = FakeLoader(league)
    aid2 = acq.acquire([2024], tmp_path, loader=loader, today=TODAY)
    assert sorted(loader.calls) == [("pbp", 2024), ("schedules", 2024)]
    m2 = acq.resolve_acquisition(None, tmp_path)
    assert m2["acquisition_id"] == aid2 and sorted(m2["seasons"]) == ["2022", "2023", "2024"]
    for s in ("2022", "2023", "2024"):
        assert m2["seasons"][s] == m1["seasons"][s]  # mesmos arquivos (sha256), mesmas datas
    assert aid2 == aid1  # nada mudou: mesmo conteúdo, mesmo id


def test_subset_acquire_without_current_has_only_requested(tmp_path, league):
    aid = acq.acquire([2024], tmp_path, loader=FakeLoader(league), today=TODAY)
    assert sorted(acq.resolve_acquisition(aid, tmp_path)["seasons"]) == ["2024"]


def test_subset_acquire_drops_inherited_entry_with_tampered_file(tmp_path, league):
    acq.acquire([2023, 2024], tmp_path, loader=FakeLoader(league), today=TODAY)
    man = acq.resolve_acquisition(None, tmp_path)
    (tmp_path / man["seasons"]["2023"]["pbp"]["path"]).write_bytes(b"adulterado")
    acq.acquire([2024], tmp_path, loader=FakeLoader(league), today=TODAY)
    kept = acq.resolve_acquisition(None, tmp_path)["seasons"]["2023"]
    assert "pbp" not in kept and kept["schedules"]  # arquivo adulterado não é herdado
