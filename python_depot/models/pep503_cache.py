"""PEP 503 caching proxy database models (pre-dev stub — schema only).

The table schemas below are part of the interface contract and are
therefore already real so interface tests can verify table/column
registration immediately. No behavioral logic lives here — caching,
proxying, eviction and analytics are implemented in
``python_depot.pep503_cache`` and ``python_depot.artifact_store`` by the
developer (currently raising NotImplementedError).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from python_depot.database import Base

__all__ = ["CachedPackage", "CachedArtifact"]


class CachedPackage(Base):
    """Per-package PEP 503 simple-index cache row.

    Fields:
        package: The package name as requested (original case).
        normalized_name: PEP 503-normalized name (unique lookup key).
        versions_json: JSON-encoded list of cached version strings.
        fetched_at: UTC timestamp of the last successful upstream fetch.
        last_access_at: UTC timestamp of the last time the cached index
            was served.
        hit_count: Number of times the cached index was served.
        miss_count: Number of times upstream had to be proxied.
        bytes_served: Bytes of artifact content served from cache.
        bytes_proxied: Bytes proxied from upstream for this package.
    """

    __tablename__ = "pep503_cached_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True, index=True
    )
    versions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_access_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    miss_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bytes_served: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bytes_proxied: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CachedArtifact(Base):
    """Wheel/sdist artifact metadata row (bytes live on disk).

    Fields:
        package_name: PEP 503-normalized package name the artifact belongs to.
        filename: Artifact filename on disk
            (e.g. requests-2.32.0-py3-none-any.whl).
        url: Upstream URL the artifact was proxied from
            (files.pythonhosted.org).
        size_bytes: Artifact size in bytes.
        stored_at: UTC timestamp of when the artifact was cached.
        last_access_at: UTC timestamp of the last serve/download (LRU key).
    """

    __tablename__ = "pep503_cached_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_access_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
