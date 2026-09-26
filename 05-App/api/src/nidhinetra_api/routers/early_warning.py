"""GET /api/early-warning (Task 8 Part B): the early-warning model's own
cohort and metrics, for the Reports page's "How the early warning works"
paragraph -- never the watch list itself. A per-work score or watch-list
membership is surfaced elsewhere (the `early_warning` row flag and the
`pendency=early_warning` filter, both in routers/works.py); this endpoint
only ever answers "does a shipped model exist, and what does it say about
itself," which is why `watch` is stripped before the artifact is returned.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import snapshot
from ..models import Envelope

router = APIRouter(prefix="/api/early-warning", tags=["early-warning"])


@router.get("")
def get_early_warning() -> Envelope:
    artifact = snapshot.read_early_warning()
    if artifact is None:
        return Envelope(success=True, data=None)
    return Envelope(success=True, data={k: v for k, v in artifact.items() if k != "watch"})


__all__ = ["router"]
