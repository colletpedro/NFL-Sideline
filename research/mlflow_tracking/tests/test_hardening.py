"""Endurecimento: importação interrompida, rollback em disco, guardas, proveniência, Default, CLI, integridade."""
import json
import os
import subprocess
import sys
from pathlib import Path

import mlflow
import pytest
from mlflow import MlflowClient

import cli
import import_v1
import importer_base as base
import integrity
import test_import_v1 as t1
import tracking

HERE = Path(__file__).resolve().parent
MODULE = HERE.parent


@pytest.fixture(autouse=True)
def no_repo_refs(tmp_path, monkeypatch):
    """design.json/RESEARCH-CONTRACT.md sintéticos, citados pelos hashes do store sintético da v1."""
    refs = tmp_path / "refs"
    refs.mkdir()
    (refs / "design.json").write_bytes(t1.DESIGN_BYTES)
    (refs / "RESEARCH-CONTRACT.md").write_bytes(t1.CONTRACT_BYTES)
    monkeypatch.setattr(import_v1, "DESIGN_PATH", refs / "design.json")
    monkeypatch.setattr(import_v1, "CONTRACT_PATH", refs / "RESEARCH-CONTRACT.md")
    return refs


@pytest.fixture
def env(tmp_path, monkeypatch):
    stores = tmp_path / "stores"
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(stores))
    return {"store": t1.make_store(stores), "home": tmp_path / "mlflow home", "stores": stores}


def exp_dir(home):
    return Path(home).resolve() / "artifacts" / "qb-iw-baseline-v1"


def run_dirs(home):
    d = exp_dir(home)
    return sorted(p.name for p in d.iterdir()) if d.exists() else []


def active_ids(home):
    exp = tracking.ensure_experiment("v1", home)
    return sorted(r.info.run_id for r in MlflowClient().search_runs([exp], max_results=1000))


# ------------------------------------------------------------ 1. crash / rebuild

CRASH = """
import os, sys
sys.path[:0] = [{module!r}, {tests!r}]
import import_v1
from pathlib import Path
import_v1.DESIGN_PATH = Path(sys.argv[3])
import_v1.CONTRACT_PATH = Path(sys.argv[4])
def boom(self, *a, **k):
    os._exit(9)
import_v1._Importer.application_run = boom
import_v1.import_v1(Path(sys.argv[1]), Path(sys.argv[2]))
"""


def test_crash_leaves_running_parent_then_cleans_and_reimports(env, no_repo_refs):
    code = CRASH.format(module=str(MODULE), tests=str(HERE))
    r = subprocess.run([sys.executable, "-c", code, str(env["store"]), str(env["home"]),
                        str(no_repo_refs / "design.json"), str(no_repo_refs / "RESEARCH-CONTRACT.md")],
                       env={**os.environ}, capture_output=True, text=True)
    assert r.returncode == 9, r.stderr
    tracking.configure(env["home"])
    client = MlflowClient()
    exp = tracking.ensure_experiment("v1", env["home"])
    parents = client.search_runs([exp], filter_string="tags.role = 'parent'")
    assert len(parents) == 1 and parents[0].info.status == "RUNNING"
    assert len(client.search_runs([exp], max_results=1000)) > 5  # filhas parciais
    assert tracking.find_parent(exp, parents[0].data.tags["source_freeze_sha256"]) is None
    old_dirs = set(run_dirs(env["home"]))

    res = import_v1.import_v1(env["store"], env["home"])
    assert res["created"] is True
    assert res["counts"] == {"parent": 1, "fold": 8, "selection": 2, "evaluation": 2, "application": 2}
    ids = active_ids(env["home"])
    assert len(ids) == 15
    assert set(run_dirs(env["home"])) <= set(ids) and len(run_dirs(env["home"])) == 5  # pai, 2 eval, 2 app
    assert not (old_dirs & set(run_dirs(env["home"])))
    again = import_v1.import_v1(env["store"], env["home"])
    assert again["created"] is False and again["counts"]["fold"] == 8


def test_finished_parent_with_missing_children_errors_and_rebuild_fixes(env):
    import_v1.import_v1(env["store"], env["home"])
    exp = tracking.ensure_experiment("v1", env["home"])
    client = MlflowClient()
    victim = client.search_runs([exp], filter_string="tags.role = 'fold'")[0].info.run_id
    client.delete_run(victim)
    with pytest.raises(import_v1.V1ImportError, match="--rebuild"):
        import_v1.import_v1(env["store"], env["home"])
    res = import_v1.import_v1(env["store"], env["home"], rebuild=True)
    assert res["created"] is True and res["counts"]["fold"] == 8
    ids = active_ids(env["home"])
    assert len(ids) == 15 and set(run_dirs(env["home"])) <= set(ids) and len(run_dirs(env["home"])) == 5


