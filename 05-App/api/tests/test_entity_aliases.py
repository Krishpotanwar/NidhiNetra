"""R-06 alias-review queue API and batched evidence resolution."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from nidhinetra_api import db
from nidhinetra_api.routers import entity_aliases
from nidhinetra_pipeline.outcomes import alias_store


def _candidate(
    canonical_id: str,
    alias_label: str,
    evidence_work_ids: list[str],
    *,
    reason: str = "identifier_has_multiple_labels",
) -> dict[str, object]:
    return {
        "entity_type": "vendor",
        "proposed_canonical_id": canonical_id,
        "alias_label": alias_label,
        "reason": reason,
        "evidence_work_ids": evidence_work_ids,
    }


@pytest.fixture()
def alias_client(client: TestClient, isolated_outcomes_db: Path) -> TestClient:
    """Start the real app, then clear only the per-test alias tables.

    Lifespan may have loaded candidates generated from the CP0 fixture. API
    tests seed their own small cases so pagination and status counts stay
    explicit rather than depending on that fixture's future ambiguity mix.
    """
    alias_store.init_db(isolated_outcomes_db)
    with sqlite3.connect(isolated_outcomes_db) as connection:
        connection.execute("DELETE FROM entity_alias_reviews")
        connection.execute("DELETE FROM entity_alias_candidates")
        connection.commit()
    return client


def _seed(candidates: list[dict[str, object]]) -> list[dict[str, Any]]:
    alias_store.upsert_candidates(candidates)
    return alias_store.list_candidates(status=None)[0]


def test_pending_queue_has_house_envelope_and_pagination(alias_client: TestClient) -> None:
    _seed(
        [
            _candidate("v1", "ALPHA", ["MPLADS-FX-0001"]),
            _candidate("v2", "BETA", ["MPLADS-FX-0002"]),
            _candidate("v3", "GAMMA", ["MPLADS-FX-0003"]),
        ]
    )

    response = alias_client.get(
        "/api/entity-aliases", params={"status": "pending", "page": 2, "page_size": 2}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"success", "data", "error", "meta"}
    assert body["success"] is True
    assert body["error"] is None
    assert [row["proposed_canonical_id"] for row in body["data"]] == ["v3"]
    assert body["meta"] == {
        "page": 2,
        "page_size": 2,
        "total": 3,
        "total_pages": 2,
    }


def test_status_filters_use_only_the_current_review(alias_client: TestClient) -> None:
    candidates = _seed(
        [
            _candidate("v1", "ALPHA", ["MPLADS-FX-0001"]),
            _candidate("v2", "BETA", ["MPLADS-FX-0002"]),
            _candidate("v3", "GAMMA", ["MPLADS-FX-0003"]),
        ]
    )
    ids = {row["proposed_canonical_id"]: row["candidate_id"] for row in candidates}
    alias_store.record_review(ids["v1"], "confirmed_merge", "RK")
    alias_store.record_review(ids["v2"], "rejected_distinct", "RK")

    pending = alias_client.get("/api/entity-aliases", params={"status": "pending"}).json()
    confirmed = alias_client.get("/api/entity-aliases", params={"status": "confirmed_merge"}).json()
    rejected = alias_client.get(
        "/api/entity-aliases", params={"status": "rejected_distinct"}
    ).json()

    assert [row["proposed_canonical_id"] for row in pending["data"]] == ["v3"]
    assert [row["proposed_canonical_id"] for row in confirmed["data"]] == ["v1"]
    assert confirmed["data"][0]["current_review"]["reviewed_by"] == "RK"
    assert [row["proposed_canonical_id"] for row in rejected["data"]] == ["v2"]


def test_page_evidence_is_resolved_with_one_batched_duckdb_query(
    alias_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    works = alias_client.get("/api/works", params={"page_size": 3}).json()["data"]
    work_ids = [row["work_id"] for row in works]
    _seed(
        [
            _candidate("v1", "ALPHA", [work_ids[1], work_ids[0]]),
            _candidate("v2", "BETA", [work_ids[1], work_ids[2]]),
        ]
    )
    calls: list[tuple[str, list[Any]]] = []
    real_rows_as_dicts = db.rows_as_dicts

    def recording_rows_as_dicts(con, sql: str, params: list[Any] | None = None):
        calls.append((sql, params or []))
        return real_rows_as_dicts(con, sql, params)

    monkeypatch.setattr(entity_aliases.db, "rows_as_dicts", recording_rows_as_dicts)

    body = alias_client.get("/api/entity-aliases", params={"status": "pending"}).json()

    evidence_queries = [call for call in calls if "works.work_id IN" in call[0]]
    assert len(evidence_queries) == 1
    assert set(evidence_queries[0][1]) == set(work_ids)
    by_id = {row["proposed_canonical_id"]: row for row in body["data"]}
    assert [work["work_id"] for work in by_id["v1"]["evidence_works"]] == sorted(
        [work_ids[0], work_ids[1]]
    )
    assert [work["work_id"] for work in by_id["v2"]["evidence_works"]] == sorted(
        [work_ids[1], work_ids[2]]
    )
    assert all("vendor_id" in work for row in body["data"] for work in row["evidence_works"])
    assert all(
        "implementing_district_authority" in work
        for row in body["data"]
        for work in row["evidence_works"]
    )


def test_review_post_assigns_history_fields_and_correction_supersedes(
    alias_client: TestClient,
) -> None:
    (candidate,) = _seed([_candidate("v1", "ALPHA", ["MPLADS-FX-0001"])])

    first = alias_client.post(
        f"/api/entity-aliases/{candidate['candidate_id']}/review",
        json={
            "status": "confirmed_merge",
            "reviewed_by": "RK",
            "reviewer_note": "The registrations match.",
        },
    )
    assert first.status_code == 200
    first_review = first.json()["data"]["current_review"]
    assert first_review["status"] == "confirmed_merge"
    assert first_review["reviewed_at"].endswith("Z")
    assert first_review["supersedes"] is None

    second = alias_client.post(
        f"/api/entity-aliases/{candidate['candidate_id']}/review",
        json={
            "status": "rejected_distinct",
            "reviewed_by": "AB",
            "reviewer_note": "Correction after checking the source IDs.",
        },
    )
    assert second.status_code == 200
    second_review = second.json()["data"]["current_review"]
    assert second_review["supersedes"] == first_review["review_id"]
    assert len(alias_store.get_review_history(candidate["candidate_id"])) == 2

    confirmed = alias_client.get("/api/entity-aliases", params={"status": "confirmed_merge"}).json()
    rejected = alias_client.get(
        "/api/entity-aliases", params={"status": "rejected_distinct"}
    ).json()
    assert confirmed["data"] == []
    assert [row["candidate_id"] for row in rejected["data"]] == [candidate["candidate_id"]]


@pytest.mark.parametrize(
    ("path", "json_body", "expected_status"),
    [
        (
            "/api/entity-aliases/999999/review",
            {"status": "confirmed_merge", "reviewed_by": "RK"},
            404,
        ),
        ("/api/entity-aliases/{id}/review", {"status": "merge", "reviewed_by": "RK"}, 400),
        ("/api/entity-aliases/{id}/review", {"status": "confirmed_merge"}, 422),
        ("/api/entity-aliases/{id}/review", {"status": "confirmed_merge", "reviewed_by": ""}, 422),
        (
            "/api/entity-aliases/{id}/review",
            {"status": "confirmed_merge", "reviewed_by": "RK", "supersedes": 4},
            422,
        ),
    ],
)
def test_review_validation_errors_use_house_envelope(
    alias_client: TestClient,
    path: str,
    json_body: dict[str, object],
    expected_status: int,
) -> None:
    (candidate,) = _seed([_candidate("v1", "ALPHA", ["MPLADS-FX-0001"])])
    path = path.format(id=candidate["candidate_id"])

    response = alias_client.post(path, json=json_body)

    assert response.status_code == expected_status
    assert response.json()["success"] is False


@pytest.mark.parametrize(
    "params",
    [
        {"status": "reviewed"},
        {"page": 0},
        {"page_size": 201},
    ],
)
def test_list_query_validation_is_422(alias_client: TestClient, params: dict[str, object]) -> None:
    response = alias_client.get("/api/entity-aliases", params=params)
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_sync_upserts_snapshot_artifact_and_missing_old_artifact_is_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    monkeypatch.setattr(entity_aliases.db, "SNAPSHOT_DIR", snapshot_dir)

    assert entity_aliases.sync_alias_candidates_from_snapshot() == 0
    assert "alias_candidates.json" in caplog.text

    (snapshot_dir / "alias_candidates.json").write_text(
        json.dumps([_candidate("v1", "ALPHA", ["MPLADS-FX-0001"])]),
        encoding="utf-8",
    )
    assert entity_aliases.sync_alias_candidates_from_snapshot() == 1
    rows, total = alias_store.list_candidates(status="pending")
    assert total == 1
    assert rows[0]["proposed_canonical_id"] == "v1"
