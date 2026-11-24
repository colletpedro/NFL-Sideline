import json
from datetime import date

import numpy as np
import polars as pl
import pytest

import acquire as acq
import features as ft
from fixtures_data import FakeLoader, pbp_frame, synthetic_league, with_historic_codes

TODAY = date(2024, 11, 24)


def targets(rows):
    d = pbp_frame(rows).with_columns(
        pl.when(pl.col("qtr") <= 2).then(1).when(pl.col("qtr") <= 4).then(2).otherwise(3).cast(pl.Int8).alias("half"))
    out = ft.add_next_score(d)
    return list(zip(out["next_score_type"], out["next_score_points"]))


# ------------------------------------------------------------------ alvo next_score
def test_own_td_includes_current_play():
    r = targets([{}, {}, {"touchdown": 1.0, "td_team": "AAA"}])
    assert r == [("TD", 7)] * 3


def test_defensive_td_is_opponent_td():
    """pick-six: posteam AAA, td_team BBB."""
    r = targets([{}, {"touchdown": 1.0, "td_team": "BBB"}])
    assert r == [("OPP_TD", -7)] * 2


def test_safety_scores_for_defteam():
    """Caso comum: o safety é do defteam. Vale com a variação do placar do posteam = 0 e, como fallback, quando a
    variação não é observável (nulos)."""
    for pre, post in ((0.0, 0.0), (None, None), (7.0, None)):
        r = targets([{}, {"safety": 1.0, "posteam_score": pre, "posteam_score_post": post},
                     {"posteam": "BBB", "defteam": "AAA"}])
        assert r[0] == r[1] == ("OPP_SAFETY", -2), (pre, post)
        # a jogada seguinte (posse de BBB, depois do safety) já não vê o evento passado
        assert r[2] == ("NO_SCORE", 0)


def test_safety_on_punt_return_scores_for_posteam_m1():
    """M1: punt cujo retornador recua para o próprio end zone: o placar do chutador (posteam) sobe 2."""
    r = targets([{}, {"play_type": "punt", "safety": 1.0, "posteam_score": 7.0, "posteam_score_post": 9.0,
                      "defteam_score": 7.0, "defteam_score_post": 7.0},
                 {"posteam": "BBB", "defteam": "AAA"}])
    assert r[0] == r[1] == ("SAFETY", 2) and r[2] == ("NO_SCORE", 0)
    # e na ótica do outro time o mesmo evento é do adversário
    r = targets([{"posteam": "BBB", "defteam": "AAA"},
                 {"play_type": "punt", "safety": 1.0, "posteam_score": 0.0, "posteam_score_post": 2.0}])
    assert r[0] == ("OPP_SAFETY", -2)


def test_safety_from_bbb_perspective():
    r = targets([{"posteam": "BBB", "defteam": "AAA"}, {"posteam": "AAA", "defteam": "BBB", "safety": 1.0}])
    assert r[0] == ("SAFETY", 2)


def test_missed_fg_is_not_event_and_possession_change():
    r = targets([{}, {"play_type": "field_goal", "field_goal_result": "missed"},
                 {"posteam": "BBB", "defteam": "AAA"}, {"posteam": "BBB", "defteam": "AAA", "touchdown": 1.0,
                                                        "td_team": "BBB"}])
    assert r == [("OPP_TD", -7)] * 2 + [("TD", 7)] * 2


def test_made_fg_and_blocked_fg_returned():
    r = targets([{}, {"play_type": "field_goal", "field_goal_result": "made"}])
    assert r == [("FG", 3)] * 2
    r = targets([{}, {"play_type": "field_goal", "field_goal_result": "blocked"}])
    assert r == [("NO_SCORE", 0)] * 2


def test_pat_and_two_point_are_not_events():
    r = targets([{"play_type": "extra_point"}, {"two_point_attempt": 1.0}])
    assert r == [("NO_SCORE", 0)] * 2


def test_end_of_half_and_overtime():
    r = targets([{"qtr": 1.0}, {"qtr": 2.0},
                 {"qtr": 3.0, "touchdown": 1.0, "td_team": "AAA"},
                 {"qtr": 4.0}, {"qtr": 5.0}, {"qtr": 5.0, "field_goal_result": "made", "posteam": "BBB",
                                              "defteam": "AAA"}])
    assert r[:2] == [("NO_SCORE", 0)] * 2  # TD é da outra metade
    assert r[2] == ("TD", 7) and r[3] == ("NO_SCORE", 0)  # qtr 4 não vê a prorrogação
    assert r[4] == ("OPP_FG", -3) and r[5] == ("FG", 3)


