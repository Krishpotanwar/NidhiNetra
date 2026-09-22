"""The judgments file, data/judgments/text_pair_judgments.parquet.

One row for every pair a run got an evidence-checked reply for: judged, or rejected because a quote
was not in the text. A rejected row keeps no relation and no quote, so the pair stays unjudged. The
file can hold answers from more than one model (a bake-off), so every row says what produced it.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd

FILENAME = "text_pair_judgments.parquet"

COLUMNS = [
    "scope",
    "fingerprint_a",
    "fingerprint_b",
    "input_fingerprint",
    "status",  # "judged" or "rejected"
    "relation",
    "rejection",  # the rule a rejected answer broke
    "asset_a",
    "place_a",
    "asset_b",
    "place_b",
    "model_id",
    "provider_id",
    "prompt_version",
    "schema_version",
    "judge_code_version",
    "run_timestamp",
]

# What makes an earlier row an answer to the same question: the same model behind the same
# provider, asked with the same prompt and schema. judge_code_version is a stamp, not a key.
_ASKED = ("model_id", "provider_id", "prompt_version", "schema_version")


def read_judgments(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=COLUMNS)


def write_judgments(frame: pd.DataFrame, path: Path) -> None:
    """Atomic: a half-written file never replaces a good one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(handle)
    try:
        frame[COLUMNS].to_parquet(temp, index=False)
        os.replace(temp, path)
    except BaseException:
        os.unlink(temp)
        raise


def answered(frame: pd.DataFrame, stamp: dict[str, str]) -> set[tuple[str, str, str, str]]:
    """(scope, fingerprint_a, fingerprint_b, input_fingerprint) of every pair already answered
    under `stamp`'s model, provider, prompt and schema."""
    same = frame
    for column in _ASKED:
        same = same[same[column] == stamp[column]]
    return set(
        zip(
            same["scope"],
            same["fingerprint_a"],
            same["fingerprint_b"],
            same["input_fingerprint"],
            strict=True,
        )
    )
