"""F-17 companion: the rebuilt national graph is about 10 MB of JSON, so API
responses are gzip-compressed when the browser accepts it (Starlette's own
GZipMiddleware, no new dependency). Tiny responses are left alone.
"""

from __future__ import annotations


def test_large_responses_are_gzip_compressed_when_accepted(client) -> None:
    response = client.get("/api/graph", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"
    assert response.json()["success"] is True  # the test client decompresses


def test_tiny_responses_are_not_compressed(client) -> None:
    response = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") is None
