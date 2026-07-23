"""Report service — monthly Best-of report generator using Jinja2 templates.

N+1 fix: batch all per-package queries (ratings, scans, reviews)
into 3 bulk queries instead of N per-package round-trips.
XSS fix: user-controlled values in _render_basic_html are html.escaped.
"""
from __future__ import annotations

import html
import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from src.models.package import Package
from src.models.rating import Rating
from src.models.review import Review
from src.models.vulnerability import VulnerabilityScan

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class ReportService:
    """Generates monthly Best-of reports aggregating data from all modules."""

    def __init__(self, db: Session) -> None:
        """Initialize with a database session.

        Args:
            db: SQLAlchemy synchronous session.
        """
        self.db = db
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)

    def generate_report(self, year: int, month: int) -> dict[str, Any]:
        """Generate a monthly report.

        Uses batch queries to avoid N+1: all ratings, scans, and reviews
        are fetched in exactly 3 bulk queries regardless of package count.

        Args:
            year: Report year.
            month: Report month (1-12).

        Returns:
            Report dict with HTML and JSON data.
        """
        # Query 1: all packages
        packages = self.db.query(Package).all()
        pkg_ids = [pkg.id for pkg in packages]

        # Query 2: all ratings for all packages (batch)
        ratings_by_pkg: dict[int, list[Rating]] = defaultdict(list)
        if pkg_ids:
            for rating in self.db.query(Rating).filter(Rating.package_id.in_(pkg_ids)):
                ratings_by_pkg[rating.package_id].append(rating)

        # Query 3: all vulnerability scans (batch)
        scans_by_pkg: dict[int, list[VulnerabilityScan]] = defaultdict(list)
        if pkg_ids:
            for scan in self.db.query(VulnerabilityScan).filter(VulnerabilityScan.package_id.in_(pkg_ids)):
                scans_by_pkg[scan.package_id].append(scan)

        # Query 4: review counts per package (batch)
        review_counts: dict[int, int] = defaultdict(int)
        if pkg_ids:
            for review_id, pkg_id in (
                self.db.query(Review.id, Review.package_id)
                .filter(Review.package_id.in_(pkg_ids))
                .all()
            ):
                review_counts[pkg_id] += 1

        # Exactly 4 queries total — regardless of N packages

        # Aggregate top packages by rating
        top_by_rating: list[dict[str, Any]] = []
        for pkg in packages:
            pkg_ratings = ratings_by_pkg.get(pkg.id, [])
            if pkg_ratings:
                avg = sum(r.score for r in pkg_ratings) / len(pkg_ratings)
                top_by_rating.append({
                    "name": pkg.name,
                    "summary": pkg.summary or "",
                    "avg_rating": round(avg, 2),
                    "rating_count": len(pkg_ratings),
                    "latest_version": pkg.latest_version or "unknown",
                })
        top_by_rating.sort(key=lambda x: (-x["avg_rating"], -x["rating_count"]))

        # Get healthiest packages (fewest vulnerabilities)
        healthiest: list[dict[str, Any]] = []
        for pkg in packages:
            pkg_scans = scans_by_pkg.get(pkg.id, [])
            latest = max(pkg_scans, key=lambda s: s.scanned_at) if pkg_scans else None
            healthiest.append({
                "name": pkg.name,
                "status": latest.status if latest else "unscanned",
                "vuln_count": latest.vuln_count if latest else 0,
            })
        healthiest.sort(key=lambda x: x["vuln_count"])

        # Most reviewed
        most_reviewed: list[dict[str, Any]] = []
        for pkg in packages:
            count = review_counts.get(pkg.id, 0)
            if count > 0:
                most_reviewed.append({"name": pkg.name, "review_count": count})
        most_reviewed.sort(key=lambda x: -x["review_count"])

        report_data = {
            "year": year,
            "month": month,
            "generated_at": datetime.now(UTC).isoformat(),
            "top_by_rating": top_by_rating[:10],
            "healthiest": healthiest[:10],
            "most_reviewed": most_reviewed[:10],
            "total_packages": len(packages),
        }

        # Render HTML
        try:
            template = self.env.get_template("report.html")
            html_out = template.render(report=report_data)
        except Exception:
            logger.warning("Template rendering failed, using basic HTML")
            html_out = self._render_basic_html(report_data)

        return {
            "year": year,
            "month": month,
            "report_json": json.dumps(report_data),
            "report_html": html_out,
            "data": report_data,
        }

    @staticmethod
    def _render_basic_html(data: dict[str, Any]) -> str:
        """Render a basic HTML report without templates.

        All user-controlled values are HTML-escaped to prevent XSS.

        Args:
            data: Report data dict.

        Returns:
            HTML string.
        """
        year_escaped = html.escape(str(data.get("year", "")))
        month_escaped = html.escape(str(data.get("month", "")))
        total_packages_escaped = html.escape(str(data.get("total_packages", 0)))

        rows = ""
        for p in data.get("top_by_rating", []):
            name = html.escape(str(p.get("name", "")))
            avg = html.escape(str(p.get("avg_rating", "")))
            count = html.escape(str(p.get("rating_count", 0)))
            rows += f"<li>{name} — {avg}★ ({count} ratings)</li>"

        return (
            f"<html><head><title>PythonDepot Report {year_escaped}-{month_escaped}</title></head>"
            f"<body><h1>PythonDepot Monthly Report — {year_escaped}/{month_escaped}</h1>"
            f"<p>Total packages: {total_packages_escaped}</p>"
            f"<h2>Top Rated</h2><ul>{rows}</ul></body></html>"
        )

    def list_reports(self, year: int | None = None) -> list[dict[str, Any]]:
        """List available reports.

        Args:
            year: Optional year filter.

        Returns:
            List of report summaries.
        """
        # For now, return empty — reports are generated on demand
        return []

    def get_report(self, year: int, month: int) -> dict[str, Any] | None:
        """Get a specific report.

        Args:
            year: Report year.
            month: Report month.

        Returns:
            Report data or None.
        """
        return None