def test_games_are_independent_and_null_posteam():
    r = targets([{"game_id": "g1"}, {"game_id": "g2", "touchdown": 1.0, "td_team": "AAA"},
                 {"game_id": "g2", "posteam": None, "defteam": None}])
    assert r[0] == ("NO_SCORE", 0) and r[1] == ("TD", 7) and r[2] == (None, None)


def test_touchdown_without_td_team_is_error():
    with pytest.raises(ft.FeatureError):
        targets([{"touchdown": 1.0}])


@pytest.mark.parametrize("over,expected", [
    ({}, True), ({"down": None}, False), ({"down": 5.0}, False), ({"posteam": None}, False),
    ({"yardline_100": None}, False), ({"play_type": None}, False), ({"play_type": "kickoff"}, False),
    ({"play_type": "extra_point"}, False), ({"two_point_attempt": 1.0}, False), ({"play_type": "punt"}, True),
])
def test_ep_eligible(over, expected):
    plays = ft.build_plays(pbp_frame([over]))
    assert plays["ep_eligible"].to_list() == [expected]


def test_plays_half_and_filters():
    p = ft.build_plays(pbp_frame([{"qtr": 2.0}, {"qtr": 3.0}, {"qtr": 5.0}, {"season_type": "PRE"}]))
    assert p["half"].to_list() == [1, 2, 3] and p["posteam_is_home"].to_list() == [True] * 3


# ------------------------------------------------------------------ games / team_game
def test_kickoff_utc_dst():
    sched = synthetic_league([2024], weeks=1)[2024]["schedules"].head(2).with_columns(
        pl.Series("gameday", ["2024-09-08", "2024-12-08"]))
    g = ft.build_games(sched)
    assert [k.strftime("%Y-%m-%d %H:%M") for k in g["kickoff_utc"]] == ["2024-09-08 17:00", "2024-12-08 18:00"]
    assert str(g["kickoff_utc"].dtype) == "Datetime(time_unit='us', time_zone='UTC')"
    assert g["completed"].to_list() == [True, True]


def test_team_game_definition():
    league = synthetic_league([2024], weeks=1)
    sched = league[2024]["schedules"].head(1)
    gid = sched["game_id"][0]
    home, away = sched["home_team"][0], sched["away_team"][0]
    rows = [{"game_id": gid, "home_team": home, "away_team": away, "posteam": home, "defteam": away, "epa": 1.0,
             "success": 1.0, "play_type": "pass"},
            {"game_id": gid, "home_team": home, "away_team": away, "posteam": home, "defteam": away, "epa": -1.0,
             "success": 0.0, "play_type": "run"},
            {"game_id": gid, "home_team": home, "away_team": away, "posteam": away, "defteam": home, "epa": 0.5,
             "success": 1.0, "play_type": "pass"},
            # fora da definição:
            {"game_id": gid, "home_team": home, "away_team": away, "posteam": home, "defteam": away, "epa": 9.0,
             "play_type": "no_play"},
            {"game_id": gid, "home_team": home, "away_team": away, "posteam": home, "defteam": away, "epa": None,
             "play_type": "run"},
            {"game_id": gid, "home_team": home, "away_team": away, "posteam": home, "defteam": away, "epa": 9.0,
             "play_type": "qb_kneel"}]
    plays = ft.build_plays(pbp_frame(rows))
    games = ft.build_games(sched)
    tg = ft.build_team_game(plays, games).sort("is_home", descending=True)
    h, a = tg.row(0, named=True), tg.row(1, named=True)
    assert h["team"] == home and h["opponent"] == away and h["is_home"]
    assert (h["off_plays"], h["off_epa_per_play"], h["off_success_rate"], h["off_pass_rate"]) == (2, 0.0, 0.5, 0.5)
    assert (h["def_plays"], h["def_epa_per_play"], h["def_success_rate"]) == (1, 0.5, 1.0)
    assert (a["off_plays"], a["off_epa_per_play"], a["off_pass_rate"]) == (1, 0.5, 1.0)
    assert a["def_epa_per_play"] == 0.0
    assert h["points_for"] == sched["home_score"][0] and h["points_against"] == sched["away_score"][0]


# ------------------------------------------------------------------ team_asof
@pytest.fixture
def league():
    return synthetic_league([2023, 2024], future_weeks={2024: 1})


