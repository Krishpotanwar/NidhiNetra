"""GET /api/works/{work_id}: 200 with a merged record for a real id, 404
with a frontend-renderable message for a fake one.
"""

from __future__ import annotations

from nidhinetra_pipeline.outcomes import duplicate_store


def test_get_work_200_for_real_id_returns_merged_record(client, works_fixture):
    work_id = works_fixture[0]["work_id"]

    response = client.get(f"/api/works/{work_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    record = body["data"]
    assert record["work_id"] == work_id
    # Merged: contract 3.1 fields...
    assert "state" in record and "work_category" in record
    # ...and contract 3.2 fields, both present on the same object.
    assert "inspection_rank" in record and "risk_score" in record and "flags" in record


def test_get_work_404_for_fake_id_has_a_renderable_error_message(client):
    response = client.get("/api/works/this-work-id-does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert set(body.keys()) == {"success", "data", "error", "meta"}
    assert body["success"] is False
    assert body["data"] is None
    # A frontend could put this string directly in an error state: no
    # stack trace, no exception class name, just a plain sentence.
    assert isinstance(body["error"], str)
    assert "this-work-id-does-not-exist" in body["error"]
    assert "Traceback" not in body["error"]


def test_a_work_carries_the_portal_description_activity_and_recommendation_date(client):
    body = client.get("/api/works/MPLADS-FX-0001").json()["data"]

    assert (
        body["work_description"] == "Construction of bore well near Zilla Parishad school, Ward 4"
    )
    assert body["activity_name"] == "Drinking water facilities"
    assert body["recommendation_date"] == "2024-06-28"


def test_work_detail_carries_duplicate_context(client):
    work_id = "MPLADS-FX-0001"
    duplicate_store.upsert_candidates(
        [
            {
                "finder": "identical_batch",
                "scope": "C1",
                "fingerprint_a": "1111111111111111",
                "fingerprint_b": "1111111111111111",
                "finder_version": "candidate_generation_v0",
                "threshold_crossing_batch": True,
                "text": "PCC Road, near Ram House",
                "work_ids": [work_id, "MPLADS-FX-0099"],
            }
        ]
    )

    response = client.get(f"/api/works/{work_id}")

    assert response.status_code == 200
    context = response.json()["data"]["duplicate_context"]
    assert context == [
        {
            "candidate_id": context[0]["candidate_id"],
            "finder": "identical_batch",
            "threshold_crossing_batch": True,
            "text": "PCC Road, near Ram House",
            "work_count": 2,
            "other_work_ids": ["MPLADS-FX-0099"],
            "status": "pending",
        }
    ]


def test_work_detail_duplicate_context_is_empty_list_when_there_is_none(client):
    response = client.get("/api/works/MPLADS-FX-0001")

    assert response.json()["data"]["duplicate_context"] == []
