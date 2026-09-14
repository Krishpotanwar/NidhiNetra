"""Normalize raw rung output into contracts/normalized_record.schema.json.

`normalize_records()` is the single function downstream code should call.
It stamps `source_rung` on every record and validates every output row
against the frozen JSON Schema (contracts/normalized_record.schema.json,
loaded by relative path, never hand-copied) before returning anything. A
record that fails validation raises -- it is never silently emitted.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import jsonschema

# pipeline/src/nidhinetra_pipeline/normalize/normalize.py -> parents[4] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = _APP_ROOT / "contracts" / "normalized_record.schema.json"

_REQUIRED_FIELDS = (
    "work_id",
    "state",
    "constituency",
    "mp_name",
    "tenure",
    "implementing_agency",
    "vendor_id",
    "vendor_name",
    "work_category",
    "sanctioned_amount_inr",
    "expenditure_amount_inr",
    "sanction_date",
    "completion_status",
    "last_updated",
    "source_rung",
)


class NormalizeValidationError(Exception):
    """Raised when a normalized record fails to validate against
    contracts/normalized_record.schema.json. The offending record is never
    included in `normalize_records()`'s return value -- the whole call
    raises instead of emitting a partial, invalid list.
    """


def _load_schema() -> dict[str, Any]:
    if not SCHEMA_PATH.exists():
        raise NormalizeValidationError(
            f"schema file not found at {SCHEMA_PATH}. This module loads it by "
            "relative path from contracts/ and never hand-copies the shape."
        )
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _to_number(value: Any, *, default: float | None = None) -> Any:
    """Best-effort coercion to a JSON-schema `number`. Returns the original
    value unchanged if it is not coercible, so the schema validator (not
    this function) is the single place that decides what counts as fatal.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value
    return value


def _map_one(raw: Any, *, source_rung: int) -> dict[str, Any]:
    """Map one raw rung-output row into the exact 14-key normalized shape.

    Raw rows are expected to already carry the normalized field names --
    every current rung either raises before returning data (Rung 1, blocked)
    or is unimplemented (Rungs 2-5), so no rung has yet defined a different
    raw shape to translate from. When a rung starts returning a genuinely
    different raw shape, translate it into these field names here, not
    downstream. Missing/wrong-typed fields are passed through as-is (not
    coerced into something schema-valid) so the schema validator below is
    the one place that decides what is fatal versus degradable, matching
    the schema's own per-field "Fatal if missing" / "Degradable" notes.
    """
    if not isinstance(raw, dict):
        raise NormalizeValidationError(
            f"expected a dict-shaped raw record, got {type(raw).__name__}: {raw!r}"
        )

    return {
        "work_id": raw.get("work_id"),
        "state": raw.get("state"),
        "constituency": raw.get("constituency"),
        "mp_name": raw.get("mp_name"),
        "tenure": raw.get("tenure"),
        "implementing_agency": raw.get("implementing_agency"),
        "vendor_id": raw.get("vendor_id"),
        "vendor_name": raw.get("vendor_name"),
        "work_category": raw.get("work_category"),
        "sanctioned_amount_inr": _to_number(raw.get("sanctioned_amount_inr")),
        "expenditure_amount_inr": _to_number(raw.get("expenditure_amount_inr"), default=0),
        "sanction_date": raw.get("sanction_date"),
        "completion_status": raw.get("completion_status"),
        "last_updated": raw.get("last_updated") or date.today().isoformat(),
        "source_rung": source_rung,
    }


def normalize_records(
    raw_records: Iterable[dict[str, Any]], *, source_rung: int
) -> list[dict[str, Any]]:
    """Map raw rung-output rows into validated normalized records.

    `source_rung` (1-5) is stamped onto every output record, overriding
    whatever the raw row may have carried, since the caller (the code that
    ran the ladder) is the authority on which rung actually produced this
    batch. Every output record is validated against
    contracts/normalized_record.schema.json before this function returns;
    the first invalid record raises `NormalizeValidationError` and no
    partial/invalid list is ever returned.
    """
    if not 1 <= source_rung <= 5:
        raise NormalizeValidationError(
            f"source_rung must be 1-5 per the schema, got {source_rung!r}"
        )

    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)

    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_records):
        record = _map_one(raw, source_rung=source_rung)
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        if errors:
            work_id = record.get("work_id")
            messages = "; ".join(
                f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
            )
            raise NormalizeValidationError(
                f"record at index {index} (work_id={work_id!r}) failed schema "
                f"validation and was not emitted: {messages}"
            )
        normalized.append(record)

    return normalized


__all__ = [
    "NormalizeValidationError",
    "SCHEMA_PATH",
    "normalize_records",
]
