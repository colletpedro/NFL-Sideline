"""Explicit evidence assertions bound to input hashes; no completeness inference."""
from datetime import datetime, timezone

from .validation import integer, text


def evidence(value):
    if not isinstance(value, dict) or set(value) != {"basis", "reference"}:
        raise ValueError("Evidence requires basis and reference")
    return {key: text(value[key], f"evidence.{key}") for key in ("basis", "reference")}


def proven_value(record, *, timestamp=False):
    if not isinstance(record, dict) or set(record) != {"value", "evidence"}:
        raise ValueError("Proven metadata requires value and evidence")
    value = text(record["value"], "metadata.value")
    if timestamp:
        try:
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Invalid metadata timestamp") from exc
        if instant.tzinfo is None or "T" not in value:
            raise ValueError("Metadata timestamp requires timezone")
        value = instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {"value": value, "evidence": evidence(record["evidence"])}


def validate_metadata(document, inputs, games):
    if document is None:
        return {"metadataVersion": 1, "games": {}, "sources": {}}
    if not isinstance(document, dict) or set(document) - {"metadataVersion", "calendar_sha256", "pbp_sha256", "games", "sources"}:
        raise ValueError("Invalid metadata document")
    if type(document.get("metadataVersion")) is not int or document["metadataVersion"] != 1:
        raise ValueError("Unsupported metadataVersion")
    for kind in ("calendar", "pbp"):
        hashes = document.get(f"{kind}_sha256")
        if not isinstance(hashes, list) or not all(isinstance(h, str) for h in hashes) or sorted(hashes) != sorted({i["sha256"] for i in inputs if i["kind"] == kind}):
            raise ValueError(f"Metadata {kind} hashes do not match input bytes")
    game_records, sources = document.get("games", {}), document.get("sources", {})
    if not isinstance(game_records, dict) or not isinstance(sources, dict):
        raise ValueError("Metadata games/sources must be objects")
    normalized = {"metadataVersion": 1, "games": {}, "sources": {}}
    for game_id, record in game_records.items():
        if game_id not in games or not isinstance(record, dict) or set(record) - {"completeness", "expected_unique_rows", "evidence", "available_at", "event_upper_bound", "ingested_at"}:
            raise ValueError(f"Invalid game metadata: {game_id}")
        status = record.get("completeness", "UNKNOWN")
        if status not in ("UNKNOWN", "PARTIAL", "COMPLETE"):
            raise ValueError(f"Invalid completeness: {game_id}")
        item = {"completeness": status}
        if status != "UNKNOWN":
            item["evidence"] = evidence(record.get("evidence"))
        elif "evidence" in record:
            item["evidence"] = evidence(record["evidence"])
        if "expected_unique_rows" in record:
            item["expected_unique_rows"] = integer(record["expected_unique_rows"], "expected_unique_rows")
        if status == "COMPLETE" and "expected_unique_rows" not in item:
            raise ValueError("COMPLETE requires explicit raw unique count as well as evidence")
        for key in ("available_at", "event_upper_bound", "ingested_at"):
            if key in record:
                item[key] = proven_value(record[key], timestamp=True)
        normalized["games"][game_id] = item
    known_hashes = {i["sha256"] for i in inputs if i["kind"] == "pbp"}
    for digest, record in sources.items():
        if digest not in known_hashes or not isinstance(record, dict) or set(record) != {"source_model_version"}:
            raise ValueError("Invalid source model metadata")
        normalized["sources"][digest] = {"source_model_version": proven_value(record["source_model_version"])}
    known_models = {s["source_model_version"]["value"] for s in normalized["sources"].values()
                    if s["source_model_version"]["value"] != "UNKNOWN"}
    if len(known_models) > 1:
        raise ValueError("Known EPA model versions differ; use separate offline batches")
    return normalized
