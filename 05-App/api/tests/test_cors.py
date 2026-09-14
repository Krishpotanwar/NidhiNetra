"""main.py's CORS configuration (2026-09-14 incident): Vercel mints a
brand-new, uniquely-hashed preview URL on every deployment, which an
exact-match ALLOWED_ORIGINS can never keep up with -- a real user hit
"Cannot reach the data service" on a URL that had simply never been (and
could never be) added to that list. _ALLOW_ORIGIN_REGEX closes the whole
family of this project's own preview URLs at once; these tests prove the
middleware actually applies it end to end, not just that the regex looks
right in isolation.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _allowed_origin(client: TestClient, origin: str) -> str | None:
    resp = client.get("/health", headers={"Origin": origin})
    return resp.headers.get("access-control-allow-origin")


def test_the_exact_preview_url_from_the_incident_is_allowed(client: TestClient) -> None:
    origin = "https://nidhinetra-5oscukrhx-krishpotanwars-projects.vercel.app"
    assert _allowed_origin(client, origin) == origin


def test_a_different_deploy_hash_is_allowed_without_any_config_change(client: TestClient) -> None:
    # The whole point: tomorrow's deploy mints a new hash nobody has to add
    # anywhere.
    origin = "https://nidhinetra-zzz999-krishpotanwars-projects.vercel.app"
    assert _allowed_origin(client, origin) == origin


def test_local_dev_origins_still_work(client: TestClient) -> None:
    assert _allowed_origin(client, "http://localhost:3000") == "http://localhost:3000"
    assert _allowed_origin(client, "http://127.0.0.1:3001") == "http://127.0.0.1:3001"


def test_a_lookalike_hostname_outside_vercel_app_is_rejected(client: TestClient) -> None:
    # The trailing $ against the literal ".vercel.app" is what stops a
    # hostile domain that merely starts with the right prefix.
    assert (
        _allowed_origin(
            client, "https://nidhinetra-krishpotanwars-projects.vercel.app.attacker.com"
        )
        is None
    )


def test_an_unrelated_vercel_project_is_rejected(client: TestClient) -> None:
    assert _allowed_origin(client, "https://someone-elses-app-a1b2c3-some-team.vercel.app") is None
