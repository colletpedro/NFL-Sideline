"""H1 - Aquisição: baixa PBP e schedules do nflverse (via nflreadpy) para o cache local do hub.

Layout (H-D10, cache endereçado por conteúdo): ``HUB/raw/{pbp,schedules}/season=YYYY/<sha256>.parquet`` (arquivo
nunca sobrescrito) e manifestos em ``HUB/acquisitions/<acquisition_id>.json`` (+ ``current.json``). Este é o único
módulo do hub que usa rede.

Protocolo de uma aquisição: (1) limpa temporários órfãos de execuções mortas; (2) baixa tudo para um diretório de
staging, validando colunas, contagens e encolhimento; (3) só então move cada arquivo para o nome definitivo
(``os.replace``; se já existe com o mesmo sha, reaproveita); (4) grava o manifesto e, por último, ``current.json``.
Falha em qualquer ponto antes de (4) deixa manifesto e ``current.json`` intactos. Como os arquivos antigos nunca
são sobrescritos, um manifesto antigo continua reconstruível depois de um refresh que mude os dados.

Regra de temporada (mar-dez = ano atual; jan/fev = ano anterior) reimplementada aqui em 5 linhas em vez de
importar ``etl-pipeline/src/.../seasons.py``: o hub é pesquisa isolada, sem dependência de caminho para a ETL
de produção. O teste ``test_current_season`` fixa o comportamento.

``acquisition_id`` = sha256 do JSON canônico do manifesto sem timestamps, versões de biblioteca nem
``migrated_from``: duas aquisições com os mesmos arquivos (mesmo sha256, linhas, colunas, semanas) têm o mesmo id.
O layout por sha mudou o formato (``FORMAT = 2``, ``path`` com o sha), logo os ids do layout antigo mudam na
migração; o manifesto migrado guarda o id antigo em ``migrated_from`` e ainda pode ser resolvido por ele.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import polars as pl

FIRST_SEASON = 2011
FORMAT = 2
#: Um refresh que reduza as linhas de uma temporada em mais que isto falha, salvo ``allow_shrink``.
SHRINK_TOLERANCE = 0.01
KINDS = ("pbp", "schedules")

#: Colunas mínimas exigidas pelo features.py (conferidas na aquisição; faltou uma -> erro claro).
REQUIRED_PBP_COLUMNS = (
    "game_id", "play_id", "season", "week", "season_type", "game_date", "posteam", "defteam", "home_team",
    "away_team", "qtr", "down", "ydstogo", "yardline_100", "half_seconds_remaining", "game_seconds_remaining",
    "goal_to_go", "score_differential", "posteam_timeouts_remaining", "defteam_timeouts_remaining", "roof",
    "play_type", "pass", "rush", "epa", "ep", "wp", "no_score_prob", "opp_fg_prob", "opp_safety_prob",
    "opp_td_prob", "fg_prob", "safety_prob", "td_prob", "touchdown", "td_team", "field_goal_result", "safety",
    "two_point_attempt", "success", "posteam_score", "posteam_score_post",
)
REQUIRED_SCHEDULE_COLUMNS = (
    "game_id", "season", "week", "game_type", "gameday", "gametime", "home_team", "away_team", "home_score",
    "away_score", "result", "total", "spread_line", "total_line", "home_moneyline", "away_moneyline", "roof",
    "surface", "temp", "wind", "div_game", "home_rest", "away_rest", "location",
)
REQUIRED = {"pbp": REQUIRED_PBP_COLUMNS, "schedules": REQUIRED_SCHEDULE_COLUMNS}

Loader = Callable[[str, int], object]


class AcquireError(RuntimeError):
    """Falha de aquisição (rede, coluna ausente, fonte vazia fora do caso tolerado)."""


class SourceNotPublished(AcquireError):
    """A fonte ainda não foi publicada (ex.: HTTP 404). Tolerado só para PBP da temporada corrente/futura."""


def current_season(today: date | None = None) -> int:
    """Temporada NFL corrente: mar-dez = ano atual, jan/fev = ano anterior."""
    d = today or date.today()
    return d.year if d.month >= 3 else d.year - 1


def default_seasons(today: date | None = None) -> list[int]:
    return list(range(FIRST_SEASON, current_season(today) + 1))


def _http_status(exc: BaseException) -> int | None:
    pending, seen = [exc], set()
    while pending:
        cur = pending.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        code = getattr(getattr(cur, "response", None), "status_code", None)
        if isinstance(code, int):
            return code
        pending += [e for e in (cur.__cause__, cur.__context__) if e is not None]
    return None


def _to_polars(df: object) -> pl.DataFrame:
    if isinstance(df, pl.DataFrame):
        return df
    return pl.from_pandas(df)  # type: ignore[arg-type]


def nflreadpy_loader(kind: str, season: int) -> pl.DataFrame:
    """Loader padrão: ``nflreadpy.load_pbp/load_schedules`` convertido para Polars. 404 -> SourceNotPublished."""
    import nflreadpy as nfl
    fn = nfl.load_pbp if kind == "pbp" else nfl.load_schedules
    try:
        return _to_polars(fn(seasons=[season]))
    except ConnectionError as exc:
        if _http_status(exc) == 404:
            raise SourceNotPublished(f"{kind} {season} ainda não publicado") from exc
        raise


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _check_columns(kind: str, season: int, columns: list[str]) -> None:
    missing = [c for c in REQUIRED[kind] if c not in columns]
    if missing:
        raise AcquireError(f"{kind} {season}: colunas exigidas ausentes: {', '.join(missing)}")


def _rel(kind: str, season: int, sha: str) -> str:
    return f"raw/{kind}/season={season}/{sha}.parquet"


def _describe(path: Path, kind: str, season: int, fetched: str) -> dict:
    """Entrada do manifesto para um arquivo já no disco (``path`` pode ser de staging: o ``path`` do manifesto
    é o endereço definitivo, derivado do sha256)."""
    cols = list(pl.read_parquet_schema(path))
    _check_columns(kind, season, cols)
    sha = sha256_file(path)
    entry = {"path": _rel(kind, season, sha), "sha256": sha, "bytes": path.stat().st_size,
             "rows": pl.scan_parquet(path).select(pl.len()).collect().item(), "columns": cols,
             "fetched_at_utc": fetched}
    if kind == "pbp":
        meta = pl.read_parquet(path, columns=["game_date", "week"])
        entry["max_game_date"] = meta["game_date"].drop_nulls().max()
        entry["weeks_with_pbp"] = sorted(int(w) for w in meta["week"].drop_nulls().unique().to_list())
    return entry


# ---------------------------------------------------------------- temporários órfãos
def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _tmp_pid(name: str) -> int | None:
    """pid embutido em ``.<nome>.tmp-<pid>`` ou ``.staging-<pid>-<token>``; ``None`` se não for temporário."""
    for marker in (".tmp-", ".staging-"):
        if marker in name and name.startswith("."):
            tail = name.split(marker, 1)[1].split("-", 1)[0]
            return int(tail) if tail.isdigit() else None
    return None


def clean_orphans(root: Path) -> list[str]:
    """Remove temporários (arquivos ``.x.tmp-PID`` e diretórios ``.staging-PID-*``/``.x.tmp-PID``) de execuções
    anteriores cujo processo já não existe. Devolve os nomes removidos."""
    removed = []
    if not Path(root).exists():
        return removed
    for p in sorted(Path(root).rglob(".*")):
        pid = _tmp_pid(p.name)
        if pid is None or pid_alive(pid) or not p.exists():
            continue
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        removed.append(str(p.relative_to(root)))
    return removed


# ---------------------------------------------------------------- manifestos
def _manifests(home: Path) -> list[dict]:
    """Manifestos legíveis do home, do mais antigo ao mais novo (``created_at_utc``)."""
    out = []
    for p in (Path(home) / "acquisitions").glob("*.json"):
        if p.stem == "current":
            continue
        try:
            out.append(json.loads(p.read_text()))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda m: (m.get("created_at_utc", ""), m.get("acquisition_id", "")))


def _known_entries(home: Path) -> dict[tuple[str, int], dict]:
    """Última entrada conhecida por (tipo, temporada), de todos os manifestos de formato atual cujo arquivo existe
    e confere o sha256; o manifesto atual tem prioridade."""
    cur = None
    try:
        cur = json.loads((Path(home) / "acquisitions" / "current.json").read_text())["acquisition_id"]
    except (OSError, ValueError, KeyError):
        pass
    mans = [m for m in _manifests(home) if m.get("format") == FORMAT]
    mans.sort(key=lambda m: m.get("acquisition_id") == cur)  # estável: o atual por último
    known: dict[tuple[str, int], dict] = {}
    for m in mans:
        for season, entries in m["seasons"].items():
            for kind, e in entries.items():
                if e and (Path(home) / e["path"]).exists():
                    known[(kind, int(season))] = e
    return known


def compute_acquisition_id(manifest: dict) -> str:
    """sha256 canônico do conteúdo, sem timestamps nem versões de biblioteca."""
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items()
                    if k not in ("created_at_utc", "fetched_at_utc", "acquisition_id", "nflreadpy_version",
                                 "polars_version", "migrated_from")}
        return o
    return hashlib.sha256(canonical(strip(manifest))).hexdigest()


def acquire(seasons: list[int] | None, home: Path, refresh: bool = False, refresh_current: bool = True,
            loader: Loader | None = None, today: date | None = None, allow_shrink: bool = False) -> str:
    """Baixa o que falta (ou tudo, com ``refresh``), grava o manifesto e devolve o ``acquisition_id``.

    - Temporada passada com arquivo presente: reutilizada (a menos que ``refresh``).
    - Temporada corrente: rebaixada por padrão (``refresh_current``).
    - PBP **ou schedules** vazio/404 da temporada corrente ou futura: tolerado (mantém a entrada existente, ou
      fica sem a tabela). Para temporada passada é fatal. Qualquer outro erro é fatal.
    - Refresh que reduz as linhas de uma tabela em mais de 1% falha, salvo ``allow_shrink``.
    - Nada vai para o nome definitivo, nem para o manifesto, antes de TODOS os downloads validarem.
    """
    home = Path(home)
    loader = loader or nflreadpy_loader
    cur = current_season(today)
    seasons = sorted(set(seasons)) if seasons else default_seasons(today)
    if min(seasons) < 1999:
        raise AcquireError(f"temporada inválida: {min(seasons)}")
    migrate_legacy(home)
    clean_orphans(home / "raw")
    clean_orphans(home / "acquisitions")
    known = {k: e for k, e in _known_entries(home).items()
             if sha256_file(home / e["path"]) == e["sha256"]}  # arquivo adulterado = ausente
    staging = home / "raw" / f".staging-{os.getpid()}-{secrets.token_hex(4)}"
    staging.mkdir(parents=True)
    try:
        result: dict[str, dict] = {}
        staged: list[tuple[Path, dict]] = []
        for season in seasons:
            entries: dict[str, dict | None] = {}
            for kind in KINDS:
                prev = known.get((kind, season))
                if not (refresh or prev is None or (season >= cur and refresh_current)):
                    entries[kind] = prev
                    continue
                try:
                    df = _to_polars(loader(kind, season))
                    if df.height == 0:
                        raise SourceNotPublished(f"{kind} {season} vazio")
                except SourceNotPublished as exc:
                    if season >= cur:
                        entries[kind] = prev  # tolerado: mantém o existente, se houver
                        continue
                    raise AcquireError(f"{kind} {season}: {exc}") from exc
                except AcquireError:
                    raise
                except Exception as exc:  # rede, auth, 5xx, esquema: fatal
                    raise AcquireError(f"{kind} {season}: falha ao baixar ({type(exc).__name__}: {exc})") from exc
                _check_columns(kind, season, df.columns)
                if prev and not allow_shrink and df.height < prev["rows"] * (1 - SHRINK_TOLERANCE):
                    raise AcquireError(
                        f"{kind} {season}: {df.height} linhas < {prev['rows']} do manifesto anterior "
                        f"(queda > {SHRINK_TOLERANCE:.0%}); confira a fonte ou use --allow-shrink")
                tmp = staging / f"{kind}-{season}.parquet"
                df.write_parquet(tmp, compression="zstd")
                del df
                entry = _describe(tmp, kind, season, _now())
                if prev and prev["sha256"] == entry["sha256"]:
                    entries[kind] = prev  # mesmos bytes: preserva a data original
                else:
                    entries[kind] = entry
                    staged.append((tmp, entry))
            result[str(season)] = entries
        for season, entries in _inherited(home, known, set(seasons)).items():  # M-1: não perde as demais temporadas
            result[str(season)] = entries
        for tmp, entry in staged:  # tudo validado: agora sim, nomes definitivos
            dest = home / entry["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and sha256_file(dest) == entry["sha256"]:
                tmp.unlink()
            else:
                os.replace(tmp, dest)
        manifest = {"format": FORMAT, "created_at_utc": _now(), "nflreadpy_version": _version("nflreadpy"),
                    "polars_version": pl.__version__, "seasons": result}
        acq_id = compute_acquisition_id(manifest)
        manifest["acquisition_id"] = acq_id
        _write_manifest(home, manifest)
        _set_current(home, acq_id)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return acq_id


def _inherited(home: Path, known: dict, requested: set) -> dict[int, dict]:
    """Entradas do manifesto ATUAL para as temporadas NÃO pedidas (M-1): ``acquire --season N`` não pode fazer o
    ``current.json`` apontar para um manifesto só com N. Herda os mesmos arquivos (mesmo sha256), só quando o arquivo
    existe e confere (``known`` já foi verificado); entrada ``None`` continua ``None``. Sem manifesto atual, nada."""
    try:
        cur = resolve_acquisition(None, home)
    except AcquireError:
        return {}
    out: dict[int, dict] = {}
    for season, entries in cur["seasons"].items():
        if int(season) in requested:
            continue
        kept = {}
        for kind, e in entries.items():
            ok = e is None or (known.get((kind, int(season))) or {}).get("sha256") == e["sha256"]
            if ok:
                kept[kind] = e
        out[int(season)] = kept
    return out


def _write_manifest(home: Path, manifest: dict) -> None:
    target = Path(home) / "acquisitions" / f"{manifest['acquisition_id']}.json"
    if not target.exists():
        _atomic_write_bytes(target, json.dumps(manifest, indent=2, sort_keys=True).encode())


def _set_current(home: Path, acq_id: str) -> None:
    _atomic_write_bytes(Path(home) / "acquisitions" / "current.json",
                        json.dumps({"acquisition_id": acq_id, "updated_at_utc": _now()}, indent=2).encode())


# ---------------------------------------------------------------- migração do layout antigo
def _link_or_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dest)
    except OSError:
        tmp = dest.with_name(f".{dest.name}.tmp-{os.getpid()}")
        try:
            shutil.copy2(src, tmp)
            os.replace(tmp, dest)
        finally:
            tmp.unlink(missing_ok=True)


def migrate_legacy(home: Path) -> dict:
    """Migra o layout antigo (``raw/<tipo>/season=Y/<tipo>.parquet``, manifesto ``format`` 1) para o endereçado por
    sha256. Idempotente: sem layout antigo, não faz nada.

    Cada arquivo antigo ganha um hardlink no endereço do seu sha256; cada manifesto antigo cujos arquivos todos
    existem é regravado no formato atual (o ``acquisition_id`` MUDA, pois o ``path`` e o ``format`` fazem parte do
    conteúdo; o id antigo fica em ``migrated_from``) e o antigo é removido; ``current.json`` acompanha. Manifesto
    antigo com arquivo ausente/alterado fica intacto e é listado em ``unrecoverable``. Só no fim os arquivos
    antigos são apagados. Devolve ``{"files": n, "manifests": {id_antigo: id_novo}, "unrecoverable": [ids]}``."""
    home = Path(home)
    report: dict = {"files": 0, "manifests": {}, "unrecoverable": []}
    legacy = [(kind, p) for kind in KINDS for p in sorted((home / "raw").glob(f"{kind}/season=*/{kind}.parquet"))]
    old_manifests = [m for m in _manifests(home) if m.get("format") == 1]
    if not legacy and not old_manifests:
        return report
    for kind, p in legacy:
        season = int(p.parent.name.split("=")[1])
        dest = home / _rel(kind, season, sha256_file(p))
        if not dest.exists():
            _link_or_copy(p, dest)
        report["files"] += 1
    cur = None
    try:
        cur = json.loads((home / "acquisitions" / "current.json").read_text())["acquisition_id"]
    except (OSError, ValueError, KeyError):
        pass
    for m in old_manifests:
        old_id = m["acquisition_id"]
        new_seasons, ok = {}, True
        for season, entries in m["seasons"].items():
            new_entries = {}
            for kind, e in entries.items():
                if e is None:
                    new_entries[kind] = None
                    continue
                rel = _rel(kind, int(season), e["sha256"])
                if not (home / rel).exists():
                    ok = False
                new_entries[kind] = {**e, "path": rel}
            new_seasons[season] = new_entries
        if not ok:
            report["unrecoverable"].append(old_id)
            continue
        new = {**{k: v for k, v in m.items() if k != "acquisition_id"}, "format": FORMAT, "seasons": new_seasons,
               "migrated_from": old_id}
        new_id = compute_acquisition_id(new)
        new["acquisition_id"] = new_id
        _write_manifest(home, new)
        if cur == old_id:
            _set_current(home, new_id)
        (home / "acquisitions" / f"{old_id}.json").unlink(missing_ok=True)
        report["manifests"][old_id] = new_id
    for _, p in legacy:
        p.unlink(missing_ok=True)
    return report


def _version(pkg: str) -> str | None:
    try:
        from importlib.metadata import version
        return version(pkg)
    except Exception:
        return None


def resolve_acquisition(acquisition_id: str | None, home: Path) -> dict:
    """Carrega um manifesto (id completo, prefixo único, id antigo de um manifesto migrado, ou o atual)."""
    acq_dir = Path(home) / "acquisitions"
    if acquisition_id is None:
        cur = acq_dir / "current.json"
        if not cur.exists():
            raise AcquireError("nenhuma aquisição atual; rode `cli.py acquire`")
        acquisition_id = json.loads(cur.read_text())["acquisition_id"]
    mans = _manifests(home)
    matches = [m for m in mans if m["acquisition_id"].startswith(acquisition_id)]
    if not matches:
        matches = [m for m in mans if str(m.get("migrated_from", "")).startswith(acquisition_id)]
    if len(matches) != 1:
        raise AcquireError(f"aquisição {acquisition_id!r}: {len(matches)} correspondências")
    if matches[0].get("format") != FORMAT:
        raise AcquireError(f"aquisição {acquisition_id!r} está no layout antigo; rode `cli.py migrate`")
    return matches[0]
