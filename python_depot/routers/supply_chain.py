"""Supply-chain typosquatting detection router.

REST API endpoints for the supply-chain attack detection feature:

- GET /api/v1/supply-chain/check?package=NAME — verdict for one package
- GET /api/v1/supply-chain/scan            — verdicts for the dependency set

Handlers build a ``SupplyChainScanner`` fed with real PyPI metadata,
persist verdicts through ``store_verdict`` / ``store_verdicts`` and fire
alerts for newly detected suspicious packages via ``SupplyChainAlerter``
(exactly-once semantics, DB-backed).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.supply_chain import (
    POPULAR_PACKAGES,
    MaliciousFeed,
    PackageInfo,
    SupplyChainAlerter,
    SupplyChainScanner,
    fetch_package_info,
    store_verdict,
    store_verdicts,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Scores at or above this threshold are considered suspicious and trigger
# an alert attempt on scan.
SUSPICIOUS_SCORE = 60

# Configuration env vars (repo convention: PYTHONDEPOT_* prefix read via
# os.getenv with documented defaults — see routers/product.py).
WEBHOOK_URL_ENV = "PYTHONDEPOT_SUPPLY_CHAIN_WEBHOOK_URL"
BLOCKLIST_ENV = "PYTHONDEPOT_SUPPLY_CHAIN_BLOCKLIST"

# Bound concurrent PyPI metadata fetches so a /scan of 20 packages does
# not open dozens of parallel outbound connections.
_FETCH_SEMAPHORE = asyncio.Semaphore(5)


def _webhook_url() -> str | None:
    """Return the configured alert webhook URL (None when unset)."""
    return os.getenv(WEBHOOK_URL_ENV) or None


def _default_blocklist() -> list[str]:
    """Return the configured known-malicious blocklist (comma-separated)."""
    raw = os.getenv(BLOCKLIST_ENV, "")
    return [name.strip() for name in raw.split(",") if name.strip()]


def _scanner() -> SupplyChainScanner:
    """Build a scanner with a feed seeded from the configured blocklist."""
    return SupplyChainScanner(feed=MaliciousFeed(blocklist=_default_blocklist()))


async def _safe_fetch(name: str) -> PackageInfo | None:
    """Fetch real PyPI metadata; any failure degrades to unknown data."""
    try:
        async with _FETCH_SEMAPHORE:
            return await fetch_package_info(name)
    except Exception:
        logger.warning("Metadata fetch failed for %s — scanning without it", name)
        return None


def _verdict_payload(verdict) -> dict[str, Any]:
    """Convert a SupplyChainVerdict into the public JSON shape."""
    return {
        "package": verdict.package,
        "score": verdict.score,
        "reasons": verdict.reasons,
    }


@router.get("/api/v1/supply-chain/check")
async def check_supply_chain(
    package: str = Query(
        min_length=1,
        max_length=200,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return a typosquatting verdict for a single package.

    The package name is validated (1-200 chars, ``[A-Za-z0-9._-]``) so
    the similarity engine can never be CPU-amplified by oversized or
    malformed input (F1). Real PyPI metadata feeds the download /
    freshness heuristics; unknown data never produces a bogus reason (F2).

    Response JSON:
        package: The scanned package name.
        score: Integer risk score 0-100 (higher = more suspicious).
        reasons: List of human-readable detection reasons.
    """
    info = await _safe_fetch(package)
    verdict = _scanner().scan(package, info)
    store_verdict(db, verdict)
    return _verdict_payload(verdict)


@router.get("/api/v1/supply-chain/scan")
async def scan_supply_chain(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Scan the dependency set and return per-package verdicts.

    Verdicts are persisted in a single batch commit (F5); suspicious
    packages trigger one webhook alert per package via a single alerter
    instance with DB-backed exactly-once dedup (F3/F4).

    Response JSON:
        verdicts: List of verdict objects (package, score, reasons).
        scanned_at: ISO-8601 timestamp of the scan.
    """
    scanner = _scanner()
    infos = await asyncio.gather(*(_safe_fetch(p) for p in POPULAR_PACKAGES))
    verdicts = [
        scanner.scan(package, info)
        for package, info in zip(POPULAR_PACKAGES, infos)
    ]
    store_verdicts(db, verdicts)

    alerter = SupplyChainAlerter(db=db, webhook_url=_webhook_url())
    for verdict in verdicts:
        if verdict.score >= SUSPICIOUS_SCORE:
            await alerter.notify_new_suspicious(verdict)

    return {
        "verdicts": [_verdict_payload(v) for v in verdicts],
        "scanned_at": datetime.now(UTC).isoformat(),
    }
