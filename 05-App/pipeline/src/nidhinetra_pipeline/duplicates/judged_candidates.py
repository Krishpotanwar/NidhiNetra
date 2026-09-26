"""Phase 1 Stage D-lite: judged same_asset_same_place pairs -> work-level review candidates.

Code, not AI (spec: "From a text answer to a work-level candidate (code, not AI)"). Every input
row here is already judged and already quote-verified: nidhinetra_pipeline.judge.verify rejected
any answer whose quotes are not literally present in their own text, and, for a
same_asset_same_place or same_place_different_asset answer, whose place quotes do not canonically
match on both sides (nidhinetra_pipeline.duplicates.candidates.canonical_description_v1). A
rejected answer never reaches status "judged", so a judged same_asset_same_place row here always
has a non-null, canonically-matching place_a/place_b -- this module trusts that and does not
re-check it.

Two things this module adds on top of that:

1. The discriminating-fact filter (DISCRIMINATING_STOPLIST_V1): a place quote made only of generic
   words ("Shamshan Ghat", a cremation ground, with no village or ward attached) is not enough to
   send an officer anywhere -- see the Stage B trial's GURDASPUR case,
   docs/superpowers/plans/2026-09-22-phase-1-stage-b-pair-judge.md.
2. work_candidate_derivation_v1, exactly as frozen in
   docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md ("From a text answer
   to a work-level candidate"). A text pair whose either side already groups more than one
   identically-worded work is labelled split_or_phase_candidate without inventing a per-work-pair
   date/amount comparison the frozen rule does not define for a group (see the Stage D-lite plan's
   Decision D2 on why, and the measured count this affects).
"""

from __future__ import annotations

import contextlib
from datetime import date
from pathlib import Path
from typing import Any, Literal

import duckdb
import pandas as pd

from .candidates import canonical_description_v1

DERIVATION_VERSION = "work_candidate_derivation_v1"
STORE_FINDER = "judged_same_asset_same_place"

# The Stage D-lite plan's own frozen list (Decision D3). Stage D may widen this from measured
# review-queue noise; any change is a new version name.
DISCRIMINATING_STOPLIST_V1 = frozenset(
    "village gram ward road school shamshan ghat community hall".split()
)

# Spec, verbatim ("From a text answer to a work-level candidate").
CONTINUATION_MARKERS_V1 = ("phase", "continuation", "continue", "remaining", "balance work")


def is_discriminating(place_quote: str) -> bool:
    """True when the quoted place/institution has at least one token that is not in the frozen,
    generic stoplist. place_a and place_b are already guaranteed to canonically match by
    nidhinetra_pipeline.judge.verify.check_answer, so checking either side's quote is equivalent;
    this checks the one it is given.
    """
    tokens = canonical_description_v1(place_quote).split()
    return any(token not in DISCRIMINATING_STOPLIST_V1 for token in tokens)


def _has_continuation_marker(text_a: str, text_b: str) -> bool:
    canonical_a = canonical_description_v1(text_a)
    canonical_b = canonical_description_v1(text_b)
    return any(marker in canonical_a or marker in canonical_b for marker in CONTINUATION_MARKERS_V1)


def _work_relation(
    group_a: dict[str, Any], group_b: dict[str, Any]
) -> Literal["duplicate_candidate", "split_or_phase_candidate"]:
    """work_candidate_derivation_v1, applied to a judged same_asset_same_place pair's two text
    groups (see the module docstring and the plan's Decision D2 for the multi-work case)."""
    if _has_continuation_marker(group_a["text"], group_b["text"]):
        return "split_or_phase_candidate"
    if group_a["work_count"] != 1 or group_b["work_count"] != 1:
        return "split_or_phase_candidate"
    date_a, date_b = group_a["sanction_date_first"], group_b["sanction_date_first"]
    amount_a, amount_b = group_a["amount_total_inr"], group_b["amount_total_inr"]
    if not date_a or not date_b or not amount_a or not amount_b:
        return "split_or_phase_candidate"
    gap_days = abs((date.fromisoformat(date_a) - date.fromisoformat(date_b)).days)
    ratio = min(amount_a, amount_b) / max(amount_a, amount_b)
    if gap_days <= 365 and ratio >= 0.5:
        return "duplicate_candidate"
    return "split_or_phase_candidate"


