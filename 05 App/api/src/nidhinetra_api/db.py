"""DuckDB connection factory, per the build plan's pattern (nidhinetra-app
-build.md section 4.1): Parquet is the committed artifact, DuckDB is a
disposable in-memory engine rebuilt from it. No .db file is ever written,
so there is nothing here that can corrupt across a laptop swap or a fresh
clone -- only data/snapshot/*.parquet needs to survive that.

A fresh connection is opened per call rather than held as a module-level
singleton: `connect()` itself is cheap (two CREATE VIEW statements, no
data loaded until a query actually runs), and a fresh connection per
request sidesteps any question of whether one DuckDB connection object is
safe to share across FastAPI's threadpool. Each CREATE VIEW is a live
query against the Parquet file path, not a snapshot taken at CREATE VIEW
time, so a connection opened after `build_snapshot()` has swapped in new
Parquet files sees the new data immediately -- confirmed empirically
against the atomic rename in build_snapshot.py's _atomic_write_parquet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

# api/src/nidhinetra_api/db.py -> parents[3] is "05 App/"
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
    con.execute(f"CREATE VIEW works  AS SELECT * FROM '{works_path.as_posix()}'")
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
]
