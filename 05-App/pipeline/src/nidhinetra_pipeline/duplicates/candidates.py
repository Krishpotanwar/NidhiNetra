"""Phase 1 Stage A: candidate generation for duplicate and split works.

Pure functions over normalized records: no model, no network, no clock. The same records give the
same candidates in the same order, so the artifact can be committed and reviewed like any other
snapshot file. Nothing here reads or changes a work's score, rank or flags.

Spec: docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any

import jsonschema

# duplicates/candidates.py -> parents[4] is "05-App/".
_APP_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = _APP_ROOT / "contracts" / "duplicate_candidates.schema.json"

CANONICAL_VERSION = "canonical_description_v1"
FINDER_VERSION = "candidate_generation_v0"

# candidate_generation_v0. Stage D may revise these once, after which the version becomes v1.
CHARACTER_SIMILARITY_MIN = 0.80
TOKEN_JACCARD_MIN = 0.75
TOKEN_SHARED_MIN = 3
DISTRICT_CHARACTER_SIMILARITY_MIN = 0.90
# MPLADS Guidelines 2023 clause 4.4.2: third-party inspection is compulsory from Rs 25 lakh and
# needs 50% coverage between Rs 15 and 25 lakh.
PER_WORK_LIMIT_INR = 1_500_000
GROUP_TOTAL_FLOOR_INR = 2_500_000
# A score is rounded before it meets a threshold, so a pair sitting on a threshold is decided the
# same way on every machine.
SCORE_DECIMALS = 4

# The 19 words that appear in at least 10% of the distinct canonical descriptions of the
# 2026-09-04 capture (a 20th, "work", sits at 9.99%). They say what kind of work it is, not which
# work, so token overlap ignores them. Frozen: a list derived from the data would move with every
# rebuild.
COMMON_TOKENS_V0 = frozenset(
    "and at block construction from gram high house in installation ke light near no of "
    "panchayat road to village".split()
)


class DuplicateCandidateValidationError(Exception):
    """Raised instead of returning an artifact that breaks duplicate_candidates.schema.json."""


def canonical_description_v1(text: str) -> str:
    """NFKC, casefold, then every run of characters that are not letters, digits or combining
    marks becomes one space. Digits are kept; nothing is stemmed, corrected or dropped. Any change
    to this rule is a new version, because the same data would group differently.
    """
    out: list[str] = []
    gap = True
    for char in unicodedata.normalize("NFKC", text).casefold():
        if unicodedata.category(char)[0] in "LNM":
            out.append(char)
            gap = False
        elif not gap:
            out.append(" ")
            gap = True
    return "".join(out).strip()


def content_tokens(canonical: str) -> list[str]:
    return [token for token in canonical.split() if token not in COMMON_TOKENS_V0]


def fingerprint(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _candidate_id(*parts: str) -> str:
    return hashlib.sha256("|".join((FINDER_VERSION, *parts)).encode("utf-8")).hexdigest()[:16]


def validate_duplicate_candidates(artifact: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = [
        f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message[:200]}"
        for error in jsonschema.Draft7Validator(schema).iter_errors(artifact)
    ]
    if errors:
        raise DuplicateCandidateValidationError(
            f"{len(errors)} violation(s) of duplicate_candidates.schema.json, first 10:\n"
            + "\n".join(errors[:10])
        )
