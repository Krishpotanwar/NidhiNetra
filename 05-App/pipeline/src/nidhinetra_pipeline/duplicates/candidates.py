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
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

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


_Members = dict[tuple[str, str], list[dict[str, Any]]]  # (scope, canonical text) -> works
_Side = tuple[str, str, str]  # (canonical text, group id, text fingerprint)
_Register = Callable[[str, str, list[dict[str, Any]]], _Side]


def _mode(values: list[str]) -> str | None:
    """The most common value, the smallest on a tie, None for an empty list."""
    counts = Counter(values)
    return min(counts, key=lambda value: (-counts[value], value)) if counts else None


def _text_group(scope: str, canonical: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    amounts = [record["sanctioned_amount_inr"] for record in records]
    dates = sorted(record["sanction_date"] for record in records if record["sanction_date"])
    return {
        "scope": scope,
        "text_fingerprint": fingerprint(canonical),
        "text": _mode([record["work_description"] for record in records]),
        "activity": _mode([r["activity_name"] for r in records if r["activity_name"]]),
        "constituencies": sorted({record["constituency"] for record in records}),
        "work_ids": sorted(record["work_id"] for record in records),
        "work_count": len(records),
        "amount_min_inr": round(min(amounts), 2),
        "amount_max_inr": round(max(amounts), 2),
        "amount_total_inr": round(sum(amounts), 2),
        "sanction_date_first": dates[0] if dates else None,
        "sanction_date_last": dates[-1] if dates else None,
        "agencies": sorted({r["implementing_agency"] for r in records if r["implementing_agency"]}),
        "statuses": dict(sorted(Counter(r["completion_status"] for r in records).items())),
    }


def _batch(finder: str, scope: str, group_id: str, group: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": _candidate_id(finder, scope, group["text_fingerprint"]),
        "finder": finder,
        "scope": scope,
        "threshold_crossing_batch": (
            group["amount_max_inr"] < PER_WORK_LIMIT_INR
            and group["amount_total_inr"] >= GROUP_TOTAL_FLOOR_INR
        ),
        "group": group_id,
    }


def _index(records: list[dict[str, Any]]) -> tuple[_Members, _Members, int]:
    """Works by (constituency, canonical text) and by (district authority, canonical text), and the
    number of works with a description that has at least one letter or digit.
    """
    by_constituency: _Members = defaultdict(list)
    by_district: _Members = defaultdict(list)
    considered = 0
    for record in records:
        canonical = canonical_description_v1(record["work_description"] or "")
        if not canonical:
            continue
        considered += 1
        by_constituency[(record["constituency"], canonical)].append(record)
        if record["implementing_district_authority"]:
            by_district[(record["implementing_district_authority"], canonical)].append(record)
    return by_constituency, by_district, considered


def _registrar(groups: dict[str, dict[str, Any]]) -> _Register:
    """`register(scope, canonical, members)` stores a text group once and returns the side tuple
    (canonical text, group id, text fingerprint) that batches and pairs refer to.
    """

    def register(scope: str, canonical: str, members: list[dict[str, Any]]) -> _Side:
        text_fingerprint = fingerprint(canonical)
        group_id = _candidate_id("group", scope, text_fingerprint)
        if group_id not in groups:
            groups[group_id] = _text_group(scope, canonical, members)
        return canonical, group_id, text_fingerprint

    return register


def _identical_batches(
    by_constituency: _Members, register: _Register, groups: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Finder 1: two or more works in one constituency with the same canonical description."""
    batches = []
    for (scope, canonical), members in sorted(by_constituency.items()):
        if len(members) >= 2:
            _, group_id, _ = register(scope, canonical, members)
            batches.append(_batch("identical_batch", scope, group_id, groups[group_id]))
    return batches


def _artifact(
    considered: int,
    groups: dict[str, dict[str, Any]],
    batches: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    by_finder = Counter(candidate["finder"] for candidate in batches + pairs)
    by_difference = Counter(
        pair["difference_group"] for pair in pairs if pair["finder"] == "near_copy"
    )
    artifact = {
        "meta": {
            "canonical_version": CANONICAL_VERSION,
            "finder_version": FINDER_VERSION,
            "thresholds": {
                "character_similarity_min": CHARACTER_SIMILARITY_MIN,
                "token_jaccard_min": TOKEN_JACCARD_MIN,
                "token_shared_min": TOKEN_SHARED_MIN,
                "district_character_similarity_min": DISTRICT_CHARACTER_SIMILARITY_MIN,
                "per_work_limit_inr": PER_WORK_LIMIT_INR,
                "group_total_floor_inr": GROUP_TOTAL_FLOOR_INR,
            },
            "common_tokens": sorted(COMMON_TOKENS_V0),
            "counts": {
                "works_considered": considered,
                "groups": len(groups),
                "identical_batches": by_finder["identical_batch"],
                "threshold_crossing_batches": sum(
                    batch["threshold_crossing_batch"]
                    for batch in batches
                    if batch["finder"] == "identical_batch"
                ),
                "district_identical_batches": by_finder["district_identical_batch"],
                "near_copy_pairs": by_finder["near_copy"],
                "reworded_match": by_difference["reworded_match"],
                "one_sided_detail": by_difference["one_sided_detail"],
                "conflicting_detail": by_difference["conflicting_detail"],
                "district_near_copy_pairs": by_finder["district_near_copy"],
            },
        },
        "groups": groups,
        "batches": batches,
        "pairs": pairs,
    }
    validate_duplicate_candidates(artifact)
    return artifact


_Index = tuple[dict[str, int], csr_matrix, csr_matrix]  # row of each text, TF-IDF, content tokens


def _difference_group(only_a: list[str], only_b: list[str]) -> str:
    if not only_a and not only_b:
        return "reworded_match"
    if not only_a or not only_b:
        return "one_sided_detail"
    return "conflicting_detail"


def _pair(
    finder: str,
    scope: str,
    side_a: _Side,
    side_b: _Side,
    cosine: float,
    hits: list[str],
) -> dict[str, Any]:
    """Each side is (canonical text, group id, text fingerprint). The finders walk a block in
    sorted order, so `a` is always the side whose canonical text sorts first.
    """
    (canonical_a, group_a, fp_a), (canonical_b, group_b, fp_b) = side_a, side_b
    tokens_a, tokens_b = set(content_tokens(canonical_a)), set(content_tokens(canonical_b))
    union = tokens_a | tokens_b
    only_a, only_b = sorted(tokens_a - tokens_b), sorted(tokens_b - tokens_a)
    return {
        "candidate_id": _candidate_id(finder, scope, fp_a, fp_b),
        "finder": finder,
        "scope": scope,
        "hits": hits,
        "character_similarity": cosine,
        "token_overlap": (
            round(len(tokens_a & tokens_b) / len(union), SCORE_DECIMALS) if union else 0.0
        ),
        "difference_group": _difference_group(only_a, only_b),
        "shared_tokens": sorted(tokens_a & tokens_b),
        "only_a_tokens": only_a,
        "only_b_tokens": only_b,
        "a": group_a,
        "b": group_b,
    }


def _token_matrix(canonicals: list[str]) -> csr_matrix:
    """Row per text, column per content token, 1 where the text has the token."""
    vocabulary: dict[str, int] = {}
    rows: list[int] = []
    cols: list[int] = []
    for row, canonical in enumerate(canonicals):
        for token in set(content_tokens(canonical)):
            rows.append(row)
            cols.append(vocabulary.setdefault(token, len(vocabulary)))
    return csr_matrix(
        (np.ones(len(rows), dtype=np.int32), (rows, cols)),
        shape=(len(canonicals), max(len(vocabulary), 1)),
    )


def _similar_pairs(
    idx: list[int],
    tfidf: csr_matrix,
    tokens: csr_matrix,
    character_min: float,
    use_tokens: bool,
) -> Iterator[tuple[int, int, float, list[str]]]:
    """(i, j, cosine, hits) for every pair of the texts at matrix rows `idx` that clears the
    character threshold or, when `use_tokens`, the token-overlap threshold. i < j are positions
    within `idx`. The whole block is compared, one dense matrix at a time (largest block: 1,371).
    """
    if len(idx) < 2:
        return
    cosine = np.round((tfidf[idx] @ tfidf[idx].T).toarray(), SCORE_DECIMALS)
    by_character = cosine >= character_min
    by_token = np.zeros_like(by_character)
    if use_tokens:
        shared = (tokens[idx] @ tokens[idx].T).toarray()
        size = np.asarray(tokens[idx].sum(axis=1)).ravel()
        union = size[:, None] + size[None, :] - shared
        jaccard = np.round(
            np.divide(shared, union, out=np.zeros(shared.shape), where=union > 0), SCORE_DECIMALS
        )
        by_token = (shared >= TOKEN_SHARED_MIN) & (jaccard >= TOKEN_JACCARD_MIN)
    for i, j in np.argwhere(np.triu(by_character | by_token, 1)):
        hit_by = (("character", by_character[i, j]), ("token", by_token[i, j]))
        yield int(i), int(j), float(cosine[i, j]), [name for name, hit in hit_by if hit]


def _similarity_index(canonicals: list[str]) -> _Index:
    """Row per distinct canonical text: character TF-IDF (fitted on all of them, so every block
    shares one vocabulary) and the content-token matrix.
    """
    row_of = {canonical: row for row, canonical in enumerate(canonicals)}
    tfidf = (
        TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=False)
        .fit(canonicals)
        .transform(canonicals)
        .tocsr()
    )
    return row_of, tfidf, _token_matrix(canonicals)


def _near_copy_pairs(
    by_constituency: _Members, register: _Register, index: _Index
) -> list[dict[str, Any]]:
    """Finder 2: distinct texts in the same constituency. Blocking by constituency is a blocking
    rule, not a claim that works cannot repeat across constituencies (Finder 3 looks there).
    """
    row_of, tfidf, tokens = index
    block_texts: dict[str, list[str]] = defaultdict(list)
    for scope, canonical in sorted(by_constituency):
        block_texts[scope].append(canonical)
    pairs = []
    for scope, block in block_texts.items():
        idx = [row_of[canonical] for canonical in block]
        for i, j, cosine, hits in _similar_pairs(
            idx, tfidf, tokens, CHARACTER_SIMILARITY_MIN, use_tokens=True
        ):
            side_i = register(scope, block[i], by_constituency[(scope, block[i])])
            side_j = register(scope, block[j], by_constituency[(scope, block[j])])
            pairs.append(_pair("near_copy", scope, side_i, side_j, cosine, hits))
    return pairs


def _district_audit(
    by_district: _Members,
    register: _Register,
    groups: dict[str, dict[str, Any]],
    index: _Index,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Finder 3, the quiet audit: one district authority, works in different constituencies."""
    row_of, tfidf, tokens = index
    batches: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    block_texts: dict[str, list[str]] = defaultdict(list)
    for authority, canonical in sorted(by_district):
        block_texts[authority].append(canonical)
        members = by_district[(authority, canonical)]
        if len({member["constituency"] for member in members}) >= 2:
            _, group_id, _ = register(authority, canonical, members)
            batches.append(
                _batch("district_identical_batch", authority, group_id, groups[group_id])
            )
    for authority, block in block_texts.items():
        idx = [row_of[canonical] for canonical in block]
        for i, j, cosine, _hits in _similar_pairs(
            idx, tfidf, tokens, DISTRICT_CHARACTER_SIMILARITY_MIN, use_tokens=False
        ):
            members_i = by_district[(authority, block[i])]
            members_j = by_district[(authority, block[j])]
            if len({member["constituency"] for member in members_i + members_j}) < 2:
                continue  # one constituency only: Finder 2 already looked there
            side_i = register(authority, block[i], members_i)
            side_j = register(authority, block[j], members_j)
            pairs.append(
                _pair("district_near_copy", authority, side_i, side_j, cosine, ["character"])
            )
    return batches, pairs


def build_duplicate_candidates(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Finder 1 (identical batches), Finder 2 (near-copy pairs) and Finder 3 (the quiet district
    audit) over the works whose description has at least one letter or digit. Validated against
    duplicate_candidates.schema.json before it is returned. Never modifies `records`.
    """
    by_constituency, by_district, considered = _index(records)
    groups: dict[str, dict[str, Any]] = {}
    register = _registrar(groups)
    batches = _identical_batches(by_constituency, register, groups)
    pairs: list[dict[str, Any]] = []
    if by_constituency:
        index = _similarity_index(sorted({canonical for _, canonical in by_constituency}))
        pairs += _near_copy_pairs(by_constituency, register, index)
        district_batches, district_pairs = _district_audit(by_district, register, groups, index)
        batches += district_batches
        pairs += district_pairs
    return _artifact(considered, groups, batches, pairs)
