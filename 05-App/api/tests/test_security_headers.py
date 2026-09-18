"""F-22 (nemotronreview.md): CORS allows only what the frontend actually uses
(GET, POST with a JSON body, and the preflight), advertises no credentials,
and every response carries baseline security headers. The origin rules
themselves are covered by test_cors.py and must not change.
"""

from __future__ import annotations

import pytest

_ORIGIN = "http://localhost:3000"


def _preflight(client, method: str, headers: str | None = None):
    request_headers = {"Origin": _ORIGIN, "Access-Control-Request-Method": method}
    if headers is not None:
        request_headers["Access-Control-Request-Headers"] = headers
    return client.options("/api/inspections", headers=request_headers)


def test_preflight_allows_the_json_post_the_web_sends(client) -> None:
    response = _preflight(client, "POST", "content-type")
    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]


def test_preflight_rejects_a_method_the_app_does_not_use(client) -> None:
    assert _preflight(client, "DELETE").status_code == 400


def test_preflight_rejects_an_unexpected_request_header(client) -> None:
    assert _preflight(client, "POST", "x-custom-header").status_code == 400


def test_no_credentials_are_advertised(client) -> None:
    response = client.get("/health", headers={"Origin": _ORIGIN})
    assert response.headers.get("access-control-allow-origin") == _ORIGIN
    assert response.headers.get("access-control-allow-credentials") is None


@pytest.mark.parametrize("path", ["/health", "/api/works", "/api/does-not-exist"])
def test_every_response_carries_baseline_security_headers(client, path: str) -> None:
    response = client.get(path)
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
