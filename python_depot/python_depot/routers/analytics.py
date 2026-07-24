"""Analytics router — backed by python_depot.pydepot.analytics.AnalyticsService."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.pydepot.analytics import AnalyticsService

router = APIRouter()


class TrackEventBody(BaseModel):
    """Request body for tracking an analytics event."""
    event_type: str = Field(..., description="Type of event (view, search, install_click)")
    package_name: str | None = Field(None, description="Related package name")
    user_id: str | None = Field(None, description="User identifier")
    metadata_json: str | None = Field(None, description="Optional JSON metadata")


def _get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/trending")
async def trending_packages(
    service: AnalyticsService = Depends(_get_analytics_service),
):
    """Get trending packages by view count."""
    return service.trending_packages()


@router.get("/popular")
async def popular_packages(
    service: AnalyticsService = Depends(_get_analytics_service),
):
    """Get most popular packages."""
    return service.popular_packages()


@router.post("/events")
async def track_event(
    body: TrackEventBody,
    service: AnalyticsService = Depends(_get_analytics_service),
):
    """Track an analytics event."""
    return service.track_event(
        body.event_type,
        package_name=body.package_name,
        user_id=body.user_id,
        metadata_json=body.metadata_json,
    )


@router.get("/stats/{package_name}")
async def package_stats(
    package_name: str,
    service: AnalyticsService = Depends(_get_analytics_service),
):
    """Get analytics stats for a package."""
    return service.package_stats(package_name)
