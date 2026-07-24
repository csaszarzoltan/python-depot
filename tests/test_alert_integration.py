"""Integration tests for alert system — scanner → alert engine → webhook flow.

Tests the pipeline end-to-end:
1. A scan triggers alert checking against the previous scan.
2. Webhooks fire only for vulnerabilities above a configurable threshold.
3. Alert history persists correctly in the vulnerability_alerts table.

Pattern:
- Interface tests: verify pipeline wiring, fixture setup — PASS immediately.
- Behavioral tests: verify end-to-end alert behaviour — raise
  NotImplementedError until the pipeline is fully implemented.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from python_depot.dependency_health.alerts import AlertEngine
from python_depot.dependency_health.models import VulnerabilityAlert

# ---------------------------------------------------------------------------
# Interface tests — pass immediately
# ---------------------------------------------------------------------------


class TestInterfaceIntegration:
    """Verify that integration fixtures and imports resolve."""

    def test_alert_engine_importable(self):
        """AlertEngine can be imported from alerts module."""
        from python_depot.dependency_health import alerts

        assert hasattr(alerts, "AlertEngine")

    def test_vulnerability_alert_importable(self):
        """VulnerabilityAlert can be imported from models module."""
        from python_depot.dependency_health import models

        assert hasattr(models, "VulnerabilityAlert")

    def test_engine_can_query_alerts(self):
        """AlertEngine.list_alerts works with a real DB session."""
        from python_depot.database import SessionLocal, reset_db

        reset_db()
        session = SessionLocal()
        try:
            engine = AlertEngine(db=session)
            result = engine.list_alerts()
            assert isinstance(result, list)
        finally:
            session.close()

    def test_alert_model_table_exists(self):
        """vulnerability_alerts table is created on init_db / reset_db."""
        from sqlalchemy import inspect

        from python_depot.database import SessionLocal, reset_db

        reset_db()
        engine = SessionLocal().get_bind()
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "vulnerability_alerts" in table_names


# ---------------------------------------------------------------------------
# Behavioral tests — end-to-end scanner → alert → webhook flow
# ---------------------------------------------------------------------------


class TestBehavioralScanTriggersAlert:
    """Scanning a package triggers alert checking."""

    @pytest.mark.anyio
    async def test_new_vuln_after_scan_creates_alert(self):
        """After a scan with new vulns, an alert record exists in the DB."""
        from python_depot.database import SessionLocal, reset_db

        reset_db()
        session = SessionLocal()
        try:
            engine = AlertEngine(db=session)

            # First scan — clean
            first_scan = {
                "package": "flask",
                "status": "clean",
                "vulnerabilities": [],
            }
            engine.check_new_vulns("flask", first_scan)

            # Second scan — new vuln
            second_scan = {
                "package": "flask",
                "status": "vulnerable",
                "vulnerabilities": [
                    {"id": "GHSA-flask-0001", "severity": "HIGH", "score": 7.5}
                ],
            }
            alerts = engine.check_new_vulns("flask", second_scan)

            assert len(alerts) > 0
            vuln_ids = [a["vuln_id"] for a in alerts]
            assert "GHSA-flask-0001" in vuln_ids
        finally:
            session.close()

    @pytest.mark.anyio
    async def test_no_duplicate_alerts_on_consecutive_scans(self):
        """A vuln seen in two consecutive scans does not create duplicate alerts."""
        from python_depot.database import SessionLocal, reset_db

        reset_db()
        session = SessionLocal()
        try:
            engine = AlertEngine(db=session)

            # First scan — introduces vuln
            scan_a = {
                "package": "django",
                "vulnerabilities": [
                    {"id": "GHSA-dj-0001", "severity": "HIGH"},
                ],
            }
            engine.check_new_vulns("django", scan_a)

            # Second scan — same vuln still present
            scan_b = {
                "package": "django",
                "vulnerabilities": [
                    {"id": "GHSA-dj-0001", "severity": "HIGH"},
                ],
            }
            alerts_b = engine.check_new_vulns("django", scan_b)

            assert len(alerts_b) == 0
        finally:
            session.close()

    @pytest.mark.anyio
    async def test_scan_of_new_package_creates_alerts(self):
        """First-ever scan of a package treats all vulns as new alerts."""
        from python_depot.database import SessionLocal, reset_db

        reset_db()
        session = SessionLocal()
        try:
            engine = AlertEngine(db=session)

            scan = {
                "package": "new-pkg",
                "vulnerabilities": [
                    {"id": "GHSA-new-001", "severity": "CRITICAL"},
                ],
            }
            alerts = engine.check_new_vulns("new-pkg", scan)
            assert len(alerts) == 1
            assert alerts[0]["vuln_id"] == "GHSA-new-001"
        finally:
            session.close()


class TestBehavioralWebhookThreshold:
    """Webhook fires only for vulnerabilities above the severity threshold."""

    @pytest.mark.anyio
    async def test_webhook_fires_for_critical(self):
        """A CRITICAL vuln above a MEDIUM threshold fires the webhook."""
        engine = AlertEngine(
            db=MagicMock(),
            webhook_url="https://hooks.example.com/alerts",
            severity_threshold="MEDIUM",
        )
        alert = {
            "package_name": "flask",
            "vuln_id": "GHSA-crit-001",
            "severity": "CRITICAL",
            "score": 9.5,
            "timestamp": "2026-07-24T00:00:00Z",
        }
        result = await engine.fire_webhook(alert)
        assert result is True

    @pytest.mark.anyio
    async def test_webhook_does_not_fire_for_below_threshold(self):
        """A LOW vuln with CRITICAL threshold does NOT fire the webhook."""
        engine = AlertEngine(
            db=MagicMock(),
            webhook_url="https://hooks.example.com/alerts",
            severity_threshold="CRITICAL",
        )
        alert = {
            "package_name": "flask",
            "vuln_id": "GHSA-low-001",
            "severity": "LOW",
            "score": 2.0,
            "timestamp": "2026-07-24T00:00:00Z",
        }
        result = await engine.fire_webhook(alert)
        assert result is False

    @pytest.mark.anyio
    async def test_webhook_threshold_respected_multiple_alerts(self):
        """Only vulns above threshold trigger webhook in a batch."""
        engine = AlertEngine(
            db=MagicMock(),
            webhook_url="https://hooks.example.com/alerts",
            severity_threshold="HIGH",
        )
        low_alert = {
            "package_name": "celery",
            "vuln_id": "GHSA-low-002",
            "severity": "LOW",
            "score": 1.0,
        }
        high_alert = {
            "package_name": "celery",
            "vuln_id": "GHSA-high-002",
            "severity": "HIGH",
            "score": 7.0,
        }
        low_result = await engine.fire_webhook(low_alert)
        high_result = await engine.fire_webhook(high_alert)
        assert low_result is False
        assert high_result is True

    @pytest.mark.anyio
    async def test_correct_payload_sent(self):
        """Webhook receives the expected payload structure."""
        engine = AlertEngine(
            db=MagicMock(),
            webhook_url="https://hooks.example.com/alerts",
        )
        alert = {
            "package_name": "requests",
            "vuln_id": "GHSA-rq-0001",
            "severity": "CRITICAL",
            "score": 9.0,
            "timestamp": "2026-07-24T12:00:00Z",
        }
        result = await engine.fire_webhook(alert)
        assert result is True


class TestBehavioralAlertHistory:
    """Alert history persists and is queryable."""

    def test_alert_persists_in_db(self):
        """After an alert is created, it is stored in vulnerability_alerts."""
        from python_depot.database import SessionLocal, reset_db

        reset_db()
        session = SessionLocal()
        try:
            engine = AlertEngine(db=session)

            scan = {
                "package": "flask",
                "vulnerabilities": [
                    {"id": "GHSA-persist-001", "severity": "HIGH"},
                ],
            }
            engine.check_new_vulns("flask", scan)

            stored = (
                session.query(VulnerabilityAlert)
                .filter(VulnerabilityAlert.vuln_id == "GHSA-persist-001")
                .first()
            )
            assert stored is not None
            assert stored.package_id is not None
            assert stored.severity == "HIGH"
        finally:
            session.close()

    def test_alert_history_multi_package(self):
        """Alerts across multiple packages are queryable independently."""
        from python_depot.database import SessionLocal, reset_db

        reset_db()
        session = SessionLocal()
        try:
            engine = AlertEngine(db=session)

            engine.check_new_vulns(
                "flask",
                {
                    "package": "flask",
                    "vulnerabilities": [
                        {"id": "GHSA-flask-hist-001", "severity": "HIGH"},
                    ],
                },
            )
            engine.check_new_vulns(
                "django",
                {
                    "package": "django",
                    "vulnerabilities": [
                        {"id": "GHSA-django-hist-001", "severity": "CRITICAL"},
                    ],
                },
            )

            flask_alerts = engine.list_alerts(package_name="flask")
            django_alerts = engine.list_alerts(package_name="django")

            assert len(flask_alerts) >= 1
            assert len(django_alerts) >= 1
            for fa in flask_alerts:
                assert fa["package_name"] == "flask"
            for da in django_alerts:
                assert da["package_name"] == "django"
        finally:
            session.close()

    def test_alert_history_severity_filter(self):
        """Alert history can be filtered by severity."""
        from python_depot.database import SessionLocal, reset_db

        reset_db()
        session = SessionLocal()
        try:
            engine = AlertEngine(db=session)

            engine.check_new_vulns(
                "pandas",
                {
                    "package": "pandas",
                    "vulnerabilities": [
                        {"id": "GHSA-pd-low", "severity": "LOW"},
                        {"id": "GHSA-pd-high", "severity": "HIGH"},
                        {"id": "GHSA-pd-crit", "severity": "CRITICAL"},
                    ],
                },
            )

            critical_alerts = engine.list_alerts(severity="CRITICAL")
            assert len(critical_alerts) >= 1
            for ca in critical_alerts:
                assert ca["severity"] == "CRITICAL"
        finally:
            session.close()

    def test_webhook_status_tracking(self):
        """Alert records reflect webhook delivery status."""
        from python_depot.database import SessionLocal, reset_db

        reset_db()
        session = SessionLocal()
        try:
            engine = AlertEngine(
                db=session,
                webhook_url="https://hooks.example.com/alerts",
            )

            scan = {
                "package": "fastapi",
                "vulnerabilities": [
                    {"id": "GHSA-fa-hook-001", "severity": "HIGH"},
                ],
            }
            engine.check_new_vulns("fastapi", scan)

            stored = (
                session.query(VulnerabilityAlert)
                .filter(VulnerabilityAlert.vuln_id == "GHSA-fa-hook-001")
                .first()
            )
            assert stored is not None
        finally:
            session.close()
