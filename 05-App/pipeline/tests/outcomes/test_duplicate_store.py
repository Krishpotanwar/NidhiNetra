"""Phase 1 Stage C: duplicate-review candidates and append-only review history."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from nidhinetra_pipeline.outcomes import duplicate_store
from nidhinetra_pipeline.outcomes import store as outcomes_store


def _candidate(
    scope: str = "C1",
    fingerprint: str = "1111111111111111",
    *,
    finder: str = "identical_batch",
    finder_version: str = "candidate_generation_v0",
    threshold_crossing_batch: bool = False,
    text: str = "PCC Road, near Ram House",
    work_ids: list[str] | None = None,
) -> dict[str, object]:
    return {
        "finder": finder,
        "scope": scope,
        "fingerprint_a": fingerprint,
        "fingerprint_b": fingerprint,
        "finder_version": finder_version,
        "threshold_crossing_batch": threshold_crossing_batch,
        "text": text,
        "work_ids": work_ids or ["W2", "W1"],
    }


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "outcomes" / "outcomes.db"


def test_init_db_coexists_with_inspection_outcomes_and_is_idempotent(db_path: Path) -> None:
    outcomes_store.init_db(db_path)
    duplicate_store.init_db(db_path)
    duplicate_store.init_db(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "inspection_outcomes" in tables
    assert "duplicate_candidates" in tables
    assert "duplicate_reviews" in tables


def test_new_candidate_is_pending_and_work_ids_are_sorted_and_deduplicated(
    db_path: Path,
) -> None:
    assert (
        duplicate_store.upsert_candidates(
            [_candidate(work_ids=["W2", "W1", "W2"])], db_path=db_path
        )
        == 1
    )

    rows, total = duplicate_store.list_candidates(status="pending", db_path=db_path)

    assert total == 1
    assert rows[0]["candidate_id"] > 0
    assert rows[0]["status"] == "pending"
    assert rows[0]["current_review"] is None
    assert rows[0]["work_ids"] == ["W1", "W2"]
    assert rows[0]["threshold_crossing_batch"] is False


def test_fingerprints_are_stored_sorted_even_if_given_reversed(db_path: Path) -> None:
    candidate = _candidate()
    candidate["fingerprint_a"], candidate["fingerprint_b"] = "2222222222222222", "1111111111111111"

    duplicate_store.upsert_candidates([candidate], db_path=db_path)

    rows, _ = duplicate_store.list_candidates(db_path=db_path)
    assert (rows[0]["fingerprint_a"], rows[0]["fingerprint_b"]) == (
        "1111111111111111",
        "2222222222222222",
    )


def test_upsert_preserves_candidate_id_and_review_while_refreshing_evidence(
    db_path: Path,
) -> None:
    duplicate_store.upsert_candidates([_candidate()], db_path=db_path)
    original = duplicate_store.list_candidates(db_path=db_path)[0][0]
    review_id = duplicate_store.record_review(
        original["candidate_id"],
        "confirmed_same",
        "RK",
        "Checked both work orders.",
        db_path=db_path,
    )

    duplicate_store.upsert_candidates(
        [_candidate(threshold_crossing_batch=True, work_ids=["W9", "W3", "W1"])],
        db_path=db_path,
    )

    current = duplicate_store.get_candidate(original["candidate_id"], db_path=db_path)
    assert current is not None
    assert current["candidate_id"] == original["candidate_id"]
    assert current["threshold_crossing_batch"] is True
    assert current["work_ids"] == ["W1", "W3", "W9"]
    assert current["status"] == "confirmed_same"
    assert current["current_review"]["review_id"] == review_id
    assert len(duplicate_store.get_review_history(original["candidate_id"], db_path=db_path)) == 1


def test_bulk_upsert_is_atomic_when_one_candidate_is_invalid(db_path: Path) -> None:
    invalid = _candidate(work_ids=["only-one"])

    with pytest.raises(duplicate_store.DuplicateStoreCandidateValidationError):
        duplicate_store.upsert_candidates([_candidate(), invalid], db_path=db_path)

    rows, total = duplicate_store.list_candidates(db_path=db_path)
    assert rows == []
    assert total == 0


def test_invalid_review_status_and_unknown_candidate_write_nothing(db_path: Path) -> None:
    duplicate_store.upsert_candidates([_candidate()], db_path=db_path)
    candidate_id = duplicate_store.list_candidates(db_path=db_path)[0][0]["candidate_id"]

    with pytest.raises(duplicate_store.UnknownDuplicateReviewStatusError):
        duplicate_store.record_review(candidate_id, "duplicate", "RK", db_path=db_path)
    with pytest.raises(duplicate_store.DuplicateCandidateNotFoundError):
        duplicate_store.record_review(999_999, "confirmed_same", "RK", db_path=db_path)

    assert duplicate_store.get_review_history(candidate_id, db_path=db_path) == []


def test_later_review_is_append_only_and_automatically_supersedes_current(
    db_path: Path,
) -> None:
    duplicate_store.upsert_candidates([_candidate()], db_path=db_path)
    candidate_id = duplicate_store.list_candidates(db_path=db_path)[0][0]["candidate_id"]
    first_time = datetime(2026, 9, 22, 8, 30, tzinfo=UTC)
    second_time = datetime(2026, 9, 22, 9, 45, tzinfo=UTC)

    first_id = duplicate_store.record_review(
        candidate_id, "confirmed_same", "RK", "Same wording.", now=first_time, db_path=db_path
    )
    second_id = duplicate_store.record_review(
        candidate_id,
        "rejected_different",
        "AB",
        "Two separate installations, checked on site.",
        now=second_time,
        db_path=db_path,
    )

    history = duplicate_store.get_review_history(candidate_id, db_path=db_path)
    assert [row["review_id"] for row in history] == [first_id, second_id]
    assert history[0]["supersedes"] is None
    assert history[0]["reviewed_at"] == "2026-09-22T08:30:00Z"
    assert history[1]["supersedes"] == first_id

    current = duplicate_store.get_candidate(candidate_id, db_path=db_path)
    assert current is not None
    assert current["status"] == "rejected_different"
    assert current["current_review"]["review_id"] == second_id


def test_status_filter_and_pagination_use_current_review_only(db_path: Path) -> None:
    duplicate_store.upsert_candidates(
        [
            _candidate("C1", "1111111111111111"),
            _candidate("C2", "2222222222222222"),
            _candidate("C3", "3333333333333333"),
        ],
        db_path=db_path,
    )
    all_rows, _ = duplicate_store.list_candidates(status=None, db_path=db_path)
    ids = {row["scope"]: row["candidate_id"] for row in all_rows}
    duplicate_store.record_review(ids["C1"], "confirmed_same", "RK", db_path=db_path)
    duplicate_store.record_review(ids["C2"], "rejected_different", "RK", db_path=db_path)

    pending, pending_total = duplicate_store.list_candidates(
        status="pending", page=1, page_size=1, db_path=db_path
    )
    confirmed, confirmed_total = duplicate_store.list_candidates(
        status="confirmed_same", db_path=db_path
    )
    rejected, rejected_total = duplicate_store.list_candidates(
        status="rejected_different", db_path=db_path
    )

    assert pending_total == 1
    assert [row["scope"] for row in pending] == ["C3"]
    assert confirmed_total == 1
    assert [row["scope"] for row in confirmed] == ["C1"]
    assert rejected_total == 1
    assert [row["scope"] for row in rejected] == ["C2"]


def test_candidates_for_work_finds_every_batch_that_includes_it(db_path: Path) -> None:
    duplicate_store.upsert_candidates(
        [
            _candidate("C1", "1111111111111111", work_ids=["W1", "W2"]),
            _candidate("C2", "2222222222222222", work_ids=["W2", "W3"]),
            _candidate("C3", "3333333333333333", work_ids=["W4", "W5"]),
        ],
        db_path=db_path,
    )

    found = duplicate_store.candidates_for_work("W2", db_path=db_path)

    assert {row["scope"] for row in found} == {"C1", "C2"}
    assert duplicate_store.candidates_for_work("W9", db_path=db_path) == []


def test_duplicate_context_summarizes_without_the_work_itself(db_path: Path) -> None:
    duplicate_store.upsert_candidates(
        [
            _candidate(
                "C1",
                "1111111111111111",
                threshold_crossing_batch=True,
                work_ids=["W1", "W2", "W3"],
            )
        ],
        db_path=db_path,
    )
    candidate_id = duplicate_store.list_candidates(db_path=db_path)[0][0]["candidate_id"]
    duplicate_store.record_review(candidate_id, "confirmed_same", "RK", db_path=db_path)

    context = duplicate_store.duplicate_context("W2", db_path=db_path)

    assert context == [
        {
            "candidate_id": candidate_id,
            "finder": "identical_batch",
            "threshold_crossing_batch": True,
            "text": "PCC Road, near Ram House",
            "work_count": 3,
            "other_work_ids": ["W1", "W3"],
            "status": "confirmed_same",
        }
    ]
    assert duplicate_store.duplicate_context("W9", db_path=db_path) == []


def test_duplicate_context_includes_the_near_copy_fields_only_when_present(db_path: Path) -> None:
    identical, judged = (
        _candidate("C1", "1111111111111111"),
        {
            "finder": "judged_same_asset_same_place",
            "scope": "C2",
            "fingerprint_a": "2222222222222222",
            "fingerprint_b": "3333333333333333",
            "finder_version": "work_candidate_derivation_v1",
            "threshold_crossing_batch": False,
            "text": "Shed at Kheda Chowk",
            "text_b": "Shed near Kheda Chowk",
            "quote_a": "Kheda Chowk",
            "quote_b": "Kheda Chowk",
            "work_relation": "duplicate_candidate",
            "work_ids": ["W3", "W4"],
        },
    )
    duplicate_store.upsert_candidates([identical, judged], db_path=db_path)

    identical_context = duplicate_store.duplicate_context("W1", db_path=db_path)[0]
    judged_context = duplicate_store.duplicate_context("W3", db_path=db_path)[0]

    assert "text_b" not in identical_context
    assert "work_relation" not in identical_context
    assert judged_context["text_b"] == "Shed near Kheda Chowk"
    assert judged_context["quote_a"] == "Kheda Chowk"
    assert judged_context["quote_b"] == "Kheda Chowk"
    assert judged_context["work_relation"] == "duplicate_candidate"
    assert judged_context["other_work_ids"] == ["W4"]