# ------------------------------------------------------------ 1b. --rebuild nunca perde a importação boa

def test_failed_rebuild_keeps_previous_import_intact(env):
    first = import_v1.import_v1(env["store"], env["home"])
    ids, dirs = active_ids(env["home"]), run_dirs(env["home"])
    assert len(ids) == 15 and len(dirs) == 5
    # JSON não coberto por hash, lido só no meio da nova importação
    (env["store"] / "application-v1" / "application_diagnostics_depth.json").write_text("{corrompido")
    with pytest.raises(import_v1.V1ImportError, match="application_diagnostics_depth"):
        import_v1.import_v1(env["store"], env["home"], rebuild=True)
    assert active_ids(env["home"]) == ids  # nenhuma execução da importação boa foi apagada
    assert run_dirs(env["home"]) == dirs  # nem seus diretórios; e os da tentativa falha foram desfeitos
    again = import_v1.import_v1(env["store"], env["home"])
    assert again["created"] is False and again["parent_run_id"] == first["parent_run_id"]
    assert again["counts"] == {"parent": 1, "fold": 8, "selection": 2, "evaluation": 2, "application": 2}


def test_successful_rebuild_replaces_old_import(env):
    first = import_v1.import_v1(env["store"], env["home"])
    old_ids = set(active_ids(env["home"]))
    res = import_v1.import_v1(env["store"], env["home"], rebuild=True)
    assert res["created"] is True and res["parent_run_id"] != first["parent_run_id"]
    new_ids = set(active_ids(env["home"]))
    assert len(new_ids) == 15 and not (new_ids & old_ids)
    assert MlflowClient().get_run(first["parent_run_id"]).info.lifecycle_stage == "deleted"
    assert set(run_dirs(env["home"])) <= new_ids and len(run_dirs(env["home"])) == 5


# ------------------------------------------------------------ 1c. kill entre "nova pronta" e "antiga apagada"

KILL_BEFORE_DELETE = """
import os, sys
sys.path[:0] = [{module!r}, {tests!r}]
import import_v1
import importer_base
from pathlib import Path
import_v1.DESIGN_PATH = Path(sys.argv[3])
import_v1.CONTRACT_PATH = Path(sys.argv[4])
orig = importer_base.delete_runs
def boom(client, ids, home):
    if list(ids):  # só a apagada da importação antiga (a limpeza de incompletas passa com lista vazia)
        os._exit(9)
    return orig(client, ids, home)
importer_base.delete_runs = boom
import_v1.import_v1(Path(sys.argv[1]), Path(sys.argv[2]), rebuild=True)
"""


def _kill_rebuild_before_old_deleted(env, no_repo_refs):
    code = KILL_BEFORE_DELETE.format(module=str(MODULE), tests=str(HERE))
    r = subprocess.run([sys.executable, "-c", code, str(env["store"]), str(env["home"]),
                        str(no_repo_refs / "design.json"), str(no_repo_refs / "RESEARCH-CONTRACT.md")],
                       env={**os.environ}, capture_output=True, text=True)
    assert r.returncode == 9, r.stderr


