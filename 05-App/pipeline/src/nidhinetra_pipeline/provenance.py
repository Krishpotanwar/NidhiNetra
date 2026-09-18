"""F-18 (nemotronreview.md): provenance recorded with every snapshot build.

Answers "where exactly did these numbers come from" without a live join:
which cached MPLADS tiles fed the build (bytes, sha256, row counts, and
whether the capture is known to be incomplete), which normalized cache was
read, which contract versions shaped the records, and which scoring
configuration ranked them. build_snapshot() writes the result into
manifest.json under "provenance"; GET /api/provenance serves it.

Read-only on data/raw/: it hashes and parses tiles, never writes them.
"""

from __future__ import annotations

import hashlib
import json
from importlib import metadata
from pathlib import Path
from typing import Any

from .ingest import mplads_adapter
from .risk import detectors, peer_groups, rank

# file name -> (role, known complete?, note). The salvaged expenditure tile is
# the one known gap: the server truncated the original capture mid-record.
_TILE_ROLES: dict[str, tuple[str, bool, str | None]] = {
    mplads_adapter.SANCTIONED_FILE: ("works_sanctioned", True, None),
    mplads_adapter.COMPLETED_FILE: ("works_completed", True, None),
    mplads_adapter.EXPENDITURE_FILE: (
        "expenditure_events",
        False,
        "Salvaged from a capture the server truncated mid-record; how many payment events "
        "were lost is unknown.",
    ),
}
_TRUNCATED_ORIGINAL = "mplads-expenditure.json"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    """sha256 of a JSON value with sorted keys and no whitespace, so the same
    configuration always hashes the same."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tile_receipts(tiles_dir: Path) -> list[dict[str, Any]]:
    """One receipt per cached tile present in `tiles_dir`, in a fixed order."""
    receipts: list[dict[str, Any]] = []
    for name, (role, complete, note) in _TILE_ROLES.items():
        path = tiles_dir / name
        if not path.exists():
            continue
        receipts.append(
            {
                "file": name,
                "role": role,
                "bytes": path.stat().st_size,
                "sha256": sha256_of(path),
                "rows": len(mplads_adapter._read_tile(path)),
                "complete": complete,
                "note": note,
            }
        )
    original = tiles_dir / _TRUNCATED_ORIGINAL
    if original.exists():
        receipts.append(
            {
                "file": _TRUNCATED_ORIGINAL,
                "role": "expenditure_events_original_capture",
                "bytes": original.stat().st_size,
                "sha256": sha256_of(original),
                "rows": None,
                "complete": False,
                "note": "The original capture, which is not valid JSON because the server "
                "truncated it. Kept as evidence; the build reads the salvaged copy instead.",
            }
        )
    return receipts


def scoring_config() -> dict[str, Any]:
    """Every constant that decides a flag or a rank, read from the live modules."""
    return {
        "flag_weights": dict(rank.FLAG_WEIGHTS),
        "flags_component_cap": rank.FLAGS_COMPONENT_CAP,
        "ensemble_component_weight": rank.ENSEMBLE_COMPONENT_WEIGHT,
        "cost_z_threshold": detectors.COST_Z_THRESHOLD,
        "stall_months_threshold": detectors.STALL_MONTHS_THRESHOLD,
        "stall_spend_percent_threshold": detectors.STALL_SPEND_PERCENT_THRESHOLD,
        "expenditure_ratio_z_threshold": detectors.EXPENDITURE_RATIO_Z_THRESHOLD,
        "concentration_z_threshold": detectors.CONCENTRATION_Z_THRESHOLD,
        "min_span_for_concentration": detectors.MIN_SPAN_FOR_CONCENTRATION,
        "min_works_for_concentration_candidacy": detectors.MIN_WORKS_FOR_CONCENTRATION_CANDIDACY,
        "min_peer_group_n": peer_groups.MIN_PEER_GROUP_N,
        "isolation_forest": {
            "n_estimators": detectors.ISOLATION_FOREST_N_ESTIMATORS,
            "contamination": detectors.ISOLATION_FOREST_CONTAMINATION,
            "random_state": detectors.ISOLATION_FOREST_RANDOM_STATE,
        },
        "lof": {
            "n_neighbors_default": detectors.LOF_N_NEIGHBORS_DEFAULT,
            "contamination": detectors.LOF_CONTAMINATION,
        },
    }


def _pipeline_version() -> str:
    try:
        return metadata.version("nidhinetra-pipeline")
    except metadata.PackageNotFoundError:
        return "unknown"


def build_provenance(
    *,
    tiles_dir: Path,
    contracts_dir: Path,
    acquisition_mode: str,
    normalized_cache: Path | None,
) -> dict[str, Any]:
    config = scoring_config()
    return {
        "acquisition_mode": acquisition_mode,
        "tile_receipts": tile_receipts(tiles_dir) if acquisition_mode == "cached_tiles" else [],
        "normalized_cache": (
            {"file": normalized_cache.name, "sha256": sha256_of(normalized_cache)}
            if normalized_cache is not None
            else None
        ),
        "contract_sha256": {
            path.name: sha256_of(path) for path in sorted(contracts_dir.glob("*.schema.json"))
        },
        "scoring_config": config,
        "scoring_config_sha256": canonical_sha256(config),
        "pipeline_version": _pipeline_version(),
    }


__all__ = [
    "build_provenance",
    "canonical_sha256",
    "scoring_config",
    "sha256_of",
    "tile_receipts",
]
