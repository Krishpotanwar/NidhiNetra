"""R-06 entity-alias candidates and append-only review history."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from nidhinetra_pipeline.outcomes import alias_store
from nidhinetra_pipeline.outcomes import store as outcomes_store


def _candidate(
    canonical_id: str = "vendor-42",
    alias_label: str = "ACME CONSTRUCTIONS",
    *,
    reason: str = "identifier_has_multiple_labels",
    evidence: list[str] | None = None,
) -> dict[str, object]:
    return {
        "entity_type": "vendor",
        "proposed_canonical_id": canonical_id,
        "alias_label": alias_label,
        "reason": reason,
        "evidence_work_ids": evidence or ["W2", "W1"],
    }


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "outcomes" / "outcomes.db"


def test_init_db_coexists_with_inspection_outcomes_and_is_idempotent(db_path: Path) -> None:
    outcomes_store.init_db(db_path)
    alias_store.init_db(db_path)
    alias_store.init_db(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "inspection_outcomes" in tables
    assert "entity_alias_candidates" in tables
    assert "entity_alias_reviews" in tables


def test_new_candidate_is_pending_and_evidence_is_sorted_and_deduplicated(
    db_path: Path,
) -> None:
    assert (
        alias_store.upsert_candidates([_candidate(evidence=["W2", "W1", "W2"])], db_path=db_path)
        == 1
    )

    rows, total = alias_store.list_candidates(status="pending", db_path=db_path)

    assert total == 1
    assert rows[0]["candidate_id"] > 0
    assert rows[0]["status"] == "pending"
    assert rows[0]["current_review"] is None
    assert rows[0]["evidence_work_ids"] == ["W1", "W2"]


def test_upsert_preserves_candidate_id_and_review_while_refreshing_evidence(
    db_path: Path,
) -> None:
    alias_store.upsert_candidates([_candidate()], db_path=db_path)
    original = alias_store.list_candidates(db_path=db_path)[0][0]
    review_id = alias_store.record_review(
        original["candidate_id"],
        "confirmed_merge",
        "RK",
        "Source documents use both labels.",
        db_path=db_path,
    )

    alias_store.upsert_candidates(
        [
            _candidate(
                reason="label_has_multiple_identifiers",
                evidence=["W9", "W3"],
            )
        ],
        db_path=db_path,
    )

    current = alias_store.get_candidate(original["candidate_id"], db_path=db_path)
    assert current is not None
    assert current["candidate_id"] == original["candidate_id"]
    assert current["reason"] == "label_has_multiple_identifiers"
    assert current["evidence_work_ids"] == ["W3", "W9"]
    assert current["status"] == "confirmed_merge"
    assert current["current_review"]["review_id"] == review_id
    assert len(alias_store.get_review_history(original["candidate_id"], db_path=db_path)) == 1


def test_bulk_upsert_is_atomic_when_one_candidate_is_invalid(db_path: Path) -> None:
    invalid = _candidate(alias_label="")

    with pytest.raises(alias_store.AliasCandidateValidationError):
        alias_store.upsert_candidates([_candidate(), invalid], db_path=db_path)

    rows, total = alias_store.list_candidates(db_path=db_path)
    assert rows == []
    assert total == 0


def test_invalid_review_status_and_unknown_candidate_write_nothing(db_path: Path) -> None:
    alias_store.upsert_candidates([_candidate()], db_path=db_path)
    candidate_id = alias_store.list_candidates(db_path=db_path)[0][0]["candidate_id"]

    with pytest.raises(alias_store.UnknownAliasReviewStatusError):
        alias_store.record_review(candidate_id, "merge", "RK", db_path=db_path)
    with pytest.raises(alias_store.AliasCandidateNotFoundError):
        alias_store.record_review(999_999, "confirmed_merge", "RK", db_path=db_path)

    assert alias_store.get_review_history(candidate_id, db_path=db_path) == []


def test_later_review_is_append_only_and_automatically_supersedes_current(
    db_path: Path,
) -> None:
    alias_store.upsert_candidates([_candidate()], db_path=db_path)
    candidate_id = alias_store.list_candidates(db_path=db_path)[0][0]["candidate_id"]
    first_time = datetime(2026, 9, 14, 8, 30, tzinfo=UTC)
    second_time = datetime(2026, 9, 14, 9, 45, tzinfo=UTC)

    first_id = alias_store.record_review(
        candidate_id,
        "confirmed_merge",
        "RK",
        "Same registration papers.",
        now=first_time,
        db_path=db_path,
    )
    second_id = alias_store.record_review(
        candidate_id,
        "rejected_distinct",
        "AB",
        "Correction after checking the source IDs.",
        now=second_time,
        db_path=db_path,
    )

    history = alias_store.get_review_history(candidate_id, db_path=db_path)
    assert [row["review_id"] for row in history] == [first_id, second_id]
    assert history[0]["supersedes"] is None
    assert history[0]["reviewed_at"] == "2026-09-14T08:30:00Z"
    assert history[1]["supersedes"] == first_id
    assert history[1]["reviewed_at"] == "2026-09-14T09:45:00Z"

    current = alias_store.get_candidate(candidate_id, db_path=db_path)
    assert current is not None
    assert current["status"] == "rejected_distinct"
    assert current["current_review"]["review_id"] == second_id


def test_status_filter_and_pagination_use_current_review_only(db_path: Path) -> None:
    alias_store.upsert_candidates(
        [
            _candidate("v1", "ALPHA"),
            _candidate("v2", "BETA"),
            _candidate("v3", "GAMMA"),
        ],
        db_path=db_path,
    )
    all_rows, _ = alias_store.list_candidates(status=None, db_path=db_path)
    ids = {row["proposed_canonical_id"]: row["candidate_id"] for row in all_rows}
    alias_store.record_review(ids["v1"], "confirmed_merge", "RK", db_path=db_path)
    alias_store.record_review(ids["v2"], "rejected_distinct", "RK", db_path=db_path)

    pending, pending_total = alias_store.list_candidates(
        status="pending", page=1, page_size=1, db_path=db_path
    )
    confirmed, confirmed_total = alias_store.list_candidates(
        status="confirmed_merge", db_path=db_path
    )
    rejected, rejected_total = alias_store.list_candidates(
        status="rejected_distinct", db_path=db_path
    )

    assert pending_total == 1
    assert [row["proposed_canonical_id"] for row in pending] == ["v3"]
    assert confirmed_total == 1
    assert [row["proposed_canonical_id"] for row in confirmed] == ["v1"]
    assert rejected_total == 1
    assert [row["proposed_canonical_id"] for row in rejected] == ["v2"]
