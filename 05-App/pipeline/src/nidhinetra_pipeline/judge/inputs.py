"""What the pair judge reads: one item per near-copy pair, built from duplicate_candidates.json.

The judge sees the two descriptions as published, each side's portal activity and the
constituency, and nothing else: no amounts, dates, agencies or work counts. Those are facts about
works, and keeping them out is what lets one answer serve every work behind a text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from nidhinetra_pipeline.duplicates.candidates import fingerprint


@dataclass(frozen=True)
class Item:
    scope: str  # the constituency
    fingerprint_a: str  # each side's text_fingerprint, as in the artifact
    fingerprint_b: str
    text_a: str  # as published, every run of whitespace collapsed to one space
    text_b: str
    activity_a: str | None
    activity_b: str | None
    input_fingerprint: str  # over everything the judge reads, so a changed input is judged again


def items_from_artifact(artifact: dict[str, Any]) -> list[Item]:
    """One item per near-copy pair, in a fixed order. `artifact` must already be validated.

    The district audit's pairs are left out: that pass is stored and unfeatured.
    """
    groups = artifact["groups"]
    items = []
    for pair in artifact["pairs"]:
        if pair["finder"] != "near_copy":
            continue
        a, b = groups[pair["a"]], groups[pair["b"]]
        text_a, text_b = " ".join(a["text"].split()), " ".join(b["text"].split())
        read = json.dumps(
            [pair["scope"], text_a, a["activity"], text_b, b["activity"]], ensure_ascii=False
        )
        items.append(
            Item(
                pair["scope"],
                a["text_fingerprint"],
                b["text_fingerprint"],
                text_a,
                text_b,
                a["activity"],
                b["activity"],
                fingerprint(read),
            )
        )
    return sorted(items, key=lambda i: (i.scope, i.fingerprint_a, i.fingerprint_b))
