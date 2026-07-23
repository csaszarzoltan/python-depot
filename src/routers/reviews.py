"""Reviews router — submit, list, and get reviews."""
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class ReviewSubmit(BaseModel):
    """Request body for submitting a review."""
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: str = Field(..., min_length=1, description="Review comment")
    reviewer: str = Field(..., min_length=1, description="Reviewer name")


@router.get("/{package_name}")
async def list_reviews(package_name: str):
    """List reviews for a package."""
    return {"package": package_name, "reviews": [], "total": 0}


@router.post("/{package_name}", status_code=201)
async def submit_review(package_name: str, body: ReviewSubmit):
    """Submit a review for a package.

    Behavioural contract:
    - Accepts JSON body with rating (int 1-5), comment (str), reviewer (str).
    - Validates rating 1-5 (422 for invalid).
    - Returns 201 with review id and timestamp on success.
    """
    # Pydantic validates rating 1-5 automatically.
    # In production we would persist to the database.
    return {
        "package": package_name,
        "review_id": 1,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/{package_name}/{review_id}")
async def get_review(package_name: str, review_id: int):
    """Get a specific review."""
    return {"package": package_name, "review_id": review_id, "found": False}
