"""Dependency health dashboard router — vulnerability overview, trends, alerts.

REST API endpoints for dependency health dashboard providing
aggregated vulnerability status across all packages, trend data,
per-package health scores, and recent alerts.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.dependency_health.alerts import AlertEngine
from python_depot.dependency_health.models import VulnerabilityAlert, VulnerabilityScan
from python_depot.dependency_health.scoring import aggregate_score

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/v1/dependency-health/overview")
async def get_overview(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Aggregate vulnerability statistics across all scanned packages.

    Returns:
        Dict with total packages scanned, vulnerability counts by severity,
        scan coverage percentage, and last scan timestamp.
    """
    total_scans = db.query(VulnerabilityScan).count()
    vulnerable_scans = (
        db.query(VulnerabilityScan)
        .filter(VulnerabilityScan.status == "vulnerable")
        .count()
    )
    clean_scans = (
        db.query(VulnerabilityScan)
        .filter(VulnerabilityScan.status == "clean")
        .count()
    )
    unknown_scans = (
        db.query(VulnerabilityScan)
        .filter(VulnerabilityScan.status == "unknown")
        .count()
    )

    # Unique packages scanned
    distinct_packages = (
        db.query(VulnerabilityScan.package_id)
        .distinct()
        .count()
    )

    # Latest scan timestamp
    latest_scan = (
        db.query(VulnerabilityScan.scanned_at)
        .order_by(VulnerabilityScan.scanned_at.desc())
        .first()
    )

    total_packages = db.query(VulnerabilityScan.package_id).distinct().count()

    return {
        "total_packages": total_packages,
        "total_scans": total_scans,
        "vuln_counts": {
            "vulnerable": vulnerable_scans,
            "clean": clean_scans,
            "unknown": unknown_scans,
        },
        "severity_breakdown": {},
        "scan_coverage": round(
            (clean_scans / total_scans * 100) if total_scans > 0 else 0, 1
        ),
        "last_scan": latest_scan[0].isoformat() if latest_scan else None,
    }


