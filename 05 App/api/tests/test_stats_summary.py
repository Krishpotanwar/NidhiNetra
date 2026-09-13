"""GET /api/stats/summary: all four figures plus data_as_of, and the
figures are internally consistent with what's actually in the snapshot
(computed independently here from the raw fixture, not hardcoded).
"""

from __future__ import annotations

from datetime import date

UNDER_IMPLEMENTATION = ("Sanctioned", "In Progress")


def _months_between(from_iso: str, to_iso: str) -> int:
    f = date.fromisoformat(from_iso)
    t = date.fromisoformat(to_iso)
    return (t.year - f.year) * 12 + (t.month - f.month)


def test_summary_has_all_four_figures_plus_data_as_of(client):
    body = client.get("/api/stats/summary").json()

    assert body["success"] is True
    data = body["data"]
    assert set(data.keys()) == {
        # The four summary-strip figures.
        "works_under_implementation",
        "flagged_count",
        "total_flagged_amount_inr",
        "idle_beyond_12_months_amount_inr",
        # Denominators for the strip's context lines ("N of M works", "X%").
        # Added 2026-09-04: the frontend used to derive these from the page
        # of rows it had fetched, which read "200 of 200 works, 100%" once
        # rung 1 landed 79,068 records against a real 44,810 and 18,093.
        "total_works_all_statuses",
        "idle_work_count",
        "total_sanctioned_under_implementation_inr",
        # Coverage behind the Dashboard's first figure. Added 2026-09-11.
        "state_count",
        "constituency_count",
        "data_as_of",
    }
    assert isinstance(data["data_as_of"], str) and data["data_as_of"]


def test_context_line_denominators_are_whole_dataset_not_a_page(client, works_fixture):
    """The three denominators must describe every record in the snapshot, so
    the strip's context lines stay true regardless of how many rows the
    table fetched.
    """
    data = client.get("/api/stats/summary").json()["data"]

    assert data["total_works_all_statuses"] == len(works_fixture)
    assert data["idle_work_count"] <= data["works_under_implementation"]
    # Flagged works are a subset of works under implementation, so the money
    # under them cannot exceed the money under all of them.
    assert data["total_flagged_amount_inr"] <= data["total_sanctioned_under_implementation_inr"]


def test_summary_works_under_implementation_matches_a_real_count(client, works_fixture):
    expected = sum(1 for r in works_fixture if r["completion_status"] in UNDER_IMPLEMENTATION)
    assert expected > 0  # otherwise this test is vacuous

    body = client.get("/api/stats/summary").json()

    assert body["data"]["works_under_implementation"] == expected


def test_summary_idle_beyond_12_months_matches_an_independent_computation(client, works_fixture):
    under_impl = [r for r in works_fixture if r["completion_status"] in UNDER_IMPLEMENTATION]
    as_of_ref = max(r["last_updated"] for r in works_fixture)

    expected_amount = round(
        sum(
            r["sanctioned_amount_inr"]
            for r in under_impl
            if r["expenditure_amount_inr"] == 0
            and r["sanction_date"] is not None
            and _months_between(r["sanction_date"], as_of_ref) > 12
        ),
        2,
    )

    body = client.get("/api/stats/summary").json()

    assert body["data"]["idle_beyond_12_months_amount_inr"] == expected_amount
