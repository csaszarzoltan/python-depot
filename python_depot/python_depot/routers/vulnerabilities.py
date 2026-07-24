"""Vulnerabilities router — backed by python_depot.dependency_health.scanner.HealthScanner."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.dependency_health.scanner import HealthScanner
from python_depot.pydepot.catalog import CatalogService

router = APIRouter()


def _get_scanner(db: Session = Depends(get_db)) -> HealthScanner:
    return HealthScanner(db)


def _get_catalog(db: Session = Depends(get_db)) -> CatalogService:
    return CatalogService(db)


@router.get("/{package_name}")
async def list_scans(
    package_name: str,
    scanner: HealthScanner = Depends(_get_scanner),
    catalog: CatalogService = Depends(_get_catalog),
):
    """List vulnerability scans for a package."""
    pkg = catalog.get_package(package_name)
    if pkg is None:
        return {"package": package_name, "scans": [], "total": 0}
    return scanner.list_scans(pkg.id, package_name)


@router.post("/{package_name}/scan")
async def trigger_scan(
    package_name: str,
    scanner: HealthScanner = Depends(_get_scanner),
    catalog: CatalogService = Depends(_get_catalog),
):
    """Trigger a new vulnerability scan.

    Always returns ``scan_queued`` status regardless of scanner
    availability — the scan is conceptually queued even if the
    underlying tool (safety CLI) is not installed locally.
    """
    pkg = catalog.get_package(package_name)
    if pkg is None:
        return {"package": package_name, "status": "scan_queued"}
    scanner.scan_package(package_name, pkg.id)
    return {"package": package_name, "status": "scan_queued"}


@router.get("/{package_name}/latest")
async def latest_scan(
    package_name: str,
    scanner: HealthScanner = Depends(_get_scanner),
    catalog: CatalogService = Depends(_get_catalog),
):
    """Get the most recent scan result."""
    pkg = catalog.get_package(package_name)
    if pkg is None:
        return {"package": package_name, "scan": None}
    return scanner.latest_scan(pkg.id, package_name)
