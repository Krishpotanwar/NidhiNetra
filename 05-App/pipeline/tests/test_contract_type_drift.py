"""F-20 (nemotronreview.md): code generation from contracts/*.schema.json is
not wired, so the TypeScript types are mirrored by hand. This test is the
drift detector for those mirrors, the same way test_web_mirror_drift.py
guards the hand-mirrored constants: it reads the TS interfaces as text and
fails when a field exists on one side only, or when nullability disagrees.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# pipeline/tests/test_contract_type_drift.py -> parents[2] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[2]
_CONTRACTS = _APP_ROOT / "contracts"
_WEB_LIB = _APP_ROOT / "web" / "lib"

_FIELD = re.compile(r"^\s*(\w+)\??\s*:\s*([^;]+);", re.MULTILINE)


def _interface_fields(ts_source: str, name: str) -> dict[str, str]:
    match = re.search(rf"export interface {name}\b[^{{]*\{{(.*?)\n\}}", ts_source, re.DOTALL)
    assert match, f"interface {name} not found"
    body = re.sub(r"/\*.*?\*/", "", match.group(1), flags=re.DOTALL)
    body = re.sub(r"//[^\n]*", "", body)
    return {field: type_text.strip() for field, type_text in _FIELD.findall(body)}


def _object_properties(schema: dict, path: tuple[str, ...]) -> dict[str, dict]:
    node = schema
    for key in path:
        node = node["properties"][key]["items"]
    return node["properties"]


def _schema_nullable(prop: dict) -> bool:
    kind = prop.get("type")
    return isinstance(kind, list) and "null" in kind


def _ts_nullable(type_text: str) -> bool:
    return re.search(r"\|\s*null\b", type_text) is not None


# (schema file, path to an array's item object, or () for the top level,
#  TS file under web/lib, interface name, fields that exist only in TS)
_CASES = [
    ("normalized_record.schema.json", (), "types.ts", "NormalizedRecord", set()),
    ("risk_scored_record.schema.json", (), "types.ts", "RiskScoredRecord", set()),
    (
        "inspection_outcome.schema.json",
        (),
        "types.ts",
        "InspectionOutcome",
        {"outcome_id", "supersedes", "superseded"},
    ),
    ("fund_flow_graph.schema.json", ("nodes",), "graph-data.ts", "GraphNode", set()),
    ("fund_flow_graph.schema.json", ("edges",), "graph-data.ts", "GraphEdge", set()),
]


def _pair(schema_file: str, path: tuple[str, ...], ts_file: str, interface: str):
    schema = json.loads((_CONTRACTS / schema_file).read_text(encoding="utf-8"))
    props = _object_properties(schema, path)
    fields = _interface_fields((_WEB_LIB / ts_file).read_text(encoding="utf-8"), interface)
    return props, fields


@pytest.mark.parametrize(("schema_file", "path", "ts_file", "interface", "ts_only"), _CASES)
def test_ts_fields_match_the_schema(schema_file, path, ts_file, interface, ts_only) -> None:
    props, fields = _pair(schema_file, path, ts_file, interface)
    missing_in_ts = set(props) - set(fields)
    extra_in_ts = set(fields) - set(props) - ts_only
    assert not missing_in_ts and not extra_in_ts, (
        f"{interface} drifted from {schema_file}: missing in TS {sorted(missing_in_ts)}, "
        f"only in TS {sorted(extra_in_ts)}"
    )


@pytest.mark.parametrize(("schema_file", "path", "ts_file", "interface", "ts_only"), _CASES)
def test_ts_nullability_matches_the_schema(schema_file, path, ts_file, interface, ts_only) -> None:
    props, fields = _pair(schema_file, path, ts_file, interface)
    wrong = sorted(
        name
        for name, prop in props.items()
        if name in fields and _schema_nullable(prop) != _ts_nullable(fields[name])
    )
    assert not wrong, f"{interface}: nullability differs from {schema_file} for {wrong}"


def test_the_checker_itself_has_teeth() -> None:
    """The parser must see fields, optional markers and nullability, so a
    silently empty parse can never make the two tests above pass."""
    source = """
export interface Sample {
  /** a comment with a: colon; and a semicolon */
  plain: string;
  maybe?: number | null;
  // another: comment;
  list: string[];
}
"""
    fields = _interface_fields(source, "Sample")
    assert fields == {"plain": "string", "maybe": "number | null", "list": "string[]"}
    assert _ts_nullable(fields["maybe"])
    assert not _ts_nullable(fields["plain"])
    assert _schema_nullable({"type": ["string", "null"]})
    assert not _schema_nullable({"type": "string"})