def test_killed_rebuild_leaves_two_finished_parents_import_refuses_compare_fails_rebuild_recovers(
        env, no_repo_refs, capsys):
    import compare
    first = import_v1.import_v1(env["store"], env["home"])
    _kill_rebuild_before_old_deleted(env, no_repo_refs)
    tracking.configure(env["home"])
    exp = tracking.ensure_experiment("v1", env["home"])
    client = MlflowClient()
    parents = client.search_runs([exp], filter_string="tags.role = 'parent' and attributes.status = 'FINISHED'")
    assert len(parents) == 2 and first["parent_run_id"] in {p.info.run_id for p in parents}
    freeze = parents[0].data.tags["source_freeze_sha256"]
    ordered = [p.info.run_id for p in tracking.find_parents(exp, freeze)]
    assert tracking.find_parent(exp, freeze).info.run_id == ordered[0]  # determinístico
    assert ordered == [p.info.run_id for p in tracking.find_parents(exp, freeze)]

    # import sem --rebuild: erro claro, nada é apagado nem importado em silêncio
    with pytest.raises(import_v1.V1ImportError, match="--rebuild") as ei:
        import_v1.import_v1(env["store"], env["home"])
    assert "2 importações FINISHED" in str(ei.value)
    assert len(client.search_runs([exp], filter_string="tags.role = 'parent' and attributes.status = 'FINISHED'")) == 2
    assert cli.main(["import", "v1", "--store", str(env["store"]), "--home", str(env["home"])]) == 2
    assert "--rebuild" in capsys.readouterr().err

    # compare reprova o experimento com mais de um pai FINISHED do mesmo freeze
    table = compare.build_table(env["home"])
    assert any("mais de um pai FINISHED" in p and "import v1 --rebuild" in p for p in compare.verify(table))
    assert "um só pai FINISHED por freeze | FAIL" in compare.render_markdown(table)

    # --rebuild recupera: fica uma só importação completa
    res = import_v1.import_v1(env["store"], env["home"], rebuild=True)
    assert res["created"] is True
    parents = client.search_runs([exp], filter_string="tags.role = 'parent' and attributes.status = 'FINISHED'")
    assert [p.info.run_id for p in parents] == [res["parent_run_id"]]
    ids = active_ids(env["home"])
    assert len(ids) == 15 and set(run_dirs(env["home"])) <= set(ids) and len(run_dirs(env["home"])) == 5
    assert not [p for p in compare.verify(compare.build_table(env["home"])) if "mais de um pai" in p]
    again = import_v1.import_v1(env["store"], env["home"])
    assert again["created"] is False and again["parent_run_id"] == res["parent_run_id"]


# ------------------------------------------------------------ 1d. elo upstream v2 -> v1 quebrado vira aviso

def test_compare_warns_when_v2_upstream_v1_parent_is_inactive_after_v1_rebuild(env):
    import compare
    import test_compare as tc
    v1 = import_v1.import_v1(env["store"], env["home"])
    tc.build_v2(env["home"])
    tc.build_xint(env["home"])
    exp2 = tracking.ensure_experiment("v2", env["home"])
    client = MlflowClient()
    (p2,) = client.search_runs([exp2], filter_string="tags.role = 'parent'")
    client.set_tag(p2.info.run_id, "upstream_v1_parent_run_id", v1["parent_run_id"])  # o que `import v2` grava
    table = compare.build_table(env["home"])
    assert table["warnings"] == []
    assert "Nenhum aviso" in compare.render_markdown(table)
    problems_before = compare.verify(table)

    new = import_v1.import_v1(env["store"], env["home"], rebuild=True)  # pai v1 antigo é apagado
    table = compare.build_table(env["home"])
    assert len(table["warnings"]) == 1 and v1["parent_run_id"] in table["warnings"][0]
    assert new["parent_run_id"] != v1["parent_run_id"]
    assert "import v2 --rebuild" in table["warnings"][0] and "register m3" in table["warnings"][0]
    md = compare.render_markdown(table)
    assert "## Avisos" in md and "upstream_v1_parent_run_id" in md
    assert json.loads(json.dumps(table, default=str))["warnings"] == table["warnings"]
    assert compare.verify(table) == problems_before  # aviso não reprova nada


def other_freeze_store(root):
    """Segundo store v1 válido, com outro freeze (constant_prevalence diferente) e recibos coerentes."""
    store = t1.make_store(root)
    fp = store / "development-v3" / "frozen_config.json"
    d = json.loads(fp.read_text())
    d["constant_prevalence"] = 0.5
    fp.write_text(json.dumps(d, indent=1))
    fsha = t1.sha(fp.read_bytes())
    for rel in ("evaluation-v1/evaluation_receipt.json", "application-v1/application_receipt.json"):
        r = json.loads((store / rel).read_text())
        r["frozen_config_sha256"] = fsha
        (store / rel).write_text(json.dumps(r))
    return store


