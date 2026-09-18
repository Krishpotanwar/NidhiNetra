"""F-18 (nemotronreview.md): every snapshot records where its numbers came
from: tile receipts (size, sha256, rows, completeness), the normalized cache,
contract hashes and the scoring configuration."""

from __future__ import annotations

import json
from pathlib import Path

from nidhinetra_pipeline import build_snapshot as bs
from nidhinetra_pipeline import provenance
from nidhinetra_pipeline.risk import rank


def _write_tiles(raw: Path) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "mplads-sanctioned.json").write_text(
        json.dumps(
            [
                {"WORK_RECOMMENDATION_DTL_ID": 1},
                {"WORK_RECOMMENDATION_DTL_ID": 2},
                {"Total_Amt": 5.0},
            ]
        ),
        encoding="utf-8",
    )
    (raw / "mplads-completed.json").write_text(
        json.dumps({"Works Completed": json.dumps([{"WORK_RECOMMENDATION_DTL_ID": 1}])}),
        encoding="utf-8",
    )
    (raw / "mplads-expenditure-salvaged.json").write_text(
        json.dumps([{"WORK_RECOMMENDATION_DTL_ID": 1, "IA_NAME": "X"}]), encoding="utf-8"
    )
    (raw / "mplads-expenditure.json").write_text('[{"truncated": ', encoding="utf-8")


def _cache_one_fixture_record(raw: Path) -> None:
    record = json.loads(bs.WORKS_FIXTURE_PATH.read_text(encoding="utf-8"))[0] | {"source_rung": 1}
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "20260904T113718Z.json").write_text(json.dumps([record]), encoding="utf-8")


def test_tile_receipts_record_size_hash_rows_and_completeness(tmp_path: Path) -> None:
    _write_tiles(tmp_path)

    receipts = {r["file"]: r for r in provenance.tile_receipts(tmp_path)}

    sanctioned = receipts["mplads-sanctioned.json"]
    assert sanctioned["rows"] == 2
    assert sanctioned["complete"] is True
    assert len(sanctioned["sha256"]) == 64
    assert sanctioned["bytes"] > 0
    assert receipts["mplads-completed.json"]["rows"] == 1
    salvaged = receipts["mplads-expenditure-salvaged.json"]
    assert salvaged["complete"] is False
    assert "truncated" in salvaged["note"]
    original = receipts["mplads-expenditure.json"]
    assert original["rows"] is None
    assert original["complete"] is False


def test_no_tiles_means_no_receipts(tmp_path: Path) -> None:
    assert provenance.tile_receipts(tmp_path) == []


def test_scoring_config_hash_is_stable_and_changes_with_a_weight(monkeypatch) -> None:
    first = provenance.canonical_sha256(provenance.scoring_config())
    assert first == provenance.canonical_sha256(provenance.scoring_config())

    monkeypatch.setitem(rank.FLAG_WEIGHTS, "cost_outlier", 31)

    assert provenance.canonical_sha256(provenance.scoring_config()) != first


def test_a_fixture_build_records_fixture_provenance(tmp_path: Path) -> None:
    manifest = bs.build_snapshot(snapshot_dir=tmp_path / "snap", raw_dir=tmp_path / "raw")

    block = manifest["provenance"]
    assert block["acquisition_mode"] == "fixture"
    assert block["tile_receipts"] == []
    assert block["normalized_cache"] is None
    assert "normalized_record.schema.json" in block["contract_sha256"]
    assert len(block["scoring_config_sha256"]) == 64
    written = json.loads((tmp_path / "snap" / "manifest.json").read_text(encoding="utf-8"))
    assert written["provenance"] == block
    assert {"row_count", "generated_at", "source", "data_as_of"} <= set(written)


def test_a_cached_build_records_the_cache_and_the_tiles(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    _write_tiles(raw)
    _cache_one_fixture_record(raw)

    manifest = bs.build_snapshot(snapshot_dir=tmp_path / "snap", raw_dir=raw)

    block = manifest["provenance"]
    assert block["acquisition_mode"] == "cached_tiles"
    assert block["normalized_cache"]["file"] == "20260904T113718Z.json"
    assert {r["file"] for r in block["tile_receipts"]} >= {
        "mplads-sanctioned.json",
        "mplads-expenditure-salvaged.json",
    }


def test_tiles_dir_says_where_the_receipts_come_from(tmp_path: Path) -> None:
    cache_only = tmp_path / "cache-only"
    _cache_one_fixture_record(cache_only)
    tiles = tmp_path / "tiles"
    _write_tiles(tiles)

    manifest = bs.build_snapshot(
        snapshot_dir=tmp_path / "snap", raw_dir=cache_only, tiles_dir=tiles
    )

    assert manifest["provenance"]["tile_receipts"]
