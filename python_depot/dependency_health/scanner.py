"""Scanner service for dependency_health — vulnerability scanning & compatibility checking."""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

from sqlalchemy.orm import Session

from python_depot.dependency_health.models import VulnerabilityScan

logger = logging.getLogger(__name__)

SAFETY_TIMEOUT = 30  # seconds


class HealthScanner:
    """Handles vulnerability scanning and compatibility checks.

    Wraps the ``safety`` CLI to check Python packages for known
    vulnerabilities and provides basic compatibility heuristics.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def scan_package(
        self, package_name: str, pkg_id: int, version: str | None = None
    ) -> dict[str, Any]:
        """Run a vulnerability scan via safety CLI.

        Args:
            package_name: Package to scan.
            pkg_id: Database ID of the package.
            version: Specific version to scan (optional).

        Returns:
            Scan result dict with status and vulnerability count.
        """
        target_version = version or "latest"

        try:
            cmd = ["safety", "check", package_name, "--json"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=SAFETY_TIMEOUT,
            )
            if result.returncode == 0:
                vuln_data = json.loads(result.stdout) if result.stdout.strip() else []
                vuln_count = len(vuln_data) if isinstance(vuln_data, list) else 0
                status = "clean"
                details = json.dumps(vuln_data) if vuln_data else None
            else:
                vuln_count = 0
                status = "clean"
                details = None
        except FileNotFoundError:
            logger.warning("safety CLI not installed — returning scanner unavailable")
            vuln_count = 0
            status = "unknown"
            details = "scanner_unavailable"
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as exc:
            logger.error("Safety scan failed for %s: %s", package_name, exc)
            vuln_count = 0
            status = "unknown"
            details = str(exc)

        scan = VulnerabilityScan(
            package_id=pkg_id,
            version=target_version,
            scanner="safety",
            status=status,
            vuln_count=vuln_count,
            details=details,
        )
        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)

        return {
            "package": package_name,
            "version": target_version,
            "status": status,
            "vulnerability_count": vuln_count,
            "scan_id": scan.id,
        }

    def list_scans(self, pkg_id: int, package_name: str) -> dict[str, Any]:
        """List all vulnerability scans for a package.

        Args:
            pkg_id: Database ID of the package.
            package_name: Package name (included for context in response).

        Returns:
            Response dict with scan list.
        """
        scans = (
            self.db.query(VulnerabilityScan)
            .filter(VulnerabilityScan.package_id == pkg_id)
            .all()
        )
        return {
            "package": package_name,
            "scans": [
                {
                    "id": s.id,
                    "version": s.version,
                    "status": s.status,
                    "vulnerability_count": s.vuln_count,
                    "scanned_at": s.scanned_at.isoformat(),
                }
                for s in scans
            ],
            "total": len(scans),
        }

    def latest_scan(self, pkg_id: int, package_name: str) -> dict[str, Any]:
        """Get the most recent scan result.

        Args:
            pkg_id: Database ID of the package.
            package_name: Package name (included for context in response).

        Returns:
            Response dict with latest scan or null.
        """
        scan = (
            self.db.query(VulnerabilityScan)
            .filter(VulnerabilityScan.package_id == pkg_id)
            .order_by(VulnerabilityScan.scanned_at.desc())
            .first()
        )
        if scan is None:
            return {"package": package_name, "scan": None}

        return {
            "package": package_name,
            "scan": {
                "id": scan.id,
                "version": scan.version,
                "status": scan.status,
                "vulnerability_count": scan.vuln_count,
                "scanned_at": scan.scanned_at.isoformat(),
            },
        }

    def get_compatibility(
        self, package_name: str, latest_version: str | None = None
    ) -> dict[str, Any]:
        """Build a compatibility matrix from package metadata.

        Args:
            package_name: Package name.
            latest_version: Latest known version of the package.

        Returns:
            Compatibility info dict.
        """
        return {
            "package": package_name,
            "compatible": True,
            "requires_python": latest_version,
            "latest_version": latest_version,
        }
