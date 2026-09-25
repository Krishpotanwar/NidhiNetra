"""policy.pendency_clause, snapshot.data_as_of_date, the district_authority/
constituency/pendency additions to /api/works, and GET /api/pendency (T4).

The three MoSPI monthly pendency checks: sanctioned more than 45 days after
recommendation, open more than a year after sanction, no payment 90 days
after sanction (D1: over works under implementation only). D4/D5: these
never touch score, rank or flags, and are never combined into one count.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from datetime import date, timedelta

import duckdb
import pytest
from nidhinetra_api import policy
from nidhinetra_api import snapshot as api_snapshot

UNDER_IMPLEMENTATION = ("Sanctioned", "In Progress")
AS_OF = "2026-09-04"


def _population(works_fixture):
    return [r for r in works_fixture if r["completion_status"] in UNDER_IMPLEMENTATION]


def _pendency(client, params=None) -> dict:
    response = client.get("/api/pendency", params=params or {})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _matches_pendency(row: dict, kind: str, as_of: date) -> bool:
    """A pure-Python mirror of policy.pendency_clause's SQL, used to compute
    an expected answer from works_fixture independently of the endpoint
    under test.
    """
    sanction = row["sanction_date"]
    if kind == "late_sanction":
        recommendation = row["recommendation_date"]
        if not recommendation or not sanction:
            return False
        return (date.fromisoformat(sanction) - date.fromisoformat(recommendation)).days > 45
    if kind == "open_past_one_year":
        if not sanction:
            return False
        return (as_of - date.fromisoformat(sanction)).days > 365
    if kind == "no_payment_90_days":
        if not sanction:
            return False
        days_idle = (as_of - date.fromisoformat(sanction)).days
        spent = row["expenditure_amount_inr"] or 0
        return days_idle > 90 and spent == 0
    raise ValueError(kind)


# --- policy.pendency_clause: boundaries (in-memory DuckDB, no snapshot) ----


def test_pendency_clause_boundaries():
    as_of_date = date.fromisoformat(AS_OF)

    def _before(days: int) -> str:
        return (as_of_date - timedelta(days=days)).isoformat()

    # Every row shares one table, so a row aimed at one clause must not
    # accidentally satisfy another: any row here with a real sanction_date
    # gets a non-zero expenditure_amount_inr unless it is itself pinning the
    # no_payment_90_days boundary, otherwise it would double as a
    # (sanction_date, zero-spend, >90-days-idle) match too.
    rows = [
        # late_sanction: 45 days is not late, 46 days is.
        ("LS-45", "2026-01-01", "2026-02-15", 1.0),
        ("LS-46", "2026-01-01", "2026-02-16", 1.0),
        ("LS-NULL-REC", None, "2026-02-16", 1.0),
        ("LS-NULL-SANCTION", "2026-01-01", None, None),
        # open_past_one_year: sanctioned exactly 365 days before as_of is not
        # past one year, 366 days is. Derived from as_of with timedelta so
        # this is exact regardless of any leap day in between.
        ("OY-365", None, _before(365), 1.0),
        ("OY-366", None, _before(366), 1.0),
        ("OY-NULL", None, None, None),
        # no_payment_90_days: 90 days + zero spend is not counted; 91 days +
        # zero is; 91 days + a real payment is not; 91 days + a null spend
        # (coalesced to zero) is.
        ("NP-90-ZERO", None, _before(90), 0.0),
        ("NP-91-ZERO", None, _before(91), 0.0),
        ("NP-91-SPEND", None, _before(91), 1.0),
        ("NP-91-NULL", None, _before(91), None),
        ("NP-NULL-SANCTION", None, None, 0.0),
    ]
    with duckdb.connect(":memory:") as con:
        con.execute(
            "CREATE TABLE works (work_id VARCHAR, recommendation_date DATE, "
            "sanction_date DATE, expenditure_amount_inr DOUBLE)"
        )
        con.executemany("INSERT INTO works VALUES (?, ?, ?, ?)", rows)

        def matched(kind: str) -> set[str]:
            clause, params = policy.pendency_clause(kind, AS_OF)
            result = con.execute(f"SELECT work_id FROM works WHERE {clause}", params).fetchall()
            return {r[0] for r in result}

        assert matched("late_sanction") == {"LS-46"}
        assert matched("open_past_one_year") == {"OY-366"}
        assert matched("no_payment_90_days") == {"NP-91-ZERO", "NP-91-NULL"}


def test_pendency_clause_unknown_kind_raises():
    with pytest.raises(ValueError):
        policy.pendency_clause("early_warning", AS_OF)


# --- snapshot.data_as_of_date ----------------------------------------------


def test_data_as_of_date_reads_the_manifest(bootstrapped_snapshot):
    assert api_snapshot.data_as_of_date() == bootstrapped_snapshot["data_as_of"][:10]


def test_data_as_of_date_is_none_without_a_manifest(tmp_path):
    assert api_snapshot.data_as_of_date(tmp_path) is None


# --- /api/works: district_authority, constituency, pendency filters -------


def test_district_authority_filters_works(client, works_fixture):
    da = works_fixture[0]["implementing_district_authority"]
    expected = sum(1 for r in works_fixture if r["implementing_district_authority"] == da)
    body = client.get("/api/works", params={"district_authority": da, "page_size": 200}).json()
    assert body["meta"]["total"] == expected
    assert all(r["implementing_district_authority"] == da for r in body["data"])


def test_constituency_filters_works(client, works_fixture):
    constituency = works_fixture[0]["constituency"]
    expected = sum(1 for r in works_fixture if r["constituency"] == constituency)
    body = client.get("/api/works", params={"constituency": constituency, "page_size": 200}).json()
    assert body["meta"]["total"] == expected
    assert all(r["constituency"] == constituency for r in body["data"])


def test_blank_district_authority_and_constituency_are_ignored(client, works_fixture):
    body = client.get(
        "/api/works", params={"district_authority": "", "constituency": "", "page_size": 200}
    ).json()
    assert body["meta"]["total"] == len(works_fixture)


def test_district_authority_scope_gives_the_narrowed_quota(client, works_fixture):
    population = _population(works_fixture)
    da, count = Counter(r["implementing_district_authority"] for r in population).most_common(1)[0]
    body = client.get(
        "/api/works",
        params={"district_authority": da, "scope": "under_implementation", "page_size": 1},
    ).json()
    assert body["meta"]["total"] == count
    assert body["meta"]["quota_n"] == policy.quota_for(count)


def test_bad_pendency_kind_is_422(client):
    response = client.get("/api/works", params={"pendency": "not_a_real_kind"})
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_pendency_filter_503s_when_as_of_is_missing(client, monkeypatch):
    monkeypatch.setattr(api_snapshot, "data_as_of_date", lambda *a, **kw: None)
    response = client.get("/api/works", params={"pendency": "late_sanction"})
    assert response.status_code == 503
    assert response.json()["success"] is False


# --- /api/works/facets: district_authorities, constituencies --------------


def test_facets_include_district_authorities_and_constituencies(client, works_fixture):
    data = client.get("/api/works/facets").json()["data"]
    population = _population(works_fixture)

    da_counts = {f["value"]: f["count"] for f in data["district_authorities"]}
    assert da_counts == dict(Counter(r["implementing_district_authority"] for r in population))

    expected = Counter((r["constituency"], r["mp_name"]) for r in population)
    got = {(row["value"], row["mp_name"]): row["count"] for row in data["constituencies"]}
    assert got == dict(expected)


# --- days_to_sanction / days_since_sanction on list and detail rows -------


def test_get_work_carries_days_to_sanction_and_days_since_sanction(client, works_fixture):
    fixture_row = next(r for r in works_fixture if r["work_id"] == "MPLADS-FX-0003")
    as_of = date.fromisoformat(api_snapshot.data_as_of_date())
    recommendation = date.fromisoformat(fixture_row["recommendation_date"])
    sanction = date.fromisoformat(fixture_row["sanction_date"])

    body = client.get("/api/works/MPLADS-FX-0003").json()["data"]

    assert body["days_to_sanction"] == (sanction - recommendation).days
    assert body["days_since_sanction"] == (as_of - sanction).days


def test_list_rows_carry_days_since_sanction_with_no_recommendation_date(client, works_fixture):
    fixture_row = next(r for r in works_fixture if r["work_id"] == "MPLADS-FX-0004")
    as_of = date.fromisoformat(api_snapshot.data_as_of_date())
    sanction = date.fromisoformat(fixture_row["sanction_date"])

    body = client.get("/api/works", params={"q": "MPLADS-FX-0004"}).json()["data"]
    row = next(r for r in body if r["work_id"] == "MPLADS-FX-0004")

    assert row["days_to_sanction"] is None
    assert row["days_since_sanction"] == (as_of - sanction).days


def test_days_fields_are_both_none_when_dates_are_missing(client):
    body = client.get("/api/works/MPLADS-FX-0015").json()["data"]
    assert body["days_to_sanction"] is None
    assert body["days_since_sanction"] is None


def test_decorate_degrades_days_since_sanction_to_none_when_as_of_is_missing(client, monkeypatch):
    monkeypatch.setattr(api_snapshot, "data_as_of_date", lambda *a, **kw: None)
    body = client.get("/api/works/MPLADS-FX-0003").json()["data"]
    assert body["days_since_sanction"] is None
    # days_to_sanction never depended on as_of, so it is unaffected.
    assert body["days_to_sanction"] is not None


# --- GET /api/pendency ------------------------------------------------------


def test_pendency_endpoint_503s_when_as_of_is_missing(client, monkeypatch):
    monkeypatch.setattr(api_snapshot, "data_as_of_date", lambda *a, **kw: None)
    response = client.get("/api/pendency")
    assert response.status_code == 503
    assert response.json()["success"] is False


def test_bad_group_by_is_422(client):
    response = client.get("/api/pendency", params={"group_by": "not_a_real_dimension"})
    assert response.status_code == 422


def test_pendency_as_of_matches_the_manifest(client, bootstrapped_snapshot):
    assert _pendency(client)["as_of"] == bootstrapped_snapshot["data_as_of"][:10]


def test_pendency_population_matches_under_implementation_scope(client, works_fixture):
    population = _population(works_fixture)
    summary = _pendency(client)
    assert summary["population_n"] == len(population)
    assert summary["population_inr"] == round(
        sum(r["sanctioned_amount_inr"] for r in population), 2
    )


def test_pendency_counts_and_amounts_match_independent_computation(client, works_fixture):
    population = _population(works_fixture)
    as_of = date.fromisoformat(api_snapshot.data_as_of_date())
    summary = _pendency(client)
    for kind in policy.PENDENCY_KINDS:
        expected_rows = [r for r in population if _matches_pendency(r, kind, as_of)]
        assert summary["kinds"][kind]["count"] == len(expected_rows)
        assert summary["kinds"][kind]["sanctioned_inr"] == round(
            sum(r["sanctioned_amount_inr"] for r in expected_rows), 2
        )


def test_pendency_kind_counts_match_the_works_list_filter(client):
    summary = _pendency(client)
    for kind in policy.PENDENCY_KINDS:
        works_body = client.get(
            "/api/works",
            params={"pendency": kind, "scope": "under_implementation", "page_size": 200},
        ).json()
        assert works_body["meta"]["total"] == summary["kinds"][kind]["count"]


def test_pendency_median_days_to_sanction_over_both_dates_present(client, works_fixture):
    population = _population(works_fixture)
    both_present = [r for r in population if r["recommendation_date"] and r["sanction_date"]]
    summary = _pendency(client)
    median = summary["kinds"]["late_sanction"]["median_days_to_sanction"]
    if not both_present:
        assert median is None
        return
    diffs = [
        (date.fromisoformat(r["sanction_date"]) - date.fromisoformat(r["recommendation_date"])).days
        for r in both_present
    ]
    assert median == round(statistics.median(diffs))


def test_pendency_other_kinds_have_no_median_field(client):
    summary = _pendency(client)
    assert "median_days_to_sanction" not in summary["kinds"]["open_past_one_year"]
    assert "median_days_to_sanction" not in summary["kinds"]["no_payment_90_days"]


def test_pendency_third_party_counts(client, works_fixture):
    population = _population(works_fixture)
    a = sum(1 for r in population if r["sanctioned_amount_inr"] >= 2_500_000)
    b = sum(1 for r in population if 1_500_000 <= r["sanctioned_amount_inr"] < 2_500_000)
    assert _pendency(client)["third_party"] == {
        "at_or_above_25_lakh": a,
        "between_15_and_25_lakh": b,
        "required_n": a + math.ceil(b / 2),
    }


def test_pendency_district_authority_n_and_quota_sum(client, works_fixture):
    population = _population(works_fixture)
    per_da = dict(Counter(r["implementing_district_authority"] for r in population))
    summary = _pendency(client)
    assert summary["district_authority_n"] == len(per_da)
    assert summary["quota_sum"] == sum(policy.quota_by_group(per_da).values())


def test_pendency_district_authority_filter_narrows_the_scope(client, works_fixture):
    population = _population(works_fixture)
    da, count = Counter(r["implementing_district_authority"] for r in population).most_common(1)[0]
    summary = _pendency(client, {"district_authority": da})
    assert summary["population_n"] == count
    assert summary["district_authority_n"] == 1
    assert summary["quota_sum"] == policy.quota_for(count)


def test_pendency_state_is_repeatable(client, works_fixture):
    population = _population(works_fixture)
    (first, first_n), (second, second_n) = Counter(r["state"] for r in population).most_common(2)
    summary = _pendency(client, [("state", first), ("state", second)])
    assert summary["population_n"] == first_n + second_n


def test_pendency_groups_is_null_without_group_by(client):
    assert _pendency(client)["groups"] is None


def test_pendency_groups_sum_to_the_totals(client):
    summary = _pendency(client, {"group_by": "state"})
    groups = summary["groups"]
    assert groups is not None
    assert sum(g["population_n"] for g in groups) == summary["population_n"]
    for kind in policy.PENDENCY_KINDS:
        assert sum(g[kind] for g in groups) == summary["kinds"][kind]["count"]


def test_pendency_groups_quota_n_and_sort_order(client):
    summary = _pendency(client, {"group_by": "district_authority"})
    groups = summary["groups"]
    assert [g["quota_n"] for g in groups] == [policy.quota_for(g["population_n"]) for g in groups]
    sort_keys = [(-g["population_n"], g["group"]) for g in groups]
    assert sort_keys == sorted(sort_keys)


def test_pendency_groups_by_constituency_covers_every_seat_in_scope(client, works_fixture):
    population = _population(works_fixture)
    summary = _pendency(client, {"group_by": "constituency"})
    groups = {g["group"]: g for g in summary["groups"]}
    assert set(groups) == {r["constituency"] for r in population}
