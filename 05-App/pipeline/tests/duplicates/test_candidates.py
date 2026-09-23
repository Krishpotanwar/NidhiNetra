"""Phase 1 Stage A: canonical text, identical batches, near-copy pairs, the district audit."""

from __future__ import annotations

import copy
import hashlib
import json
import random
import unicodedata
from typing import Any

import pytest
from nidhinetra_pipeline.duplicates.candidates import (
    CHARACTER_SIMILARITY_MIN,
    COMMON_TOKENS_V0,
    DISTRICT_CHARACTER_SIMILARITY_MIN,
    GROUP_TOTAL_FLOOR_INR,
    PER_WORK_LIMIT_INR,
    TOKEN_JACCARD_MIN,
    TOKEN_SHARED_MIN,
    DuplicateCandidateValidationError,
    _candidate_id,
    _similar_pairs,
    build_duplicate_candidates,
    canonical_description_v1,
    content_tokens,
    fingerprint,
    validate_duplicate_candidates,
)
from scipy.sparse import csr_matrix


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

    def test_the_frozen_derivations_have_not_moved(self) -> None:
        # These become keys in committed data (fingerprints and ids) and inputs to every judgment
        # about a pair. Changing any of them is a new version, not an edit.
        assert fingerprint("pcc road") == "510078ed9a39e322"
        assert _candidate_id("group", "C1", "ab") == "0cb611682ba87185"
        assert sorted(COMMON_TOKENS_V0) == [
            "and",
            "at",
            "block",
            "construction",
            "from",
            "gram",
            "high",
            "house",
            "in",
            "installation",
            "ke",
            "light",
            "near",
            "no",
            "of",
            "panchayat",
            "road",
            "to",
            "village",
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

    def test_a_tie_goes_to_the_smaller_string(self) -> None:
        records = [
            _rec("W1", "pcc road near ram house"),
            _rec("W2", "PCC Road near Ram House"),
        ]

        for ordered in (records, records[::-1]):
            (group,) = build_duplicate_candidates(ordered)["groups"].values()
            assert group["text"] == "PCC Road near Ram House"  # capitals sort before lower case

    def test_the_most_common_wording_wins_even_when_it_sorts_after_the_minority(self) -> None:
        # "PCC Road..." (capitalized) sorts before "pcc road..." (lower case) in a plain string
        # comparison, so a version of _mode that picked the alphabetically smallest wording
        # regardless of frequency would show the 1-of-3 minority here, not the 2-of-3 majority.
        records = [
            _rec("W1", "pcc road near ram house"),
            _rec("W2", "pcc road near ram house"),
            _rec("W3", "PCC Road near Ram House"),
        ]

        for ordered in (records, records[::-1], [records[2], records[0], records[1]]):
            (group,) = build_duplicate_candidates(ordered)["groups"].values()
            assert group["text"] == "pcc road near ram house"

    def test_a_group_with_no_agency_activity_or_date_still_summarises(self) -> None:
        missing = {"implementing_agency": None, "activity_name": None, "sanction_date": None}
        records = [
            _rec("W1", "Solar street lights", **missing),
            _rec("W2", "Solar street lights", **missing),
        ]

        (group,) = build_duplicate_candidates(records)["groups"].values()

        assert (
            group["activity"],
            group["agencies"],
            group["sanction_date_first"],
            group["sanction_date_last"],
        ) == (None, [], None, None)


def _pairs(records: list[dict[str, Any]], finder: str = "near_copy") -> list[dict[str, Any]]:
    return [p for p in build_duplicate_candidates(records)["pairs"] if p["finder"] == finder]


class TestNearCopyPairs:
    def test_a_typo_is_paired_by_character_similarity(self) -> None:
        records = [
            _rec("W1", "Installation of high mask light at Kheda"),
            _rec("W2", "Installation of high mast light at Kheda"),
        ]

        (pair,) = _pairs(records)

        assert pair["hits"] == ["character"]
        assert pair["character_similarity"] >= 0.80
        assert pair["difference_group"] == "conflicting_detail"
        assert sorted((pair["only_a_tokens"], pair["only_b_tokens"])) == [["mask"], ["mast"]]

    def test_many_shared_words_pair_by_token_overlap_when_the_letters_differ_a_lot(self) -> None:
        records = [
            _rec("W1", "ram sai raj may day sun venkatanarasimharajuvaripeta"),
            _rec("W2", "ram sai raj may day sun chandrasekharapuramcolony"),
        ]

        (pair,) = _pairs(records)

        assert pair["hits"] == ["token"]
        assert pair["character_similarity"] < 0.80
        assert pair["token_overlap"] == 0.75
        assert pair["shared_tokens"] == ["day", "may", "raj", "ram", "sai", "sun"]

    def test_the_same_words_in_another_order_are_a_reworded_match(self) -> None:
        records = [
            _rec("W1", "Road to Ram Mandir at village Kheda"),
            _rec("W2", "Kheda village road near Ram Mandir"),
        ]

        (pair,) = _pairs(records)

        assert pair["difference_group"] == "reworded_match"
        assert (pair["only_a_tokens"], pair["only_b_tokens"]) == ([], [])
        assert pair["shared_tokens"] == ["kheda", "mandir", "ram"]

    def test_extra_detail_on_one_side_is_one_sided_detail(self) -> None:
        records = [
            _rec("W1", "ram sai raj may day sun mandir"),
            _rec("W2", "ram sai raj may day sun mandir sector"),
        ]

        (pair,) = _pairs(records)

        assert pair["difference_group"] == "one_sided_detail"
        assert sorted((pair["only_a_tokens"], pair["only_b_tokens"])) == [[], ["sector"]]

    def test_numbers_count_so_numbered_siblings_are_conflicting_detail(self) -> None:
        records = [
            _rec("W1", "Community hall no 3 ward 9"),
            _rec("W2", "Community hall no 4 ward 9"),
        ]

        (pair,) = _pairs(records)

        assert pair["difference_group"] == "conflicting_detail"
        assert sorted((pair["only_a_tokens"], pair["only_b_tokens"])) == [["3"], ["4"]]

    def test_two_shared_words_are_not_enough_for_token_overlap(self) -> None:
        records = [
            _rec("W1", "Construction of road to Ram Mandir in village"),
            _rec("W2", "Installation near house at Mandir Ram gram panchayat"),
        ]

        assert _pairs(records) == []

    def test_token_overlap_below_three_quarters_is_not_a_pair(self) -> None:
        records = [
            _rec("W1", "ram sai raj may day sun venkatanarasimharajuvaripeta"),
            _rec("W2", "ram sai raj may day chandrasekharapuramcolony"),
        ]

        assert _pairs(records) == []

    def test_a_cosine_just_under_the_character_threshold_is_not_a_pair(self) -> None:
        # Cosine 0.79. Stage D may move the line; until then this pair is below it.
        records = [
            _rec("W1", "cremation ground at village"),
            _rec("W2", "cremation ground at village chak dana"),
        ]

        assert _pairs(records) == []

    def test_side_a_is_the_text_that_sorts_first(self) -> None:
        records = [
            _rec("W1", "Installation of high mast light at Kheda"),
            _rec("W2", "Installation of high mask light at Kheda"),
        ]

        (pair,) = build_duplicate_candidates(records)["pairs"]

        assert (pair["only_a_tokens"], pair["only_b_tokens"]) == (["mask"], ["mast"])

    def test_a_score_is_rounded_before_it_meets_a_threshold(self) -> None:
        # Rows [1, 0] and [0.79996, 0.6] have a dot product of 0.79996, which rounds to 0.8.
        just_over = csr_matrix([[1.0, 0.0], [0.79996, 0.6]])
        just_under = csr_matrix([[1.0, 0.0], [0.79994, 0.6]])
        no_tokens = csr_matrix((2, 1))

        assert [p[:3] for p in _similar_pairs([0, 1], just_over, no_tokens, 0.80, False)] == [
            (0, 1, 0.8)
        ]
        assert list(_similar_pairs([0, 1], just_under, no_tokens, 0.80, False)) == []

    def test_a_typo_in_another_constituency_is_not_paired(self) -> None:
        records = [
            _rec("W1", "Installation of high mask light at Kheda"),
            _rec(
                "W2",
                "Installation of high mast light at Kheda",
                constituency="C2",
                implementing_district_authority="D2",
            ),
        ]

        assert build_duplicate_candidates(records)["pairs"] == []

    def test_a_lookalike_in_another_constituency_adds_no_pair(self) -> None:
        records = [
            _rec("W1", "Installation of high mask light at Kheda"),
            _rec("W2", "Installation of high mast light at Kheda"),
            _rec(
                "W3",
                "Installation of high mast light at Kheda",
                constituency="C2",
                implementing_district_authority="D2",
            ),
        ]

        (pair,) = _pairs(records)

        assert pair["scope"] == "C1"

    def test_three_shared_words_at_exactly_three_quarters_are_enough(self) -> None:
        # Both token-channel lines at once: exactly three shared content words and Jaccard exactly
        # 0.75. The texts share almost no letters, so only the token channel fires.
        records = [
            _rec("W1", "ram sai raj road in village kheda"),
            _rec("W2", "ram sai raj installation near house"),
        ]

        (pair,) = _pairs(records)

        assert pair["hits"] == ["token"]
        assert pair["token_overlap"] == 0.75
        assert len(pair["shared_tokens"]) == 3

    def test_five_shared_words_of_seven_are_not_enough(self) -> None:
        records = [
            _rec("W1", "ram sai raj may day venkatanarasimharajuvaripeta"),
            _rec("W2", "ram sai raj may day chandrasekharapuramcolony"),
        ]

        assert _pairs(records) == []  # Jaccard 5/7 = 0.714, under 0.75

    def test_a_cosine_a_little_over_the_character_line_is_a_character_only_pair(self) -> None:
        # Cosine 0.84: over 0.80 and under 0.85. One shared content word, so the token channel is
        # silent.
        records = [
            _rec("W1", "Installation of high mask light at Kheda"),
            _rec("W2", "Installation of high mast light at Kheda no"),
        ]

        (pair,) = _pairs(records)

        assert pair["hits"] == ["character"]
        assert 0.80 <= pair["character_similarity"] < 0.85

    def test_a_pair_found_by_both_channels_lists_character_first(self) -> None:
        records = [
            _rec("W1", "Road to Ram Mandir at village Kheda"),
            _rec("W2", "Kheda village road near Ram Mandir"),
        ]

        (pair,) = _pairs(records)

        assert pair["hits"] == ["character", "token"]


class TestDistrictAudit:
    def test_identical_text_in_two_constituencies_of_one_district_is_a_quiet_batch(self) -> None:
        records = [
            _rec("W1", "Construction of Community Center", constituency="C1"),
            _rec("W2", "Construction of Community Center", constituency="C2"),
        ]

        artifact = build_duplicate_candidates(records)

        (batch,) = artifact["batches"]
        assert (batch["finder"], batch["scope"]) == ("district_identical_batch", "D1")
        assert artifact["groups"][batch["group"]]["constituencies"] == ["C1", "C2"]

    def test_similar_text_across_constituencies_of_one_district_is_a_district_pair(self) -> None:
        records = [
            _rec("W1", "Providing and installation of Open Gym Equipment", constituency="C1"),
            _rec("W2", "Providing and installation of Open Gym Equipments", constituency="C2"),
        ]

        (pair,) = _pairs(records, "district_near_copy")

        assert (pair["scope"], pair["hits"]) == ("D1", ["character"])
        assert pair["character_similarity"] >= 0.90

    def test_two_texts_that_sit_in_one_constituency_are_left_to_finder_two(self) -> None:
        records = [
            _rec("W1", "Providing and installation of Open Gym Equipment", constituency="C1"),
            _rec("W2", "Providing and installation of Open Gym Equipments", constituency="C1"),
        ]

        artifact = build_duplicate_candidates(records)

        assert [p["finder"] for p in artifact["pairs"]] == ["near_copy"]

    def test_across_constituencies_only_the_stricter_district_threshold_applies(self) -> None:
        # Cosine 0.87: a Finder 2 pair inside one constituency, but not a district pair.
        records = [
            _rec("W1", "Installation of high mask light at Kheda", constituency="C1"),
            _rec("W2", "Installation of high mast light at Kheda", constituency="C2"),
        ]

        assert build_duplicate_candidates(records)["pairs"] == []

    def test_works_without_a_district_authority_are_not_audited(self) -> None:
        records = [
            _rec(
                "W1",
                "Construction of Community Center",
                constituency="C1",
                implementing_district_authority=None,
            ),
            _rec(
                "W2",
                "Construction of Community Center",
                constituency="C2",
                implementing_district_authority=None,
            ),
        ]

        assert build_duplicate_candidates(records)["batches"] == []


class TestArtifact:
    @staticmethod
    def _mixed_records() -> list[dict[str, Any]]:
        return [
            _rec("W1", "Solar street lights", sanctioned_amount_inr=900_000.0),
            _rec("W2", "Solar street lights", sanctioned_amount_inr=900_000.0),
            _rec("W3", "Solar street lights", sanctioned_amount_inr=900_000.0),
            _rec("W4", "Installation of high mask light at Kheda"),
            _rec("W5", "Installation of high mast light at Kheda"),
            _rec("W6", "Construction of Community Center", constituency="C2"),
            _rec("W7", "Construction of Community Center", constituency="C3"),
        ]

    def test_the_output_does_not_depend_on_the_input_order(self) -> None:
        records = self._mixed_records()
        shuffled = records[:]
        random.Random(7).shuffle(shuffled)

        assert json.dumps(build_duplicate_candidates(records)) == json.dumps(
            build_duplicate_candidates(shuffled)
        )

    def test_the_whole_artifact_has_not_moved(self) -> None:
        # The two golden values in TestCanonicalDescription pin fingerprint() and _candidate_id()
        # in isolation, not their call sites. This pins the artifact those call sites actually
        # produce: swapping _batch's id arguments, swapping _pair's fingerprints, renaming the
        # "group" id prefix, or hashing text_fingerprint on canonical + " " all change this hash.
        # Changing any of them is a new version, not an edit.
        artifact = build_duplicate_candidates(self._mixed_records())
        text = json.dumps(artifact, sort_keys=True, separators=(",", ":"))

        assert hashlib.sha256(text.encode()).hexdigest()[:16] == "81fc8c67c89e5074"

    def test_every_reference_resolves_and_no_group_is_orphaned(self) -> None:
        artifact = build_duplicate_candidates(self._mixed_records())

        referenced = {batch["group"] for batch in artifact["batches"]}
        referenced |= {pair[side] for pair in artifact["pairs"] for side in ("a", "b")}

        assert referenced == set(artifact["groups"])
        assert artifact["meta"]["counts"]["groups"] == len(artifact["groups"])

    def test_a_reference_to_a_missing_group_is_rejected(self) -> None:
        # Every group stays referenced (nothing is orphaned): a batch is added pointing at a
        # missing id, rather than redirecting an existing batch, which would also orphan the
        # group it used to point at and let a check narrowed to "groups - referenced" pass.
        artifact = build_duplicate_candidates(self._mixed_records())
        artifact["batches"].append({**artifact["batches"][0], "group": "0123456789abcdef"})

        with pytest.raises(
            DuplicateCandidateValidationError,
            match=r"^1 reference\(s\) resolve to no group and 0 group",
        ):
            validate_duplicate_candidates(artifact)

    def test_a_group_nothing_refers_to_is_rejected(self) -> None:
        # Every reference still resolves: only a group is added, nothing is redirected away from
        # one, so this cannot be satisfied by a check that only looks for a dangling reference.
        artifact = build_duplicate_candidates(self._mixed_records())
        artifact["groups"]["0123456789abcdef"] = copy.deepcopy(
            next(iter(artifact["groups"].values()))
        )

        with pytest.raises(
            DuplicateCandidateValidationError,
            match=r"^0 reference\(s\) resolve to no group and 1 group",
        ):
            validate_duplicate_candidates(artifact)

    def test_meta_records_the_thresholds_the_code_used(self) -> None:
        thresholds = build_duplicate_candidates(self._mixed_records())["meta"]["thresholds"]

        assert thresholds == {
            "character_similarity_min": CHARACTER_SIMILARITY_MIN,
            "token_jaccard_min": TOKEN_JACCARD_MIN,
            "token_shared_min": TOKEN_SHARED_MIN,
            "district_character_similarity_min": DISTRICT_CHARACTER_SIMILARITY_MIN,
            "per_work_limit_inr": PER_WORK_LIMIT_INR,
            "group_total_floor_inr": GROUP_TOTAL_FLOOR_INR,
        }

    def test_the_input_records_are_not_modified(self) -> None:
        records = self._mixed_records()
        before = copy.deepcopy(records)

        build_duplicate_candidates(records)

        assert records == before

    def test_candidate_ids_are_unique(self) -> None:
        artifact = build_duplicate_candidates(self._mixed_records())
        ids = [c["candidate_id"] for c in artifact["batches"] + artifact["pairs"]]

        assert len(ids) == len(set(ids)) > 0

    def test_the_counts_add_up(self) -> None:
        artifact = build_duplicate_candidates(self._mixed_records())
        counts = artifact["meta"]["counts"]

        assert counts["works_considered"] == 7
        assert counts["identical_batches"] == 1
        assert counts["threshold_crossing_batches"] == 1
        assert counts["district_identical_batches"] == 1
        assert counts["near_copy_pairs"] == (
            counts["reworded_match"] + counts["one_sided_detail"] + counts["conflicting_detail"]
        )


class TestDistrictAuditGuarantees:
    """Finder 3 inside the artifact-level guarantees: order, orphans, counters and shared pairs."""

    GYM = "Providing and installation of Open Gym Equipment"
    GYMS = "Providing and installation of Open Gym Equipments"

    @classmethod
    def _records(cls) -> list[dict[str, Any]]:
        def rec(work_id: str, text: str, constituency: str, authority: str) -> dict[str, Any]:
            return _rec(
                work_id,
                text,
                constituency=constituency,
                implementing_district_authority=authority,
            )

        centre = "Construction of Community Center"
        return [
            rec("A1", centre, "C2", "D1"),  # a district batch across two constituencies
            rec("A2", centre, "C3", "D1"),
            rec("B1", centre, "C5", "D2"),  # a second district batch, in another authority
            rec("B2", centre, "C6", "D2"),
            rec("P1", cls.GYM, "C7", "D3"),  # a district pair across two constituencies
            rec("P2", cls.GYMS, "C8", "D3"),
            rec("Q1", cls.GYM, "C9", "D4"),  # one constituency only: Finder 2 alone
            rec("Q2", cls.GYMS, "C9", "D4"),
            rec("R1", cls.GYM, "C10", "D5"),  # found by both finders
            rec("R2", cls.GYMS, "C10", "D5"),
            rec("R3", cls.GYMS, "C11", "D5"),
            rec("T1", "ram sai raj may day sun venkatanarasimharajuvaripeta", "C12", "D6"),
            rec(
                "T2", "ram sai raj may day sun chandrasekharapuramcolony", "C13", "D6"
            ),  # tokens only
            rec("U1", "purchase books for library", "C16", "D9"),
            rec("U2", "Purchase of books for library", "C17", "D9"),
            rec("S1", "Solar street lights", "C14", "D7"),  # two Finder 1 batches
            rec("S2", "Solar street lights", "C14", "D7"),
            rec("S3", "Solar street lights", "C15", "D8"),
            rec("S4", "Solar street lights", "C15", "D8"),
        ]

    def test_the_output_does_not_depend_on_the_input_order_with_finder_three_in_play(self) -> None:
        records = self._records()
        expected = json.dumps(build_duplicate_candidates(records))
        shuffled = records[:]
        random.Random(7).shuffle(shuffled)

        assert json.dumps(build_duplicate_candidates(records[::-1])) == expected
        assert json.dumps(build_duplicate_candidates(shuffled)) == expected

    def test_no_group_is_orphaned_and_every_reference_resolves(self) -> None:
        artifact = build_duplicate_candidates(self._records())

        referenced = {batch["group"] for batch in artifact["batches"]}
        referenced |= {pair[side] for pair in artifact["pairs"] for side in ("a", "b")}

        assert referenced == set(artifact["groups"])

    def test_every_counter_counts_its_own_finder(self) -> None:
        counts = build_duplicate_candidates(self._records())["meta"]["counts"]

        assert (
            counts["identical_batches"],
            counts["district_identical_batches"],
            counts["near_copy_pairs"],
            counts["district_near_copy_pairs"],
            counts["groups"],
        ) == (2, 3, 2, 3, 14)

    def test_a_pair_found_by_both_finders_keeps_its_own_id_and_groups(self) -> None:
        artifact = build_duplicate_candidates(self._records())
        groups = artifact["groups"]

        def texts(pair: dict[str, Any]) -> frozenset[str]:
            return frozenset(groups[pair[side]]["text_fingerprint"] for side in ("a", "b"))

        (near,) = [
            p for p in artifact["pairs"] if p["finder"] == "near_copy" and p["scope"] == "C10"
        ]
        (district,) = [
            p
            for p in artifact["pairs"]
            if p["finder"] == "district_near_copy" and p["scope"] == "D5"
        ]

        assert texts(near) == texts(district)
        assert near["candidate_id"] != district["candidate_id"]
        assert not {near["a"], near["b"]} & {district["a"], district["b"]}
        assert groups[district["b"]]["constituencies"] == ["C10", "C11"]
        assert groups[near["b"]]["constituencies"] == ["C10"]

    def test_a_cosine_just_over_the_district_line_is_a_district_pair(self) -> None:
        # Cosine 0.9016: over the district line of 0.90 by a hair.
        records = [
            _rec("W1", "Purchase of books for the village library", constituency="C1"),
            _rec("W2", "Purchase of books for the village librarys", constituency="C2"),
        ]

        (pair,) = _pairs(records, "district_near_copy")

        assert 0.90 <= pair["character_similarity"] < 0.91

    def test_a_cosine_just_under_the_district_line_is_not_a_district_pair(self) -> None:
        # Cosine 0.8982: over the near-copy line of 0.80, under the district line of 0.90.
        records = [
            _rec("W1", "Purchase of books for the village library", constituency="C1"),
            _rec("W2", "Purchase of book for the village library", constituency="C2"),
        ]

        assert _pairs(records, "district_near_copy") == []

    def test_a_constituency_and_a_district_authority_with_one_name_fail_loudly(self) -> None:
        records = [
            _rec(
                "W1", "Solar street lights", constituency="X", implementing_district_authority="X"
            ),
            _rec(
                "W2", "Solar street lights", constituency="X", implementing_district_authority="X"
            ),
            _rec(
                "W3", "Solar street lights", constituency="Y", implementing_district_authority="X"
            ),
        ]

        with pytest.raises(DuplicateCandidateValidationError, match="constituency and a district"):
            build_duplicate_candidates(records)
