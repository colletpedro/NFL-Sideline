"""Read bytes once; project only contractual columns. No path/mtime identity."""
import hashlib
import io
import json
from decimal import Decimal
from pathlib import Path

from .validation import CALENDAR_FIELDS, PBP_FIELDS, require_fields


def load_json(data):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"Non-standard JSON number {value}; use sentinel string")

    return json.loads(data, parse_float=Decimal, parse_constant=reject_constant,
                      object_pairs_hook=unique_object)


def read_source(path, kind):
    path = Path(path)
    data = path.read_bytes()
    fields = CALENDAR_FIELDS if kind == "calendar" else PBP_FIELDS
    if path.suffix == ".parquet":
        import polars as pl
        try:
            source_schema = pl.read_parquet_schema(io.BytesIO(data))
            require_fields(source_schema, fields)
            numeric_fields = {"play_id", "drive", "season", "week", "epa",
                              "qb_kneel", "qb_spike", "play_deleted", "special_teams_play", "two_point_attempt"}
            for key in fields:
                dtype = source_schema[key]
                text_scalar = dtype.base_type() in (pl.String, pl.Categorical, pl.Enum, pl.Null)
                valid = (dtype.is_numeric() or dtype in (pl.String, pl.Null)) if key in numeric_fields else text_scalar
                if not valid:
                    raise ValueError(f"Invalid Parquet schema type: {key}={dtype}")
            schema = {key: str(source_schema[key]) for key in fields}
            rows = pl.read_parquet(io.BytesIO(data), columns=list(fields)).to_dicts()
        except pl.exceptions.PolarsError as exc:
            raise ValueError(f"Invalid local Parquet: {path.name}") from exc
    elif path.suffix == ".json":
        document = load_json(data)
        if not isinstance(document, dict) or set(document) != {"columns", "rows"}:
            raise ValueError("JSON source requires exactly columns and rows")
        columns, rows = document["columns"], document["rows"]
        if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns) or len(set(columns)) != len(columns):
            raise ValueError("Invalid JSON column declaration")
        require_fields(columns, fields)
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError("JSON rows must be objects")
        for row in rows:
            require_fields(row, fields)
            if set(row) - set(columns):
                raise ValueError("Undeclared JSON columns")
        rows = [{key: row[key] for key in fields} for row in rows]
        schema = {key: "JSON scalar (validated per row)" for key in fields}
    else:
        raise ValueError("Offline sources must be .json or .parquet")
    sha256 = hashlib.sha256(data).hexdigest()
    return rows, {"kind": kind, "sha256": sha256, "source_revision_id": f"sha256:{sha256}",
                  "bytes": len(data), "raw_rows": len(rows), "relevant_schema": schema}


def read_inputs(calendar_paths, pbp_paths):
    calendars, plays, inputs = [], [], []
    for kind, paths, target in (("calendar", calendar_paths, calendars), ("pbp", pbp_paths, plays)):
        for path in paths:
            rows, descriptor = read_source(path, kind)
            target.extend(rows)
            inputs.append(descriptor)
    return calendars, plays, inputs
