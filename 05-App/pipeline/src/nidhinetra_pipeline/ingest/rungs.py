"""The five-rung data acquisition fallback ladder (Execution Plan section 2).

`run_ladder()` tries each rung in order and stops at the first one that
returns data.

**Rung 1 is live as of 2026-09-04** and returns 79,068 real work-level
records. The structure held exactly as designed: unblocking it needed real
logic in `Rung1LiveApi` and nothing else -- `run_ladder()`, the `Rung`
interface and rungs 2-5 are untouched from when Rung 1 was still raising.
Rungs 2-4 remain deliberately unimplemented; they are for when Rung 1 is
confirmed *dead*, which it now demonstrably is not.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from .mplads_adapter import MpladsAdapterError, load_and_adapt
from .mplads_api import MpladsClient

logger = logging.getLogger(__name__)


class RungBlockedError(Exception):
    """A rung is known to work in principle but is blocked on a specific,
    named prerequisite (as opposed to `NotImplementedError`, which means the
    rung's logic has not been written yet at all).
    """


class AllRungsFailedError(Exception):
    """Every rung in the ladder was blocked, unimplemented, or empty."""


class Rung(ABC):
    """One rung of the acquisition ladder."""

    number: int
    name: str

    @abstractmethod
    def try_fetch(self) -> list[dict] | None:
        """Attempt to fetch work-level records.

        Returns a non-empty list of raw record dicts on success, or raises
        `RungBlockedError` / `NotImplementedError` to signal "try the next
        rung". Must never return fabricated or placeholder data -- an
        unavailable rung fails loudly, it does not degrade silently.
        """
        raise NotImplementedError


class Rung1LiveApi(Rung):
    """Rung 1: the real MPLADS work-level data, via `mplads_adapter.py`.

    **Unblocked 2026-09-04.** The blocker was never the endpoint, it was the
    request body: `getTilesReportData` takes `{"combo": "0,0,0,2", "key":
    "<tile name>"}` where combo is a comma-separated *string*. Every earlier
    probe sent an integer, which is why they all came back `Total_Amt: 0.0`
    and why this rung previously raised. A human captured the real body from
    the dashboard's own network traffic; see 04 Prototype/Logbook.md,
    2026-09-04.

    Reads the cached tile responses from `data/raw/` rather than calling the
    endpoint itself. That is deliberate for now: the endpoint needs a live
    browser JSESSIONID that expires within hours, so a rung that called it
    directly would be a rung that works only for whoever pulled the cookie
    most recently, and every test of it would be a test of someone's session
    rather than of this code. Re-pulling the tiles is a documented manual
    step (04 Prototype/NEXT-STEPS.md); wiring an authenticated client in
    front of it is a separate piece of work with its own credential-handling
    decisions, and it is not needed for a snapshot-driven product whose
    "hard rule" is that everything downstream reads the on-disk snapshot
    anyway (Execution Plan section 2).

    Returns None (not an exception) when the cached tiles are absent, so a
    checkout without them falls cleanly to the next rung instead of dying.
    """

    number = 1
    name = "mplads_live_api"

    def __init__(
        self, client: MpladsClient | None = None, raw_dir: Path | None = None
    ) -> None:
        self._client = client
        self._raw_dir = raw_dir

    def try_fetch(self) -> list[dict] | None:
        try:
            records, counts = load_and_adapt(self._raw_dir)
        except MpladsAdapterError as exc:
            logger.warning(
                "Rung 1: cached MPLADS tiles unusable, falling through: %s", exc
            )
            return None
        if not records:
            logger.warning("Rung 1: adapter produced no records from the cached tiles")
            return None
        logger.info(
            "Rung 1: %d records from cached MPLADS tiles "
            "(sanctioned=%d, completed=%d, expenditure_events=%d, dropped=%d)",
            counts["records"],
            counts["sanctioned_rows"],
            counts["completed_rows"],
            counts["expenditure_rows"],
            counts["dropped_no_work_id"],
        )
        completeness = {
            key: value
            for key, value in counts.items()
            if key.endswith(("_present", "_missing", "_unparseable"))
        }
        logger.info("Rung 1 source completeness: %s", completeness)
        return records


class Rung2PlaywrightScrape(Rung):
    """Rung 2: Playwright headless scrape of the rendered dashboard UI.

    Drives the real dashboard at
    https://mplads.mospi.gov.in/digigov/dashboard.html with Playwright,
    paginating by state and constituency, and scrapes the rendered results
    table's DOM row by row rather than calling a JSON endpoint. Reliable
    but slow and brittle to markup changes (Execution Plan section 2). Build
    this only once Rung 1 is confirmed permanently dead -- right now it is
    blocked on parameters, not dead, so Rung 2 is not yet warranted.
    """

    number = 2
    name = "playwright_ui_scrape"

    def try_fetch(self) -> list[dict] | None:
        raise NotImplementedError(
            "Rung 2 (Playwright UI scrape) is not implemented. It would "
            "launch a headless browser against "
            "https://mplads.mospi.gov.in/digigov/dashboard.html, select "
            "each state/constituency filter combination, wait for the "
            "results table to render, and scrape it row by row. Use this "
            "for when Rung 1 is confirmed dead, not merely unparameterised."
        )


class Rung3EmpoweredIndian(Rung):
    """Rung 3: reuse Empowered Indian (empoweredindian.in/mplads), an
    existing public MPLADS visualization that has already solved this data
    problem -- check their approach or dataset before building anything new,
    and credit them (Execution Plan section 2).
    """

    number = 3
    name = "empowered_indian_mirror"

    def try_fetch(self) -> list[dict] | None:
        raise NotImplementedError(
            "Rung 3 (Empowered Indian mirror) is not implemented. It would "
            "fetch or reuse the MPLADS dataset already published at "
            "https://empoweredindian.in/mplads instead of re-solving the "
            "acquisition problem from scratch, with attribution."
        )


class Rung4DataGovIn(Rung):
    """Rung 4: data.gov.in's MPLADS datasets, plus Lok Sabha/Rajya Sabha Q&A
    answers, which routinely contain tabular MPLADS figures. Lower
    resolution than a live pull, but real and citable (Execution Plan
    section 2).
    """

    number = 4
    name = "data_gov_in"

    def try_fetch(self) -> list[dict] | None:
        raise NotImplementedError(
            "Rung 4 (data.gov.in) is not implemented. It would pull MPLADS "
            "datasets from data.gov.in and tabular figures out of Lok "
            "Sabha/Rajya Sabha Q&A answers, at lower resolution than a live "
            "pull but citable to a public source."
        )


class Rung5SeedFixtures(Rung):
    """Rung 5: last resort. A hand-curated seed dataset built from published
    CAG reports and dashboard exports, clearly labelled in the UI as a demo
    dataset -- honest labelling is mandatory here (Execution Plan section
    2). Note: the CLI's own fallback to `contracts/fixtures/works.fixture.json`
    (see `cli.py`) is the practical version of this rung today; this class
    is the stub for a rung that would *generate* such a seed set on demand.
    """

    number = 5
    name = "labelled_seed_set"

    def try_fetch(self) -> list[dict] | None:
        raise NotImplementedError(
            "Rung 5 (hand-curated seed dataset) is not implemented as a "
            "ladder rung. It would build a labelled sample dataset from "
            "published CAG reports and MPLADS dashboard exports. The "
            "existing labelled fixture at contracts/fixtures/works.fixture.json "
            "already serves this purpose for today's demo; see cli.py's "
            "fallback path."
        )


def default_rungs() -> list[Rung]:
    """The ladder in order. A fresh list every call so callers can safely
    mutate what they get back without affecting other callers.
    """
    return [
        Rung1LiveApi(),
        Rung2PlaywrightScrape(),
        Rung3EmpoweredIndian(),
        Rung4DataGovIn(),
        Rung5SeedFixtures(),
    ]


def run_ladder(rungs: Sequence[Rung] | None = None) -> tuple[list[dict], int]:
    """Try each rung in order, stop at the first that returns data.

    Catches `RungBlockedError` and `NotImplementedError` from each rung,
    logs which rung was attempted and why it failed, and moves on. Returns
    `(records, rung_number)` for the first rung that returns a non-empty
    list. Raises `AllRungsFailedError` if every rung fails.
    """
    for rung in rungs if rungs is not None else default_rungs():
        logger.info("Attempting rung %d (%s)", rung.number, rung.name)
        try:
            result = rung.try_fetch()
        except RungBlockedError as exc:
            logger.warning("Rung %d (%s) blocked: %s", rung.number, rung.name, exc)
            continue
        except NotImplementedError as exc:
            logger.warning(
                "Rung %d (%s) not implemented: %s", rung.number, rung.name, exc
            )
            continue
        if result:
            logger.info(
                "Rung %d (%s) succeeded with %d records",
                rung.number,
                rung.name,
                len(result),
            )
            return result, rung.number
        logger.warning("Rung %d (%s) returned no records", rung.number, rung.name)

    raise AllRungsFailedError(
        "All 5 rungs in the acquisition ladder failed, are blocked, or are "
        "unimplemented. See 04 Prototype/Logbook.md, the 2026-09-01 19:45 "
        "and 20:10 entries, for current status. Callers (e.g. cli.py) should "
        "fall back to the labelled seed fixture and say so loudly."
    )
