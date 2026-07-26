"""Ecosystem statistics — adoption rates, trending migrations, compatibility matrix.

Provides the `EcosystemStatsService` for aggregating scan data.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from python_depot.ecosystem.models import PackageScan

# Known migration directions with their descriptions
TRENDING_MIGRATIONS: list[dict[str, str | int]] = [
    {"from": "pip", "to": "uv", "description": "pip → uv (faster, lockfile, workspace support)", "estimated_packages": 12000},
    {"from": "poetry", "to": "uv", "description": "poetry → uv (better performance, workspace)", "estimated_packages": 5000},
    {"from": "pip", "to": "poetry", "description": "pip → poetry (dependency management, lockfile)", "estimated_packages": 3000},
    {"from": "pip-tools", "to": "uv", "description": "pip-tools → uv (unified tool, faster)", "estimated_packages": 2000},
]


class EcosystemStatsService:
    """Aggregate ecosystem statistics from package scan data.

    Args:
        db: SQLAlchemy session for querying scan results.
    """

    MANAGER_TO_KEY = {
        "pip": "pip_only",
        "uv": "uv_ready",
        "poetry": "poetry_compatible",
        "pip-tools": "pip_tools_compatible",
    }

    def __init__(self, db: Session | None) -> None:
        self._db = db

    def compute_stats(self) -> dict[str, Any]:
        """Compute aggregated ecosystem adoption statistics.

        Returns:
            Dict with:
                - total_packages_scanned: int
                - adoption_rates: dict[str, dict[str, int | float]]
                - trending_migrations: list[dict]
        """
        if self._db is None:
            return {
                "total_packages_scanned": 0,
                "adoption_rates": {
                    "pip_only": {"count": 0, "pct": 0.0},
                    "uv_ready": {"count": 0, "pct": 0.0},
                    "poetry_compatible": {"count": 0, "pct": 0.0},
                    "pip_tools_compatible": {"count": 0, "pct": 0.0},
                },
                "trending_migrations": list(TRENDING_MIGRATIONS),
            }

        scans = self._db.query(PackageScan).all()
        total = len(scans)

        counts: dict[str, int] = {
            "pip_only": 0,
            "uv_ready": 0,
            "poetry_compatible": 0,
            "pip_tools_compatible": 0,
        }

        for scan in scans:
            try:
                managers = json.loads(scan.managers_supported) if scan.managers_supported else ["pip"]
            except (json.JSONDecodeError, TypeError):
                managers = ["pip"]

            if "uv" in managers:
                counts["uv_ready"] += 1
            if "poetry" in managers:
                counts["poetry_compatible"] += 1
            if "pip-tools" in managers:
                counts["pip_tools_compatible"] += 1
            if len(managers) == 1 and managers[0] == "pip":
                counts["pip_only"] += 1

        adoption_rates = {
            key: {
                "count": count,
                "pct": round((count / total * 100), 1) if total > 0 else 0.0,
            }
            for key, count in counts.items()
        }

        return {
            "total_packages_scanned": total,
            "adoption_rates": adoption_rates,
            "trending_migrations": list(TRENDING_MIGRATIONS),
        }

    def get_compatibility_matrix(
        self, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """Get paginated compatibility matrix across all scanned packages.

        Args:
            limit: Maximum results per page.
            offset: Pagination offset.

        Returns:
            Dict with:
                - packages: list[dict] — each with name, pip, uv, poetry, pip_tools booleans
                - total: int
                - limit: int
                - offset: int
        """
        if self._db is None:
            return {"packages": [], "total": 0, "limit": limit, "offset": offset}

        query = self._db.query(PackageScan).order_by(PackageScan.package_name)
        total = query.count()
        scans = query.offset(offset).limit(limit).all()

        packages = []
        for scan in scans:
            try:
                managers = json.loads(scan.managers_supported) if scan.managers_supported else ["pip"]
            except (json.JSONDecodeError, TypeError):
                managers = ["pip"]
            packages.append({
                "name": scan.package_name,
                "pip": "pip" in managers,
                "uv": "uv" in managers,
                "poetry": "poetry" in managers,
                "pip_tools": "pip-tools" in managers,
            })

        return {
            "packages": packages,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