def make_build(tmp_path, league, name="h"):
    home = tmp_path / name
    aid = acq.acquire(sorted(league), home, loader=FakeLoader(league), today=TODAY)
    return home, aid, ft.build(aid, home, allow_partial=True)


def test_build_layout_and_manifest(tmp_path, league):
    home, aid, bid = make_build(tmp_path, league)
    bdir = home / "features" / bid
    man = json.loads((bdir / "manifest.json").read_text())
    assert man["acquisition_id"] == aid and man["features_code_sha256"] == ft.code_sha256()
    assert bid == ft.compute_build_id(aid)
    for t in ft.TABLES:
        assert acq.sha256_file(bdir / f"{t}.parquet") == man["tables"][t]["sha256"]
        assert pl.read_parquet(bdir / f"{t}.parquet").height == man["tables"][t]["rows"]
    tabs = ft.load_tables(bid, home)
    assert tabs["games"].height == 12 * 0 + tabs["team_asof"].height // 2
    assert tabs["team_asof"].height == 2 * tabs["games"].height  # inclui jogos futuros
    assert tabs["games"]["completed"].sum() < tabs["games"].height
    assert not list((home / "features").glob(".*tmp*"))
    assert man["qa"] == {"games_qtr_out_of_order": 0, "partial": True}


def test_asof_values_strictly_prior(tmp_path, league):
    home, _, bid = make_build(tmp_path, league)
    t = ft.load_tables(bid, home)
    asof, tg = t["team_asof"], t["team_game"]
    first = asof.sort("kickoff_utc").row(0, named=True)
    assert first["games_prior_total"] == 0 and first["games_prior_season"] == 0
    assert first["season_off_epa"] is None and first["ewm4_off_epa"] is None  # nulo, nunca zero
    team = "T00"
    rows = asof.filter(pl.col("team") == team).sort("kickoff_utc")
    mine = tg.filter(pl.col("team") == team).sort("kickoff_utc")
    for i, r in enumerate(rows.iter_rows(named=True)):
        prior = mine.filter(pl.col("kickoff_utc") < r["kickoff_utc"])
        assert r["games_prior_total"] == prior.height
        same = prior.filter(pl.col("season") == r["season"])
        assert r["games_prior_season"] == same.height
        if same.height:
            assert r["season_off_epa"] == pytest.approx(same["off_epa_per_play"].mean())
        if prior.height:
            assert r["last3_def_epa"] == pytest.approx(prior.tail(3)["def_epa_per_play"].mean())
            ages = np.arange(prior.height - 1, -1, -1)
            w = 0.5 ** (ages / 4)
            assert r["ewm4_off_success"] == pytest.approx(np.sum(w * prior["off_success_rate"].to_numpy()) / w.sum())
    # virada de temporada: ewm atravessa, season_* reinicia
    first24 = rows.filter(pl.col("season") == 2024).row(0, named=True)
    assert first24["games_prior_season"] == 0 and first24["season_off_epa"] is None
    assert first24["games_prior_total"] > 0 and first24["ewm4_off_epa"] is not None
    # jogo futuro (sem PBP) também tem linha, com features do passado
    future = asof.filter(pl.col("week") == 4, pl.col("season") == 2024)
    assert future.height > 0 and future["games_prior_total"].min() > 0


def test_no_leakage_when_a_game_changes(tmp_path, league):
    home1, _, bid1 = make_build(tmp_path, league, "h1")
    sched = league[2024]["schedules"]
    x = sched.filter(pl.col("week") == 2).row(0, named=True)
    altered = {**league, 2024: {
        "pbp": league[2024]["pbp"].with_columns(
            pl.when(pl.col("game_id") == x["game_id"]).then(pl.col("epa") + 5).otherwise(pl.col("epa")).alias("epa"),
            pl.when(pl.col("game_id") == x["game_id"]).then(1.0 - pl.col("success")).otherwise(pl.col("success"))
            .alias("success")),
        "schedules": sched.with_columns(
            pl.when(pl.col("game_id") == x["game_id"]).then(pl.col("home_score") + 14)
            .otherwise(pl.col("home_score")).alias("home_score"))}}
    home2, _, bid2 = make_build(tmp_path, altered, "h2")
    a, b = ft.load_tables(bid1, home1)["team_asof"], ft.load_tables(bid2, home2)["team_asof"]
    assert bid1 != bid2 and a.height == b.height
    kx = a.filter(pl.col("game_id") == x["game_id"])["kickoff_utc"][0]
    key = ["game_id", "team"]
    j = a.join(b, on=key, suffix="_b")
    value_cols = [c for c in a.columns if c not in key]
    changed = pl.any_horizontal(*[
        ~pl.col(c).eq_missing(pl.col(f"{c}_b")) for c in value_cols])
    early = j.filter(pl.col("kickoff_utc") <= kx)
    assert early.height > 0 and early.filter(changed).height == 0
    assert j.filter(pl.col("kickoff_utc") > kx).filter(changed).height > 0


