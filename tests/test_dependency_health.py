"""Pre-dev tests for dependency health dashboard endpoints.

Pattern:
- Interface tests: verify router registration and endpoint shapes — PASS immediately.
- Behavioral tests: verify dashboard data — FAIL with NotImplementedError.
"""

from __future__ import annotations

import pytest
from fastapi.routing import APIRoute, _IncludedRouter

from src.app import app


class Routes:
    """Helper to access all routes including those in included routers."""

    @staticmethod
    def paths():
        """Return set of all registered route paths (full, with prefixes)."""
        paths = set()
        for r in app.routes:
            if isinstance(r, _IncludedRouter):
                prefix = r.include_context.prefix
                for route in r.original_router.routes:
                    paths.add(prefix + route.path)
            elif isinstance(r, APIRoute):
                paths.add(r.path)
        return paths


# ---------------------------------------------------------------------------
# Interface tests — pass immediately (imports, route definitions)
# ---------------------------------------------------------------------------


class TestDashboardInterface:
    """Verify the dependency health router module can be imported."""

    def test_dependency_health_router_import(self):
        """Dependency health router can be imported."""
        from python_depot.routers.dependency_health import router

        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_endpoints(self):
        """Router has at least one endpoint defined."""
        from python_depot.routers.dependency_health import router

        assert len(router.routes) >= 4

    def test_overview_endpoint_registered(self):
        """GET /api/v1/dependency-health/overview is registered."""
        paths = Routes.paths()
        assert "/api/v1/dependency-health/overview" in paths

    def test_trends_endpoint_registered(self):
        """GET /api/v1/dependency-health/trends is registered."""
        paths = Routes.paths()
        assert "/api/v1/dependency-health/trends" in paths

    def test_packages_endpoint_registered(self):
        """GET /api/v1/dependency-health/packages is registered."""
        paths = Routes.paths()
        assert "/api/v1/dependency-health/packages" in paths

    def test_alerts_endpoint_registered(self):
        """GET /api/v1/dependency-health/alerts is registered."""
        paths = Routes.paths()
        assert "/api/v1/dependency-health/alerts" in paths

    def test_package_score_endpoint_registered(self):
        """GET /api/v1/dependency-health/{package_name}/score is registered."""
        paths = Routes.paths()
        assert "/api/v1/dependency-health/{package_name}/score" in paths


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestDashboardBehavioral:
    """Behavioral tests for dashboard endpoints — fail with NotImplementedError."""

    @pytest.mark.anyio
    async def test_overview_endpoint_returns_stats(self, client):
        """GET /api/v1/dependency-health/overview returns aggregate stats."""
        resp = await client.get("/api/v1/dependency-health/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_packages" in data
        assert "vuln_counts" in data
        assert "severity_breakdown" in data or "vuln_counts" in data
        assert "last_scan" in data or "last_scan_at" in data

    @pytest.mark.anyio
    async def test_trends_endpoint_returns_time_series(self, client):
        """GET /api/v1/dependency-health/trends returns trend data."""
        resp = await client.get("/api/v1/dependency-health/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert "trends" in data
        assert isinstance(data["trends"], list)

    @pytest.mark.anyio
    async def test_packages_endpoint_returns_list(self, client):
        """GET /api/v1/dependency-health/packages returns packages sorted by score."""
        resp = await client.get("/api/v1/dependency-health/packages")
        assert resp.status_code == 200
        data = resp.json()
        assert "packages" in data
        assert isinstance(data["packages"], list)
        assert "total" in data

    @pytest.mark.anyio
    async def test_packages_endpoint_supports_sorting(self, client):
        """GET /api/v1/dependency-health/packages supports sort_by param."""
        resp = await client.get(
            "/api/v1/dependency-health/packages?sort_by=vuln_count"
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_packages_endpoint_supports_pagination(self, client):
        """GET /api/v1/dependency-health/packages supports limit and offset."""
        resp = await client.get(
            "/api/v1/dependency-health/packages?limit=5&offset=0"
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_alerts_endpoint_returns_alerts(self, client):
        """GET /api/v1/dependency-health/alerts returns alerts list."""
        resp = await client.get("/api/v1/dependency-health/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)
        assert "total" in data

    @pytest.mark.anyio
    async def test_alerts_endpoint_filters_by_severity(self, client):
        """GET /api/v1/dependency-health/alerts supports severity filter."""
        resp = await client.get(
            "/api/v1/dependency-health/alerts?severity=CRITICAL"
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_alerts_endpoint_supports_pagination(self, client):
        """GET /api/v1/dependency-health/alerts supports limit and offset."""
        resp = await client.get(
            "/api/v1/dependency-health/alerts?limit=10&offset=0"
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_package_score_returns_score(self, client):
        """GET /api/v1/dependency-health/{name}/score returns health score."""
        resp = await client.get(
            "/api/v1/dependency-health/requests/score"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "package" in data
        assert data["package"] == "requests"
        assert "score" in data
        assert "breakdown" in data
        assert isinstance(data["score"], (int, float))

    @pytest.mark.anyio
    async def test_package_score_unknown_package(self, client):
        """GET /api/v1/dependency-health/{name}/score handles unknown packages."""
        resp = await client.get(
            "/api/v1/dependency-health/nonexistent-pkg-12345/score"
        )
        # Should return 200 with a score of 100 (no vulns = perfect)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_package_score_includes_breakdown(self, client):
        """GET /api/v1/dependency-health/{name}/score includes breakdown."""
        resp = await client.get(
            "/api/v1/dependency-health/flask/score"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "breakdown" in data
        assert "vuln_count" in data or "vulnerability_count" in data
        assert "max_severity" in data or "severity" in data
        assert "score_label" in data
