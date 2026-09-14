"""Maps live MPLADS dashboard responses into contracts/normalized_record.schema.json shape.

The dashboard's `getTilesReportData` endpoint returns one tile per call, and
no single tile carries every field the schema needs. Three are joined here
on `WORK_RECOMMENDATION_DTL_ID`, which is unique and non-null in all of
them:

  Works Sanctioned  -> the spine. One row per sanctioned work, carrying
                       state, constituency, MP, agency, sanctioned amount,
                       sanction date and work stage.
  Works Completed   -> a subset of the same works, used only to decide
                       completion_status. Do NOT infer completion from the
                       spine's WORK_STAGE alone: that column marks just
                       4,207 works "Work Completed" while this tile lists
                       34,258, so WORK_STAGE under-reports completion by
                       8x and using it would push 30,051 finished works
                       into the inspection queue.
  Expenditure       -> one row per *payment event*, not per work, so a work
                       appears once per disbursement. Aggregated here into
                       a per-work total and one observed vendor ID/name
                       pair. This is the only tile carrying VENDOR_ID and
                       VENDOR_NAME, which is why the fund-flow graph depends
                       on this join.

Call signature for all three (corrected 2026-09-04; the earlier reading of
poptable.js had `combo` as an int, which is why every probe returned
`Total_Amt: 0.0`):

    POST /rest/PreLoginDashboardData/getTilesReportData
    Content-Type: application/json; charset=UTF-8
    body: {"combo": "0,0,0,2", "key": "<tile name>"}

`combo` is a comma-separated string, not an integer.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

# ingest/mplads_adapter.py -> parents[4] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RAW_DIR = _APP_ROOT / "data" / "raw"

SANCTIONED_FILE = "mplads-sanctioned.json"
COMPLETED_FILE = "mplads-completed.json"
EXPENDITURE_FILE = "mplads-expenditure-salvaged.json"

MPLADS_SOURCE_RUNG = 1


class MpladsAdapterError(Exception):
    """Raised when a source file is missing, unparseable, or so misshapen
    that emitting records from it would be guesswork.
    """


# --------------------------------------------------------------------------
# Activity -> work_category
# --------------------------------------------------------------------------

# normalized_record.schema.json fixes work_category to seven values. MPLADS
# publishes 112 distinct activity strings and a WORK_CATEGORY column that is
# useless for this purpose ("Normal/Others" on 98% of rows), so the activity
# string is what gets mapped.
#
# Ordered most-specific-first and matched on the first hit: "purchase of
# vans and buses for educational institutions" has to reach the School rule
# before the Road rule sees "road" nowhere but a laxer rule might catch it,
# and "construction of veterinary hospitals" has to reach Health before
# Community Infrastructure's catch-all. Ordering is the whole mechanism, so
# do not sort this list.
#
# The residual honesty problem, stated rather than hidden: MPLADS funds
# categories this schema has no bucket for (agriculture, fisheries, animal
# husbandry, disaster warning). They land in Community Infrastructure as the
# least-wrong option. That is a real limitation of the frozen seven-value
# enum, not a mapping bug, and it means peer groups for those works compare
# them against community buildings. Recorded in the Logbook for CP2.
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    # Health before everything: "veterinary hospital", "mobile dispensaries",
    # and the assistive-devices line all contain words other rules would
    # otherwise claim.
    (
        "Health",
        (
            "hospital",
            "dispensar",
            "phc ",
            "fwc",
            "anm",
            "ambulance",
            "prosthetic",
            "wheel chair",
            "wheelchair",
            "hearing aid",
            "differently abled",
            "veterinary",
            "semen",
            "insemination",
            "medical",
            "sick and injured animals",
            "clinics for animals",
        ),
    ),
    # School before Community: library/anganwadi/creche buildings are
    # buildings, and the catch-all would swallow them.
    (
        "School",
        (
            "school",
            "college",
            "librar",
            "book",
            "anganwad",
            "crèche",
            "creche",
            "educational",
            "laborator",
            "training equipment",
            "training institution",
            "smart board",
            "visual display",
            "farmers’ training",
            "farmers' training",
        ),
    ),
    # Protective/heritage works, claimed explicitly and before Road, for one
    # activity: "flood control embankments/ protection walls along
    # riverbanks, hilltops, roadsides" (506 works). It contains "roadsides",
    # so Road would take it, and it previously matched Drinking Water on
    # "flood control" -- neither is right. A flood embankment is protective
    # community infrastructure. Explicit rather than left to the fallback so
    # the reasoning is visible at the point of decision.
    (
        "Community Infrastructure",
        (
            "flood control",
            "embankment",
            "protection wall",
            "retrofitting",
            "heritage",
            "archaeological",
            "early warning",
            "anti-pollution",
        ),
    ),
    # Road above Sanitation, deliberately. The single largest activity in
    # the dataset -- "Construction of roads, link roads, pathways or any
    # other road with or without drainage system", 18,248 works -- contains
    # "drainage", so a Sanitation rule matching "drain" that ran first
    # classified 23% of every work in the country as sanitation. Caught by
    # checking the category distribution against the raw activity counts
    # rather than trusting the rules read correctly (2026-09-04).
    (
        "Road",
        (
            "road",
            "pathway",
            "footpath",
            "culvert",
            "bridge",
            "cycle track",
            "cycle stand",
            "non-motorized",
            "staircase",
            "stair ghat",
            "railway station",
            "railway crossing",
            "escalator",
            "travellator",
            "passenger shed",
            "bus-shed",
            "bus-stop",
            "bus shed",
        ),
    ),
    # Sanitation before Drinking Water: "night soil collection" and
    # "effluent treatment" are water-adjacent but are waste, not supply.
    (
        "Sanitation",
        (
            "toilet",
            "bathroom",
            "drain",
            "gutter",
            "sewer",
            "garbage",
            "effluent",
            "sanitary",
            "sanitation",
            "biodigester",
            "night soil",
            "incinerator",
        ),
    ),
    (
        "Drinking Water",
        (
            "drinking water",
            "tube-well",
            "tubewell",
            "borewell",
            "bore well",
            "hand pump",
            "handpump",
            "water tanker",
            "water tank",
            "water plant",
            "supply pipeline",
            "rainwater",
            "rain water",
            "irrigation",
            "pond",
            "lake",
            "ground water",
            "reef",
            "motor boats",
        ),
    ),
    (
        "Electricity",
        (
            "light",
            "electricity",
            "electric vehicle",
            "energy",
            "solar",
            "wi-fi",
            "charging station",
        ),
    ),
]

CATEGORY_FALLBACK = "Community Infrastructure"

VALID_CATEGORIES = frozenset(
    {
        "Road",
        "Drinking Water",
        "School",
        "Health",
        "Community Infrastructure",
        "Electricity",
        "Sanitation",
    }
)

# Sanctioned/Completed embed the activity behind a reference prefix:
#   "WS/\t MP620/2024-2025/133166-Construction of buildings for ..."
# The Expenditure tile carries the bare activity with no prefix, so callers
# must tolerate both. Anchored on the numeric work id followed by "-" so the
# hyphen inside "2024-2025" cannot end the match early.
_ACTIVITY_PREFIX = re.compile(r"^WS/\s*MP\d+/\d{4}-\d{4}/\d+-(.+)$", re.DOTALL)


def activity_of(activity_name: str | None) -> str:
    """The bare activity string, prefix stripped when one is present."""
    if not activity_name:
        return ""
    stripped = activity_name.strip()
    match = _ACTIVITY_PREFIX.match(stripped)
    return (match.group(1) if match else stripped).strip()


def category_for(activity_name: str | None) -> str:
    """Maps an MPLADS activity string onto one of the schema's seven
    categories. Never raises and never returns anything outside the enum:
    an unrecognised activity falls to Community Infrastructure rather than
    failing the whole batch, because a single new activity string appearing
    upstream must not be able to take the pipeline down.
    """
    haystack = activity_of(activity_name).lower()
    if not haystack:
        return CATEGORY_FALLBACK
    for category, needles in _CATEGORY_RULES:
        if any(needle in haystack for needle in needles):
            return category
    return CATEGORY_FALLBACK


# --------------------------------------------------------------------------
# Field-level helpers
# --------------------------------------------------------------------------

# WORK_STAGE values that mean the work is sanctioned but has not started.
# "Vendor Identification" and "Time Estimation" are procurement steps that
# happen before any ground work.
_NOT_STARTED_STAGES = frozenset({"Sanction", "Vendor Identification", "Time Estimation"})


def _parse_ddmmmyyyy(value: str | None) -> str | None:
    """'09-Jul-2024' -> '2024-07-09'. Returns None for the empty/NA cases
    rather than inventing a date -- normalized_record.schema.json marks
    sanction_date nullable precisely so a missing date stays missing.
    """
    if not value or value in {"NA", "-"}:
        return None
    try:
        return datetime.strptime(value.strip(), "%d-%b-%Y").date().isoformat()
    except ValueError:
        return None


def _tenure_range(start: Any, end: Any) -> str | None:
    """'Jun 4, 2024 12:00:00 AM' + 'Jun 3, 2029 11:59:59 PM' -> '2024-2029'.

    normalized_record.schema.json constrains tenure to `^[0-9]{4}-[0-9]{4}$`,
    so the source's own TENURE label ("18th Lok Sabha") cannot be used
    directly -- it is the Sabha number, not the year range the schema wants.
    The two tenure boundary timestamps carry the years, and every row in the
    live data has both.
    """
    years: list[str] = []
    for value in (start, end):
        text = _clean(value)
        if not text:
            return None
        match = re.search(r"\b(\d{4})\b", text)
        if not match:
            return None
        years.append(match.group(1))
    return f"{years[0]}-{years[1]}"


def _clean(value: Any) -> str | None:
    """Trims a source string and collapses the empty/NA cases to None.
    MPLADS pads several fields with tabs (LETTER_NO, ACTIVITY_NAME), which
    reach the UI as visible whitespace if not stripped here.
    """
    if value is None:
        return None
    text = str(value).replace("\t", " ").strip()
    text = re.sub(r"\s{2,}", " ", text)
    return text or None


def _number(value: Any) -> float:
    """Amount fields, coerced to a non-negative float. The schema sets
    `minimum: 0` on both amount fields, and a negative disbursement (which
    does appear upstream as a correction entry) would fail validation for
    the whole batch, so it is floored rather than dropped.
    """
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------
# Aggregation of the per-payment Expenditure tile
# --------------------------------------------------------------------------

# Only settled payments count toward expenditure_amount_inr. "Payment
# In-Progress" is committed but not yet disbursed, and counting it would
# overstate spend on exactly the works stalled_work exists to surface --
# a work whose money is stuck mid-disbursement is the case that detector
# should catch, not one it should be told is already spent.
_SETTLED_PAYMENT_STATUS = "Payment Success"


class _ExpenditureRollup:
    """Per-work totals, vendor and last activity date, rolled up from
    payment events.
    """

    __slots__ = (
        "total_inr",
        "vendor_counts",
        "vendor_ids_by_name",
        "last_activity",
    )

    def __init__(self) -> None:
        self.total_inr = 0.0
        self.vendor_counts: Counter[str] = Counter()
        self.vendor_ids_by_name: dict[str, Counter[str]] = defaultdict(Counter)
        # Latest EXPENDITURE_DATE seen for this work, ISO. Unlike the
        # amount, this counts in-progress payments too: a disbursement that
        # has been initiated is activity on the work, which is exactly what
        # "days since something last happened here" should reflect.
        self.last_activity: str | None = None

    def note_activity(self, iso_date: str | None) -> None:
        if iso_date and (self.last_activity is None or iso_date > self.last_activity):
            self.last_activity = iso_date

    def vendor(self) -> str | None:
        """The vendor paid on the most events for this work. A work can be
        paid across several vendors (a contractor plus a supplier); the
        schema has one vendor_name field, so the modal one is used and ties
        break alphabetically to keep the choice deterministic across runs.
        """
        if not self.vendor_counts:
            return None
        top = max(self.vendor_counts.values())
        return sorted(name for name, n in self.vendor_counts.items() if n == top)[0]

    def vendor_id(self) -> str | None:
        """The source ID observed with :meth:`vendor`'s selected name.

        Name and identifier cannot be selected from independent modal
        populations: ties can otherwise pair an ID from one payment event
        with a name from another, fabricating an identity the source never
        contained. The name rule stays exactly as before; within that
        name's real events, the modal ID wins and ties break lexically.
        """
        vendor = self.vendor()
        if vendor is None:
            return None
        counts = self.vendor_ids_by_name[vendor]
        if not counts:
            return None
        top = max(counts.values())
        return sorted(vendor_id for vendor_id, n in counts.items() if n == top)[0]


def rollup_expenditure(expenditure_rows: Iterable[dict[str, Any]]) -> dict[int, _ExpenditureRollup]:
    """work_id -> settled total and modal vendor. Rows whose payment has not
    settled still contribute their vendor (the vendor is real and identified
    even while the payment clears) but not their amount.
    """
    rollups: dict[int, _ExpenditureRollup] = defaultdict(_ExpenditureRollup)
    for row in expenditure_rows:
        work_id = row.get("WORK_RECOMMENDATION_DTL_ID")
        if work_id is None:
            continue
        rollup = rollups[work_id]
        vendor = _clean(row.get("VENDOR_NAME"))
        if vendor:
            rollup.vendor_counts[vendor] += 1
            vendor_id = _clean(row.get("VENDOR_ID"))
            if vendor_id:
                rollup.vendor_ids_by_name[vendor][vendor_id] += 1
        rollup.note_activity(_parse_ddmmmyyyy(row.get("EXPENDITURE_DATE")))
        if row.get("WORK_STATUS") == _SETTLED_PAYMENT_STATUS:
            rollup.total_inr += _number(row.get("FUND_DISBURSED_AMT"))
    return dict(rollups)


# --------------------------------------------------------------------------
# The adapter
# --------------------------------------------------------------------------


def adapt(
    sanctioned_rows: Iterable[dict[str, Any]],
    completed_rows: Iterable[dict[str, Any]],
    expenditure_rows: Iterable[dict[str, Any]],
    *,
    as_of: date | None = None,
) -> list[dict[str, Any]]:
    """Joins the three tiles into normalized_record.schema.json shape.

    Deliberately does NOT stamp source_rung or validate -- normalize.py owns
    both, and duplicating either here would give two places that decide what
    a valid record is. This returns raw-shaped dicts using the schema's own
    field names, which is exactly what normalize_records() expects to be
    handed by a rung.

    `as_of` becomes every record's last_updated. It is a property of the
    snapshot (when this data was pulled), not of the individual work: MPLADS
    publishes no per-work modification timestamp on these tiles, and
    fabricating one per row would put a number on screen that nothing
    upstream actually said.
    """
    as_of = as_of or datetime.now().date()
    last_updated = as_of.isoformat()

    completed_ids = {
        row.get("WORK_RECOMMENDATION_DTL_ID")
        for row in completed_rows
        if row.get("WORK_RECOMMENDATION_DTL_ID") is not None
    }
    rollups = rollup_expenditure(expenditure_rows)

    records: list[dict[str, Any]] = []
    for row in sanctioned_rows:
        work_id = row.get("WORK_RECOMMENDATION_DTL_ID")
        if work_id is None:
            # No stable identity -> no record. Silently dropping would hide
            # an upstream shape change, so this is counted by the caller
            # (see load_and_adapt's dropped tally).
            continue

        rollup = rollups.get(work_id)
        stage = _clean(row.get("WORK_STAGE"))

        if work_id in completed_ids:
            status = "Completed"
        elif stage in _NOT_STARTED_STAGES:
            status = "Sanctioned"
        else:
            # "Physical Inspection" and "Work partially Completed" both mean
            # ground work is underway. An unrecognised future stage also
            # lands here: a work that is sanctioned, not listed complete and
            # not in a known pre-start stage is in progress by elimination.
            status = "In Progress"

        records.append(
            {
                "work_id": str(work_id),
                "state": _clean(row.get("STATE_NAME")),
                "constituency": _clean(row.get("CONSTITUENCY")),
                "mp_name": _clean(row.get("MP_NAME")),
                "tenure": _tenure_range(row.get("TENURE_START_DATE"), row.get("TENURE_END_DATE")),
                "implementing_agency": _clean(row.get("IDA_NAME")),
                "vendor_id": rollup.vendor_id() if rollup else None,
                "vendor_name": rollup.vendor() if rollup else None,
                "work_category": category_for(row.get("ACTIVITY_NAME")),
                "sanctioned_amount_inr": _number(row.get("SANCTION_AMOUNT")),
                "expenditure_amount_inr": rollup.total_inr if rollup else 0.0,
                "sanction_date": _parse_ddmmmyyyy(row.get("SANCTION_DATE")),
                "completion_status": status,
                # The most recent thing known to have happened to this work:
                # its latest payment event, falling back to its sanction date
                # when no money has moved yet. NOT the snapshot date -- that
                # was the first version, and it made every record equally
                # fresh, which rendered the Days stale column all zeros and
                # gave stalled_work's no-update fallback nothing to measure.
                # MPLADS publishes no per-work modification timestamp, so
                # payment activity is the truest available proxy, and a work
                # with no payments since sanction is precisely the case the
                # stalled_work detector exists to surface.
                "last_updated": (
                    (rollup.last_activity if rollup else None)
                    or _parse_ddmmmyyyy(row.get("SANCTION_DATE"))
                    or last_updated
                ),
            }
        )
    return records


# --------------------------------------------------------------------------
# Loading the cached tiles
# --------------------------------------------------------------------------


def _unwrap(payload: Any) -> list[dict[str, Any]]:
    """Accepts either shape the cached files come in.

    getTilesReportData returns {"<Tile Label>": "<json string>"} -- a JSON
    document whose single value is itself a JSON *string* that has to be
    decoded a second time. Some cached files were saved already unwrapped
    as a plain list. Both are handled so a re-pull does not have to be
    normalised by hand before use.

    The final element of the decoded list is a {"Total_Amt": ...} summary
    row rather than a work, and is dropped.
    """
    if isinstance(payload, dict):
        if len(payload) != 1:
            raise MpladsAdapterError(
                f"expected a single-key tile wrapper, got keys {sorted(payload)}"
            )
        inner = next(iter(payload.values()))
        payload = json.loads(inner) if isinstance(inner, str) else inner
    if not isinstance(payload, list):
        raise MpladsAdapterError(f"expected a list of rows, got {type(payload).__name__}")
    return [row for row in payload if isinstance(row, dict) and "Total_Amt" not in row]


def _read_tile(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise MpladsAdapterError(
            f"cached MPLADS tile missing at {path}. Re-pull it with a live "
            'getTilesReportData call ({"combo": "0,0,0,2", "key": "<tile>"}) '
            "and a fresh JSESSIONID; see this module's docstring."
        )
    try:
        return _unwrap(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise MpladsAdapterError(
            f"{path.name} is not valid JSON: {exc}. The Expenditure tile in "
            "particular is truncated mid-record by the server at national "
            "scale -- use the salvaged file, not the raw one."
        ) from exc


def load_and_adapt(
    raw_dir: Path | None = None, *, as_of: date | None = None
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Reads the three cached tiles and returns (records, counts).

    `counts` reports what each tile contributed, so a caller can log real
    numbers rather than asserting a pull "worked". Sanctioned is required;
    Completed and Expenditure are not, and their absence degrades specific
    fields rather than failing the build: without Completed every finished
    work is reported In Progress, and without Expenditure every work shows
    zero spend and no vendor. Both are stated in the returned counts so the
    degradation is visible instead of silent.
    """
    raw_dir = raw_dir or DEFAULT_RAW_DIR

    sanctioned = _read_tile(raw_dir / SANCTIONED_FILE)

    completed: list[dict[str, Any]] = []
    expenditure: list[dict[str, Any]] = []
    for filename, sink in ((COMPLETED_FILE, "completed"), (EXPENDITURE_FILE, "expenditure")):
        path = raw_dir / filename
        if path.exists():
            rows = _read_tile(path)
            if sink == "completed":
                completed = rows
            else:
                expenditure = rows

    records = adapt(sanctioned, completed, expenditure, as_of=as_of)
    counts = {
        "sanctioned_rows": len(sanctioned),
        "completed_rows": len(completed),
        "expenditure_rows": len(expenditure),
        "records": len(records),
        "dropped_no_work_id": len(sanctioned) - len(records),
    }
    return records, counts


__all__ = [
    "CATEGORY_FALLBACK",
    "MPLADS_SOURCE_RUNG",
    "MpladsAdapterError",
    "VALID_CATEGORIES",
    "activity_of",
    "adapt",
    "category_for",
    "load_and_adapt",
    "rollup_expenditure",
]
