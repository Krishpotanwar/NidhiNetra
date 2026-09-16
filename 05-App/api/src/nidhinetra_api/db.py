"""DuckDB connection factory, per the build plan's pattern (nidhinetra-app
-build.md section 4.1): Parquet is the committed artifact, DuckDB is a
disposable in-memory engine rebuilt from it. No .db file is ever written,
so there is nothing here that can corrupt across a laptop swap or a fresh
clone -- only data/snapshot/*.parquet needs to survive that.

A fresh connection is opened per call rather than held as a module-level
singleton: `connect()` itself is cheap (a few CREATE VIEW statements, no
data loaded until a query actually runs), and a fresh connection per
request sidesteps any question of whether one DuckDB connection object is
safe to share across FastAPI's threadpool. Each CREATE VIEW is a live
query against the Parquet file path, not a snapshot taken at CREATE VIEW
time, so a connection opened after `build_snapshot()` has swapped in new
Parquet files sees the new data immediately -- confirmed empirically
against the atomic rename in build_snapshot.py's _atomic_write_parquet.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

import duckdb

# api/src/nidhinetra_api/db.py -> parents[3] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = _APP_ROOT / "data" / "snapshot"

# scored.parquet columns build_snapshot.py wrote as JSON text (see that
# module's _JSON_ENCODED_SCORED_COLUMNS docstring for why flags,
# why_flagged and peer_group specifically can't be trusted as native
# parquet list/struct columns). Any query that selects these columns must
# decode them back with `decode_scored_json(rows)` before the values reach
# a response envelope.
JSON_ENCODED_SCORED_COLUMNS = ("flags", "why_flagged", "peer_group")


class SnapshotNotReadyError(Exception):
    """Raised when data/snapshot/{works,scored}.parquet do not exist yet.
    main.py's startup hook is what's supposed to prevent this by
    bootstrapping the snapshot before the app starts serving; this
    exception is the defensive fallback if something calls connect()
    before that has happened.
    """


def works_columns(snapshot_dir: Path | None = None) -> set[str]:
    """Column names physically present in works.parquet, before any of
    connect()'s compatibility projections. Lets a caller tell a snapshot built
    before a contract change from a current one (routers/graph.py uses it for
    F-01).
    """
    snapshot_dir = snapshot_dir or SNAPSHOT_DIR
    works_path = snapshot_dir / "works.parquet"
    if not works_path.exists():
        raise SnapshotNotReadyError(
            f"snapshot parquet files not found in {snapshot_dir}. Run "
            "nidhinetra_pipeline.build_snapshot.build_snapshot() first "
            "(main.py's startup hook does this automatically)."
        )
    with contextlib.closing(duckdb.connect(":memory:")) as con:
        rows = con.execute(f"DESCRIBE SELECT * FROM '{works_path.as_posix()}'").fetchall()
    return {row[0] for row in rows}


def connect(snapshot_dir: Path | None = None) -> duckdb.DuckDBPyConnection:
    snapshot_dir = snapshot_dir or SNAPSHOT_DIR
    works_path = snapshot_dir / "works.parquet"
    scored_path = snapshot_dir / "scored.parquet"
    if not works_path.exists() or not scored_path.exists():
        raise SnapshotNotReadyError(
            f"snapshot parquet files not found in {snapshot_dir}. Run "
            "nidhinetra_pipeline.build_snapshot.build_snapshot() first "
            "(main.py's startup hook does this automatically)."
        )

    con = duckdb.connect(":memory:")
    con.execute(f"CREATE VIEW works_snapshot AS SELECT * FROM '{works_path.as_posix()}'")
    work_columns = {
        row[0] for row in con.execute("DESCRIBE SELECT * FROM works_snapshot").fetchall()
    }
    star = "works_snapshot.*"
    optional_columns = []
    if "vendor_id" not in work_columns:
        # R-06 adds vendor_id to newly-built snapshots, but the real
        # committed snapshot predates that field. Keep that snapshot
        # queryable until an operator explicitly rebuilds it; a missing
        # source identifier is truthfully represented as null.
        optional_columns.append("CAST(NULL AS VARCHAR) AS vendor_id")
    if "implementing_district_authority" not in work_columns:
        # F-01 legacy snapshot: built before the IDA/IA split, so its
        # implementing_agency column holds IDA_NAME values. Serve them under
        # the field that means District Authority, and report the true agency
        # as unknown, never as the authority.
        star = "* EXCLUDE (implementing_agency)"
        optional_columns.append(
            "works_snapshot.implementing_agency AS implementing_district_authority"
        )
        optional_columns.append("CAST(NULL AS VARCHAR) AS implementing_agency")
    projection = ", ".join([star, *optional_columns])
    con.execute(f"CREATE VIEW works AS SELECT {projection} FROM works_snapshot")
    con.execute(f"CREATE VIEW scored AS SELECT * FROM '{scored_path.as_posix()}'")
    return con


def rows_as_dicts(
    con: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None
) -> list[dict[str, Any]]:
    """Runs `sql` and returns the result as a list of plain dicts, one per
    row -- the shape this whole API treats records as (see models.py's
    module docstring on the deferred codegen gap). Deliberately does not
    go through pandas: DuckDB's own cursor description + fetchall() is
    enough, and it keeps `nidhinetra-api` from needing an undeclared,
    merely-transitive dependency on pandas (a real dependency of
    nidhinetra-pipeline, not of this package).
    """
    result = con.execute(sql, params or [])
    columns = [c[0] for c in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def decode_scored_json(
    rows: list[dict[str, Any]], columns: tuple[str, ...] = JSON_ENCODED_SCORED_COLUMNS
) -> list[dict[str, Any]]:
    """Decodes the JSON-text scored columns back into real lists/dicts in
    place, and casts peer_group.n back to int (parquet's struct round trip
    turns it into a float64 -- see build_snapshot.py). Only touches
    columns that are actually present in a given row, so this is safe to
    call on rows from either a full works+scored join or a scored-only
    query.
    """
    for row in rows:
        for column in columns:
            if column not in row or row[column] is None:
                continue
            value = json.loads(row[column])
            if column == "peer_group" and value is not None:
                value["n"] = int(value["n"])
            row[column] = value
    return rows


__all__ = [
    "JSON_ENCODED_SCORED_COLUMNS",
    "SNAPSHOT_DIR",
    "SnapshotNotReadyError",
    "connect",
    "decode_scored_json",
    "rows_as_dicts",
    "works_columns",
]
