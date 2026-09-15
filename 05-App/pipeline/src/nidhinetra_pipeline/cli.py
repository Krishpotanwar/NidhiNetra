"""Minimal pipeline CLI.

Usage:
    python -m nidhinetra_pipeline.cli pull-live   # optional, see below
    python -m nidhinetra_pipeline.cli build

`build` runs the acquisition ladder (`ingest/rungs.py`), normalizes whatever
it returns (`normalize/normalize.py`), atomically caches the result
(`ingest/cache.py`), and then rebuilds the served snapshot in data/snapshot/
from that cache (`build_snapshot.py`; F-12). Rung 1 has been live since 2026-09-04 and reads
whatever tiles are cached in `data/raw/mplads-*.json`; if the ladder is ever
exhausted (no cached tiles and every other rung still unimplemented), `build`
falls through to the labelled seed fixture at
`contracts/fixtures/works.fixture.json` and prints a loud, unambiguous
warning when it does -- this keeps the pipeline runnable end to end even
without a live pull, without ever letting fixture output pass for real data
silently.

`pull-live` is the optional step that refreshes those cached tiles from the
real MPLADS endpoint before a `build`. It needs no cookie or credential
input, but it must be run from an ordinary (non-datacenter) network by a
human, a few minutes before a demo -- see 04 Prototype/Checkpoints.md CP6
for why an automated/cloud environment (this kind of sandbox, CI) cannot run
it at all.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

from .build_snapshot import SnapshotDowngradeError, SnapshotWriteError, build_snapshot
from .ingest import cache, mplads_adapter
from .ingest.mplads_api import MpladsClient, MpladsClientError
from .ingest.rungs import AllRungsFailedError, run_ladder
from .normalize.normalize import NormalizeValidationError, normalize_records

logger = logging.getLogger("nidhinetra_pipeline.cli")

# pipeline/src/nidhinetra_pipeline/cli.py -> parents[3] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_PATH = _APP_ROOT / "contracts" / "fixtures" / "works.fixture.json"
FIXTURE_SOURCE_RUNG = 5  # labelled seed set, per Execution Plan section 2

# The three tiles Rung 1 needs, joined by ingest/mplads_adapter.py -- see
# that module's docstring for why each one is needed and how they join.
# Same combo for all three (confirmed 2026-09-04, Logbook).
_LIVE_COMBO = "0,0,0,2"
_TILE_REQUESTS: dict[str, str] = {
    mplads_adapter.SANCTIONED_FILE: "Works Sanctioned",
    mplads_adapter.COMPLETED_FILE: "Works Completed",
    mplads_adapter.EXPENDITURE_FILE: "Expenditure on Completed and On-going Works as on Date",
}


def _load_fixture_fallback() -> list[dict]:
    banner = (
        "\n"
        + "!" * 72
        + "\n"
        + "! LIVE DATA ACQUISITION IS BLOCKED. Falling back to the labelled\n"
        + "! seed fixture -- THIS IS NOT LIVE DATA.\n"
        + f"! Source: {FIXTURES_PATH}\n"
        + "! Every emitted record carries source_rung=5.\n"
        + "! See 04 Prototype/Logbook.md, 2026-09-01 19:45 and 20:10 entries.\n"
        + "!" * 72
        + "\n"
    )
    print(banner, file=sys.stderr)
    logger.warning(
        "Falling back to labelled seed fixture at %s (source_rung=%d). "
        "This is NOT live MPLADS data.",
        FIXTURES_PATH,
        FIXTURE_SOURCE_RUNG,
    )
    if not FIXTURES_PATH.exists():
        raise FileNotFoundError(
            f"fixture fallback file missing at {FIXTURES_PATH}; cannot run "
            "the pipeline end to end without either live data or fixtures"
        )
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def build(*, raw_dir: Path | None = None, snapshot_dir: Path | None = None) -> int:
    """Run ladder -> normalize -> cache -> served snapshot. Returns an exit code.

    `raw_dir` overrides where the cache write lands and where the snapshot
    rebuild reads it from; `snapshot_dir` overrides where the served snapshot
    is written. `None` (every real invocation) means the defaults, data/raw/
    and data/snapshot/. Both exist so tests can point a full run at temp
    directories (pipeline/tests/test_cli.py).

    F-12 (nemotronreview.md, fixed with the 2026-09-15 resequencing): the
    served snapshot is rebuilt from the cache this call just wrote, so `make
    pipeline` produces what the API actually serves instead of stopping at
    the raw cache. A rebuild that would downgrade a better-provenance snapshot
    (for example, the rung-5 fixture fallback on a machine that already
    serves real data) is refused by build_snapshot(); that refusal is
    reported and is not a failure, because the cache write succeeded and
    keeping the better snapshot is correct.

    The cache file, and therefore the snapshot's data_as_of, is stamped with
    the time of this build. Run it right after a real `pull-live`, never to
    rebuild old tiles (that needs an explicit acquisition time).
    """
    try:
        raw_records, source_rung = run_ladder()
    except AllRungsFailedError as exc:
        logger.warning("Acquisition ladder exhausted: %s", exc)
        try:
            raw_records = _load_fixture_fallback()
        except FileNotFoundError as fnf:
            logger.error("%s", fnf)
            return 1
        source_rung = FIXTURE_SOURCE_RUNG

    try:
        normalized = normalize_records(raw_records, source_rung=source_rung)
    except NormalizeValidationError as exc:
        logger.error("Normalization failed, nothing was cached: %s", exc)
        return 1

    snapshot_path = cache.write_snapshot(normalized, raw_dir=raw_dir)
    logger.info(
        "Wrote %d normalized records to %s (source_rung=%d)",
        len(normalized),
        snapshot_path,
        source_rung,
    )
    print(
        f"Wrote {len(normalized)} normalized records to {snapshot_path} (source_rung={source_rung})"
    )

    try:
        manifest = build_snapshot(snapshot_dir=snapshot_dir, raw_dir=raw_dir)
    except SnapshotDowngradeError as exc:
        logger.warning("Served snapshot left unchanged: %s", exc)
        print(f"Served snapshot left unchanged: {exc}")
        return 0
    except SnapshotWriteError as exc:
        logger.error("Served snapshot rebuild failed; the previous one is untouched: %s", exc)
        return 1

    print(
        f"Rebuilt the served snapshot: {manifest['row_count']} records "
        f"(source={manifest['source']}, data_as_of={manifest['data_as_of']})"
    )
    return 0


def _write_tiles_atomically(payloads: dict[str, dict], raw_dir: Path) -> None:
    """Stages every tile to a temp file in raw_dir first and renames them
    into place only once every one of them has round-tripped cleanly -- the
    same group-atomicity discipline build_snapshot.py uses for its own four
    artifacts. Without it, a failure partway through (e.g. disk full on the
    third file) could leave two tiles from a fresh pull sitting next to one
    stale tile from the last pull, and the adapter has no way to know its
    three inputs came from different pulls.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        for filename, payload in payloads.items():
            final_path = raw_dir / filename
            text = json.dumps(payload, ensure_ascii=False)
            fd, tmp_name = tempfile.mkstemp(dir=raw_dir, prefix=f".{filename}.", suffix=".tmp")
            tmp_path = Path(tmp_name)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            reloaded = json.loads(tmp_path.read_text(encoding="utf-8"))
            if reloaded != payload:
                raise OSError(f"{filename} did not round-trip cleanly, refusing to swap")
            staged.append((tmp_path, final_path))
    except Exception:
        for tmp_path, _final_path in staged:
            tmp_path.unlink(missing_ok=True)
        raise

    for tmp_path, final_path in staged:
        os.rename(tmp_path, final_path)


