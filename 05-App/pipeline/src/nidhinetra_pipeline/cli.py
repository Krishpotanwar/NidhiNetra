"""Minimal pipeline CLI.

Usage:
    python -m nidhinetra_pipeline.cli pull-live   # optional, see below
    python -m nidhinetra_pipeline.cli build
    python -m nidhinetra_pipeline.cli duplicates [--write]
    python -m nidhinetra_pipeline.cli early-warning [--write]
    python -m nidhinetra_pipeline.cli judge [--run --max-usd DOLLARS] [--limit N]

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

`duplicates` reads works.parquet from the served snapshot and prints how many
identical and near-identical work descriptions Phase 1 Stage A's finder
(`duplicates/candidates.py`) found. It writes nothing unless `--write` is given,
and then it writes only data/snapshot/duplicate_candidates.json, so no score,
rank or flag can move (a full `build` scores again as of the day it runs).

`early-warning` reads works.parquet and manifest.json's data_as_of from the served
snapshot, and builds Task 8's early-warning artifact (`early_warning.build`): a logistic
regression ranks recently sanctioned works by risk of staying open past one year. It
prints the metrics (never the watch list itself) and writes nothing unless `--write` is
given, and then only data/snapshot/early_warning.json.

`judge` is Phase 1 Stage B (`judge/`). It asks the pinned model on Hugging Face Inference
Providers what each near-copy pair in data/snapshot/duplicate_candidates.json has in common, and
stores the evidence-checked answers in data/judgments/text_pair_judgments.parquet. It sends
nothing unless `--run` is given, and then only with HF_TOKEN in the environment and a dollar cap
in `--max-usd`. It is never part of `build`.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .build_snapshot import (
    SNAPSHOT_DIR,
    SnapshotDowngradeError,
    SnapshotWriteError,
    build_snapshot,
    duplicate_candidates_from_snapshot,
    write_duplicate_candidates,
)
from .duplicates.candidates import (
    DuplicateCandidateValidationError,
    validate_duplicate_candidates,
)
from .early_warning import build as build_early_warning
from .early_warning import write as write_early_warning
from .ingest import cache, mplads_adapter
from .ingest.mplads_api import MpladsClient, MpladsClientError
from .ingest.rungs import AllRungsFailedError, run_ladder
from .judge import runner, store
from .judge.inputs import items_from_artifact
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


def _archive_existing_tile(final_path: Path, raw_dir: Path) -> None:
    """Copies (never moves) a tile a pull is about to replace into
    raw_dir/archive/<UTC stamp of its own mtime>/ -- the 2026-09-04 captures
    are irreplaceable audit evidence. This must be a copy, not a move: see
    _write_tiles_atomically for why the swap itself has to stay a single
    atomic os.rename with no archiving step interleaved into it. A name
    already sitting in that archive directory (two old tiles landing on the
    same UTC second) is never overwritten either: this falls back to a
    numeric `.1`, `.2`, ... suffix. Nothing this function touches is ever
    deleted.
    """
    stamp = datetime.fromtimestamp(final_path.stat().st_mtime, tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_dir = raw_dir / "archive" / stamp
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / final_path.name
    suffix = 0
    while dest.exists():
        suffix += 1
        dest = archive_dir / f"{final_path.name}.{suffix}"
    shutil.copy2(final_path, dest)


def _write_tiles_atomically(payloads: dict[str, dict], raw_dir: Path) -> None:
    """Stages every tile to a temp file in raw_dir first and renames them
    into place only once every one of them has round-tripped cleanly -- the
    same group-atomicity discipline build_snapshot.py uses for its own six
    artifacts. Without it, a failure partway through (e.g. disk full on the
    third file) could leave two tiles from a fresh pull sitting next to one
    stale tile from the last pull, and the adapter has no way to know its
    three inputs came from different pulls.

    Archiving runs as its own phase, for every staged tile, entirely before
    any rename -- never one tile's archive-then-rename at a time. Each old
    file is *copied* (see _archive_existing_tile) to raw_dir/archive/ while
    still sitting untouched at its final path; only once every tile that
    needed archiving has one are any renames attempted, and each of those
    stays the single atomic os.rename(tmp, final) syscall it always was.
    That ordering is load-bearing (T9 review, round 1): archiving via
    move-then-rename, one tile at a time, meant a process death between the
    two calls for tile i left tile i completely missing from raw_dir --
    worse than the pre-existing worst case this function exists to prevent.
    With copy-first/rename-after, a tile's old bytes are never gone before
    its swap, and the swap itself can never leave a tile absent: a tile is
    always either its old content, its new content, or (mid-archive-phase,
    transiently) both an old file and its archive copy. If any archive copy
    fails, nothing is renamed and the staged .tmp files are cleaned up the
    same way an invalid round-trip above already is.
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

        for _tmp_path, final_path in staged:
            if final_path.exists():
                _archive_existing_tile(final_path, raw_dir)
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
    used, and the kind this VM itself sits on: the portal answered from
    here too on 2026-09-26 -- a few minutes before a demo, never during
    it. See 04 Prototype/Checkpoints.md CP6: every attempt from an
    automated/cloud environment has tarpitted regardless of session,
    headers, or browser-TLS-fingerprint impersonation (tested directly,
    2026-09-05), so this still cannot and will not succeed from CI or a
    genuine datacenter sandbox -- that is a network-origin fact, not a bug
    in this function.

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


