"""PEP 503 caching proxy service.

Implements the caching proxy in front of the PyPI simple index:

- ``normalize_package_name`` — PEP 503 name normalization (the unique
  lookup key for cached version lists).
- ``validate_upstream_url`` — SSRF guard: only http(s) URLs against the
  allowlisted PyPI hosts pass.  ``fetch_upstream_index`` additionally
  reuses the repo-wide IP-range SSRF check from ``python_depot.api``
  (defense in depth).
- ``PyPICacheService`` — serves cached version lists on a hit, proxies
  upstream PyPI on a miss, persists the fetched list, applies the
  configured TTL, supports cache-only offline mode and exposes the
  analytics counters (hit rate, bytes served vs proxied, per-package
  stats).
- Artifact serving: ``get_artifact`` returns cached wheel/sdist bytes,
  ``fetch_artifact`` proxies a missing artifact from upstream, stores it
  on disk (via :class:`python_depot.artifact_store.ArtifactStore`) and
  records SQLite metadata (``CachedArtifact`` rows) for LRU/TTL/analytics.

Timestamps are stored UTC-naive on purpose: SQLite/SQLAlchemy has no
timezone support, so naive UTC round-trips exactly and TTL arithmetic is
deterministic.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.orm import Session

from python_depot.database import SessionLocal
from python_depot.models.pep503_cache import CachedArtifact, CachedPackage  # noqa: F401

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

#: Suffixes that identify a distribution filename in a simple-index href.
_ARTIFACT_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz", ".whl", ".zip", ".tar")


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
    """Outcome of a simple-index lookup.

    ``links`` carries the real upstream artifact URLs for the package
    (empty when only the version list is available, e.g. rows seeded
    without artifact metadata) so the router can render genuine
    download links.
    """

    package: str
    versions: list[str]
    served_from_cache: bool
    links: list[str] = field(default_factory=list)


def normalize_package_name(name: str) -> str:
    """Normalize a package name per PEP 503 (lowercase, separators -> '-').

    Runs of ``-_.`` are collapsed into a single ``-`` and the result is
    lowercased (e.g. ``My.Package_Name`` -> ``my-package-name``).
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def validate_upstream_url(
    url: str, allowed_hosts: tuple[str, ...] = ALLOWED_HOSTS
) -> bool:
    """SSRF guard: only http(s) schemes against allowlisted hosts pass.

    The hostname is matched exactly (no subdomain or trailing-dot tricks)
    against ``allowed_hosts``.  This is the first line of defence; the
    network fetch itself is additionally guarded by the repo-wide
    IP-range check (``python_depot.api.validate_url``).
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in allowed_hosts


def _strip_fragment(href: str) -> str:
    """Return the URL with any ``#fragment`` (e.g. ``#sha256=...``) removed."""
    return href.split("#", 1)[0]


def _filename_from_href(href: str) -> str:
    """Extract the distribution filename from a simple-index href."""
    return _strip_fragment(href).rstrip("/").rsplit("/", 1)[-1]


def _versions_from_html(html: str) -> list[str]:
    """Parse the version list out of upstream simple-index HTML.

    Each ``<a href>`` points at a distribution file; the version is the
    second ``-``-separated token of the filename, which per PEP 503
    encoding is the version component (``{name}-{version}-...``).
    """
    versions: list[str] = []
    for match in re.finditer(r'href="([^"]+)"', html):
        filename = _filename_from_href(match.group(1))
        for suffix in _ARTIFACT_SUFFIXES:
            if filename.endswith(suffix):
                filename = filename[: -len(suffix)]
                break
        parts = filename.split("-")
        if len(parts) >= 2 and parts[1][:1].isdigit():
            versions.append(parts[1])
    return sorted(set(versions))


def _links_from_html(html: str, base_url: str) -> dict[str, str]:
    """Map distribution filename -> absolute URL from simple-index HTML.

    Keys are the file names pip requests from the proxy; values are the
    upstream artifact URLs (host allowlisted by the caller before use).
    """
    links: dict[str, str] = {}
    for match in re.finditer(r'href="([^"]+)"', html):
        href = match.group(1)
        filename = _filename_from_href(href)
        if not filename or not filename.endswith(_ARTIFACT_SUFFIXES):
            continue
        links.setdefault(filename, urljoin(base_url, _strip_fragment(href)))
    return links


def _filename_matches_version(version: str, filename: str) -> bool:
    """Whether a distribution filename belongs to the given version.

    The version is matched as one dash-separated token of the filename
    (per PEP 503 the second token is the version): ``six-1.16.0.tar.gz``
    and ``numpy-2.0.0-cp312-...-any.whl`` both match their version.
    """
    name = filename
    for suffix in _ARTIFACT_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return version in name.split("-")


