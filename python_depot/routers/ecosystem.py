"""Ecosystem & Migration Hub router — package manager detection, stats, migration guides."""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.ecosystem.migration import MigrationGuideGenerator, SUPPORTED_MIGRATIONS
from python_depot.ecosystem.scanner import EcosystemScanner
from python_depot.ecosystem.stats import EcosystemStatsService

router = APIRouter()


@router.get("/api/v1/ecosystem/detect/{name}")
async def detect_package(
    name: str = Path(..., description="Package name on PyPI"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Detect package manager(s) supported by a package."""
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", name):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid package name: '{name}'. Must match PEP 508 naming convention.",
        )

    scanner = EcosystemScanner(db=db)
    result = await scanner.scan_package(name)

    if result.get("detection_tier") == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Package '{name}' not found on PyPI or could not be reached.",
        )

    return result


@router.get("/api/v1/ecosystem/stats")
async def ecosystem_stats(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Aggregated ecosystem adoption statistics."""
    service = EcosystemStatsService(db=db)
    return service.compute_stats()


@router.get("/api/v1/ecosystem/migration-guide/{name}")
async def migration_guide(
    name: str = Path(..., description="Package name"),
    from_manager: str = Query(..., alias="from", description="Source package manager"),
    to_manager: str = Query(..., alias="to", description="Target package manager"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Generate a migration guide between package managers for a package."""
    supported_keys = list(SUPPORTED_MIGRATIONS.keys())

    if (from_manager, to_manager) not in supported_keys:
        pairs_str = ", ".join(f"{f}→{t}" for f, t in supported_keys)
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported migration: {from_manager} → {to_manager}. "
                   f"Supported pairs: {pairs_str}",
        )

    generator = MigrationGuideGenerator(db=db)
    return generator.generate_guide(
        package=name,
        from_manager=from_manager,
        to_manager=to_manager,
    )


@router.get("/api/v1/ecosystem/compatibility")
async def compatibility_matrix(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Compatibility matrix across all scanned packages."""
    service = EcosystemStatsService(db=db)
    return service.get_compatibility_matrix(limit=limit, offset=offset)