def test_purge_and_rebuild_preserve_other_freeze(env, tmp_path):
    other = other_freeze_store(tmp_path / "outro")
    a = import_v1.import_v1(env["store"], env["home"])
    b = import_v1.import_v1(other, env["home"])
    assert a["parent_run_id"] != b["parent_run_id"]
    client = MlflowClient()
    exp = tracking.ensure_experiment("v1", env["home"])

    def family(parent_id):
        kids = {r.info.run_id for r in base.child_runs(client, exp, parent_id)}
        return kids | {parent_id}

    b_ids = family(b["parent_run_id"])
    assert len(b_ids) == 15 and len(active_ids(env["home"])) == 30
    b_dirs = {d for d in run_dirs(env["home"]) if d in b_ids}
    import_v1.import_v1(env["store"], env["home"], rebuild=True)
    ids = set(active_ids(env["home"]))
    assert b_ids <= ids and len(ids) == 30
    assert b_dirs <= set(run_dirs(env["home"]))
    # pai KILLED do outro freeze não é limpo ao importar este
    client.set_terminated(b["parent_run_id"], "KILLED")
    import_v1.import_v1(env["store"], env["home"])
    assert client.get_run(b["parent_run_id"]).info.lifecycle_stage == "active"
    res = import_v1.import_v1(other, env["home"])  # o dono do freeze limpa o próprio resto e reimporta
    assert res["created"] is True
    assert client.get_run(b["parent_run_id"]).info.lifecycle_stage == "deleted"


def test_stale_importer_code_warns_but_does_not_fail(env, monkeypatch, capsys):
    import_v1.import_v1(env["store"], env["home"])
    capsys.readouterr()
    res = import_v1.import_v1(env["store"], env["home"])
    assert res["created"] is False and "aviso" not in capsys.readouterr().err
    monkeypatch.setattr(tracking, "importer_code_sha256", lambda importer_file=None: "f" * 64)
    res = import_v1.import_v1(env["store"], env["home"])
    err = capsys.readouterr().err
    assert res["created"] is False
    assert "aviso (v1)" in err and "--rebuild" in err and res["parent_run_id"] in err


# ------------------------------------------------------------ 1c. exceções viram ImporterError

def test_unexpected_exceptions_become_importer_error_with_context(env):
    ev = env["store"] / "evaluation-v1" / "metrics.json"
    m = json.loads(ev.read_text())
    del m["depth"]
    t1.wjson(ev, m)
    with pytest.raises(import_v1.V1ImportError, match="KeyError") as e:
        import_v1.import_v1(env["store"], env["home"])
    assert isinstance(e.value.__cause__, KeyError) and "importação v1" in str(e.value)
    assert active_ids(env["home"]) == []  # rollback antes de embrulhar


def test_cli_reports_unexpected_failure_without_traceback(env, capsys):
    ev = env["store"] / "evaluation-v1" / "metrics.json"
    m = json.loads(ev.read_text())
    del m["depth"]
    t1.wjson(ev, m)
    code = cli.main(["import", "v1", "--store", str(env["store"]), "--home", str(env["home"])])
    err = capsys.readouterr().err
    assert code == 2 and "\nerro (v1): importação v1: KeyError" in "\n" + err and "Traceback" not in err


def test_wrap_errors_keeps_notes_and_passes_importer_errors_through():
    class E(base.ImporterError):
        pass

    @base.wrap_errors(E, "alvo")
    def boom(kind):
        if kind == "own":
            raise base.ImporterError("já é nosso")
        exc = ValueError("ruim")
        exc.add_note("nota de limpeza")
        raise exc

    with pytest.raises(base.ImporterError, match="já é nosso") as own:
        boom("own")
    assert type(own.value) is base.ImporterError
    with pytest.raises(E, match="alvo: ValueError: ruim") as e:
        boom("other")
    assert e.value.__notes__ == ["nota de limpeza"] and isinstance(e.value.__cause__, ValueError)


def test_ensure_experiment_restores_deleted_with_same_location(tmp_path):
    home = tracking.configure(tmp_path / "h")
    client = MlflowClient()
    exp_id = tracking.ensure_experiment("v1", home)
    client.delete_experiment(exp_id)
    assert client.get_experiment(exp_id).lifecycle_stage == "deleted"
    assert tracking.ensure_experiment("v1", home) == exp_id
    assert client.get_experiment(exp_id).lifecycle_stage == "active"


def test_ensure_experiment_deleted_with_other_location_is_clear_error(tmp_path):
    home = tracking.configure(tmp_path / "h")
    client = MlflowClient()
    exp_id = client.create_experiment("qb-iw-baseline-v1", artifact_location=(tmp_path / "outro").as_uri())
    client.delete_experiment(exp_id)
    with pytest.raises(RuntimeError, match="artifact_location"):
        tracking.ensure_experiment("v1", home)


