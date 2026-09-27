"""Phase 1 Stage D-lite: judged same_asset_same_place pairs -> work-level review candidates."""

from __future__ import annotations

import pandas as pd
import pytest
from nidhinetra_pipeline.duplicates.judged_candidates import (
    CONTINUATION_MARKERS_V1,
    DERIVATION_VERSION,
    DISCRIMINATING_STOPLIST_V1,
    STORE_FINDER,
    build_judged_candidates,
    is_discriminating,
    judge_rates,
    read_candidate_judgments,
)


def _group(scope, fingerprint, text, work_ids, *, amount=500_000.0, sanction_date="2024-07-01"):
    return {
        "scope": scope,
        "text_fingerprint": fingerprint,
        "text": text,
        "work_ids": work_ids,
        "work_count": len(work_ids),
        "amount_total_inr": amount,
        "sanction_date_first": sanction_date,
    }


def _artifact(groups: dict) -> dict:
    return {"groups": groups}


def _judgment_row(
    scope,
    fp_a,
    fp_b,
    *,
    status="judged",
    relation="same_asset_same_place",
    place_a="Kheda Chowk",
    place_b="Kheda Chowk",
):
    return {
        "scope": scope,
        "fingerprint_a": fp_a,
        "fingerprint_b": fp_b,
        "status": status,
        "relation": relation,
        "place_a": place_a,
        "place_b": place_b,
    }


FP_A, FP_B = "a" * 16, "b" * 16


def test_duplicate_candidate_when_close_in_date_and_amount():
    groups = {
        "g1": _group(
            "C1", FP_A, "Shed at Kheda Chowk", ["W1"], amount=500_000.0, sanction_date="2024-07-01"
        ),
        "g2": _group(
            "C1",
            FP_B,
            "Shed near Kheda Chowk",
            ["W2"],
            amount=520_000.0,
            sanction_date="2024-07-31",
        ),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["finder"] == STORE_FINDER
    assert candidate["finder_version"] == DERIVATION_VERSION
    assert candidate["work_relation"] == "duplicate_candidate"
    assert candidate["threshold_crossing_batch"] is False
    assert candidate["text"] == "Shed at Kheda Chowk"
    assert candidate["text_b"] == "Shed near Kheda Chowk"
    assert candidate["quote_a"] == "Kheda Chowk"
    assert candidate["quote_b"] == "Kheda Chowk"
    assert candidate["work_ids"] == ["W1", "W2"]


def test_split_or_phase_when_date_gap_exceeds_one_year():
    groups = {
        "g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1"], sanction_date="2022-01-01"),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"], sanction_date="2024-07-31"),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["work_relation"] == "split_or_phase_candidate"


def test_split_or_phase_when_amount_ratio_is_below_half():
    groups = {
        "g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1"], amount=100_000.0),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"], amount=300_000.0),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["work_relation"] == "split_or_phase_candidate"


def test_split_or_phase_when_a_continuation_marker_is_present_even_if_date_and_amount_would_pass():
    groups = {
        "g1": _group("C1", FP_A, "Phase 2 shed at Kheda Chowk", ["W1"]),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"]),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["work_relation"] == "split_or_phase_candidate"


def test_split_or_phase_when_either_side_has_more_than_one_work():
    groups = {
        "g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1", "W3"], amount=1_000_000.0),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"], amount=500_000.0),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["work_relation"] == "split_or_phase_candidate"
    assert candidate["work_ids"] == ["W1", "W2", "W3"]


def test_non_discriminating_place_quote_is_excluded():
    groups = {
        "g1": _group("C1", FP_A, "Shed at village", ["W1"]),
        "g2": _group("C1", FP_B, "Shed near village", ["W2"]),
    }
    judgments = pd.DataFrame(
        [_judgment_row("C1", FP_A, FP_B, place_a="village", place_b="village")]
    )

    assert build_judged_candidates(_artifact(groups), judgments) == []
    assert is_discriminating("village") is False
    assert is_discriminating("Village") is False
    assert is_discriminating("Shamshan Ghat") is False
    assert is_discriminating("Kheda Chowk") is True


@pytest.mark.parametrize(
    ("status", "relation"),
    [("rejected", None), ("judged", "same_asset_different_place")],
    ids=["rejected pair", "different relation"],
)
def test_only_judged_same_asset_same_place_rows_are_considered(status, relation):
    groups = {
        "g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1"]),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"]),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B, status=status, relation=relation)])

    assert build_judged_candidates(_artifact(groups), judgments) == []


