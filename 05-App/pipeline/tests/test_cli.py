"""Tests for cli.py's `build()` -- the real glue between the acquisition
ladder, normalization, and the on-disk cache.

This is the integration point CP6's "a partial or malformed pull leaves the
previous snapshot untouched" checkpoint item is actually about. The pieces
were already tested in isolation (ingest/test_mplads_api.py proves the ZK
error HTML raises a typed exception rather than returning garbage rows;
ingest/test_cache.py proves a failed write never disturbs a prior good
file), but nothing exercised `build()` itself end to end before this file --
there was no test_cli.py at all.

Rung 1 is genuinely blocked today (see rungs.py), so `run_ladder()` always
raises `AllRungsFailedError` in real runs and `build()` falls through to the
labelled fixture. That happy path is covered here too, but the case that
matters for CP6 is: a rung *does* return data (simulating the day Rung 1 is
unblocked, or an already-implemented rung misbehaving), that data is
malformed in a way normalize_records() rejects (the realistic shape of what
a ZK error page would produce if it were naively treated as tile rows --
missing required fields), and `build()` must return non-zero, log the
failure, and never call `cache.write_snapshot()` at all -- so a snapshot
already sitting in `raw_dir` from a previous good run is byte-for-byte
untouched.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from nidhinetra_pipeline import cli
from nidhinetra_pipeline.ingest import cache
from nidhinetra_pipeline.ingest.mplads_api import MpladsClientError
from nidhinetra_pipeline.ingest.rungs import AllRungsFailedError

VALID_RAW_RECORD = {
    "work_id": "MPLADS-TEST-0001",
    "state": "Bihar",
    "constituency": "Bihar Constituency 1",
    "mp_name": "Test MP",
    "tenure": "2024-2029",
    "implementing_district_authority": "Bihar District Authority",
    "implementing_agency": "PWD Division 1",
    "vendor_id": "test-vendor-id",
    "vendor_name": "Test Vendor Pvt Ltd",
    "work_category": "Road",
    "sanctioned_amount_inr": 1000000.0,
    "expenditure_amount_inr": 500000.0,
    "sanction_date": "2024-01-01",
    "completion_status": "In Progress",
    "last_updated": "2026-08-01",
}

# What a rung would hand back if it naively treated the ZK error HTML page
# (pipeline/tests/ingest/fixtures/zk_error_response.html) as if it were a
# row of real tile data -- no schema-required fields at all, just whatever
# scraps a parser desperate to find *something* might scrape out of an
# error page. mplads_api.py itself already refuses to let this shape reach
# a caller (see test_mplads_api.py's zk_html_error tests); this simulates
# the case where a rung's own bug lets something malformed slip past that
# guard, which is exactly the failure normalize_records()'s schema
# validation exists to catch as the last line of defence.
MALFORMED_RAW_RECORD = {"error": "invalid request", "zk_page": True}


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    d = tmp_path / "raw"
    d.mkdir()
    return d


@pytest.fixture
def snapshot_dir(tmp_path: Path) -> Path:
    """Stands in for data/snapshot/ -- the served analytical snapshot that
    build() now also rebuilds (Completion Plan Task 1.3, ultra-review's
    reproduced stale-snapshot defect: `cli build` used to stop after the
    raw cache write below, so `make pipeline` never touched what the API
    actually serves). Every build() call in this file must pass this,
    never the real default, or a test run would overwrite the committed
    data/snapshot/ on disk.
    """
    d = tmp_path / "snapshot"
    d.mkdir()
    return d


def test_build_falls_back_to_fixture_when_all_rungs_blocked(monkeypatch, raw_dir, snapshot_dir):
    """Today's real behaviour: Rung 1 is blocked, every other rung is
    unimplemented, so run_ladder() raises and build() must fall through to
    the labelled seed fixture rather than failing outright -- the pipeline
    stays runnable end to end even while live data is blocked.
    """

    def fake_run_ladder():
        raise AllRungsFailedError("all rungs blocked (simulated)")

    monkeypatch.setattr(cli, "run_ladder", fake_run_ladder)

    exit_code = cli.build(raw_dir=raw_dir, snapshot_dir=snapshot_dir)

    assert exit_code == 0
    written = list(raw_dir.glob("*.json"))
    assert len(written) == 1
    records = cache.latest_good(raw_dir=raw_dir)
    assert records is not None
    # Every record from the fixture fallback must carry source_rung=5
    # (labelled seed set), never silently pass for a live pull.
    import json

    payload = json.loads(records.read_text(encoding="utf-8"))
    assert len(payload) > 0
    assert all(r["source_rung"] == 5 for r in payload)


def test_build_writes_normalized_records_on_ladder_success(monkeypatch, raw_dir, snapshot_dir):
    """Sanity check for the day Rung 1 (or any rung) actually returns real
    data: build() normalizes it and caches it, stamping the rung that
    produced it.
    """

    def fake_run_ladder():
        return [dict(VALID_RAW_RECORD)], 1

    monkeypatch.setattr(cli, "run_ladder", fake_run_ladder)

    exit_code = cli.build(raw_dir=raw_dir, snapshot_dir=snapshot_dir)

    assert exit_code == 0
    path = cache.latest_good(raw_dir=raw_dir)
    assert path is not None
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload[0]["work_id"] == "MPLADS-TEST-0001"
    assert payload[0]["source_rung"] == 1


def test_build_also_rebuilds_the_served_snapshot_on_success(monkeypatch, raw_dir, snapshot_dir):
    """The Task 1.3 fix itself. Until 2026-09-08 build() stopped after the
    raw-cache write above, so `python -m nidhinetra_pipeline.cli build` and
    `make pipeline` never touched data/snapshot/ -- the files the API
    actually reads. A successful build must now also rebuild the served
    snapshot from what it just cached.
    """

    def fake_run_ladder():
        return [dict(VALID_RAW_RECORD)], 1

    monkeypatch.setattr(cli, "run_ladder", fake_run_ladder)

    exit_code = cli.build(raw_dir=raw_dir, snapshot_dir=snapshot_dir)

    assert exit_code == 0
    manifest_path = snapshot_dir / "manifest.json"
    assert manifest_path.exists(), (
        "build() must rebuild the served snapshot, not just the raw cache"
    )
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["row_count"] == 1
    assert manifest["source"] == "mplads_live_api"
    assert (snapshot_dir / "works.parquet").exists()
    assert (snapshot_dir / "scored.parquet").exists()
    assert (snapshot_dir / "graph.json").exists()


def test_build_reports_but_does_not_crash_on_a_snapshot_downgrade(
    monkeypatch, raw_dir, snapshot_dir, tmp_path
):
    """The safety case build_snapshot.py's SnapshotDowngradeError exists
    for (see its docstring): a machine already has the real, committed
    rung-1 served snapshot, but an empty raw cache (data/raw/ is
    gitignored -- a fresh clone or a second machine). A plain `build`
    there falls to the rung-5 fixture; that must never silently replace
    the better snapshot. build() must catch the guard's refusal, say so
    plainly, and still exit 0 -- the raw-cache write did succeed, and
    refusing the downgrade is correct behavior, not a failure.
    """
    from nidhinetra_pipeline import build_snapshot as bs

    # Build the "already has a real snapshot" precondition from a separate,
    # throwaway raw dir -- this must not touch the test's own (empty)
    # raw_dir fixture, which stands in for that machine's real gitignored
    # data/raw/.
    seed_raw_dir = tmp_path / "seed-raw"
    cache.write_snapshot([{**VALID_RAW_RECORD, "source_rung": 1}], raw_dir=seed_raw_dir)
    bs.build_snapshot(snapshot_dir=snapshot_dir, raw_dir=seed_raw_dir)
    manifest_path = snapshot_dir / "manifest.json"
    import json

    assert json.loads(manifest_path.read_text(encoding="utf-8"))["source"] == "mplads_live_api"
    manifest_bytes_before = manifest_path.read_bytes()

    def fake_run_ladder():
        raise AllRungsFailedError("all rungs blocked (simulated)")

    monkeypatch.setattr(cli, "run_ladder", fake_run_ladder)

    exit_code = cli.build(raw_dir=raw_dir, snapshot_dir=snapshot_dir)

    assert exit_code == 0
    assert cache.latest_good(raw_dir=raw_dir) is not None, (
        "the raw cache should still get the rung-5 fallback write"
    )
    assert manifest_path.read_bytes() == manifest_bytes_before, (
        "the served snapshot must not be silently downgraded"
    )


def test_malformed_pull_is_rejected_and_previous_snapshot_untouched(
    monkeypatch, raw_dir, snapshot_dir
):
    """CP6: 'A partial or malformed pull ... leaves the previous snapshot
    untouched.' Plants a real prior good snapshot first, then simulates a
    rung handing back malformed rows (the ZK-error-page shape). build()
    must return non-zero and cache.write_snapshot() must never be called --
    verified two ways: the previous file's bytes are unchanged, and no
    second file appears in raw_dir at all.
    """
    good_path = cache.write_snapshot(
        [dict(VALID_RAW_RECORD)],
        raw_dir=raw_dir,
        now=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )
    good_bytes_before = good_path.read_bytes()

    def fake_run_ladder():
        return [dict(MALFORMED_RAW_RECORD)], 1

    monkeypatch.setattr(cli, "run_ladder", fake_run_ladder)

    exit_code = cli.build(raw_dir=raw_dir, snapshot_dir=snapshot_dir)

    assert exit_code == 1
    assert good_path.read_bytes() == good_bytes_before
    assert cache.latest_good(raw_dir=raw_dir) == good_path
    assert len(list(raw_dir.glob("*.json"))) == 1, (
        "a malformed pull must never produce a second file in raw_dir, cached or otherwise"
    )
    assert not (snapshot_dir / "manifest.json").exists(), (
        "a rejected pull must never reach the served-snapshot rebuild either"
    )


def test_all_rungs_failed_and_fixture_missing_leaves_previous_snapshot_untouched(
    monkeypatch, raw_dir, snapshot_dir
):
    """The other way a pull can fail to produce anything usable: every rung
    blocked AND the fixture fallback file itself missing. Same guarantee
    must hold -- a prior good snapshot survives untouched.
    """
    good_path = cache.write_snapshot(
        [dict(VALID_RAW_RECORD)],
        raw_dir=raw_dir,
        now=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )
    good_bytes_before = good_path.read_bytes()

    def fake_run_ladder():
        raise AllRungsFailedError("all rungs blocked (simulated)")

    monkeypatch.setattr(cli, "run_ladder", fake_run_ladder)
    monkeypatch.setattr(cli, "FIXTURES_PATH", raw_dir / "does-not-exist.json")

    exit_code = cli.build(raw_dir=raw_dir, snapshot_dir=snapshot_dir)

    assert exit_code == 1
    assert good_path.read_bytes() == good_bytes_before
    assert cache.latest_good(raw_dir=raw_dir) == good_path


# --------------------------------------------------------------------------
# pull_live -- CP6's autonomous, zero-cookie-copying live refresh
# --------------------------------------------------------------------------


class _FakeMpladsClient:
    """Minimal stand-in for MpladsClient. pull_live()'s entire contract with
    a client is warm_session() / get_tiles_report_data_raw() / close(), so
    that is all this fake needs to implement -- no real HTTP, no MockTransport
    plumbing required for testing pull_live()'s own orchestration and
    atomicity, which is what these tests are actually about (the client's
    own behavior is covered in ingest/test_mplads_api.py).
    """

    def __init__(self, tiles: dict[str, dict] | None = None, *, fail_on: str | None = None):
        self._tiles = dict(tiles or {})
        self._fail_on = fail_on
        self.warmed = False
        self.closed = False

    def warm_session(self) -> None:
        self.warmed = True

    def get_tiles_report_data_raw(self, combo: str, key: str) -> dict:
        del combo  # unused by the fake; the real client is what validates it
        if key == self._fail_on:
            raise MpladsClientError(f"simulated failure for {key!r}")
        return self._tiles[key]

    def close(self) -> None:
        self.closed = True


def _tile_payloads(**overrides: dict) -> dict[str, dict]:
    """All three tiles, keyed by their tile name (not filename) -- the shape
    _FakeMpladsClient.get_tiles_report_data_raw expects to look up by `key`.
    Defaults to an empty-but-valid row list for whichever tiles the caller
    doesn't override.
    """
    defaults = {
        "Works Sanctioned": {"Works Sanctioned": "[]"},
        "Works Completed": {"Works Completed": "[]"},
        "Expenditure on Completed and On-going Works as on Date": {
            "Expenditure on Completed and On-going Works as on Date": "[]"
        },
    }
    defaults.update(overrides)
    return defaults


def test_pull_live_writes_all_three_tiles(raw_dir):
    sanctioned_payload = {"Works Sanctioned": json.dumps([{"WORK_RECOMMENDATION_DTL_ID": 1}])}
    fake_client = _FakeMpladsClient(_tile_payloads(**{"Works Sanctioned": sanctioned_payload}))

    exit_code = cli.pull_live(raw_dir=raw_dir, client=fake_client)

    assert exit_code == 0
    assert fake_client.warmed is True
    written = json.loads((raw_dir / cli.mplads_adapter.SANCTIONED_FILE).read_text())
    assert written == sanctioned_payload
    assert (raw_dir / cli.mplads_adapter.COMPLETED_FILE).exists()
    assert (raw_dir / cli.mplads_adapter.EXPENDITURE_FILE).exists()


def test_pull_live_never_closes_a_caller_supplied_client(raw_dir):
    """A client the caller built (e.g. a test, or a future caller reusing it
    for something else) is not pull_live()'s to close."""
    fake_client = _FakeMpladsClient(_tile_payloads())

    cli.pull_live(raw_dir=raw_dir, client=fake_client)

    assert fake_client.closed is False


