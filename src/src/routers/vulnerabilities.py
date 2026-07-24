"""Vulnerabilities router."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/{package_name}")
async def list_scans(package_name: str):
    """List vulnerability scans for a package."""
    return {"package": package_name, "scans": [], "total": 0}


@router.post("/{package_name}/scan")
async def trigger_scan(package_name: str):
    """Trigger a new vulnerability scan."""
    return {"package": package_name, "status": "scan_queued"}


@router.get("/{package_name}/latest")
async def latest_scan(package_name: str):
    """Get the most recent scan result."""
    return {"package": package_name, "scan": None}
