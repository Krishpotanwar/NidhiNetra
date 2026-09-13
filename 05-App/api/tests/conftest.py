"""Shared fixtures for the API test suite.

Bootstraps a real data/snapshot/ from the CP0 fixtures once per test
session and runs every test against it through the real DuckDB-over-
Parquet read path -- the data layer is never mocked, per the eng review
instruction for this pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from nidhinetra_api import db
from nidhinetra_api import snapshot as api_snapshot
from nidhinetra_api.main import app
from nidhinetra_pipeline.build_snapshot import build_snapshot
from nidhinetra_pipeline.outcomes import store as outcomes_store

# api/tests/conftest.py -> parents[2] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[2]
_WORKS_FIXTURE_PATH = _APP_ROOT / "contracts" / "fixtures" / "works.fixture.json"

UNDER_IMPLEMENTATION = ("Sanctioned", "In Progress")


@pytest.fixture(scope="session", autouse=True)
def bootstrapped_snapshot(tmp_path_factory) -> dict[str, Any]:
    """Builds a snapshot from the CP0 fixtures into a temp directory and
    points the API's readers at it for the whole session -- the same call
    main.py's startup hook makes, but isolated.

    Isolated on both sides, and both mattered as of 2026-09-04:

    - `raw_dir` at a nonexistent path forces the CP0-fixture branch.
      build_snapshot() now prefers the most recent cached
      acquisition-ladder snapshot in data/raw/, so without this the suite
      silently switched to 79,068 live records and every assertion written
      against the 20-row fixture failed.
    - `snapshot_dir` in tmp, with db.SNAPSHOT_DIR repointed to match, keeps
      the suite from writing over the real data/snapshot/. That was
      harmless while every path produced the same fixture output; once
      rung 1 went live, running `pytest api/` destroyed a real snapshot and
      replaced it with 20 demo rows, which is a genuinely bad thing for a
      test suite to do to a working install.
    """
    snapshot_dir = tmp_path_factory.mktemp("snapshot")
    manifest = build_snapshot(
        snapshot_dir=snapshot_dir,
        raw_dir=snapshot_dir / "no-cache-here",
    )
    # The routers call db.connect() and snapshot helpers with no arguments,
    # so the module constants are the only seam available.
    db.SNAPSHOT_DIR = snapshot_dir
    api_snapshot.SNAPSHOT_DIR = snapshot_dir
    # POST /api/refresh rebuilds; without this it would rebuild from the
    # operator's real acquisition cache and replace this session's 20-row
    # fixture snapshot with 79,068 live records mid-suite.
    api_snapshot.RAW_DIR = snapshot_dir / "no-cache-here"
    return manifest


@pytest.fixture(autouse=True)
def isolated_outcomes_db(tmp_path: Path) -> Path:
    """Repoints the outcomes store at a per-test temp file -- same reason
    `bootstrapped_snapshot` repoints db.SNAPSHOT_DIR: without this, running
    `pytest api/` would read and write the operator's real
    data/outcomes/outcomes.db, a file that (unlike the snapshot) holds
    non-regenerable human judgements. Function-scoped (not session-scoped
    like the snapshot fixture) because outcome writes are exactly what
    these tests exercise, and tests must not see each other's rows.
    """
    db_path = tmp_path / "outcomes.db"
    outcomes_store.DEFAULT_DB_PATH = db_path
    return db_path


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def works_fixture() -> list[dict[str, Any]]:
    """The raw CP0 fixture rows, for tests that compute an independent
    expected value rather than trusting the endpoint under test.
    """
    return json.loads(_WORKS_FIXTURE_PATH.read_text(encoding="utf-8"))
