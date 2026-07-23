"""Ratings router."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/{package_name}")
async def get_ratings(package_name: str):
    """Get ratings for a package."""
    return {"package": package_name, "ratings": [], "average": 0.0}


@router.post("/{package_name}")
async def submit_rating(package_name: str):
    """Submit a rating for a package."""
    return {"package": package_name, "status": "rated"}


@router.get("/{package_name}/summary")
async def rating_summary(package_name: str):
    """Get rating summary with distribution."""
    return {"package": package_name, "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}
