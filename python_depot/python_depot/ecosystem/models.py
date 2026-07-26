"""SQLAlchemy models for the Ecosystem & Migration Hub.

Stores per-package scan results and aggregated ecosystem snapshots.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from python_depot.database import Base


class PackageScan(Base):
    """Stores the latest ecosystem scan result for a single package."""

    __tablename__ = "package_scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_name = Column(String(255), unique=True, nullable=False, index=True)
    managers_supported = Column(Text, nullable=False)  # JSON list e.g. '["pip","uv"]'
    detection_tier = Column(Integer, nullable=False, default=1)  # 1 = PyPI, 2 = repo
    build_backend = Column(String(255), nullable=True)
    lockfile_type = Column(String(100), nullable=True)
    has_pyproject_toml = Column(Integer, nullable=False, default=0)  # boolean
    scanned_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return f"<PackageScan {self.package_name} tier={self.detection_tier}>"


class EcosystemStatsSnapshot(Base):
    """Periodic snapshot of ecosystem-wide adoption statistics."""

    __tablename__ = "ecosystem_stats_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    total_scanned = Column(Integer, nullable=False, default=0)
    pip_only_count = Column(Integer, nullable=False, default=0)
    uv_ready_count = Column(Integer, nullable=False, default=0)
    poetry_compatible_count = Column(Integer, nullable=False, default=0)
    pip_tools_compatible_count = Column(Integer, nullable=False, default=0)
    snapshot_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
