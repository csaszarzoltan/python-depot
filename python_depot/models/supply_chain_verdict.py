"""Supply-chain typosquatting verdict model (pre-dev stub — schema only).

The table schema below is part of the interface contract and is therefore
already real so interface tests can verify table/column registration
immediately. No behavioral logic lives here — detection, scoring and
persistence are implemented in ``python_depot.supply_chain`` by the
developer (currently raising NotImplementedError).
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from python_depot.database import Base


class SupplyChainVerdict(Base):
    """Verdict for a package scanned for supply-chain typosquatting risk.

    Fields:
        package: The scanned package name.
        score: Integer risk score 0-100 (higher = more suspicious).
        reasons: Human-readable list of detection reasons, stored as a
                 JSON-encoded string (Text column), consistent with the
                 repo's existing ``details`` column convention.
        detected_at: UTC timestamp of when the verdict was produced.
        notified: Whether an alert webhook has already fired for this
                  package — DB-backed exactly-once dedup for the
                  SupplyChainAlerter (mirrors VulnerabilityAlert's
                  ``webhook_status`` pattern).
    """

    __tablename__ = "supply_chain_verdicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    notified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
