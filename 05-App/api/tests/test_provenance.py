"""GET /api/provenance (F-18): where the served numbers came from."""

from __future__ import annotations

from nidhinetra_api import snapshot


def test_provenance_reports_the_served_snapshot(client) -> None:
    body = client.get("/api/provenance").json()

    assert body["success"] is True
    data = body["data"]
    assert data["row_count"] == 20
    assert data["source"] == "cp0_fixtures"
    assert data["provenance"]["acquisition_mode"] == "fixture"
    assert len(data["provenance"]["scoring_config_sha256"]) == 64


def test_a_manifest_without_provenance_says_so(client, monkeypatch) -> None:
    legacy = {
        "row_count": 79068,
        "generated_at": "2026-09-13T06:27:54Z",
        "data_as_of": "2026-09-04T11:37:18Z",
        "source": "mplads_live_api",
    }
    monkeypatch.setattr(snapshot, "read_manifest", lambda snapshot_dir=None: legacy)

    data = client.get("/api/provenance").json()["data"]

    assert data["provenance"] is None
    assert data["data_as_of"] == "2026-09-04T11:37:18Z"