def test_build_reproducible_across_homes_and_reused(tmp_path, league):
    h1, a1, b1 = make_build(tmp_path, league, "h1")
    h2, a2, b2 = make_build(tmp_path, league, "h2")
    assert (a1, b1) == (a2, b2)
    m1 = json.loads((h1 / "features" / b1 / "manifest.json").read_text())
    for t in ft.TABLES:
        assert acq.sha256_file(h1 / "features" / b1 / f"{t}.parquet") == \
            acq.sha256_file(h2 / "features" / b2 / f"{t}.parquet") == m1["tables"][t]["sha256"]
    mtime = (h1 / "features" / b1 / "manifest.json").stat().st_mtime_ns
    assert ft.build(None, h1, allow_partial=True) == b1 and (h1 / "features" / b1 / "manifest.json").stat().st_mtime_ns == mtime


def test_corrupt_build_is_rebuilt(tmp_path, league):
    home, aid, bid = make_build(tmp_path, league)
    (home / "features" / bid / "games.parquet").write_bytes(b"lixo")
    with pytest.raises(ft.FeatureError):
        ft.load_tables(bid, home)
    assert ft.build(aid, home, allow_partial=True) == bid
    assert ft.load_tables(bid, home)["games"].height > 0


def test_sha_mismatch_is_error(tmp_path, league):
    home, aid, _ = make_build(tmp_path, league)
    path = home / acq.resolve_acquisition(aid, home)["seasons"]["2023"]["pbp"]["path"]
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(ft.FeatureError, match="sha256 divergente"):
        ft.build(aid, home, allow_partial=True)


def test_build_id_depends_on_acquisition(tmp_path, league):
    _, a1, b1 = make_build(tmp_path, league, "h1")
    other = synthetic_league([2023, 2024], seed=9)
    _, a2, b2 = make_build(tmp_path, other, "h2")
    assert a1 != a2 and b1 != b2


# ------------------------------------------------------------------ B1, B3
def test_two_point_attempts_excluded_from_team_game_b1():
    sched = synthetic_league([2024], weeks=1)[2024]["schedules"].head(1)
    gid, home, away = sched["game_id"][0], sched["home_team"][0], sched["away_team"][0]
    base = {"game_id": gid, "home_team": home, "away_team": away, "posteam": home, "defteam": away}
    rows = [{**base, "epa": 1.0, "success": 1.0, "play_type": "pass"},
            {**base, "epa": 8.0, "success": 1.0, "play_type": "pass", "two_point_attempt": 1.0},
            {**base, "epa": -9.0, "success": 0.0, "play_type": "run", "two_point_attempt": 1.0}]
    tg = ft.build_team_game(ft.build_plays(pbp_frame(rows)), ft.build_games(sched))
    h = tg.filter(pl.col("team") == home).row(0, named=True)
    assert (h["off_plays"], h["off_epa_per_play"], h["off_pass_rate"]) == (1, 1.0, 1.0)
    assert tg.filter(pl.col("team") == away).row(0, named=True)["def_plays"] == 1


def test_out_of_order_games_are_counted_b3():
    rows = [{"game_id": "g1", "qtr": q} for q in (1.0, 2.0, 1.0, 3.0)] + \
           [{"game_id": "g2", "qtr": q} for q in (1.0, 2.0, 3.0)] + \
           [{"game_id": "g3", "qtr": q} for q in (4.0, 3.0, 2.0)]
    plays = pbp_frame(rows).with_columns(pl.col("qtr").cast(pl.Int8))
    assert ft.count_out_of_order_games(plays) == 2
    # o rótulo de metade depende só do qtr da própria jogada, não da ordem
    built = ft.build_plays(pbp_frame(rows))
    assert built["half"].to_list() == [1, 1, 1, 2, 1, 1, 2, 2, 2, 1]


# ------------------------------------------------------------------ C1: siglas históricas
TEAMS = ["LV", "LAC", "LA", "T03", "T04", "T05"]
HISTORIC = {"LV": "OAK", "LAC": "SD", "LA": "STL"}  # atual -> histórica
CURRENT = {v: k for k, v in HISTORIC.items()}


