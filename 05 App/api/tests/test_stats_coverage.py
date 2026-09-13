"""GET /api/stats/summary, 2026-09-11: the coverage counts behind the
Dashboard's first figure ("Across N constituencies in M states and union
territories"), over the same population as works_under_implementation.
"""

from __future__ import annotations

UNDER_IMPLEMENTATION = ("Sanctioned", "In Progress")


def test_summary_reports_state_and_constituency_coverage(client, works_fixture):
    data = client.get("/api/stats/summary").json()["data"]
    population = [r for r in works_fixture if r["completion_status"] in UNDER_IMPLEMENTATION]
    assert data["state_count"] == len({r["state"] for r in population})
    assert data["constituency_count"] == len({r["constituency"] for r in population})
