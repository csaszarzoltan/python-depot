"""Ratings router — backed by python_depot.ratings.service.RatingService."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.pydepot.models import Package
from python_depot.ratings.service import RatingService

router = APIRouter()


class RatingSubmit(BaseModel):
    """Request body for submitting a rating."""
    score: int = Field(..., ge=1, le=5, description="Rating score 1-5")
    user_id: str = Field("anonymous", description="User identifier")


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
async def get_ratings(
    package_name: str,
    service: RatingService = Depends(_get_rating_service),
):
    """Get ratings for a package via RatingService."""
    return service.get_ratings(package_name)


@router.post("/{package_name}")
async def submit_rating(
    package_name: str,
    body: RatingSubmit,
    db: Session = Depends(get_db),
    service: RatingService = Depends(_get_rating_service),
):
    """Submit a rating for a package via RatingService.

    Auto-creates a placeholder package entry if the package does not
    exist yet, so ratings can be submitted before PyPI sync.
    """
    _ensure_package(db, package_name)
    return service.submit_rating(package_name, body.user_id, body.score)


@router.get("/{package_name}/summary")
async def rating_summary(
    package_name: str,
    service: RatingService = Depends(_get_rating_service),
):
    """Get rating summary with distribution via RatingService."""
    return service.rating_summary(package_name)
