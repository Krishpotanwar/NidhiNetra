"""GET /api/works: sorting (the hard contract requirement), each filter
individually, pagination, and the envelope shape.
"""

from __future__ import annotations

import shutil
from collections import Counter

import duckdb
from nidhinetra_api import db
from nidhinetra_api.routers import works as works_router
from nidhinetra_pipeline.risk.peer_groups import financial_year_of


def test_legacy_snapshot_without_vendor_id_stays_queryable(tmp_path):
    """Deploying R-06 must not strand the committed pre-R-06 snapshot.

    The checked-in production Parquet predates ``vendor_id``.  Until an
    operator performs an authorised rebuild, the API compatibility view
    must expose that new field as null rather than failing every works
    query with a DuckDB binder error.
    """
    legacy_snapshot = tmp_path / "legacy-snapshot"
    legacy_snapshot.mkdir()
    works_path = legacy_snapshot / "works.parquet"
    with duckdb.connect(":memory:") as connection:
        connection.execute(
            "CREATE TABLE legacy_works AS SELECT * EXCLUDE (vendor_id) FROM read_parquet(?)",
            [str(db.SNAPSHOT_DIR / "works.parquet")],
        )
        connection.execute("COPY legacy_works TO ? (FORMAT PARQUET)", [str(works_path)])
    shutil.copyfile(db.SNAPSHOT_DIR / "scored.parquet", legacy_snapshot / "scored.parquet")

    with db.connect(legacy_snapshot) as connection:
        rows = db.rows_as_dicts(connection, "SELECT vendor_id FROM works LIMIT 1")

    assert rows == [{"vendor_id": None}]


def test_legacy_snapshot_without_source_fields_stays_queryable(tmp_path, works_fixture):
    """Phase 0 adds work_description, activity_name and recommendation_date
    to newly built snapshots, but the committed pre-Phase-0 snapshot has none
    of them. Until an operator performs an authorised rebuild, the API
    compatibility view must expose those fields as null rather than failing
    every works query with a DuckDB binder error.
    """
    legacy_snapshot = tmp_path / "legacy-source-fields-snapshot"
    legacy_snapshot.mkdir()
    works_path = legacy_snapshot / "works.parquet"
    with duckdb.connect(":memory:") as connection:
        connection.execute(
            "CREATE TABLE legacy_works AS SELECT * "
            "EXCLUDE (work_description, activity_name, recommendation_date) "
            "FROM read_parquet(?)",
            [str(db.SNAPSHOT_DIR / "works.parquet")],
        )
        connection.execute("COPY legacy_works TO ? (FORMAT PARQUET)", [str(works_path)])
    shutil.copyfile(db.SNAPSHOT_DIR / "scored.parquet", legacy_snapshot / "scored.parquet")

    work_id = works_fixture[0]["work_id"]
    with db.connect(legacy_snapshot) as connection:
        rows = db.rows_as_dicts(
            connection, works_router._MERGED_SELECT + " WHERE works.work_id = ?", [work_id]
        )

    assert rows[0]["work_description"] is None
    assert rows[0]["activity_name"] is None
    assert rows[0]["recommendation_date"] is None


def test_legacy_snapshot_answers_detail_and_search_through_the_real_endpoints(
    tmp_path, works_fixture, monkeypatch, client
):
    """The tests above query the compatibility view directly; this one goes
    through the real endpoints. The committed production Parquet is the
    14-column shape this builds: no vendor_id, no IDA/IA split and none of
    Phase 0's three source fields. That is the shape the app actually serves
    to an officer until someone performs the gated rebuild, so both the
    detail endpoint and search have to answer on it correctly, not only the
    SQL compatibility view underneath them.
    """
    legacy_snapshot = tmp_path / "legacy-committed-shape-snapshot"
    legacy_snapshot.mkdir()
    works_path = legacy_snapshot / "works.parquet"
    with duckdb.connect(":memory:") as connection:
        connection.execute(
            "CREATE TABLE legacy_works AS SELECT * EXCLUDE "
            "(implementing_district_authority, implementing_agency, vendor_id, "
            "work_description, activity_name, recommendation_date), "
            "implementing_district_authority AS implementing_agency "
            "FROM read_parquet(?)",
            [str(db.SNAPSHOT_DIR / "works.parquet")],
        )
        connection.execute("COPY legacy_works TO ? (FORMAT PARQUET)", [str(works_path)])
    shutil.copyfile(db.SNAPSHOT_DIR / "scored.parquet", legacy_snapshot / "scored.parquet")

    assert len(db.works_columns(legacy_snapshot)) == 14

    monkeypatch.setattr(db, "SNAPSHOT_DIR", legacy_snapshot)

    work_id = works_fixture[0]["work_id"]
    detail = client.get(f"/api/works/{work_id}")
    assert detail.status_code == 200
    record = detail.json()["data"]
    assert record["work_description"] is None
    assert record["activity_name"] is None
    assert record["recommendation_date"] is None
    assert record["implementing_district_authority"] is not None

    listing = client.get("/api/works", params={"q": "District Authority", "page_size": 200})
    assert listing.status_code == 200
    rows = listing.json()["data"]
    assert len(rows) > 0
    for row in rows:
        assert row["work_description"] is None
        assert row["activity_name"] is None
        assert row["recommendation_date"] is None


