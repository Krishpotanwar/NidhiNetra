"""Checks a judge answer's evidence against the two texts it was given."""

from __future__ import annotations

from typing import Any

from nidhinetra_pipeline.duplicates.candidates import canonical_description_v1

from .inputs import Item

SAME_PLACE = frozenset({"same_asset_same_place", "same_place_different_asset"})


def check_answer(item: Item, answer: dict[str, Any]) -> str | None:
    """None when the answer's evidence holds, else the code of the first rule it breaks.

    A quote must be words that appear, exactly, in the description it is quoted from. A same-place
    answer must quote a place from both sides, and the two quotes must name the same place.
    """
    for side, text in (("a", item.text_a), ("b", item.text_b)):
        for field in ("asset", "place"):
            quote = answer[f"{field}_{side}"]
            if quote is not None and (not quote.strip() or quote not in text):
                return f"{field}_{side}_not_in_text"
    if answer["relation"] in SAME_PLACE:
        place_a, place_b = answer["place_a"], answer["place_b"]
        if place_a is None or place_b is None:
            return "same_place_without_quotes"
        canonical = canonical_description_v1(place_a)
        if not canonical:
            return "place_quote_without_words"
        if canonical != canonical_description_v1(place_b):
            return "place_quotes_differ"
    return None