@router.get("/api/v1/dependency-health/trends")
async def get_trends(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Vulnerability trend data over time.

    Returns:
        Dict with time-series data showing vulnerability counts,
        new findings, and resolved issues per time period.
    """
    scans = (
        db.query(VulnerabilityScan)
        .order_by(VulnerabilityScan.scanned_at.asc())
        .all()
    )

    trends: list[dict[str, Any]] = []
    cumulative = {"vulnerable": 0, "clean": 0, "unknown": 0}
    for scan in scans:
        cumulative[scan.status] = cumulative.get(scan.status, 0) + 1
        trends.append({
            "timestamp": scan.scanned_at.isoformat(),
            "vulnerable": cumulative["vulnerable"],
            "clean": cumulative["clean"],
            "unknown": cumulative["unknown"],
            "total": cumulative["vulnerable"]
            + cumulative["clean"]
            + cumulative["unknown"],
        })

    return {"trends": trends}


@router.get("/api/v1/dependency-health/packages")
async def get_package_health(
    db: Session = Depends(get_db),
    sort_by: str = "score",
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List packages sorted by health score.

    Args:
        db: Database session.
        sort_by: Sort field ('score', 'name', 'vuln_count').
        limit: Maximum results per page.
        offset: Pagination offset.

    Returns:
        Dict with list of packages, each containing name, health score,
        vulnerability count, severity breakdown, and last scan time.
    """
    # Get all distinct package IDs with their latest scan
    package_ids = (
        db.query(VulnerabilityScan.package_id)
        .distinct()
        .all()
    )

    packages: list[dict[str, Any]] = []
    for (pkg_id,) in package_ids:
        latest = (
            db.query(VulnerabilityScan)
            .filter(VulnerabilityScan.package_id == pkg_id)
            .order_by(VulnerabilityScan.scanned_at.desc())
            .first()
        )
        if latest is None:
            continue

        total_vulns = (
            db.query(VulnerabilityScan)
            .filter(
                VulnerabilityScan.package_id == pkg_id,
                VulnerabilityScan.status == "vulnerable",
            )
            .count()
        )

        packages.append({
            "package_id": pkg_id,
            "vuln_count": total_vulns,
            "status": latest.status,
            "last_scan": latest.scanned_at.isoformat(),
        })

    # Sort
    reverse = sort_by != "name"
    packages.sort(
        key=lambda p: (
            p.get("vuln_count", 0) if sort_by == "vuln_count" else p.get("package_id", 0)
        ),
        reverse=reverse,
    )

    total = len(packages)
    paginated = packages[offset:offset + limit]

    return {
        "packages": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/v1/dependency-health/alerts")
async def get_alerts(
    db: Session = Depends(get_db),
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List recent vulnerability alerts.

    Args:
        db: Database session.
        severity: Optional severity filter ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW').
        limit: Maximum results per page.
        offset: Pagination offset.

    Returns:
        Dict with list of alerts, each containing package name, vuln ID,
        severity, score, timestamp, and webhook delivery status.
    """
    engine = AlertEngine(db)
    alerts = engine.list_alerts(severity=severity)
    total = len(alerts)
    paginated = alerts[offset:offset + limit]

    return {
        "alerts": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/v1/dependency-health/{package_name}/score")
async def get_package_score(
    package_name: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Calculate and return a composite security score for a package.

    Combines CVSS severity, vulnerability count, fix availability,
    and scan recency into a single 0-100 health score.

    Args:
        package_name: Name of the package to score.
        db: Database session.

    Returns:
        Dict with:
            - 'package' (str): Package name
            - 'score' (float): Composite score 0-100
            - 'breakdown' (dict): Score component breakdown
            - 'vuln_count' (int): Total vulnerabilities found
            - 'max_severity' (str): Highest severity level
            - 'score_label' (str): 'CRITICAL', 'POOR', 'FAIR', 'GOOD', or 'EXCELLENT'
    """
    # Get all vulnerable scans for this package
    vulnerable_scans = (
        db.query(VulnerabilityScan)
        .filter(
            VulnerabilityScan.status == "vulnerable",
        )
        .all()
    )

    vulns: list[dict[str, Any]] = []
    for scan in vulnerable_scans:
        if scan.details:
            try:
                details = json.loads(scan.details) if isinstance(scan.details, str) else scan.details  # type: ignore[arg-type]
                if isinstance(details, list):
                    for v in details:
                        vulns.append({
                            "severity": v.get("severity", "MEDIUM"),
                            "score": v.get("score", 5.0),
                            "fixed": v.get("fixed", False),
                        })
            except (json.JSONDecodeError, TypeError):
                continue

    if not vulns:
        return {
            "package": package_name,
            "score": 100.0,
            "breakdown": {
                "base_score": 100.0,
                "vuln_penalty": 0.0,
                "severity_penalty": 0.0,
            },
            "vuln_count": 0,
            "max_severity": "NONE",
            "score_label": "EXCELLENT",
        }

    agg = aggregate_score(vulns)

    # Convert 0-10 CVSS-like score to 0-100 health score (inverted)
    # Lower vulnerability score = better health
    raw_score = agg["total"]
    health_score = round(max(0.0, 100.0 - raw_score * 10.0), 1)

    # Score label
    if health_score >= 90:
        label = "EXCELLENT"
    elif health_score >= 70:
        label = "GOOD"
    elif health_score >= 50:
        label = "FAIR"
    elif health_score >= 30:
        label = "POOR"
    else:
        label = "CRITICAL"

    return {
        "package": package_name,
        "score": health_score,
        "breakdown": {
            "base_score": health_score,
            "vuln_penalty": round(raw_score * 10.0, 1),
        },
        "vuln_count": agg["vuln_count"],
        "max_severity": agg["max_severity"],
        "score_label": label,
    }