def test_legacy_snapshot_ida_values_are_never_served_as_the_agency(tmp_path):
    """F-01 legacy mode (decision D4). A snapshot built before the split has no
    implementing_district_authority column, and its implementing_agency column
    holds IDA_NAME values. The API must expose those values as the District
    Authority and report the agency as unknown.
    """
    legacy_snapshot = tmp_path / "legacy-f01-snapshot"
    legacy_snapshot.mkdir()
    works_path = legacy_snapshot / "works.parquet"
    with duckdb.connect(":memory:") as connection:
        connection.execute(
            "CREATE TABLE legacy_works AS SELECT * "
            "EXCLUDE (implementing_district_authority, implementing_agency), "
            "implementing_district_authority AS implementing_agency FROM read_parquet(?)",
            [str(db.SNAPSHOT_DIR / "works.parquet")],
        )
        connection.execute("COPY legacy_works TO ? (FORMAT PARQUET)", [str(works_path)])
        expected = dict(
            connection.execute("SELECT work_id, implementing_agency FROM legacy_works").fetchall()
        )
    shutil.copyfile(db.SNAPSHOT_DIR / "scored.parquet", legacy_snapshot / "scored.parquet")

    assert "implementing_district_authority" not in db.works_columns(legacy_snapshot)
    with db.connect(legacy_snapshot) as connection:
        rows = db.rows_as_dicts(
            connection,
            "SELECT work_id, implementing_district_authority, implementing_agency FROM works",
        )

    assert {r["work_id"]: r["implementing_district_authority"] for r in rows} == expected
    assert all(r["implementing_agency"] is None for r in rows)


def test_list_works_returns_200_and_envelope_shape(client):
    response = client.get("/api/works")
    assert response.status_code == 200

    body = response.json()
    assert set(body.keys()) == {"success", "data", "error", "meta"}
    assert body["success"] is True
    assert body["error"] is None
    assert isinstance(body["data"], list)
    assert body["meta"]["total"] == len(body["data"]) == 20


def test_list_works_always_sorted_by_inspection_rank_ascending(client):
    """The one hard requirement in contracts/openapi.yaml's /api/works
    description: sorted by inspection_rank ascending, always -- filters
    narrow the set, they never change the sort.
    """
    body = client.get("/api/works").json()
    ranks = [row["inspection_rank"] for row in body["data"]]
    assert ranks == sorted(ranks)
    assert ranks == list(range(1, 21))  # dense, gap-free, per CP2


def test_list_works_sorted_by_inspection_rank_still_holds_under_a_filter(client, works_fixture):
    state = works_fixture[0]["state"]
    body = client.get("/api/works", params={"state": state}).json()
    ranks = [row["inspection_rank"] for row in body["data"]]
    assert ranks == sorted(ranks)
    assert len(ranks) > 0  # otherwise this test is vacuous


def test_list_works_filters_by_state(client, works_fixture):
    counts = Counter(row["state"] for row in works_fixture)
    state, expected_count = counts.most_common(1)[0]

    body = client.get("/api/works", params={"state": state}).json()

    assert body["meta"]["total"] == expected_count
    assert all(row["state"] == state for row in body["data"])


def test_list_works_filters_by_category(client, works_fixture):
    counts = Counter(row["work_category"] for row in works_fixture)
    category, expected_count = counts.most_common(1)[0]

    body = client.get("/api/works", params={"category": category}).json()

    assert body["meta"]["total"] == expected_count
    assert all(row["work_category"] == category for row in body["data"])


def test_list_works_filters_by_flag(client):
    """The CP0 fixture set is only 20 rows, below the eng-review peer-group
    floor of 30 (risk_scored_record.schema.json, engine.py), so no record
    is ever flagged against it -- the correct, honest behaviour is a 200
    with an empty result, not an error and not a nonempty list.
    """
    body = client.get("/api/works", params={"flag": "cost_outlier"}).json()

    assert body["success"] is True
    assert body["data"] == []
    assert body["meta"]["total"] == 0


def test_list_works_filters_by_year(client, works_fixture):
    reference = next(r for r in works_fixture if r["sanction_date"] or r["last_updated"])
    year = financial_year_of(reference)
    assert year is not None  # otherwise this test picked a bad fixture row

    expected_count = sum(1 for r in works_fixture if financial_year_of(r) == year)

    body = client.get("/api/works", params={"year": year}).json()

    assert body["meta"]["total"] == expected_count
    assert expected_count > 0


def test_list_works_pagination(client):
    body = client.get("/api/works", params={"page": 2, "page_size": 5}).json()

    paging = {k: body["meta"][k] for k in ("page", "page_size", "total", "total_pages")}
    assert paging == {"page": 2, "page_size": 5, "total": 20, "total_pages": 4}
    assert len(body["data"]) == 5
    # Page 2 continues where page 1 left off, in the same sorted order.
    ranks = [row["inspection_rank"] for row in body["data"]]
    assert ranks == [6, 7, 8, 9, 10]


def test_list_works_page_size_over_max_is_a_422(client):
    response = client.get("/api/works", params={"page_size": 500})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]
