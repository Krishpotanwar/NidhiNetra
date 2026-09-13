"""Disk cache for normalized snapshots, with an atomic write-swap.

Everything downstream reads the on-disk snapshot, never the live source
(Execution Plan section 2, "hard rule"). A partial or invalid pull must
never overwrite the last good file: this module always writes to a fresh
temp file in the target directory first, validates that temp file, and only
then does an `os.rename` into the final `<timestamp>.json` path. `os.rename`
within the same directory (same filesystem) is atomic on POSIX, so readers
never observe a half-written file at the final path -- they either see the
old file or the fully-written new one, never something in between.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# pipeline/src/nidhinetra_pipeline/ingest/cache.py -> parents[4] is "05 App/"
_APP_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RAW_DIR = _APP_ROOT / "data" / "raw"


class CacheWriteError(Exception):
    """Raised when a snapshot write cannot be safely completed. The caller's
    previous good snapshot is guaranteed untouched when this is raised.
    """


def default_raw_dir() -> Path:
    """The project's `data/raw/` directory (already exists, gitignored)."""
    return DEFAULT_RAW_DIR


def _timestamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_snapshot(
    records: list[dict],
    *,
    raw_dir: Path | None = None,
    now: datetime | None = None,
) -> Path:
    """Atomically write `records` as a timestamped JSON snapshot.

    Steps, in order:
      1. Serialize `records` to JSON in memory.
      2. Write that JSON to a temp file in `raw_dir` (same filesystem as the
         final path, required for `os.rename` to be atomic).
      3. Re-read and re-parse the temp file to confirm it landed on disk
         intact -- this is the "validate" step, catching a truncated or
         corrupted write before it can ever become the "latest" snapshot.
      4. `os.rename()` the temp file onto `<raw_dir>/<timestamp>.json`.

    If any step before the rename fails, the temp file is removed and the
    previous good snapshot (if any) is left completely untouched. Raises
    `CacheWriteError` on failure.
    """
    raw_dir = raw_dir or default_raw_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    now = now or datetime.now(timezone.utc)
    timestamp = _timestamp(now)
    final_path = raw_dir / f"{timestamp}.json"

    try:
        payload = json.dumps(records, indent=2, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise CacheWriteError(f"records are not JSON-serializable: {exc}") from exc

    fd, tmp_name = tempfile.mkstemp(
        dir=raw_dir, prefix=f".{timestamp}.", suffix=".json.tmp"
    )
    tmp_path = Path(tmp_name)

    try:
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise CacheWriteError(
                f"snapshot write for {timestamp} was interrupted before it "
                f"could be safely persisted: {exc}"
            ) from exc

        # Validate before the swap: re-read what actually landed on disk.
        try:
            reloaded = json.loads(tmp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise CacheWriteError(
                f"snapshot write for {timestamp} produced unparseable JSON, "
                f"refusing to swap: {exc}"
            ) from exc
        if reloaded != records:
            raise CacheWriteError(
                f"snapshot write for {timestamp} did not round-trip cleanly, "
                "refusing to swap"
            )

        try:
            os.rename(tmp_path, final_path)
        except OSError as exc:
            raise CacheWriteError(
                f"could not atomically swap snapshot {timestamp} into place: {exc}"
            ) from exc
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return final_path


# Snapshot filenames are exactly `<YYYYMMDDTHHMMSSZ>.json` (see _timestamp).
# Matching on this rather than `*.json` is what stops an unrelated JSON file
# in the same directory from being mistaken for a snapshot: as of 2026-09-04
# data/raw/ also holds raw MPLADS tile responses (`mplads-sanctioned.json`
# and friends, the adapter's *input*), and those sort lexicographically after
# any timestamp, so a bare `*.json` glob returned one of them as "the latest
# snapshot" and build_snapshot() then tried to read source_rung off raw
# dashboard rows. The old docstring already claimed this function was
# defensive about stray files; it only checked that they parsed as JSON, not
# that they were snapshots.
_SNAPSHOT_NAME = re.compile(r"^\d{8}T\d{6}Z\.json$")


def latest_good(raw_dir: Path | None = None) -> Path | None:
    """The most recent valid snapshot in `raw_dir`, or `None` if none exists.

    "Valid" means the filename is a snapshot timestamp AND the contents
    parse as JSON. Timestamps sort lexicographically in chronological
    order, so a reverse sort gives newest-first.
    """
    raw_dir = raw_dir or default_raw_dir()
    if not raw_dir.exists():
        return None

    candidates = [p for p in raw_dir.glob("*.json") if _SNAPSHOT_NAME.match(p.name)]
    for path in sorted(candidates, reverse=True):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        return path

    return None