def test_fingerprint_order_is_sorted_and_text_quotes_follow_their_own_side():
    zzzz, aaaa = "z" * 16, "a" * 16
    groups = {
        "g1": _group(zzzz[:0] or "C1", zzzz, "Shed at Kheda Chowk near Ram Mandir", ["W2"]),
        "g2": _group("C1", aaaa, "Shed at Kheda Chowk near Shiv Mandir", ["W1"]),
    }
    judgments = pd.DataFrame([_judgment_row("C1", zzzz, aaaa)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["fingerprint_a"] == aaaa
    assert candidate["fingerprint_b"] == zzzz
    assert candidate["text"] == "Shed at Kheda Chowk near Shiv Mandir"
    assert candidate["text_b"] == "Shed at Kheda Chowk near Ram Mandir"
    assert candidate["work_ids"] == ["W1", "W2"]


def test_judge_rates_uses_every_pair_asked_as_the_population():
    rows = (
        [("judged", "same_asset_same_place")]
        + [("judged", "not_enough_detail")] * 3
        + [("rejected", None)] * 2
        + [("judged", "unrelated")]
        + [("judged", "same_asset_different_place")] * 2
        + [("judged", "same_place_different_asset")]
    )
    judgments = pd.DataFrame(
        [_judgment_row("C1", FP_A, FP_B, status=s, relation=r) for s, r in rows]
    )

    assert judge_rates(judgments) == {
        "abstention_rate": 30.0,
        "quote_rejection_rate": 20.0,
        "pairs_total": 10,
    }


def test_judge_rates_is_zero_on_an_empty_frame():
    assert judge_rates(pd.DataFrame(columns=["status", "relation"])) == {
        "abstention_rate": 0.0,
        "quote_rejection_rate": 0.0,
        "pairs_total": 0,
    }


def test_read_candidate_judgments_selects_columns_and_filters_rows(tmp_path):
    """T12B.5 fix round 1: reads via DuckDB, selecting only the seven columns
    build_judged_candidates needs and only judged/same_asset_same_place rows, dropping everything
    else -- both the extra provenance columns (model_id, run_timestamp) and the non-matching rows
    (rejected, or judged but a different relation)."""
    rows = [
        {**_judgment_row("C1", FP_A, FP_B), "model_id": "gpt-x", "run_timestamp": "2026-01-01"},
        {
            **_judgment_row("C1", FP_A, FP_B, status="rejected", relation=None),
            "model_id": "gpt-x",
            "run_timestamp": "2026-01-01",
        },
        {
            **_judgment_row("C1", FP_A, FP_B, relation="unrelated"),
            "model_id": "gpt-x",
            "run_timestamp": "2026-01-01",
        },
    ]
    path = tmp_path / "text_pair_judgments.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)

    result = read_candidate_judgments(path)

    assert list(result.columns) == [
        "scope",
        "fingerprint_a",
        "fingerprint_b",
        "status",
        "relation",
        "place_a",
        "place_b",
    ]
    assert len(result) == 1
    kept = result.iloc[0]
    assert (kept["status"], kept["relation"]) == ("judged", "same_asset_same_place")


def test_missing_group_is_skipped_and_logged(caplog):
    """Final review I1: T13's rebuild can drop a group that a stale judgment still names (the
    TF-IDF weights shift and it no longer clears the near-copy threshold). Reproduces the
    report's KeyError('SAGAR', ...) case -- the pair must be skipped, not raise, and the skip
    count logged so a rebuild's checklist can see it."""
    groups = {"g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1"])}
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])  # FP_B has no group

    with caplog.at_level("WARNING"):
        result = build_judged_candidates(_artifact(groups), judgments)

    assert result == []
    assert "1" in caplog.text
    assert "skip" in caplog.text.lower()


def test_frozen_constants_are_pinned():
    assert DERIVATION_VERSION == "work_candidate_derivation_v1"
    assert STORE_FINDER == "judged_same_asset_same_place"
    assert DISCRIMINATING_STOPLIST_V1 == frozenset(
        "village gram ward road school shamshan ghat community hall".split()
    )
    assert CONTINUATION_MARKERS_V1 == (
        "phase",
        "continuation",
        "continue",
        "remaining",
        "balance work",
    )
