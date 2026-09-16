"""GET /api/inspections (Reports page, 2026-09-11): every recorded outcome,
newest first, plus per-group counts. An issue rate is reported only once a
group has enough inspections that reached the work; below that the rate is
null, and the page says so instead of showing a number.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
from fastapi.testclient import TestClient
from nidhinetra_api.routers import inspections as inspections_router

EMPTY_GROUP = {"n": 0, "reached_work": 0, "issues": 0, "within_quota": 0, "issue_rate": None}


def _works(client: TestClient, n: int) -> list[dict[str, Any]]:
    return client.get("/api/works", params={"page_size": n}).json()["data"]


def _record(client: TestClient, work_id: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "work_id": work_id,
        "inspected_on": "2026-09-05",
        "outcome": "work_present_and_matches",
        "notes": "",
        "inspector_id": "AB",
    }
    payload.update(overrides)
    response = client.post("/api/inspections", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_list_is_empty_before_any_inspection(client: TestClient) -> None:
    body = client.get("/api/inspections").json()
    assert body["success"] is True
    assert body["data"]["outcomes"] == []
    summary = body["data"]["summary"]
    assert summary["total"] == 0
    assert summary["ranked"] == EMPTY_GROUP
    assert summary["spot_check"] == EMPTY_GROUP
    assert summary["min_reached_per_group"] == inspections_router.MIN_REACHED_PER_GROUP
    assert summary["comparison_ready"] is False


def test_outcomes_come_back_newest_first_with_their_frozen_context(client: TestClient) -> None:
    first, second = _works(client, 2)
    a = _record(client, first["work_id"])
    b = _record(client, second["work_id"], in_control_sample=True)

    data = client.get("/api/inspections").json()["data"]

    assert [o["outcome_id"] for o in data["outcomes"]] == [b["outcome_id"], a["outcome_id"]]
    assert data["outcomes"][0]["constituency"] == second["constituency"]
    assert (
        data["outcomes"][0]["implementing_district_authority"]
        == second["implementing_district_authority"]
    )
    assert data["summary"]["total"] == 2
    assert data["summary"]["ranked"]["n"] == 1
    assert data["summary"]["spot_check"]["n"] == 1


def test_agency_unresponsive_is_recorded_but_did_not_reach_the_work(client: TestClient) -> None:
    (work,) = _works(client, 1)
    _record(client, work["work_id"], outcome="agency_unresponsive")
    ranked = client.get("/api/inspections").json()["data"]["summary"]["ranked"]
    assert ranked["n"] == 1
    assert ranked["reached_work"] == 0
    assert ranked["issues"] == 0


def test_within_quota_uses_the_rank_frozen_at_recording_time(client: TestClient) -> None:
    (work,) = _works(client, 1)
    recorded = _record(client, work["work_id"])
    ranked = client.get("/api/inspections").json()["data"]["summary"]["ranked"]
    inside = recorded["inspection_rank_at_time"] <= recorded["cutoff_rank_at_time"]
    assert ranked["within_quota"] == (1 if inside else 0)


def test_issue_rate_stays_null_below_the_minimum(client: TestClient) -> None:
    (work,) = _works(client, 1)
    _record(client, work["work_id"], outcome="work_not_found_at_site")
    ranked = client.get("/api/inspections").json()["data"]["summary"]["ranked"]
    assert ranked["issues"] == 1
    assert ranked["issue_rate"] is None


def test_issue_rate_and_wilson_interval_once_the_minimum_is_met(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(inspections_router, "MIN_REACHED_PER_GROUP", 2)
    first, second = _works(client, 2)
    _record(client, first["work_id"], outcome="work_not_found_at_site")
    _record(client, second["work_id"], outcome="work_present_and_matches")

    summary = client.get("/api/inspections").json()["data"]["summary"]
    rate = summary["ranked"]["issue_rate"]

    # Wilson score interval at 95 percent, n = 2, p = 0.5, computed here
    # independently of the implementation.
    z, n, p = 1.959963984540054, 2, 0.5
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    assert rate["value"] == pytest.approx(0.5)
    assert rate["low"] == pytest.approx(centre - margin)
    assert rate["high"] == pytest.approx(centre + margin)
    # The spot-check group is still empty, so no comparison yet.
    assert summary["comparison_ready"] is False


def test_a_superseded_outcome_is_listed_but_not_counted_twice(client: TestClient) -> None:
    (work,) = _works(client, 1)
    original = _record(client, work["work_id"], outcome="documentation_incomplete")
    _record(
        client,
        work["work_id"],
        inspected_on="2026-09-06",
        outcome="work_present_and_matches",
        supersedes=original["outcome_id"],
    )

    data = client.get("/api/inspections").json()["data"]

    assert len(data["outcomes"]) == 2
    flags = {o["outcome_id"]: o["superseded"] for o in data["outcomes"]}
    assert flags[original["outcome_id"]] is True
    assert data["summary"]["total"] == 1
    assert data["summary"]["ranked"]["n"] == 1
    assert data["summary"]["ranked"]["issues"] == 0