def test_cli_import_after_experiment_deleted(env, capsys):
    a = ["import", "v1", "--store", str(env["store"]), "--home", str(env["home"])]
    assert cli.main(a) == 0
    MlflowClient().delete_experiment(tracking.ensure_experiment("v1", env["home"]))
    capsys.readouterr()
    assert cli.main(a) == 0
    assert "Traceback" not in capsys.readouterr().err
    assert MlflowClient().get_experiment_by_name("qb-iw-baseline-v1").lifecycle_stage == "active"


def test_cli_import_all_prints_full_counts_with_created_false(env, tmp_path, monkeypatch, capsys):
    """`import all` com os três importadores reais sobre stores sintéticos: segunda rodada = created=false nos três."""
    import import_v2
    import import_xint
    import test_import_v2 as t2
    import test_import_xint as tx

    repo = tmp_path / "repo2"
    t2.make_store(env["stores"], repo)
    x = tx.make_store(tmp_path / "x")
    monkeypatch.setenv("NFL_RESEARCH_STORES", str(env["stores"]))
    # xINT sintético mora em outra raiz: o alvo recebe seu store por --store, então só o importador é redirecionado
    real_v2, real_x = import_v2.import_v2, import_xint.import_xint
    monkeypatch.setattr(import_v2, "import_v2", lambda store, home, rebuild=False: real_v2(
        store, home, repo_root=repo, rebuild=rebuild))
    monkeypatch.setattr(import_xint, "import_xint", lambda store, home, rebuild=False: real_x(
        x["store"], home, code_dir=x["code"], config_path=x["code"] / "config.json", model_sha=x["model_sha"],
        contract_path=x["contract"], rebuild=rebuild))
    base_args = ["import", "all", "--home", str(env["home"])]
    assert cli.main(base_args) == 0
    first = capsys.readouterr().out
    assert first.count("created=true") == 3
    assert cli.main(base_args) == 0
    out = capsys.readouterr().out
    assert out.count("created=false") == 3 and "created=true" not in out
    blocks = {b.split("\n")[0]: b for b in out.split("target=")[1:]}
    assert set(blocks) == {"v1", "v2", "xint"}
    assert "fold=8" in blocks["v1"] and "selection=2" in blocks["v1"] and "evaluation=2" in blocks["v1"]
    assert "application=2" in blocks["v1"] and "parent=1" in blocks["v1"] and "parent_run_id=" in blocks["v1"]
    assert "candidate=12" in blocks["v2"] and "selection=1" in blocks["v2"] and "parent=1" in blocks["v2"]
    for role, n in (("fold", 8), ("selection", 1), ("evaluation", 4), ("final", 1), ("application", 1), ("parent", 1)):
        assert f"{role}={n}" in blocks["xint"]


# ------------------------------------------------------------ 2. rollback em disco

def test_rollback_leaves_no_directories(env):
    (env["store"] / "application-v1" / "application_diagnostics_depth.json").write_text("{corrompido")
    with pytest.raises(import_v1.V1ImportError):
        import_v1.import_v1(env["store"], env["home"])
    assert run_dirs(env["home"]) == []


def test_rollback_errors_are_attached(env, monkeypatch):
    (env["store"] / "application-v1" / "application_diagnostics_depth.json").write_text("{corrompido")
    def bad(path, home):
        raise OSError("sem permissão")
    monkeypatch.setattr(base, "remove_run_dir", bad)
    with pytest.raises(import_v1.V1ImportError) as e:
        import_v1.import_v1(env["store"], env["home"])
    assert any("sem permissão" in n for n in e.value.__notes__)


def test_remove_run_dir_refuses_outside_home(tmp_path):
    home = tmp_path / "h"
    (home / "artifacts").mkdir(parents=True)
    outside = tmp_path / "fora"
    outside.mkdir()
    with pytest.raises(base.ImporterError, match="fora de"):
        base.remove_run_dir(outside, home)
    with pytest.raises(base.ImporterError):
        base.remove_run_dir(home / "artifacts", home)
    assert outside.exists()


# ------------------------------------------------------------ 5. proveniência

def test_provenance_tags_on_all_runs(env):
    import_v1.import_v1(env["store"], env["home"])
    exp = tracking.ensure_experiment("v1", env["home"])
    runs = MlflowClient().search_runs([exp], max_results=1000)
    codes = {r.data.tags["importer_code_sha256"] for r in runs}
    assert len(codes) == 1 and all(len(c) == 64 for c in codes)
    assert all(r.data.tags["imported_at_utc"].endswith("+00:00") for r in runs)
    # a tag gravada é exatamente o hash do código atual (tracking + importer_base + import_v1)
    assert codes == {tracking.importer_code_sha256(MODULE / "import_v1.py")}


