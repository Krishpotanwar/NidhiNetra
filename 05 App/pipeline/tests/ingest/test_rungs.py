"""Tests for ingest/rungs.py -- the five-rung fallback ladder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nidhinetra_pipeline.ingest.rungs import (
    AllRungsFailedError,
    Rung,
    Rung1LiveApi,
    Rung2PlaywrightScrape,
    Rung3EmpoweredIndian,
    Rung4DataGovIn,
    Rung5SeedFixtures,
    RungBlockedError,
    default_rungs,
    run_ladder,
)


def _tile_row(work_id: int, **overrides):
    """One MPLADS-shaped Works Sanctioned row. Field names and value shapes
    match the live dashboard exactly (tab-padded ACTIVITY_NAME, DD-MMM-YYYY
    dates, the Java-style tenure timestamps) so these tests exercise the
    same parsing the real tiles do.
    """
    row = {
        "WORK_RECOMMENDATION_DTL_ID": work_id,
        "STATE_NAME": "Karnataka",
        "CONSTITUENCY": "DHARWAD",
        "MP_NAME": "Test MP",
        "IDA_NAME": "DHARWAD(DEPUTY COMMISSIONER_IDA)",
        "ACTIVITY_NAME": f"WS/\t MP620/2024-2025/{work_id}-Street lights",
        "SANCTION_AMOUNT": 100000.0,
        "SANCTION_DATE": "09-Jul-2024",
        "WORK_STAGE": "Sanction",
        "TENURE_START_DATE": "Jun 4, 2024 12:00:00 AM",
        "TENURE_END_DATE": "Jun 3, 2029 11:59:59 PM",
    }
    row.update(overrides)
    return row


def _write_tiles(raw_dir: Path, *, sanctioned=None, completed=None, expenditure=None):
    """Writes the three cached tiles Rung 1 reads. Sanctioned defaults to two
    rows so a caller that only cares about "did it return records" does not
    have to build fixtures by hand.
    """
    (raw_dir / "mplads-sanctioned.json").write_text(
        json.dumps(sanctioned if sanctioned is not None else [_tile_row(1), _tile_row(2)]),
        encoding="utf-8",
    )
    if completed is not None:
        (raw_dir / "mplads-completed.json").write_text(json.dumps(completed), encoding="utf-8")
    if expenditure is not None:
        (raw_dir / "mplads-expenditure-salvaged.json").write_text(
            json.dumps(expenditure), encoding="utf-8"
        )


def test_rung1_returns_records_from_cached_tiles(tmp_path):
    """Rung 1 went live 2026-09-04. This replaces a test that asserted it
    raised RungBlockedError -- that assertion was correct until the real
    getTilesReportData request body was captured, and is wrong now.
    """
    _write_tiles(tmp_path)
    records = Rung1LiveApi(raw_dir=tmp_path).try_fetch()
    assert records is not None
    assert len(records) == 2
    assert {r["work_id"] for r in records} == {"1", "2"}


def test_rung1_returns_none_when_tiles_absent(tmp_path):
    """A checkout without the cached tiles must fall through to the next
    rung, not crash the ladder. `data/raw/` is gitignored, so this is the
    state of every fresh clone.
    """
    assert Rung1LiveApi(raw_dir=tmp_path).try_fetch() is None


def test_rung1_returns_none_on_unparseable_tile(tmp_path):
    """The Expenditure tile is truncated mid-record by the server at
    national scale. A corrupt tile must degrade to the next rung rather
    than take the build down.
    """
    (tmp_path / "mplads-sanctioned.json").write_text("{not json", encoding="utf-8")
    assert Rung1LiveApi(raw_dir=tmp_path).try_fetch() is None


@pytest.mark.parametrize(
    "rung_cls",
    [Rung2PlaywrightScrape, Rung3EmpoweredIndian, Rung4DataGovIn, Rung5SeedFixtures],
)
def test_stub_rungs_raise_not_implemented(rung_cls):
    rung = rung_cls()
    with pytest.raises(NotImplementedError):
        rung.try_fetch()


def test_default_rungs_are_five_in_order():
    rungs = default_rungs()
    assert [r.number for r in rungs] == [1, 2, 3, 4, 5]
    assert isinstance(rungs[0], Rung1LiveApi)
    assert isinstance(rungs[4], Rung5SeedFixtures)


def test_default_rungs_returns_fresh_list_each_call():
    a = default_rungs()
    b = default_rungs()
    assert a is not b
    assert a[0] is not b[0]


def test_run_ladder_raises_all_rungs_failed_when_every_rung_declines():
    # Rung 1 is live as of 2026-09-04, so exhausting the ladder now requires
    # a Rung 1 with no cached tiles to read. The property under test is
    # unchanged and still the important one: when no rung can produce data,
    # the ladder fails loudly rather than returning empty or invented rows.
    rungs = default_rungs()
    rungs[0] = Rung1LiveApi(raw_dir=Path("/nonexistent-raw-dir"))
    with pytest.raises(AllRungsFailedError):
        run_ladder(rungs)


def test_run_ladder_returns_first_rung_that_succeeds():
    class FakeBlockedRung(Rung):
        number = 1
        name = "fake_blocked"

        def try_fetch(self):
            raise RungBlockedError("nope")

    class FakeSucceedingRung(Rung):
        number = 2
        name = "fake_succeeding"

        def try_fetch(self):
            return [{"work_id": "W1"}, {"work_id": "W2"}]

    class FakeUnreachedRung(Rung):
        number = 3
        name = "fake_unreached"
        called = False

        def try_fetch(self):
            type(self).called = True
            return [{"work_id": "should not be reached"}]

    records, rung_number = run_ladder(
        [FakeBlockedRung(), FakeSucceedingRung(), FakeUnreachedRung()]
    )

    assert rung_number == 2
    assert records == [{"work_id": "W1"}, {"work_id": "W2"}]
    assert FakeUnreachedRung.called is False


def test_run_ladder_skips_rung_that_returns_empty_list():
    class FakeEmptyRung(Rung):
        number = 1
        name = "fake_empty"

        def try_fetch(self):
            return []

    class FakeSucceedingRung(Rung):
        number = 2
        name = "fake_succeeding"

        def try_fetch(self):
            return [{"work_id": "W1"}]

    records, rung_number = run_ladder([FakeEmptyRung(), FakeSucceedingRung()])

    assert rung_number == 2
    assert records == [{"work_id": "W1"}]


def test_run_ladder_skips_rung_that_returns_none():
    class FakeNoneRung(Rung):
        number = 1
        name = "fake_none"

        def try_fetch(self):
            return None

    class FakeSucceedingRung(Rung):
        number = 2
        name = "fake_succeeding"

        def try_fetch(self):
            return [{"work_id": "W1"}]

    records, rung_number = run_ladder([FakeNoneRung(), FakeSucceedingRung()])

    assert rung_number == 2


def test_run_ladder_catches_not_implemented_and_continues():
    class FakeUnimplementedRung(Rung):
        number = 1
        name = "fake_unimplemented"

        def try_fetch(self):
            raise NotImplementedError("not built yet")

    class FakeSucceedingRung(Rung):
        number = 2
        name = "fake_succeeding"

        def try_fetch(self):
            return [{"work_id": "W1"}]

    records, rung_number = run_ladder([FakeUnimplementedRung(), FakeSucceedingRung()])

    assert rung_number == 2