def test_pull_live_closes_a_client_it_created_itself(monkeypatch, raw_dir):
    created = _FakeMpladsClient(_tile_payloads())
    monkeypatch.setattr(cli, "MpladsClient", lambda: created)

    exit_code = cli.pull_live(raw_dir=raw_dir)

    assert exit_code == 0
    assert created.closed is True


def test_pull_live_failure_on_any_tile_leaves_raw_dir_completely_untouched(raw_dir):
    """CP6's core safety property: a failed live pull -- including the
    network-origin tarpit every automated/cloud environment hits, per
    Checkpoints.md CP6 -- must never leave a partial set of tiles. The app
    keeps serving whatever it already had.
    """
    pre_existing = raw_dir / "some-other-file.json"
    pre_existing.write_text('{"untouched": true}', encoding="utf-8")

    fake_client = _FakeMpladsClient(_tile_payloads(), fail_on="Works Completed")

    exit_code = cli.pull_live(raw_dir=raw_dir, client=fake_client)

    assert exit_code == 1
    assert list(raw_dir.iterdir()) == [pre_existing]
    assert pre_existing.read_text(encoding="utf-8") == '{"untouched": true}'
    assert not (raw_dir / cli.mplads_adapter.SANCTIONED_FILE).exists(), (
        "the tile fetched before the failure must not be written either -- all three or none"
    )