def duplicates(*, snapshot_dir: Path | None = None, write: bool = False) -> int:
    """Phase 1 Stage A candidates for the works in the served snapshot. Prints the counts and
    writes nothing unless `write` is set; with it, only duplicate_candidates.json is written,
    so no score, rank or flag can move.
    """
    try:
        artifact = duplicate_candidates_from_snapshot(snapshot_dir)
        path = write_duplicate_candidates(artifact, snapshot_dir) if write else None
    except (OSError, SnapshotWriteError, DuplicateCandidateValidationError) as exc:
        logger.error("Duplicate candidates were not written: %s", exc)
        return 1
    print(json.dumps(artifact["meta"]["counts"], indent=2))
    if path is None:
        print("Dry run: nothing was written. Add --write to write duplicate_candidates.json.")
    else:
        print(f"Wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")
    return 0


def early_warning(*, snapshot_dir: Path | None = None, write: bool = False) -> int:
    """Task 8: reads works.parquet and manifest.json's data_as_of from the served snapshot,
    builds the early-warning artifact (early_warning.build) and prints its metrics (never the
    watch list itself). Writes nothing unless `write` is set; with it, only early_warning.json
    is written, so no score, rank or flag can move.
    """
    snapshot_dir = snapshot_dir or SNAPSHOT_DIR
    try:
        works = pd.read_parquet(snapshot_dir / "works.parquet")
        manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
        as_of = pd.Timestamp(manifest["data_as_of"]).date()
        artifact = build_early_warning(works, as_of)
        path = write_early_warning(artifact, snapshot_dir) if write else None
    except (OSError, SnapshotWriteError, KeyError, ValueError) as exc:
        logger.error("Early warning was not written: %s", exc)
        return 1
    print(json.dumps({k: v for k, v in artifact.items() if k != "watch"}, indent=2))
    if path is None:
        print("Dry run: nothing was written. Add --write to write early_warning.json.")
    else:
        print(f"Wrote {path}")
    return 0


def judge(
    *,
    snapshot_dir: Path | None = None,
    out_dir: Path | None = None,
    model: str = runner.DEFAULT_MODEL,
    provider: str = runner.DEFAULT_PROVIDER,
    limit: int | None = None,
    max_usd: float | None = None,
    run: bool = False,
    workers: int = 1,
    transport: runner.Transport = runner.http_transport,
) -> int:
    """Phase 1 Stage B: ask the pinned model about the near-copy pairs that have no answer yet.

    Sends nothing unless `run` is set, and then only with HF_TOKEN in the environment and a
    dollar cap in `max_usd`.
    """
    if limit is not None and limit < 1:
        logger.error("--limit must be at least 1")
        return 1
    token = os.environ.get("HF_TOKEN", "")
    if run and not (token and max_usd and max_usd > 0):
        logger.error("--run needs HF_TOKEN in the environment and --max-usd above zero")
        return 1
    store_path = (out_dir or _APP_ROOT / "data" / "judgments") / store.FILENAME
    try:
        candidates = (snapshot_dir or SNAPSHOT_DIR) / "duplicate_candidates.json"
        artifact = json.loads(candidates.read_text(encoding="utf-8"))
        validate_duplicate_candidates(artifact)
        items = items_from_artifact(artifact)
        if not run:
            todo = runner.pending(items, store_path, model, provider, limit)
            print(f"{len(items)} near-copy pairs; {len(todo)} to judge with {model} on {provider}.")
            print("Dry run: nothing was sent. Add --run and --max-usd DOLLARS to send them.")
            return 0
        report = runner.run_judge(
            items,
            store_path=store_path,
            model_id=model,
            provider_id=provider,
            token=token,
            max_usd=max_usd,
            limit=limit,
            transport=transport,
            workers=workers,
        )
    except (OSError, ValueError, DuplicateCandidateValidationError, runner.JudgeError) as exc:
        logger.error("The judge did not finish: %s", exc)
        return 1
    print(json.dumps({**asdict(report), "cost_usd": round(report.cost_usd, 4)}, indent=2))
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
    duplicates_parser = subparsers.add_parser(
        "duplicates",
        help="Find identical and near-identical work descriptions in data/snapshot/works.parquet.",
    )
    duplicates_parser.add_argument(
        "--write", action="store_true", help="Write data/snapshot/duplicate_candidates.json."
    )
    early_warning_parser = subparsers.add_parser(
        "early-warning",
        help="Rank recently sanctioned works under implementation by risk of staying open "
        "past one year.",
    )
    early_warning_parser.add_argument(
        "--write", action="store_true", help="Write data/snapshot/early_warning.json."
    )
    judge_parser = subparsers.add_parser(
        "judge",
        help="Ask the pinned model about the near-copy pairs in duplicate_candidates.json.",
    )
    judge_parser.add_argument(
        "--run",
        action="store_true",
        help="Send the requests. Needs HF_TOKEN in the environment and --max-usd.",
    )
    judge_parser.add_argument("--max-usd", type=float, help="Stop once this much has been spent.")
    judge_parser.add_argument(
        "--limit", type=int, help="Judge only this many pairs, spread evenly through the pending."
    )
    judge_parser.add_argument("--model", default=runner.DEFAULT_MODEL)
    judge_parser.add_argument("--provider", default=runner.DEFAULT_PROVIDER)
    judge_parser.add_argument("--workers", type=int, default=1, help="Requests sent at once.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.command == "build":
        return build()
    if args.command == "pull-live":
        return pull_live()
    if args.command == "duplicates":
        return duplicates(write=args.write)
    if args.command == "early-warning":
        return early_warning(write=args.write)
    if args.command == "judge":
        return judge(
            model=args.model,
            provider=args.provider,
            limit=args.limit,
            max_usd=args.max_usd,
            run=args.run,
            workers=args.workers,
        )

    parser.error(f"unknown command {args.command!r}")
    return 2  # pragma: no cover - argparse.error() exits before this


if __name__ == "__main__":
    raise SystemExit(main())
