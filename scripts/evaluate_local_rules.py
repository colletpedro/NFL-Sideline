#!/usr/bin/env python3
"""Offline local-rules evaluation, independent of Gemini attempts/ledgers.

freeze writes immutable code/contract/JAR digests. holdout verifies the seal before
opening any reserved context. Never reads model outputs or contacts a service.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "editorial/evaluations/2026-09-26/cases.json"
JAR = ROOT / "core-api/target/core-api-0.1.0.jar"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    files = list((ROOT / "core-api/src/main/java/com/nflsideline/coreapi/editorial").rglob("*.java"))
    files += list((ROOT / "core-api/src/test/java/com/nflsideline/coreapi/editorial").rglob("*.java"))
    files += [ROOT / "core-api/src/main/java/com/nflsideline/coreapi/CoreApiApplication.java",
              ROOT / "docs/analysis-claims-contract.md", ROOT / "docs/local-rules-editorial.md", Path(__file__), JAR, MANIFEST]
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(files)}


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["freeze", "development", "holdout"])
    parser.add_argument("output", type=Path, help="New directory for evaluation or new JSON file for freeze")
    parser.add_argument("--freeze", type=Path)
    args = parser.parse_args()
    selector_source = ROOT / "core-api/src/main/java/com/nflsideline/coreapi/editorial/local/LocalRuleSelector.java"
    if 'VERSION = "1.0.0"' not in selector_source.read_text():
        parser.error("Historical v1 protocol only; all six cases are now known regressions. Use scripts/compare_local_rules.py.")
    output = args.output.resolve()
    if "public" in output.parts:
        parser.error("Public output forbidden")
    if args.mode == "freeze":
        write(output, {"frozenAt": datetime.now(timezone.utc).isoformat(), "selector": "local-descriptive-rules",
                       "selectorVersion": "1.0.0", "contractVersion": 4, "files": sources(),
                       "policy": "No changes to frozen rules after opening reserved contexts in this delivery"})
        return
    seal = None
    if args.mode == "holdout":
        if args.freeze is None:
            parser.error("holdout requires --freeze")
        seal = json.loads(args.freeze.read_text())
        if seal["files"] != sources():
            parser.error("Frozen files differ; holdout refused before reading contexts")
    manifest = json.loads(MANIFEST.read_text())
    cases = [case for case in manifest["cases"] if case["split"] == args.mode]
    output.mkdir()  # Fail if an earlier attempt exists.
    java = str(Path(os.environ["JAVA_HOME"]) / "bin/java") if "JAVA_HOME" in os.environ else "java"
    write(output / "run.json", {"mode": "LOCAL_RULES_OFFLINE", "split": args.mode, "cases": cases,
                               "manifestSha256": digest(MANIFEST), "jarSha256": digest(JAR),
                               "freezeSha256": digest(args.freeze) if seal else None,
                               "startedAt": datetime.now(timezone.utc).isoformat(), "publicationApproved": False})
    results = []
    for case in cases:
        directory = output / case["gameId"]
        context = MANIFEST.parent / case["context"]
        code = subprocess.run([java, "-jar", str(JAR), "editorial-local", str(context), str(directory)], cwd=ROOT).returncode
        result = json.loads((directory / "result.json").read_text()) if (directory / "result.json").exists() else {}
        status = result.get("status", "FAILED")
        if result.get("gameId") != case["gameId"]:
            code, status = 1, "CONTEXT_GAME_MISMATCH"
        results.append({"gameId": case["gameId"], "exitCode": code, "status": status,
                        "validationFailures": result.get("validationFailures", [])})
    write(output / "results.json", {"results": results, "qualityEditorialProven": False,
                                   "geminiEvaluationEvidence": False})
    raise SystemExit(1 if any(item["exitCode"] for item in results) else 0)


if __name__ == "__main__":
    main()