def build_judged_candidates(
    artifact: dict[str, Any], judgments: pd.DataFrame
) -> list[dict[str, Any]]:
    """One review-store candidate per judged same_asset_same_place pair whose place quote is
    discriminating. fingerprint_a/fingerprint_b are sorted here (matching
    outcomes.duplicate_store's own sort of every candidate it stores), with text/quote swapped
    along with them, so the store's later re-sort of an already-sorted pair is a no-op.
    """
    groups_by_scope_fp = {
        (group["scope"], group["text_fingerprint"]): group for group in artifact["groups"].values()
    }
    same_asset_same_place = judgments[
        (judgments["status"] == "judged") & (judgments["relation"] == "same_asset_same_place")
    ]
    candidates = []
    for row in same_asset_same_place.itertuples():
        if not is_discriminating(row.place_a):
            continue
        fingerprint_a, fingerprint_b = row.fingerprint_a, row.fingerprint_b
        quote_a, quote_b = row.place_a, row.place_b
        group_a = groups_by_scope_fp[(row.scope, fingerprint_a)]
        group_b = groups_by_scope_fp[(row.scope, fingerprint_b)]
        if fingerprint_a > fingerprint_b:
            fingerprint_a, fingerprint_b = fingerprint_b, fingerprint_a
            quote_a, quote_b = quote_b, quote_a
            group_a, group_b = group_b, group_a
        candidates.append(
            {
                "finder": STORE_FINDER,
                "scope": row.scope,
                "fingerprint_a": fingerprint_a,
                "fingerprint_b": fingerprint_b,
                "finder_version": DERIVATION_VERSION,
                "threshold_crossing_batch": False,
                "text": group_a["text"],
                "text_b": group_b["text"],
                "quote_a": quote_a,
                "quote_b": quote_b,
                "work_relation": _work_relation(group_a, group_b),
                "work_ids": sorted(set(group_a["work_ids"]) | set(group_b["work_ids"])),
            }
        )
    return candidates


# The only judgments columns build_judged_candidates reads (see that function above): the
# place-quote filter needs status/relation/place_a, the fingerprint join needs
# scope/fingerprint_a/fingerprint_b, and place_b is carried through as quote_b. The judgments
# file's full 16-column schema (model_id, run_timestamp, ...) is provenance for the judge run
# itself, not needed to derive a candidate.
_CANDIDATE_JUDGMENT_COLUMNS = (
    "scope",
    "fingerprint_a",
    "fingerprint_b",
    "status",
    "relation",
    "place_a",
    "place_b",
)


def read_candidate_judgments(path: Path) -> pd.DataFrame:
    """The judgments build_judged_candidates needs: only _CANDIDATE_JUDGMENT_COLUMNS, pre-filtered
    to its own same_asset_same_place & judged mask (build_judged_candidates re-applies the
    identical predicate, harmlessly, to an already-filtered frame).

    Reads via DuckDB, not this module's own pandas -- specifically never through
    nidhinetra_pipeline.judge.store.read_judgments's pd.read_parquet (T12B.5 fix round 1).
    Measured cause: pandas' parquet engine (pyarrow) pays a large one-time initialization cost
    the first time a process calls pd.read_parquet at all -- ~100+ MB, independent of how narrow
    the query is (confirmed empirically: an identical second read cost ~18 MB more; a third read
    of 30x more data cost ~24 MB more). nidhinetra_api must never pay that on its sync path or,
    worse, on a live GET /api/duplicates request. DuckDB has no such fixed tax for a ~1.6 MB
    file. The returned DataFrame is built with pandas' own constructor from plain query-result
    tuples, not read_parquet, so pyarrow is never touched by this function either.
    """
    columns_sql = ", ".join(_CANDIDATE_JUDGMENT_COLUMNS)
    sql = (
        f"SELECT {columns_sql} FROM read_parquet('{path.as_posix()}') "  # noqa: S608
        "WHERE status = 'judged' AND relation = 'same_asset_same_place'"
    )
    with contextlib.closing(duckdb.connect(":memory:")) as connection:
        rows = connection.execute(sql).fetchall()
    return pd.DataFrame(rows, columns=_CANDIDATE_JUDGMENT_COLUMNS)


def judge_rates(judgments: pd.DataFrame) -> dict[str, float]:
    """The two rates the spec allows reporting: abstention and quote-rejection, both of every
    pair asked -- never of judged pairs only, and never an agreement or accuracy figure (there is
    no two-model reference in Stage D-lite)."""
    total = len(judgments)
    if total == 0:
        return {"abstention_rate": 0.0, "quote_rejection_rate": 0.0, "pairs_total": 0}
    rejected = int((judgments["status"] == "rejected").sum())
    abstained = int(
        ((judgments["status"] == "judged") & (judgments["relation"] == "not_enough_detail")).sum()
    )
    return {
        "abstention_rate": round(100 * abstained / total, 1),
        "quote_rejection_rate": round(100 * rejected / total, 1),
        "pairs_total": total,
    }


__all__ = [
    "CONTINUATION_MARKERS_V1",
    "DERIVATION_VERSION",
    "DISCRIMINATING_STOPLIST_V1",
    "STORE_FINDER",
    "build_judged_candidates",
    "is_discriminating",
    "judge_rates",
    "read_candidate_judgments",
]