def test_importer_code_sha256_depends_on_content_and_name(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    (a / "imp.py").write_text("x = 1\n")
    (b / "imp.py").write_text("x = 1\n")
    same = tracking.importer_code_sha256(a / "imp.py")
    assert same == tracking.importer_code_sha256(b / "imp.py")  # só nome e bytes importam, não o diretório
    (b / "imp.py").write_text("x = 2\n")
    assert tracking.importer_code_sha256(b / "imp.py") != same
    assert tracking.importer_code_sha256() != same and tracking.importer_code_sha256(None) != same
    (b / "imp.py").write_text("x = 1\n")
    (b / "outro.py").write_text("x = 1\n")
    assert tracking.importer_code_sha256(b / "outro.py") != same  # o nome do arquivo entra no hash


def test_git_info_outside_repo(tmp_path):
    info = tracking.git_info(tmp_path)
    assert info == {"commit": "unknown", "branch": "unknown", "dirty": "unknown"}
    tags = tracking.base_tags("s", "f", "d", "p", 1, "parent", tmp_path)
    assert tags["git_dirty"] == "unknown"


def test_git_dirty_only_for_module_pathspec(tmp_path):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    def g(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True, env=env)
    (tmp_path / "research" / "mlflow_tracking").mkdir(parents=True)
    (tmp_path / "research" / "mlflow_tracking" / "a.py").write_text("1")
    g("init", "-q")
    g("add", ".")
    g("commit", "-q", "-m", "x")
    (tmp_path / "outro.txt").write_text("sujo")
    assert tracking.git_info(tmp_path)["dirty"] is False
    (tmp_path / "research" / "mlflow_tracking" / "a.py").write_text("2")
    assert tracking.git_info(tmp_path)["dirty"] is True


# ------------------------------------------------------------ 6. Default

def test_default_experiment_is_retired(tmp_path):
    home = tmp_path / "h"
    tracking.configure(home)
    assert MlflowClient().get_experiment("0").lifecycle_stage == "deleted"
    with pytest.raises(Exception):
        with mlflow.start_run():
            pass
    assert list(Path.cwd().iterdir()) == []  # nada escrito no cwd
    tracking.configure(home)  # idempotente


# ------------------------------------------------------------ 7. guardas

def test_size_and_key_guards(env):
    class I(base.BaseImporter):
        error_cls = import_v1.V1ImportError
        def tags(self, role, extra=None):
            return {"role": role, **(extra or {})}
    tracking.configure(env["home"])
    exp = tracking.ensure_experiment("v1", env["home"])
    src = env["store"] / "sources.json"
    imp = I(env["store"], MlflowClient(), exp, {"freeze_sha": "x"}, env["home"])
    with pytest.raises(import_v1.V1ImportError, match="6000"):
        imp.new_run("n", "r", src, base.Bag(), {"p": "x" * 6001})
    with pytest.raises(import_v1.V1ImportError, match="8000"):
        imp.new_run("n", "r", src, base.Bag(), {}, extra_tags={"t": "x" * 8001})
    bag = base.Bag()
    bag.add("métrica$ruim", 1.0)
    with pytest.raises(import_v1.V1ImportError, match="inválida"):
        imp.new_run("n", "r", src, bag, {})
    with pytest.raises(import_v1.V1ImportError, match="inválida"):
        imp.new_run("n", "r", src, base.Bag(), {"a#b": "1"})
    ok = base.Bag()
    ok.add("a.b-c_d/e f:g", 1.0)
    imp.new_run("n", "r", src, ok, {"p": "x" * 6000}, extra_tags={"t": "x" * 8000})


# ------------------------------------------------------------ 8. v1 verify_chain

def test_v1_design_and_contract_hash_checks(env, tmp_path):
    frozen_p = env["store"] / "development-v3" / "frozen_config.json"
    frozen = json.loads(frozen_p.read_text())
    d, c = tmp_path / "design.json", tmp_path / "contract.md"
    d.write_text("design")
    c.write_text("contrato")
    with pytest.raises(import_v1.V1ImportError, match="design.json"):
        import_v1.verify_chain(env["store"], d, c)
    frozen["design_sha256"] = t1.sha(b"design")
    t1.wjson(frozen_p, frozen)
    # reescrever frozen_config muda seu hash: recibos precisam acompanhar
    fsha = t1.sha(frozen_p.read_bytes())
    for rel, name in (("evaluation-v1/evaluation_receipt.json", None), ("application-v1/application_receipt.json", None)):
        p = env["store"] / rel
        r = json.loads(p.read_text())
        r["frozen_config_sha256"] = fsha
        t1.wjson(p, r)
    with pytest.raises(import_v1.V1ImportError, match="RESEARCH-CONTRACT"):
        import_v1.verify_chain(env["store"], d, c)
    frozen["contract_sha256"] = t1.sha("contrato".encode())
    t1.wjson(frozen_p, frozen)
    fsha = t1.sha(frozen_p.read_bytes())
    for rel in ("evaluation-v1/evaluation_receipt.json", "application-v1/application_receipt.json"):
        p = env["store"] / rel
        r = json.loads(p.read_text())
        r["frozen_config_sha256"] = fsha
        t1.wjson(p, r)
    assert import_v1.verify_chain(env["store"], d, c)["freeze_sha"] == fsha


def test_missing_variant_in_chosen_c_is_import_error():
    pooled = {"context": {0.1: 1.0}, "depth": {0.1: 1.0}}
    with pytest.raises(import_v1.V1ImportError, match="depth"):
        import_v1.check_chosen(pooled, {"chosen_C": {"context": 0.1}})


def test_pooled_selection_tie_prefers_smaller_c():
    design = {"variants": ["context"], "C_grid": [0.1, 1.0], "folds": [{"validation": 2023}]}
    blk = {"log_loss": 0.2, "n": 10}
    history = [{"variant": "context", "C": c, "validation": 2023, "model": blk} for c in (0.1, 1.0)]
    pooled = import_v1.pooled_selection(history, design)
    assert pooled["context"][0.1] == pooled["context"][1.0]
    import_v1.check_chosen(pooled, {"chosen_C": {"context": 0.1}})
    with pytest.raises(import_v1.V1ImportError, match="argmin"):
        import_v1.check_chosen(pooled, {"chosen_C": {"context": 1.0}})


# ------------------------------------------------------------ 4. integridade

def mk(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    (root / "a.txt").write_text("a")
    return root


def _neutral(m):
    """Zera ctime/ino de todas as entradas: sobra só (size, mtime[, hash]); prova o que o hash sozinho detecta."""
    return {**m, "entries": {k: [v[0], v[1], 0, 0, *v[4:]] for k, v in m["entries"].items()}}


def test_integrity_manifest_format(tmp_path):
    root = mk(tmp_path)
    m = integrity.snapshot(root)
    assert m["format"] == 2 and m["root"] == str(root.resolve()) and len(m["entries"]["a.txt"]) == 4
    h = integrity.snapshot(root, with_hash=True)
    assert len(h["entries"]["a.txt"]) == 5 and len(h["entries"]["a.txt"][4]) == 64
    assert integrity.compare(h, integrity.snapshot(root, with_hash=True)) == {"added": [], "removed": [], "changed": []}


def test_integrity_hash_alone_detects_same_size_same_mtime_change(tmp_path):
    root = mk(tmp_path)
    st = (root / "a.txt").stat()
    snaps = {}
    for with_hash in (False, True):
        (root / "a.txt").write_text("a")
        os.utime(root / "a.txt", ns=(st.st_atime_ns, st.st_mtime_ns))
        before = _neutral(integrity.snapshot(root, with_hash))
        (root / "a.txt").write_text("b")  # mesmo tamanho; mtime restaurado; ctime/ino neutralizados
        os.utime(root / "a.txt", ns=(st.st_atime_ns, st.st_mtime_ns))
        after = _neutral(integrity.snapshot(root, with_hash))
        snaps[with_hash] = integrity.compare(before, after)["changed"]
    assert snaps[False] == []  # sem --hash, size+mtime iguais: invisível
    assert snaps[True] == ["a.txt"]  # com --hash, só o sha256 denuncia


def test_integrity_refuses_mixed_hash_and_plain_manifests(tmp_path):
    root = mk(tmp_path)
    plain, hashed = integrity.snapshot(root), integrity.snapshot(root, with_hash=True)
    for a, b in ((plain, hashed), (hashed, plain)):
        with pytest.raises(integrity.IntegrityError, match="hash"):
            integrity.compare(a, b)
    pa, pb = tmp_path / "plain.json", tmp_path / "hashed.json"
    pa.write_text(json.dumps(plain))
    pb.write_text(json.dumps(hashed))
    assert integrity.main(["compare", "--before", str(pa), "--after", str(pb)]) == 2
    assert integrity.main(["compare", "--before", str(pb), "--after", str(pb)]) == 0


def test_integrity_walk_error_aborts_instead_of_partial_manifest(tmp_path):
    root = mk(tmp_path)
    locked = root / "trancada"
    locked.mkdir()
    (locked / "x.txt").write_text("x")
    locked.chmod(0)
    try:
        if os.access(locked, os.R_OK):
            pytest.skip("permissões não se aplicam (root)")
        with pytest.raises(integrity.IntegrityError, match="trancada"):
            integrity.snapshot(root)
        assert integrity.main(["snapshot", "--root", str(root), "--out", str(tmp_path / "o.json")]) == 2
        assert not (tmp_path / "o.json").exists()
    finally:
        locked.chmod(0o755)


def test_integrity_symlinks_not_followed_and_target_recorded(tmp_path):
    root = mk(tmp_path)
    (root / "sub").mkdir()
    (root / "sub" / "b.txt").write_text("b")
    (root / "ln_file").symlink_to("a.txt")
    (root / "ln_dir").symlink_to("sub")
    m = integrity.snapshot(root, with_hash=True)
    assert m["entries"]["ln_file"][4:] == [None, "a.txt"] and m["entries"]["ln_dir"][4:] == [None, "sub"]
    assert not any(k.startswith("ln_dir/") for k in m["entries"])  # diretório apontado não é percorrido
    (root / "ln_file").unlink()
    (root / "ln_file").symlink_to("sub/b.txt")
    m2 = integrity.snapshot(root, with_hash=True)
    assert "ln_file" in integrity.compare(m, m2)["changed"]


def test_integrity_cli_errors_exit_2(tmp_path):
    root = mk(tmp_path)
    out = tmp_path / "o.json"
    assert integrity.main(["snapshot", "--root", str(tmp_path / "nao"), "--out", str(out)]) == 2
    assert integrity.main(["snapshot", "--root", str(root), "--out", str(root / "o.json")]) == 2
    assert integrity.main(["snapshot", "--root", str(root), "--out", str(out), "--hash"]) == 0
    empty = tmp_path / "e.json"
    empty.write_text(json.dumps({"format": 2, "root": "x", "entries": {}}))
    assert integrity.main(["compare", "--before", str(empty), "--after", str(out)]) == 2
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"a": [1, 2]}))
    assert integrity.main(["compare", "--before", str(old), "--after", str(out)]) == 2
    v3 = tmp_path / "v3.json"
    v3.write_text(json.dumps({"format": 3, "root": "x", "entries": {"a": [1]}}))
    assert integrity.main(["compare", "--before", str(v3), "--after", str(out)]) == 2


