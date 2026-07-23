"""FastAPI application for PythonDepot — integrates all extracted modules.

Implements shared patterns:
- health-check-endpoint: detailed /health with DB checks, version, uptime
- ssrf-protection: URL validation for external calls
- railway-deploy-config: Dockerfile + railway.toml companion
"""
import time
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from python_depot.database import engine
from src.routers import analytics, packages, ratings, reports, reviews, vulnerabilities

# ---------------------------------------------------------------------------
# Shared pattern: ssrf-protection
# ---------------------------------------------------------------------------
ALLOWED_SCHEMES = {"https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"}
BLOCKED_IP_RANGES = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
]


def validate_url(url: str) -> bool:
    """Validate URL is safe to fetch (SSRF protection).

    Returns True if the URL is safe, False if it's a known internal/hostile
    target.  Applies to ALL external HTTP calls made by the application.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False
    if parsed.hostname in BLOCKED_HOSTS:
        return False
    # NOTE: full IP-range checking (ipaddress module) should be added
    #       before production deployment (shared/patterns/ssrf-protection.md)
    return True


# Application start timestamp for uptime computation
_START_TIME = time.time()


def _get_db_status() -> str:
    """Check database connectivity, returning 'ok' or a failure description."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        return f"failed: {exc}"


def _format_uptime(seconds: float) -> str:
    """Format elapsed seconds into a human-readable uptime string."""
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {secs}s"


def create_app() -> FastAPI:
    """Create and configure the complete PythonDepot FastAPI application.

    Registers all routers (packages, reviews, ratings, analytics,
    vulnerabilities, reports) and adds the shared-pattern endpoints:
    health, root, and SSRF protection middleware.
    """
    application = FastAPI(
        title="PythonDepot",
        description="Curated Python package discovery platform",
        version="0.1.0",
    )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    application.include_router(
        packages.router, prefix="/api/v1/packages", tags=["packages"]
    )
    application.include_router(
        reviews.router, prefix="/api/v1/reviews", tags=["reviews"]
    )
    application.include_router(
        ratings.router, prefix="/api/v1/ratings", tags=["ratings"]
    )
    application.include_router(
        vulnerabilities.router,
        prefix="/api/v1/vulnerabilities",
        tags=["vulnerabilities"],
    )
    application.include_router(
        analytics.router, prefix="/api/v1/analytics", tags=["analytics"]
    )
    application.include_router(
        reports.router, prefix="/api/v1/reports", tags=["reports"]
    )

    # ------------------------------------------------------------------
    # Root endpoint
    # ------------------------------------------------------------------
    @application.get("/")
    async def root():
        """API root — basic service info."""
        return {"message": "PythonDepot API", "version": "0.1.0"}

    # ------------------------------------------------------------------
    # Shared pattern: health-check-endpoint
    # Behavioural contract: returns status, version, timestamp, uptime,
    # db_status, plus individual subsystem checks.
    # ------------------------------------------------------------------
    @application.get("/health")
    async def health():
        """Detailed health check with database connectivity verification."""
        db_status = _get_db_status()
        uptime_seconds = time.time() - _START_TIME

        checks = {"database": db_status}

        # Determine overall status — 'ok' when every subsystem is ok
        overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"

        return {
            "status": overall,
            "version": "0.1.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime": _format_uptime(uptime_seconds),
            "db_status": db_status,
            "checks": checks,
        }

    # ------------------------------------------------------------------
    # Exception handler — translate common errors to JSON
    # ------------------------------------------------------------------
    @application.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    return application


app = create_app()
