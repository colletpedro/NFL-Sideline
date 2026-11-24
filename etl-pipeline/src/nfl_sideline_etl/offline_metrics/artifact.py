"""Pure batch calculation and audit; serialization publishes one validated directory."""
from collections import Counter, defaultdict
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from . import ADAPTER_VERSION, ARTIFACT_VERSION, DEFINITION_VERSION, POPULATION_VERSION
from .population import exclusion_reason
from .provenance import validate_metadata
from .statistics import accumulate
from .validation import CALENDAR_FIELDS, PBP_FIELDS, calendar_index, reconcile_raw

VERSIONS = dict(adapter=ADAPTER_VERSION, artifact=ARTIFACT_VERSION,
                definition=DEFINITION_VERSION, population=POPULATION_VERSION)
LIMITATIONS = ["Completeness UNKNOWN unless explicitly evidenced for these input bytes.",
               "AUDITABLE_SUBSET counts describe present content, not certified full-game volume.",
               "Absent rows do not identify bye, source delay or ingestion failure.",
               "Evidence assertions are supplied by the caller, not independently authenticated.",
               "EPA model version UNKNOWN unless explicitly evidenced; adapter version is separate.",
               "No certified temporal window, revision selection, pregame or POINT_IN_TIME guarantee."]


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def identity(value):
    return "sha256:" + hashlib.sha256(json_bytes(value)).hexdigest()


def calculate(calendar_rows, pbp_rows, inputs, metadata=None, *, seasons=None):
    games, calendar_duplicates = calendar_index(calendar_rows)
    if seasons is not None and any(g["season"] not in seasons for g in games.values()):
        raise ValueError("Input calendar contains a season outside explicit selection")
    unique, raw_n, duplicates = reconcile_raw(pbp_rows, games)
    proof = validate_metadata(metadata, inputs, games)
    inputs = sorted(inputs, key=lambda i: (i["kind"], i["sha256"]))
    for kind, rows in (("calendar", calendar_rows), ("pbp", pbp_rows)):
        if sum(i["raw_rows"] for i in inputs if i["kind"] == kind) != len(rows):
            raise ValueError(f"Input manifest raw count mismatch: {kind}")
    by_game = defaultdict(list)
    for play in unique:
        by_game[play["game_id"]].append(play)
    audits, stats = [], []
    calendar_revision = identity([i["source_revision_id"] for i in inputs if i["kind"] == "calendar"])
    pbp_revision = identity([i["source_revision_id"] for i in inputs if i["kind"] == "pbp"])
    for game_id, game in sorted(games.items()):
        plays = by_game[game_id]
        reasons = Counter()
        eligible = []
        outside_null_n = 0
        for play in plays:
            reason = exclusion_reason(play)
            if reason:
                reasons[reason] += 1
                if reason == "outside_pass_run" and (play["posteam"] is None or play["defteam"] is None):
                    outside_null_n += 1
            else:
                eligible.append(play)
        supplied = proof["games"].get(game_id, {})
        declared = supplied.get("completeness", "UNKNOWN")
        expected = supplied.get("expected_unique_rows")
        mismatch = expected is not None and expected != len(plays)
        completeness = "PARTIAL" if mismatch else declared
        has_observation = bool(plays) or (completeness == "COMPLETE" and expected == 0)
        scope = ("FULL_GAME_CONTENT" if completeness == "COMPLETE" else "AUDITABLE_SUBSET") if has_observation else "NO_SOURCE_OBSERVATION"
        status = ("COMPLETE" if completeness == "COMPLETE" else "PARTIAL") if has_observation else "SOURCE_UNKNOWN"
        content_id = identity(plays)
        revision = identity(dict(game=game, calendar_revision=calendar_revision, pbp_revision=pbp_revision,
                                content_id=content_id, provenance=supplied, versions=VERSIONS))
        audit = {**game, "coverage_revision_id": revision, "pbp_content_id": content_id,
                 "calendar_revision_id": calendar_revision, "pbp_revision_id": pbp_revision,
                 "raw_n": raw_n.get(game_id, 0), "unique_n": len(plays),
                 "duplicate_rows_ignored": duplicates.get(game_id, 0),
                 "calendar_duplicate_rows_ignored": calendar_duplicates.get(game_id, 0),
                 "excluded_n": sum(reasons.values()), "exclusions": dict(sorted(reasons.items())),
                 "outside_pass_run_null_teams_n": outside_null_n,
                 "eligible_content_n": len(eligible) if has_observation else None,
                 "unknown_filter_flags_n": reasons["unknown_filter_flags"],
                 "declared_completeness": declared, "completeness": completeness,
                 "expected_unique_rows": expected, "expected_raw_unique_count_matches": None if expected is None else not mismatch,
                 "scope": scope, "statistics_status": status,
                 "provenance": {"available_at": None, "event_upper_bound": None, "ingested_at": None, **supplied}}
        if audit["raw_n"] != audit["unique_n"] + audit["duplicate_rows_ignored"] or len(plays) != sum(reasons.values()) + len(eligible):
            raise ValueError("Raw/population reconciliation failed")
        audits.append(audit)
        if has_observation:
            for result in accumulate(game, eligible):
                stats.append({**game, **result, "coverage_revision_id": revision, "pbp_revision_id": pbp_revision,
                              "definition_version": DEFINITION_VERSION, "population_version": POPULATION_VERSION,
                              "scope": scope, "statistics_status": status, "completeness": completeness})
    manifest = {"artifactVersion": ARTIFACT_VERSION, "versions": VERSIONS, "mode": "OFFLINE_DRY_RUN",
                "inputs": inputs, "metadata": proof,
                "source_model_versions": {i["sha256"]: proof["sources"].get(i["sha256"], {}).get("source_model_version", {"value": "UNKNOWN", "evidence": None}) for i in inputs if i["kind"] == "pbp"},
                "replica_projection": {"calendar": list(CALENDAR_FIELDS), "pbp": list(PBP_FIELDS),
                    "normalization": "Numeric round-trip decimals, binary flags, phase/round; additional columns ignored. Drive and all raw contract fields participate, even outside pass/run."},
                "requested_seasons": list(seasons) if seasons is not None else None,
                "limitations": LIMITATIONS}
    reconciliation = {"calendar_games_n": len(games), "calendar_raw_n": len(calendar_rows),
                      "pbp_raw_n": len(pbp_rows), "pbp_unique_n": len(unique),
                      "duplicate_rows_ignored": sum(duplicates.values()),
                      "excluded_n": sum(a["excluded_n"] for a in audits),
                      "eligible_content_n": len(unique) - sum(a["excluded_n"] for a in audits),
                      "calendar_without_pbp": [a["game_id"] for a in audits if a["unique_n"] == 0],
                      "outside_pass_run_null_teams_n": sum(a["outside_pass_run_null_teams_n"] for a in audits),
                      "exclusions": dict(sorted(sum((Counter(a["exclusions"]) for a in audits), Counter()).items())),
                      "checks": {"raw_equals_unique_plus_duplicates": True, "unique_equals_eligible_plus_excluded": True,
                                 "general_equals_pass_plus_rush": True, "off_equals_opponent_def": True,
                                 "epa_partition": True}, "historical_availability_certified": False}
    result = {"manifest.json": manifest, "game-audit.json": audits, "statistics.json": stats,
              "reconciliation.json": reconciliation, "limitations.json": LIMITATIONS}
    manifest["calculation_id"] = identity(result)
    return result


