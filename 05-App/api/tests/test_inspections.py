"""POST /api/inspections (Checkpoints CP8). Unknown work_id rejected,
outcome outside the enum rejected, duplicate for the same work+date+inspector
rejected -- and the recorded rank/score/context are looked up server-side
from the current snapshot, never trusted from the client, since that is
precisely what makes them a trustworthy frozen fact later.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi.testclient import TestClient
from nidhinetra_pipeline.outcomes import store as outcomes_store


def _first_work_id(client: TestClient) -> dict[str, Any]:
    resp = client.get("/api/works", params={"page_size": 1})
    row = resp.json()["data"][0]
    return row


def _payload(work_id: str, **overrides: Any) -> dict[str, Any]:
    base = {
        "work_id": work_id,
        "inspected_on": "2026-09-05",
        "outcome": "work_present_and_matches",
        "notes": "",
        "inspector_id": "AB",
    }
    base.update(overrides)
    return base


def test_valid_outcome_is_recorded_with_server_side_rank_score_and_context(
    client: TestClient,
) -> None:
    row = _first_work_id(client)

    resp = client.post(
        "/api/inspections",
        json=_payload(
            row["work_id"],
            outcome="work_present_and_matches",
            notes="Confirmed on site, matches the record.",
        ),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["work_id"] == row["work_id"]
    assert body["data"]["outcome"] == "work_present_and_matches"
    assert body["data"]["inspector_id"] == "AB"
    # Looked up server-side from the same snapshot the client just read,
    # not echoed back from anything the client sent.
    assert body["data"]["inspection_rank_at_time"] == row["inspection_rank"]
    assert body["data"]["risk_score_at_time"] == row["risk_score"]
    assert body["data"]["in_control_sample"] is False
    assert body["data"]["supersedes"] is None
    assert isinstance(body["data"]["outcome_id"], int)

    stored = outcomes_store.get_outcomes_for_work(row["work_id"])
    assert len(stored) == 1
    assert stored[0]["inspection_rank_at_time"] == row["inspection_rank"]
    assert stored[0]["state"] == row["state"]
    assert stored[0]["constituency"] == row["constituency"]
    assert stored[0]["work_category"] == row["work_category"]
    assert stored[0]["sanctioned_amount_inr"] == row["sanctioned_amount_inr"]


def test_population_n_and_cutoff_rank_match_the_summary_endpoint(client: TestClient) -> None:
    """Outside-voice finding: inspection_rank spans all works, the quota
    cutoff spans only works under implementation -- this proves the two
    endpoints agree on that population, not just that inspections.py has
    *a* number.
    """
    row = _first_work_id(client)
    summary = client.get("/api/stats/summary").json()["data"]

    resp = client.post("/api/inspections", json=_payload(row["work_id"]))
    data = resp.json()["data"]

    assert data["population_n_at_time"] == summary["works_under_implementation"]
    expected_cutoff = max(1, math.ceil(summary["works_under_implementation"] * 0.1))
    assert data["cutoff_rank_at_time"] == expected_cutoff


def test_in_control_sample_round_trips_true(client: TestClient) -> None:
    row = _first_work_id(client)
    resp = client.post("/api/inspections", json=_payload(row["work_id"], in_control_sample=True))
    assert resp.json()["data"]["in_control_sample"] is True
    stored = outcomes_store.get_outcomes_for_work(row["work_id"])[0]
    assert stored["in_control_sample"] is True


def test_unknown_work_id_is_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/inspections",
        json=_payload("does-not-exist-in-this-snapshot"),
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert "does-not-exist-in-this-snapshot" in body["error"]
    assert outcomes_store.list_all_outcomes() == []


def test_outcome_outside_the_enum_is_rejected(client: TestClient) -> None:
    row = _first_work_id(client)
    resp = client.post(
        "/api/inspections",
        # a verdict, deliberately excluded from the enum
        json=_payload(row["work_id"], outcome="fraud"),
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert outcomes_store.list_all_outcomes() == []


def test_duplicate_for_same_work_date_and_inspector_is_rejected(client: TestClient) -> None:
    row = _first_work_id(client)
    first = client.post("/api/inspections", json=_payload(row["work_id"], notes="first visit"))
    assert first.status_code == 200

    second = client.post(
        "/api/inspections",
        json=_payload(row["work_id"], outcome="documentation_incomplete", notes="second attempt"),
    )
    assert second.status_code == 409
    assert second.json()["success"] is False

    # The rejected duplicate must not have overwritten the first record.
    stored = outcomes_store.get_outcomes_for_work(row["work_id"])
    assert len(stored) == 1
    assert stored[0]["outcome"] == "work_present_and_matches"


def test_different_inspector_same_work_and_date_is_not_a_duplicate(client: TestClient) -> None:
    """Outside-voice correction: a real case the old constraint blocked --
    agency unresponsive in the morning, a different inspector gets access
    and completes a real inspection that same afternoon.
    """
    row = _first_work_id(client)
    first = client.post(
        "/api/inspections",
        json=_payload(row["work_id"], outcome="agency_unresponsive", inspector_id="AB"),
    )
    assert first.status_code == 200

    second = client.post(
        "/api/inspections",
        json=_payload(row["work_id"], inspector_id="RK", notes="Got access in the afternoon."),
    )
    assert second.status_code == 200

    stored = outcomes_store.get_outcomes_for_work(row["work_id"])
    assert len(stored) == 2
    assert {r["inspector_id"] for r in stored} == {"AB", "RK"}


def test_supersedes_records_an_explicit_amendment(client: TestClient) -> None:
    row = _first_work_id(client)
    original = client.post(
        "/api/inspections",
        json=_payload(row["work_id"], outcome="documentation_incomplete"),
    )
    original_id = original.json()["data"]["outcome_id"]

    amended = client.post(
        "/api/inspections",
        json=_payload(
            row["work_id"],
            inspected_on="2026-09-06",
            notes="Documentation located, amending yesterday's entry.",
            supersedes=original_id,
        ),
    )
    assert amended.status_code == 200
    assert amended.json()["data"]["supersedes"] == original_id


def test_missing_required_field_is_a_422_not_a_500(client: TestClient) -> None:
    resp = client.post(
        "/api/inspections",
        json={"inspected_on": "2026-09-05", "outcome": "work_present_and_matches"},
    )
    assert resp.status_code == 422
    assert resp.json()["success"] is False
