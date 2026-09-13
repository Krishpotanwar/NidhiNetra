"""Tests for ingest/mplads_api.py.

Uses httpx.MockTransport throughout -- no real network calls. The ZK error
page fixture at fixtures/zk_error_response.html is what getTilesReportData
and friends actually return for a malformed request (Logbook 2026-09-01
19:45), so the "server returned HTML instead of JSON" tests replay it
verbatim rather than inventing a fake error body.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from nidhinetra_pipeline.ingest import mplads_api
from nidhinetra_pipeline.ingest.mplads_api import (
    MpladsClient,
    MpladsHttpError,
    MpladsResponseFormatError,
    MpladsUpstreamHtmlError,
    StateInfo,
    TilesData,
    TilesReportData,
    _RateLimiter,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ZK_ERROR_HTML = (FIXTURES_DIR / "zk_error_response.html").read_text(encoding="utf-8")


def _client_with_handler(handler) -> MpladsClient:
    transport = httpx.MockTransport(handler)
    httpx_client = httpx.Client(transport=transport, base_url=mplads_api.BASE_URL)
    # A no-op rate limiter (min interval 0, real clock) keeps tests fast
    # while still exercising the real _post() code path.
    return MpladsClient(client=httpx_client, rate_limiter=_RateLimiter(0.0))


# --------------------------------------------------------------------------
# getStateData
# --------------------------------------------------------------------------


def test_get_state_data_happy_path():
    body = [
        {"STATE_NAME": "Bihar", "STATE_ID": 4},
        {"STATE_NAME": "Jharkhand", "STATE_ID": 18},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == mplads_api.STATE_DATA_PATH
        return httpx.Response(200, json=body)

    client = _client_with_handler(handler)
    result = client.get_state_data()

    assert result == [
        StateInfo(state_name="Bihar", state_id=4),
        StateInfo(state_name="Jharkhand", state_id=18),
    ]
    assert isinstance(result[0], StateInfo)


def test_get_state_data_zk_html_error_raises_typed_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=ZK_ERROR_HTML, headers={"content-type": "text/html"})

    client = _client_with_handler(handler)
    with pytest.raises(MpladsUpstreamHtmlError):
        client.get_state_data()


def test_get_state_data_non_list_payload_raises_format_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"not": "a list"})

    client = _client_with_handler(handler)
    with pytest.raises(MpladsResponseFormatError):
        client.get_state_data()


# --------------------------------------------------------------------------
# getTilesData
# --------------------------------------------------------------------------


def test_get_tiles_data_happy_path_is_permissive():
    body = {
        "works_recommended": 105640,
        "works_sanctioned": 78547,
        "works_completed": 34067,
        "allocated_amt_cr": 8318.06,
        "expenditure_amt_cr": 2748.49,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == mplads_api.TILES_DATA_PATH
        return httpx.Response(200, json=body)

    client = _client_with_handler(handler)
    result = client.get_tiles_data()

    assert isinstance(result, TilesData)
    dumped = result.model_dump()
    assert dumped["works_recommended"] == 105640
    assert dumped["works_sanctioned"] == 78547


def test_get_tiles_data_sends_required_headers():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["content_type"] = request.headers.get("content-type")
        captured["referer"] = request.headers.get("referer")
        return httpx.Response(200, json={})

    client = _client_with_handler(handler)
    client.get_tiles_data()

    assert captured["content_type"] == "application/json; charset=utf-8"
    assert captured["referer"] == mplads_api.DASHBOARD_REFERER


def test_get_tiles_data_zk_html_error_raises_typed_exception_not_crash():
    """This is the exact regression from the 19:45 Logbook entry: a request
    without the right headers gets a ZK HTML page, which must not crash the
    JSON parser -- it must raise a clear, typed exception.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=ZK_ERROR_HTML, headers={"content-type": "text/html"})

    client = _client_with_handler(handler)
    with pytest.raises(MpladsUpstreamHtmlError):
        client.get_tiles_data()


def test_non_200_status_raises_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal server error")

    client = _client_with_handler(handler)
    with pytest.raises(MpladsHttpError):
        client.get_tiles_data()


# --------------------------------------------------------------------------
# getTilesReportData
# --------------------------------------------------------------------------


def test_get_tiles_report_data_happy_path_matches_logbook_shape():
    # Exact response shape documented live in Logbook 2026-09-01 19:45:
    # a single-key object whose value is a JSON-encoded string. combo is
    # the comma-separated STRING form confirmed live 2026-09-04 (Logbook,
    # NEXT-STEPS.md item 1) -- an outside-voice finding (2026-09-05 eng
    # review) caught this test still asserting the debunked integer form,
    # which would have silently reproduced the original bug (every
    # zeroed-out Total_Amt probe) if anyone had trusted this test as the
    # spec for a live call.
    body = {"Works Sanctioned": json.dumps([{"Total_Amt": 0.0}])}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == mplads_api.TILES_REPORT_DATA_PATH
        sent = json.loads(request.content)
        assert sent == {"combo": "0,0,0,2", "key": "Works Sanctioned"}
        return httpx.Response(200, json=body)

    client = _client_with_handler(handler)
    result = client.get_tiles_report_data(combo="0,0,0,2", key="Works Sanctioned")

    assert isinstance(result, TilesReportData)
    assert result.tile_key == "Works Sanctioned"
    assert result.rows == [mplads_api.TilesReportRow(total_amt=0.0)]


