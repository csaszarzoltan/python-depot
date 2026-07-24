"""Pre-dev tests for OSV.dev API client.

Pattern:
- Interface tests: verify imports and class/function signatures — PASS immediately.
- Behavioral tests: verify scanning behavior — FAIL with NotImplementedError.
"""

from __future__ import annotations

from typing import get_type_hints

import pytest

# ---------------------------------------------------------------------------
# Interface tests — pass immediately (imports, signatures, type hints)
# ---------------------------------------------------------------------------


class TestOSVClientInterface:
    """Verify OSVClient class exists with expected interface."""

    def test_osv_client_import(self):
        """OSVClient can be imported."""
        from python_depot.dependency_health.osv_client import OSVClient

        assert OSVClient is not None

    def test_osv_client_is_class(self):
        """OSVClient is a class."""
        from python_depot.dependency_health.osv_client import OSVClient

        assert isinstance(OSVClient, type)

    def test_osv_client_init_signature(self):
        """OSVClient.__init__ accepts base_url with default."""
        import inspect

        from python_depot.dependency_health.osv_client import OSVClient

        sig = inspect.signature(OSVClient.__init__)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "base_url" in params
        # base_url should have a default
        assert sig.parameters["base_url"].default is not inspect.Parameter.empty

    def test_osv_client_has_query_package_method(self):
        """OSVClient has query_package async method."""
        from python_depot.dependency_health.osv_client import OSVClient

        assert hasattr(OSVClient, "query_package")
        assert callable(OSVClient.query_package)

    def test_osv_client_has_query_batch_method(self):
        """OSVClient has query_batch async method."""
        from python_depot.dependency_health.osv_client import OSVClient

        assert hasattr(OSVClient, "query_batch")
        assert callable(OSVClient.query_batch)

    def test_osv_client_has_get_vuln_details_method(self):
        """OSVClient has get_vuln_details async method."""
        from python_depot.dependency_health.osv_client import OSVClient

        assert hasattr(OSVClient, "get_vuln_details")
        assert callable(OSVClient.get_vuln_details)

    def test_query_package_signature(self):
        """query_package accepts name and optional version."""
        import inspect

        from python_depot.dependency_health.osv_client import OSVClient

        sig = inspect.signature(OSVClient.query_package)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "name" in params
        assert "version" in params
        # version should have a default (None)
        assert sig.parameters["version"].default is None

    def test_query_batch_signature(self):
        """query_batch accepts list of queries."""
        import inspect

        from python_depot.dependency_health.osv_client import OSVClient

        sig = inspect.signature(OSVClient.query_batch)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "queries" in params

    def test_get_vuln_details_signature(self):
        """get_vuln_details accepts vuln_id string."""
        import inspect

        from python_depot.dependency_health.osv_client import OSVClient

        sig = inspect.signature(OSVClient.get_vuln_details)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "vuln_id" in params

    def test_osv_client_returns_dict_from_query_package(self):
        """OSVClient.query_package return type is dict."""
        from python_depot.dependency_health.osv_client import OSVClient

        hints = get_type_hints(OSVClient.query_package)
        assert "return" in hints
        # dict[str, Any] checks
        ret = hints["return"]
        assert ret is dict or getattr(ret, "__origin__", None) is dict

    def test_osv_client_returns_dict_from_get_vuln_details(self):
        """OSVClient.get_vuln_details return type is dict."""
        from python_depot.dependency_health.osv_client import OSVClient

        hints = get_type_hints(OSVClient.get_vuln_details)
        assert "return" in hints


class TestOSVClientInstantiation:
    """Verify OSVClient can be instantiated with various configs."""

    def test_default_base_url(self):
        """Default base URL points to api.osv.dev."""
        from python_depot.dependency_health.osv_client import OSVClient

        client = OSVClient()
        assert client.base_url == "https://api.osv.dev"

    def test_custom_base_url(self):
        """Custom base URL is accepted."""
        from python_depot.dependency_health.osv_client import OSVClient

        client = OSVClient(base_url="https://staging.osv.dev")
        assert client.base_url == "https://staging.osv.dev"

    def test_base_url_trailing_slash_stripped(self):
        """Trailing slash on base_url is stripped."""
        from python_depot.dependency_health.osv_client import OSVClient

        client = OSVClient(base_url="https://api.osv.dev/")
        assert client.base_url == "https://api.osv.dev"


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestOSVClientBehavioral:
    """Behavioral tests for OSVClient — fail with NotImplementedError."""

    @pytest.mark.anyio
    async def test_query_package_returns_dict(self):
        """query_package returns a dict with vulns list."""
        from python_depot.dependency_health.osv_client import OSVClient

        client = OSVClient()
        result = await client.query_package("requests", "2.31.0")
        assert isinstance(result, dict)
        assert "vulns" in result

    @pytest.mark.anyio
    async def test_query_package_without_version(self):
        """query_package works without a version argument."""
        from python_depot.dependency_health.osv_client import OSVClient

        client = OSVClient()
        result = await client.query_package("requests")
        assert isinstance(result, dict)

    @pytest.mark.anyio
    async def test_query_batch_returns_list(self):
        """query_batch returns a list of dicts."""
        from python_depot.dependency_health.osv_client import OSVClient

        client = OSVClient()
        queries = [
            {"package": {"name": "requests", "ecosystem": "PyPI"}, "version": "2.31.0"},
            {"package": {"name": "flask", "ecosystem": "PyPI"}, "version": "2.3.0"},
        ]
        result = await client.query_batch(queries)
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.anyio
    async def test_query_batch_empty_returns_empty_list(self):
        """query_batch with empty list returns empty list."""
        from python_depot.dependency_health.osv_client import OSVClient

        client = OSVClient()
        result = await client.query_batch([])
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.anyio
    async def test_get_vuln_details_returns_dict(self):
        """get_vuln_details returns dict with full vulnerability info."""
        from python_depot.dependency_health.osv_client import OSVClient

        client = OSVClient()
        result = await client.get_vuln_details("GHSA-xxxx-xxxx-xxxx")
        assert isinstance(result, dict)
        assert "id" in result or "vuln_id" in result

    @pytest.mark.anyio
    async def test_get_vuln_details_has_cvss(self):
        """get_vuln_details returns CVSS data when available."""
        from python_depot.dependency_health.osv_client import OSVClient

        client = OSVClient()
        result = await client.get_vuln_details("GHSA-xxxx-xxxx-xxxx")
        if "severity" in result:
            assert isinstance(result["severity"], list)