@pytest.fixture
def renamed_league():
    base = synthetic_league([2018, 2019, 2020], team_names=TEAMS)
    return with_historic_codes(base, HISTORIC, through=2019)


def test_franchise_codes_are_normalized_everywhere_c1(tmp_path, renamed_league):
    # a premissa do defeito: schedules históricos, PBP atual
    sched19 = renamed_league[2019]["schedules"]
    assert {"OAK", "SD", "STL"} <= set(sched19["home_team"]) | set(sched19["away_team"])
    assert not {"OAK", "SD", "STL"} & set(renamed_league[2019]["pbp"]["posteam"].drop_nulls())
    home, aid, bid = make_build(tmp_path, renamed_league)
    t = ft.load_tables(bid, home)
    old = set(CURRENT)
    for name, cols in (("plays", ["posteam", "defteam", "home_team", "away_team", "td_team"]),
                       ("games", ["home_team", "away_team"]), ("team_game", ["team", "opponent"]),
                       ("team_asof", ["team", "opponent"])):
        for c in cols:
            assert not old & set(t[name][c].drop_nulls().to_list()), (name, c)
    g = t["games"]
    h = g.filter(pl.col("home_team_raw").is_in(list(CURRENT)))
    assert h.height > 0 and (h["home_team_raw"].replace(CURRENT) == h["home_team"]).all()
    assert g.filter(pl.col("season") == 2020)["home_team_raw"].equals(g.filter(pl.col("season") == 2020)["home_team"])
    # invariante: todo team_game é de um dos dois times do jogo e os pontos batem com is_home
    j = t["team_game"].join(g.select("game_id", "home_team", "away_team", "home_score", "away_score"), on="game_id")
    assert j.height == t["team_game"].height > 0
    assert j.filter((pl.col("team") != pl.col("home_team")) & (pl.col("team") != pl.col("away_team"))).height == 0
    assert j.filter(pl.col("is_home") != (pl.col("team") == pl.col("home_team"))).height == 0
    exp = pl.when(pl.col("is_home")).then(pl.col("home_score")).otherwise(pl.col("away_score"))
    assert j.filter(pl.col("points_for") != exp).height == 0
    # cada jogo completo com PBP tem as duas linhas, uma de cada lado
    per = t["team_game"].group_by("game_id").agg(pl.col("is_home").sum().alias("h"), pl.len().alias("n"))
    assert (per["n"] == 2).all() and (per["h"] == 1).all()


def test_history_crosses_the_franchise_change_h_d9(tmp_path, renamed_league):
    home, _, bid = make_build(tmp_path, renamed_league)
    asof = ft.load_tables(bid, home)["team_asof"]
    for team in ("LV", "LAC", "LA"):
        rows = asof.filter(pl.col("team") == team).sort("kickoff_utc")
        assert rows["games_prior_total"].to_list() == list(range(rows.height))  # contínuo: 0,1,2,...
        first20 = rows.filter(pl.col("season") == 2020).row(0, named=True)
        assert first20["games_prior_season"] == 0 and first20["games_prior_total"] == 8
        assert first20["ewm4_off_epa"] is not None and first20["last3_off_epa"] is not None
        assert first20["season_off_epa"] is None


def test_old_acquisition_still_builds_after_refresh_m2(tmp_path, league):
    home = tmp_path / "h"
    aid1 = acq.acquire([2023, 2024], home, loader=FakeLoader(league), today=TODAY)
    b1 = ft.build(aid1, home, allow_partial=True)
    changed = {**league, 2024: {"pbp": league[2024]["pbp"].with_columns(epa=pl.col("epa") + 1),
                                "schedules": league[2024]["schedules"]}}
    aid2 = acq.acquire([2023, 2024], home, loader=FakeLoader(changed), today=TODAY)
    assert aid2 != aid1
    assert ft.build(aid1, home, allow_partial=True) == b1  # reconstruível (e idêntico)
    assert ft.build(aid2, home, allow_partial=True) != b1


def test_build_migrates_legacy_layout(tmp_path, league):
    from test_acquire import legacy_home
    home = tmp_path / "h"
    old_id, _ = legacy_home(home, league, [2023, 2024])
    bid = ft.build(None, home, allow_partial=True)
    assert ft.load_tables(bid, home)["games"].height > 0
    assert acq.resolve_acquisition(old_id, home)["migrated_from"] == old_id


