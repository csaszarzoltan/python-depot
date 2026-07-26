"""Ecosystem scanner — fetches PyPI metadata and detects package manager support."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from python_depot.ecosystem.detector import PackageManagerDetector
from python_depot.ecosystem.models import PackageScan

logger = logging.getLogger(__name__)

PYPI_JSON_URL = "https://pypi.org/pypi/{name}/json"
REQUEST_TIMEOUT = 15.0


class EcosystemScanner:
    """Scan individual packages or batches for package manager compatibility."""

    def __init__(self, db: Session | None) -> None:
        self._db = db

    async def scan_package(
        self, name: str, save: bool = True
    ) -> dict[str, Any]:
        """Scan a single package for package manager compatibility."""
        pypi_data = await self._fetch_pypi_json(name)
        if pypi_data is None:
            result = {
                "package": name,
                "managers_supported": ["pip"],
                "detection_tier": 0,
                "build_backend": None,
                "lockfile_type": None,
                "has_pyproject_toml": False,
                "scanned_at": datetime.now(UTC).isoformat(),
            }
            if save and self._db is not None:
                self._persist(result)
            return result

        tier1_result = PackageManagerDetector.detect_from_pypi_json(pypi_data)

        result = {
            "package": name,
            "managers_supported": tier1_result.get("managers_supported", ["pip"]),
            "detection_tier": tier1_result.get("detection_tier", 1),
            "build_backend": self._infer_build_backend(pypi_data),
            "lockfile_type": self._infer_lockfile_type(tier1_result),
            "has_pyproject_toml": self._check_pyproject_availability(pypi_data),
            "scanned_at": datetime.now(UTC).isoformat(),
        }

        if save and self._db is not None:
            self._persist(result)

        return result

    async def scan_batch(
        self, names: list[str], tier_1_only: bool = False
    ) -> list[dict[str, Any]]:
        """Scan multiple packages."""
        results: list[dict[str, Any]] = []
        for name in names:
            result = await self.scan_package(name)
            results.append(result)
        return results

    async def _fetch_pypi_json(self, name: str) -> dict[str, Any] | None:
        """Fetch PyPI JSON metadata for a package."""
        url = PYPI_JSON_URL.format(name=name)
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(url)
                if resp.status_code == 404:
                    logger.info("Package %s not found on PyPI", name)
                    return None
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException:
            logger.warning("Timeout fetching PyPI data for %s", name)
            return None
        except httpx.HTTPStatusError as exc:
            logger.warning("HTTP %s fetching PyPI data for %s", exc.response.status_code, name)
            return None
        except Exception as exc:
            logger.error("Unexpected error fetching PyPI data for %s: %s", name, exc)
            return None

    def _infer_build_backend(self, pypi_data: dict[str, Any]) -> str | None:
        """Infer build backend from PyPI metadata."""
        classifiers = pypi_data.get("info", {}).get("classifiers") or []
        for c in classifiers:
            if "setuptools" in c.lower():
                return PackageManagerDetector.BUILDBACKEND_SETUPTOOLS
        return None

    def _infer_lockfile_type(self, detection: dict[str, Any]) -> str | None:
        """Infer lockfile type from detection signals."""
        managers = detection.get("managers_supported", [])
        if "uv" in managers:
            return "uv.lock"
        if "poetry" in managers:
            return "poetry.lock"
        if "pip-tools" in managers:
            return "requirements.txt"
        return None

    def _check_pyproject_availability(self, pypi_data: dict[str, Any]) -> bool:
        """Check if the package likely has a pyproject.toml."""
        classifiers = pypi_data.get("info", {}).get("classifiers") or []
        for c in classifiers:
            if "pyproject" in c.lower() or "project" in c.lower():
                return True
        return self._infer_build_backend(pypi_data) is not None

    def _persist(self, result: dict[str, Any]) -> None:
        """Save a scan result to the database."""
        if self._db is None:
            return
        try:
            existing = (
                self._db.query(PackageScan)
                .filter(PackageScan.package_name == result["package"])
                .first()
            )
            if existing:
                existing.managers_supported = json.dumps(result["managers_supported"])
                existing.detection_tier = result["detection_tier"]
                existing.build_backend = result.get("build_backend")
                existing.lockfile_type = result.get("lockfile_type")
                existing.has_pyproject_toml = 1 if result.get("has_pyproject_toml") else 0
                existing.scanned_at = datetime.now(UTC)
            else:
                scan = PackageScan(
                    package_name=result["package"],
                    managers_supported=json.dumps(result["managers_supported"]),
                    detection_tier=result["detection_tier"],
                    build_backend=result.get("build_backend"),
                    lockfile_type=result.get("lockfile_type"),
                    has_pyproject_toml=1 if result.get("has_pyproject_toml") else 0,
                    scanned_at=datetime.now(UTC),
                )
                self._db.add(scan)
            self._db.commit()
        except Exception as exc:
            logger.error("Failed to persist scan for %s: %s", result["package"], exc)
            self._db.rollback()
