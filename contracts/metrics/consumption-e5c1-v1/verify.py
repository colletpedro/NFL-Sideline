"""Offline fixture contract checker; no acquisition, revision selection or consumer API."""
import copy
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
BASE = "fed166d1682a818b0cca8dd11325ff23ea672c07"
PREFIX = "contracts/metrics/consumption-e5c1-v1/"
FAMILIES = ("volume", "frequency", "epa", "successRate")
NUMERIC_OPS = ("align", "difference", "sort")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(name):
    return json.loads((PACKAGE / name).read_text())


def semantic_identity(document):
    semantic = {k: v for k, v in document.items()
                if k not in {"observationId", "derivedAt", "presentation"}}
    encoded = json.dumps(semantic, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def validate_document(d, check_identity=True):
    # Structure and exact arithmetic of this projection, not authenticity/recálculo.
    Draft202012Validator(load("observation.schema.json")).validate(d)
    for instant in (d["derivedAt"], d["guarantees"]["temporal"]["cutoff"],
                    d["guarantees"]["temporal"]["targetKickoff"]):
        if instant is not None:
            datetime.fromisoformat(instant)
    require(d["members"] == sorted(d["members"], key=lambda m: m["gameId"]), "MEMBER_ORDER")
    require(len({m["gameId"] for m in d["members"]}) == len(d["members"]), "AMBIGUOUS_GAME_SELECTION")
    present = [m for m in d["members"] if m["sourceState"] == "PRESENT"]
    for m in d["members"]:
        if m["sourceState"] == "ABSENT":
            require(m["statistics"] is None and not m["sourceRevisionIds"]
                    and not m["archiveReceiptIds"] and m["calculationId"] is None
                    and m["artifactId"] is None and m["completeness"] == "UNKNOWN", "ABSENT_IS_NOT_ZERO")
        else:
            require(m["statistics"] is not None and m["sourceRevisionIds"]
                    and m["calculationId"] and m["artifactId"] and m["archiveReceiptIds"], "MISSING_LINEAGE")
        require(m["week"] in d["request"]["period"]["weeks"], "MEMBER_OUTSIDE_REQUEST")
        require((d["request"]["phase"] == "REG" and m["round"] == "REG") or
                (d["request"]["phase"] == "POST" and m["round"] != "REG"), "ROUND_PHASE_MISMATCH")
    for stats in [m["statistics"] for m in present] + ([d["totals"]] if d["totals"] else []):
        require(stats["eligibleN"] == stats["epaN"] + stats["epaMissingN"] + stats["epaNonfiniteN"], "COUNT_PARTITION")
        require(stats["successN"] <= stats["epaN"], "SUCCESS_COUNT")
        require((stats["epaSum"] is None) == (stats["epaN"] == 0), "NULL_SUM_SEMANTICS")
        require(stats["generalEligibleN"] >= stats["eligibleN"], "GENERAL_DENOMINATOR")
        if d["subject"]["foundation"] == "general":
            require(stats["generalEligibleN"] == stats["eligibleN"], "GENERAL_EQUALITY")
    require((d["totals"] is None) == (not present), "ABSENCE_TOTALS")
    if present:
        for key in d["totals"]:
            if key == "epaSum":
                sums = [Fraction(Decimal(m["statistics"][key])) for m in present
                        if m["statistics"][key] is not None]
                require((d["totals"][key] is None) == (not sums), "TOTAL_NULL_SUM")
                if sums:
                    require(Fraction(Decimal(d["totals"][key])) == sum(sums), "EXACT_SUM")
            else:
                require(d["totals"][key] == sum(m["statistics"][key] for m in present), "EXACT_COUNT")
    expected_values = dict.fromkeys(FAMILIES)
    if d["totals"] is not None:
        t = d["totals"]
        expected_values["volume"] = {"numerator": str(t["eligibleN"]), "denominator": 1}
        if t["epaN"]:
            expected_values["epa"] = {"numerator": t["epaSum"], "denominator": t["epaN"]}
            expected_values["successRate"] = {"numerator": str(t["successN"]), "denominator": t["epaN"]}
        if t["generalEligibleN"] and d["subject"]["foundation"] != "general":
            expected_values["frequency"] = {"numerator": str(t["eligibleN"]), "denominator": t["generalEligibleN"]}
    require(d["values"] == expected_values, "EXACT_RATIOS")
    ids = sorted(m["gameId"] for m in present)
    require(d["observed"]["includedGameIds"] == ids, "INCLUDED_GAMES")
    require(d["observed"]["actualWeeks"] == sorted({m["week"] for m in present}), "OBSERVED_WEEKS")
    for fam in FAMILIES:
        used = sorted(m["gameId"] for m in present if
                      (fam == "volume" or
                       (fam in {"epa", "successRate"} and m["statistics"]["epaN"] > 0) or
                       (fam == "frequency" and d["subject"]["foundation"] != "general"
                        and m["statistics"]["generalEligibleN"] > 0)))
        require(d["observed"]["metricUsedGameIds"][fam] == used, "METRIC_USED_GAMES")
    cov = d["guarantees"]["coverage"]
    if cov["state"] in {"UNKNOWN", "CONFLICT"}:
        require(all(cov[k] is None for k in ("expectedGameIds", "expectedCount", "coverageRatio")), "UNKNOWN_EXPECTATION")
    else:
        require(cov["expectedGameIds"] is not None and cov["expectedCount"] == len(cov["expectedGameIds"]), "EXPECTED_COUNT")
        require(set(ids) <= set(cov["expectedGameIds"]), "EXPECTED_IDS")
        ratio = {"numerator": str(len(ids)), "denominator": cov["expectedCount"]} if cov["expectedCount"] else None
        require(cov["coverageRatio"] == ratio, "COVERAGE_RATIO")
        require((cov["state"] == "KNOWN") == (len(ids) == cov["expectedCount"]), "COVERAGE_STATE")
    if cov["expectedGameIds"] is not None:
        require(set(cov["expectedGameIds"]) == {m["gameId"] for m in d["members"]}, "MISSING_GAP_MEMBER")
    comp = d["guarantees"]["completeness"]
    states = {m["completeness"] for m in d["members"]}
    state = next((s for s in ("CONFLICT", "PARTIAL", "UNKNOWN", "COMPLETE") if s in states), "UNKNOWN")
    require(comp["state"] == state, "COMPLETENESS_NOT_PROMOTED")
    model = d["guarantees"]["compatibility"]["epaModel"]
    require((model["id"] is not None) == (model["state"] == "KNOWN"), "MODEL_UNKNOWN")
    sources = d["guarantees"]["compatibility"]["sourceModels"]
    require([m["sourceRevisionId"] for m in sources] == sorted({src for member in present for src in member["sourceRevisionIds"]}), "SOURCE_MODEL_MAP")
    for source in sources:
        require((source["modelId"] is not None) == (source["state"] == "KNOWN"), "SOURCE_MODEL_UNKNOWN")
        if source["state"] == "KNOWN":
            require(source["evidenceIds"], "SOURCE_MODEL_UNPROVEN")
    if d["values"]["epa"] is not None:
        require(len({m["modelId"] for m in sources if m["state"] == "KNOWN"}) <= 1, "MIXED_EPA_MODELS")
        require(not ({m["state"] for m in sources} >= {"KNOWN", "UNKNOWN"}), "MIXED_KNOWN_UNKNOWN_MODELS")
    if model["state"] == "KNOWN":
        require(sources and all(x["state"] == "KNOWN" and x["modelId"] == model["id"] for x in sources), "SOURCE_MODEL_CONFLICT")
    if d["guarantees"]["integrity"]["state"] != "RECONCILED":
        require(d["totals"] is None and all(v is None for v in d["values"].values()), "NUMERIC_INTEGRITY_UNPROVEN")
    for dim in d["guarantees"].values():
        require(dim["evidenceIds"] or dim["state"] == "UNKNOWN", "UNSUPPORTED_GUARANTEE")
        if dim["state"] not in {"RECONCILED", "KNOWN", "COMPLETE", "KNOWN_AT_CUTOFF"}:
            require(dim["reasonCodes"], "MISSING_REASON")
    for key in ("actualWeeks", "includedGameIds"):
        require(d["observed"][key] == sorted(d["observed"][key]), "CANONICAL_SET")
    require(d["request"]["period"]["weeks"] == sorted(d["request"]["period"]["weeks"]), "CANONICAL_PERIOD")
    if check_identity:
        require(d["observationId"] == semantic_identity(d), "SEMANTIC_ID")


# Finite fixture witnesses for the published acceptance table. No revision
# selection, real observation construction, matchup or editorial computation.
def check_case(case, documents):
    a, b = [documents[r] for r in case["observations"]]
    w = set(case["witnesses"])
    require(len(w) == len(case["witnesses"]), "DUPLICATE_WITNESS")
    t = [d["totals"] for d in (a, b)]
    basic = (a["definition"] == b["definition"] and
             {k:v for k,v in a["subject"].items() if k != "team"} ==
             {k:v for k,v in b["subject"].items() if k != "team"} and
             {k:v for k,v in a["request"].items() if k not in {"calendarSourceSetId", "selectionManifestId"}} ==
             {k:v for k,v in b["request"].items() if k not in {"calendarSourceSetId", "selectionManifestId"}} and
             all(d["guarantees"]["compatibility"]["state"] == "KNOWN" for d in (a, b)) and
             a["guarantees"]["temporal"]["cutoff"] == b["guarantees"]["temporal"]["cutoff"])
    # Finite pregame witnesses also check the target and request boundaries;
    # KNOWN_AT_CUTOFF alone is not a witness for exclusion of the target.
    temporal = [d["guarantees"]["temporal"] for d in (a, b)]
    pregame_request = (
        all(x["cutoff"] is not None and x["targetKickoff"] is not None
            and x["targetGameId"] is not None
            and x["cutoff"] <= x["targetKickoff"] for x in temporal)
        and temporal[0]["targetGameId"] == temporal[1]["targetGameId"]
        and temporal[0]["targetKickoff"] == temporal[1]["targetKickoff"]
        and all(d["guarantees"]["temporal"]["targetGameId"] not in
                {m["gameId"] for m in d["members"]} for d in (a, b)))
    actual = {
        "DISPLAY": all(d["guarantees"]["integrity"]["state"] == "RECONCILED" and d["totals"] is not None for d in (a,b)),
        "BASIC_MATCH": basic,
        "SAMPLE_SELECTION": all(x is None or x["unknownFilterFlagsN"] == 0 for x in t),
        "FREQUENCY_DENOMINATOR": all(x is not None and x["generalEligibleN"] > 0 for x in t),
        "EPA_DENOMINATOR": all(x is not None and x["epaN"] > 0 for x in t),
        "EPA_COMPLETE": all(x is not None and x["epaMissingN"] == x["epaNonfiniteN"] == x["unknownFilterFlagsN"] == 0 for x in t),
        "FULL_PERIOD": all(d["guarantees"]["coverage"]["state"] == "KNOWN" and d["guarantees"]["completeness"]["state"] == "COMPLETE" for d in (a,b)),
        "MODEL_MATCH": all(d["guarantees"]["compatibility"]["epaModel"]["state"] == "KNOWN" for d in (a,b)) and a["guarantees"]["compatibility"]["epaModel"] == b["guarantees"]["compatibility"]["epaModel"],
        "PIT_CHAIN": all(d["guarantees"]["temporal"]["state"] == "KNOWN_AT_CUTOFF" for d in (a,b)),
        "PREGAME_CUTOFF": pregame_request}
    require(w == {k for k,v in actual.items() if v}, "WITNESS_MISMATCH: " + case["id"])
    base = {"DISPLAY", "BASIC_MATCH", "SAMPLE_SELECTION"}
    requirements = {"volume": base, "frequency": base | {"FREQUENCY_DENOMINATOR"},
                    "epa": base | {"EPA_DENOMINATOR", "EPA_COMPLETE", "FULL_PERIOD", "MODEL_MATCH"},
                    "successRate": base | {"EPA_DENOMINATOR", "EPA_COMPLETE", "FULL_PERIOD", "MODEL_MATCH"}}
    frozen = copy.deepcopy((a,b))
    for fam in FAMILIES:
        r = case["expected"][fam]
        require((r["point"]["decision"] == "ALLOW") == (a["values"][fam] is not None), "POINT_EXPECTATION")
        comparable = requirements[fam] <= w
        for op in NUMERIC_OPS:
            require((r[op]["decision"] == "ALLOW") == comparable, "OPERATION_EXPECTATION")
            require(r[op]["missingRequirements"] == sorted(requirements[fam] - w), "MISSING_REQUIREMENTS")
            if comparable:
                require(r[op]["scope"] == ("REQUESTED_POPULATION" if "FULL_PERIOD" in w else "OBSERVED_SAMPLE"), "SCOPE_EXPECTATION")
        require((r["highlight"]["decision"] == "ALLOW") == (comparable and fam in {"epa","successRate"}), "QUALITY_DIRECTION")
        require(r["superiority"]["decision"] == "REFUSE", "NO_EDITORIAL_VALIDATION")
        required_pregame = requirements[fam] | {"FULL_PERIOD", "PIT_CHAIN", "PREGAME_CUTOFF"}
        require(r["pregameData"]["missingRequirements"] == sorted(required_pregame - w), "PREGAME_MISSING_REQUIREMENTS")
        require((r["pregameData"]["decision"] == "ALLOW") == (required_pregame <= w), "PREGAME_EXPECTATION")
        require(r["metricId"] == "def." + ("success_rate" if fam == "successRate" else fam) + ".classified_pass", "METRIC_ID")
        for op, result in r.items():
            if op == "metricId":
                continue
            require(result["decision"] in {"ALLOW", "REFUSE"}, "DECISION_ENUM")
            require(bool(result["reasonCodes"]) == (result["decision"] == "REFUSE"), "DECISION_REASON")
    require((a,b) == frozen, "REFUSAL_PRESERVES_VALUES_AND_LINEAGE")


def patched_invalid(case, documents):
    d = copy.deepcopy(documents[case["base"]])
    cursor = d
    for key in case["path"][:-1]:
        cursor = cursor[key]
    cursor[case["path"][-1]] = case["value"]
    d["observationId"] = semantic_identity(d)
    return d


def check_preservation():
    # All tracked paths outside this new package must equal the exact task base.
    changed = subprocess.check_output(["git", "diff", "--name-only", BASE], cwd=ROOT).decode().splitlines()
    require(all(path.startswith(PREFIX) for path in changed), "PROTECTED_TRACKED_PATH_CHANGED")
    subprocess.run(["git", "diff", "--check", BASE], cwd=ROOT, check=True)
    return {"base": BASE, "outsidePackageChanged": [], "diffCheck": "PASS"}


def main():
    fixtures = load("examples.json")
    Draft202012Validator.check_schema(load("observation.schema.json"))
    for d in fixtures["observations"].values():
        validate_document(d)
    for c in fixtures["cases"]:
        check_case(c, fixtures["observations"])
    for c in fixtures["invalid"]:
        try:
            validate_document(patched_invalid(c, fixtures["observations"]))
        except ValueError:
            require(c["failure"] == "SEMANTIC", "WRONG_FAILURE_CLASS")
        except Exception as exc:
            from jsonschema.exceptions import ValidationError
            require(isinstance(exc, ValidationError) and c["failure"] == "SCHEMA", "WRONG_SCHEMA_FAILURE")
        else:
            raise ValueError("INVALID_ACCEPTED: " + c["id"])
    history = fixtures["history"]
    late = history[0]
    require(all(late["before"][k] < late["cutoff"] <= late["correction"][k]
                for k in ("availableAt", "ingestedAt", "evidenceReceivedAt")), "LATE_CORRECTION_TIMES")
    require(late["expected"]["chosen"] == late["before"]["revisionId"] and
            late["expected"]["rejected"] == late["correction"]["revisionId"], "LATE_CORRECTION_EXPECTATION")
    conflict = history[1]
    require(len({c["value"] for c in conflict["declarations"]}) == 2 and
            conflict["expected"]["state"] == "CONFLICT" and conflict["expected"]["preserveBoth"], "DECLARATION_CONFLICT")
    receipt = history[2]
    require(receipt["eventAt"] < receipt["cutoff"] < receipt["receivedAt"] <= receipt["persistedAt"] and
            receipt["expected"]["historicalAvailability"] == "UNKNOWN", "RECEIPT_IS_NOT_HISTORY")
    catalogue = json.loads((ROOT / "contracts/metrics/e5a-v1/contract.json").read_text())
    # The authoritative catalogue uses metrics, not copied definitions here.
    metrics = catalogue["metrics"]
    require(len(metrics) == 22, "CATALOGUE_COUNT")
    counts = {family: sum("." + family + "." in m["id"] for m in metrics)
              for family in ("volume", "frequency", "epa", "success_rate")}
    require(counts == {"volume":6,"frequency":4,"epa":6,"success_rate":6}, "FAMILY_COVERAGE")
    preservation = check_preservation()
    print(json.dumps({"status":"PASS", "schema":"Draft 2020-12", "observations":len(fixtures["observations"]),
                      "cases":len(fixtures["cases"]), "operationDecisions":len(fixtures["cases"])*4*7,
                      "invalid":len(fixtures["invalid"]), "catalogue":counts, "preservation":preservation}, indent=2))


if __name__ == "__main__":
    main()
