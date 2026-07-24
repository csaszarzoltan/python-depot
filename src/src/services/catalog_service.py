"""Catalog service — PyPI Simple API client, metadata fetcher, SQLite storage."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import aiohttp
from sqlalchemy.orm import Session

from src.models.package import Package

logger = logging.getLogger(__name__)

PYPI_JSON_API = "https://pypi.org/pypi/{name}/json"
PYPI_SIMPLE_API = "https://pypi.org/simple/{name}/"
RATE_LIMIT_DELAY = 1.0  # seconds between requests


class CatalogService:
    """Manages package catalog: fetching from PyPI, storing locally, searching."""

    def __init__(self, db: Session) -> None:
        """Initialize with a database session.

        Args:
            db: SQLAlchemy synchronous session.
        """
        self.db = db

    async def fetch_package_metadata(self, name: str) -> dict[str, Any] | None:
        """Fetch package metadata from PyPI JSON API.

        Args:
            name: Package name on PyPI.

        Returns:
            Metadata dict or None if not found.
        """
        url = PYPI_JSON_API.format(name=name)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 404:
                        logger.warning("Package %s not found on PyPI", name)
                        return None
                    resp.raise_for_status()
                    return await resp.json()
        except (TimeoutError, aiohttp.ClientError) as exc:
            logger.error("Failed to fetch metadata for %s: %s", name, exc)
            return None

    def store_package(self, metadata: dict[str, Any]) -> Package:
        """Store or update a package in the database from PyPI metadata.

        Args:
            metadata: Raw JSON metadata from PyPI.

        Returns:
            The stored Package instance.
        """
        info = metadata.get("info", {})
        name = info.get("name", "")
        version = info.get("version", "")

        existing = self.db.query(Package).filter(Package.name == name).first()
        if existing:
            existing.summary = info.get("summary")
            existing.description = info.get("description")
            existing.homepage = info.get("home_page")
            existing.author = info.get("author")
            existing.license = info.get("license")
            existing.latest_version = version
            existing.updated_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        pkg = Package(
            name=name,
            summary=info.get("summary"),
            description=info.get("description"),
            homepage=info.get("home_page"),
            repository=info.get("project_url") or (info.get("project_urls") or {}).get("Source"),
            author=info.get("author"),
            license=info.get("license"),
            latest_version=version,
            pypi_url=f"https://pypi.org/project/{name}/",
        )
        self.db.add(pkg)
        self.db.commit()
        self.db.refresh(pkg)
        return pkg

    async def sync_package(self, name: str) -> Package | None:
        """Fetch and store a single package.

        Args:
            name: Package name.

        Returns:
            Stored Package or None on failure.
        """
        metadata = await self.fetch_package_metadata(name)
        if metadata is None:
            return None
        return self.store_package(metadata)

    def search_packages(self, query: str, limit: int = 20) -> list[Package]:
        """Search packages by name prefix or summary text.

        Args:
            query: Search string.
            limit: Max results.

        Returns:
            List of matching Package instances.
        """
        q = f"%{query}%"
        return (
            self.db.query(Package)
            .filter(Package.name.ilike(q) | Package.summary.ilike(q))
            .limit(limit)
            .all()
        )

    def get_package(self, name: str) -> Package | None:
        """Get a package by exact name.

        Args:
            name: Package name.

        Returns:
            Package or None.
        """
        return self.db.query(Package).filter(Package.name == name).first()
