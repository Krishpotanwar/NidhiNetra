"""Tests for the pair judge's rubric, answer schema and request."""

from __future__ import annotations

import json
from typing import Any

import jsonschema
import pytest
from nidhinetra_pipeline.duplicates.candidates import fingerprint
from nidhinetra_pipeline.judge.inputs import Item
from nidhinetra_pipeline.judge.rubric import (
    ANSWER_SCHEMA,
    PROMPT_VERSION,
    RELATIONS,
    SCHEMA_VERSION,
    SYSTEM_PROMPT,
    render_messages,
    response_format,
)

# Editing the prompt or the schema changes what every stored answer means. Bump the version, add
# its pin here, and expect the whole judgments file to be asked again.
PROMPT_PINS = {"pair_judge_prompt_v1": "cd72fac3420753e7"}
SCHEMA_PINS = {"pair_judge_schema_v1": "95a5b6a647997601"}


def _answer(**overrides: Any) -> dict[str, Any]:
    answer = {
        "id": "1",
        "relation": "same_asset_same_place",
        "asset_a": "boundary wall",
        "place_a": "Govt School Rampur",
        "asset_b": "boundary wall",
        "place_b": "Govt School Rampur",
    }
    return {**answer, **overrides}


def _valid(answers: list[dict[str, Any]]) -> None:
    jsonschema.validate({"answers": answers}, ANSWER_SCHEMA)


def test_the_prompt_and_the_schema_are_pinned_to_their_versions() -> None:
    schema_text = json.dumps(ANSWER_SCHEMA, sort_keys=True)

    assert PROMPT_PINS[PROMPT_VERSION] == fingerprint(SYSTEM_PROMPT)
    assert SCHEMA_PINS[SCHEMA_VERSION] == fingerprint(schema_text)


def test_the_prompt_names_every_relation_the_schema_allows() -> None:
    assert all(relation in SYSTEM_PROMPT for relation in RELATIONS)


class TestAnswerSchema:
    def test_a_well_formed_answer_passes(self) -> None:
        _valid([_answer(), _answer(id="2", relation="unrelated")])

    def test_a_quote_may_be_null(self) -> None:
        _valid([_answer(relation="not_enough_detail", asset_a=None, place_a=None, place_b=None)])

    @pytest.mark.parametrize(
        "bad",
        [
            _answer(relation="duplicate"),
            _answer(relation=None),
            _answer(id=1),
            _answer(place_a=5),
            {**_answer(), "confidence": 0.9},
            {key: value for key, value in _answer().items() if key != "place_b"},
        ],
        ids=[
            "unknown relation",
            "null relation",
            "numeric id",
            "numeric quote",
            "extra key",
            "gap",
        ],
    )
    def test_a_malformed_answer_is_refused(self, bad: dict[str, Any]) -> None:
        with pytest.raises(jsonschema.ValidationError):
            _valid([bad])

    def test_the_reply_must_be_an_object_with_answers(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate([_answer()], ANSWER_SCHEMA)


def test_the_request_asks_for_a_strict_json_schema() -> None:
    fmt = response_format()

    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"] is ANSWER_SCHEMA


class TestRenderMessages:
    ITEMS = [
        Item("RAMPUR", "fa", "fb", "Boundary wall", "Boundary wall at स्कूल", "Roads", None, "i1"),
        Item("AGRA", "fc", "fd", "Hall no 3", "Hall no 4", None, "Schools", "i2"),
    ]

    def test_the_system_message_is_the_rubric(self) -> None:
        system, _ = render_messages(self.ITEMS)

        assert system == {"role": "system", "content": SYSTEM_PROMPT}

    def test_pairs_are_numbered_from_one_and_carry_only_what_the_judge_reads(self) -> None:
        _, user = render_messages(self.ITEMS)

        assert user["role"] == "user"
        assert json.loads(user["content"]) == {
            "pairs": [
                {
                    "id": "1",
                    "constituency": "RAMPUR",
                    "a": {"text": "Boundary wall", "activity": "Roads"},
                    "b": {"text": "Boundary wall at स्कूल", "activity": None},
                },
                {
                    "id": "2",
                    "constituency": "AGRA",
                    "a": {"text": "Hall no 3", "activity": None},
                    "b": {"text": "Hall no 4", "activity": "Schools"},
                },
            ]
        }

    def test_non_latin_text_is_sent_as_written_not_escaped(self) -> None:
        _, user = render_messages(self.ITEMS)

        assert "स्कूल" in user["content"]
