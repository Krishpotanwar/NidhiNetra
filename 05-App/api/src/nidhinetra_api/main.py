"""FastAPI app entry point (contracts/openapi.yaml, Execution Plan 3.4).

Run standalone with `make api` (`uv run uvicorn nidhinetra_api.main:app
--reload --port 8000` from api/), or as part of `make demo`. CORS is
enabled for http://localhost:3000, the Next.js dev server A5 built.

Authority note, carried over from contracts/openapi.yaml's own header:
that hand-written YAML is authoritative until this app exists; from here
on, FastAPI's own generated openapi.json (served at /openapi.json once
this app is running) is authoritative, because it is derived from the
route code below and cannot drift from what the API really does.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from nidhinetra_pipeline.build_snapshot import SnapshotDowngradeError, StaleCacheError

from . import snapshot
from .db import SnapshotNotReadyError
from .routers import entity_aliases, graph, inspections, refresh, stats, works

logger = logging.getLogger("nidhinetra_api")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """If data/snapshot/manifest.json doesn't exist yet, build it once from
    the CP0 fixtures so `make api` works standalone -- no manual pipeline
    run required first. A no-op when a snapshot (committed or from a prior
    run) is already there.
    """
    manifest = snapshot.bootstrap_if_needed()
    logger.info(
        "Snapshot ready: %d records, source=%s, generated_at=%s",
        manifest["row_count"],
        manifest["source"],
        manifest["generated_at"],
    )
    entity_aliases.sync_alias_candidates_from_snapshot()
    yield


app = FastAPI(
    title="NidhiNetra API",
    version="0.1.0",
    description="Execution Plan section 3.4. See contracts/openapi.yaml for the design record.",
    lifespan=_lifespan,
)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    """Liveness only: no query, no snapshot read. A host's health check must
    answer in well under its timeout regardless of dataset size; /api/stats
    /summary joins and scans all 79,068 rows on every call, which is fine
    for a page load but was killing the free-tier instance under repeated
    health-check load (Render events, 2026-09-13: HTTP health check timeout
    -> OOM -> restart loop, exit 137)."""
    return {"status": "ok"}


# Demo-day failure this closes, found in the 2026-09-03 review: the
# original single entry was exactly "http://localhost:3000", and three
# realistic situations all fall outside it. `next dev` silently moves to
# :3001 when :3000 is already taken (a stale dev server is enough);
# http://127.0.0.1:3000 is a *different* origin to the browser than
# http://localhost:3000 even on the same machine; and presenting from a
# second device uses the LAN address `next dev` prints on startup. Any of
# the three blocks every fetch, and the officer-facing result is
# "Cannot reach the data service" -- the honest fallback working exactly
# as designed, on a stage, with nothing wrong with the API.
#
# Regex rather than a longer allow_origins list: it covers both hostnames
# on both ports without enumerating four strings, and stays anchored so it
# cannot match a hostile origin that merely *contains* localhost
# (http://localhost.attacker.example would not match -- the $ anchor is
# what stops it). This regex alone is local-development-only by
# construction; a deployed frontend's origin is admitted only by explicit
# opt-in below, never by loosening this pattern.
_LOCAL_DEV_ORIGIN = r"^http://(localhost|127\.0\.0\.1):(3000|3001)$"

# 2026-09-14 incident: "Cannot reach the data service" on the live site,
# consistently, not just under a slow cold start -- an exact-match
# ALLOWED_ORIGINS listed only the stable aliases (nidhinetra.vercel.app,
# nidhinetra-krishpotanwars-projects.vercel.app), but the URL actually
# being tested was a per-deployment preview link
# (nidhinetra-5oscukrhx-krishpotanwars-projects.vercel.app). Vercel mints
# a brand-new, uniquely-hashed URL like that on every single deployment;
# there is no way to add each one to an exact-match list in advance, and
# testing against today's hash after tomorrow's deploy would just
# reproduce this same failure again. A regex for this project's own
# preview-URL shape closes the whole family at once, anchored exactly
# like _LOCAL_DEV_ORIGIN above: the trailing $ against the literal
# ".vercel.app" means only Vercel's own infrastructure can ever mint a
# matching hostname -- same reasoning that makes the localhost regex safe.
_VERCEL_PREVIEW_ORIGIN = r"^https://nidhinetra-[a-z0-9]+-krishpotanwars-projects\.vercel\.app$"

# The deployed frontend's exact origin(s), comma-separated, e.g.
# "https://nidhinetra.vercel.app,https://nidhinetra-<hash>.vercel.app".
# Unset by default, so a host with no ALLOWED_ORIGINS configured behaves
# exactly as before: local dev only. Exact strings, not a regex, so a
# production value can never accidentally admit more than it lists. Still
# useful alongside the regex above for a custom domain or another team's
# alias that doesn't fit this project's own preview-URL shape.
_PRODUCTION_ORIGINS = [
    origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",") if origin.strip()
]

# CORSMiddleware takes exactly one allow_origin_regex, so local dev and
# this project's Vercel previews are combined into one pattern rather
# than one replacing the other -- each half keeps its own anchors, so
# neither can widen what the other matches.
_ALLOW_ORIGIN_REGEX = f"{_LOCAL_DEV_ORIGIN}|{_VERCEL_PREVIEW_ORIGIN}"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_PRODUCTION_ORIGINS,
    allow_origin_regex=_ALLOW_ORIGIN_REGEX,
    # F-22: the app uses no cookies or other credentials, and the browser only
    # ever sends GET, POST with a JSON body, and the preflight OPTIONS.
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# F-17 companion: the rebuilt national graph is about 10 MB of JSON.
# Compressing responses (Starlette's gzip middleware, no new dependency) cuts
# that transfer roughly tenfold for the browser. Responses under 1 KB, like
# /health, are left alone.
app.add_middleware(GZipMiddleware, minimum_size=1024)

# F-22: baseline headers for a JSON API that is never framed and never needs to
# send a referrer. Added last, so this middleware is the outermost layer and
# also covers CORS preflight and error responses.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


@app.middleware("http")
async def _security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    for name, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


app.include_router(works.router)
app.include_router(graph.router)
app.include_router(stats.router)
app.include_router(refresh.router)
app.include_router(inspections.router)
app.include_router(entity_aliases.router)


def _envelope_error(status_code: int, message: str) -> JSONResponse:
    """Every error response uses the same house envelope as every success
    response (coding-style rules): {success, data, error, meta}, never a
    bare FastAPI default-error body.
    """
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "data": None, "error": message, "meta": None},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return _envelope_error(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    detail = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
    return _envelope_error(422, f"Invalid request: {detail}")


@app.exception_handler(SnapshotNotReadyError)
async def snapshot_not_ready_handler(request: Request, exc: SnapshotNotReadyError) -> JSONResponse:
    return _envelope_error(503, str(exc))


@app.exception_handler(SnapshotDowngradeError)
async def snapshot_downgrade_handler(request: Request, exc: SnapshotDowngradeError) -> JSONResponse:
    # Eng review, 2026-09-05: refresh on a machine whose data/raw/ cache is
    # empty (any machine but the one that pulled it, since data/raw/ is
    # gitignored) used to silently replace the real snapshot with the CP0
    # fixture. build_snapshot() now refuses instead of falling through to
    # the generic 500 handler -- a specific, honest message beats a bare
    # "Internal error" for a state an operator can actually act on.
    logger.warning("Refresh refused, would have downgraded the snapshot: %s", exc)
    return _envelope_error(
        409,
        "Refresh could not find a real data pull to rebuild from, and would "
        "have replaced the current data with the demo dataset. Showing the "
        "current data unchanged.",
    )


@app.exception_handler(StaleCacheError)
async def stale_cache_handler(request: Request, exc: StaleCacheError) -> JSONResponse:
    # F-01: the newest normalized cache predates the current contract, so a
    # rebuild from it would bring the IDA/IA mislabel back. Refused before
    # anything was written.
    logger.warning("Refresh refused, the cached normalized data is outdated: %s", exc)
    return _envelope_error(
        409,
        "Refresh found only an outdated cached data file and did not use it. "
        "Showing the current data unchanged.",
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return _envelope_error(500, "Internal error. Please try again.")


__all__ = ["app"]