# ------------------------------------------------------------------ dados reais
@pytest.fixture(scope="module")
def real_manifest():
    from hubpaths import hub_home
    home = hub_home()
    try:
        return home, acq.resolve_acquisition(None, home)
    except acq.AcquireError:
        pytest.skip("sem aquisição real no hub")


@pytest.mark.real_data
def test_real_next_score_against_scoreboard(real_manifest):
    """Confere o alvo em 3 jogos reais contra a variação do placar (total_home/away_score)."""
    home, man = real_manifest
    season = max(s for s, e in man["seasons"].items() if e.get("pbp") and int(s) < 2026)
    path = home / man["seasons"][season]["pbp"]["path"]
    ids = pl.scan_parquet(path).filter(pl.col("season_type") == "REG").select("game_id").unique() \
        .sort("game_id").head(3).collect()["game_id"].to_list()
    raw = pl.read_parquet(path).filter(pl.col("game_id").is_in(ids))
    plays = ft.build_plays(ft.cast_pbp(raw))
    raw = raw.select("game_id", "play_id", "total_home_score", "total_away_score", "home_team", "posteam",
                     "two_point_attempt", "touchdown", "play_type", "qtr").with_columns(
        pl.col("play_id").cast(pl.Int64)).sort(["game_id", "play_id"])
    checked = 0
    for gid in ids:
        # só jogadas com posteam: linhas de timeout/fim de quarto trazem placar defasado no raw
        g = raw.filter((pl.col("game_id") == gid) & pl.col("posteam").is_not_null())
        p = plays.filter((pl.col("game_id") == gid) & pl.col("posteam").is_not_null())
        assert g["play_id"].to_list() == p["play_id"].to_list()
        # eventos independentes: salto de total_*_score (placar APÓS a jogada) entre linhas consecutivas (6/3/2),
        # exceto conversões de 2 pontos
        hs, as_ = g["total_home_score"].to_list(), g["total_away_score"].to_list()
        two = g["two_point_attempt"].fill_null(0).to_list()
        events = []  # (índice da jogada que pontuou, time, pontos)
        for i in range(1, g.height):
            dh, da = hs[i] - hs[i - 1], as_[i] - as_[i - 1]
            if two[i] == 1:
                continue
            for team, d in ((g["home_team"][0], dh), (None, da)):
                if d in (2, 3, 6):
                    events.append((i, "home" if team else "away", d))
        assert events, gid
        types, pts, half = p["next_score_type"].to_list(), p["next_score_points"].to_list(), p["half"].to_list()
        posh = p["posteam_is_home"].to_list()
        for i in range(g.height):
            if posh[i] is None:
                continue
            nxt = next(((j, t, d) for j, t, d in events if j >= i and half[j] == half[i]), None)
            if nxt is None:
                assert types[i] == "NO_SCORE" and pts[i] == 0, (gid, i)
            else:
                _, t, d = nxt
                own = (t == "home") == posh[i]
                assert abs(pts[i]) == {6: 7, 3: 3, 2: 2}[d] and (pts[i] > 0) == own, (gid, i, types[i], pts[i], nxt)
            checked += 1
    assert checked > 300


@pytest.mark.real_data
def test_real_build_current_is_consistent(real_manifest):
    home, man = real_manifest
    try:
        t = ft.load_tables(None, home)
    except ft.FeatureError:
        pytest.skip("sem build real")
    plays, asof = t["plays"], t["team_asof"]
    assert plays["next_score_type"].drop_nulls().is_in(
        ["TD", "FG", "SAFETY", "OPP_TD", "OPP_FG", "OPP_SAFETY", "NO_SCORE"]).all()
    assert plays.filter(pl.col("ep_eligible"))["next_score_type"].null_count() == 0
    assert asof.height == 2 * t["games"].height
    assert asof.filter(pl.col("games_prior_total") == 0)["season_off_epa"].null_count() == \
        asof.filter(pl.col("games_prior_total") == 0).height


# ------------------------------------------------------------------ dados reais: revisão H1-H3
@pytest.fixture(scope="module")
def real_build(real_manifest):
    home, man = real_manifest
    try:
        return home, man, ft.load_tables(None, home)
    except ft.FeatureError:
        pytest.skip("sem build real")


def raw_pbp(home, man, columns):
    parts = [pl.read_parquet(home / e["pbp"]["path"], columns=columns) for e in man["seasons"].values() if e.get("pbp")]
    return pl.concat(parts, how="vertical_relaxed")


