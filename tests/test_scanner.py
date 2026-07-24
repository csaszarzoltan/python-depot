"""Pre-dev tests for DependencyScanner.

Pattern:
- Interface tests: verify imports and class signatures — PASS immediately.
- Behavioral tests: verify scanning behavior — FAIL with NotImplementedError.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Interface tests — pass immediately (imports, signatures, type hints)
# ---------------------------------------------------------------------------


class TestScannerInterface:
    """Verify DependencyScanner class exists with expected interface."""

    def test_dependency_scanner_import(self):
        """DependencyScanner can be imported."""
        from python_depot.dependency_health.scanner import DependencyScanner

        assert DependencyScanner is not None

    def test_health_scanner_still_imports(self):
        """Existing HealthScanner still imports (backward compat)."""
        from python_depot.dependency_health.scanner import HealthScanner

        assert HealthScanner is not None

    def test_dependency_scanner_is_class(self):
        """DependencyScanner is a class."""
        from python_depot.dependency_health.scanner import DependencyScanner

        assert isinstance(DependencyScanner, type)

    def test_dependency_scanner_init_signature(self):
        """DependencyScanner.__init__ accepts db session."""
        import inspect

        from python_depot.dependency_health.scanner import DependencyScanner

        sig = inspect.signature(DependencyScanner.__init__)
        params = list(sig.parameters.keys())
        assert "self" in params

    def test_has_scan_package_method(self):
        """DependencyScanner has scan_package method."""
        from python_depot.dependency_health.scanner import DependencyScanner

        assert hasattr(DependencyScanner, "scan_package")
        assert callable(DependencyScanner.scan_package)

    def test_has_scan_batch_method(self):
        """DependencyScanner has scan_batch method."""
        from python_depot.dependency_health.scanner import DependencyScanner

        assert hasattr(DependencyScanner, "scan_batch")
        assert callable(DependencyScanner.scan_batch)

    def test_has_list_scans_method(self):
        """DependencyScanner has list_scans method."""
        from python_depot.dependency_health.scanner import DependencyScanner

        assert hasattr(DependencyScanner, "list_scans")
        assert callable(DependencyScanner.list_scans)

    def test_has_latest_scan_method(self):
        """DependencyScanner has latest_scan method."""
        from python_depot.dependency_health.scanner import DependencyScanner

        assert hasattr(DependencyScanner, "latest_scan")
        assert callable(DependencyScanner.latest_scan)

    def test_scan_package_signature(self):
        """scan_package accepts name and optional version."""
        import inspect

        from python_depot.dependency_health.scanner import DependencyScanner

        sig = inspect.signature(DependencyScanner.scan_package)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "name" in params
        assert "version" in params or "pkg_id" in params

    def test_scan_batch_signature(self):
        """scan_batch accepts packages list."""
        import inspect

        from python_depot.dependency_health.scanner import DependencyScanner

        sig = inspect.signature(DependencyScanner.scan_batch)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "packages" in params

    def test_list_scans_signature(self):
        """list_scans accepts package identifiers."""
        import inspect

        from python_depot.dependency_health.scanner import DependencyScanner

        sig = inspect.signature(DependencyScanner.list_scans)
        params = list(sig.parameters.keys())
        assert "self" in params

    def test_latest_scan_signature(self):
        """latest_scan accepts package identifiers."""
        import inspect

        from python_depot.dependency_health.scanner import DependencyScanner

        sig = inspect.signature(DependencyScanner.latest_scan)
        params = list(sig.parameters.keys())
        assert "self" in params


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestScannerBehavioral:
    """Behavioral tests for DependencyScanner — fail with NotImplementedError."""

    @pytest.mark.anyio
    async def test_scan_package_returns_dict(self):
        """scan_package returns dict with status, vuln count."""
        from python_depot.dependency_health.scanner import DependencyScanner

        async def mock_db():
            raise NotImplementedError

        scanner = DependencyScanner(db=None)  # type: ignore[arg-type]
        result = await scanner.scan_package("requests", "2.31.0")
        assert isinstance(result, dict)
        assert "status" in result
        assert "package" in result
        assert result["package"] == "requests"

    @pytest.mark.anyio
    async def test_scan_batch_returns_list(self):
        """scan_batch returns list of scan results."""
        from python_depot.dependency_health.scanner import DependencyScanner

        scanner = DependencyScanner(db=None)  # type: ignore[arg-type]
        packages = [
            {"name": "requests", "version": "2.31.0"},
            {"name": "flask", "version": "2.3.0"},
        ]
        result = await scanner.scan_batch(packages)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_list_scans_returns_dict(self):
        """list_scans returns dict with scans list."""
        from python_depot.dependency_health.scanner import DependencyScanner

        scanner = DependencyScanner(db=None)  # type: ignore[arg-type]
        result = scanner.list_scans(pkg_id=1, name="requests")
        assert isinstance(result, dict)
        assert "scans" in result

    def test_list_scans_empty_returns_empty_list(self):
        """list_scans returns empty scans list when no scans exist."""
        from python_depot.dependency_health.scanner import DependencyScanner

        scanner = DependencyScanner(db=None)  # type: ignore[arg-type]
        result = scanner.list_scans(pkg_id=1, name="requests")
        assert result["scans"] == []

    def test_latest_scan_returns_dict(self):
        """latest_scan returns dict with scan or null."""
        from python_depot.dependency_health.scanner import DependencyScanner

        scanner = DependencyScanner(db=None)  # type: ignore[arg-type]
        result = scanner.latest_scan(pkg_id=1, name="requests")
        assert isinstance(result, dict)
        assert "scan" in result

    @pytest.mark.anyio
    async def test_scan_package_stores_results(self):
        """scan_package stores scan results in DB."""
        from python_depot.dependency_health.scanner import DependencyScanner

        scanner = DependencyScanner(db=None)  # type: ignore[arg-type]
        result = await scanner.scan_package("requests", "2.31.0")
        assert "scan_id" in result

    @pytest.mark.anyio
    async def test_scan_empty_package_handled_gracefully(self):
        """scan_package handles empty or invalid package names."""
        from python_depot.dependency_health.scanner import DependencyScanner

        scanner = DependencyScanner(db=None)  # type: ignore[arg-type]
        result = await scanner.scan_package("")
        assert isinstance(result, dict)
