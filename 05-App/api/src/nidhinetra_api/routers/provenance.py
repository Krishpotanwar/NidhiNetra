"""GET /api/provenance (F-18, nemotronreview.md): where the served numbers
came from. Returns the manifest's identity fields and its provenance block
(tile receipts with hashes and completeness, the normalized cache, contract
and scoring-configuration hashes). A snapshot built before F-18 has no such
block and says so with provenance = null, rather than inventing one.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import snapshot
from ..db import SnapshotNotReadyError
from ..models import Envelope

router = APIRouter(prefix="/api/provenance", tags=["provenance"])


@router.get("")
def get_provenance() -> Envelope:
    manifest = snapshot.read_manifest()
    if manifest is None:
        raise SnapshotNotReadyError("manifest.json not found; the snapshot has not been built yet.")
    return Envelope(
        success=True,
        data={
            "row_count": manifest.get("row_count"),
            "generated_at": manifest.get("generated_at"),
            "data_as_of": manifest.get("data_as_of"),
            "source": manifest.get("source"),
            "provenance": manifest.get("provenance"),
        },
    )


__all__ = ["router"]
