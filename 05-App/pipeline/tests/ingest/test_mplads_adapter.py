"""Tests for ingest/mplads_adapter.py -- the live MPLADS tile join.

Rows here are shaped exactly like the live dashboard's: tab-padded
ACTIVITY_NAME with the `WS/ MPnnn/yyyy-yyyy/<id>-` reference prefix,
DD-MMM-YYYY dates, Java-style tenure timestamps, and the per-payment
Expenditure tile that repeats a work once per disbursement. Fabricating a
tidier shape here would test a parser that does not exist.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from nidhinetra_pipeline.ingest.mplads_adapter import (
    CATEGORY_FALLBACK,
    VALID_CATEGORIES,
    MpladsAdapterError,
    activity_of,
    adapt,
    category_for,
    load_and_adapt,
    rollup_expenditure,
)
from nidhinetra_pipeline.normalize.normalize import normalize_records

AS_OF = date(2026, 9, 4)


def sanctioned_row(work_id: int, **overrides):
    row = {
        "WORK_RECOMMENDATION_DTL_ID": work_id,
        "STATE_NAME": "Karnataka",
        "CONSTITUENCY": "DHARWAD",
        "MP_NAME": "Pralhad Venkatesh Joshi",
        "IDA_NAME": "DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)",
        "ACTIVITY_NAME": f"WS/\t MP620/2024-2025/{work_id}-Street lights",
        "SANCTION_AMOUNT": 497185.0,
        "SANCTION_DATE": "09-Jul-2024",
        "WORK_STAGE": "Sanction",
        "TENURE": "18th Lok Sabha",
        "TENURE_START_DATE": "Jun 4, 2024 12:00:00 AM",
        "TENURE_END_DATE": "Jun 3, 2029 11:59:59 PM",
    }
    row.update(overrides)
    return row


def payment_row(
    work_id: int,
    amount: float,
    vendor: str,
    status="Payment Success",
    *,
    vendor_id: int | str | None = 1,
):
    return {
        "WORK_RECOMMENDATION_DTL_ID": work_id,
        "VENDOR_NAME": vendor,
        "VENDOR_ID": vendor_id,
        "FUND_DISBURSED_AMT": amount,
        "WORK_STATUS": status,
        "EXPENDITURE_DATE": "21-Aug-2026",
    }


class TestActivityAndCategory:
    def test_prefix_is_stripped_from_sanctioned_shape(self):
        assert (
            activity_of("WS/\t MP620/2024-2025/133166-Construction of community halls")
            == "Construction of community halls"
        )

    def test_bare_activity_passes_through_for_expenditure_shape(self):
        # The Expenditure tile carries no reference prefix.
        assert activity_of("Street lights") == "Street lights"

    def test_hyphen_inside_the_year_range_does_not_end_the_match(self):
        # "2024-2025" contains a hyphen; a lazy pattern would cut here and
        # return "2025/133166-Construction ...", which is what an earlier
        # ad-hoc regex did and why every activity looked distinct.
        assert activity_of("WS/MP1/2024-2025/9-Road work") == "Road work"

    @pytest.mark.parametrize(
        "activity, expected",
        [
            # The 18,248-work line. "drainage system" inside it made a
            # Sanitation rule that ran before Road classify 23% of the
            # country's works as sanitation (caught 2026-09-04).
            (
                "Construction of roads, link roads, pathways or any other road "
                "with or without drainage system",
                "Road",
            ),
            # Genuinely sanitation: drains with no road in sight.
            ("Providing drains and gutters for public drainage", "Sanitation"),
            # Contains "roadsides" and "flood control"; is neither Road nor
            # Drinking Water.
            (
                "Construction of flood control embankments/ protection walls "
                "along riverbanks, hilltops, roadsides",
                "Community Infrastructure",
            ),
            ("Street lights", "Electricity"),
            ("Lighting of public spaces", "Electricity"),
            ("Installing tube-wells and borewells", "Drinking Water"),
            ("Purchase of ambulances (Four, three and two wheelers)", "Health"),
            ("Construction of veterinary hospitals and dispensaries", "Health"),
            ("Construction of rooms and halls in school and colleges", "School"),
            ("Purchase of books and periodicals for libraries", "School"),
            ("Construction of public toilets and bathrooms", "Sanitation"),
            ("Construction of culverts and bridges", "Road"),
            ("Construction of community centers and community halls", "Community Infrastructure"),
        ],
    )
    def test_known_activities_map_to_expected_category(self, activity, expected):
        assert category_for(activity) == expected

    def test_unknown_activity_falls_back_rather_than_raising(self):
        # A new activity string appearing upstream must not be able to take
        # the pipeline down.
        assert category_for("Purchase of something never seen before") == CATEGORY_FALLBACK

    def test_empty_activity_falls_back(self):
        assert category_for(None) == CATEGORY_FALLBACK
        assert category_for("") == CATEGORY_FALLBACK

    def test_every_category_returned_is_in_the_schema_enum(self):
        samples = [
            "Street lights",
            "Construction of roads",
            "Installing hand pumps",
            "Purchase of hospital equipment",
            "Construction of public toilets",
            "Construction of stadiums",
            "Setting up crops conservation facilities",
            "",
            None,
            "wholly unrecognisable input",
        ]
        assert {category_for(s) for s in samples} <= VALID_CATEGORIES


class TestExpenditureRollup:
    def test_settled_payments_sum_per_work(self):
        rollups = rollup_expenditure(
            [payment_row(1, 100.0, "ACME"), payment_row(1, 50.0, "ACME"), payment_row(2, 7.0, "B")]
        )
        assert rollups[1].total_inr == 150.0
        assert rollups[2].total_inr == 7.0

    def test_in_progress_payments_contribute_vendor_but_not_amount(self):
        # Money committed but not disbursed is not money spent. Counting it
        # would suppress the stalled_work flag on exactly the works whose
        # payments are stuck, which is the case that detector exists for.
        rollups = rollup_expenditure([payment_row(1, 999.0, "ACME", status="Payment In-Progress")])
        assert rollups[1].total_inr == 0.0
        assert rollups[1].vendor() == "ACME"

    def test_modal_vendor_wins_when_a_work_has_several(self):
        rollups = rollup_expenditure(
            [payment_row(1, 1.0, "ACME"), payment_row(1, 1.0, "ACME"), payment_row(1, 1.0, "OTHER")]
        )
        assert rollups[1].vendor() == "ACME"

    def test_vendor_tie_breaks_alphabetically_for_determinism(self):
        # Two vendors, one event each. Without a deterministic tie-break the
        # chosen vendor would depend on dict ordering and the same input
        # could produce two different snapshots.
        rollups = rollup_expenditure([payment_row(1, 1.0, "ZEBRA"), payment_row(1, 1.0, "ALPHA")])
        assert rollups[1].vendor() == "ALPHA"

    def test_vendor_id_is_selected_from_the_same_observed_pair_as_the_modal_name(self):
        """Selecting the name and ID independently can fabricate an identity.

        Both IDs and both names tie here. The existing name rule chooses
        ALPHA alphabetically, so its ID must come from the ALPHA event, not
        from the independently-smallest ID on the ZEBRA event.
        """
        rollups = rollup_expenditure(
            [
                payment_row(1, 1.0, "ZEBRA", vendor_id=1),
                payment_row(1, 1.0, "ALPHA", vendor_id=2),
            ]
        )

        assert rollups[1].vendor() == "ALPHA"
        assert rollups[1].vendor_id() == "2"

    def test_vendor_id_is_null_when_the_modal_name_has_no_source_identifier(self):
        rollups = rollup_expenditure([payment_row(1, 1.0, "UNIDENTIFIED VENDOR", vendor_id=None)])

        assert rollups[1].vendor() == "UNIDENTIFIED VENDOR"
        assert rollups[1].vendor_id() is None

    def test_rows_without_a_work_id_are_skipped(self):
        rollups = rollup_expenditure([{"VENDOR_NAME": "X", "FUND_DISBURSED_AMT": 5.0}])
        assert rollups == {}


class TestAdapt:
    def test_joins_all_three_tiles_onto_one_record(self):
        records = adapt(
            [sanctioned_row(1)],
            [],
            [payment_row(1, 250.0, "SHRINIVAS CONTRACTOR")],
            as_of=AS_OF,
        )
        assert len(records) == 1
        r = records[0]
        assert r["work_id"] == "1"
        assert r["vendor_name"] == "SHRINIVAS CONTRACTOR"
        assert r["vendor_id"] == "1"
        assert r["expenditure_amount_inr"] == 250.0
        assert r["sanctioned_amount_inr"] == 497185.0

    def test_work_id_is_stringified(self):
        # Source gives an int; the schema wants a string with minLength 1.
        assert adapt([sanctioned_row(133166)], [], [], as_of=AS_OF)[0]["work_id"] == "133166"

    def test_sanction_date_is_converted_to_iso(self):
        assert adapt([sanctioned_row(1)], [], [], as_of=AS_OF)[0]["sanction_date"] == "2024-07-09"

    def test_unparseable_sanction_date_becomes_null_not_invented(self):
        rows = [sanctioned_row(1, SANCTION_DATE="NA")]
        assert adapt(rows, [], [], as_of=AS_OF)[0]["sanction_date"] is None

    def test_tenure_is_the_year_range_not_the_sabha_label(self):
        # The schema constrains tenure to ^[0-9]{4}-[0-9]{4}$, so the
        # source's "18th Lok Sabha" cannot be passed through.
        assert adapt([sanctioned_row(1)], [], [], as_of=AS_OF)[0]["tenure"] == "2024-2029"

    def test_tab_padding_is_stripped_from_source_strings(self):
        rows = [sanctioned_row(1, IDA_NAME="DHARWAD\t\t(DEPUTY   COMMISSIONER)")]
        assert adapt(rows, [], [], as_of=AS_OF)[0]["implementing_agency"] == (
            "DHARWAD (DEPUTY COMMISSIONER)"
        )

    @pytest.mark.parametrize(
        "stage, expected",
        [
            ("Sanction", "Sanctioned"),
            ("Vendor Identification", "Sanctioned"),
            ("Time Estimation", "Sanctioned"),
            ("Physical Inspection", "In Progress"),
            ("Work partially Completed", "In Progress"),
            # An unrecognised future stage is in progress by elimination:
            # sanctioned, not listed complete, not in a known pre-start stage.
            ("Some New Stage MoSPI Adds Later", "In Progress"),
        ],
    )
    def test_completion_status_from_work_stage(self, stage, expected):
        rows = [sanctioned_row(1, WORK_STAGE=stage)]
        assert adapt(rows, [], [], as_of=AS_OF)[0]["completion_status"] == expected

    def test_completed_tile_overrides_work_stage(self):
        # The live data lists 34,258 works in the Completed tile while
        # WORK_STAGE marks only 4,207 "Work Completed". Trusting WORK_STAGE
        # alone would push 30,051 finished works into the inspection queue.
        rows = [sanctioned_row(1, WORK_STAGE="Physical Inspection")]
        completed = [{"WORK_RECOMMENDATION_DTL_ID": 1}]
        assert adapt(rows, completed, [], as_of=AS_OF)[0]["completion_status"] == "Completed"

    def test_work_with_no_expenditure_records_reports_zero_not_null(self):
        # Zero is the honest value for a sanctioned work with no payments,
        # and it is what makes stalled_work able to fire. The schema also
        # requires a number here, not null.
        r = adapt([sanctioned_row(1)], [], [], as_of=AS_OF)[0]
        assert r["expenditure_amount_inr"] == 0.0
        assert r["vendor_name"] is None
        assert r["vendor_id"] is None

    def test_negative_disbursement_is_floored_at_zero(self):
        # Correction entries appear upstream as negative amounts; the schema
        # sets minimum 0, so one negative row would fail the whole batch.
        rows = [sanctioned_row(1)]
        recs = adapt(rows, [], [payment_row(1, -500.0, "ACME")], as_of=AS_OF)
        assert recs[0]["expenditure_amount_inr"] == 0.0

    def test_rows_without_a_work_id_are_dropped(self):
        rows = [sanctioned_row(1), {"STATE_NAME": "Kerala"}]
        assert len(adapt(rows, [], [], as_of=AS_OF)) == 1

    def test_last_updated_is_the_latest_payment_date(self):
        """The most recent thing known to have happened to the work. The
        first version of this adapter used the snapshot date for every row,
        which made every record equally fresh -- the Days stale column read
        0 on all 79,068 and stalled_work's no-update fallback had nothing to
        measure.
        """
        recs = adapt(
            [sanctioned_row(1)],
            [],
            [payment_row(1, 10.0, "ACME"), payment_row(1, 20.0, "ACME")],
            as_of=AS_OF,
        )
        # payment_row's EXPENDITURE_DATE is 21-Aug-2026.
        assert recs[0]["last_updated"] == "2026-08-21"

    def test_last_updated_takes_the_most_recent_of_several_payments(self):
        recs = adapt(
            [sanctioned_row(1)],
            [],
            [
                {**payment_row(1, 10.0, "ACME"), "EXPENDITURE_DATE": "01-Feb-2025"},
                {**payment_row(1, 10.0, "ACME"), "EXPENDITURE_DATE": "14-Nov-2025"},
                {**payment_row(1, 10.0, "ACME"), "EXPENDITURE_DATE": "03-Jun-2025"},
            ],
            as_of=AS_OF,
        )
        assert recs[0]["last_updated"] == "2025-11-14"

    def test_in_progress_payment_still_counts_as_activity(self):
        # It contributes no money (see the rollup tests) but a disbursement
        # that has been initiated is something happening to the work.
        recs = adapt(
            [sanctioned_row(1)],
            [],
            [payment_row(1, 500.0, "ACME", status="Payment In-Progress")],
            as_of=AS_OF,
        )
        assert recs[0]["last_updated"] == "2026-08-21"
        assert recs[0]["expenditure_amount_inr"] == 0.0

    def test_last_updated_falls_back_to_sanction_date_when_no_payments(self):
        """A work with no payments has had nothing happen since it was
        sanctioned, and saying so is what lets stalled_work measure the gap.
        """
        recs = adapt([sanctioned_row(1)], [], [], as_of=AS_OF)
        assert recs[0]["last_updated"] == "2024-07-09"

    def test_last_updated_falls_back_to_the_snapshot_date_as_a_last_resort(self):
        # No payments and no parseable sanction date: the schema requires a
        # date here, so the snapshot date is the only honest remaining answer.
        recs = adapt([sanctioned_row(1, SANCTION_DATE="NA")], [], [], as_of=AS_OF)
        assert recs[0]["last_updated"] == "2026-09-04"

    def test_output_validates_against_the_frozen_schema(self):
        records = adapt(
            [
                sanctioned_row(1),
                sanctioned_row(2, WORK_STAGE="Physical Inspection", SANCTION_DATE="NA"),
                sanctioned_row(3, IDA_NAME=None),
            ],
            [{"WORK_RECOMMENDATION_DTL_ID": 3}],
            [payment_row(1, 100.0, "ACME")],
            as_of=AS_OF,
        )
        # normalize_records raises on the first schema violation, so this
        # passing means every emitted record is contract-valid.
        out = normalize_records(records, source_rung=1)
        assert len(out) == 3
        assert all(r["source_rung"] == 1 for r in out)


class TestLoadAndAdapt:
    def test_missing_sanctioned_tile_raises_with_a_recovery_hint(self, tmp_path):
        with pytest.raises(MpladsAdapterError, match="getTilesReportData"):
            load_and_adapt(tmp_path)

    def test_missing_optional_tiles_degrade_rather_than_fail(self, tmp_path):
        (tmp_path / "mplads-sanctioned.json").write_text(
            json.dumps([sanctioned_row(1)]), encoding="utf-8"
        )
        records, counts = load_and_adapt(tmp_path, as_of=AS_OF)
        assert counts["records"] == 1
        assert counts["completed_rows"] == 0
        assert counts["expenditure_rows"] == 0
        # The degradation is specific and visible: no vendor, no spend.
        assert records[0]["vendor_name"] is None
        assert records[0]["expenditure_amount_inr"] == 0.0

    def test_reads_the_dict_wrapped_tile_shape(self, tmp_path):
        # getTilesReportData returns {"<Tile Label>": "<json string>"} -- the
        # value is itself a JSON string needing a second decode. The
        # Completed tile is cached in this shape.
        (tmp_path / "mplads-sanctioned.json").write_text(
            json.dumps({"Total Sanction Work": json.dumps([sanctioned_row(1)])}),
            encoding="utf-8",
        )
        records, counts = load_and_adapt(tmp_path, as_of=AS_OF)
        assert counts["records"] == 1

    def test_total_amt_summary_row_is_not_treated_as_a_work(self, tmp_path):
        # Every tile's decoded list ends with a {"Total_Amt": ...} aggregate.
        (tmp_path / "mplads-sanctioned.json").write_text(
            json.dumps([sanctioned_row(1), {"Total_Amt": 5.69e10}]), encoding="utf-8"
        )
        records, counts = load_and_adapt(tmp_path, as_of=AS_OF)
        assert counts["sanctioned_rows"] == 1
        assert len(records) == 1

    def test_unparseable_tile_names_the_truncation_problem(self, tmp_path):
        (tmp_path / "mplads-sanctioned.json").write_text('[{"a": 1}', encoding="utf-8")
        with pytest.raises(MpladsAdapterError, match="truncated"):
            load_and_adapt(tmp_path)
