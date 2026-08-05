"""PEP 503 caching proxy API router.

Endpoints (``router`` — 3 routes, contract-pinned):
- GET  /simple/{package}/      — PEP 503 simple index (cache hit /
                                 upstream proxy / offline 503)
- GET  /api/v1/cache/analytics — hit rate, bytes served vs proxied,
                                 per-package stats
- POST /api/v1/cache/warmup    — prefetch top-N packages

``artifact_router`` adds the artifact download endpoint
(``GET /simple/{package}/{filename}``) that serves cached wheel/sdist
bytes and proxies missing artifacts from upstream through the cache.
It lives on a separate router so the contract-pinned 3-route ``router``
is untouched; ``create_proxy_app()`` wires both into a standalone
FastAPI app suitable for ``uvicorn`` (this is how the end-to-end
``pip install --index-url http://127.0.0.1:<port>/simple/`` integration
test runs the proxy).

Note: the production ``create_app()`` deliberately does NOT mount these
routers — ``tests/test_pre_dev_contract.py`` pins the full app route
set.  Deployments that want the proxy on the main app should include
``pep503.router`` / ``pep503.artifact_router`` explicitly.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from html import escape
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from python_depot.database import init_db
from python_depot.pep503_cache import (
    CacheMissError,
    PyPICacheService,
    _filename_matches_version,
)
from python_depot.warmup import TOP_PACKAGES, WarmupService

__all__ = [
    "WarmupRequest",
    "artifact_router",
    "cache_analytics",
    "cache_warmup",
    "create_proxy_app",
    "router",
    "serve_artifact",
    "serve_simple_index",
]

router = APIRouter()
artifact_router = APIRouter()


class WarmupRequest(BaseModel):
    """Body of POST /api/v1/cache/warmup."""

    top_n: int = Field(10, ge=1, le=1000)
    packages: list[str] | None = Field(None)


def _get_cache_service() -> PyPICacheService:
    return PyPICacheService()


def _link_filename(package: str, version: str) -> str:
    """Deterministic wheel filename for a version (resolved on download)."""
    return f"{package}-{version}-py3-none-any.whl"


def _basename(url: str) -> str:
    """Leaf filename of an artifact URL (fragment stripped)."""
    return url.split("#", 1)[0].rstrip("/").rsplit("/", 1)[-1]


@router.get("/simple/{package}/")
async def serve_simple_index(
    package: str,
    service: PyPICacheService = Depends(_get_cache_service),
) -> Any:
    """PEP 503 simple index: cached versions, else proxy upstream.

    Links are the package's real distribution files (from the cached
    upstream link map), rewritten to point at the proxy's own artifact
    endpoint so downloads flow through the cache and stay installable
    offline.  When no link map is available (e.g. rows seeded without
    artifact metadata) deterministic wheel/sdist links are emitted.
    """
    try:
        result = await service.get_simple_index(package)
    except CacheMissError:
        raise HTTPException(
            status_code=503,
            detail="cache miss: package not cached and upstream unreachable (offline mode)",
        )
    # B1: every value interpolated into the HTML (package name, artifact
    # filenames) is attacker-controllable via the URL path or the upstream
    # link map — escape all of it so `<script>`/`"` cannot break out of
    # elements or attributes (reflected/stored XSS for browser users).
    package_escaped = escape(result.package)
    html = f"<!DOCTYPE html><html><head><title>Links for {package_escaped}</title></head><body>"
    html += f"<h1>Links for {package_escaped}</h1>"
    for version in result.versions:
        matched = [
            url for url in result.links if _filename_matches_version(version, _basename(url))
        ]
        if not matched:
            for filename in (
                _link_filename(result.package, version),
                f"{result.package}-{version}.tar.gz",
            ):
                filename_escaped = escape(filename)
                html += (
                    f'<a href="/simple/{package_escaped}/{filename_escaped}">'
                    f"{filename_escaped}</a><br>"
                )
            continue
        for url in matched:
            filename_escaped = escape(_basename(url))
            html += (
                f'<a href="/simple/{package_escaped}/{filename_escaped}">'
                f"{filename_escaped}</a><br>"
            )
    html += "</body></html>"
    return HTMLResponse(content=html)


@router.get("/api/v1/cache/analytics")
async def cache_analytics(
    service: PyPICacheService = Depends(_get_cache_service),
) -> dict[str, Any]:
    """Cache analytics: hit rate, bytes served vs proxied, per-package stats."""
    return service.overall_stats()


@router.post("/api/v1/cache/warmup")
async def cache_warmup(
    body: WarmupRequest,
    service: PyPICacheService = Depends(_get_cache_service),
) -> dict[str, Any]:
    """Prefetch top-N packages (or an explicit list) into the cache."""
    warmer = WarmupService(cache=service, top_packages=TOP_PACKAGES)
    if body.packages:
        result = await warmer.prefetch(body.packages)
    else:
        result = await warmer.prefetch_top(body.top_n)
    return {"requested": result.requested, "cached": result.cached, "failed": result.failed}


@artifact_router.get("/simple/{package}/{filename}")
async def serve_artifact(
    package: str,
    filename: str,
    service: PyPICacheService = Depends(_get_cache_service),
) -> Response:
    """Serve cached artifact bytes; proxy and cache them on a miss."""
    data = await service.get_artifact(package, filename)
    if data is None and not service.is_offline_mode():
        data = await service.fetch_artifact(package, filename)
    if data is None:
        raise HTTPException(
            status_code=503,
            detail=f"artifact '{filename}' not cached and upstream unreachable",
        )
    return Response(content=data, media_type="application/octet-stream")


@asynccontextmanager
async def _proxy_lifespan(_application: FastAPI):
    """Create the cache tables on proxy startup."""
    init_db()
    yield


def create_proxy_app() -> FastAPI:
    """Standalone FastAPI app exposing the PEP 503 caching proxy.

    Run with ``uvicorn python_depot.routers.pep503:create_proxy_app --factory``
    (or ``--factory python_depot.routers.pep503:create_proxy_app``).
    """
    application = FastAPI(title="PythonDepot PyPI Caching Proxy", lifespan=_proxy_lifespan)
    application.include_router(router, prefix="")
    application.include_router(artifact_router, prefix="")
    return application
