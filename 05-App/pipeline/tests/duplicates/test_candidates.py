"""Phase 1 Stage A: canonical text, identical batches, near-copy pairs, the district audit."""

from __future__ import annotations

import unicodedata

import pytest
from nidhinetra_pipeline.duplicates.candidates import (
    DuplicateCandidateValidationError,
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
