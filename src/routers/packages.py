"""Packages router."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_packages():
    """List all packages."""
    return {"packages": [], "total": 0}


@router.get("/{package_name}")
async def get_package(package_name: str):
    """Get a package by name."""
    return {"name": package_name, "found": False}


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
