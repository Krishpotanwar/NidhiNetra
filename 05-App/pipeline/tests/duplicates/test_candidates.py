"""Phase 1 Stage A: canonical text, identical batches, near-copy pairs, the district audit."""

from __future__ import annotations

import unicodedata
from typing import Any

import pytest
from nidhinetra_pipeline.duplicates.candidates import (
    DuplicateCandidateValidationError,
    build_duplicate_candidates,
    canonical_description_v1,
    content_tokens,
    fingerprint,
    validate_duplicate_candidates,
)


class TestCanonicalDescription:
    def test_lowercases_and_collapses_punctuation_and_spacing(self) -> None:
        assert (
            canonical_description_v1("  PCC Road,  from Ram-house (Ward 3)\n")
            == "pcc road from ram house ward 3"
        )

    def test_keeps_digits_and_folds_compatibility_forms(self) -> None:
        assert canonical_description_v1("Ｎｏ ３５ ﬁtting") == "no 35 fitting"

    def test_keeps_devanagari_words_whole(self) -> None:
        text = "सड़क निर्माण"
        assert canonical_description_v1(text) == unicodedata.normalize("NFKC", text)
        assert len(canonical_description_v1(text).split()) == 2

    def test_punctuation_only_is_empty(self) -> None:
        assert canonical_description_v1("--- . ,") == ""

    def test_fingerprint_is_16_hex_and_depends_only_on_the_canonical_text(self) -> None:
        assert fingerprint("pcc road") == fingerprint("pcc road")
        assert fingerprint("pcc road") != fingerprint("pcc roads")
        assert len(fingerprint("pcc road")) == 16
        assert int(fingerprint("pcc road"), 16) >= 0

    def test_content_tokens_drop_common_words_and_keep_numbers(self) -> None:
        assert content_tokens("construction of community hall no 3 at ward 9") == [
            "community",
            "hall",
            "3",
            "ward",
            "9",
        ]


def _valid_artifact() -> dict:
    return {
        "meta": {
            "canonical_version": "canonical_description_v1",
            "finder_version": "candidate_generation_v0",
            "thresholds": {
                "character_similarity_min": 0.8,
                "token_jaccard_min": 0.75,
                "token_shared_min": 3,
                "district_character_similarity_min": 0.9,
                "per_work_limit_inr": 1500000,
                "group_total_floor_inr": 2500000,
            },
            "common_tokens": ["of", "road"],
            "counts": {
                key: 0
                for key in (
                    "works_considered",
                    "groups",
                    "identical_batches",
                    "threshold_crossing_batches",
                    "district_identical_batches",
                    "near_copy_pairs",
                    "reworded_match",
                    "one_sided_detail",
                    "conflicting_detail",
                    "district_near_copy_pairs",
                )
            },
        },
        "groups": {},
        "batches": [],
        "pairs": [],
    }


class TestSchema:
    def test_an_empty_artifact_is_valid(self) -> None:
        validate_duplicate_candidates(_valid_artifact())

    def test_an_artifact_without_its_counts_is_rejected(self) -> None:
        artifact = _valid_artifact()
        del artifact["meta"]["counts"]

        with pytest.raises(DuplicateCandidateValidationError, match="counts"):
            validate_duplicate_candidates(artifact)

    def test_a_batch_from_an_unknown_finder_is_rejected(self) -> None:
        artifact = _valid_artifact()
        artifact["batches"].append(
            {
                "candidate_id": "0123456789abcdef",
                "finder": "guess",
                "scope": "C1",
                "threshold_crossing_batch": False,
                "group": "0123456789abcdef",
            }
        )

        with pytest.raises(DuplicateCandidateValidationError, match="finder"):
            validate_duplicate_candidates(artifact)


def _rec(work_id: str, description: str | None, **overrides: Any) -> dict[str, Any]:
    """The fields Stage A reads from a normalized record."""
    record = {
        "work_id": work_id,
        "constituency": "C1",
        "implementing_district_authority": "D1",
        "implementing_agency": "Agency 1",
        "work_description": description,
        "activity_name": "Construction of roads",
        "sanctioned_amount_inr": 500_000.0,
        "sanction_date": "2024-07-09",
        "completion_status": "Sanctioned",
    }
    record.update(overrides)
    return record