@pytest.mark.real_data
def test_real_team_game_invariant_and_franchise_c1(real_build):
    home, man, t = real_build
    for name, cols in (("plays", ["posteam", "defteam", "home_team", "away_team", "td_team"]),
                       ("games", ["home_team", "away_team"]), ("team_game", ["team", "opponent"]),
                       ("team_asof", ["team", "opponent"])):
        for c in cols:
            assert not {"OAK", "SD", "STL"} & set(t[name][c].drop_nulls().unique().to_list()), (name, c)
    j = t["team_game"].join(t["games"].select("game_id", "home_team", "away_team", "home_score", "away_score"),
                            on="game_id")
    assert j.height == t["team_game"].height
    bad_team = j.filter((pl.col("team") != pl.col("home_team")) & (pl.col("team") != pl.col("away_team")))
    bad_home = j.filter(pl.col("is_home") != (pl.col("team") == pl.col("home_team")))
    exp_for = pl.when(pl.col("is_home")).then(pl.col("home_score")).otherwise(pl.col("away_score"))
    exp_against = pl.when(pl.col("is_home")).then(pl.col("away_score")).otherwise(pl.col("home_score"))
    bad_pts = j.filter((pl.col("points_for") != exp_for) | (pl.col("points_against") != exp_against))
    assert bad_team.height == bad_home.height == bad_pts.height == 0
    r = t["team_game"].filter((pl.col("game_id") == "2011_01_PHI_STL") & (pl.col("team") == "LA")).row(0, named=True)
    assert r["is_home"] is True and r["points_for"] == 13 and r["opponent"] == "PHI"
    g = t["games"].filter(pl.col("game_id") == "2011_01_PHI_STL").row(0, named=True)
    assert (g["home_team"], g["home_team_raw"]) == ("LA", "STL")
    # histórico contínuo atravessando a mudança de cidade (H-D9): LV começa 2020 com os jogos de OAK
    lv = t["team_asof"].filter(pl.col("team") == "LV").sort("kickoff_utc")
    played = lv.filter(pl.col("game_id").is_in(t["team_game"]["game_id"].to_list()))  # jogos futuros repetem a contagem
    assert played["games_prior_total"].to_list() == list(range(played.height)) and played.height > 250
    first20 = lv.filter(pl.col("season") == 2020).row(0, named=True)
    assert first20["games_prior_total"] > 30 and first20["ewm4_off_epa"] is not None


@pytest.mark.real_data
def test_real_punt_return_safeties_score_for_kicker_m1(real_build):
    home, man, t = real_build
    cases = {"2017_08_LAC_NE": (1279, "NE"), "2017_13_DEN_MIA": (3703, "MIA"), "2018_14_JAX_TEN": (786, "JAX"),
             "2020_15_KC_NO": (2492, "NO"), "2021_17_ATL_BUF": (203, "ATL")}
    for gid, (pid, kicker) in cases.items():
        r = t["plays"].filter((pl.col("game_id") == gid) & (pl.col("play_id") == pid)).row(0, named=True)
        assert r["safety"] == 1.0 and r["play_type"] == "punt" and r["posteam"] == kicker, gid
        assert (r["next_score_type"], r["next_score_points"]) == ("SAFETY", 2), gid