def test_pull_live_overwrites_a_previous_pulls_stale_tiles_on_success(raw_dir):
    stale = {"Works Sanctioned": json.dumps([{"WORK_RECOMMENDATION_DTL_ID": "stale"}])}
    (raw_dir / cli.mplads_adapter.SANCTIONED_FILE).write_text(json.dumps(stale), encoding="utf-8")

    fresh = {"Works Sanctioned": json.dumps([{"WORK_RECOMMENDATION_DTL_ID": "fresh"}])}
    fake_client = _FakeMpladsClient(_tile_payloads(**{"Works Sanctioned": fresh}))

    exit_code = cli.pull_live(raw_dir=raw_dir, client=fake_client)

    assert exit_code == 0
    written = json.loads((raw_dir / cli.mplads_adapter.SANCTIONED_FILE).read_text())
    assert written == fresh


def test_pull_live_output_is_readable_by_the_real_adapter(raw_dir):
    """End-to-end within pull_live()'s own scope: what it writes has to be
    exactly what ingest/mplads_adapter.py's load_and_adapt() already knows
    how to read -- no reshaping step exists between the two.
    """
    from nidhinetra_pipeline.ingest.mplads_adapter import load_and_adapt

    sanctioned_payload = {
        "Works Sanctioned": json.dumps(
            [
                {
                    "WORK_RECOMMENDATION_DTL_ID": 1,
                    "STATE_NAME": "Bihar",
                    "CONSTITUENCY": "Test",
                    "MP_NAME": "Test MP",
                    "TENURE_START_DATE": "Jun 4, 2024 12:00:00 AM",
                    "TENURE_END_DATE": "Jun 3, 2029 11:59:59 PM",
                    "IDA_NAME": "Test Agency",
                    "ACTIVITY_NAME": "Construction of roads",
                    "SANCTION_AMOUNT": 100000.0,
                    "SANCTION_DATE": "09-Jul-2024",
                    "WORK_STAGE": "Sanction",
                },
                {"Total_Amt": 100000.0},
            ]
        )
    }
    fake_client = _FakeMpladsClient(_tile_payloads(**{"Works Sanctioned": sanctioned_payload}))

    exit_code = cli.pull_live(raw_dir=raw_dir, client=fake_client)
    assert exit_code == 0

    records, counts = load_and_adapt(raw_dir)
    assert counts["records"] == 1
    assert records[0]["work_id"] == "1"
    assert records[0]["state"] == "Bihar"
