"""Tests for what the pair judge reads."""

from __future__ import annotations

import copy
from dataclasses import fields
from typing import Any

from nidhinetra_pipeline.duplicates.candidates import (
    build_duplicate_candidates,
    validate_duplicate_candidates,
)
from nidhinetra_pipeline.judge.inputs import Item, items_from_artifact


def _group(text: str, fingerprint: str, activity: str | None = "Roads") -> dict[str, Any]:
    return {"text": text, "text_fingerprint": fingerprint, "activity": activity}


def _artifact() -> dict[str, Any]:
    """The parts of a duplicate_candidates.json the judge reads, with amounts the judge must not."""
    return {
        "groups": {
            "g1": {**_group("Boundary wall\n at  Govt School Rampur", "f1"), "amount_total_inr": 5},
            "g2": _group("Boundary wall at Govt School Rampur Kalan", "f2", "Schools"),
            "g3": _group("Hall no 3", "f3", None),
        },
        "pairs": [
            {"finder": "near_copy", "scope": "RAMPUR", "a": "g1", "b": "g2"},
            {"finder": "district_near_copy", "scope": "MORADABAD", "a": "g1", "b": "g3"},
            {"finder": "near_copy", "scope": "AGRA", "a": "g3", "b": "g2"},
        ],
    }


class TestItemsFromArtifact:
    def test_there_is_one_item_per_near_copy_pair_and_none_for_the_district_audit(self) -> None:
        items = items_from_artifact(_artifact())

        assert [(i.scope, i.fingerprint_a, i.fingerprint_b) for i in items] == [
            ("AGRA", "f3", "f2"),
            ("RAMPUR", "f1", "f2"),
        ]

    def test_the_order_does_not_depend_on_the_order_of_the_pairs(self) -> None:
        artifact = _artifact()
        reversed_artifact = {**artifact, "pairs": artifact["pairs"][::-1]}

        assert items_from_artifact(artifact) == items_from_artifact(reversed_artifact)

    def test_texts_are_shown_with_every_run_of_whitespace_collapsed(self) -> None:
        rampur = items_from_artifact(_artifact())[1]

        assert rampur.text_a == "Boundary wall at Govt School Rampur"
        assert rampur.text_b == "Boundary wall at Govt School Rampur Kalan"

    def test_the_activities_pass_through_and_may_be_null(self) -> None:
        agra, rampur = items_from_artifact(_artifact())

        assert (agra.activity_a, agra.activity_b) == (None, "Schools")
        assert (rampur.activity_a, rampur.activity_b) == ("Roads", "Schools")

    def test_an_item_holds_no_amount_date_agency_or_work_count(self) -> None:
        assert {f.name for f in fields(Item)} == {
            "scope",
            "fingerprint_a",
            "fingerprint_b",
            "text_a",
            "text_b",
            "activity_a",
            "activity_b",
            "input_fingerprint",
        }


class TestInputFingerprint:
    @staticmethod
    def _rampur(artifact: dict[str, Any]) -> Item:
        return items_from_artifact(artifact)[1]

    def test_it_ignores_what_the_judge_does_not_read(self) -> None:
        changed = copy.deepcopy(_artifact())
        changed["groups"]["g1"]["amount_total_inr"] = 999
        changed["groups"]["g1"]["text_fingerprint"] = "another"  # the key of the answer, not input

        assert (
            self._rampur(changed).input_fingerprint == self._rampur(_artifact()).input_fingerprint
        )

    def test_it_moves_with_every_field_the_judge_reads(self) -> None:
        base = self._rampur(_artifact()).input_fingerprint
        edits = {
            "text a": lambda a: a["groups"]["g1"].update(text="Boundary wall at Govt School"),
            "text b": lambda a: a["groups"]["g2"].update(text="Boundary wall at Govt School"),
            "activity a": lambda a: a["groups"]["g1"].update(activity="Schools"),
            "activity b": lambda a: a["groups"]["g2"].update(activity="Roads"),
            "constituency": lambda a: a["pairs"][0].update(scope="AGRA"),
        }
        for label, edit in edits.items():
            changed = copy.deepcopy(_artifact())
            edit(changed)

            fingerprints = {i.input_fingerprint for i in items_from_artifact(changed)}

            assert base not in fingerprints, label

    def test_the_two_sides_are_not_interchangeable(self) -> None:
        swapped = copy.deepcopy(_artifact())
        swapped["pairs"][0].update(a="g2", b="g1")

        assert (
            self._rampur(swapped).input_fingerprint != self._rampur(_artifact()).input_fingerprint
        )


def test_it_reads_an_artifact_the_real_builder_made() -> None:
    records = [
        {
            "work_id": work_id,
            "constituency": "C1",
            "implementing_district_authority": "D1",
            "implementing_agency": "Agency 1",
            "work_description": description,
            "activity_name": "Lighting of public spaces",
            "sanctioned_amount_inr": 500_000.0,
            "sanction_date": "2024-07-09",
            "completion_status": "Sanctioned",
        }
        for work_id, description in (
            ("W1", "Installation of high mask light at Kheda"),
            ("W2", "Installation of high mast light at Kheda"),
        )
    ]
    artifact = build_duplicate_candidates(records)
    validate_duplicate_candidates(artifact)

    (item,) = items_from_artifact(artifact)

    assert item.scope == "C1"
    assert {item.text_a, item.text_b} == {
        "Installation of high mask light at Kheda",
        "Installation of high mast light at Kheda",
    }
    assert {item.fingerprint_a, item.fingerprint_b} == {
        group["text_fingerprint"] for group in artifact["groups"].values()
    }
    assert item.activity_a == item.activity_b == "Lighting of public spaces"