def test_get_tiles_report_data_zk_html_error_raises_typed_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=ZK_ERROR_HTML, headers={"content-type": "text/html"})

    client = _client_with_handler(handler)
    with pytest.raises(MpladsUpstreamHtmlError):
        client.get_tiles_report_data(combo="0", key="anything")


def test_get_tiles_report_data_malformed_inner_json_raises_format_error():
    # Inner value is not valid JSON at all -- must not crash, must raise typed.
    body = {"Works Sanctioned": "{not valid json"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    client = _client_with_handler(handler)
    with pytest.raises(MpladsResponseFormatError):
        client.get_tiles_report_data(combo="0", key="Works Sanctioned")


def test_get_tiles_report_data_empty_object_raises_format_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = _client_with_handler(handler)
    with pytest.raises(MpladsResponseFormatError):
        client.get_tiles_report_data(combo="0", key="anything")


# --------------------------------------------------------------------------
# warm_session (CP6: autonomous session bootstrap, no human-supplied cookie)
# --------------------------------------------------------------------------


def test_warm_session_hits_the_dashboard_path():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == mplads_api.DASHBOARD_PATH
        return httpx.Response(200, text="<html></html>")

    client = _client_with_handler(handler)
    client.warm_session()  # must not raise


def test_warm_session_non_200_raises_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    client = _client_with_handler(handler)
    with pytest.raises(MpladsHttpError):
        client.warm_session()


def test_warm_session_persists_cookies_for_a_later_request_with_no_human_input():
    """The entire point of warm_session(): a Set-Cookie header from the GET
    must be attached automatically to a later POST through the same client,
    with no cookie ever supplied by the caller. This is what lets cli.py's
    pull_live() run with zero human cookie-copying -- see
    04 Prototype/Checkpoints.md CP6.
    """
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == mplads_api.DASHBOARD_PATH:
            return httpx.Response(
                200,
                text="<html></html>",
                headers={"set-cookie": "JSESSIONID=abc123.jboss_8081; Path=/"},
            )
        captured["cookie_header"] = request.headers.get("cookie")
        return httpx.Response(200, json={"Works Sanctioned": "[]"})

    client = _client_with_handler(handler)
    client.warm_session()
    client.get_tiles_report_data_raw(combo="0,0,0,2", key="Works Sanctioned")

    assert captured["cookie_header"] is not None
    assert "JSESSIONID=abc123.jboss_8081" in captured["cookie_header"]


# --------------------------------------------------------------------------
# getTilesReportData raw (byte-for-byte passthrough for cli.py's pull_live)
# --------------------------------------------------------------------------


def test_get_tiles_report_data_raw_returns_the_wrapper_unvalidated():
    """This is the exact shape ingest/mplads_adapter.py's `_unwrap()` already
    parses from data/raw/mplads-*.json -- pull_live() writes this straight
    to disk with no reshaping, so it has to come back byte-for-byte
    equivalent to what the server sent, not a re-typed pydantic model.
    """
    body = {
        "Works Sanctioned": json.dumps(
            [
                {"WORK_RECOMMENDATION_DTL_ID": 1, "STATE_NAME": "Bihar"},
                {"Total_Amt": 12345.0},
            ]
        )
    }

    def handler(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)
        assert sent == {"combo": "0,0,0,2", "key": "Works Sanctioned"}
        return httpx.Response(200, json=body)

    client = _client_with_handler(handler)
    result = client.get_tiles_report_data_raw(combo="0,0,0,2", key="Works Sanctioned")

    assert result == body


def test_get_tiles_report_data_raw_empty_object_raises_format_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = _client_with_handler(handler)
    with pytest.raises(MpladsResponseFormatError):
        client.get_tiles_report_data_raw(combo="0", key="anything")


def test_get_tiles_report_data_raw_zk_html_error_raises_typed_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=ZK_ERROR_HTML, headers={"content-type": "text/html"})

    client = _client_with_handler(handler)
    with pytest.raises(MpladsUpstreamHtmlError):
        client.get_tiles_report_data_raw(combo="0", key="anything")


# --------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------


def test_rate_limiter_sleeps_when_called_too_soon():
    clock_values = iter([100.0, 100.2])  # one clock read per wait() call
    sleeps: list[float] = []

    limiter = _RateLimiter(
        1.5,
        clock=lambda: next(clock_values),
        sleep=lambda seconds: sleeps.append(seconds),
    )

    limiter.wait()  # t=100.0, no prior call, no sleep
    limiter.wait()  # t=100.2, elapsed 0.2s < 1.5s, must sleep ~1.3s

    assert sleeps == [pytest.approx(1.3)]


def test_rate_limiter_does_not_sleep_when_interval_already_elapsed():
    clock_values = iter([100.0, 102.0])
    sleeps: list[float] = []

    limiter = _RateLimiter(
        1.5,
        clock=lambda: next(clock_values),
        sleep=lambda seconds: sleeps.append(seconds),
    )

    limiter.wait()
    limiter.wait()

    assert sleeps == []


def test_client_default_min_interval_is_1_5_seconds():
    assert mplads_api.MIN_REQUEST_INTERVAL_SECONDS == 1.5
