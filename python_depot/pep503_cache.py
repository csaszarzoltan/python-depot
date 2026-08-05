"""PEP 503 caching proxy service (pre-dev stub).

Interface contract for the PEP 503 simple-index cache. Constants, the
``CacheConfig`` / ``SimpleIndexResult`` dataclasses and the
``CacheMissError`` exception below are real so interface tests can verify
the contract immediately; every behavioral method raises
``NotImplementedError`` until the developer implements this module.

Public API:
- ``normalize_package_name`` — PEP 503 normalization.
- ``validate_upstream_url`` — SSRF guard (scheme + host allowlist).
- ``PyPICacheService`` — simple-index cache/proxy service.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from python_depot.database import SessionLocal

__all__ = [
    "ALLOWED_HOSTS",
    "CacheConfig",
    "CacheMissError",
    "DEFAULT_MAX_CACHE_BYTES",
    "DEFAULT_TTL_SECONDS",
    "DEFAULT_UPSTREAM_TIMEOUT",
    "PYPI_FILES_HOST",
    "PYPI_SIMPLE_URL",
    "PyPICacheService",
    "SimpleIndexResult",
    "normalize_package_name",
    "validate_upstream_url",
]

PYPI_SIMPLE_URL = "https://pypi.org/simple/{package}/"
PYPI_FILES_HOST = "files.pythonhosted.org"
ALLOWED_HOSTS: tuple[str, ...] = (
    "pypi.org",
    "pypi.python.org",
    PYPI_FILES_HOST,
)
DEFAULT_TTL_SECONDS = 300
DEFAULT_MAX_CACHE_BYTES = 5 * 1024 * 1024 * 1024
DEFAULT_UPSTREAM_TIMEOUT = 10.0


class CacheMissError(Exception):
    """Raised when a package is not cached and upstream is unavailable."""


@dataclass
class CacheConfig:
    """Cache knobs; every default is overridable via PYTHONDEPOT_* env vars."""

    cache_dir: Path = field(
        default_factory=lambda: Path(os.getenv("PYTHONDEPOT_CACHE_DIR", ".pypi_cache"))
    )
    ttl_seconds: int = field(
        default_factory=lambda: int(
            os.getenv("PYTHONDEPOT_CACHE_TTL", str(DEFAULT_TTL_SECONDS))
        )
    )
    max_size_bytes: int = field(
        default_factory=lambda: int(
            os.getenv("PYTHONDEPOT_CACHE_MAX_BYTES", str(DEFAULT_MAX_CACHE_BYTES))
        )
    )
    offline_mode: bool = field(
        default_factory=lambda: os.getenv("PYTHONDEPOT_OFFLINE_MODE", "").lower()
        in {"1", "true", "yes"}
    )
    upstream_timeout: float = DEFAULT_UPSTREAM_TIMEOUT


@dataclass
class SimpleIndexResult:
    """Outcome of a simple-index lookup."""

    package: str
    versions: list[str]
    served_from_cache: bool


def normalize_package_name(name: str) -> str:
    """Normalize a package name per PEP 503 (lowercase, separators -> '-').

    Runs of ``-_.`` are collapsed into a single ``-`` and the result is
    lowercased (e.g. ``My.Package_Name`` -> ``my-package-name``).
    """
    raise NotImplementedError


def validate_upstream_url(
    url: str, allowed_hosts: tuple[str, ...] = ALLOWED_HOSTS
) -> bool:
    """SSRF guard: only http(s) schemes against allowlisted hosts pass."""
    raise NotImplementedError


class PyPICacheService:
    """Caching proxy in front of the PyPI PEP 503 simple index."""

    def __init__(
        self, config: CacheConfig | None = None, db: Session | None = None
    ) -> None:
        self.config = config or CacheConfig()
        self.db = db or SessionLocal()
        self._offline_mode: bool = self.config.offline_mode

    async def get_simple_index(self, package: str) -> SimpleIndexResult:
        """Return cached versions, or proxy upstream on a cache miss."""
        raise NotImplementedError

    async def fetch_upstream_index(self, package: str) -> str:
        """Fetch the raw upstream simple-index HTML for a package."""
        raise NotImplementedError

    def get_cached_versions(self, package: str) -> list[str]:
        """Return the stored version list (empty when uncached)."""
        raise NotImplementedError

    def is_cached(self, package: str) -> bool:
        """Whether a version list is cached for the package."""
        raise NotImplementedError

    def set_offline_mode(self, offline: bool) -> None:
        """Toggle cache-only offline fallback."""
        raise NotImplementedError

    def is_offline_mode(self) -> bool:
        """Whether cache-only offline fallback is enabled."""
        raise NotImplementedError

    async def get_artifact(self, package: str, filename: str) -> bytes | None:
        """Return a cached wheel/sdist artifact, or None when missing."""
        raise NotImplementedError

    def hit_rate(self) -> float:
        """Cache hit rate across all packages (0.0 with no traffic)."""
        raise NotImplementedError

    def bytes_served(self) -> int:
        """Total artifact bytes served from cache."""
        raise NotImplementedError

    def bytes_proxied(self) -> int:
        """Total artifact bytes proxied from upstream."""
        raise NotImplementedError

    def package_stats(self, package: str) -> dict[str, Any]:
        """Per-package hits/misses/bytes/versions."""
        raise NotImplementedError

    def overall_stats(self) -> dict[str, Any]:
        """Aggregate hit rate, bytes and per-package stats."""
        raise NotImplementedError
