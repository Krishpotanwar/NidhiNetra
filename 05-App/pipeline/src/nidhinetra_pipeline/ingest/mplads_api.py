"""Thin HTTP client for the MPLADS government dashboard's REST endpoints.

Base host: https://mplads.mospi.gov.in
All three endpoints below were probed live on 2026-09-01 -- see
04 Prototype/Logbook.md, the 19:45 entry, for the full spike writeup, and
the 20:10 entry for the surrounding decisions. Each function's docstring
states whether ITS endpoint is CONFIRMED LIVE or STILL BLOCKED; "confirmed
live" means the endpoint returns real 200 JSON for a known request shape,
not that every field name in the response has been pinned down.

Every function returns typed objects (pydantic models), never raw dicts.
Rate limit: a minimum of 1.5 seconds between requests to this host. This is
a public government server -- treat it gently. This is a hard requirement,
not a suggestion, and is enforced inside this module, not left to callers.

Why getTilesData's model is loose (`extra="allow"`) but getStateData's is
not: getStateData's exact field names (`STATE_NAME`, `STATE_ID`) were read
directly off a live response and are pinned down. getTilesData's live
response was read as human-summarized numbers in the Logbook (e.g. "105,640
works recommended"), not as a captured raw JSON body, so the literal key
names are still unknown. Guessing at key names here would silently produce
`None`s instead of a loud failure, exactly the class of mistake the 19:45
Logbook entry warns about ("a failed probe with the wrong request shape is
not evidence the endpoint is dead"). Tighten `TilesData` to named fields
once a real payload is captured.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

BASE_URL = "https://mplads.mospi.gov.in"
DASHBOARD_REFERER = "https://mplads.mospi.gov.in/digigov/dashboard.html"
MIN_REQUEST_INTERVAL_SECONDS = 1.5

STATE_DATA_PATH = "/rest/PreLoginDashboardData/getStateData"
TILES_DATA_PATH = "/rest/PreLoginDashboardData/getTilesData"
TILES_REPORT_DATA_PATH = "/rest/PreLoginDashboardData/getTilesReportData"
DASHBOARD_PATH = "/digigov/dashboard.html"


# --------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------


class MpladsClientError(Exception):
    """Base class for every error this module raises."""


class MpladsHttpError(MpladsClientError):
    """The server responded with a non-200 HTTP status."""


class MpladsUpstreamHtmlError(MpladsClientError):
    """The server returned a ZK-framework HTML error page instead of JSON.

    This is what getTilesReportData and other endpoints return when the
    request is missing a required header, or is otherwise malformed. An
    earlier probe without the Content-Type/Referer headers hit this on
    getTilesData and was wrongly logged as "endpoint dead" -- see Logbook
    2026-09-01 19:45. Catch this specifically rather than letting a bare
    JSONDecodeError propagate, so callers can tell "wrong request shape"
    apart from "genuinely unparseable response".
    """


class MpladsResponseFormatError(MpladsClientError):
    """The response was valid JSON but not the shape this function expects."""


# --------------------------------------------------------------------------
# Typed response models
# --------------------------------------------------------------------------


class StateInfo(BaseModel):
    """One row of the getStateData dropdown lookup. Field names confirmed live."""

    model_config = ConfigDict(populate_by_name=True)

    state_name: str = Field(alias="STATE_NAME")
    state_id: int = Field(alias="STATE_ID")


class TilesData(BaseModel):
    """National aggregates from getTilesData (works recommended/sanctioned/
    completed, allocated/expenditure amounts). Deliberately permissive --
    see module docstring for why the field names are not pinned down yet.
    Every key the server actually sends is preserved and reachable via
    `model_dump()` or `model_extra`; nothing is silently dropped.
    """

    model_config = ConfigDict(extra="allow")


class TilesReportRow(BaseModel):
    """One row of a getTilesReportData tile. Shape confirmed live: every
    combo/key pair tried so far returns rows shaped exactly like this, just
    with Total_Amt stuck at 0.0 (see get_tiles_report_data's docstring).
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    total_amt: float = Field(alias="Total_Amt")


class TilesReportData(BaseModel):
    """A parsed getTilesReportData response.

    The raw response is a single-key JSON object whose value is itself a
    JSON-encoded string (double-encoded), e.g.
    `{"Works Sanctioned": "[{\\"Total_Amt\\":0.0}]"}`. `tile_key` is that
    outer key (the tile name for whatever combo/key was requested);
    `rows` is the parsed inner list.
    """

    tile_key: str
    rows: list[TilesReportRow]


# --------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------


class _RateLimiter:
    """Enforces a minimum interval between calls to `wait()`.

    `clock`/`sleep` are injectable so tests can exercise the throttling
    logic without actually sleeping in real wall-clock time.
    """

    def __init__(
        self,
        min_interval_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = min_interval_seconds
        self._clock = clock
        self._sleep = sleep
        self._last_request_at: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last_request_at is not None:
            remaining = self._min_interval - (now - self._last_request_at)
            if remaining > 0:
                self._sleep(remaining)
                now += remaining  # avoid a second clock read; sleep() covers the gap
        self._last_request_at = now


# --------------------------------------------------------------------------
# Response parsing helpers
# --------------------------------------------------------------------------


def _looks_like_zk_error_page(text: str) -> bool:
    lowered = text.lower()
    return "<!doctype html>" in lowered and ("/zkau/" in lowered or "new page title" in lowered)


def _parse_json_or_raise(response: httpx.Response, *, endpoint: str) -> Any:
    if response.status_code != 200:
        raise MpladsHttpError(
            f"{endpoint}: HTTP {response.status_code} from {response.request.url}"
        )
    text = response.text
    try:
        return response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        if _looks_like_zk_error_page(text):
            raise MpladsUpstreamHtmlError(
                f"{endpoint}: MPLADS returned a ZK-framework HTML error page "
                "instead of JSON. This usually means the request is missing a "
                "required header (Content-Type: application/json; charset=utf-8, "
                "or Referer) or the request body shape is wrong -- see "
                "04 Prototype/Logbook.md, the 2026-09-01 19:45 entry, before "
                "concluding the endpoint itself is dead."
            ) from exc
        snippet = text[:200].replace("\n", " ")
        raise MpladsResponseFormatError(
            f"{endpoint}: response body was not valid JSON and is not a "
            f"recognisable ZK error page either. First 200 chars: {snippet!r}"
        ) from exc


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------


class MpladsClient:
    """HTTP client for the three confirmed MPLADS dashboard REST endpoints.

    Pass an `httpx.Client` (e.g. one built with a `httpx.MockTransport`) for
    testing; otherwise a real client against `BASE_URL` is created and owned
    (and closed on `close()`/context-exit) automatically.
    """

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        rate_limiter: _RateLimiter | None = None,
    ) -> None:
        self._client = client or httpx.Client(base_url=BASE_URL, timeout=30.0)
        self._owns_client = client is None
        self._rate_limiter = rate_limiter or _RateLimiter(MIN_REQUEST_INTERVAL_SECONDS)

    def __enter__(self) -> MpladsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _post(self, path: str, json_body: dict[str, Any]) -> httpx.Response:
        self._rate_limiter.wait()
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Referer": DASHBOARD_REFERER,
        }
        return self._client.post(path, json=json_body, headers=headers)

    def warm_session(self) -> None:
        """GETs the dashboard HTML page so the server issues session cookies
        into this client's own cookie jar -- exactly what happens when a
        person opens the page in a browser, before any data call fires. No
        cookie or credential is supplied by the caller: httpx.Client stores
        whatever Set-Cookie headers come back and attaches them to every
        later request made through this same client automatically. This is
        what lets get_tiles_report_data_raw() below run with zero
        human-provided cookie input.

        CONFIRMED LIVE: this exact GET has succeeded in well under 1s in
        every attempt on record, including from the automated/cloud
        environments where the POST endpoints below are tarpitted -- see
        get_tiles_report_data_raw's docstring and 04 Prototype/
        Checkpoints.md CP6. Rate-limited the same as every other call this
        client makes, out of the same courtesy to a public government
        server.
        """
        self._rate_limiter.wait()
        response = self._client.get(DASHBOARD_PATH)
        if response.status_code != 200:
            raise MpladsHttpError(
                f"warm_session: HTTP {response.status_code} from {response.request.url}"
            )

    def get_state_data(self) -> list[StateInfo]:
        """CONFIRMED LIVE.

        POST /rest/PreLoginDashboardData/getStateData returns the 36-state
        filter-dropdown lookup as a JSON array of
        `{"STATE_NAME": str, "STATE_ID": int}`. Verified against a live
        response on 2026-09-01 (Logbook 19:45 entry).
        """
        response = self._post(STATE_DATA_PATH, json_body={})
        payload = _parse_json_or_raise(response, endpoint="getStateData")
        if not isinstance(payload, list):
            raise MpladsResponseFormatError(
                f"getStateData: expected a JSON array, got {type(payload).__name__}"
            )
        return [StateInfo.model_validate(row) for row in payload]

    def get_tiles_data(self) -> TilesData:
        """CONFIRMED LIVE.

        POST /rest/PreLoginDashboardData/getTilesData returns the national
        summary strip: works recommended/sanctioned/completed and
        allocated/expenditure amounts. Requires
        `Content-Type: application/json; charset=utf-8` and a `Referer` of
        the dashboard page -- both are sent unconditionally by this client.
        Verified live on 2026-09-01: 105,640 recommended, 78,547 sanctioned,
        34,067 completed (Logbook 19:45 entry). See the module docstring for
        why the returned model is permissive rather than pinned to named
        fields.
        """
        response = self._post(TILES_DATA_PATH, json_body={})
        payload = _parse_json_or_raise(response, endpoint="getTilesData")
        if not isinstance(payload, dict):
            raise MpladsResponseFormatError(
                f"getTilesData: expected a JSON object, got {type(payload).__name__}"
            )
        return TilesData.model_validate(payload)

    def get_tiles_report_data(self, combo: str, key: str) -> TilesReportData:
        """Request shape CONFIRMED (2026-09-04); live automated calls STILL
        BLOCKED, for a different reason than the one this docstring used to
        name.

        POST /rest/PreLoginDashboardData/getTilesReportData with body
        `{"combo": combo, "key": key}`. `combo` is a comma-separated STRING
        (e.g. `"0,0,0,2"`), not an integer -- every early probe sent an int
        and got `Total_Amt: 0.0` back for that reason alone. See
        `ingest/mplads_adapter.py`'s module docstring and
        04 Prototype/NEXT-STEPS.md item 1 for the full story; that fix lives
        in the adapter, this method's signature just has to stop
        contradicting it.

        What is blocked now: calling this method live, from an automated
        client, at all. A 2026-09-05 eng-review probe (04 Prototype/
        Checkpoints.md CP6) sent this exact request three ways -- no cookie,
        a freshly bootstrapped real `JSESSIONID`, and that cookie plus a full
        realistic browser header set -- and got the identical result every
        time: a full connection-level timeout, zero bytes, no HTTP status.
        Two plain GETs to the dashboard HTML page succeeded instantly in the
        same session. That pattern (clean GETs, hanging POSTs regardless of
        cookie or headers) reads as a WAF/anti-automation block on this
        specific endpoint, not a missing session -- see Checkpoints CP6 for
        the full probe writeup and what would disambiguate it (testing from
        a real browser or a non-datacenter IP) before reaching for Playwright.
        Today's real data (`data/raw/*.json`) came from a human-captured
        browser cURL, not from this method; `ingest/rungs.py`'s
        `Rung1LiveApi` reads those cached files rather than calling this.
        """
        payload = self._fetch_tile_payload(combo, key)
        tile_key, raw_rows_json = next(iter(payload.items()))
        try:
            rows_data = json.loads(raw_rows_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise MpladsResponseFormatError(
                f"getTilesReportData: inner value for tile {tile_key!r} was not "
                f"a valid JSON-encoded string: {exc}"
            ) from exc
        if not isinstance(rows_data, list):
            raise MpladsResponseFormatError(
                f"getTilesReportData: inner value for tile {tile_key!r} decoded "
                f"to {type(rows_data).__name__}, expected a list of rows"
            )
        rows = [TilesReportRow.model_validate(row) for row in rows_data]
        return TilesReportData(tile_key=tile_key, rows=rows)

    def _fetch_tile_payload(self, combo: str, key: str) -> dict[str, Any]:
        """The POST plus outer-wrapper validation shared by
        get_tiles_report_data (typed rows) and get_tiles_report_data_raw
        (byte-for-byte passthrough) -- both need the same
        `{"<tile>": "<json string>"}` shape check before they diverge on
        what to do with the inner JSON-encoded string.
        """
        response = self._post(
            TILES_REPORT_DATA_PATH, json_body={"combo": combo, "key": key}
        )
        payload = _parse_json_or_raise(response, endpoint="getTilesReportData")
        if not isinstance(payload, dict) or not payload:
            raise MpladsResponseFormatError(
                "getTilesReportData: expected a non-empty single-key JSON "
                f"object, got {payload!r}"
            )
        return payload

    def get_tiles_report_data_raw(self, combo: str, key: str) -> dict[str, Any]:
        """Same request as get_tiles_report_data, but returns the raw
        `{"<tile label>": "<json-encoded string>"}` wrapper with no
        pydantic validation of the inner rows.

        This is the exact shape ingest/mplads_adapter.py's `_unwrap()`
        already parses when it reads data/raw/mplads-*.json -- a caller
        persisting a live pull straight to those files (see cli.py's
        `pull_live`) needs no reshaping and no field-name translation.
        get_tiles_report_data() is for callers that want typed rows in
        memory; this is for callers that want the response preserved
        exactly as the server sent it.
        """
        return self._fetch_tile_payload(combo, key)
