"""snapshot.read_early_warning, the pendency=early_warning filter and row
flag (works._where/_decorate), GET /api/early-warning and the pendency
summary's early_warning_n (Task 8 Part B).

Part A (pipeline/src/nidhinetra_pipeline/early_warning.py, committed
6f55d10) already ships data/snapshot/early_warning.json on the real
snapshot; these tests write their own small fixture into the session's tmp
snapshot dir instead of depending on that file, so the suite still passes
on a machine that has never run the CLI. bootstrapped_snapshot's tmp dir is
session-scoped and shared with every other test module, so every test that
writes the fixture removes it again on teardown (write_early_warning below).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest
from nidhinetra_api import policy
from nidhinetra_api import snapshot as api_snapshot

# Two works.fixture.json rows under implementation (In Progress, D1) plus one
# Completed row, so a scope-narrowed count (early_warning_n) has something
# real to exclude, and the two In Progress rows sit in different states
# (Uttar Pradesh, Rajasthan) so a state scope narrows to exactly one.
WATCH_IN_PROGRESS = ["MPLADS-FX-0004", "MPLADS-FX-0006"]
WATCH_COMPLETED = "MPLADS-FX-0003"


def _artifact(bootstrapped_snapshot: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    artifact = {
        "model_version": "early_warning_v1",
        "data_as_of": bootstrapped_snapshot["data_as_of"][:10],
        "status": "shipped",
        "cohort": {
            "start": "2024-07-04",
            "train_cutoff": "2025-01-04",
            "end": "2025-04-04",
            "train_n": 10,
            "test_n": 10,
        },
        "features": {
            "numeric": ["log_sanctioned", "agency_prior", "sanction_month"],
            "categorical": ["work_category", "state"],
        },
        "metrics": {"roc_auc": 0.7, "average_precision": 0.4, "base_rate": 0.2, "lift_at_10": 2.0},
        "scored_n": 3,
        "watch_n": 3,
        "watch": [*WATCH_IN_PROGRESS, WATCH_COMPLETED],
    }
    artifact.update(overrides)
    return artifact


@pytest.fixture()
def write_early_warning(bootstrapped_snapshot: dict[str, Any]) -> Callable[..., dict[str, Any]]:
    """Writes a small fixture early_warning.json into the session's tmp
    snapshot dir and removes it again on teardown, so tests in other
    modules never see it left behind.
    """
    path = api_snapshot.SNAPSHOT_DIR / "early_warning.json"

    def _write(**overrides: Any) -> dict[str, Any]:
        artifact = _artifact(bootstrapped_snapshot, **overrides)
        path.write_text(json.dumps(artifact), encoding="utf-8")
        return artifact

    try:
        yield _write
    finally:
        path.unlink(missing_ok=True)


# --- snapshot.read_early_warning ------------------------------------------


def test_read_early_warning_is_none_without_a_file(bootstrapped_snapshot):
    assert api_snapshot.read_early_warning() is None


def test_read_early_warning_returns_the_artifact_when_shipped_and_fresh(write_early_warning):
    written = write_early_warning()
    assert api_snapshot.read_early_warning() == written


def test_read_early_warning_is_none_when_data_as_of_is_stale(write_early_warning):
    write_early_warning(data_as_of="2000-01-01")
    assert api_snapshot.read_early_warning() is None


def test_read_early_warning_is_none_when_status_is_not_shipped(write_early_warning):
    write_early_warning(status="not_shipped")
    assert api_snapshot.read_early_warning() is None


def test_read_early_warning_cache_picks_up_a_rewrite(write_early_warning):
    first = write_early_warning()
    assert api_snapshot.read_early_warning() == first
    second = write_early_warning(watch=[WATCH_IN_PROGRESS[0]], watch_n=1, scored_n=1)
    assert api_snapshot.read_early_warning() == second


# --- policy.pendency_clause stays guideline-only (R6) ----------------------


def test_pendency_clause_still_rejects_early_warning():
    with pytest.raises(ValueError):
        policy.pendency_clause("early_warning", "2026-09-04")


# --- /api/works: pendency=early_warning filter and the row flag -----------


def test_pendency_early_warning_matches_nothing_without_an_artifact(client):
    body = client.get("/api/works", params={"pendency": "early_warning", "page_size": 200}).json()
    assert body["meta"]["total"] == 0


def test_pendency_early_warning_filters_to_the_watch_list(client, write_early_warning):
    write_early_warning()
    body = client.get("/api/works", params={"pendency": "early_warning", "page_size": 200}).json()
    assert {r["work_id"] for r in body["data"]} == {*WATCH_IN_PROGRESS, WATCH_COMPLETED}


def test_pendency_early_warning_503s_when_as_of_is_missing(client, monkeypatch):
    monkeypatch.setattr(api_snapshot, "data_as_of_date", lambda *a, **kw: None)
    response = client.get("/api/works", params={"pendency": "early_warning"})
    assert response.status_code == 503
    assert response.json()["success"] is False


def test_row_early_warning_flag_true_for_watch_members(client, write_early_warning):
    write_early_warning()
    body = client.get(f"/api/works/{WATCH_IN_PROGRESS[0]}").json()["data"]
    assert body["early_warning"] is True


def test_row_early_warning_flag_false_for_non_members(client, write_early_warning):
    write_early_warning()
    body = client.get("/api/works/MPLADS-FX-0001").json()["data"]
    assert body["early_warning"] is False


def test_row_early_warning_flag_false_without_an_artifact(client):
    body = client.get("/api/works/MPLADS-FX-0001").json()["data"]
    assert body["early_warning"] is False


def test_list_rows_carry_the_early_warning_flag(client, write_early_warning):
    write_early_warning()
    body = client.get("/api/works", params={"page_size": 200}).json()["data"]
    flagged = {r["work_id"] for r in body if r["early_warning"]}
    assert flagged == {*WATCH_IN_PROGRESS, WATCH_COMPLETED}


# --- GET /api/early-warning -------------------------------------------------


def test_get_early_warning_is_null_without_an_artifact(client):
    body = client.get("/api/early-warning").json()
    assert body["success"] is True
    assert body["data"] is None


def test_get_early_warning_returns_the_artifact_without_the_watch_list(client, write_early_warning):
    written = write_early_warning()
    body = client.get("/api/early-warning").json()["data"]
    assert "watch" not in body
    assert body == {k: v for k, v in written.items() if k != "watch"}


def test_get_early_warning_is_null_when_stale(client, write_early_warning):
    write_early_warning(data_as_of="2000-01-01")
    body = client.get("/api/early-warning").json()
    assert body["data"] is None


# --- GET /api/pendency: early_warning_n ------------------------------------


def test_pendency_early_warning_n_is_null_without_an_artifact(client):
    body = client.get("/api/pendency").json()["data"]
    assert body["early_warning_n"] is None


def test_pendency_early_warning_n_counts_only_the_scope_population(client, write_early_warning):
    write_early_warning()
    body = client.get("/api/pendency").json()["data"]
    # WATCH_COMPLETED is Completed, outside D1's under-implementation scope
    # that /api/pendency always applies -- only the two In Progress works count.
    assert body["early_warning_n"] == len(WATCH_IN_PROGRESS)


def test_pendency_early_warning_n_narrows_with_state_scope(client, write_early_warning):
    write_early_warning()
    body = client.get("/api/pendency", params={"state": "Uttar Pradesh"}).json()["data"]
    assert body["early_warning_n"] == 1  # only MPLADS-FX-0004 (In Progress, Uttar Pradesh)
