"""POST /api/refresh: succeeds once, then 429s on an immediate second call
(eng review task T12, the server-side rate limit).

The session-scoped `bootstrapped_snapshot` fixture (conftest.py) itself
writes manifest.json with generated_at = now, which means the "last
refresh" the rate limiter sees is never more than a few hundred
milliseconds old at the point any test runs -- a real, correct rate-limit
hit, not a bug. To exercise the "succeeds once" branch deterministically
(no wall-clock sleep(31) making this test slow and flaky), this test
directly backdates manifest.json's generated_at past the 30-second window
before making its first call. That's on-disk state manipulation of the
same manifest.json the app itself reads and writes, not a mock of the
data layer.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from nidhinetra_api import snapshot


def _backdate_last_refresh(seconds: float) -> None:
    manifest_path = snapshot.SNAPSHOT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    backdated = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    manifest["generated_at"] = backdated.strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def test_refresh_succeeds_then_429s_on_immediate_second_call(client):
    _backdate_last_refresh(seconds=60)

    first = client.post("/api/refresh")
    assert first.status_code == 202
    first_body = first.json()
    assert first_body["success"] is True
    assert first_body["data"]["row_count"] == 20

    second = client.post("/api/refresh")
    assert second.status_code == 429
    second_body = second.json()
    assert second_body["success"] is False
    assert second_body["data"] is None
    assert "30" in second_body["error"]


def test_refresh_within_the_window_is_429_without_backdating(client):
    """A refresh that lands soon after another one -- the ordinary case,
    with no manifest manipulation -- is rejected. This is effectively what
    every other test in this suite already relies on implicitly (the
    session bootstrap counts as "the last refresh"), asserted explicitly.
    """
    response = client.post("/api/refresh")
    assert response.status_code == 429
