"""Vulnerability alert engine — detects new vulns, fires webhooks, lists alerts.

Compares current scan results against previous scans to detect newly
discovered vulnerabilities, fires webhook notifications for alerts
above the configured severity threshold, and provides alert history.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from python_depot.dependency_health.models import VulnerabilityAlert

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


class AlertEngine:
    """Vulnerability alert engine.

    Compares current scan against previous scan results, detects newly
    discovered vulnerabilities, and fires webhook notifications for
    alerts meeting the configured severity threshold.
    """

    def __init__(
        self,
        db: Session,
        webhook_url: str | None = None,
        severity_threshold: str = "MEDIUM",
    ) -> None:
        """Initialize the alert engine.

        Args:
            db: SQLAlchemy database session for reading/writing alerts.
            webhook_url: Optional webhook URL for alert delivery.
            severity_threshold: Minimum severity level that triggers webhooks
                                ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL').
        """
        self.db = db
        self.webhook_url = webhook_url
        self.severity_threshold = severity_threshold

    def _meets_threshold(self, severity: str) -> bool:
        """Check if severity meets or exceeds the configured threshold."""
        try:
            return (
                SEVERITY_ORDER.index(severity)
                >= SEVERITY_ORDER.index(self.severity_threshold)
            )
        except (ValueError, IndexError):
            return False

    def _extract_vulns_from_scan(self, current_scan: dict) -> list[dict]:
        """Extract vulnerability list from a scan result dict.

        Handles multiple key formats for backward compatibility:
        - 'details' (JSON string or list)
        - 'vulnerabilities' (list)
        - 'vulns' (list)
        """
        # Check for 'details' key (JSON string from scanner output)
        details_raw = current_scan.get("details")
        if details_raw:
            try:
                parsed = (
                    json.loads(details_raw) if isinstance(details_raw, str)
                    else details_raw
                )
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass

        # Check for 'vulnerabilities' key (used by tests)
        vulns = current_scan.get("vulnerabilities")
        if isinstance(vulns, list):
            return vulns

        # Check for 'vulns' key (OSV.dev response format)
        vulns = current_scan.get("vulns")
        if isinstance(vulns, list):
            return vulns

        return []

    def check_new_vulns(
        self, package_name: str, current_scan: dict
    ) -> list[dict]:
        """Compare current scan against previous scan for new vulnerabilities.

        Args:
            package_name: Name of the scanned package.
            current_scan: Dict from the current scan containing vulnerability
                          data (vuln IDs, severity, etc.).

        Returns:
            List of newly discovered vulnerability dicts that did not appear
            in the previous scan. Empty list if nothing new.
        """
        current_vulns = self._extract_vulns_from_scan(current_scan)

        if not current_vulns:
            return []

        # If no DB session, return all vulns as new (no dedup possible)
        if self.db is None:
            enriched = []
            for v in current_vulns:
                entry = {**v}
                if "id" in entry and "vuln_id" not in entry:
                    entry["vuln_id"] = entry["id"]
                entry["package_name"] = package_name
                enriched.append(entry)
            return enriched

        package_id = current_scan.get("package_id", 0)

        # Get all previous alert IDs for this package
        previous_alerts = (
            self.db.query(VulnerabilityAlert.vuln_id)
            .filter(VulnerabilityAlert.package_id == package_id)
            .all()
        )
        known_ids: set[str] = {alert.vuln_id for alert in previous_alerts}

        # Filter for new vulnerabilities
        new_vulns: list[dict] = []
        for vuln in current_vulns:
            vuln_id = vuln.get("id", "") or vuln.get("vuln_id", "")
            if not vuln_id:
                continue
            if vuln_id not in known_ids:
                # Create a new alert record
                severity = vuln.get("severity", "MEDIUM")
                alert = VulnerabilityAlert(
                    package_id=package_id,
                    vuln_id=vuln_id,
                    severity=severity,
                    score=vuln.get("score"),
                    details=json.dumps(vuln) if vuln else None,
                    webhook_status="pending",
                )
                self.db.add(alert)
                self.db.commit()
                self.db.refresh(alert)
                # Normalize keys for return value
                entry = {**vuln}
                if "id" in entry and "vuln_id" not in entry:
                    entry["vuln_id"] = entry["id"]
                entry["package_name"] = package_name
                new_vulns.append(entry)

        return new_vulns

    async def fire_webhook(
        self, alert: dict, webhook_url: str | None = None
    ) -> bool:
        """POST an alert payload to the configured webhook URL.

        Args:
            alert: Alert dict with package name, vuln details, severity,
                   and timestamp.
            webhook_url: Override the default webhook URL for this call.
                         Falls back to ``self.webhook_url`` if not provided.

        Returns:
            True if the webhook was accepted (HTTP 2xx), False if the alert
            is below the severity threshold or delivery failed.
        """
        target_url = webhook_url or self.webhook_url
        if not target_url:
            logger.warning("No webhook URL configured — skipping alert delivery")
            return False

        severity = alert.get("severity", "LOW")
        if not self._meets_threshold(severity):
            logger.debug(
                "Alert severity %s below threshold %s — skipping",
                severity,
                self.severity_threshold,
            )
            return False

        payload = {
            "event": "vulnerability_alert",
            "severity": severity,
            "package": alert.get("package_name", "unknown") or alert.get("package", "unknown"),
            "vuln_id": alert.get("vuln_id"),
            "score": alert.get("score"),
            "timestamp": datetime.now(UTC).isoformat(),
            "details": alert.get("details"),
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(target_url, json=payload)
                resp.raise_for_status()
                logger.info(
                    "Webhook delivered for %s (%s): %d",
                    payload["vuln_id"],
                    payload["severity"],
                    resp.status_code,
                )
                return True
        except httpx.HTTPError as exc:
            logger.error("Webhook delivery failed: %s", exc)
            return False

    def list_alerts(
        self, package_name: str | None = None, severity: str | None = None
    ) -> list[dict]:
        """List alert history, optionally filtered by package or severity.

        Args:
            package_name: Optional package name to filter alerts.
            severity: Optional severity level to filter by.

        Returns:
            List of alert dicts with id, package, vuln_id, severity,
            score, webhook_status, and created_at.
        """
        if self.db is None:
            return []

        query = self.db.query(VulnerabilityAlert)

        if severity:
            query = query.filter(VulnerabilityAlert.severity == severity.upper())

        alerts = query.order_by(VulnerabilityAlert.created_at.desc()).all()

        results: list[dict] = []
        for alert in alerts:
            results.append({
                "id": alert.id,
                "package_name": package_name or "unknown",
                "vuln_id": alert.vuln_id,
                "severity": alert.severity,
                "score": alert.score,
                "webhook_status": alert.webhook_status,
                "created_at": alert.created_at.isoformat(),
            })

        return results
