"""POST /api/inspections (Checkpoints CP8). Unknown work_id rejected,
outcome outside the enum rejected, duplicate for the same work+date+inspector
rejected -- and the recorded rank/score/context are looked up server-side
from the current snapshot, never trusted from the client, since that is
precisely what makes them a trustworthy frozen fact later.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from nidhinetra_api.routers import inspections as inspections_router
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
    # Looked up server-side from the same snapshot the client just read, not
    # echoed back from anything the client sent. The exact value of
    # inspection_rank_at_time (district-scoped, F-03/F-04) is covered by
    # test_district_population_and_rank_match_an_independent_computation
    # below; this test only proves it is server-computed and internally
    # consistent between the response and the stored row.
    assert isinstance(body["data"]["inspection_rank_at_time"], int)
    assert body["data"]["inspection_rank_at_time"] >= 1
    assert body["data"]["risk_score_at_time"] == row["risk_score"]
    assert body["data"]["in_control_sample"] is False
    assert body["data"]["supersedes"] is None
    assert isinstance(body["data"]["outcome_id"], int)

    stored = outcomes_store.get_outcomes_for_work(row["work_id"])
    assert len(stored) == 1
    assert stored[0]["inspection_rank_at_time"] == body["data"]["inspection_rank_at_time"]
    assert stored[0]["state"] == row["state"]
    assert stored[0]["constituency"] == row["constituency"]
    assert stored[0]["implementing_district_authority"] == row["implementing_district_authority"]
    assert stored[0]["implementing_agency"] == row["implementing_agency"]
    assert stored[0]["work_category"] == row["work_category"]
    assert stored[0]["sanctioned_amount_inr"] == row["sanctioned_amount_inr"]


def test_district_population_and_rank_match_an_independent_computation(
    client: TestClient,
) -> None:
    """F-03/F-04, corrected 2026-09-14: population_n_at_time and
    cutoff_rank_at_time must be this work's own District Authority's
    under-implementation population and quota, not the national ones (a
    district with zero of its own works inspected is a real gap even when
    the national aggregate looks fine), and inspection_rank_at_time must be
    this work's rank strictly within that same district-scoped population
    (rank.py's tie-break re-applied: risk_score descending, work_id
    ascending) -- not the unrelated national inspection_rank that spans all
    79,068 works regardless of district or completion status.

    Proven here by independently recomputing both from the same
    under-implementation-scoped work list the dashboard itself reads
    (GET /api/works?scope=under_implementation), not by trusting
    inspections.py's own arithmetic back at itself.
    """
    under_implementation = client.get(
        "/api/works", params={"scope": "under_implementation", "page_size": 200}
    ).json()["data"]
    # The lowest national priority under implementation: a real edge case
    # where a district-scoped rank should differ sharply from any
    # national-scoped number, which is exactly what F-04 got wrong.
    target = under_implementation[-1]
    district = [
        w
        for w in under_implementation
        if w["implementing_district_authority"] == target["implementing_district_authority"]
    ]
    expected_population = len(district)
    expected_rank = 1 + sum(
        1
        for w in district
        if w["work_id"] != target["work_id"]
        and (
            w["risk_score"] > target["risk_score"]
            or (w["risk_score"] == target["risk_score"] and w["work_id"] < target["work_id"])
        )
    )
    expected_cutoff = max(1, math.ceil(expected_population * 0.1)) if expected_population else 0

    recorded = client.post("/api/inspections", json=_payload(target["work_id"])).json()["data"]

    assert recorded["population_n_at_time"] == expected_population
    assert recorded["inspection_rank_at_time"] == expected_rank
    assert recorded["cutoff_rank_at_time"] == expected_cutoff


def test_quota_population_is_the_district_authority_not_the_agency(client: TestClient) -> None:
    """F-01: clause 4.5.2 is the District Authority's duty. An agency can work
    under several District Authorities, so the frozen population must follow
    the authority. The fixture maps each state to its own synthetic authority,
    which groups differently from the fixture's agencies.
    """
    under = client.get(
        "/api/works", params={"scope": "under_implementation", "page_size": 200}
    ).json()["data"]

    def population(field: str, value: str | None) -> int:
        return sum(1 for w in under if w[field] == value)

    target = next(
        w
        for w in under
        if w["implementing_agency"]
        and population("implementing_district_authority", w["implementing_district_authority"])
        != population("implementing_agency", w["implementing_agency"])
    )
    recorded = client.post("/api/inspections", json=_payload(target["work_id"])).json()["data"]

    assert recorded["population_n_at_time"] == population(
        "implementing_district_authority", target["implementing_district_authority"]
    )
    assert recorded["population_n_at_time"] != population(
        "implementing_agency", target["implementing_agency"]
    )


def test_client_supplied_in_control_sample_is_ignored_and_not_persisted(
    client: TestClient,
) -> None:
    """F-09 (engineering-review task T7): the comparison group is the server's
    decision. A client that sends in_control_sample=True must not be able to
    put an outcome into the random group after seeing the work.
    """
    row = _first_work_id(client)
    resp = client.post("/api/inspections", json=_payload(row["work_id"], in_control_sample=True))

    assert resp.status_code == 200
    assert resp.json()["data"]["in_control_sample"] is False
    stored = outcomes_store.get_outcomes_for_work(row["work_id"])[0]
    assert stored["in_control_sample"] is False


def test_control_group_membership_comes_from_the_server_assignment(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(inspections_router, "_server_control_assignment", lambda work_id: True)
    row = _first_work_id(client)

    resp = client.post("/api/inspections", json=_payload(row["work_id"]))

    assert resp.json()["data"]["in_control_sample"] is True
    assert outcomes_store.get_outcomes_for_work(row["work_id"])[0]["in_control_sample"] is True


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


_IST = timezone(timedelta(hours=5, minutes=30))


@pytest.mark.parametrize(
    "overrides",
    [
        {"inspected_on": "2026-02-30"},
        {"inspected_on": "05-09-2026"},
        {"inspected_on": (datetime.now(_IST).date() + timedelta(days=1)).isoformat()},
        {"inspector_id": "   "},
        {"inspector_id": "x" * 41},
        {"notes": "n" * 2001},
        {"work_id": "w" * 65},
        {"supersedes": 0},
    ],
)
def test_invalid_outcome_input_is_a_422_and_stores_nothing(
    client: TestClient, overrides: dict[str, Any]
) -> None:
    """F-10: strict request constraints, even in demo mode."""
    row = _first_work_id(client)
    # Built with update(), not _payload(row["work_id"], **overrides): the
    # {"work_id": ...} case's key collides with _payload's own first
    # positional parameter name, which raises TypeError before any request
    # is made (proven in this task's red-test-output.txt). update() applies
    # overrides on top of a valid payload exactly like _payload's own
    # base.update(overrides) does internally, without that collision.
    payload = _payload(row["work_id"])
    payload.update(overrides)
    resp = client.post("/api/inspections", json=payload)
    assert resp.status_code == 422
    assert resp.json()["success"] is False
    assert outcomes_store.list_all_outcomes() == []


def test_whitespace_around_initials_is_trimmed(client: TestClient) -> None:
    row = _first_work_id(client)
    resp = client.post("/api/inspections", json=_payload(row["work_id"], inspector_id="  AB  "))
    assert resp.status_code == 200
    assert resp.json()["data"]["inspector_id"] == "AB"


def test_an_amendment_must_name_an_outcome_for_the_same_work(client: TestClient) -> None:
    first, second = client.get("/api/works", params={"page_size": 2}).json()["data"]
    original = client.post("/api/inspections", json=_payload(first["work_id"])).json()["data"]

    resp = client.post(
        "/api/inspections",
        json=_payload(second["work_id"], supersedes=original["outcome_id"]),
    )

    assert resp.status_code == 422
    assert len(outcomes_store.list_all_outcomes()) == 1


def test_an_outcome_can_be_amended_only_once(client: TestClient) -> None:
    row = _first_work_id(client)
    original = client.post("/api/inspections", json=_payload(row["work_id"])).json()["data"]
    first_fix = client.post(
        "/api/inspections",
        json=_payload(row["work_id"], inspected_on="2026-09-06", supersedes=original["outcome_id"]),
    )
    assert first_fix.status_code == 200

    second_fix = client.post(
        "/api/inspections",
        json=_payload(
            row["work_id"],
            inspected_on="2026-09-07",
            inspector_id="RK",
            supersedes=original["outcome_id"],
        ),
    )

    assert second_fix.status_code == 409
