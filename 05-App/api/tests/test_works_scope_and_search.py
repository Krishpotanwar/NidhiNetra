"""GET /api/works, 2026-09-11 additions for the redesigned Inspection List.

scope=under_implementation pushes the District Authority quota population
(Sanctioned, In Progress) into the query, state is repeatable, q searches the
fields an officer would actually type, and meta carries the filtered quota and
flag counts so the browser never derives a population figure from one page.
Every expected value is computed from the raw CP0 fixture, never hardcoded.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

UNDER_IMPLEMENTATION = ("Sanctioned", "In Progress")
SEARCH_FIELDS = (
    "work_id",
    "constituency",
    "implementing_agency",
    "mp_name",
    "state",
    "vendor_name",
)


def _get(client, params: Any) -> dict[str, Any]:
    response = client.get("/api/works", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _matches(row: dict[str, Any], needle: str) -> bool:
    lowered = needle.strip().lower()
    return any(lowered in str(row.get(field) or "").lower() for field in SEARCH_FIELDS)


def test_scope_under_implementation_keeps_only_the_quota_population(client, works_fixture):
    body = _get(client, {"scope": "under_implementation", "page_size": 200})
    expected = sum(1 for r in works_fixture if r["completion_status"] in UNDER_IMPLEMENTATION)
    assert expected > 0  # otherwise this test is vacuous
    assert body["meta"]["total"] == expected
    assert all(r["completion_status"] in UNDER_IMPLEMENTATION for r in body["data"])


def test_scope_defaults_to_all_so_existing_callers_are_unchanged(client, works_fixture):
    assert _get(client, {"page_size": 200})["meta"]["total"] == len(works_fixture)
    assert _get(client, {"scope": "all", "page_size": 200})["meta"]["total"] == len(works_fixture)


def test_unknown_scope_is_a_422(client):
    response = client.get("/api/works", params={"scope": "everything"})
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_scoped_results_stay_in_inspection_rank_order(client):
    body = _get(client, {"scope": "under_implementation", "page_size": 200})
    ranks = [r["inspection_rank"] for r in body["data"]]
    assert ranks == sorted(ranks)


def test_state_is_repeatable(client, works_fixture):
    (first, first_n), (second, second_n) = Counter(r["state"] for r in works_fixture).most_common(2)
    body = _get(client, [("state", first), ("state", second), ("page_size", 200)])
    assert body["meta"]["total"] == first_n + second_n
    assert {r["state"] for r in body["data"]} == {first, second}


def test_q_searches_officer_facing_text_case_insensitively(client, works_fixture):
    needle = works_fixture[0]["constituency"].split()[0]
    expected = sum(1 for r in works_fixture if _matches(r, needle))
    assert expected > 0
    body = _get(client, {"q": needle.upper(), "page_size": 200})
    assert body["meta"]["total"] == expected
    assert all(_matches(r, needle) for r in body["data"])


def test_q_finds_a_work_by_its_id(client, works_fixture):
    work_id = works_fixture[5]["work_id"]
    body = _get(client, {"q": work_id, "page_size": 200})
    assert work_id in {r["work_id"] for r in body["data"]}


def test_q_treats_sql_wildcards_as_plain_text(client, works_fixture):
    # A LIKE-based search would read "%" as "match anything" and return all 20.
    expected = sum(1 for r in works_fixture if _matches(r, "%"))
    assert _get(client, {"q": "%", "page_size": 200})["meta"]["total"] == expected


def test_blank_q_is_ignored(client, works_fixture):
    assert _get(client, {"q": "   ", "page_size": 200})["meta"]["total"] == len(works_fixture)


def test_meta_carries_the_filtered_quota(client):
    body = _get(client, {"scope": "under_implementation", "page_size": 1})
    total = body["meta"]["total"]
    assert body["meta"]["quota_n"] == max(1, math.ceil(total * 0.1))


def test_quota_is_zero_when_the_filter_is_empty(client):
    body = _get(client, {"scope": "under_implementation", "q": "no-work-matches-this"})
    assert body["meta"]["total"] == 0
    assert body["meta"]["quota_n"] == 0
    assert body["data"] == []


def test_quota_is_not_reported_outside_the_quota_population(client):
    assert _get(client, {"page_size": 1})["meta"]["quota_n"] is None


def test_flag_counts_cover_every_page_not_just_the_returned_one(client):
    everything = _get(client, {"scope": "under_implementation", "page_size": 200})
    quota_n = everything["meta"]["quota_n"]
    one_page = _get(client, {"scope": "under_implementation", "page_size": 1})
    assert one_page["meta"]["flagged_total"] == sum(1 for r in everything["data"] if r["flags"])
    assert one_page["meta"]["flagged_beyond_quota"] == sum(
        1 for r in everything["data"][quota_n:] if r["flags"]
    )