class TestIdenticalBatches:
    def test_identical_descriptions_in_one_constituency_form_one_batch(self) -> None:
        records = [
            _rec("W1", "PCC Road, near Ram House", sanctioned_amount_inr=300_000.0),
            _rec(
                "W2",
                "PCC Road, near Ram House",
                sanctioned_amount_inr=400_000.0,
                sanction_date="2024-09-01",
            ),
            _rec(
                "W3",
                "pcc road near ram house.",
                sanctioned_amount_inr=500_000.0,
                completion_status="In Progress",
            ),
        ]

        artifact = build_duplicate_candidates(records)

        assert len(artifact["batches"]) == 1
        batch = artifact["batches"][0]
        group = artifact["groups"][batch["group"]]
        assert (batch["finder"], batch["scope"]) == ("identical_batch", "C1")
        assert group["work_ids"] == ["W1", "W2", "W3"]
        assert group["work_count"] == 3
        assert group["text"] == "PCC Road, near Ram House"  # the most common published variant
        assert group["activity"] == "Construction of roads"
        assert (group["amount_min_inr"], group["amount_max_inr"]) == (300_000.0, 500_000.0)
        assert group["amount_total_inr"] == 1_200_000.0
        assert (group["sanction_date_first"], group["sanction_date_last"]) == (
            "2024-07-09",
            "2024-09-01",
        )
        assert group["agencies"] == ["Agency 1"]
        assert group["statuses"] == {"In Progress": 1, "Sanctioned": 2}
        assert artifact["meta"]["counts"]["identical_batches"] == 1

    @pytest.mark.parametrize(
        ("amounts", "crosses"),
        [
            ([900_000.0, 900_000.0, 900_000.0], True),  # Rs 27 lakh, each below Rs 15 lakh
            ([900_000.0, 900_000.0, 700_000.0], True),  # exactly Rs 25 lakh counts
            ([900_000.0, 900_000.0, 600_000.0], False),  # Rs 24 lakh is under the floor
            ([1_500_000.0, 700_000.0, 700_000.0], False),  # one work at Rs 15 lakh is not below it
        ],
    )
    def test_threshold_crossing_needs_every_work_below_15_lakh_and_a_total_of_25_lakh(
        self, amounts: list[float], crosses: bool
    ) -> None:
        records = [
            _rec(f"W{n}", "Solar street lights", sanctioned_amount_inr=amount)
            for n, amount in enumerate(amounts)
        ]

        batch = build_duplicate_candidates(records)["batches"][0]

        assert batch["threshold_crossing_batch"] is crosses

    def test_the_same_text_in_two_constituencies_is_not_one_batch(self) -> None:
        records = [
            _rec(
                "W1", "Solar street lights", constituency="C1", implementing_district_authority="D1"
            ),
            _rec(
                "W2", "Solar street lights", constituency="C2", implementing_district_authority="D2"
            ),
        ]

        assert build_duplicate_candidates(records)["batches"] == []

    def test_descriptions_without_letters_or_digits_are_ignored(self) -> None:
        records = [_rec("W1", "---"), _rec("W2", "---"), _rec("W3", None), _rec("W4", "")]

        artifact = build_duplicate_candidates(records)

        assert artifact["batches"] == []
        assert artifact["meta"]["counts"]["works_considered"] == 0

    def test_a_single_work_is_never_a_batch(self) -> None:
        assert build_duplicate_candidates([_rec("W1", "Solar street lights")])["batches"] == []

    def test_no_records_gives_an_empty_valid_artifact(self) -> None:
        artifact = build_duplicate_candidates([])

        assert (artifact["groups"], artifact["batches"], artifact["pairs"]) == ({}, [], [])
        validate_duplicate_candidates(artifact)