def ensure_destination(output):
    output = Path(output)
    if "web-ui" in output.resolve().parts:
        parts = output.resolve().parts
        if any(parts[i:i+3] == ("web-ui", "public", "data") for i in range(len(parts)-2)):
            raise ValueError("Output under web-ui/public/data is forbidden")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Output already exists: {output}")
    return output


def rename_exclusive(source, destination):
    """Atomic no-clobber directory rename, including a competing empty directory."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        call = libc.renamex_np
        call.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rc = call(os.fsencode(source), os.fsencode(destination), 4)  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        call = libc.renameat2
        call.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rc = call(-100, os.fsencode(source), -100, os.fsencode(destination), 1)  # RENAME_NOREPLACE
    else:
        raise OSError("Atomic no-clobber publication requires Linux or macOS")
    if rc != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), str(destination))


def write_artifact(output, result):
    output = ensure_destination(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.pending-", dir=output.parent))
    try:
        for name, value in sorted(result.items()):
            (temporary / name).write_bytes(json_bytes(value))
        # A final marker records output hashes; never marks a partial write as done.
        (temporary / "COMPLETED.json").write_bytes(json_bytes({
            "artifactVersion": ARTIFACT_VERSION, "calculation_id": result["manifest.json"]["calculation_id"],
            "files": {name: hashlib.sha256((temporary / name).read_bytes()).hexdigest() for name in sorted(result)}}))
        rename_exclusive(temporary, output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
