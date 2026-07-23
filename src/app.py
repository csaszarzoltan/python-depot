"""FastAPI application factory for PythonDepot."""
from datetime import UTC, datetime

from fastapi import FastAPI

from src.routers import analytics, packages, ratings, reports, reviews, vulnerabilities


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="PythonDepot",
        description="Curated Python package discovery platform",
        version="0.1.0",
    )

    # Register routers
    application.include_router(packages.router, prefix="/api/v1/packages", tags=["packages"])
    application.include_router(ratings.router, prefix="/api/v1/ratings", tags=["ratings"])
    application.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
    application.include_router(vulnerabilities.router, prefix="/api/v1/vulnerabilities", tags=["vulnerabilities"])
    application.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    application.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])

    @application.get("/")
    async def root():
        return {"message": "PythonDepot API", "version": "0.1.0"}

    @application.get("/health")
    async def health():
        return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}

    return application


app = create_app()
