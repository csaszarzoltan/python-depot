"""Analytics router."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/trending")
async def trending_packages():
    """Get trending packages by view count."""
    return {"trending": [], "period": "7d"}


@router.get("/popular")
async def popular_packages():
    """Get most popular packages."""
    return {"popular": []}


@router.post("/events")
async def track_event():
    """Track an analytics event."""
    return {"status": "tracked"}


@router.get("/stats/{package_name}")
async def package_stats(package_name: str):
    """Get analytics stats for a package."""
    return {"package": package_name, "views": 0, "installs": 0}
