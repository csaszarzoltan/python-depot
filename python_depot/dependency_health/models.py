"""Vulnerability scan and alert models for dependency_health."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from python_depot.database import Base


class VulnerabilityScan(Base):
    """Result of a vulnerability scan for a package version."""

    __tablename__ = "vulnerability_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("packages.id"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    scanner: Mapped[str] = mapped_column(String(100), nullable=False, default="safety")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="clean"
    )  # clean, vulnerable, unknown
    vuln_count: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )


class VulnerabilityAlert(Base):
    """Alert record for a newly discovered vulnerability.

    Created when a scan detects a vulnerability that was not present
    in the previous scan of the same package.
    """

    __tablename__ = "vulnerability_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("packages.id"), nullable=False, index=True
    )
    vuln_id: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MEDIUM"
    )  # CRITICAL, HIGH, MEDIUM, LOW
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, sent, failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True
    )