# ------------------------------------------------------------ 10. CLI

def test_cli_all_rejects_store_and_reports_errors(env, capsys):
    assert cli.main(["import", "all", "--store", "x"]) == 2
    assert "--store" in capsys.readouterr().err
    assert cli.main(["import", "v1", "--store", str(env["stores"] / "nao"), "--home", str(env["home"])]) == 2
    assert "erro" in capsys.readouterr().err


def test_cli_rebuild_flag(env, capsys):
    a = ["import", "v1", "--store", str(env["store"]), "--home", str(env["home"])]
    assert cli.main(a) == 0
    assert cli.main(a + ["--rebuild"]) == 0
    assert "created=true" in capsys.readouterr().out.split("target=v1")[-1]


def test_cli_compare_subcommand(monkeypatch, tmp_path, capsys):
    import types
    fake = types.SimpleNamespace(build_table=lambda home=None: {"x": 1}, verify=lambda t: [],
                                 render_markdown=lambda t: "# md")
    monkeypatch.setitem(sys.modules, "compare", fake)
    assert cli.main(["compare"]) == 0
    assert "# md" in capsys.readouterr().out
    out = tmp_path / "t.json"
    assert cli.main(["compare", "--format", "json", "--out", str(out)]) == 0
    assert json.loads(out.read_text()) == {"x": 1}
    fake.verify = lambda t: ["quebrou"]
    assert cli.main(["compare"]) == 1
    assert "quebrou" in capsys.readouterr().err
