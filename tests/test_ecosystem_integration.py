"""Integration tests for the Ecosystem & Migration Hub endpoints."""
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

    @staticmethod
    def methods_for_path(target_path):
        """Return the union of HTTP methods across all routes at the given path."""
        all_methods = set()
        for r in app.routes:
            if isinstance(r, _IncludedRouter):
                prefix = r.include_context.prefix
                for route in r.original_router.routes:
                    if prefix + route.path == target_path and route.methods:
                        all_methods.update(route.methods)
            elif isinstance(r, APIRoute) and r.path == target_path and r.methods:
                all_methods.update(r.methods)
        return all_methods


# ---------------------------------------------------------------------------
# Interface tests
# ---------------------------------------------------------------------------


class TestEcosystemRouterInterface:
    """Verify the ecosystem router module can be imported and has expected routes."""

    def test_ecosystem_router_import(self):
        """Ecosystem router can be imported."""
        from python_depot.routers.ecosystem import router

        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_endpoints(self):
        """Ecosystem router has at least 4 endpoints defined."""
        from python_depot.routers.ecosystem import router

        assert len(router.routes) >= 4

    def test_all_ecosystem_endpoints_registered(self):
        """All ecosystem endpoints are registered on the app."""
        paths = Routes.paths()
        expected = {
            "/api/v1/ecosystem/detect/{name}",
            "/api/v1/ecosystem/stats",
            "/api/v1/ecosystem/migration-guide/{name}",
            "/api/v1/ecosystem/compatibility",
        }
        missing = expected - paths
        assert not missing, f"Expected ecosystem routes missing: {missing}"

    def test_ecosystem_routes_are_get(self):
        """All ecosystem routes use GET method."""
        for path in (
            "/api/v1/ecosystem/detect/{name}",
            "/api/v1/ecosystem/stats",
            "/api/v1/ecosystem/migration-guide/{name}",
            "/api/v1/ecosystem/compatibility",
        ):
            methods = Routes.methods_for_path(path)
            assert "GET" in methods, f"{path} should support GET"


# ---------------------------------------------------------------------------
# Behavioral tests
# ---------------------------------------------------------------------------


class TestDetectEndpoint:
    """Behavioral contract: GET /api/v1/ecosystem/detect/{name}"""

    @pytest.mark.anyio
    async def test_detect_known_package_returns_200(self, client):
        """GET /api/v1/ecosystem/detect/requests returns 200 with expected schema."""
        resp = await client.get("/api/v1/ecosystem/detect/requests")
        assert resp.status_code == 200
        data = resp.json()
        assert "package" in data
        assert data["package"] == "requests"
        assert "managers_supported" in data
        assert isinstance(data["managers_supported"], list)
        assert "detection_tier" in data
        assert "scanned_at" in data

    @pytest.mark.anyio
    async def test_detect_unknown_package_returns_404(self, client):
        """GET /api/v1/ecosystem/detect/unknown-pkg-xyz returns 404."""
        resp = await client.get(
            "/api/v1/ecosystem/detect/nonexistent-pkg-xyz-12345"
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "invalid_name",
        [
            "pkg.with.dots",
        ],
    )
    async def test_detect_invalid_name_returns_422(self, client, invalid_name):
        """GET /api/v1/ecosystem/detect/ with invalid name returns 422 or 404."""
        resp = await client.get(
            f"/api/v1/ecosystem/detect/{invalid_name}"
        )
        # Names could be rejected as 422 (validation) or if valid per PEP 508
        # but not found on PyPI, they return 404
        assert resp.status_code in (404, 422), (
            f"Expected 404 or 422 (validation) but got {resp.status_code}"
        )


class TestStatsEndpoint:
    """Behavioral contract: GET /api/v1/ecosystem/stats"""

    @pytest.mark.anyio
    async def test_stats_returns_correct_structure(self, client):
        """GET /api/v1/ecosystem/stats returns adoption rates and trending migrations."""
        resp = await client.get("/api/v1/ecosystem/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_packages_scanned" in data
        assert isinstance(data["total_packages_scanned"], int)
        assert "adoption_rates" in data
        rates = data["adoption_rates"]
        for key in ("pip_only", "uv_ready", "poetry_compatible", "pip_tools_compatible"):
            assert key in rates
            assert "count" in rates[key]
            assert "pct" in rates[key]
        assert "trending_migrations" in data
        assert isinstance(data["trending_migrations"], list)


class TestMigrationGuideEndpoint:
    """Behavioral contract: GET /api/v1/ecosystem/migration-guide/{name}"""

    @pytest.mark.anyio
    async def test_migration_guide_happy_path(self, client):
        """GET /api/v1/ecosystem/migration-guide/requests?from=pip&to=uv returns 200."""
        resp = await client.get(
            "/api/v1/ecosystem/migration-guide/requests?from=pip&to=uv"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "package" in data
        assert data["package"] == "requests"
        assert "from_manager" in data
        assert data["from_manager"] == "pip"
        assert "to_manager" in data
        assert data["to_manager"] == "uv"
        assert "guide_markdown" in data
        assert isinstance(data["guide_markdown"], str)
        assert "config_changes" in data
        assert isinstance(data["config_changes"], list)
        if data["config_changes"]:
            change = data["config_changes"][0]
            assert "file" in change
            assert "change" in change

    @pytest.mark.anyio
    async def test_migration_guide_unsupported_pair_returns_422(self, client):
        """Unsupported migration path returns 422 with detail message."""
        resp = await client.get(
            "/api/v1/ecosystem/migration-guide/requests?from=pip&to=npm"
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "detail" in data

    @pytest.mark.anyio
    async def test_migration_guide_missing_params_returns_422(self, client):
        """Missing from/to query params returns 422."""
        resp = await client.get(
            "/api/v1/ecosystem/migration-guide/requests"
        )
        assert resp.status_code == 422


class TestCompatibilityEndpoint:
    """Behavioral contract: GET /api/v1/ecosystem/compatibility"""

    @pytest.mark.anyio
    async def test_compatibility_returns_paginated_list(self, client):
        """GET /api/v1/ecosystem/compatibility returns packages, total, limit, offset."""
        resp = await client.get("/api/v1/ecosystem/compatibility?limit=50&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert "packages" in data
        assert isinstance(data["packages"], list)
        assert "total" in data
        assert isinstance(data["total"], int)
        assert "limit" in data
        assert data["limit"] == 50
        assert "offset" in data
        assert data["offset"] == 0

    @pytest.mark.anyio
    async def test_compatibility_defaults_limit_50(self, client):
        """Default limit is 50 when not specified."""
        resp = await client.get("/api/v1/ecosystem/compatibility")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 50
        assert data["offset"] == 0
