"""Health service — vulnerability scanning, compatibility matrix builder."""
from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

from sqlalchemy.orm import Session

from src.models.package import Package
from src.models.vulnerability import VulnerabilityScan

logger = logging.getLogger(__name__)

SAFETY_TIMEOUT = 30  # seconds


class HealthService:
    """Handles vulnerability scanning and compatibility checks."""

    def __init__(self, db: Session) -> None:
        """Initialize with a database session.

        Args:
            db: SQLAlchemy synchronous session.
        """
        self.db = db

    def scan_package(self, package_name: str, version: str | None = None) -> dict[str, Any]:
        """Run a vulnerability scan via safety CLI.

        Args:
            package_name: Package to scan.
            version: Specific version to scan (optional).

        Returns:
            Scan result dict.
        """
        pkg = self.db.query(Package).filter(Package.name == package_name).first()
        if pkg is None:
            return {"error": "package_not_found", "package": package_name}

        target_version = version or pkg.latest_version or "latest"

        # Try running safety check
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
            package_id=pkg.id,
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

    def list_scans(self, package_name: str) -> dict[str, Any]:
        """List all vulnerability scans for a package.

        Args:
            package_name: Package name.

        Returns:
            Response dict with scan list.
        """
        pkg = self.db.query(Package).filter(Package.name == package_name).first()
        if pkg is None:
            return {"package": package_name, "scans": [], "total": 0}

        scans = self.db.query(VulnerabilityScan).filter(VulnerabilityScan.package_id == pkg.id).all()
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

    def latest_scan(self, package_name: str) -> dict[str, Any]:
        """Get the most recent scan result.

        Args:
            package_name: Package name.

        Returns:
            Response dict with latest scan or null.
        """
        pkg = self.db.query(Package).filter(Package.name == package_name).first()
        if pkg is None:
            return {"package": package_name, "scan": None}

        scan = (
            self.db.query(VulnerabilityScan)
            .filter(VulnerabilityScan.package_id == pkg.id)
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

    def get_compatibility(self, package_name: str, python_version: str | None = None) -> dict[str, Any]:
        """Build a compatibility matrix from package metadata.

        Args:
            package_name: Package name.
            python_version: Optional specific version to check.

        Returns:
            Compatibility info dict.
        """
        pkg = self.db.query(Package).filter(Package.name == package_name).first()
        if pkg is None:
            return {"package": package_name, "compatible": False, "requires_python": None}

        return {
            "package": package_name,
            "compatible": True,
            "requires_python": pkg.latest_version,
            "latest_version": pkg.latest_version,
        }
