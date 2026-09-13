"""The house response envelope -- {success, data, error, meta} -- is
present and correctly populated on every endpoint, success or error.
"""

from __future__ import annotations

import pytest

_ENVELOPE_KEYS = {"success", "data", "error", "meta"}


@pytest.mark.parametrize(
    "method, path, params",
    [
        ("get", "/api/works", None),
        ("get", "/api/works/MPLADS-FX-0001", None),
        ("get", "/api/graph", None),
        ("get", "/api/stats/summary", None),
    ],
)
def test_success_responses_carry_the_envelope(client, method, path, params):
    response = getattr(client, method)(path, params=params)
    assert response.status_code == 200
    body = response.json()

    assert set(body.keys()) == _ENVELOPE_KEYS
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"] is not None


@pytest.mark.parametrize(
    "method, path, params, expected_status",
    [
        ("get", "/api/works/does-not-exist", None, 404),
        ("get", "/api/works", {"page_size": 9999}, 422),
    ],
)
def test_error_responses_carry_the_envelope(client, method, path, params, expected_status):
    response = getattr(client, method)(path, params=params)
    assert response.status_code == expected_status
    body = response.json()

    assert set(body.keys()) == _ENVELOPE_KEYS
    assert body["success"] is False
    assert body["data"] is None
    assert isinstance(body["error"], str) and body["error"]
