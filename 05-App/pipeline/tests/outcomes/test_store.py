"""Checkpoints CP8: outcomes must survive a snapshot rebuild, reject a bad
outcome, and reject a duplicate for the same work, date and inspector. This
file proves all three, plus the actual acceptance test Checkpoints.md names
verbatim: record an outcome, run a full build_snapshot() rebuild, outcome
still readable and still joined to its work.

Also covers two rounds of outside-voice corrections (2026-09-05, same eng
review session): round 1 -- cutoff_rank_at_time / population_n_at_time (a
second population, frozen alongside the rank) and in_control_sample (a real
comparison group for precision-at-quota), plus issue_mapping(), the frozen
enum-to-"had an issue" mapping. Round 2 -- inspector_id and denormalized
context fields (state/constituency/implementing_agency/work_category/
sanctioned_amount_inr, for orphan recovery if work_id ever turns out not to
be stable across pulls) and the UNIQUE(work_id, inspected_on, inspector_id)
+ supersedes redesign, replacing the original UNIQUE(work_id, inspected_on)
that blocked a legitimate same-day re-visit.
"""

from __future__ import annotations

import contextlib
import sqlite3
from pathlib import Path

import pytest
from nidhinetra_pipeline.build_snapshot import build_snapshot
from nidhinetra_pipeline.outcomes import alias_store, store

VALID_OUTCOME = "work_present_and_matches"


def _record(
    work_id: str,
    inspected_on: str,
    outcome: str,
    db_path: Path,
    *,
    notes: str = "",
    inspector_id: str = "AB",
    state: str = "Bihar",
    constituency: str = "Patna Sahib",
    implementing_district_authority: str | None = "Patna District Authority",
    implementing_agency: str | None = "PWD Division 7",
    work_category: str = "Road",
    sanctioned_amount_inr: float = 1_500_000.0,
    rank: int = 5,
    score: float = 70.0,
    cutoff_rank: int = 4481,
    population_n: int = 44810,
    in_control_sample: bool = False,
    supersedes: int | None = None,
) -> int:
    return store.record_outcome(
        work_id=work_id,
        inspected_on=inspected_on,
        outcome=outcome,
        notes=notes,
        inspector_id=inspector_id,
        state=state,
        constituency=constituency,
        implementing_district_authority=implementing_district_authority,
        implementing_agency=implementing_agency,
        work_category=work_category,
        sanctioned_amount_inr=sanctioned_amount_inr,
        inspection_rank_at_time=rank,
        risk_score_at_time=score,
        cutoff_rank_at_time=cutoff_rank,
        population_n_at_time=population_n,
        in_control_sample=in_control_sample,
        supersedes=supersedes,
        db_path=db_path,
    )


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "outcomes" / "outcomes.db"
    store.init_db(db_path=path)
    return path


def test_init_db_creates_parent_dir_and_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "outcomes.db"
    assert not path.parent.exists()
    store.init_db(db_path=path)
    assert path.exists()
    # Calling it again on an existing DB must not raise or wipe anything.
    _record("W1", "2026-09-05", VALID_OUTCOME, path, rank=340)
    store.init_db(db_path=path)
    assert len(store.list_all_outcomes(db_path=path)) == 1


def test_record_and_read_back_round_trips_every_field(db_path: Path) -> None:
    _record(
        "W123",
        "2026-09-05",
        "work_not_found_at_site",
        db_path,
        notes="Site was an empty plot, neighbours confirmed no construction ever happened.",
        inspector_id="RK",
        state="Uttar Pradesh",
        constituency="Lucknow",
        implementing_district_authority="Lucknow District Authority",
        implementing_agency=None,
        work_category="Drinking Water",
        sanctioned_amount_inr=250_000.0,
        rank=42,
        score=88.0,
        cutoff_rank=4481,
        population_n=44810,
        in_control_sample=False,
    )
    rows = store.get_outcomes_for_work("W123", db_path=db_path)
    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row["outcome_id"], int)
    assert row["work_id"] == "W123"
    assert row["inspected_on"] == "2026-09-05"
    assert row["outcome"] == "work_not_found_at_site"
    assert row["notes"].startswith("Site was an empty plot")
    assert row["inspector_id"] == "RK"
    assert row["state"] == "Uttar Pradesh"
    assert row["constituency"] == "Lucknow"
    assert row["implementing_agency"] is None
    assert row["implementing_district_authority"] == "Lucknow District Authority"
    assert row["context_version"] == 2
    assert row["work_category"] == "Drinking Water"
    assert row["sanctioned_amount_inr"] == 250_000.0
    assert row["inspection_rank_at_time"] == 42
    assert row["risk_score_at_time"] == 88.0
    assert row["cutoff_rank_at_time"] == 4481
    assert row["population_n_at_time"] == 44810
    assert row["in_control_sample"] is False
    assert row["supersedes"] is None


