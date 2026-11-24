"""CLI do hub de modelos. Subcomandos em ``COMMANDS``: cada um é uma função ``add_<nome>(sub)`` que registra
o parser e define ``func``. Outros módulos (backtest/register) acrescentam o seu com ``register_command``.

    cli.py acquire [--season N ...] [--refresh] [--no-refresh-current] [--allow-shrink] [--home DIR]
    cli.py migrate [--home DIR]       (layout antigo de raw/ -> endereçado por sha256; idempotente)
    cli.py build [--acquisition ID] [--allow-partial] [--home DIR]
    cli.py status [--home DIR]
    cli.py backtest|register|predict|card ep [--build ID] [--home DIR]   (modelos em models/)

Erros vão para stderr com exit 2.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
COMMANDS: dict[str, Callable] = {}


def register_command(name: str):
    """Decorador: ``@register_command("backtest") def add_backtest(sub): ...`` (recebe o subparsers)."""
    def deco(fn):
        COMMANDS[name] = fn
        return fn
    return deco


def _home(args) -> Path:
    from hubpaths import hub_home
    return Path(args.home) if args.home else hub_home()


def _add_home(p):
    p.add_argument("--home", help="home do hub (padrão: NFL_HUB_HOME ou o padrão do projeto)")


@register_command("acquire")
def add_acquire(sub):
    p = sub.add_parser("acquire", help="baixa PBP e schedules do nflverse")
    p.add_argument("--season", type=int, action="append", help="repetível; padrão 2011..corrente")
    p.add_argument("--refresh", action="store_true", help="rebaixa também temporadas passadas")
    p.add_argument("--no-refresh-current", action="store_true", help="não rebaixa a temporada corrente")
    p.add_argument("--allow-shrink", action="store_true",
                   help="aceita um refresh que reduz as linhas de uma temporada em mais de 1%%")
    _add_home(p)

    def run(args):
        import acquire
        t0 = time.time()
        acq_id = acquire.acquire(args.season, _home(args), refresh=args.refresh,
                                 refresh_current=not args.no_refresh_current, allow_shrink=args.allow_shrink)
        print(f"acquisition_id {acq_id} ({time.time() - t0:.1f}s)")
    p.set_defaults(func=run)


@register_command("migrate")
def add_migrate(sub):
    p = sub.add_parser("migrate", help="migra raw/ do layout antigo para o endereçado por sha256 (idempotente)")
    _add_home(p)

    def run(args):
        import acquire
        rep = acquire.migrate_legacy(_home(args))
        print(f"arquivos {rep['files']}")
        for old, new in rep["manifests"].items():
            print(f"manifesto {old} -> {new}")
        for old in rep["unrecoverable"]:
            print(f"irrecuperável {old}")
    p.set_defaults(func=run)


@register_command("build")
def add_build(sub):
    p = sub.add_parser("build", help="constrói o feature store a partir de uma aquisição")
    p.add_argument("--acquisition", help="id (ou prefixo); padrão: aquisição atual")
    p.add_argument("--allow-partial", action="store_true",
                   help="aceita um manifesto que não cobre 2011..temporada corrente de forma contínua")
    _add_home(p)

    def run(args):
        import features
        t0 = time.time()
        bid = features.build(args.acquisition, _home(args), allow_partial=args.allow_partial)
        print(f"build_id {bid} ({time.time() - t0:.1f}s)")
    p.set_defaults(func=run)


@register_command("status")
def add_status(sub):
    p = sub.add_parser("status", help="mostra aquisição atual, builds e semanas com PBP")
    _add_home(p)
    p.set_defaults(func=_status)


def _status(args):
    import acquire
    home = _home(args)
    print(f"home: {home}")
    try:
        man = acquire.resolve_acquisition(None, home)
    except acquire.AcquireError as exc:
        print(f"aquisição atual: nenhuma ({exc})")
        man = None
    if man:
        print(f"aquisição atual: {man['acquisition_id']} (criada {man['created_at_utc']})")
        for season, e in sorted(man["seasons"].items()):
            pbp, sch = e.get("pbp"), e.get("schedules")
            weeks = pbp["weeks_with_pbp"] if pbp else []
            span = f"{min(weeks)}..{max(weeks)}" if weeks else "-"
            print(f"  {season}: pbp {pbp['rows'] if pbp else 0} linhas, semanas {span}, "
                  f"última game_date {pbp['max_game_date'] if pbp else '-'}; schedules {sch['rows'] if sch else 0}")
    fdir = home / "features"
    builds = sorted(p.name for p in fdir.iterdir() if p.is_dir()) if fdir.exists() else []
    cur = None
    if (fdir / "current.json").exists():
        cur = json.loads((fdir / "current.json").read_text())["build_id"]
    print(f"builds: {len(builds)}")
    for b in builds:
        bm = json.loads((fdir / b / "manifest.json").read_text()) if (fdir / b / "manifest.json").exists() else {}
        rows = {t: v["rows"] for t, v in bm.get("tables", {}).items()}
        print(f"  {b}{' *' if b == cur else ''} acquisition {str(bm.get('acquisition_id'))[:12]} linhas {rows}")


def _model_command(name: str, help_: str, extra=None):
    """Registra `<name> <modelo>` (modelo = chave de `models.MODELS`); despacha para `cmd_<name>` do módulo."""
    @register_command(name)
    def add(sub):
        import importlib

        from models import MODELS
        p = sub.add_parser(name, help=help_)
        p.add_argument("model", choices=sorted(MODELS))
        p.add_argument("--build", help="id (ou prefixo) do build; padrão: o atual")
        _add_home(p)
        if extra:
            extra(p)
        p.set_defaults(func=lambda args: getattr(importlib.import_module(MODELS[args.model]), f"cmd_{name}")(args))
    return add


_model_command("backtest", "roda o backtest de um modelo (MLflow hub-<modelo>)",
               lambda p: p.add_argument("--force", action="store_true", help="reexecuta mesmo com config idêntica"))
_model_command("register", "ajusta o modelo selecionado em tudo e registra hub-<modelo>@champion",
               lambda p: p.add_argument("--run-id", help="pai do backtest (padrão: o mais recente que bateu os baselines)"))
_model_command("predict", "grava as previsões em lote do champion em HUB/predictions/<modelo>/<build>/")
def _card_args(p):
    p.add_argument("--out", required=True, help="arquivo de saída")
    p.add_argument("--run-id", help="pai do backtest (padrão: o mais recente do build atual)")


_model_command("card", "gera o cartão do modelo em Markdown", _card_args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for add in COMMANDS.values():
        add(sub)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:  # erros esperados e inesperados: mensagem curta em stderr
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
