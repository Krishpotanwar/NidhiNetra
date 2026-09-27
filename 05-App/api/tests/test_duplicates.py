"""Phase 1 Stage C: duplicate-review queue API and batched evidence resolution."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from nidhinetra_api import db
from nidhinetra_api.main import app
from nidhinetra_api.routers import duplicates
from nidhinetra_pipeline.outcomes import duplicate_store


def _candidate(
    scope: str,
    fingerprint: str,
    work_ids: list[str],
    *,
    finder: str = "identical_batch",
    threshold_crossing_batch: bool = False,
    text: str = "PCC Road, near Ram House",
) -> dict[str, object]:
    return {
        "finder": finder,
        "scope": scope,
        "fingerprint_a": fingerprint,
        "fingerprint_b": fingerprint,
        "finder_version": "candidate_generation_v0",
        "threshold_crossing_batch": threshold_crossing_batch,
        "text": text,
        "work_ids": work_ids,
    }


@pytest.fixture()
def duplicates_client(client: TestClient, isolated_outcomes_db: Path) -> TestClient:
    """Start the real app, then clear only the per-test duplicate tables."""
    duplicate_store.init_db(isolated_outcomes_db)
    with sqlite3.connect(isolated_outcomes_db) as connection:
        connection.execute("DELETE FROM duplicate_reviews")
        connection.execute("DELETE FROM duplicate_candidates")
        connection.commit()
    return client


def _seed(candidates: list[dict[str, object]]) -> list[dict[str, Any]]:
    duplicate_store.upsert_candidates(candidates)
    return duplicate_store.list_candidates(status=None)[0]


def test_pending_queue_has_house_envelope_and_pagination(duplicates_client: TestClient) -> None:
    _seed(
        [
            _candidate("C1", "1111111111111111", ["MPLADS-FX-0001", "MPLADS-FX-0002"]),
            _candidate("C2", "2222222222222222", ["MPLADS-FX-0003", "MPLADS-FX-0004"]),
            _candidate("C3", "3333333333333333", ["MPLADS-FX-0005", "MPLADS-FX-0006"]),
        ]
    )

    response = duplicates_client.get(
        "/api/duplicates", params={"status": "pending", "page": 2, "page_size": 2}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"success", "data", "error", "meta"}
    assert body["success"] is True
    assert [row["scope"] for row in body["data"]] == ["C3"]
    assert body["meta"] == {
        "page": 2,
        "page_size": 2,
        "total": 3,
        "total_pages": 2,
        "judge_abstention_rate": None,
        "judge_quote_rejection_rate": None,
        "judge_pairs_total": None,
    }


def test_status_filters_use_only_the_current_review(duplicates_client: TestClient) -> None:
    candidates = _seed(
        [
            _candidate("C1", "1111111111111111", ["MPLADS-FX-0001", "MPLADS-FX-0002"]),
            _candidate("C2", "2222222222222222", ["MPLADS-FX-0003", "MPLADS-FX-0004"]),
            _candidate("C3", "3333333333333333", ["MPLADS-FX-0005", "MPLADS-FX-0006"]),
        ]
    )
    ids = {row["scope"]: row["candidate_id"] for row in candidates}
    duplicate_store.record_review(ids["C1"], "confirmed_same", "RK")
    duplicate_store.record_review(ids["C2"], "rejected_different", "RK")

    pending = duplicates_client.get("/api/duplicates", params={"status": "pending"}).json()
    confirmed = duplicates_client.get("/api/duplicates", params={"status": "confirmed_same"}).json()
    rejected = duplicates_client.get(
        "/api/duplicates", params={"status": "rejected_different"}
    ).json()

    assert [row["scope"] for row in pending["data"]] == ["C3"]
    assert [row["scope"] for row in confirmed["data"]] == ["C1"]
    assert confirmed["data"][0]["current_review"]["reviewed_by"] == "RK"
    assert [row["scope"] for row in rejected["data"]] == ["C2"]


def test_page_evidence_is_resolved_with_one_batched_duckdb_query(
    duplicates_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    works = duplicates_client.get("/api/works", params={"page_size": 3}).json()["data"]
    work_ids = [row["work_id"] for row in works]
    _seed(
        [
            _candidate("C1", "1111111111111111", [work_ids[1], work_ids[0]]),
            _candidate("C2", "2222222222222222", [work_ids[1], work_ids[2]]),
        ]
    )
    calls: list[tuple[str, list[Any]]] = []
    real_rows_as_dicts = db.rows_as_dicts

    def recording_rows_as_dicts(con, sql: str, params: list[Any] | None = None):
        calls.append((sql, params or []))
        return real_rows_as_dicts(con, sql, params)

    monkeypatch.setattr(duplicates.db, "rows_as_dicts", recording_rows_as_dicts)

    body = duplicates_client.get("/api/duplicates", params={"status": "pending"}).json()

    evidence_queries = [call for call in calls if "works.work_id IN" in call[0]]
    assert len(evidence_queries) == 1
    assert set(evidence_queries[0][1]) == set(work_ids)
    by_id = {row["scope"]: row for row in body["data"]}
    assert [work["work_id"] for work in by_id["C1"]["evidence_works"]] == sorted(
        [work_ids[0], work_ids[1]]
    )
    assert all("work_description" in work for row in body["data"] for work in row["evidence_works"])


def test_review_post_assigns_history_fields_and_correction_supersedes(
    duplicates_client: TestClient,
) -> None:
    (candidate,) = _seed(
        [_candidate("C1", "1111111111111111", ["MPLADS-FX-0001", "MPLADS-FX-0002"])]
    )

    first = duplicates_client.post(
        f"/api/duplicates/{candidate['candidate_id']}/review",
        json={"status": "confirmed_same", "reviewed_by": "RK", "reviewer_note": "Checked."},
    )
    assert first.status_code == 200
    first_review = first.json()["data"]["current_review"]
    assert first_review["status"] == "confirmed_same"
    assert first_review["reviewed_at"].endswith("Z")
    assert first_review["supersedes"] is None

    second = duplicates_client.post(
        f"/api/duplicates/{candidate['candidate_id']}/review",
        json={"status": "rejected_different", "reviewed_by": "AB", "reviewer_note": "Corrected."},
    )
    assert second.status_code == 200
    second_review = second.json()["data"]["current_review"]
    assert second_review["supersedes"] == first_review["review_id"]
    assert len(duplicate_store.get_review_history(candidate["candidate_id"])) == 2


@pytest.mark.parametrize(
    ("path", "json_body", "expected_status"),
    [
        ("/api/duplicates/999999/review", {"status": "confirmed_same", "reviewed_by": "RK"}, 404),
        ("/api/duplicates/{id}/review", {"status": "duplicate", "reviewed_by": "RK"}, 400),
        ("/api/duplicates/{id}/review", {"status": "confirmed_same"}, 422),
        ("/api/duplicates/{id}/review", {"status": "confirmed_same", "reviewed_by": ""}, 422),
        (
            "/api/duplicates/{id}/review",
            {"status": "confirmed_same", "reviewed_by": "RK", "supersedes": 4},
            422,
        ),
    ],
)
def test_review_validation_errors_use_house_envelope(
    duplicates_client: TestClient,
    path: str,
    json_body: dict[str, object],
    expected_status: int,
) -> None:
    (candidate,) = _seed(
        [_candidate("C1", "1111111111111111", ["MPLADS-FX-0001", "MPLADS-FX-0002"])]
    )
    path = path.format(id=candidate["candidate_id"])

    response = duplicates_client.post(path, json=json_body)

    assert response.status_code == expected_status
    assert response.json()["success"] is False


@pytest.mark.parametrize(
    "params",
    [{"status": "duplicate"}, {"page": 0}, {"page_size": 201}, {"kind": "bogus"}],
)
def test_list_query_validation_is_422(
    duplicates_client: TestClient, params: dict[str, object]
) -> None:
    response = duplicates_client.get("/api/duplicates", params=params)
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_kind_filter_narrows_to_judged_rows_and_leaves_no_kind_unchanged(
    duplicates_client: TestClient,
) -> None:
    _seed(
        [
            _candidate("C1", "1111111111111111", ["MPLADS-FX-0001", "MPLADS-FX-0002"]),
            _candidate(
                "C2",
                "2222222222222222",
                ["MPLADS-FX-0003", "MPLADS-FX-0004"],
                finder="judged_same_asset_same_place",
            ),
        ]
    )

    judged = duplicates_client.get("/api/duplicates", params={"kind": "judged"}).json()
    unfiltered = duplicates_client.get("/api/duplicates").json()

    assert [row["scope"] for row in judged["data"]] == ["C2"]
    assert judged["meta"]["total"] == 1
    assert [row["scope"] for row in unfiltered["data"]] == ["C1", "C2"]
    assert unfiltered["meta"]["total"] == 2


def test_sync_upserts_only_identical_batches_and_missing_artifact_is_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    monkeypatch.setattr(duplicates.db, "SNAPSHOT_DIR", snapshot_dir)

    assert duplicates.sync_duplicate_candidates_from_snapshot() == 0
    assert "duplicate_candidates.json" in caplog.text

    artifact = {
        "meta": {"finder_version": "candidate_generation_v0"},
        "groups": {
            "aaaaaaaaaaaaaaaa": {
                "text_fingerprint": "aaaaaaaaaaaaaaaa",
                "text": "PCC Road, near Ram House",
                "work_ids": ["MPLADS-FX-0001", "MPLADS-FX-0002"],
            },
            "bbbbbbbbbbbbbbbb": {
                "text_fingerprint": "bbbbbbbbbbbbbbbb",
                "text": "Solar street lights",
                "work_ids": ["MPLADS-FX-0003", "MPLADS-FX-0004"],
            },
        },
        "batches": [
            {
                "finder": "identical_batch",
                "scope": "C1",
                "group": "aaaaaaaaaaaaaaaa",
                "threshold_crossing_batch": True,
            }
        ],
        "pairs": [
            {
                "finder": "near_copy",
                "scope": "C1",
                "a": "aaaaaaaaaaaaaaaa",
                "b": "bbbbbbbbbbbbbbbb",
            }
        ],
    }
    (snapshot_dir / "duplicate_candidates.json").write_text(json.dumps(artifact), encoding="utf-8")

    assert duplicates.sync_duplicate_candidates_from_snapshot() == 1
    rows, total = duplicate_store.list_candidates(status="pending")
    assert total == 1
    assert rows[0]["scope"] == "C1"
    assert rows[0]["threshold_crossing_batch"] is True


def _judgments_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_sync_judged_candidates_upserts_and_is_safe_when_either_file_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot_dir = tmp_path / "snapshot"
    judgments_dir = tmp_path / "judgments"
    snapshot_dir.mkdir()
    judgments_dir.mkdir()
    monkeypatch.setattr(duplicates.db, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(duplicates.db, "JUDGMENTS_DIR", judgments_dir)

    assert duplicates.sync_judged_candidates_from_judgments() == 0

    artifact = {
        "groups": {
            "g1": {
                "scope": "C1",
                "text_fingerprint": "1111111111111111",
                "text": "Shed at Kheda Chowk",
                "work_ids": ["MPLADS-FX-0001"],
                "work_count": 1,
                "amount_total_inr": 500000.0,
                "sanction_date_first": "2024-07-01",
            },
            "g2": {
                "scope": "C1",
                "text_fingerprint": "2222222222222222",
                "text": "Shed near Kheda Chowk",
                "work_ids": ["MPLADS-FX-0002"],
                "work_count": 1,
                "amount_total_inr": 520000.0,
                "sanction_date_first": "2024-07-20",
            },
        }
    }
    (snapshot_dir / "duplicate_candidates.json").write_text(json.dumps(artifact), encoding="utf-8")
    _judgments_frame(
        [
            {
                "scope": "C1",
                "fingerprint_a": "1111111111111111",
                "fingerprint_b": "2222222222222222",
                "status": "judged",
                "relation": "same_asset_same_place",
                "place_a": "Kheda Chowk",
                "place_b": "Kheda Chowk",
            }
        ]
    ).to_parquet(judgments_dir / "text_pair_judgments.parquet", index=False)

    assert duplicates.sync_judged_candidates_from_judgments() == 1
    rows, total = duplicate_store.list_candidates(status="pending")
    assert total == 1
    assert rows[0]["finder"] == "judged_same_asset_same_place"
    assert rows[0]["work_relation"] == "duplicate_candidate"


def test_list_duplicates_reports_the_judges_rates(
    duplicates_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    judgments_dir = tmp_path / "judgments"
    judgments_dir.mkdir()
    monkeypatch.setattr(duplicates.db, "JUDGMENTS_DIR", judgments_dir)
    _judgments_frame(
        [{"status": "judged", "relation": "not_enough_detail"}] * 3
        + [{"status": "rejected", "relation": None}] * 2
        + [{"status": "judged", "relation": "unrelated"}] * 5
    ).to_parquet(judgments_dir / "text_pair_judgments.parquet", index=False)

    body = duplicates_client.get("/api/duplicates").json()

    assert body["meta"]["judge_abstention_rate"] == 30.0
    assert body["meta"]["judge_quote_rejection_rate"] == 20.0
    assert body["meta"]["judge_pairs_total"] == 10


def test_list_duplicates_rates_never_call_pandas_read_parquet(
    duplicates_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T12B.5 fix round 1 (Critical): the R28 fix moved pyarrow's one-time engine-init cost off
    the startup path, but _judge_rates_meta ran on every GET /api/duplicates and still called
    judge_store.read_judgments -> pandas.read_parquet -- so the very first real request, not
    startup, would pay it instead (unverified by the R28 RSS check, which only hit /health). The
    rates must come from a DuckDB aggregate; pandas.read_parquet must never be called here."""
    judgments_dir = tmp_path / "judgments"
    judgments_dir.mkdir()
    monkeypatch.setattr(duplicates.db, "JUDGMENTS_DIR", judgments_dir)
    _judgments_frame(
        [{"status": "judged", "relation": "not_enough_detail"}] * 3
        + [{"status": "rejected", "relation": None}] * 2
        + [{"status": "judged", "relation": "unrelated"}] * 5
    ).to_parquet(judgments_dir / "text_pair_judgments.parquet", index=False)

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("pandas.read_parquet must not be called on the request path")

    monkeypatch.setattr(pd, "read_parquet", _forbidden)

    response = duplicates_client.get("/api/duplicates")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["judge_abstention_rate"] == 30.0
    assert body["meta"]["judge_quote_rejection_rate"] == 20.0
    assert body["meta"]["judge_pairs_total"] == 10


