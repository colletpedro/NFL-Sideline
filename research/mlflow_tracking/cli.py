"""CLI do rastreamento local. Subcomandos: `smoke`, `import {v1,v2,xint,all}`, `compare`, `register {m3,b2,all}`, `verify-models` e `provenance`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mlflow

import tracking


def smoke(home: Path | None = None) -> tuple[str, str]:
    """Cria UMA execução sintética com todas as tags obrigatórias. Devolve (run_id, tracking_uri)."""
    home = tracking.configure(home)
    exp_id = tracking.ensure_experiment("smoke", home)
    tags = tracking.base_tags(
        source_store="synthetic",
        source_freeze_sha256="0" * 64,
        dataset_sha256="0" * 64,
        design_sha256="0" * 64,
        seed=0,
        role="smoke",
        repo_path=Path(__file__).resolve().parent,
        importer_file=Path(__file__).resolve(),
    )
    with mlflow.start_run(experiment_id=exp_id, run_name="smoke") as run:
        mlflow.set_tags(tags)
        mlflow.log_param("purpose", "smoke")
        mlflow.log_metric("answer", 1.0)
    return run.info.run_id, tracking.tracking_uri(home)


TARGETS = ("v1", "v2", "xint")


def run_import(target: str, store, home, rebuild: bool) -> dict:
    if target == "v1":
        import import_v1 as m
        return m.import_v1(store, home, rebuild=rebuild)
    if target == "v2":
        import import_v2 as m
        return m.import_v2(store, home, rebuild=rebuild)
    import import_xint as m
    return m.import_xint(store, home, rebuild=rebuild)


def _print_result(target: str, res: dict) -> None:
    print(f"target={target}")
    print(f"parent_run_id={res['parent_run_id']}")
    print(f"created={str(res['created']).lower()}")
    for role, n in sorted(res["counts"].items()):
        print(f"{role}={n}")


def cmd_import(args) -> int:
    if args.what == "all" and args.store:
        print("erro: --store só vale para um alvo (v1, v2 ou xint), não para 'all'", file=sys.stderr)
        return 2
    home = Path(args.home) if args.home else None
    targets = TARGETS if args.what == "all" else (args.what,)
    for t in targets:
        try:
            res = run_import(t, Path(args.store) if args.store else None, home, args.rebuild)
        except Exception as exc:  # nunca mostrar traceback: ImporterError, RuntimeError, OSError, MlflowException...
            print(f"erro ({t}): {exc}", file=sys.stderr)
            for note in getattr(exc, "__notes__", []):
                print(note, file=sys.stderr)
            return 2
        _print_result(t, res)
    return 0


def cmd_compare(args) -> int:
    import compare

    table = compare.build_table(Path(args.home) if args.home else None)
    problems = compare.verify(table)
    text = compare.render_markdown(table) if args.format == "md" else json.dumps(table, indent=1, default=str)
    if args.out:
        Path(args.out).write_text(text)
    else:
        print(text)
    for p in problems:
        print(f"problema: {p}", file=sys.stderr)
    return 1 if problems else 0


def cmd_register(args) -> int:
    import registry

    try:
        res = registry.register(args.what, Path(args.home) if args.home else None)
    except (registry.RegistryError, RuntimeError, OSError) as exc:
        print(f"erro (register): {exc}", file=sys.stderr)
        for note in getattr(exc, "__notes__", []):
            print(note, file=sys.stderr)
        return 2
    for key, r in res.items():
        print(f"model={r['model']} version={r['version']} run_id={r['run_id']} created={str(r['created']).lower()}")
    return 0


def cmd_verify_models(args) -> int:
    import registry

    problems = registry.verify_models(Path(args.home) if args.home else None)
    print(json.dumps(registry.verify_models.report, indent=1))
    for p in problems:
        print(f"problema: {p}", file=sys.stderr)
    return 1 if problems else 0


def cmd_provenance(args) -> int:
    import provenance

    home = Path(args.home) if args.home else None
    try:
        if args.check:
            problems = provenance.check_provenance(args.out, home)
            for p in problems:
                print(f"problema: {p}", file=sys.stderr)
            return 1 if problems else 0
        path, changed = provenance.write_provenance(args.out, home)
    except (provenance.ProvenanceError, RuntimeError, OSError) as exc:
        print(f"erro (provenance): {exc}", file=sys.stderr)
        return 2
    print(f"path={path}")
    print(f"changed={str(changed).lower()}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    home_help = "padrão: NFL_MLFLOW_HOME ou M/editorial/local-artifacts/mlflow"
    s = sub.add_parser("smoke")
    s.add_argument("--home", default=None, help=home_help)
    imp = sub.add_parser("import", help="importa um store científico para o MLflow")
    imp.add_argument("what", choices=(*TARGETS, "all"))
    imp.add_argument("--store", default=None, help="padrão: o store canônico do alvo (não vale para 'all')")
    imp.add_argument("--home", default=None, help=home_help)
    imp.add_argument("--rebuild", action="store_true", help="apaga a importação existente do freeze e reimporta")
    c = sub.add_parser("compare", help="tabela de comparação lida do MLflow e conferência da seleção")
    c.add_argument("--home", default=None, help=home_help)
    c.add_argument("--format", choices=("md", "json"), default="md")
    c.add_argument("--out", default=None)
    r = sub.add_parser("register", help="registra M3 (qb-iw-m3) e/ou B2 (xint-ftn) com o alias champion")
    r.add_argument("what", choices=("m3", "b2", "all"))
    r.add_argument("--home", default=None, help=home_help)
    v = sub.add_parser("verify-models", help="confere os modelos champion contra stores e laboratórios (exit 1 se falhar)")
    v.add_argument("--home", default=None, help=home_help)
    pv = sub.add_parser("provenance", help="gera (ou confere com --check) web-ui/.../risk-outcomes/provenance.json")
    pv.add_argument("--home", default=None, help=home_help)
    pv.add_argument("--out", default=None, help="padrão: web-ui/broadcast-journey/risk-outcomes/provenance.json")
    pv.add_argument("--check", action="store_true", help="exit 1 se o arquivo diferir do que seria gerado")
    args = ap.parse_args(argv)
    if args.cmd == "import":
        return cmd_import(args)
    if args.cmd == "compare":
        return cmd_compare(args)
    if args.cmd == "register":
        return cmd_register(args)
    if args.cmd == "verify-models":
        return cmd_verify_models(args)
    if args.cmd == "provenance":
        return cmd_provenance(args)
    run_id, uri = smoke(Path(args.home) if args.home else None)
    print(f"run_id={run_id}")
    print(f"tracking_uri={uri}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
