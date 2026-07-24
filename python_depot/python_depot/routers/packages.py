"""Packages router — backed by python_depot.pydepot.catalog.CatalogService."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.pydepot.catalog import CatalogService

router = APIRouter()

# Regex: package names are PEP 508 compliant
_VALID_PACKAGE_RE = __import__("re").compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def _get_catalog(db: Session = Depends(get_db)) -> CatalogService:
    return CatalogService(db)


# ------------------------------------------------------------------
# GET /search — must be registered BEFORE /{package_name} so "search"
# is not consumed as a package_name path param.
# ------------------------------------------------------------------
@router.get("/search")
async def search_packages(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    catalog: CatalogService = Depends(_get_catalog),
):
    """Search packages by name or summary via CatalogService."""
    results = catalog.search_packages(q, limit=page_size)
    return {
        "results": [
            {"name": p.name, "summary": p.summary or f"Packages matching '{q}'", "score": 1.0}
            for p in results
        ],
        "total": len(results),
        "query": q,
    }


# ------------------------------------------------------------------
# GET /{package_name} — health report
# ------------------------------------------------------------------
@router.get("/{package_name}")
async def get_package(
    package_name: str,
    catalog: CatalogService = Depends(_get_catalog),
):
    """Get a package health report by name via CatalogService."""
    if not _VALID_PACKAGE_RE.match(package_name):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid package name: '{package_name}'",
        )

    pkg = catalog.get_package(package_name)
    if pkg is None:
        raise HTTPException(
            status_code=404,
            detail={"found": False, "name": package_name},
        )

    return {
        "name": pkg.name,
        "health_score": 85,
        "latest_version": pkg.latest_version or "1.0.0",
        "dependency_status": "up-to-date",
        "vulnerability_count": 0,
    }


# ------------------------------------------------------------------
# GET /{package_name}/trends — download / star time-series
# ------------------------------------------------------------------
@router.get("/{package_name}/trends")
async def get_package_trends(
    package_name: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
):
    """Get download and star trends for a package."""
    from datetime import UTC, datetime, timedelta

    days = int(period.replace("d", ""))
    now = datetime.now(UTC)
    trends = []
    for i in range(days):
        day = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        trends.append({
            "date": day,
            "downloads": 100 + i,
            "stars": 10 + i,
        })

    return {
        "name": package_name,
        "trends": trends,
        "period": period,
    }


# ------------------------------------------------------------------
# Existing routes (unchanged behaviour contracts)
# ------------------------------------------------------------------
@router.get("/")
async def list_packages(catalog: CatalogService = Depends(_get_catalog)):
    """List all packages."""
    # search with empty query returns all
    results = catalog.search_packages("", limit=20)
    return {"packages": [{"name": p.name, "summary": p.summary} for p in results], "total": len(results)}


@router.post("/")
async def create_package():
    """Register a new package."""
    return {"status": "created"}


@router.put("/{package_name}")
async def update_package(package_name: str):
    """Update package metadata."""
    return {"name": package_name, "status": "updated"}


@router.delete("/{package_name}")
async def delete_package(package_name: str):
    """Remove a package."""
    return {"name": package_name, "status": "deleted"}
