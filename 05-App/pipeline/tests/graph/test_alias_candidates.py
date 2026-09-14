"""R-06 vendor identity candidates, built from normalized work evidence."""

from __future__ import annotations

import json

import jsonschema
from nidhinetra_pipeline.graph.alias_candidates import (
    SCHEMA_PATH,
    build_alias_candidates,
)

from .conftest import make_normalized


def _by_identity(candidates: list[dict]) -> dict[tuple[str, str], dict]:
    return {
        (candidate["proposed_canonical_id"], candidate["alias_label"]): candidate
        for candidate in candidates
    }


def test_emits_every_ambiguous_observed_vendor_id_and_name_pair() -> None:
    records = [
        make_normalized(work_id="W1", vendor_id="ID-1", vendor_name="Alpha Works"),
        make_normalized(work_id="W2", vendor_id="ID-1", vendor_name="Beta Works"),
        make_normalized(work_id="W3", vendor_id="ID-2", vendor_name="Alpha Works"),
        make_normalized(work_id="W4", vendor_id="ID-9", vendor_name="Solo Works"),
    ]

    candidates = build_alias_candidates(records)
    by_identity = _by_identity(candidates)

    assert set(by_identity) == {
        ("ID-1", "Alpha Works"),
        ("ID-1", "Beta Works"),
        ("ID-2", "Alpha Works"),
    }
    assert by_identity[("ID-1", "Alpha Works")] == {
        "entity_type": "vendor",
        "proposed_canonical_id": "ID-1",
        "alias_label": "Alpha Works",
        "reason": "identifier_and_label_ambiguous",
        "evidence_work_ids": ["W1", "W2", "W3"],
    }
    assert by_identity[("ID-1", "Beta Works")]["reason"] == ("identifier_has_multiple_labels")
    assert by_identity[("ID-1", "Beta Works")]["evidence_work_ids"] == ["W1", "W2"]
    assert by_identity[("ID-2", "Alpha Works")]["reason"] == ("label_has_multiple_identifiers")
    assert by_identity[("ID-2", "Alpha Works")]["evidence_work_ids"] == ["W1", "W3"]


def test_candidate_generation_uses_exact_name_strings() -> None:
    records = [
        make_normalized(work_id="W1", vendor_id="ID-1", vendor_name="ACME"),
        make_normalized(work_id="W2", vendor_id="ID-2", vendor_name="acme"),
    ]

    assert build_alias_candidates(records) == []


def test_missing_vendor_identity_parts_are_excluded() -> None:
    records = [
        make_normalized(work_id="W1", vendor_id=None, vendor_name="A Name"),
        make_normalized(work_id="W2", vendor_id="ID-2", vendor_name=None),
    ]

    assert build_alias_candidates(records) == []


def test_candidates_are_sorted_deduplicated_and_input_order_independent() -> None:
    records = [
        make_normalized(work_id="W2", vendor_id="ID-1", vendor_name="Beta"),
        make_normalized(work_id="W1", vendor_id="ID-1", vendor_name="Alpha"),
        make_normalized(work_id="W1", vendor_id="ID-1", vendor_name="Alpha"),
    ]

    first = build_alias_candidates(records)
    second = build_alias_candidates(list(reversed(records)))

    assert first == second
    assert [
        (candidate["proposed_canonical_id"], candidate["alias_label"]) for candidate in first
    ] == [("ID-1", "Alpha"), ("ID-1", "Beta")]
    assert all(candidate["evidence_work_ids"] == ["W1", "W2"] for candidate in first)


def test_every_candidate_validates_against_the_contract() -> None:
    records = [
        make_normalized(work_id="W1", vendor_id="ID-1", vendor_name="Alpha"),
        make_normalized(work_id="W2", vendor_id="ID-1", vendor_name="Beta"),
    ]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    for candidate in build_alias_candidates(records):
        assert list(validator.iter_errors(candidate)) == []
