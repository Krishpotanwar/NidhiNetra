"""Builds the combined "current snapshot" the API (A4) reads: normalized
records, risk-scored records, and the fund-flow graph, joined and written
to data/snapshot/ for FastAPI + DuckDB to serve straight off disk.

Owned by A4. Nothing else in this codebase yet produces this join --
normalize/normalize.py and risk/engine.py each produce one half of the
contract, and A3's graph/build_graph.py produces the third piece, but
nobody assembles them into the single artifact api/db.py's DuckDB views
expect at data/snapshot/{works,scored}.parquet.

Source selection, corrected 2026-09-04: `build_snapshot()` prefers the most
recent cached acquisition-ladder snapshot in data/raw/ and falls back to
contracts/fixtures/works.fixture.json only when there is none. It previously
read the fixture unconditionally with rung 5 hardcoded into both
normalize_records() and manifest.source. That was invisible while rung 1 was
blocked and every path led to the fixture anyway -- but the moment rung 1
went live, `cli build` wrote 79,068 real records to data/raw/ and this
module cheerfully rebuilt the snapshot from the 20-row fixture regardless,
reporting "cp0_fixtures" while the API served demo data the operator
believed was live. Provenance (rung and label) is now read off the data
rather than assumed, so the UI's "Demo dataset" banner tracks what is
actually loaded.

Either way the records go through the *real* `normalize_records()` rather
than a hand-copy of its output, so validation happens on every build
regardless of which source won.

Every artifact (works.parquet, scored.parquet, graph.json, manifest.json)
follows the same stage/validate/commit discipline as ingest/cache.py's
write_snapshot(): serialize to a temp file in the target directory, read
it back to confirm it landed intact, only then rename it into place. Since
2026-09-02 this happens as one batch, not four independent ones: every
artifact is staged and validated FIRST, and only if all four succeed does
build_snapshot() commit (rename) any of them. A failure partway through a
single-file write always left that one file's OLD version in place; the
earlier per-file-only version of this discipline still let an EARLIER
artifact in the same build get committed while a LATER one failed
validation, producing an internally inconsistent snapshot (new
works.parquet paired with an old graph.json). Batching the commits closes
that gap. Full directory-level atomicity (one rename swapping a whole
staging directory into place) would close the remaining small window
between individual commits too, but is a larger restructure this fix
does not attempt -- see build_snapshot()'s own comment for the honest
accounting of what is and isn't covered.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .ingest import cache
from .normalize.normalize import normalize_records
from .risk.engine import score_all

# A3's module in parallel: this file is written before graph/build_graph.py
# is guaranteed to exist. Import it defensively -- if it is not there yet
# (or not yet exporting build_fund_flow_graph), fall back to the frozen
# graph fixture below. The moment A3's module lands, this import starts
# succeeding and build_snapshot() automatically switches to real graph
# output with no code change here.
try:
    from .graph.build_graph import build_fund_flow_graph
except ImportError:  # pragma: no cover - exercised only pre-A3
    build_fund_flow_graph = None  # type: ignore[assignment]

# pipeline/src/nidhinetra_pipeline/build_snapshot.py -> parents[3] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_DIR = _APP_ROOT / "contracts"
WORKS_FIXTURE_PATH = CONTRACTS_DIR / "fixtures" / "works.fixture.json"
GRAPH_FIXTURE_PATH = CONTRACTS_DIR / "fixtures" / "graph.fixture.json"
SNAPSHOT_DIR = _APP_ROOT / "data" / "snapshot"


def _schema_columns(schema_filename: str) -> list[str]:
    """Column order for pd.DataFrame(..., columns=...), read from the frozen
    schema rather than hardcoded -- the same "schema is the single source
    of truth" discipline contracts/validate.py and every A1/A2/A3 validator
    already follows. Passing `columns=` explicitly (not left to pandas to
    infer from row dicts) is the actual fix below: pd.DataFrame([]) with no
    columns= produces a zero-column frame, so scored_df['flags'] raises
    KeyError on an empty result set -- found live, 2026-09-02, testing the
    zero-results path CP5/CP6 both call for. Explicit columns= makes an
    empty DataFrame still have the right (empty) columns to select.
    """
    schema = json.loads((CONTRACTS_DIR / schema_filename).read_text(encoding="utf-8"))
    return list(schema["properties"].keys())


def _nullable_string_columns(schema_filename: str) -> list[str]:
    """Columns whose schema type is `["string", "null"]` -- these need an
    explicit pandas nullable dtype before the parquet write (see
    _NULLABLE_STRING_COLUMNS' docstring for why), derived from the frozen
    schema rather than hardcoded so a future field addition can't silently
    fall through this fix the way it fell through in the first place.
    """
    schema = json.loads((CONTRACTS_DIR / schema_filename).read_text(encoding="utf-8"))
    return [
        name
        for name, prop in schema["properties"].items()
        if isinstance(prop.get("type"), list) and "null" in prop["type"] and "string" in prop["type"]
    ]


_NORMALIZED_COLUMNS = _schema_columns("normalized_record.schema.json")
_SCORED_COLUMNS = _schema_columns("risk_scored_record.schema.json")

# implementing_agency, vendor_name, sanction_date. A distinct bug from the
# empty-DataFrame one above, found by the same 2026-09-02 test pass:
# constructing works_df from a list of dicts containing Python `None` for
# these columns is fine going IN, but pandas' default object-dtype
# round-trip through parquet can come back out as the float `NaN` rather
# than `None` -- valid for pandas, invalid against
# normalized_record.schema.json's `["string", "null"]`, and not valid JSON
# at all (json.dumps(float('nan')) emits the non-standard `NaN` token).
# The live API was not actually affected (db.py reads through DuckDB's SQL
# NULL handling, which maps correctly), which is exactly why this stayed
# invisible until a test read works.parquet back with plain pandas -- the
# most obvious tool for a parquet file, and something a future consumer of
# this artifact could reasonably do without going through DuckDB at all.
# Casting to pandas' "string" extension dtype (pd.NA-based, not NaN-based)
# before the write is the standard fix for this exact quirk.
_NULLABLE_STRING_COLUMNS = _nullable_string_columns("normalized_record.schema.json")

# Matches pipeline/src/nidhinetra_pipeline/cli.py's FIXTURE_SOURCE_RUNG:
# rung 5, the labelled hand-curated seed set (Execution Plan section 2).
FIXTURE_SOURCE_RUNG = 5
SOURCE_LABEL = "cp0_fixtures"

# manifest.source, per acquisition rung (Execution Plan section 2). This
# string is what the UI's data-provenance banner keys off to decide whether
# to show "Demo dataset. Not live MPLADS data." -- so it has to name the
# real provenance, not a generic "live". Rungs 2-4 are listed for when they
# are built; an unknown rung falls back to a generic label rather than
# claiming a source it cannot substantiate.
_SOURCE_LABELS = {
    1: "mplads_live_api",
    2: "mplads_playwright_scrape",
    3: "empowered_indian_mirror",
    4: "data_gov_in",
    5: SOURCE_LABEL,
}

# scored_records columns whose pandas/pyarrow-inferred parquet type is not
# trustworthy, for two independent reasons:
#
# - why_flagged is a dict with a *different key set per row* (one key per
#   fired flag, and which flags fire varies record to record). Writing that
#   straight through pyarrow does not error -- it infers a struct type from
#   the union of every key it sees across the whole column, then pads every
#   row with the keys it personally lacks, as an explicit null. That is
#   silent corruption here: risk_scored_record.schema.json requires
#   why_flagged to carry exactly one key per entry in flags, and null is
#   not the `string, minLength: 1` the schema demands.
# - flags and peer_group are typed from whatever data happens to be in
#   *this* snapshot. With the CP0 fixtures every peer group is below the
#   eng-review floor of 30 (engine.py), so every record's flags is `[]` and
#   every peer_group is `None` -- an all-empty / all-null column gives
#   pyarrow nothing to infer a real element type from, and it has been
#   observed to fall back to INTEGER / INTEGER[] instead of VARCHAR(-ish).
#   A future rebuild with real, non-empty data would self-heal (pyarrow
#   would see actual strings and infer correctly), but that means the
#   column's on-disk type would silently depend on today's data shape
#   rather than the contract -- not something to leave load-bearing.
#
# JSON-encoding all three as text sidesteps type inference entirely,
# round-trips byte-for-byte, and gives every snapshot the same on-disk
# shape regardless of how much data is in it. The API layer (db.py)
# decodes them back to real lists/dicts on read.
_JSON_ENCODED_SCORED_COLUMNS = ("flags", "why_flagged", "peer_group")


class SnapshotWriteError(Exception):
    """Raised when a snapshot artifact (parquet or JSON) cannot be safely
    written. Mirrors ingest/cache.py's CacheWriteError: the caller's
    previous good snapshot is guaranteed untouched when this is raised,
    because the failure is always caught before the atomic rename.
    """


class SnapshotDowngradeError(SnapshotWriteError):
    """Raised when a rebuild would silently replace a better-provenance
    snapshot with a worse one -- eng review finding, 2026-09-05: data/raw/
    is gitignored (single-disk), data/snapshot/*.parquet is committed, so a
    second machine (a teammate's clone, a backup laptop, or specifically the
    second-person dry run NEXT-STEPS.md asks for) boots correctly on the
    real snapshot right up until someone clicks Refresh -- which used to
    call this function unconditionally, falling back to the 20-row CP0
    fixture the moment that machine's data/raw/ had nothing cached, and
    silently overwriting the real snapshot with demo data. Pass
    `force=True` to rebuild anyway (used by the CLI when a genuine downgrade
    is intended, e.g. deliberately reverting to fixtures for a screenshot).
    """


def _rung_from_label(label: str) -> int | None:
    """Reverses _SOURCE_LABELS. None for a label this build never produced
    (a legacy or hand-edited manifest), which the caller treats as "unknown
    provenance, cannot compare" rather than as a specific rung number.
    """
    for rung, candidate in _SOURCE_LABELS.items():
        if candidate == label:
            return rung
    return None


def _utc_timestamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cache_pull_timestamp(path: Path) -> str | None:
    """ingest/cache.py names its files '<YYYYMMDDTHHMMSSZ>.json' -- the UTC
    instant that pull landed. Re-rendered here into the manifest's
    '%Y-%m-%dT%H:%M:%SZ' form so data_as_of reports when the data was
    *acquired* rather than when this rebuild ran. Returns None for a
    filename that does not parse, so a hand-dropped file in data/raw/ makes
    data_as_of fall back rather than crash the build.
    """
    try:
        return _utc_timestamp(
            datetime.strptime(path.stem, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        )
    except ValueError:
        return None


def _load_raw_records(
    raw_dir: Path | None = None,
) -> tuple[list[dict[str, Any]], int, str, str | None]:
    """Returns (records, source_rung, source_label, data_as_of).

    Prefers the most recent cached acquisition-ladder snapshot in data/raw/
    over the CP0 fixtures. Before 2026-09-04 this read the fixture
    unconditionally with rung 5 hardcoded, which meant a successful `cli
    build` writing 79,068 real rung-1 records to data/raw/ had no effect on
    what the API served -- the snapshot silently rebuilt itself from the
    20-row fixture every time. Rung 1 going live is what surfaced it.

    The cached file is already normalized (cli.py runs normalize_records
    before caching), so its records carry their own source_rung and it must
    not be re-stamped here. The rung is read back off the records rather
    than assumed, and a cache whose rows disagree about it is treated as
    corrupt rather than silently taking the first value.
    """
    cached = cache.latest_good(raw_dir)
    if cached is not None:
        records = json.loads(cached.read_text(encoding="utf-8"))
        if records:
            rungs = {r.get("source_rung") for r in records}
            if len(rungs) != 1 or None in rungs:
                raise SnapshotWriteError(
                    f"cached snapshot {cached.name} has inconsistent "
                    f"source_rung values {sorted(r for r in rungs if r is not None)}; "
                    "refusing to build a snapshot whose provenance cannot be "
                    "stated in one number"
                )
            rung = rungs.pop()
            return (
                records,
                rung,
                _SOURCE_LABELS.get(rung, f"acquisition_rung{rung}"),
                _cache_pull_timestamp(cached),
            )
    if not WORKS_FIXTURE_PATH.exists():
        raise SnapshotWriteError(
            f"no cached snapshot in {raw_dir or cache.default_raw_dir()} and no fixture "
            f"at {WORKS_FIXTURE_PATH}; cannot build a snapshot from either path"
        )
    return (
        json.loads(WORKS_FIXTURE_PATH.read_text(encoding="utf-8")),
        FIXTURE_SOURCE_RUNG,
        SOURCE_LABEL,
        None,
    )


def _build_graph(
    normalized: list[dict[str, Any]], scored: list[dict[str, Any]]
) -> dict[str, Any]:
    if build_fund_flow_graph is not None:
        return build_fund_flow_graph(normalized, scored)

    # Pre-A3 fallback. graph/build_graph.py does not exist yet (or does
    # not yet export build_fund_flow_graph), so serve the frozen
    # contracts/fixtures/graph.fixture.json directly instead of blocking
    # the whole snapshot on A3's parallel work.
    if not GRAPH_FIXTURE_PATH.exists():
        raise SnapshotWriteError(
            f"graph fixture missing at {GRAPH_FIXTURE_PATH} and "
            "nidhinetra_pipeline.graph.build_graph is not importable yet; "
            "cannot produce data/snapshot/graph.json by either path"
        )
    return json.loads(GRAPH_FIXTURE_PATH.read_text(encoding="utf-8"))


def _stage_bytes(payload: bytes, final_path: Path) -> Path:
    """Write `payload` to a temp file next to `final_path`, fsync, and read
    it back to confirm it landed intact -- ingest/cache.py's discipline,
    but split into stage/commit (see the module docstring's "group
    atomicity" note): this function does NOT rename. It returns the
    validated temp path so the caller can commit it later, after every
    other artifact in the same snapshot has also been staged successfully.
    Raises SnapshotWriteError and cleans up the temp file on any failure.
    """
    final_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=final_path.parent, prefix=f".{final_path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)

    try:
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise SnapshotWriteError(
                f"write of {final_path.name} was interrupted before it "
                f"could be safely persisted: {exc}"
            ) from exc

        try:
            reloaded = tmp_path.read_bytes()
        except OSError as exc:
            raise SnapshotWriteError(
                f"{final_path.name} could not be read back after writing, "
                f"refusing to swap: {exc}"
            ) from exc
        if reloaded != payload:
            raise SnapshotWriteError(
                f"{final_path.name} did not round-trip cleanly, refusing to swap"
            )
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return tmp_path


def _stage_json(obj: Any, final_path: Path) -> Path:
    payload = json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")
    return _stage_bytes(payload, final_path)


def _stage_parquet(df: pd.DataFrame, final_path: Path) -> Path:
    """Parquet counterpart to `_stage_bytes`: parquet bytes can't be
    byte-compared after a round trip the way JSON text can (pyarrow is free
    to reorder internal metadata), so "validate by reading it back" here
    means re-reading the temp file as a DataFrame and confirming its shape
    and columns match what was written. Does not rename; see `_stage_bytes`.
    """
    final_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=final_path.parent, prefix=f".{final_path.name}.", suffix=".tmp"
    )
    os.close(fd)
    tmp_path = Path(tmp_name)

    try:
        try:
            df.to_parquet(tmp_path, engine="pyarrow", index=False)
        except Exception as exc:
            raise SnapshotWriteError(
                f"write of {final_path.name} failed: {exc}"
            ) from exc

        try:
            reloaded = pd.read_parquet(tmp_path, engine="pyarrow")
        except Exception as exc:
            raise SnapshotWriteError(
                f"{final_path.name} produced an unreadable parquet file, "
                f"refusing to swap: {exc}"
            ) from exc
        if len(reloaded) != len(df) or list(reloaded.columns) != list(df.columns):
            raise SnapshotWriteError(
                f"{final_path.name} did not round-trip cleanly (shape or "
                "columns changed), refusing to swap"
            )
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return tmp_path


def _commit_staged(tmp_path: Path, final_path: Path) -> None:
    """The rename half of stage/commit. By the time this is called every
    artifact in the snapshot has already been staged and validated, so this
    is the only part of the whole build that can still fail after real work
    has been done -- and a rename failing partway through a batch is the
    residual risk the group-atomicity note below is honest about, not
    something this function can eliminate on its own.
    """
    try:
        os.rename(tmp_path, final_path)
    except OSError as exc:
        raise SnapshotWriteError(
            f"could not atomically swap {final_path.name} into place: {exc}"
        ) from exc


def build_snapshot(
    *,
    snapshot_dir: Path | None = None,
    raw_dir: Path | None = None,
    now: datetime | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Runs fixture-read -> normalize_records() -> score_all() -> graph,
    writes works.parquet, scored.parquet, graph.json and manifest.json to
    `snapshot_dir` (default data/snapshot/), and returns the manifest dict.

    `now` is accepted (rather than always calling datetime.now()) so tests
    and callers can pin a reference time; it also becomes the `as_of` date
    passed to score_all(), matching score_all's own advice to pass an
    explicit as_of for reproducible output within a single build.

    Raises SnapshotDowngradeError (before anything is staged or written) if
    a manifest.json already exists in `snapshot_dir` and the rung this call
    resolved to is numerically worse than that manifest's -- unless
    `force=True`. See SnapshotDowngradeError's docstring for why this
    check exists.
    """
    snapshot_dir = snapshot_dir or SNAPSHOT_DIR
    now = now or datetime.now(timezone.utc)
    as_of: date = now.astimezone(timezone.utc).date()

    raw_records, source_rung, source_label, data_as_of = _load_raw_records(raw_dir)

    if not force:
        existing_manifest_path = snapshot_dir / "manifest.json"
        if existing_manifest_path.exists():
            try:
                existing_source = json.loads(
                    existing_manifest_path.read_text(encoding="utf-8")
                ).get("source")
            except (json.JSONDecodeError, OSError):
                existing_source = None
            existing_rung = _rung_from_label(existing_source) if existing_source else None
            # existing_rung is None for a first-ever build (no prior manifest
            # to protect) or an unrecognised label (nothing to compare
            # against) -- both fall through to "not a downgrade" rather than
            # blocking a build that has nothing to compare against.
            if existing_rung is not None and source_rung > existing_rung:
                raise SnapshotDowngradeError(
                    f"refusing to rebuild: resolved source is {source_label!r} "
                    f"(rung {source_rung}), which is worse than the current "
                    f"snapshot's {existing_source!r} (rung {existing_rung}). "
                    "Pass force=True to rebuild anyway."
                )
    # Idempotent by design: normalize_records re-stamps source_rung with the
    # value the loader reported, so a cached (already-normalized) batch keeps
    # the rung it was acquired at and a fixture batch gets rung 5. Running it
    # over already-normalized records is a validation pass, which is worth
    # doing on every build rather than trusting the cache file's contents.
    normalized = normalize_records(raw_records, source_rung=source_rung)
    scored = score_all(normalized, as_of=as_of)
    graph = _build_graph(normalized, scored)

    # columns= explicit, not inferred from row dicts -- see _schema_columns'
    # docstring for the empty-input crash this fixes.
    works_df = pd.DataFrame(normalized, columns=_NORMALIZED_COLUMNS)
    # pd.NA-based "string" dtype, not the default object/NaN dtype -- see
    # _NULLABLE_STRING_COLUMNS' docstring for the None-becomes-NaN
    # round-trip bug this avoids. Skipped when the frame has zero rows:
    # pandas' StringDtype cast is a no-op on an already-empty column and
    # the column still needs to exist either way, which columns= above
    # already guarantees.
    for column in _NULLABLE_STRING_COLUMNS:
        works_df[column] = works_df[column].astype("string")
    scored_df = pd.DataFrame(scored, columns=_SCORED_COLUMNS)
    for column in _JSON_ENCODED_SCORED_COLUMNS:
        scored_df[column] = scored_df[column].apply(json.dumps)

    generated_at = _utc_timestamp(now)
    manifest = {
        "row_count": len(normalized),
        "generated_at": generated_at,
        # Names the acquisition rung this batch actually came from, rather
        # than the hardcoded "cp0_fixtures" it reported before 2026-09-04.
        # The UI's data-provenance banner keys off this: a snapshot built
        # from rung 5 must keep saying "Demo dataset. Not live MPLADS data."
        # and one built from rung 1 must stop saying it.
        "source": source_label,
        # data_as_of is the acquisition time when there is one to report:
        # the cached ladder snapshot's filename is a UTC timestamp of when
        # that pull landed, which is a truer "as of" for the data than the
        # moment this rebuild happened to run. Falls back to generated_at
        # for fixtures, which have no acquisition time of their own.
        "data_as_of": data_as_of or generated_at,
    }

    # Stage every artifact BEFORE committing any of them. This is the
    # group-atomicity fix (2026-09-02): the previous version validated and
    # renamed one file at a time, so a failure on (say) graph.json would
    # leave works.parquet and scored.parquet already swapped to the new
    # build while graph.json and manifest.json stayed on the old one --
    # a torn, internally-inconsistent snapshot, exactly what CP1's "a
    # partial pull must never replace a good snapshot" is about. Staging
    # all four first means a failure at any point still leaves every real
    # file in snapshot_dir completely untouched; only the temp files (which
    # nothing reads) are affected. The four commits at the end are still
    # four separate os.rename() calls, not one, so a crash between commit 1
    # and commit 4 remains a real (much smaller, metadata-only) residual
    # window -- true directory-level atomicity would need a staging
    # directory swapped in with a single rename, which is a larger
    # restructure than this fix scopes to. Documented, not hidden.
    targets = [
        (works_df, snapshot_dir / "works.parquet", _stage_parquet),
        (scored_df, snapshot_dir / "scored.parquet", _stage_parquet),
        (graph, snapshot_dir / "graph.json", _stage_json),
        (manifest, snapshot_dir / "manifest.json", _stage_json),
    ]

    staged: list[tuple[Path, Path]] = []
    try:
        for obj, final_path, stage_fn in targets:
            tmp_path = stage_fn(obj, final_path)
            staged.append((tmp_path, final_path))
    except Exception:
        for tmp_path, _final_path in staged:
            tmp_path.unlink(missing_ok=True)
        raise

    for tmp_path, final_path in staged:
        _commit_staged(tmp_path, final_path)

    return manifest


def main(argv: list[str] | None = None) -> int:  # noqa: ARG001 - CLI entry point
    manifest = build_snapshot()
    print(
        f"Wrote {manifest['row_count']} records to {SNAPSHOT_DIR} "
        f"(source={manifest['source']}, generated_at={manifest['generated_at']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SnapshotWriteError",
    "SNAPSHOT_DIR",
    "build_snapshot",
    "main",
]
