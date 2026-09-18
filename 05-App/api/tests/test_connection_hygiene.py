"""F-23 (nemotronreview.md): every request closes the DuckDB connection it
opened, and path and filter inputs are bounded.
"""

from __future__ import annotations

from typing import Any

import pytest
from nidhinetra_api import db


class _TrackingConnection:
    """Wraps a real DuckDB connection and records whether close() ran."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection
        self.closed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def close(self) -> None:
        self.closed = True
        self._connection.close()


@pytest.fixture()
def tracked(monkeypatch: pytest.MonkeyPatch) -> list[_TrackingConnection]:
    opened: list[_TrackingConnection] = []
    real_connect = db.connect

    def tracking_connect(*args: Any, **kwargs: Any) -> _TrackingConnection:
        connection = _TrackingConnection(real_connect(*args, **kwargs))
        opened.append(connection)
        return connection

    monkeypatch.setattr(db, "connect", tracking_connect)
    return opened


@pytest.mark.parametrize("path", ["/api/stats/summary", "/api/works", "/api/works/facets"])
def test_read_endpoints_close_their_connection(client, tracked, path: str) -> None:
    assert client.get(path).status_code == 200
    assert tracked
    assert all(connection.closed for connection in tracked)


def test_recording_an_inspection_closes_its_connection(client, tracked) -> None:
    work_id = client.get("/api/works", params={"page_size": 1}).json()["data"][0]["work_id"]
    tracked.clear()

    response = client.post(
        "/api/inspections",
        json={
            "work_id": work_id,
            "inspected_on": "2026-09-05",
            "outcome": "work_present_and_matches",
            "notes": "",
            "inspector_id": "AB",
        },
    )

    assert response.status_code == 200
    assert tracked
    assert all(connection.closed for connection in tracked)


def test_an_overlong_work_id_path_is_a_422(client) -> None:
    response = client.get("/api/works/" + "w" * 65)
    assert response.status_code == 422
    assert response.json()["success"] is False


@pytest.mark.parametrize("param", ["agency", "vendor"])
def test_graph_filters_are_bounded(client, param: str) -> None:
    response = client.get("/api/graph", params={param: "x" * 121})
    assert response.status_code == 422