def _existing_ssrf_check(url: str) -> bool:
    """Apply the repo-wide IP-range SSRF protection.

    Imported lazily to avoid an import cycle: ``python_depot.api`` pulls
    in the router package which imports this module.
    """
    from python_depot.api import validate_url

    return validate_url(url)


class PyPICacheService:
    """Caching proxy in front of the PyPI PEP 503 simple index."""

    def __init__(
        self, config: CacheConfig | None = None, db: Session | None = None
    ) -> None:
        self.config = config or CacheConfig()
        self.db = db or SessionLocal()
        self._offline_mode: bool = self.config.offline_mode
        self._store: Any = None

    # ------------------------------------------------------------------
    # Simple index
    # ------------------------------------------------------------------
    async def get_simple_index(self, package: str) -> SimpleIndexResult:
        """Return cached versions, or proxy upstream on a cache miss.

        On a cache hit the stored version list is served and the hit
        counter bumped.  A row older than ``ttl_seconds`` (or with an
        empty version list) is treated as a miss and refetched.  In
        offline mode a missing/stale package raises ``CacheMissError``
        instead of touching the network.
        """
        norm = normalize_package_name(package)
        # SQLite stores naive datetimes (no tz support) — keep UTC-naive.
        now = datetime.now(UTC).replace(tzinfo=None)
        row = self.db.query(CachedPackage).filter_by(normalized_name=norm).first()
        if row is not None:
            versions = json.loads(row.versions_json or "[]")
            stale = False
            if row.fetched_at is not None:
                age = (now - row.fetched_at).total_seconds()
                stale = age > self.config.ttl_seconds
            if versions and not stale:
                row.hit_count += 1
                row.last_access_at = now
                self.db.commit()
                links = self._artifact_links(norm)
                return SimpleIndexResult(
                    package=package,
                    versions=versions,
                    served_from_cache=True,
                    links=links,
                )
        if self.is_offline_mode():
            raise CacheMissError(f"package '{package}' not cached and offline mode is enabled")
        html = await self.fetch_upstream_index(package)
        versions = _versions_from_html(html)
        if row is None:
            row = CachedPackage(package=package, normalized_name=norm, versions_json="[]")
            self.db.add(row)
            self.db.flush()  # apply column defaults (hit_count/miss_count/bytes = 0)
        row.versions_json = json.dumps(versions)
        row.fetched_at = now
        row.last_access_at = now
        row.miss_count += 1
        links = self._persist_artifact_links(norm, html)
        self.db.commit()
        return SimpleIndexResult(
            package=package, versions=versions, served_from_cache=False, links=links
        )

    async def fetch_upstream_index(self, package: str) -> str:
        """Fetch the raw upstream simple-index HTML for a package.

        The URL is built from the pinned template and validated twice:
        against the host allowlist and against the repo-wide IP-range
        SSRF check.  Any failure raises ``CacheMissError``.
        """
        norm = normalize_package_name(package)
        url = PYPI_SIMPLE_URL.format(package=norm)
        if not validate_upstream_url(url):
            raise CacheMissError(f"refusing unsafe upstream URL: {url}")
        if not _existing_ssrf_check(url):
            raise CacheMissError(f"refusing upstream URL failing IP-range SSRF check: {url}")
        async with httpx.AsyncClient(timeout=self.config.upstream_timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    def get_cached_versions(self, package: str) -> list[str]:
        """Return the stored version list (empty when uncached)."""
        norm = normalize_package_name(package)
        row = self.db.query(CachedPackage).filter_by(normalized_name=norm).first()
        if row is None:
            return []
        return json.loads(row.versions_json or "[]")

    def is_cached(self, package: str) -> bool:
        """Whether a version list is cached for the package."""
        return bool(self.get_cached_versions(package))

    # ------------------------------------------------------------------
    # Offline mode
    # ------------------------------------------------------------------
    def set_offline_mode(self, offline: bool) -> None:
        """Toggle cache-only offline fallback."""
        self._offline_mode = bool(offline)

    def is_offline_mode(self) -> bool:
        """Whether cache-only offline fallback is enabled."""
        return self._offline_mode

    # ------------------------------------------------------------------
    # Artifacts (wheel/sdist bytes)
    # ------------------------------------------------------------------
    @property
    def store(self) -> Any:
        """Lazily-created on-disk artifact store (keeps tests side-effect free)."""
        if self._store is None:
            from python_depot.artifact_store import ArtifactStore

            self._store = ArtifactStore(
                root_dir=self.config.cache_dir / "artifacts",
                max_size_bytes=self.config.max_size_bytes,
                ttl_seconds=self.config.ttl_seconds,
            )
        return self._store

    def _artifact_links(self, package: str) -> list[str]:
        """Persisted upstream artifact URLs for a package (metadata only)."""
        rows = self.db.query(CachedArtifact).filter_by(package_name=package).all()
        return [row.url for row in rows if row.url]

    def _persist_artifact_links(self, package: str, html: str) -> list[str]:
        """Upsert the upstream link map as CachedArtifact metadata rows.

        Returns the absolute artifact URLs so the caller can pass them
        straight into ``SimpleIndexResult``.
        """
        base_url = PYPI_SIMPLE_URL.format(package=package)
        links = _links_from_html(html, base_url)
        for filename, url in links.items():
            existing = (
                self.db.query(CachedArtifact)
                .filter_by(package_name=package, filename=filename)
                .first()
            )
            if existing is None:
                self.db.add(
                    CachedArtifact(package_name=package, filename=filename, url=url)
                )
        return list(links.values())

    async def get_artifact(self, package: str, filename: str) -> bytes | None:
        """Return a cached wheel/sdist artifact, or None when missing."""
        norm = normalize_package_name(package)
        if not self.store.contains(norm, filename):
            return None
        data = self.store.get(norm, filename)
        if data is None:
            return None
        now = datetime.now(UTC).replace(tzinfo=None)
        row = self.db.query(CachedArtifact).filter_by(
            package_name=norm, filename=filename
        ).first()
        if row is not None:
            row.last_access_at = now
        pkg_row = self.db.query(CachedPackage).filter_by(normalized_name=norm).first()
        if pkg_row is not None:
            pkg_row.bytes_served += len(data)
            pkg_row.last_access_at = now
        self.db.commit()
        return data

    async def fetch_artifact(self, package: str, filename: str) -> bytes | None:
        """Proxy a missing artifact from upstream, cache it, return bytes.

        The upstream URL comes from the persisted artifact metadata
        (populated when the simple index was fetched); if no metadata
        exists yet the filename is resolved against a fresh upstream
        index fetch.  The URL is validated against the SSRF guards, and
        on success the bytes are stored on disk with the ``CachedArtifact``
        row updated.  Returns None when the artifact is unavailable
        (offline mode, not found upstream, or refused by the SSRF guards).
        """
        norm = normalize_package_name(package)
        if self.is_offline_mode():
            return None
        row = (
            self.db.query(CachedArtifact)
            .filter_by(package_name=norm, filename=filename)
            .first()
        )
        url = row.url if row is not None else None
        if url is None:
            base_url = PYPI_SIMPLE_URL.format(package=norm)
            html = await self.fetch_upstream_index(package)
            url = _links_from_html(html, base_url).get(filename)
        if url is None:
            return None
        if not validate_upstream_url(url):
            return None
        if not _existing_ssrf_check(url):
            return None
        async with httpx.AsyncClient(timeout=self.config.upstream_timeout) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.content
        self.store.store(norm, filename, data)
        now = datetime.now(UTC).replace(tzinfo=None)
        if row is None:
            row = CachedArtifact(package_name=norm, filename=filename, url=url)
            self.db.add(row)
        row.size_bytes = len(data)
        row.stored_at = now
        row.last_access_at = now
        pkg_row = self.db.query(CachedPackage).filter_by(normalized_name=norm).first()
        if pkg_row is None:
            pkg_row = CachedPackage(package=package, normalized_name=norm, versions_json="[]")
            self.db.add(pkg_row)
            self.db.flush()
        pkg_row.bytes_proxied += len(data)
        self.db.commit()
        return data

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------
    def hit_rate(self) -> float:
        """Cache hit rate across all packages (0.0 with no traffic)."""
        rows = self.db.query(CachedPackage).all()
        hits = sum(r.hit_count for r in rows)
        misses = sum(r.miss_count for r in rows)
        total = hits + misses
        return 0.0 if total == 0 else hits / total

    def bytes_served(self) -> int:
        """Total artifact bytes served from cache."""
        return sum(r.bytes_served for r in self.db.query(CachedPackage).all())

    def bytes_proxied(self) -> int:
        """Total artifact bytes proxied from upstream."""
        return sum(r.bytes_proxied for r in self.db.query(CachedPackage).all())

    def package_stats(self, package: str) -> dict[str, Any]:
        """Per-package hits/misses/bytes/versions."""
        norm = normalize_package_name(package)
        row = self.db.query(CachedPackage).filter_by(normalized_name=norm).first()
        if row is None:
            return {"hits": 0, "misses": 0, "bytes_served": 0, "bytes_proxied": 0, "versions": []}
        return {
            "hits": row.hit_count,
            "misses": row.miss_count,
            "bytes_served": row.bytes_served,
            "bytes_proxied": row.bytes_proxied,
            "versions": json.loads(row.versions_json or "[]"),
        }

    def overall_stats(self) -> dict[str, Any]:
        """Aggregate hit rate, bytes and per-package stats."""
        rows = self.db.query(CachedPackage).all()
        per_package = {r.normalized_name: self.package_stats(r.package) for r in rows}
        return {
            "hit_rate": self.hit_rate(),
            "bytes_served": self.bytes_served(),
            "bytes_proxied": self.bytes_proxied(),
            "per_package": per_package,
        }
