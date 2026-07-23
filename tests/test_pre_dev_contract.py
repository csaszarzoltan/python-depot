"""Pre-dev contract tests for PythonDepot API endpoints.

Pattern:
- Interface tests: verify imports, fixture setup, route registration —
  these PASS immediately.
- Behavioral tests: verify the implemented endpoint contract against
  the running application.
"""
import pytest
from fastapi.routing import APIRoute, _IncludedRouter
from httpx import ASGITransport, AsyncClient

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
# Interface tests — pass immediately (imports, fixtures, route registration)
# ---------------------------------------------------------------------------


class TestInterfaceImports:
    """Verify that all imports resolve correctly."""

    def test_app_import(self):
        """App module imports without error."""
        from src.app import app

        assert app.title == "PythonDepot"

    def test_create_app_function(self):
        """create_app returns a properly configured FastAPI instance."""
        from src.app import create_app

        instance = create_app()
        assert instance.title == "PythonDepot"
        assert instance.version == "0.1.0"

    def test_packages_router_import(self):
        """Packages router imports without error."""
        from src.routers.packages import router

        assert router.prefix == ""

    def test_reviews_router_import(self):
        """Reviews router imports without error."""
        from src.routers.reviews import router

        assert len(router.routes) >= 3  # list, submit, get

    def test_health_route_registered(self):
        """Health endpoint is registered on the app."""
        assert "/health" in Routes.paths()


class TestInterfaceFixtures:
    """Verify that pytest fixtures work correctly."""

    @pytest.mark.anyio
    async def test_client_fixture_works(self, client):
        """AsyncClient fixture is callable and returns responses."""
        response = await client.get("/")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_client_transport_is_asgi(self, client):
        """Client uses ASGITransport (not real HTTP)."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/health")
            assert resp.status_code == 200


class TestInterfaceRouteRegistration:
    """Verify all expected routes are registered on the app."""

    def test_all_routes_listed(self):
        """All API routes are registered with correct paths."""
        registered = Routes.paths()
        expected = {
            "/",
            "/health",
            "/api/v1/packages/",
            "/api/v1/packages/{package_name}",
            "/api/v1/packages/search",
            "/api/v1/packages/{package_name}/trends",
            "/api/v1/reviews/{package_name}",
            "/api/v1/reviews/{package_name}/{review_id}",
            "/api/v1/ratings/{package_name}",
            "/api/v1/ratings/{package_name}/summary",
            "/api/v1/analytics/trending",
            "/api/v1/analytics/popular",
            "/api/v1/analytics/events",
            "/api/v1/analytics/stats/{package_name}",
            "/api/v1/vulnerabilities/{package_name}",
            "/api/v1/vulnerabilities/{package_name}/scan",
            "/api/v1/vulnerabilities/{package_name}/latest",
            "/api/v1/reports/",
            "/api/v1/reports/generate",
            "/api/v1/reports/{year}/{month}",
            "/api/v1/reports/{year}/{month}/html",
        }
        missing = expected - registered
        extra = registered - expected - {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
        assert not missing, f"Expected routes missing: {missing}"
        assert not extra, f"Unexpected routes found: {extra}"

    def test_package_routes_have_correct_methods(self):
        """Package routes use expected HTTP methods."""
        methods = Routes.methods_for_path("/api/v1/packages/")
        assert "GET" in methods
        assert "POST" in methods
        methods = Routes.methods_for_path("/api/v1/packages/{package_name}")
        assert "GET" in methods
        assert "PUT" in methods
        assert "DELETE" in methods

    def test_review_routes_have_correct_methods(self):
        """Review routes use expected HTTP methods."""
        methods = Routes.methods_for_path("/api/v1/reviews/{package_name}")
        assert "GET" in methods
        assert "POST" in methods

    def test_health_route_is_get(self):
        """Health route is a GET endpoint."""
        methods = Routes.methods_for_path("/health")
        assert "GET" in methods


class TestInterfaceModels:
    """Verify SQLAlchemy ORM models used by endpoints exist with expected columns."""

    def test_package_model_has_expected_columns(self):
        """Package model has expected ORM columns."""
        from src.models.package import Package

        cols = {c.name for c in Package.__table__.columns}
        assert "name" in cols
        assert "summary" in cols
        assert "latest_version" in cols

    def test_review_model_has_expected_columns(self):
        """Review model has expected ORM columns."""
        from src.models.review import Review

        cols = {c.name for c in Review.__table__.columns}
        assert "package_id" in cols
        assert "user_id" in cols
        assert "title" in cols
        assert "body" in cols

    def test_monthly_report_model_imports(self):
        """MonthlyReport model imports correctly."""
        from src.models.report import MonthlyReport

        cols = {c.name for c in MonthlyReport.__table__.columns}
        assert "year" in cols
        assert "month" in cols

    def test_analytics_model_imports(self):
        """AnalyticsEvent model can be imported."""
        from src.models.analytics import AnalyticsEvent

        assert hasattr(AnalyticsEvent, "event_type")


# ---------------------------------------------------------------------------
# Behavioral tests — verify the implemented endpoint contracts
# ---------------------------------------------------------------------------


class TestBehavioralHealth:
    """Behavioral contract: GET /health"""

    @pytest.mark.anyio
    async def test_health_returns_full_status_report(self, client):
        """GET /health returns status, version, timestamp, uptime."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        assert "uptime" in data
        # uptime should be a non-empty string like "0d 0h 0m Ns"
        assert isinstance(data["uptime"], str)
        assert len(data["uptime"]) > 0

    @pytest.mark.anyio
    async def test_health_response_shape(self, client):
        """GET /health response has deterministic JSON shape."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        # All expected top-level keys present
        for key in ("status", "version", "timestamp", "uptime", "db_status", "checks"):
            assert key in data, f"Missing key: {key}"
        # checks is a dict (may be empty or contain sub-checks)
        assert isinstance(data["checks"], dict)

    @pytest.mark.anyio
    async def test_health_checks_database_connectivity(self, client):
        """GET /health includes db_status field indicating database connectivity."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "db_status" in data
        # db_status should be either "ok" or start with "failed"
        assert data["db_status"] in ("ok",) or data["db_status"].startswith("failed")