def test_in_control_sample_round_trips_as_a_real_bool_not_an_int(db_path: Path) -> None:
    _record("W1", "2026-09-05", VALID_OUTCOME, db_path, in_control_sample=True)
    row = store.get_outcomes_for_work("W1", db_path=db_path)[0]
    assert row["in_control_sample"] is True
    assert type(row["in_control_sample"]) is bool


def test_invalid_outcome_enum_rejected_before_touching_the_database(db_path: Path) -> None:
    with pytest.raises(store.UnknownOutcomeEnumError):
        _record("W1", "2026-09-05", "fraud", db_path)  # excluded verdict, not an observable fact
    assert store.list_all_outcomes(db_path=db_path) == []


def test_same_inspector_duplicate_work_and_date_is_rejected(db_path: Path) -> None:
    _record("W1", "2026-09-05", VALID_OUTCOME, db_path, inspector_id="AB", rank=5)
    with pytest.raises(store.DuplicateOutcomeError):
        _record(
            "W1", "2026-09-05", "documentation_incomplete", db_path,
            inspector_id="AB", notes="second attempt",
        )
    # The rejected duplicate must not have overwritten the original.
    rows = store.get_outcomes_for_work("W1", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["outcome"] == VALID_OUTCOME


def test_different_inspector_same_work_and_date_is_not_a_duplicate(db_path: Path) -> None:
    """Outside-voice correction: a real case the old UNIQUE(work_id,
    inspected_on) blocked -- agency unresponsive in the morning, a
    different inspector gets access and completes a real inspection that
    same afternoon.
    """
    _record("W1", "2026-09-05", "agency_unresponsive", db_path, inspector_id="AB")
    _record(
        "W1", "2026-09-05", "work_present_and_matches", db_path,
        inspector_id="RK", notes="Got access in the afternoon, matches record.",
    )
    rows = store.get_outcomes_for_work("W1", db_path=db_path)
    assert len(rows) == 2
    assert {r["inspector_id"] for r in rows} == {"AB", "RK"}


def test_same_work_different_date_is_not_a_duplicate(db_path: Path) -> None:
    _record("W1", "2026-09-05", VALID_OUTCOME, db_path)
    _record("W1", "2026-10-01", "work_present_but_differs", db_path, notes="follow-up visit")
    assert len(store.get_outcomes_for_work("W1", db_path=db_path)) == 2


def test_supersedes_records_an_explicit_amendment(db_path: Path) -> None:
    """Outside-voice correction: CP8's own wording allows 'rejected or
    explicitly versioned'. supersedes is the versioned path -- a genuine
    correction to an earlier entry, not a duplicate.
    """
    original_id = _record(
        "W1", "2026-09-05", "documentation_incomplete", db_path, inspector_id="AB",
    )
    amended_id = _record(
        "W1", "2026-09-06", VALID_OUTCOME, db_path,
        inspector_id="AB", notes="Documentation located, amending yesterday's entry.",
        supersedes=original_id,
    )
    rows = store.get_outcomes_for_work("W1", db_path=db_path)
    assert len(rows) == 2
    amended = next(r for r in rows if r["outcome_id"] == amended_id)
    assert amended["supersedes"] == original_id


def test_outcome_survives_a_full_snapshot_rebuild(tmp_path: Path, db_path: Path) -> None:
    """The exact acceptance test Checkpoints.md CP8 names: record an
    outcome, run a full rebuild, outcome still readable and still joined
    to its work. build_snapshot() must never import or touch this module.
    """
    _record("W1", "2026-09-05", VALID_OUTCOME, db_path, rank=1, score=95.0)

    snapshot_dir = tmp_path / "snapshot"
    empty_raw_dir = tmp_path / "raw"
    empty_raw_dir.mkdir()
    # No cached ladder snapshot in empty_raw_dir, so build_snapshot() falls
    # back to the CP0 fixtures -- proving this is a real, independent
    # rebuild, not a no-op.
    build_snapshot(snapshot_dir=snapshot_dir, raw_dir=empty_raw_dir)

    rows = store.get_outcomes_for_work("W1", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["outcome"] == VALID_OUTCOME


def test_list_all_outcomes_returns_every_row_for_precision_at_quota(db_path: Path) -> None:
    _record("W1", "2026-09-05", VALID_OUTCOME, db_path, rank=10)
    _record("W2", "2026-09-05", "work_not_found_at_site", db_path, rank=9000)
    all_rows = store.list_all_outcomes(db_path=db_path)
    assert {r["work_id"] for r in all_rows} == {"W1", "W2"}


class TestIssueMapping:
    """Outside-voice correction: the enum has 6 values, precision-at-quota
    needs a binary "had an issue" -- issue_mapping() is the frozen answer,
    read from the schema, never chosen after seeing real results.
    """

    def test_covers_every_enum_value_with_no_extras(self) -> None:
        mapping = store.issue_mapping()
        assert set(mapping.keys()) == store._valid_outcomes()

    def test_matches_documented_values(self) -> None:
        mapping = store.issue_mapping()
        assert mapping["work_present_and_matches"] is False
        assert mapping["work_present_but_differs"] is True
        assert mapping["work_not_found_at_site"] is True
        assert mapping["documentation_incomplete"] is True
        assert mapping["duplicate_of_another_work"] is True
        # Inconclusive: no inspection of the WORK actually happened, so it
        # must not count toward the denominator at all -- None, not False.
        assert mapping["agency_unresponsive"] is None

    def test_no_underscore_metadata_keys_leak_into_the_mapping(self) -> None:
        assert all(not k.startswith("_") for k in store.issue_mapping())


_PRE_F01_TABLE = """
    CREATE TABLE inspection_outcomes (
        outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_id TEXT NOT NULL,
        inspected_on TEXT NOT NULL,
        outcome TEXT NOT NULL,
        notes TEXT NOT NULL,
        inspector_id TEXT NOT NULL,
        state TEXT NOT NULL,
        constituency TEXT NOT NULL,
        implementing_agency TEXT,
        work_category TEXT NOT NULL,
        sanctioned_amount_inr REAL NOT NULL,
        inspection_rank_at_time INTEGER NOT NULL,
        risk_score_at_time REAL NOT NULL,
        cutoff_rank_at_time INTEGER NOT NULL,
        population_n_at_time INTEGER NOT NULL,
        in_control_sample INTEGER NOT NULL,
        supersedes INTEGER,
        UNIQUE(work_id, inspected_on, inspector_id),
        FOREIGN KEY (supersedes) REFERENCES inspection_outcomes(outcome_id)
    )
"""


def test_a_pre_f01_database_is_migrated_without_reinterpreting_old_rows(tmp_path: Path) -> None:
    """F-01: rows stored before the split hold IDA_NAME in implementing_agency.
    The migration adds columns only; old rows keep their bytes and read back
    under the field that matches their meaning; the R-06 alias tables sharing
    the same SQLite file are untouched.
    """
    path = tmp_path / "outcomes.db"
    with contextlib.closing(sqlite3.connect(path)) as connection:
        connection.execute(_PRE_F01_TABLE)
        connection.execute(
            "INSERT INTO inspection_outcomes (work_id, inspected_on, outcome, notes, "
            "inspector_id, state, constituency, implementing_agency, work_category, "
            "sanctioned_amount_inr, inspection_rank_at_time, risk_score_at_time, "
            "cutoff_rank_at_time, population_n_at_time, in_control_sample, supersedes) "
            "VALUES ('W-OLD', '2026-09-05', 'work_present_and_matches', '', 'AB', "
            "'Karnataka', 'DHARWAD', 'DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)', 'Road', "
            "100.0, 3, 50.0, 1, 5, 0, NULL)"
        )
        connection.commit()
    alias_store.upsert_candidates(
        [
            {
                "entity_type": "vendor",
                "proposed_canonical_id": "v1",
                "alias_label": "ALPHA",
                "reason": "identifier_has_multiple_labels",
                "evidence_work_ids": ["W-OLD"],
            }
        ],
        db_path=path,
    )
    (candidate,), _total = alias_store.list_candidates(db_path=path)
    review_id = alias_store.record_review(
        candidate["candidate_id"], "confirmed_merge", "RK", db_path=path
    )

    store.init_db(db_path=path)
    store.init_db(db_path=path)  # idempotent

    (old,) = store.get_outcomes_for_work("W-OLD", db_path=path)
    assert old["context_version"] == 1
    assert old["implementing_district_authority"] == "DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)"
    assert old["implementing_agency"] is None
    with contextlib.closing(sqlite3.connect(path)) as connection:
        stored = connection.execute(
            "SELECT implementing_agency, implementing_district_authority "
            "FROM inspection_outcomes WHERE work_id = 'W-OLD'"
        ).fetchone()
    assert stored == ("DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)", None)

    rows, total = alias_store.list_candidates(db_path=path)
    assert total == 1
    assert rows[0]["candidate_id"] == candidate["candidate_id"]
    history = alias_store.get_review_history(candidate["candidate_id"], db_path=path)
    assert [review["review_id"] for review in history] == [review_id]

    _record(
        "W-NEW",
        "2026-09-06",
        VALID_OUTCOME,
        path,
        implementing_district_authority="DHARWAD IDA",
        implementing_agency="KRIDL DHARWAD",
    )
    (new,) = store.get_outcomes_for_work("W-NEW", db_path=path)
    assert new["context_version"] == 2
    assert new["implementing_district_authority"] == "DHARWAD IDA"
    assert new["implementing_agency"] == "KRIDL DHARWAD"
