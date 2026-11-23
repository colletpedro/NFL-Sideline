"""Manifesto de integridade dos stores: {"format": 2, "root", "entries": {rel: [size, mtime_ns, ctime_ns, ino]}}.

Com `--hash`, arquivos regulares ganham um quinto campo (sha256). `compare` usa todos os campos presentes
nos dois manifestos e recusa manifestos vazios, de formatos diferentes, ou um com hash e o outro sem (exit 2).

Symlinks: nunca são seguidos (nem arquivo nem diretório). A entrada é `[size, mtime_ns, ctime_ns, ino, None,
<alvo de os.readlink>]`; assim trocar o alvo do link é uma mudança, e o conteúdo do alvo só é coberto pela
entrada do próprio alvo quando ele está sob `--root`. Erros de leitura de diretório (permissão etc.) abortam
o snapshot em vez de produzir um manifesto parcial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

FORMAT = 2


class IntegrityError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root, with_hash: bool = False) -> dict:
    """Cobre arquivos e diretórios sob `root` (caminhos relativos, sem seguir symlinks)."""
    root = Path(root)
    if not root.is_dir():
        raise IntegrityError(f"--root não é um diretório: {root}")
    entries: dict[str, list] = {}

    def fail(exc: OSError) -> None:
        raise IntegrityError(f"erro ao percorrer {exc.filename}: {exc.strerror or exc}") from exc

    for dirpath, dirnames, filenames in os.walk(root, onerror=fail):
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            st = p.lstat()
            rec: list = [st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino]
            if stat.S_ISLNK(st.st_mode):
                rec += [None, os.readlink(p)]
            elif with_hash and stat.S_ISREG(st.st_mode):
                rec.append(_sha256(p))
            entries[p.relative_to(root).as_posix()] = rec
    return {"format": FORMAT, "root": str(root.resolve()), "entries": dict(sorted(entries.items()))}


def _check(m, name: str) -> dict:
    if not isinstance(m, dict) or not isinstance(m.get("entries"), dict):
        raise IntegrityError(f"manifesto '{name}' inválido (esperado formato {FORMAT})")
    if m.get("format") != FORMAT:
        raise IntegrityError(f"manifesto '{name}' tem formato {m.get('format')!r}, esperado {FORMAT}")
    if not m["entries"]:
        raise IntegrityError(f"manifesto '{name}' está vazio")
    return m["entries"]


def has_hash(entries: dict) -> bool:
    """True quando o manifesto foi gerado com `--hash` (algum arquivo regular tem sha256 no quinto campo)."""
    return any(len(v) > 4 and isinstance(v[4], str) for v in entries.values())


def compare(before: dict, after: dict) -> dict:
    b, a = _check(before, "before"), _check(after, "after")
    if before["format"] != after["format"]:
        raise IntegrityError("manifestos de formatos diferentes")
    if has_hash(b) != has_hash(a):
        raise IntegrityError("um manifesto tem hash (--hash) e o outro não; gere os dois do mesmo jeito")
    changed = []
    for k in set(b) & set(a):
        n = min(len(b[k]), len(a[k]))
        if list(b[k][:n]) != list(a[k][:n]):
            changed.append(k)
    return {"added": sorted(set(a) - set(b)), "removed": sorted(set(b) - set(a)), "changed": sorted(changed)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--root", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--hash", action="store_true", help="acrescenta sha256 por arquivo regular")
    c = sub.add_parser("compare")
    c.add_argument("--before", required=True)
    c.add_argument("--after", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "snapshot":
            root = Path(args.root)
            if not root.is_dir():
                raise IntegrityError(f"--root não é um diretório: {root}")
            if Path(args.out).resolve().is_relative_to(root.resolve()):
                raise IntegrityError("--out não pode ficar dentro de --root")
            snap = snapshot(root, args.hash)
            Path(args.out).write_text(json.dumps(snap, indent=1))
            print(f"{len(snap['entries'])} entradas")
            return 0
        diff = compare(json.loads(Path(args.before).read_text()), json.loads(Path(args.after).read_text()))
    except (IntegrityError, OSError, ValueError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(diff, indent=1))
    return 1 if any(diff.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
