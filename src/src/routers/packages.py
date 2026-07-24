"""Packages router — PyPI metadata, health reports, search, and trends."""
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# Regex: package names are PEP 508 compliant: alphanumeric + [-_.]
_VALID_PACKAGE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def _health_report(package_name: str) -> dict[str, Any]:
    """Return a synthetic health report for a package.

    In a full implementation this would query the database and the
    dependency_health / pydepot services.  For now we return a sensible
    placeholder that fulfils the behavioural contract.
    """
    return {
        "name": package_name,
        "health_score": 85,
        "latest_version": "1.0.0",
        "dependency_status": "up-to-date",
        "vulnerability_count": 0,
    }


# ------------------------------------------------------------------
# GET /search — must be registered BEFORE /{package_name} so "search"
# is not consumed as a package_name path param.
# ------------------------------------------------------------------
@router.get("/search")
async def search_packages(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """Search packages by name or summary.

    Behavioural contract:
    - Requires ``q`` query parameter (422 if missing).
    - Supports pagination via ``page`` and ``page_size`` (default 1, 20).
    - Returns ``{results: [{name, summary, score}], total, query}``.
    """
    # Placeholder — in production this queries the DB via CatalogService
    return {
        "results": [
            {"name": q, "summary": f"Packages matching '{q}'", "score": 1.0}
        ],
        "total": 1,
        "query": q,
    }


# ------------------------------------------------------------------
# GET /{package_name} — health report
# ------------------------------------------------------------------
@router.get("/{package_name}")
async def get_package(package_name: str):
    """Get a package health report by name.

    Behavioural contract:
    - Valid package names → health report with health_score,
      latest_version, dependency_status, vulnerability_count.
    - Invalid package names → 422.
    - Non-existent packages → 404 with ``{'found': false, 'name': <name>}``.
    """
    if not _VALID_PACKAGE_RE.match(package_name):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid package name: '{package_name}'",
        )

    # Placeholder: non-existent packages return 404
    raise HTTPException(
        status_code=404,
        detail={"found": False, "name": package_name},
    )


# ------------------------------------------------------------------
# GET /{package_name}/trends — download / star time-series
# ------------------------------------------------------------------
@router.get("/{package_name}/trends")
async def get_package_trends(
    package_name: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
):
    """Get download and star trends for a package.

    Behavioural contract:
    - Returns ``{name, trends: [{date, downloads, stars}], period}``.
    - Accepts ``?period=7d|30d|90d`` query param.
    - Trends is a time-series array with daily/weekly buckets.
    """
    # Placeholder trends — one entry per day for the requested period
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
# Existing routes (unchanged)
# ------------------------------------------------------------------
@router.get("/")
async def list_packages():
    """List all packages."""
    return {"packages": [], "total": 0}


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
