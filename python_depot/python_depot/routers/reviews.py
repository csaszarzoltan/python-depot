"""Reviews router — backed by python_depot.ratings.service.RatingService."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.pydepot.models import Package
from python_depot.ratings.service import RatingService

router = APIRouter()


class ReviewSubmit(BaseModel):
    """Request body for submitting a review."""
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: str = Field(..., min_length=1, description="Review comment")
    reviewer: str = Field(..., min_length=1, description="Reviewer name")


def _get_rating_service(db: Session = Depends(get_db)) -> RatingService:
    return RatingService(db)


def _ensure_package(db: Session, package_name: str) -> None:
    """Create a minimal package record if one does not exist."""
    existing = db.query(Package).filter(Package.name == package_name).first()
    if existing is None:
        pkg = Package(
            name=package_name,
            summary=f"Auto-created placeholder for {package_name}",
            latest_version="0.0.0",
        )
        db.add(pkg)
        db.commit()


@router.get("/{package_name}")
async def list_reviews(
    package_name: str,
    service: RatingService = Depends(_get_rating_service),
):
    """List reviews for a package via RatingService."""
    return service.list_reviews(package_name)


@router.post("/{package_name}", status_code=201)
async def submit_review(
    package_name: str,
    body: ReviewSubmit,
    db: Session = Depends(get_db),
    service: RatingService = Depends(_get_rating_service),
):
    """Submit a review for a package via RatingService."""
    _ensure_package(db, package_name)
    result = service.submit_review(
        package_name,
        user_id=body.reviewer,
        title=f"Review by {body.reviewer}",
        body=body.comment,
    )
    # Add timestamp for backward compat with pre-dev contract tests
    if "timestamp" not in result:
        result["timestamp"] = datetime.now(UTC).isoformat()
    return result


@router.get("/{package_name}/{review_id}")
async def get_review(
    package_name: str,
    review_id: int,
    service: RatingService = Depends(_get_rating_service),
):
    """Get a specific review via RatingService."""
    return service.get_review(package_name, review_id)