def test_list_duplicates_rates_are_null_without_a_judgments_file(
    duplicates_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(duplicates.db, "JUDGMENTS_DIR", tmp_path / "no-judgments-here")

    body = duplicates_client.get("/api/duplicates").json()

    assert body["meta"]["judge_abstention_rate"] is None
    assert body["meta"]["judge_quote_rejection_rate"] is None
    assert body["meta"]["judge_pairs_total"] is None


def test_lifespan_parses_duplicate_candidates_json_once_for_both_syncs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T12B.5 perf fix (controller ruling R28): duplicate_candidates.json is ~23 MB on the real
    snapshot. main.py's lifespan must parse it once and hand the same artifact to both
    sync_duplicate_candidates_from_snapshot and sync_judged_candidates_from_judgments, not once
    each -- a second independent parse measured ~100 MB of avoidable peak RSS on Render's 512 MB
    free tier."""
    calls: list[Path | None] = []
    real_loader = duplicates.load_duplicate_candidates_artifact

    def counting_loader(snapshot_dir: Path | None = None) -> dict[str, object] | None:
        calls.append(snapshot_dir)
        return real_loader(snapshot_dir)

    monkeypatch.setattr(duplicates, "load_duplicate_candidates_artifact", counting_loader)

    with TestClient(app):
        pass

    assert len(calls) == 1


@pytest.mark.parametrize(
    "failing_sync",
    ["sync_duplicate_candidates_from_snapshot", "sync_judged_candidates_from_judgments"],
)
def test_lifespan_survives_either_duplicate_sync_raising(
    failing_sync: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Final review I1 / deferred minor #39: T13's rebuild can leave the judgments file naming a
    group the fresh duplicate_candidates.json no longer has, or either file can be malformed.
    Either sync raising must not stop the app from starting and serving /health."""

    def _raise(**_kwargs: object) -> int:
        raise RuntimeError("boom")

    monkeypatch.setattr(duplicates, failing_sync, _raise)

    with TestClient(app) as test_client:
        response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
