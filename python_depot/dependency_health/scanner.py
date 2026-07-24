"""Scanner service for dependency_health — vulnerability scanning & compatibility checking.

Provides:
- HealthScanner: legacy scanner wrapping safety CLI (existing)
- DependencyScanner: new async scanner using OSV.dev API (stub)
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import Any

import httpx
from sqlalchemy.orm import Session

from python_depot.dependency_health.models import VulnerabilityScan
from python_depot.dependency_health.osv_client import OSVClient

logger = logging.getLogger(__name__)

SAFETY_TIMEOUT = 30  # seconds


class DependencyScanner:
    """Async vulnerability scanner backed by OSV.dev API.

    Replaces HealthScanner with async OSV.dev queries for vulnerability
    detection. Maintains backward-compatible response format.
    """

    def __init__(self, db: Session) -> None:
        """Initialize scanner with database session.

        Args:
            db: SQLAlchemy database session for storing scan results.
        """
        self.db = db
        self._client: OSVClient | None = None

    async def _get_client(self) -> OSVClient:
        """Lazy-init the OSV client."""
        if self._client is None:
            self._client = OSVClient()
        return self._client

    async def scan_package(
        self, name: str, version: str | None = None
    ) -> dict[str, Any]:
        """Run a vulnerability scan via OSV.dev API.

        Args:
            name: Package name to scan.
            version: Specific version to scan (optional).

        Returns:
            Scan result dict with status, vulnerability count, and scan_id.
        """
        client = await self._get_client()
        try:
            result = await client.query_package(name, version)
            vulns = result.get("vulns", [])
            vuln_count = len(vulns)
            status = "vulnerable" if vuln_count > 0 else "clean"
            details = json.dumps(vulns) if vulns else None
        except httpx.HTTPError as exc:
            logger.error("OSV scan failed for %s: %s", name, exc)
            vuln_count = 0
            status = "unknown"
            details = f"scan_error: {exc}"
        except Exception as exc:
            logger.error("Unexpected error scanning %s: %s", name, exc)
            vuln_count = 0
            status = "unknown"
            details = f"scan_error: {exc}"

        scan_id: int | None = None
        if self.db is not None:
            scan = VulnerabilityScan(
                package_id=0,  # placeholder; caller should set real pkg_id
                version=version or "latest",
                scanner="osv",
                status=status,
                vuln_count=vuln_count,
                details=details,
            )
            self.db.add(scan)
            self.db.commit()
            self.db.refresh(scan)
            scan_id = scan.id

        return {
            "package": name,
            "version": version or "latest",
            "status": status,
            "vulnerability_count": vuln_count,
            "scan_id": scan_id,
        }

    async def scan_batch(self, packages: list[dict]) -> list[dict]:
        """Run a batch vulnerability scan for multiple packages.

        Args:
            packages: List of dicts with 'name' and optional 'version' keys.

        Returns:
            List of scan result dicts.
        """
        results: list[dict] = []
        for pkg in packages:
            name = pkg.get("name", "")
            version = pkg.get("version")
            result = await self.scan_package(name, version)
            results.append(result)
        return results

    def list_scans(
        self, pkg_id: int, name: str
    ) -> dict[str, Any]:
        """List all vulnerability scans for a package.

        Args:
            pkg_id: Database ID of the package.
            name: Package name (included for context in response).

        Returns:
            Response dict with scan list.
        """
        if self.db is None:
            return {"package": name, "scans": [], "total": 0}
        scans = (
            self.db.query(VulnerabilityScan)
            .filter(VulnerabilityScan.package_id == pkg_id)
            .all()
        )
        return {
            "package": name,
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

    def latest_scan(
        self, pkg_id: int, name: str
    ) -> dict[str, Any]:
        """Get the most recent scan result.

        Args:
            pkg_id: Database ID of the package.
            name: Package name (included for context in response).

        Returns:
            Response dict with latest scan or null.
        """
        if self.db is None:
            return {"package": name, "scan": None}
        scan = (
            self.db.query(VulnerabilityScan)
            .filter(VulnerabilityScan.package_id == pkg_id)
            .order_by(VulnerabilityScan.scanned_at.desc())
            .first()
        )
        if scan is None:
            return {"package": name, "scan": None}
        return {
            "package": name,
            "scan": {
                "id": scan.id,
                "version": scan.version,
                "status": scan.status,
                "vulnerability_count": scan.vuln_count,
                "scanned_at": scan.scanned_at.isoformat(),
            },
        }


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
                status = "clean" if vuln_count == 0 else "vulnerable"
                details = json.dumps(vuln_data) if vuln_data else None
            else:
                # safety CLI exits non-zero when vulnerabilities are found,
                # but still outputs valid JSON to stdout.
                vuln_data = json.loads(result.stdout) if result.stdout.strip() else []
                vuln_count = len(vuln_data) if isinstance(vuln_data, list) else 0
                status = "vulnerable" if vuln_count > 0 else "clean"
                details = json.dumps(vuln_data) if vuln_data else None
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
