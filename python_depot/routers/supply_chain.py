"""Supply-chain typosquatting detection router.

REST API endpoints for the supply-chain attack detection feature:

- GET /api/v1/supply-chain/check?package=NAME — verdict for one package
- GET /api/v1/supply-chain/scan            — verdicts for the dependency set

Handlers build a ``SupplyChainScanner``, persist verdicts through
``store_verdict`` and fire alerts for newly detected suspicious packages
via ``SupplyChainAlerter`` (exactly-once semantics).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.supply_chain import (
    POPULAR_PACKAGES,
    SupplyChainAlerter,
    SupplyChainScanner,
    store_verdict,
)

router = APIRouter()

# Scores at or above this threshold are considered suspicious and trigger
# an alert attempt on scan.
SUSPICIOUS_SCORE = 60


def _scanner() -> SupplyChainScanner:
    """Build a scanner with the default engine and feed."""
    return SupplyChainScanner()


def _verdict_payload(verdict) -> dict[str, Any]:
    """Convert a SupplyChainVerdict into the public JSON shape."""
    return {
        "package": verdict.package,
        "score": verdict.score,
        "reasons": verdict.reasons,
    }


@router.get("/api/v1/supply-chain/check")
async def check_supply_chain(
    package: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Return a typosquatting verdict for a single package.

    Response JSON:
        package: The scanned package name.
        score: Integer risk score 0-100 (higher = more suspicious).
        reasons: List of human-readable detection reasons.
    """
    verdict = _scanner().scan(package)
    store_verdict(db, verdict)
    return _verdict_payload(verdict)


@router.get("/api/v1/supply-chain/scan")
async def scan_supply_chain(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Scan the dependency set and return per-package verdicts.

    Response JSON:
        verdicts: List of verdict objects (package, score, reasons).
        scanned_at: ISO-8601 timestamp of the scan.
    """
    scanner = _scanner()
    verdicts = scanner.scan_many(POPULAR_PACKAGES)
    for verdict in verdicts:
        store_verdict(db, verdict)
        if verdict.score >= SUSPICIOUS_SCORE:
            alerter = SupplyChainAlerter(db=db)
            await alerter.notify_new_suspicious(verdict)
    return {
        "verdicts": [_verdict_payload(v) for v in verdicts],
        "scanned_at": datetime.now(UTC).isoformat(),
    }