@pytest.mark.real_data
def test_real_points_reconcile_with_schedule_for_all_completed_games(real_build):
    """Pontos por time reconstruídos das jogadas (TD 6 + FG 3 + safety 2 + PAT 1 + conversão de 2) = placar do schedule,
    em TODO jogo completo. Usa a mesma atribuição de time do alvo (``td_team``, ``posteam``, ``safety_scorer``)."""
    home, man, t = real_build
    cols = ["game_id", "season_type", "posteam", "defteam", "td_team", "touchdown", "field_goal_result", "safety",
            "posteam_score", "posteam_score_post", "extra_point_result", "two_point_conv_result",
            "defensive_two_point_conv"]
    raw = raw_pbp(home, man, cols).filter(pl.col("season_type").is_in(["REG", "POST"])).with_columns(
        [ft.normalize_team(c) for c in ("posteam", "defteam", "td_team")]).with_columns(
        pl.col("touchdown", "safety", "defensive_two_point_conv", "posteam_score", "posteam_score_post").cast(pl.Float64))
    parts = [
        raw.filter(pl.col("touchdown") == 1).select("game_id", pl.col("td_team").alias("team"), pl.lit(6).alias("pts")),
        raw.filter(pl.col("field_goal_result") == "made").select("game_id", pl.col("posteam").alias("team"), pl.lit(3).alias("pts")),
        raw.filter(pl.col("safety") == 1).select("game_id", ft.safety_scorer().alias("team"), pl.lit(2).alias("pts")),
        raw.filter(pl.col("extra_point_result") == "good").select("game_id", pl.col("posteam").alias("team"), pl.lit(1).alias("pts")),
        raw.filter(pl.col("two_point_conv_result") == "success").select("game_id", pl.col("posteam").alias("team"), pl.lit(2).alias("pts")),
        raw.filter(pl.col("defensive_two_point_conv") == 1).select("game_id", pl.col("defteam").alias("team"), pl.lit(2).alias("pts")),
    ]
    pts = pl.concat(parts).group_by("game_id", "team").agg(pl.col("pts").sum())
    g = t["games"].filter(pl.col("completed")).select("game_id", "home_team", "away_team", "home_score", "away_score")
    g = g.join(pts.rename({"team": "home_team", "pts": "h"}), on=["game_id", "home_team"], how="left") \
        .join(pts.rename({"team": "away_team", "pts": "a"}), on=["game_id", "away_team"], how="left") \
        .with_columns(pl.col("h", "a").fill_null(0))
    assert g.height > 4000
    bad = g.filter((pl.col("h") != pl.col("home_score")) | (pl.col("a") != pl.col("away_score")))
    assert bad.height == 0, bad


@pytest.mark.real_data
def test_real_half_matches_nflverse_game_half_and_out_of_order_count_b3(real_build):
    home, man, t = real_build
    raw = raw_pbp(home, man, ["game_id", "play_id", "season_type", "game_half"]).filter(
        pl.col("season_type").is_in(["REG", "POST"])).with_columns(pl.col("play_id").cast(pl.Int64))
    j = t["plays"].select("game_id", "play_id", "half").join(raw, on=["game_id", "play_id"], how="inner")
    assert j.height == t["plays"].height
    gh = j["game_half"].replace_strict({"Half1": 1, "Half2": 2, "Overtime": 3})
    assert (j["half"] == gh).all()
    bm = json.loads((ft.resolve_build(None, home) / "manifest.json").read_text())
    assert bm["qa"]["games_qtr_out_of_order"] == ft.count_out_of_order_games(t["plays"]) > 0


# ------------------------------------------------------------------ M-1: cobertura do manifesto
def test_build_refuses_partial_manifest_unless_allowed(tmp_path, league):
    home = tmp_path / "h"
    aid = acq.acquire([2024], home, loader=FakeLoader(league), today=TODAY)
    with pytest.raises(ft.FeatureError, match="não cobre 2011..2024"):
        ft.build(aid, home, last_season=2024)
    assert not (home / "features").exists() or not list((home / "features").glob("*/manifest.json"))
    bid = ft.build(aid, home, allow_partial=True)
    assert json.loads((home / "features" / bid / "manifest.json").read_text())["qa"]["partial"] is True


def test_build_accepts_continuous_range_with_configurable_first_season(tmp_path, league):
    home = tmp_path / "h"
    aid = acq.acquire([2023, 2024], home, loader=FakeLoader(league), today=TODAY)
    bid = ft.build(aid, home, first_season=2023, last_season=2024)
    assert json.loads((home / "features" / bid / "manifest.json").read_text())["qa"]["partial"] is False
    with pytest.raises(ft.FeatureError, match="2022"):  # a primeira exigida não está no manifesto
        ft.build(aid, home, first_season=2022, last_season=2024)
    with pytest.raises(ft.FeatureError, match="2025"):  # falta a temporada corrente
        ft.build(aid, home, first_season=2023, last_season=2025)


def test_build_requires_pbp_except_last_season(tmp_path, league):
    home = tmp_path / "h"
    aid = acq.acquire([2023, 2024], home, loader=FakeLoader(league), today=TODAY)
    man = json.loads((home / "acquisitions" / f"{aid}.json").read_text())
    man["seasons"]["2023"]["pbp"] = None
    with pytest.raises(ft.FeatureError, match="2023: sem pbp"):
        ft.check_coverage(man, 2023, 2024)
    man["seasons"]["2023"]["pbp"] = {"x": 1}
    man["seasons"]["2024"]["pbp"] = None
    ft.check_coverage(man, 2023, 2024)  # última temporada pode estar sem PBP