def pull_live(*, raw_dir: Path | None = None, client: MpladsClient | None = None) -> int:
    """Fetches the three MPLADS tiles live and atomically replaces the
    cached copies in raw_dir (default data/raw/) that ingest/rungs.py's
    Rung1LiveApi reads. Does not touch Rung1LiveApi or run_ladder() at
    all -- it refreshes the cache those already read, upstream of the
    ladder rather than a change to it.

    No cookie or credential input is required from a human. `warm_session()`
    bootstraps a fresh session exactly the way a browser opening the
    dashboard does, and every following request reuses it automatically via
    the client's own cookie jar.

    Meant to be run once, by a human, from an ordinary (non-datacenter)
    network -- a home or office connection, the kind the 2026-09-04 pull
    used -- a few minutes before a demo, never during it. See
    04 Prototype/Checkpoints.md CP6: every attempt from an automated/cloud
    environment has tarpitted regardless of session, headers, or
    browser-TLS-fingerprint impersonation (tested directly, 2026-09-05), so
    this cannot and will not succeed from CI or a sandbox like this one --
    that is a network-origin fact, not a bug in this function.

    A failure here (including the tarpit above) leaves raw_dir completely
    untouched: nothing is written until every tile has round-tripped
    cleanly, so the app keeps serving whatever it already had.
    """
    raw_dir = raw_dir or mplads_adapter.DEFAULT_RAW_DIR
    owns_client = client is None
    client = client or MpladsClient()

    try:
        try:
            client.warm_session()
            payloads = {
                filename: client.get_tiles_report_data_raw(_LIVE_COMBO, key)
                for filename, key in _TILE_REQUESTS.items()
            }
        except MpladsClientError as exc:
            logger.error("Live pull failed, %s left untouched: %s", raw_dir, exc)
            print(f"Live pull failed: {exc}", file=sys.stderr)
            return 1
    finally:
        if owns_client:
            client.close()

    try:
        _write_tiles_atomically(payloads, raw_dir)
    except OSError as exc:
        logger.error("Could not write fetched tiles to %s: %s", raw_dir, exc)
        print(f"Could not write fetched tiles: {exc}", file=sys.stderr)
        return 1

    for filename in payloads:
        print(f"Wrote {raw_dir / filename}")
    logger.info("Live pull succeeded: %d tiles written to %s", len(payloads), raw_dir)
    print(
        "Live pull succeeded. Run `python -m nidhinetra_pipeline.cli build` "
        "next to turn these into a fresh snapshot."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nidhinetra_pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "build", help="Run the acquisition ladder, normalize, and cache a snapshot."
    )
    subparsers.add_parser(
        "pull-live",
        help=(
            "Fetch fresh MPLADS tiles live into data/raw/. Run this once, by hand, "
            "from a normal network, a few minutes before a demo -- see "
            "04 Prototype/Checkpoints.md CP6 for why it must not run from CI or a "
            "cloud sandbox. Follow with `build` to turn the fresh tiles into a snapshot."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.command == "build":
        return build()
    if args.command == "pull-live":
        return pull_live()

    parser.error(f"unknown command {args.command!r}")
    return 2  # pragma: no cover - argparse.error() exits before this


if __name__ == "__main__":
    raise SystemExit(main())
