"""GET /api/works/facets: filter options for the Inspection List, counted over
the whole quota population rather than over a fetched page, so an option the
officer needs is never missing just because it was not on page one.
"""

from __future__ import annotations

from collections import Counter

from nidhinetra_pipeline.risk import rank
from nidhinetra_pipeline.risk.peer_groups import financial_year_of

UNDER_IMPLEMENTATION = ("Sanctioned", "In Progress")


def _population(works_fixture):
    return [r for r in works_fixture if r["completion_status"] in UNDER_IMPLEMENTATION]


def _as_counts(facet):
    return {f["value"]: f["count"] for f in facet}


def test_facets_count_the_quota_population(client, works_fixture):
    body = client.get("/api/works/facets").json()
    assert body["success"] is True
    data = body["data"]
    population = _population(works_fixture)
    assert _as_counts(data["states"]) == dict(Counter(r["state"] for r in population))
    assert _as_counts(data["categories"]) == dict(Counter(r["work_category"] for r in population))
    years = Counter(financial_year_of(r) for r in population)
    years.pop(None, None)
    assert _as_counts(data["years"]) == dict(years)


def test_flag_facet_lists_every_detector_even_when_it_never_fired(client):
    data = client.get("/api/works/facets").json()["data"]
    assert [f["value"] for f in data["flags"]] == list(rank.FLAG_WEIGHTS)
    assert all(isinstance(f["count"], int) for f in data["flags"])


def test_facet_ordering(client):
    data = client.get("/api/works/facets").json()["data"]
    states = [f["value"] for f in data["states"]]
    years = [f["value"] for f in data["years"]]
    assert states == sorted(states)
    assert years == sorted(years, reverse=True)


def test_facets_path_is_not_mistaken_for_a_work_id(client):
    response = client.get("/api/works/facets")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], dict)
