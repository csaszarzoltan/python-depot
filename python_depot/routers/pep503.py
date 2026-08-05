"""PEP 503 caching proxy API router (pre-dev stub).

Routes are registered with the documented paths and the ``WarmupRequest``
body model is real (request validation runs before handler logic), so
interface tests pass immediately; handlers raise ``NotImplementedError``
until the developer implements this module.

Endpoints:
- GET  /simple/{package}/      — PEP 503 simple index (cache hit /
                                 upstream proxy / offline 503)
- GET  /api/v1/cache/analytics — hit rate, bytes served vs proxied,
                                 per-package stats
- POST /api/v1/cache/warmup    — prefetch top-N packages
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from python_depot.pep503_cache import PyPICacheService

__all__ = [
    "WarmupRequest",
    "cache_analytics",
    "cache_warmup",
    "router",
    "serve_simple_index",
]

router = APIRouter()


class WarmupRequest(BaseModel):
    """Body of POST /api/v1/cache/warmup."""

    top_n: int = Field(10, ge=1, le=1000)
    packages: list[str] | None = Field(None)


def _get_cache_service() -> PyPICacheService:
    return PyPICacheService()


@router.get("/simple/{package}/")
async def serve_simple_index(
    package: str,
    service: PyPICacheService = Depends(_get_cache_service),
) -> Any:
    raise NotImplementedError


@router.get("/api/v1/cache/analytics")
async def cache_analytics(
    service: PyPICacheService = Depends(_get_cache_service),
) -> dict[str, Any]:
    raise NotImplementedError


@router.post("/api/v1/cache/warmup")
async def cache_warmup(
    body: WarmupRequest,
    service: PyPICacheService = Depends(_get_cache_service),
) -> dict[str, Any]:
    raise NotImplementedError
