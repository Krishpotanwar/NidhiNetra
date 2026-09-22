"""Tests for the judgments file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from nidhinetra_pipeline.judge import store

STAMP = {
    "model_id": "m",
    "provider_id": "p",
    "prompt_version": "prompt1",
    "schema_version": "schema1",
}


def _row(scope: str = "C1", **overrides: Any) -> dict[str, Any]:
    row = {
        "scope": scope,
        "fingerprint_a": "fa",
        "fingerprint_b": "fb",
        "input_fingerprint": "i1",
        "status": "judged",
        "relation": "unrelated",
        "rejection": None,
        "asset_a": None,
        "place_a": "Rampur",
        "asset_b": None,
        "place_b": None,
        **STAMP,
        "judge_code_version": "code1",
        "run_timestamp": "2026-09-22T10:00:00+00:00",
    }
    return {**row, **overrides}


def _frame(*rows: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=store.COLUMNS)


class TestFile:
    def test_a_missing_file_reads_as_an_empty_frame_with_every_column(self, tmp_path: Path) -> None:
        frame = store.read_judgments(tmp_path / "none.parquet")

        assert frame.empty
        assert list(frame.columns) == store.COLUMNS

    def test_a_frame_round_trips_with_its_nulls(self, tmp_path: Path) -> None:
        path = tmp_path / "judgments" / store.FILENAME  # the folder does not exist yet
        written = _frame(
            _row(),
            _row("C2", status="rejected", relation=None, rejection="place_quotes_differ"),
        )

        store.write_judgments(written, path)
        read = store.read_judgments(path)

        assert list(read.columns) == store.COLUMNS
        assert read["scope"].tolist() == ["C1", "C2"]
        assert read["status"].tolist() == ["judged", "rejected"]
        assert read["relation"].isna().tolist() == [False, True]
        assert read["rejection"].isna().tolist() == [True, False]
        assert read["place_a"].tolist() == ["Rampur", "Rampur"]

    def test_a_failed_write_leaves_the_old_file_and_no_temp_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / store.FILENAME
        store.write_judgments(_frame(_row()), path)
        before = path.read_bytes()

        def boom(self: pd.DataFrame, *args: Any, **kwargs: Any) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(pd.DataFrame, "to_parquet", boom)
        with pytest.raises(OSError, match="disk full"):
            store.write_judgments(_frame(_row(), _row("C2")), path)

        assert path.read_bytes() == before
        assert list(tmp_path.iterdir()) == [path]


class TestAnswered:
    def test_a_row_answers_only_the_same_model_provider_prompt_and_schema(self) -> None:
        frame = _frame(
            _row("kept"),
            _row("other model", model_id="m2"),
            _row("other provider", provider_id="p2"),
            _row("other prompt", prompt_version="prompt2"),
            _row("other schema", schema_version="schema2"),
        )

        assert store.answered(frame, STAMP) == {("kept", "fa", "fb", "i1")}

    def test_a_rejected_row_counts_as_answered_so_it_is_not_paid_for_twice(self) -> None:
        frame = _frame(_row(status="rejected", relation=None, rejection="place_quotes_differ"))

        assert store.answered(frame, STAMP) == {("C1", "fa", "fb", "i1")}

    def test_a_changed_input_is_not_answered(self) -> None:
        frame = _frame(_row(input_fingerprint="old"))

        assert ("C1", "fa", "fb", "new") not in store.answered(frame, STAMP)

    def test_an_empty_frame_answers_nothing(self) -> None:
        assert store.answered(_frame(), STAMP) == set()
