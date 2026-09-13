"""Reads data/snapshot/manifest.json and triggers snapshot rebuilds via
nidhinetra_pipeline.build_snapshot. Shared by main.py's startup bootstrap,
routers/stats.py (data_as_of) and routers/refresh.py (rate limiting plus
the rebuild itself).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nidhinetra_pipeline.build_snapshot import build_snapshot as _build_snapshot

# api/src/nidhinetra_api/snapshot.py -> parents[3] is "05 App/"
_APP_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = _APP_ROOT / "data" / "snapshot"
# Where a rebuild reads its source records from: the acquisition ladder's
# cache (build_snapshot prefers the newest snapshot there over the CP0
# fixtures). Exposed as a module constant, like SNAPSHOT_DIR, so a caller
# that repoints one can repoint the other -- and so the test suite can
# isolate a rebuild from the operator's real 79k-record cache. None means
# "use build_snapshot's own default", which is the production case.
RAW_DIR: Path | None = None


def _manifest_path(snapshot_dir: Path | None) -> Path:
    return (snapshot_dir or SNAPSHOT_DIR) / "manifest.json"


def read_manifest(snapshot_dir: Path | None = None) -> dict[str, Any] | None:
    """The current manifest, or None if the snapshot has never been built."""
    path = _manifest_path(snapshot_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def bootstrap_if_needed(snapshot_dir: Path | None = None) -> dict[str, Any]:
    """Called once from main.py's startup hook. Builds the snapshot only if
    manifest.json doesn't exist yet, so `make api` works standalone without
    a manual `make pipeline` / build_snapshot run first. Returns the
    existing manifest unchanged if one is already there -- this is a
    bootstrap, not an unconditional rebuild-on-every-boot.
    """
    existing = read_manifest(snapshot_dir)
    if existing is not None:
        return existing
    # Resolved here rather than passed through as None: build_snapshot's
    # own default is the *pipeline* module's SNAPSHOT_DIR, so forwarding
    # None honoured this module's SNAPSHOT_DIR on reads (via _manifest_path)
    # while silently ignoring it on writes. Repointing the API at another
    # snapshot directory would have read from the new one and written to the
    # old. Found 2026-09-04.
    return _build_snapshot(snapshot_dir=snapshot_dir or SNAPSHOT_DIR, raw_dir=RAW_DIR)


def rebuild(snapshot_dir: Path | None = None) -> dict[str, Any]:
    """Unconditionally rebuilds the snapshot. What POST /api/refresh calls
    once its own rate-limit check (seconds_since_last_refresh) has passed.
    """
    # See bootstrap_if_needed on why this resolves rather than forwards None.
    return _build_snapshot(snapshot_dir=snapshot_dir or SNAPSHOT_DIR, raw_dir=RAW_DIR)


def seconds_since_last_refresh(snapshot_dir: Path | None = None) -> float | None:
    """Seconds since manifest.generated_at, or None if there is no
    manifest yet (in which case a refresh should always be allowed).
    """
    manifest = read_manifest(snapshot_dir)
    if manifest is None:
        return None
    generated_at = datetime.strptime(manifest["generated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    return (datetime.now(timezone.utc) - generated_at).total_seconds()


__all__ = [
    "RAW_DIR",
    "SNAPSHOT_DIR",
    "bootstrap_if_needed",
    "read_manifest",
    "rebuild",
    "seconds_since_last_refresh",
]
