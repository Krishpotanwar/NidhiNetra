"""Build R-06 vendor alias-review candidates from normalized work evidence."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import jsonschema

# graph/alias_candidates.py -> parents[4] is "05-App/".
_APP_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = _APP_ROOT / "contracts" / "entity_alias_candidate.schema.json"


class AliasCandidateValidationError(Exception):
    """Raised instead of returning an invalid alias-candidate artifact."""


def _load_schema() -> dict[str, Any]:
    if not SCHEMA_PATH.exists():
        raise AliasCandidateValidationError(
            f"schema file not found at {SCHEMA_PATH}. This module loads it "
            "from contracts/ and never hand-copies the shape."
        )
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _reason(*, identifier_ambiguous: bool, label_ambiguous: bool) -> str:
    if identifier_ambiguous and label_ambiguous:
        return "identifier_and_label_ambiguous"
    if identifier_ambiguous:
        return "identifier_has_multiple_labels"
    return "label_has_multiple_identifiers"


def build_alias_candidates(normalized_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one candidate per ambiguous observed vendor-ID/name pair.

    An association is ambiguous when its stable source identifier appears
    under more than one exact normalized label, or its exact label appears
    under more than one stable identifier. Evidence is the union of works
    across both competing dimensions, so one API page can show both sides
    without an N+1 lookup. Missing IDs or labels are excluded rather than
    turning a name into identity.
    """
    pair_work_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    labels_by_identifier: dict[str, set[str]] = defaultdict(set)
    identifiers_by_label: dict[str, set[str]] = defaultdict(set)

    for record in normalized_records:
        vendor_id = record.get("vendor_id")
        vendor_name = record.get("vendor_name")
        if not vendor_id or not vendor_name:
            continue
        work_id = record["work_id"]
        pair_work_ids[(vendor_id, vendor_name)].add(work_id)
        labels_by_identifier[vendor_id].add(vendor_name)
        identifiers_by_label[vendor_name].add(vendor_id)

    candidates: list[dict[str, Any]] = []
    for vendor_id, vendor_name in sorted(pair_work_ids):
        identifier_ambiguous = len(labels_by_identifier[vendor_id]) > 1
        label_ambiguous = len(identifiers_by_label[vendor_name]) > 1
        if not identifier_ambiguous and not label_ambiguous:
            continue

        evidence_work_ids: set[str] = set()
        if identifier_ambiguous:
            for competing_label in labels_by_identifier[vendor_id]:
                evidence_work_ids.update(pair_work_ids[(vendor_id, competing_label)])
        if label_ambiguous:
            for competing_identifier in identifiers_by_label[vendor_name]:
                evidence_work_ids.update(pair_work_ids[(competing_identifier, vendor_name)])

        candidates.append(
            {
                "entity_type": "vendor",
                "proposed_canonical_id": vendor_id,
                "alias_label": vendor_name,
                "reason": _reason(
                    identifier_ambiguous=identifier_ambiguous,
                    label_ambiguous=label_ambiguous,
                ),
                "evidence_work_ids": sorted(evidence_work_ids),
            }
        )

    validator = jsonschema.Draft7Validator(_load_schema())
    errors: list[str] = []
    for index, candidate in enumerate(candidates):
        errors.extend(
            f"candidate {index} ({'.'.join(str(part) for part in error.path) or '<root>'}): "
            f"{error.message}"
            for error in validator.iter_errors(candidate)
        )
    if errors:
        raise AliasCandidateValidationError(
            "build_alias_candidates produced output that violates "
            "entity_alias_candidate.schema.json:\n" + "\n".join(errors)
        )

    return candidates


__all__ = [
    "AliasCandidateValidationError",
    "SCHEMA_PATH",
    "build_alias_candidates",
]
