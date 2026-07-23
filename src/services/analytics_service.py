"""Analytics service — download stats aggregation, trend analysis."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
from sqlalchemy.orm import Session

from src.models.analytics import AnalyticsEvent

logger = logging.getLogger(__name__)

PYPI_STATS_RECENT = "https://pypistats.org/api/packages/{name}/recent"
PYPI_STATS_OVERALL = "https://pypistats.org/api/packages/{name}/overall"


class AnalyticsService:
    """Handles analytics event tracking and download stats."""

    def __init__(self, db: Session) -> None:
        """Initialize with a database session.

        Args:
            db: SQLAlchemy synchronous session.
        """
        self.db = db

    def track_event(
        self,
        event_type: str,
        package_name: str | None = None,
        user_id: str | None = None,
        metadata_json: str | None = None,
    ) -> dict[str, Any]:
        """Track an analytics event.

        Args:
            event_type: Type of event (view, search, install_click).
            package_name: Related package name.
            user_id: User identifier.
            metadata_json: Optional JSON metadata.

        Returns:
            Response dict.
        """
        event = AnalyticsEvent(
            event_type=event_type,
            package_name=package_name,
            user_id=user_id,
            metadata_json=metadata_json,
        )
        self.db.add(event)
        self.db.commit()
        return {"status": "tracked", "event_type": event_type}

    def package_stats(self, package_name: str) -> dict[str, Any]:
        """Get download stats for a package.

        Args:
            package_name: Package name.

        Returns:
            Stats dict with view/install counts.
        """
        views = (
            self.db.query(AnalyticsEvent)
            .filter(
                AnalyticsEvent.package_name == package_name,
                AnalyticsEvent.event_type == "view",
            )
            .count()
        )
        installs = (
            self.db.query(AnalyticsEvent)
            .filter(
                AnalyticsEvent.package_name == package_name,
                AnalyticsEvent.event_type == "install_click",
            )
            .count()
        )
        return {"package": package_name, "views": views, "installs": installs}

    def trending_packages(self, period: str = "7d") -> dict[str, Any]:
        """Get trending packages by view count.

        Args:
            period: Time period (7d, 30d).

        Returns:
            Trending packages list.
        """
        # Simple aggregation: count views per package
        results = (
            self.db.query(
                AnalyticsEvent.package_name,
            )
            .filter(AnalyticsEvent.event_type == "view", AnalyticsEvent.package_name.isnot(None))
            .group_by(AnalyticsEvent.package_name)
            .order_by()
            .limit(10)
            .all()
        )
        trending = [r[0] for r in results if r[0]]
        return {"trending": trending, "period": period}

    def popular_packages(self) -> dict[str, Any]:
        """Get most popular packages by total events.

        Returns:
            Popular packages list.
        """
        results = (
            self.db.query(AnalyticsEvent.package_name)
            .filter(AnalyticsEvent.package_name.isnot(None))
            .group_by(AnalyticsEvent.package_name)
            .limit(10)
            .all()
        )
        popular = [r[0] for r in results if r[0]]
        return {"popular": popular}

    async def fetch_download_stats(self, package_name: str) -> dict[str, Any] | None:
        """Fetch download stats from PyPI Stats API.

        Args:
            package_name: Package name.

        Returns:
            Download stats dict or None on failure.
        """
        url = PYPI_STATS_RECENT.format(name=package_name)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return None
                    return await resp.json()
        except (aiohttp.ClientError, Exception) as exc:
            logger.warning("Failed to fetch stats for %s: %s", package_name, exc)
            return None
