"""Report service — monthly Best-of report generator using Jinja2 templates."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
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

        Args:
            year: Report year.
            month: Report month (1-12).

        Returns:
            Report dict with HTML and JSON data.
        """
        # Aggregate top packages by rating
        packages = self.db.query(Package).all()
        top_by_rating: list[dict[str, Any]] = []
        for pkg in packages:
            ratings = self.db.query(Rating).filter(Rating.package_id == pkg.id).all()
            if ratings:
                avg = sum(r.score for r in ratings) / len(ratings)
                top_by_rating.append({
                    "name": pkg.name,
                    "summary": pkg.summary or "",
                    "avg_rating": round(avg, 2),
                    "rating_count": len(ratings),
                    "latest_version": pkg.latest_version or "unknown",
                })
        top_by_rating.sort(key=lambda x: (-x["avg_rating"], -x["rating_count"]))

        # Get healthiest packages (fewest vulnerabilities)
        healthiest: list[dict[str, Any]] = []
        for pkg in packages:
            scans = self.db.query(VulnerabilityScan).filter(VulnerabilityScan.package_id == pkg.id).all()
            latest = max(scans, key=lambda s: s.scanned_at) if scans else None
            healthiest.append({
                "name": pkg.name,
                "status": latest.status if latest else "unscanned",
                "vuln_count": latest.vuln_count if latest else 0,
            })
        healthiest.sort(key=lambda x: x["vuln_count"])

        # Most reviewed
        most_reviewed: list[dict[str, Any]] = []
        for pkg in packages:
            reviews = self.db.query(Review).filter(Review.package_id == pkg.id).count()
            if reviews > 0:
                most_reviewed.append({"name": pkg.name, "review_count": reviews})
        most_reviewed.sort(key=lambda x: -x["review_count"])

        report_data = {
            "year": year,
            "month": month,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "top_by_rating": top_by_rating[:10],
            "healthiest": healthiest[:10],
            "most_reviewed": most_reviewed[:10],
            "total_packages": len(packages),
        }

        # Render HTML
        try:
            template = self.env.get_template("report.html")
            html = template.render(report=report_data)
        except Exception:
            logger.warning("Template rendering failed, using basic HTML")
            html = self._render_basic_html(report_data)

        return {
            "year": year,
            "month": month,
            "report_json": json.dumps(report_data),
            "report_html": html,
            "data": report_data,
        }

    def _render_basic_html(self, data: dict[str, Any]) -> str:
        """Render a basic HTML report without templates.

        Args:
            data: Report data dict.

        Returns:
            HTML string.
        """
        return (
            f"<html><head><title>PythonDepot Report {data['year']}-{data['month']:02d}</title></head>"
            f"<body><h1>PythonDepot Monthly Report — {data['year']}/{data['month']:02d}</h1>"
            f"<p>Total packages: {data['total_packages']}</p>"
            f"<h2>Top Rated</h2><ul>"
            + "".join(f"<li>{p['name']} — {p['avg_rating']}★ ({p['rating_count']} ratings)</li>" for p in data["top_by_rating"])
            + "</ul></body></html>"
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
