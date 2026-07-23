"""Reviews router."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/{package_name}")
async def list_reviews(package_name: str):
    """List reviews for a package."""
    return {"package": package_name, "reviews": [], "total": 0}


@router.post("/{package_name}")
async def submit_review(package_name: str):
    """Submit a review for a package."""
    return {"package": package_name, "status": "reviewed"}


@router.get("/{package_name}/{review_id}")
async def get_review(package_name: str, review_id: int):
    """Get a specific review."""
    return {"package": package_name, "review_id": review_id, "found": False}