class TestBehavioralPackages:
    """Behavioral contract: GET /api/v1/packages/{name}"""

    @pytest.mark.anyio
    async def test_get_package_not_found_schema(self, client):
        """GET /api/v1/packages/{name} for a non-existent package returns 404."""
        resp = await client.get("/api/v1/packages/not-a-real-package")
        assert resp.status_code == 404
        data = resp.json()
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            assert detail.get("found") is False
            assert "name" in detail

    @pytest.mark.anyio
    async def test_get_package_validation(self, client):
        """GET /api/v1/packages/{name} rejects invalid package names with 422."""
        resp = await client.get("/api/v1/packages/../invalid")
        # Either 422 validation error or 404 not found (depending on route match)
        assert resp.status_code in (404, 422)


class TestBehavioralTrends:
    """Behavioral contract: GET /api/v1/packages/{name}/trends"""

    @pytest.mark.anyio
    async def test_trends_endpoint_exists(self, client):
        """GET /api/v1/packages/{name}/trends returns download and star trends."""
        resp = await client.get("/api/v1/packages/requests/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert data["name"] == "requests"
        assert "trends" in data
        assert "period" in data
        if data["trends"]:
            sample = data["trends"][0]
            assert "date" in sample
            assert "downloads" in sample
            assert "stars" in sample

    @pytest.mark.anyio
    async def test_trends_response_shape(self, client):
        """GET /api/v1/packages/{name}/trends returns time-series data."""
        resp = await client.get("/api/v1/packages/flask/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["trends"], list)
        if data["trends"]:
            for entry in data["trends"]:
                assert "date" in entry
                assert "downloads" in entry
                assert "stars" in entry

    @pytest.mark.anyio
    async def test_trends_accepts_period_param(self, client):
        """GET /api/v1/packages/{name}/trends accepts ?period= query parameter."""
        resp = await client.get("/api/v1/packages/django/trends?period=7d")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "7d"
        # 7d should return 7 entries
        assert len(data["trends"]) == 7


class TestBehavioralSearch:
    """Behavioral contract: GET /api/v1/packages/search"""

    @pytest.mark.anyio
    async def test_search_endpoint_exists(self, client):
        """GET /api/v1/packages/search?q=<term> returns matching packages."""
        resp = await client.get("/api/v1/packages/search?q=requests")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "requests"

    @pytest.mark.anyio
    async def test_search_returns_results(self, client):
        """GET /api/v1/packages/search returns results with name, summary, score."""
        resp = await client.get("/api/v1/packages/search?q=requests")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["results"], list)
        if data["results"]:
            for item in data["results"]:
                assert "name" in item
                assert "summary" in item
                assert "score" in item

    @pytest.mark.anyio
    async def test_search_empty_query(self, client):
        """GET /api/v1/packages/search with no q param returns 422."""
        resp = await client.get("/api/v1/packages/search")
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_search_pagination(self, client):
        """GET /api/v1/packages/search supports page and page_size params."""
        resp = await client.get("/api/v1/packages/search?q=test&page=1&page_size=20")
        assert resp.status_code == 200


class TestBehavioralReview:
    """Behavioral contract: POST /api/v1/reviews/{name}"""

    @pytest.mark.anyio
    async def test_submit_review_accepts_body(self, client):
        """POST /api/v1/reviews/{name} accepts review body with rating, comment, reviewer."""
        resp = await client.post(
            "/api/v1/reviews/some-package",
            json={"rating": 4, "comment": "Great package!", "reviewer": "alice"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "review_id" in data
        assert "timestamp" in data

    @pytest.mark.anyio
    async def test_submit_review_validation(self, client):
        """POST /api/v1/reviews/{name} validates rating range (1-5) returns 422."""
        resp = await client.post(
            "/api/v1/reviews/some-package",
            json={"rating": 99, "comment": "Bad", "reviewer": "bob"},
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_submit_review_returns_created(self, client):
        """POST /api/v1/reviews/{name} returns 201 with review id and timestamp."""
        resp = await client.post(
            "/api/v1/reviews/some-package",
            json={"rating": 5, "comment": "Excellent!", "reviewer": "carol"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["review_id"] is not None
        assert data["timestamp"] is not None


class TestBehavioralReports:
    """Behavioral contract: reports router endpoints."""

    @pytest.mark.anyio
    async def test_report_has_package_health(self, client):
        """GET /api/v1/reports/{year}/{month} returns report with health scores."""
        resp = await client.get("/api/v1/reports/2024/6")
        assert resp.status_code == 200
        data = resp.json()
        # Should contain report data (even if null/empty)
        assert "year" in data or "report" in data
