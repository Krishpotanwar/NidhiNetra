"""POST /api/refresh (contracts/openapi.yaml). Re-runs build_snapshot.py,
which since 2026-09-04 rebuilds from the most recent acquisition-ladder
snapshot in data/raw/ (rung 1, real MPLADS data) and falls back to the CP0
fixtures only when there is none. Rate-limited to one rebuild per 30
seconds, checked by reading manifest.generated_at rather than adding any
new state (eng review task T12).

What this does NOT yet do is re-pull from MPLADS. It rebuilds the snapshot
from whatever the ladder last cached; refreshing that cache is still a
manual step (04 Prototype/NEXT-STEPS.md) because getTilesReportData needs
a browser JSESSIONID that expires within hours. So the data-age label
advances when the cache is refreshed, not on every click of this endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import snapshot
from ..models import Envelope
from . import entity_aliases

router = APIRouter(prefix="/api/refresh", tags=["refresh"])

RATE_LIMIT_SECONDS = 30.0


@router.post("", status_code=202)
def refresh() -> Envelope:
    elapsed = snapshot.seconds_since_last_refresh()
    if elapsed is not None and elapsed < RATE_LIMIT_SECONDS:
        retry_after = round(RATE_LIMIT_SECONDS - elapsed, 1)
        raise HTTPException(
            status_code=429,
            detail=(
                "The snapshot was refreshed less than 30 seconds ago. "
                f"Try again in {retry_after} seconds."
            ),
        )
    manifest = snapshot.rebuild()
    entity_aliases.sync_alias_candidates_from_snapshot()
    return Envelope(success=True, data=manifest)


__all__ = ["router"]
