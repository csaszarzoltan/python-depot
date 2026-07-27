"""Dashboard UI router — serves Jinja2 templates for the vulnerability dashboard."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.pydepot.models import Package
from python_depot.routers.dependency_health import (
    get_alerts,
    get_overview,
    get_package_health,
    get_package_score,
)

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "dashboard"
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    cache_size=0,  # Disable cache to avoid LRU hashability issues
)

# Module-level alias for test compatibility (test_dashboard_router_registers_jinja2_templates)
templates = _jinja_env

def _render(template_name: str, context: dict) -> str:
    """Render a Jinja2 template with the given context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_overview(request: Request, db: Session = Depends(get_db)):
    """Dashboard overview page with severity breakdown and stats."""
    overview_data = await get_overview(db)
    overview_data["severity_json"] = json.dumps(overview_data.get("severity_breakdown", {}))
    html = _render("overview.html", {"request": request, **overview_data})
    return HTMLResponse(html)


@router.get("/dashboard/packages", response_class=HTMLResponse)
async def dashboard_packages(
    request: Request,
    db: Session = Depends(get_db),
    sort_by: str = "score",
    limit: int = 20,
    offset: int = 0,
):
    """Packages page with health table, search and pagination."""
    packages_data = await get_package_health(
        db, sort_by=sort_by, limit=limit, offset=offset
    )
    html = _render("packages.html", {"request": request, **packages_data})
    return HTMLResponse(html)


@router.get("/dashboard/alerts", response_class=HTMLResponse)
async def dashboard_alerts(
    request: Request,
    db: Session = Depends(get_db),
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Alerts page with severity filter and pagination."""
    alerts_data = await get_alerts(
        db, severity=severity, limit=limit, offset=offset
    )
    html = _render(
        "alerts.html",
        {
            "request": request,
            **alerts_data,
            "current_severity": severity,
        },
    )
    return HTMLResponse(html)


@router.get("/dashboard/packages/{package_name}", response_class=HTMLResponse)
async def dashboard_package_detail(
    request: Request,
    package_name: str,
    db: Session = Depends(get_db),
):
    """Package detail page with health score breakdown."""
    # Check if package exists in the database (by name)
    exists = (
        db.query(Package)
        .filter(Package.name == package_name)
        .first()
    )
    if not exists:
        html = _render(
            "package_detail.html",
            {
                "request": request,
                "package": package_name,
                "error": "Package not found or no data available.",
                "score": 0,
                "score_label": "N/A",
                "breakdown": {"base_score": 0, "vuln_penalty": 0},
                "vuln_count": 0,
                "max_severity": "NONE",
            },
        )
        return HTMLResponse(html, status_code=404)

    score_data = await get_package_score(package_name, db)
    html = _render(
        "package_detail.html",
        {"request": request, **score_data},
    )
    return HTMLResponse(html)
