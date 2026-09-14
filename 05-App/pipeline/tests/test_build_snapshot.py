"""Regression coverage for build_snapshot.py.

There was no test file for this module at all until 2026-09-02 -- that gap
is exactly how the empty-input crash below shipped silently in Wave 2.
Every other module in this codebase (ingest, normalize, risk, graph) had
real tests from the moment it was written; this one didn't, because it
was written to unblock A4's API against the CP0 fixtures, which are never
empty, so the empty-input path was never exercised until the CP5/CP6
zero-results checkpoint forced it.

WORKS_FIXTURE_PATH is a module-level constant, not a build_snapshot()
parameter, so these tests monkeypatch it to point at temp fixture files
rather than touching the real contracts/fixtures/works.fixture.json.
snapshot_dir IS parameterized, so every test writes to tmp_path, never to
the real data/snapshot/.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from nidhinetra_pipeline import build_snapshot as bs

REAL_FIXTURE = Path(__file__).parents[2] / "contracts" / "fixtures" / "works.fixture.json"


@pytest.fixture
def fixture_path(tmp_path, monkeypatch, request):
    """Points WORKS_FIXTURE_PATH at a temp file with the given content,
    for the duration of one test, then restores the real constant."""
    content = request.param
    p = tmp_path / "works.fixture.json"
    p.write_text(json.dumps(content), encoding="utf-8")
    monkeypatch.setattr(bs, "WORKS_FIXTURE_PATH", p)
    return p


class TestSchemaColumns:
    def test_normalized_columns_match_the_frozen_schema(self):
        schema = json.loads((bs.CONTRACTS_DIR / "normalized_record.schema.json").read_text())
        assert bs._NORMALIZED_COLUMNS == list(schema["properties"].keys())

    def test_scored_columns_match_the_frozen_schema(self):
        schema = json.loads((bs.CONTRACTS_DIR / "risk_scored_record.schema.json").read_text())
        assert bs._SCORED_COLUMNS == list(schema["properties"].keys())


class TestBuildSnapshotEmptyInput:
    """The regression this file exists to prevent: pd.DataFrame([]) with no
    explicit columns= has zero columns, so scored_df['flags'] raised
    KeyError the moment the real 20-row CP0 fixture was swapped for an
    empty one and the API cold-booted against it. Confirmed live 2026-09-02
    before this fix landed -- this is not a hypothetical edge case."""

    @pytest.mark.parametrize("fixture_path", [[]], indirect=True)
    def test_zero_row_fixture_does_not_raise(self, fixture_path, tmp_path):
        # The bug's exact failure mode: this call raised KeyError('flags')
        # before the fix. It must not raise at all now.
        manifest = bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")
        assert manifest["row_count"] == 0

    @pytest.mark.parametrize("fixture_path", [[]], indirect=True)
    def test_zero_row_fixture_writes_correctly_shaped_parquet(self, fixture_path, tmp_path):
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")

        works_df = pd.read_parquet(tmp_path / "works.parquet")
        scored_df = pd.read_parquet(tmp_path / "scored.parquet")

        assert len(works_df) == 0
        assert len(scored_df) == 0
        # The actual assertion the bug violated: these columns must exist
        # and be selectable even with zero rows.
        assert list(works_df.columns) == bs._NORMALIZED_COLUMNS
        assert list(scored_df.columns) == bs._SCORED_COLUMNS
        for col in bs._JSON_ENCODED_SCORED_COLUMNS:
            assert col in scored_df.columns

    @pytest.mark.parametrize("fixture_path", [[]], indirect=True)
    def test_zero_row_fixture_produces_empty_graph_not_a_crash(self, fixture_path, tmp_path):
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")
        graph = json.loads((tmp_path / "graph.json").read_text())
        assert graph == {"nodes": [], "edges": []}

    @pytest.mark.parametrize("fixture_path", [[]], indirect=True)
    def test_zero_row_fixture_produces_an_empty_alias_queue(self, fixture_path, tmp_path):
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")

        aliases = json.loads((tmp_path / "alias_candidates.json").read_text())
        assert aliases == []

    @pytest.mark.parametrize("fixture_path", [[]], indirect=True)
    def test_zero_row_fixture_manifest_is_honest(self, fixture_path, tmp_path):
        manifest = bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")
        assert manifest["source"] == bs.SOURCE_LABEL
        assert manifest["row_count"] == 0
        # data_as_of must still be a real timestamp, not null/omitted, even
        # with nothing in the snapshot -- the frontend's provenance banner
        # depends on this field always being present.
        assert manifest["data_as_of"]


class TestBuildSnapshotRealFixture:
    """The non-empty path this module was originally written and tested
    against (informally, via the API's own integration tests) -- included
    here too so this file is a complete, self-contained regression suite
    for build_snapshot.py rather than only covering the new edge case."""

    def test_real_fixture_builds_without_error(self, tmp_path):
        manifest = bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")
        assert manifest["row_count"] == 20

    def test_build_writes_alias_candidates_from_the_same_normalized_records(
        self, tmp_path, monkeypatch
    ):
        fixture = json.loads(REAL_FIXTURE.read_text(encoding="utf-8"))
        fixture[0]["vendor_id"] = "SYNTH-AMBIGUOUS"
        fixture[0]["vendor_name"] = "Alpha Works"
        fixture[1]["vendor_id"] = "SYNTH-AMBIGUOUS"
        fixture[1]["vendor_name"] = "Beta Works"
        source = tmp_path / "ambiguous-works.json"
        source.write_text(json.dumps(fixture), encoding="utf-8")
        monkeypatch.setattr(bs, "WORKS_FIXTURE_PATH", source)

        snapshot_dir = tmp_path / "snapshot"
        bs.build_snapshot(snapshot_dir=snapshot_dir, raw_dir=tmp_path / "raw")

        aliases = json.loads((snapshot_dir / "alias_candidates.json").read_text())
        assert {
            (candidate["proposed_canonical_id"], candidate["alias_label"]) for candidate in aliases
        } >= {
            ("SYNTH-AMBIGUOUS", "Alpha Works"),
            ("SYNTH-AMBIGUOUS", "Beta Works"),
        }

    def test_real_fixture_output_validates_against_both_schemas(self, tmp_path):
        import jsonschema

        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")

        works_df = pd.read_parquet(tmp_path / "works.parquet")
        scored_df = pd.read_parquet(tmp_path / "scored.parquet")

        normalized_schema = json.loads(
            (bs.CONTRACTS_DIR / "normalized_record.schema.json").read_text()
        )
        scored_schema = json.loads(
            (bs.CONTRACTS_DIR / "risk_scored_record.schema.json").read_text()
        )
        norm_validator = jsonschema.Draft7Validator(normalized_schema)
        scored_validator = jsonschema.Draft7Validator(scored_schema)

        for record in works_df.to_dict(orient="records"):
            errors = list(norm_validator.iter_errors(record))
            assert not errors, errors

        for record in scored_df.to_dict(orient="records"):
            decoded = dict(record)
            for col in bs._JSON_ENCODED_SCORED_COLUMNS:
                decoded[col] = json.loads(decoded[col])
            errors = list(scored_validator.iter_errors(decoded))
            assert not errors, errors


class TestBuildSnapshotRefusesADowngrade:
    """Outside-voice finding, 2026-09-05 eng review: data/raw/ is gitignored
    (single-disk), data/snapshot/*.parquet is committed, so a fresh clone or
    a second machine boots correctly on the real snapshot -- right up until
    someone clicks Refresh. POST /api/refresh calls build_snapshot()
    unconditionally, and _load_raw_records() falls back to the 20-row CP0
    fixture (rung 5) the moment data/raw/ has nothing cached. Without this
    guard, that one click silently replaces 79,068 real rows with 20 demo
    rows and no error -- the exact failure mode NEXT-STEPS.md's planned
    second-person dry run (a machine that is, by design, not this one) would
    trigger.
    """

    def _seed_rung1_cache(self, raw_dir: Path) -> None:
        real_records = json.loads(REAL_FIXTURE.read_text(encoding="utf-8"))
        rung1_records = [{**r, "source_rung": 1} for r in real_records]
        from nidhinetra_pipeline.ingest import cache

        cache.write_snapshot(rung1_records, raw_dir=raw_dir)

    def test_first_ever_build_is_never_a_downgrade(self, tmp_path):
        # No manifest.json exists yet -- nothing to protect, so even the
        # worst rung (5, the fixture fallback) must succeed.
        manifest = bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "no-cache")
        assert manifest["source"] == bs.SOURCE_LABEL

    def test_falling_back_to_the_fixture_after_a_real_rung1_build_is_refused(self, tmp_path):
        raw_dir = tmp_path / "raw"
        self._seed_rung1_cache(raw_dir)
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=raw_dir)

        with pytest.raises(bs.SnapshotDowngradeError):
            bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "now-empty")

        # The refusal must be real: the good rung-1 manifest is untouched.
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        assert manifest["source"] == "mplads_live_api"

    def test_force_bypasses_the_guard(self, tmp_path):
        raw_dir = tmp_path / "raw"
        self._seed_rung1_cache(raw_dir)
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=raw_dir)

        manifest = bs.build_snapshot(
            snapshot_dir=tmp_path, raw_dir=tmp_path / "now-empty", force=True
        )
        assert manifest["source"] == bs.SOURCE_LABEL

    def test_an_upgrade_is_never_refused(self, tmp_path):
        # Build once from the fixture (rung 5), then a real rung-1 pull
        # lands. That rebuild must succeed without needing force=True.
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "no-cache-yet")

        raw_dir = tmp_path / "raw"
        self._seed_rung1_cache(raw_dir)
        manifest = bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=raw_dir)
        assert manifest["source"] == "mplads_live_api"

    def test_rebuilding_from_the_same_rung_is_never_refused(self, tmp_path):
        raw_dir = tmp_path / "raw"
        self._seed_rung1_cache(raw_dir)
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=raw_dir)
        # A second, identical rung-1 rebuild (e.g. a second live pull) is not
        # a downgrade even though it's not technically an upgrade either.
        manifest = bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=raw_dir)
        assert manifest["source"] == "mplads_live_api"

    def test_null_implementing_agency_and_vendor_round_trip_as_none_not_nan(self, tmp_path):
        """The second bug this test file exists for, distinct from the
        empty-DataFrame one: pandas' default object dtype can turn a
        Python None into the float NaN on a parquet round trip. NaN passes
        pandas' own truthiness checks fine, which is exactly how this
        stayed invisible -- it only shows up once something checks the
        value's actual type, like jsonschema (which is what caught it) or
        json.dumps (which emits the non-standard `NaN` token for it,
        invalid JSON). The real CP0 fixture has rows with a null
        vendor_name (MPLADS-FX seed data, 'some works have no vendor yet')
        so this is exercised against genuine data, not a synthetic case.
        """
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")
        works_df = pd.read_parquet(tmp_path / "works.parquet")

        null_vendor_rows = works_df[works_df["vendor_name"].isna()]
        assert len(null_vendor_rows) > 0, (
            "test fixture no longer has a null-vendor row -- this test needs "
            "a genuine null to be meaningful, update the fixture assumption"
        )

        for record in works_df.to_dict(orient="records"):
            for col in bs._NULLABLE_STRING_COLUMNS:
                value = record[col]
                if value is None:
                    continue
                # The actual regression: this must never be pandas.NA or
                # float('nan') -- either one is a null-ish sentinel that is
                # NOT the same thing as Python None to jsonschema or to
                # json.dumps, which is the whole point of the assertion.
                assert isinstance(value, str), (
                    f"{col}={value!r} ({type(value).__name__}) is neither a "
                    "real string nor None -- likely NaN or pd.NA leaking "
                    "through the parquet round trip"
                )

    def test_explicit_now_pins_the_manifest_timestamp(self, tmp_path):
        fixed = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        manifest = bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw", now=fixed)
        assert manifest["generated_at"] == "2026-01-01T12:00:00Z"
        assert manifest["data_as_of"] == "2026-01-01T12:00:00Z"

    def test_two_builds_with_the_same_pinned_now_are_deterministic(self, tmp_path):
        fixed = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        m1 = bs.build_snapshot(snapshot_dir=tmp_path / "a", raw_dir=tmp_path / "raw", now=fixed)
        m2 = bs.build_snapshot(snapshot_dir=tmp_path / "b", raw_dir=tmp_path / "raw", now=fixed)
        assert m1 == m2
        works_a = pd.read_parquet(tmp_path / "a" / "works.parquet")
        works_b = pd.read_parquet(tmp_path / "b" / "works.parquet")
        pd.testing.assert_frame_equal(works_a, works_b)


class TestBuildSnapshotAtomicity:
    def test_alias_candidate_stage_failure_leaves_the_whole_snapshot_unchanged(
        self, tmp_path, monkeypatch
    ):
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")
        artifact_names = (
            "works.parquet",
            "scored.parquet",
            "graph.json",
            "alias_candidates.json",
            "manifest.json",
        )
        before = {name: (tmp_path / name).read_bytes() for name in artifact_names}

        real_stage_json = bs._stage_json

        def _fail_on_aliases(obj, final_path):
            if final_path.name == "alias_candidates.json":
                raise RuntimeError("simulated alias candidate staging failure")
            return real_stage_json(obj, final_path)

        monkeypatch.setattr(bs, "_stage_json", _fail_on_aliases)

        with pytest.raises(RuntimeError, match="alias candidate"):
            bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")

        assert {name: (tmp_path / name).read_bytes() for name in artifact_names} == before
        assert list(tmp_path.glob(".*tmp")) == []

    def test_a_failed_stage_never_leaves_a_partial_snapshot_in_place(self, tmp_path, monkeypatch):
        """Mirrors ingest/cache.py's atomic-swap test: build a good snapshot
        first, then force graph.json's STAGE step (not the rename) to fail
        on the second build. works.parquet and scored.parquet stage
        successfully before graph.json does (targets list order in
        build_snapshot()), which is exactly the case the 2026-09-02
        group-atomicity fix exists for: under the old one-file-at-a-time
        version, those two would already have been renamed into place by
        the time graph.json's failure was discovered, leaving a torn
        snapshot. With staging batched before any commit, none of the four
        real files may change at all."""
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")
        good_works = (tmp_path / "works.parquet").read_bytes()
        good_scored = (tmp_path / "scored.parquet").read_bytes()
        good_graph = (tmp_path / "graph.json").read_text()
        good_manifest = (tmp_path / "manifest.json").read_text()

        real_stage_json = bs._stage_json
        call_count = {"n": 0}

        def _fail_on_graph(obj, final_path):
            call_count["n"] += 1
            if final_path.name == "graph.json":
                raise RuntimeError("simulated staging failure")
            return real_stage_json(obj, final_path)

        monkeypatch.setattr(bs, "_stage_json", _fail_on_graph)

        with pytest.raises(RuntimeError):
            bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")

        # The real assertion: works.parquet and scored.parquet (staged
        # before the graph.json failure) were never committed either, even
        # though their own staging succeeded.
        assert (tmp_path / "works.parquet").read_bytes() == good_works
        assert (tmp_path / "scored.parquet").read_bytes() == good_scored
        assert (tmp_path / "graph.json").read_text() == good_graph
        assert (tmp_path / "manifest.json").read_text() == good_manifest

        # And no stray .tmp files were left behind from the two artifacts
        # that staged successfully before the batch was aborted.
        leftover_tmp = list(tmp_path.glob(".*tmp"))
        assert leftover_tmp == [], leftover_tmp

    def test_commit_failure_partway_through_the_batch_is_a_documented_residual_risk(
        self, tmp_path, monkeypatch
    ):
        """The honest limit of this fix, made explicit as a test rather than
        left only as a comment: commits are still four separate renames, not
        one. If the SECOND commit raises, the first has already landed.
        This is the "residual window" the module docstring and
        build_snapshot()'s own comment both name directly -- true
        directory-level atomicity would remove it, and is out of scope for
        this fix."""
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")

        real_commit = bs._commit_staged
        call_count = {"n": 0}

        def _fail_on_second_commit(tmp_path_arg, final_path):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("simulated commit failure")
            return real_commit(tmp_path_arg, final_path)

        monkeypatch.setattr(bs, "_commit_staged", _fail_on_second_commit)

        with pytest.raises(RuntimeError):
            bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")

        # The first commit (works.parquet, per targets' order) DID land --
        # this is the documented gap, not a hidden one.
        assert call_count["n"] == 2


class TestBuildSnapshotSourceSelection:
    """build_snapshot() prefers the cached acquisition-ladder snapshot over
    the CP0 fixture, and reports provenance read off the data rather than
    hardcoded. Before 2026-09-04 it read the fixture unconditionally with
    rung 5 baked into both normalize_records() and manifest.source, so a
    successful rung-1 pull of 79,068 real records had no effect on what the
    API served -- and the manifest still said "cp0_fixtures" while the
    operator believed the pull had landed.
    """

    @staticmethod
    def _cache(raw_dir: Path, records: list[dict], stamp: str = "20260904T110000Z") -> None:
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{stamp}.json").write_text(json.dumps(records), encoding="utf-8")

    @staticmethod
    def _record(work_id: str, source_rung: int) -> dict:
        return {
            "work_id": work_id,
            "state": "Karnataka",
            "constituency": "DHARWAD",
            "mp_name": "Test MP",
            "tenure": "2024-2029",
            "implementing_agency": "AGENCY",
            "vendor_id": "synthetic-vendor-id",
            "vendor_name": "VENDOR",
            "work_category": "Road",
            "sanctioned_amount_inr": 100000.0,
            "expenditure_amount_inr": 0.0,
            "sanction_date": "2024-07-09",
            "completion_status": "Sanctioned",
            "last_updated": "2026-09-04",
            "source_rung": source_rung,
        }

    def test_cached_snapshot_is_preferred_over_the_fixture(self, tmp_path):
        raw = tmp_path / "raw"
        self._cache(raw, [self._record("cached-1", 1), self._record("cached-2", 1)])

        manifest = bs.build_snapshot(snapshot_dir=tmp_path / "snap", raw_dir=raw)

        assert manifest["row_count"] == 2, "took the fixture instead of the cache"
        works = pd.read_parquet(tmp_path / "snap" / "works.parquet")
        assert set(works["work_id"]) == {"cached-1", "cached-2"}

    def test_manifest_source_names_the_rung_the_data_came_from(self, tmp_path):
        raw = tmp_path / "raw"
        self._cache(raw, [self._record("w1", 1)])
        manifest = bs.build_snapshot(snapshot_dir=tmp_path / "snap", raw_dir=raw)
        assert manifest["source"] == "mplads_live_api"

    def test_source_rung_survives_the_rebuild(self, tmp_path):
        """The cached batch is already normalized and carries its own rung.
        Re-stamping it with the fixture's rung 5 would relabel real data as
        the demo seed set, which is what the UI's provenance banner reads.
        """
        raw = tmp_path / "raw"
        self._cache(raw, [self._record("w1", 1)])
        bs.build_snapshot(snapshot_dir=tmp_path / "snap", raw_dir=raw)
        works = pd.read_parquet(tmp_path / "snap" / "works.parquet")
        assert set(works["source_rung"]) == {1}

    def test_data_as_of_reports_the_pull_time_not_the_rebuild_time(self, tmp_path):
        """The cache filename is the UTC instant that pull landed, which is a
        truer "as of" for the data than whenever a rebuild happened to run.
        The UI shows this as the data-age label.
        """
        raw = tmp_path / "raw"
        self._cache(raw, [self._record("w1", 1)], stamp="20260901T083000Z")
        rebuilt_at = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

        manifest = bs.build_snapshot(snapshot_dir=tmp_path / "snap", raw_dir=raw, now=rebuilt_at)

        assert manifest["data_as_of"] == "2026-09-01T08:30:00Z"
        assert manifest["generated_at"] == "2026-09-04T12:00:00Z"

    def test_falls_back_to_the_fixture_when_no_cache_exists(self, tmp_path):
        """A fresh clone has an empty data/raw/ (it is gitignored), so the
        fixture path has to keep working or the app cannot start at all.
        """
        manifest = bs.build_snapshot(snapshot_dir=tmp_path / "snap", raw_dir=tmp_path / "empty")
        assert manifest["source"] == "cp0_fixtures"

    def test_raw_tile_files_are_not_mistaken_for_a_cached_snapshot(self, tmp_path):
        """data/raw/ holds two different kinds of file since rung 1 went
        live: `<timestamp>.json` snapshots and `mplads-*.json` raw tile
        responses (the adapter's input). The tile names sort after any
        timestamp, so a bare *.json glob picked one as "latest" and the
        build then tried to read source_rung off raw dashboard rows.
        """
        raw = tmp_path / "raw"
        raw.mkdir()
        (raw / "mplads-sanctioned.json").write_text(
            json.dumps([{"WORK_RECOMMENDATION_DTL_ID": 1, "STATE_NAME": "Kerala"}]),
            encoding="utf-8",
        )
        manifest = bs.build_snapshot(snapshot_dir=tmp_path / "snap", raw_dir=raw)
        assert manifest["source"] == "cp0_fixtures"

    def test_a_cache_with_mixed_source_rungs_is_refused(self, tmp_path):
        """Provenance has to be statable in one number. A cache whose rows
        disagree about where they came from cannot be labelled honestly, so
        it is rejected rather than silently taking the first value.
        """
        raw = tmp_path / "raw"
        self._cache(raw, [self._record("w1", 1), self._record("w2", 5)])
        with pytest.raises(bs.SnapshotWriteError, match="inconsistent"):
            bs.build_snapshot(snapshot_dir=tmp_path / "snap", raw_dir=raw)
