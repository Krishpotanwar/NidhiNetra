"""Reads data/snapshot/manifest.json and triggers snapshot rebuilds via
nidhinetra_pipeline.build_snapshot. Shared by main.py's startup bootstrap,
routers/stats.py (data_as_of) and routers/refresh.py (rate limiting plus
the rebuild itself).
"""

from __future__ import annotations

import fcntl
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nidhinetra_pipeline.build_snapshot import build_snapshot as _build_snapshot

# api/src/nidhinetra_api/snapshot.py -> parents[3] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = _APP_ROOT / "data" / "snapshot"
# Where a rebuild reads its source records from: the acquisition ladder's
# cache (build_snapshot prefers the newest snapshot there over the CP0
# fixtures). Exposed as a module constant, like SNAPSHOT_DIR, so a caller
# that repoints one can repoint the other -- and so the test suite can
# isolate a rebuild from the operator's real 79k-record cache. None means
# "use build_snapshot's own default", which is the production case.
RAW_DIR: Path | None = None


class RefreshInProgressError(Exception):
    """Another snapshot refresh holds the single-flight guard (F-11)."""


# One rebuild at a time in this process. The advisory file lock in
# refresh_guard() extends that to every process on the machine (several
# uvicorn workers, or a CLI run in another terminal).
_REFRESH_LOCK = threading.Lock()


@contextmanager
def refresh_guard(snapshot_dir: Path | None = None) -> Iterator[None]:
    """Single-flight guard for snapshot rebuilds (F-11, nemotronreview.md).

    Takes a non-blocking in-process lock, then a non-blocking advisory lock on
    <snapshot_dir>/.refresh.lock. If either is already held, raises
    RefreshInProgressError immediately instead of queueing a second rebuild.
    Callers run their rate-limit check inside this guard, so check-then-act
    is one critical section. POSIX only (macOS, Linux, Render), like the rest
    of the deployment.
    """
    if not _REFRESH_LOCK.acquire(blocking=False):
        raise RefreshInProgressError("a snapshot refresh is already running in this process")
    try:
        directory = snapshot_dir or SNAPSHOT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        with open(directory / ".refresh.lock", "w", encoding="utf-8") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RefreshInProgressError(
                    "a snapshot refresh is already running in another process"
                ) from exc
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        _REFRESH_LOCK.release()


def _manifest_path(snapshot_dir: Path | None) -> Path:
    return (snapshot_dir or SNAPSHOT_DIR) / "manifest.json"


def read_manifest(snapshot_dir: Path | None = None) -> dict[str, Any] | None:
    """The current manifest, or None if the snapshot has never been built."""
    path = _manifest_path(snapshot_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def data_as_of_date(snapshot_dir: Path | None = None) -> str | None:
    """The "YYYY-MM-DD" date part of the manifest's data_as_of (D2: never
    today, never max(last_updated)), or None if there is no manifest yet.
    Callers that need this to answer a request (the pendency filter and
    /api/pendency) turn None into a 503 themselves rather than guessing a
    date; _decorate() in routers/works.py instead degrades a single field
    to None, since a work's own detail is still worth showing.
    """
    manifest = read_manifest(snapshot_dir)
    if manifest is None:
        return None
    return manifest["data_as_of"][:10]


def _early_warning_path(snapshot_dir: Path | None) -> Path:
    return (snapshot_dir or SNAPSHOT_DIR) / "early_warning.json"


# T8B: (path, st_mtime_ns, st_size) -> the parsed early_warning.json. Same
# pattern as routers/graph.py's _ANALYSIS_CACHE: a rewritten artifact changes
# mtime/size, so a stale parse is never served, and clearing before inserting
# keeps exactly one entry rather than one per snapshot generation this
# process has ever read.
_EARLY_WARNING_CACHE: dict[tuple[str, int, int], dict[str, Any]] = {}


def read_early_warning(snapshot_dir: Path | None = None) -> dict[str, Any] | None:
    """Task 8's early-warning artifact, or None when it should not be
    served: the file does not exist yet, its data_as_of does not match the
    current manifest's (D8 -- a refresh that moves as_of forward makes the
    old artifact's ranking stale before the pipeline re-runs it), or its own
    status is not "shipped" (the ship gate in early_warning.build did not
    clear, so there is no watch list worth showing).

    Only the parsed JSON is cached, by file mtime; the data_as_of/status
    check is cheap and re-run against the *current* manifest on every call,
    since a snapshot refresh can move that target without early_warning.json
    itself changing.
    """
    path = _early_warning_path(snapshot_dir)
    if not path.exists():
        return None
    stat = path.stat()
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if key not in _EARLY_WARNING_CACHE:
        _EARLY_WARNING_CACHE.clear()
        _EARLY_WARNING_CACHE[key] = json.loads(path.read_text(encoding="utf-8"))
    artifact = _EARLY_WARNING_CACHE[key]
    is_fresh = artifact.get("data_as_of") == data_as_of_date(snapshot_dir)
    is_shipped = artifact.get("status") == "shipped"
    return artifact if is_fresh and is_shipped else None


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
    "RefreshInProgressError",
    "SNAPSHOT_DIR",
    "bootstrap_if_needed",
    "data_as_of_date",
    "read_early_warning",
    "read_manifest",
    "rebuild",
    "refresh_guard",
    "seconds_since_last_refresh",
]
