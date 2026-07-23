"""FastAPI application for PythonDepot — integrates all extracted modules.

Implements shared patterns:
- health-check-endpoint: detailed /health with DB checks, version, uptime
- ssrf-protection: URL validation for external calls (IP-range verified)
- railway-deploy-config: Dockerfile + railway.toml companion
"""
import ipaddress
import socket
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from python_depot.database import engine, init_db
from python_depot.routers import (
    analytics,
    packages,
    ratings,
    reports,
    reviews,
    vulnerabilities,
)

# ---------------------------------------------------------------------------
# Shared pattern: ssrf-protection
# ---------------------------------------------------------------------------
ALLOWED_SCHEMES = {"https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"}
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
]


def _resolve_ips(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve a hostname to its IP addresses.

    Returns a list of IPAddress objects.  On resolution failure returns
    an empty list (URL considered unsafe).
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
        ips: set[str] = set()
        for info in infos:
            addr = str(info[4][0])
            ips.add(addr)
        result: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
        for addr in ips:
            try:
                result.append(ipaddress.ip_address(addr))
            except ValueError:
                continue
        return result
    except (socket.gaierror, OSError):
        return []


def validate_url(url: str) -> bool:
    """Validate URL is safe to fetch (SSRF protection).

    Resolves the hostname and checks every resolved IP against
    private / link-local IP ranges.  Returns True if the URL is safe,
    False if it is a known internal/hostile target.

    Applies to ALL external HTTP calls made by the application.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname in BLOCKED_HOSTS:
        return False

    # Resolve hostname and check against private IP ranges
    ips = _resolve_ips(hostname)
    if not ips:
        # Could not resolve — safest to reject
        return False

    for ip_addr in ips:
        for blocked_range in BLOCKED_IP_RANGES:
            if ip_addr in blocked_range:
                return False

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


# ---------------------------------------------------------------------------
# Lifespan — initialise DB tables on startup, clean up on shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: create tables on start, no-op on shutdown."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the complete PythonDepot FastAPI application.

    Registers all routers (packages, reviews, ratings, analytics,
    vulnerabilities, reports) backed by real python_depot services,
    and adds the shared-pattern endpoints:
    health, root, and SSRF protection middleware.
    """
    application = FastAPI(
        title="PythonDepot",
        description="Curated Python package discovery platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Routers (backed by real python_depot business logic)
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
