"""The pair judge's rubric, its answer schema and the request built from them.

Editing SYSTEM_PROMPT or ANSWER_SCHEMA changes what every stored answer means, so it must come
with a new PROMPT_VERSION or SCHEMA_VERSION. test_rubric.py fails until it does.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from .inputs import Item

PROMPT_VERSION = "pair_judge_prompt_v1"
SCHEMA_VERSION = "pair_judge_schema_v1"

RELATIONS = (
    "same_asset_same_place",
    "same_place_different_asset",
    "same_asset_different_place",
    "not_enough_detail",
    "unrelated",
)

SYSTEM_PROMPT = """\
You compare pairs of short descriptions of public works funded by an Indian government scheme \
(MPLADS). Each pair comes from one constituency and looks alike. Say what the two descriptions \
have in common, using only their words and the activity label shown with each.

Choose exactly one relation for every pair:
- same_asset_same_place: the same kind of asset at the same named place or institution.
- same_place_different_asset: the same named place or institution, but a different asset or a \
different numbered unit (hall no 3 and hall no 4 are different assets).
- same_asset_different_place: the same kind of asset, at different named places or institutions.
- not_enough_detail: the words do not name a place or institution, or not the asset, so you \
cannot tell. "Construction of Mandap" against "Construction of Mandap" is this. It is a correct \
answer, and you should prefer it whenever a description names no place or institution.
- unrelated: a different asset at a different place.

Evidence: asset_a and asset_b are the words in each description that name the asset. place_a \
and place_b are the words that name the place or institution (a village, ward, road, school, \
hospital, temple or office). Copy them exactly, character for character, from that description. \
Use null where a description has no such words. For same_asset_same_place and \
same_place_different_asset, place_a and place_b must both be copied words and must name the same \
place or institution. Never write words that are not in the description.

Do not explain or comment. Reply with JSON only: one answer for every pair, using each pair's \
id exactly as given.
"""

_QUOTE = {"type": ["string", "null"]}

ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answers"],
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "relation", "asset_a", "place_a", "asset_b", "place_b"],
                "properties": {
                    "id": {"type": "string"},
                    "relation": {"type": "string", "enum": list(RELATIONS)},
                    "asset_a": _QUOTE,
                    "place_a": _QUOTE,
                    "asset_b": _QUOTE,
                    "place_b": _QUOTE,
                },
            },
        }
    },
}


def response_format() -> dict[str, Any]:
    """The `response_format` field of a chat completion request: strict JSON schema."""
    return {
        "type": "json_schema",
        "json_schema": {"name": "pair_judge_answers", "schema": ANSWER_SCHEMA, "strict": True},
    }


def render_messages(batch: Sequence[Item]) -> list[dict[str, str]]:
    """The chat messages for one request. Pairs are numbered 1, 2, ... within the request."""
    pairs = [
        {
            "id": str(n),
            "constituency": item.scope,
            "a": {"text": item.text_a, "activity": item.activity_a},
            "b": {"text": item.text_b, "activity": item.activity_b},
        }
        for n, item in enumerate(batch, 1)
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps({"pairs": pairs}, ensure_ascii=False)},
    ]
