"""Tests for the evidence check on a judge answer."""

from __future__ import annotations

from typing import Any

import pytest
from nidhinetra_pipeline.judge.inputs import Item
from nidhinetra_pipeline.judge.verify import SAME_PLACE, check_answer

TEXT_A = "Boundary wall at Govt School Rampur"
TEXT_B = "BOUNDARY WALL AT GOVT. SCHOOL, RAMPUR (phase 2)"


def _item(text_a: str = TEXT_A, text_b: str = TEXT_B) -> Item:
    return Item("C1", "fa", "fb", text_a, text_b, "Schools", "Schools", "i1")


def _answer(**overrides: Any) -> dict[str, Any]:
    answer = {
        "relation": "same_asset_same_place",
        "asset_a": "Boundary wall",
        "place_a": "Govt School Rampur",
        "asset_b": "BOUNDARY WALL",
        "place_b": "GOVT. SCHOOL, RAMPUR",
    }
    return {**answer, **overrides}


class TestQuotes:
    def test_quotes_found_in_their_own_text_pass_even_when_the_case_and_punctuation_differ(
        self,
    ) -> None:
        assert check_answer(_item(), _answer()) is None

    @pytest.mark.parametrize("field", ["asset_a", "place_a", "asset_b", "place_b"])
    def test_a_quote_that_is_not_in_its_text_is_refused_on_every_side_and_field(
        self, field: str
    ) -> None:
        assert check_answer(_item(), _answer(**{field: "Zila Parishad"})) == f"{field}_not_in_text"

    def test_a_quote_taken_from_the_other_text_is_refused(self) -> None:
        # "(phase 2)" is only in text b, so quoting it for side a must fail.
        assert check_answer(_item(), _answer(asset_a="(phase 2)")) == "asset_a_not_in_text"

    def test_a_quote_must_match_character_for_character(self) -> None:
        assert check_answer(_item(), _answer(asset_a="boundary wall")) == "asset_a_not_in_text"

    @pytest.mark.parametrize("empty", ["", "   "])
    def test_a_quote_with_no_characters_is_refused(self, empty: str) -> None:
        assert check_answer(_item(), _answer(asset_b=empty)) == "asset_b_not_in_text"

    def test_the_first_broken_rule_is_the_one_reported(self) -> None:
        answer = _answer(place_a="nowhere", place_b=None)  # also breaks the same-place rule

        assert check_answer(_item(), answer) == "place_a_not_in_text"


class TestSamePlace:
    def test_the_two_relations_that_claim_the_same_place(self) -> None:
        assert SAME_PLACE == {"same_asset_same_place", "same_place_different_asset"}

    @pytest.mark.parametrize("relation", sorted(SAME_PLACE))
    @pytest.mark.parametrize("missing", ["place_a", "place_b"])
    def test_a_same_place_answer_needs_a_place_quoted_from_both_texts(
        self, relation: str, missing: str
    ) -> None:
        answer = _answer(relation=relation, **{missing: None})

        assert check_answer(_item(), answer) == "same_place_without_quotes"

    @pytest.mark.parametrize(
        "relation", ["same_asset_different_place", "not_enough_detail", "unrelated"]
    )
    def test_the_other_relations_need_no_place(self, relation: str) -> None:
        answer = _answer(relation=relation, place_a=None, place_b=None)

        assert check_answer(_item(), answer) is None

    def test_places_that_differ_are_refused_for_a_same_place_answer(self) -> None:
        item = _item("RO plant at Madugula", "RO plant at Madugula Koduru")
        answer = _answer(
            asset_a="RO plant", place_a="Madugula", asset_b="RO plant", place_b="Madugula Koduru"
        )

        assert check_answer(item, answer) == "place_quotes_differ"

    def test_places_that_differ_are_what_a_different_place_answer_says(self) -> None:
        item = _item("RO plant at Madugula", "RO plant at Madugula Koduru")
        answer = _answer(
            relation="same_asset_different_place",
            asset_a="RO plant",
            place_a="Madugula",
            asset_b="RO plant",
            place_b="Madugula Koduru",
        )

        assert check_answer(item, answer) is None

    def test_a_place_quote_of_punctuation_alone_names_nothing(self) -> None:
        item = _item("Road - Rampur", "Road - Agra")
        answer = _answer(asset_a="Road", place_a="-", asset_b="Road", place_b="-")

        assert check_answer(item, answer) == "place_quote_without_words"
