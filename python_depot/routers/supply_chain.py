"""Supply-chain typosquatting detection router (pre-dev stub).

REST API endpoints for the supply-chain attack detection feature:

- GET /api/v1/supply-chain/check?package=NAME — verdict for one package
- GET /api/v1/supply-chain/scan            — verdicts for the dependency set

Both handlers currently raise ``NotImplementedError``; the developer
implements them (and registers this router in ``python_depot/api.py``).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from python_depot.database import get_db

router = APIRouter()


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
    raise NotImplementedError("supply-chain check not implemented")


@router.get("/api/v1/supply-chain/scan")
async def scan_supply_chain(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Scan the dependency set and return per-package verdicts.

    Response JSON:
        verdicts: List of verdict objects (package, score, reasons).
        scanned_at: ISO-8601 timestamp of the scan.
    """
    raise NotImplementedError("supply-chain scan not implemented")
