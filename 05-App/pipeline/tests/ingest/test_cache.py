"""Tests for ingest/cache.py -- the atomic write-swap and latest_good()."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nidhinetra_pipeline.ingest import cache
from nidhinetra_pipeline.ingest.cache import CacheWriteError


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    d = tmp_path / "raw"
    d.mkdir()
    return d


SAMPLE_RECORDS = [{"work_id": "W1", "state": "Bihar"}, {"work_id": "W2", "state": "Jharkhand"}]


def test_write_snapshot_creates_file_with_expected_content(raw_dir):
    path = cache.write_snapshot(SAMPLE_RECORDS, raw_dir=raw_dir)

    assert path.exists()
    assert path.parent == raw_dir
    assert json.loads(path.read_text(encoding="utf-8")) == SAMPLE_RECORDS


def test_write_snapshot_filename_is_utc_timestamp(raw_dir):
    now = datetime(2026, 9, 1, 20, 10, 5, tzinfo=timezone.utc)
    path = cache.write_snapshot(SAMPLE_RECORDS, raw_dir=raw_dir, now=now)

    assert path.name == "20260901T201005Z.json"


def test_write_snapshot_leaves_no_tmp_files_behind_on_success(raw_dir):
    cache.write_snapshot(SAMPLE_RECORDS, raw_dir=raw_dir)

    leftovers = list(raw_dir.glob("*.tmp"))
    assert leftovers == []


def test_write_snapshot_two_calls_produce_two_distinct_files(raw_dir):
    first = cache.write_snapshot(
        SAMPLE_RECORDS, raw_dir=raw_dir, now=datetime(2026, 9, 1, 20, 0, 0, tzinfo=timezone.utc)
    )
    second = cache.write_snapshot(
        [{"work_id": "W3"}],
        raw_dir=raw_dir,
        now=datetime(2026, 9, 1, 20, 5, 0, tzinfo=timezone.utc),
    )

    assert first != second
    assert first.exists()
    assert second.exists()


def test_latest_good_returns_none_when_no_snapshots_exist(raw_dir):
    assert cache.latest_good(raw_dir=raw_dir) is None


def test_latest_good_returns_none_when_dir_does_not_exist(tmp_path):
    missing = tmp_path / "does_not_exist_yet"
    assert cache.latest_good(raw_dir=missing) is None


def test_latest_good_returns_most_recent_valid_snapshot(raw_dir):
    cache.write_snapshot(
        [{"work_id": "old"}],
        raw_dir=raw_dir,
        now=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    newest = cache.write_snapshot(
        [{"work_id": "new"}],
        raw_dir=raw_dir,
        now=datetime(2026, 9, 1, 20, 0, 0, tzinfo=timezone.utc),
    )

    result = cache.latest_good(raw_dir=raw_dir)

    assert result == newest
    assert json.loads(result.read_text())[0]["work_id"] == "new"


def test_latest_good_skips_unparseable_json_files(raw_dir):
    good = cache.write_snapshot(
        SAMPLE_RECORDS, raw_dir=raw_dir, now=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    # A file that lexically sorts after `good` but is corrupt -- latest_good
    # must skip it rather than returning it just because it is newest by name.
    corrupt = raw_dir / "20260901T230000Z.json"
    corrupt.write_text("{not valid json", encoding="utf-8")

    result = cache.latest_good(raw_dir=raw_dir)

    assert result == good


# --------------------------------------------------------------------------
# Interrupted-write / atomic-swap safety
# --------------------------------------------------------------------------


def test_interrupted_write_never_leaves_a_corrupt_final_file(raw_dir, monkeypatch):
    """Simulates a write interrupted by a disk error during fsync. The swap
    must never happen: no final `<timestamp>.json` is created, and the temp
    file is cleaned up rather than left behind as debris.
    """

    def failing_fsync(fd):
        raise OSError("simulated disk error during fsync")

    monkeypatch.setattr(cache.os, "fsync", failing_fsync)

    with pytest.raises(CacheWriteError):
        cache.write_snapshot(SAMPLE_RECORDS, raw_dir=raw_dir)

    assert list(raw_dir.glob("*.json")) == []
    assert list(raw_dir.glob("*.tmp")) == []


def test_interrupted_write_does_not_disturb_previous_good_snapshot(raw_dir, monkeypatch):
    """The core atomic-swap guarantee: a failed second write must leave the
    first (good) snapshot exactly as it was -- `latest_good()` keeps
    resolving to it, and its bytes are unchanged.
    """
    good_path = cache.write_snapshot(
        SAMPLE_RECORDS, raw_dir=raw_dir, now=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    good_bytes_before = good_path.read_bytes()

    def failing_fsync(fd):
        raise OSError("simulated disk error during fsync")

    monkeypatch.setattr(cache.os, "fsync", failing_fsync)

    with pytest.raises(CacheWriteError):
        cache.write_snapshot(
            [{"work_id": "should never land"}],
            raw_dir=raw_dir,
            now=datetime(2026, 9, 1, 20, 0, 0, tzinfo=timezone.utc),
        )

    assert good_path.read_bytes() == good_bytes_before
    assert cache.latest_good(raw_dir=raw_dir) == good_path


def test_torn_write_content_mismatch_is_rejected_before_swap(raw_dir, monkeypatch):
    """Simulates a write that lands on disk truncated (a torn write): the
    temp file exists but its re-parsed content does not match what was
    meant to be written. The validate-before-swap step must catch this and
    refuse to rename, rather than promoting a truncated file to `latest`.
    """
    real_loads = cache.json.loads
    call_count = {"n": 0}

    def flaky_loads(text, *args, **kwargs):
        call_count["n"] += 1
        # First call is the validation re-read inside write_snapshot; return
        # something that does not match SAMPLE_RECORDS to simulate torn content.
        if call_count["n"] == 1:
            return [{"work_id": "TRUNCATED"}]
        return real_loads(text, *args, **kwargs)

    monkeypatch.setattr(cache.json, "loads", flaky_loads)

    with pytest.raises(CacheWriteError, match="did not round-trip"):
        cache.write_snapshot(SAMPLE_RECORDS, raw_dir=raw_dir)

    assert list(raw_dir.glob("*.json")) == []
    assert list(raw_dir.glob("*.tmp")) == []


def test_write_snapshot_rejects_non_serializable_records(raw_dir):
    class NotSerializable:
        pass

    with pytest.raises(CacheWriteError):
        cache.write_snapshot([{"work_id": NotSerializable()}], raw_dir=raw_dir)

    assert list(raw_dir.glob("*")) == []
