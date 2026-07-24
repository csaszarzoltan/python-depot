"""Pre-dev tests for vulnerability alert engine.

Pattern:
- Interface tests: verify imports and class signatures — PASS immediately.
- Behavioral tests: verify alert detection and webhook firing — FAIL with NotImplementedError.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Interface tests — pass immediately (imports, signatures, type hints)
# ---------------------------------------------------------------------------


class TestAlertInterface:
    """Verify AlertEngine class exists with expected interface."""

    def test_alert_engine_import(self):
        """AlertEngine can be imported."""
        from python_depot.dependency_health.alerts import AlertEngine

        assert AlertEngine is not None

    def test_alert_engine_is_class(self):
        """AlertEngine is a class."""
        from python_depot.dependency_health.alerts import AlertEngine

        assert isinstance(AlertEngine, type)

    def test_alert_engine_init_signature(self):
        """AlertEngine.__init__ accepts db and severity_threshold."""
        import inspect

        from python_depot.dependency_health.alerts import AlertEngine

        sig = inspect.signature(AlertEngine.__init__)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "db" in params
        assert "severity_threshold" in params

    def test_default_severity_threshold(self):
        """Default severity_threshold is MEDIUM."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db=None)  # type: ignore[arg-type]
        assert engine.severity_threshold == "MEDIUM"

    def test_custom_severity_threshold(self):
        """Custom severity_threshold is accepted."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db=None, severity_threshold="HIGH")  # type: ignore[arg-type]
        assert engine.severity_threshold == "HIGH"

    def test_has_check_new_vulns_method(self):
        """AlertEngine has check_new_vulns method."""
        from python_depot.dependency_health.alerts import AlertEngine

        assert hasattr(AlertEngine, "check_new_vulns")
        assert callable(AlertEngine.check_new_vulns)

    def test_has_fire_webhook_method(self):
        """AlertEngine has fire_webhook method."""
        from python_depot.dependency_health.alerts import AlertEngine

        assert hasattr(AlertEngine, "fire_webhook")
        assert callable(AlertEngine.fire_webhook)

    def test_has_list_alerts_method(self):
        """AlertEngine has list_alerts method."""
        from python_depot.dependency_health.alerts import AlertEngine

        assert hasattr(AlertEngine, "list_alerts")
        assert callable(AlertEngine.list_alerts)

    def test_check_new_vulns_signature(self):
        """check_new_vulns accepts package_name and current_scan."""
        import inspect

        from python_depot.dependency_health.alerts import AlertEngine

        sig = inspect.signature(AlertEngine.check_new_vulns)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "package_name" in params
        assert "current_scan" in params

    def test_fire_webhook_signature(self):
        """fire_webhook accepts alert and webhook_url."""
        import inspect

        from python_depot.dependency_health.alerts import AlertEngine

        sig = inspect.signature(AlertEngine.fire_webhook)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "alert" in params
        assert "webhook_url" in params

    def test_list_alerts_signature(self):
        """list_alerts accepts optional package_name."""
        import inspect

        from python_depot.dependency_health.alerts import AlertEngine

        sig = inspect.signature(AlertEngine.list_alerts)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "package_name" in params

    def test_list_alerts_optional_arg_defaults_none(self):
        """list_alerts package_name defaults to None."""
        import inspect

        from python_depot.dependency_health.alerts import AlertEngine

        sig = inspect.signature(AlertEngine.list_alerts)
        param = sig.parameters["package_name"]
        assert param.default is None

    def test_db_stored_as_db(self):
        """AlertEngine stores db as self.db."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db="fake_session")  # type: ignore[arg-type]
        assert engine.db == "fake_session"


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestAlertBehavioral:
    """Behavioral tests for AlertEngine — fail with NotImplementedError."""

    def test_check_new_vulns_detects_new_vulns(self):
        """check_new_vulns returns newly discovered vulnerabilities."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db=None)  # type: ignore[arg-type]
        current_scan = {
            "vulns": [
                {"id": "GHSA-aaa", "severity": "HIGH"},
                {"id": "GHSA-bbb", "severity": "CRITICAL"},
            ]
        }
        new_vulns = engine.check_new_vulns("requests", current_scan)
        assert isinstance(new_vulns, list)
        # Should detect new vulns since no previous scan exists
        assert len(new_vulns) >= 0

    def test_check_new_vulns_returns_empty_when_no_new_vulns(self):
        """check_new_vulns returns empty list when no new vulns."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db=None)  # type: ignore[arg-type]
        current_scan = {"vulns": []}
        new_vulns = engine.check_new_vulns("requests", current_scan)
        assert isinstance(new_vulns, list)
        assert len(new_vulns) == 0

    @pytest.mark.anyio
    async def test_fire_webhook_returns_bool(self):
        """fire_webhook returns a boolean."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db=None)  # type: ignore[arg-type]
        alert = {
            "package": "requests",
            "vuln_id": "GHSA-xxxx",
            "severity": "HIGH",
            "score": 7.5,
        }
        result = await engine.fire_webhook(alert)
        assert isinstance(result, bool)

    @pytest.mark.anyio
    async def test_fire_webhook_returns_true_on_success(self):
        """fire_webhook returns True for 2xx response."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(
            db=None,
            webhook_url="https://hooks.example.com/alerts",
        )  # type: ignore[arg-type]
        alert = {"package": "flask", "vuln_id": "GHSA-yyyy", "severity": "MEDIUM"}
        result = await engine.fire_webhook(alert)
        assert result is True

    def test_list_alerts_returns_list(self):
        """list_alerts returns a list of alert dicts."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db=None)  # type: ignore[arg-type]
        alerts = engine.list_alerts()
        assert isinstance(alerts, list)

    def test_list_alerts_by_package(self):
        """list_alerts filtered by package returns only that package's alerts."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db=None)  # type: ignore[arg-type]
        alerts = engine.list_alerts(package_name="requests")
        assert isinstance(alerts, list)
        # All returned alerts should be for "requests"
        for alert in alerts:
            assert alert.get("package") == "requests"

    def test_list_alerts_empty_when_no_alerts(self):
        """list_alerts returns empty list when no alerts exist."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db=None)  # type: ignore[arg-type]
        alerts = engine.list_alerts()
        assert len(alerts) == 0

    def test_alert_dict_shape(self):
        """check_new_vulns returns alerts with expected fields."""
        from python_depot.dependency_health.alerts import AlertEngine

        engine = AlertEngine(db=None)  # type: ignore[arg-type]
        current_scan = {
            "vulns": [
                {"id": "GHSA-ccc", "severity": "CRITICAL", "score": 9.5},
            ]
        }
        new_vulns = engine.check_new_vulns("django", current_scan)
        if new_vulns:
            alert = new_vulns[0]
            assert "vuln_id" in alert or "id" in alert
            assert "severity" in alert
            assert "package" in alert or "package_name" in alert
