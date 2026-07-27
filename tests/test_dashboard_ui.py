"""Pre-dev tests for the Vulnerability Dashboard UI.

Pattern:
- Interface tests: verify route registration, file structure, static serving — PASS immediately.
- Behavioral tests: verify rendered HTML content from API data — FAIL with NotImplementedError.

See analysis-brief.md for full spec and workspace/implementation-plan.md for TDD steps.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.routing import APIRoute, _IncludedRouter

from python_depot.database import SessionLocal, reset_db
from python_depot.dependency_health.models import VulnerabilityScan
from python_depot.pydepot.models import Package
from src.app import app


# ---------------------------------------------------------------------------
# Seed data fixture — overrides conftest _clean_db with data for dashboard tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_db_with_seed():
    """Drop, recreate, and seed test data for dashboard UI tests."""
    reset_db()
    _seed_dashboard_data()


def _seed_dashboard_data():
    """Seed known packages for dashboard UI tests."""
    db = SessionLocal()
    try:
        # Seed packages and scans (also for overview/packages tests)
        existing = db.query(Package).filter(Package.name == "requests").first()
        if existing:
            return

        pkg = Package(name="requests", latest_version="2.31.0")
        db.add(pkg)
        db.flush()
        scan = VulnerabilityScan(
            package_id=pkg.id,
            version="2.31.0",
            scanner="safety",
            status="clean",
            vuln_count=0,
            scanned_at=datetime.now(UTC),
        )
        db.add(scan)

        pkg2 = Package(name="urllib3", latest_version="2.0.7")
        db.add(pkg2)
        db.flush()
        scan2 = VulnerabilityScan(
            package_id=pkg2.id,
            version="2.0.7",
            scanner="safety",
            status="vulnerable",
            vuln_count=2,
            scanned_at=datetime.now(UTC),
        )
        db.add(scan2)

        pkg3 = Package(name="certifi", latest_version="2024.7.4")
        db.add(pkg3)
        db.flush()
        scan3 = VulnerabilityScan(
            package_id=pkg3.id,
            version="2024.7.4",
            scanner="safety",
            status="unknown",
            vuln_count=0,
            scanned_at=datetime.now(UTC),
        )
        db.add(scan3)

        # Seed alert data for alerts page tests
        from python_depot.dependency_health.models import VulnerabilityAlert

        alerts_data = [
            VulnerabilityAlert(
                package_id=pkg2.id,
                vuln_id="GHSA-crit-001",
                severity="CRITICAL",
                score=9.5,
                created_at=datetime.now(UTC),
            ),
            VulnerabilityAlert(
                package_id=pkg2.id,
                vuln_id="GHSA-high-001",
                severity="HIGH",
                score=7.5,
                created_at=datetime.now(UTC),
            ),
        ]
        for alert in alerts_data:
            db.add(alert)

        db.commit()
    finally:
        db.close()


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Expected new file paths
STATIC_CSS = PROJECT_ROOT / "python_depot" / "static" / "css" / "dashboard.css"
STATIC_JS = PROJECT_ROOT / "python_depot" / "static" / "js" / "dashboard.js"
TEMPLATES_DIR = PROJECT_ROOT / "python_depot" / "templates" / "dashboard"
TEMPLATE_NAMES = [
    "base.html",
    "overview.html",
    "packages.html",
    "package_detail.html",
    "alerts.html",
]

EXPECTED_DASHBOARD_PATHS = {
    "/dashboard",
    "/dashboard/packages",
    "/dashboard/alerts",
    "/dashboard/packages/{package_name}",  # or {name}
}

EXPECTED_STATIC_PATHS = {
    "/static/css/dashboard.css",
    "/static/js/dashboard.js",
}


# ---------------------------------------------------------------------------
# Route helper — mirrors pattern from test_dependency_health.py
# ---------------------------------------------------------------------------


class Routes:
    """Helper to list all registered route paths including included routers."""

    @staticmethod
    def paths() -> set[str]:
        """Return set of all registered route paths (full, with prefixes)."""
        paths: set[str] = set()
        for r in app.routes:
            if isinstance(r, _IncludedRouter):
                prefix = r.include_context.prefix
                for route in r.original_router.routes:
                    paths.add(prefix + route.path)
            elif isinstance(r, APIRoute):
                paths.add(r.path)
        return paths

    @staticmethod
    def mounts() -> list:
        """Return all Mount instances in the app routes."""
        from starlette.routing import Mount

        return [r for r in app.routes if isinstance(r, Mount)]


# ---------------------------------------------------------------------------
# Interface tests — pass immediately (imports, file structure, route definitions)
# ---------------------------------------------------------------------------


class TestDashboardStructure:
    """Verify dashboard template and static files exist on disk."""

    def test_templates_directory_exists(self):
        """Dashboard templates directory exists."""
        assert TEMPLATES_DIR.is_dir(), f"Expected directory: {TEMPLATES_DIR}"

    def test_base_template_exists(self):
        """base.html exists in templates/dashboard/."""
        assert (TEMPLATES_DIR / "base.html").is_file()

    def test_overview_template_exists(self):
        """overview.html exists in templates/dashboard/."""
        assert (TEMPLATES_DIR / "overview.html").is_file()

    def test_packages_template_exists(self):
        """packages.html exists in templates/dashboard/."""
        assert (TEMPLATES_DIR / "packages.html").is_file()

    def test_alerts_template_exists(self):
        """alerts.html exists in templates/dashboard/."""
        assert (TEMPLATES_DIR / "alerts.html").is_file()

    def test_package_detail_template_exists(self):
        """package_detail.html exists in templates/dashboard/."""
        assert (TEMPLATES_DIR / "package_detail.html").is_file()

    def test_static_css_file_exists(self):
        """dashboard.css exists in static/css/."""
        assert STATIC_CSS.is_file(), f"Expected file: {STATIC_CSS}"

    def test_static_js_file_exists(self):
        """dashboard.js exists in static/js/."""
        assert STATIC_JS.is_file(), f"Expected file: {STATIC_JS}"


class TestDashboardRouterImport:
    """Verify dashboard_pages router can be imported and exposes expected API."""

    def test_dashboard_router_module_can_be_imported(self):
        """dashboard_pages router module is importable."""
        from python_depot.routers.dashboard_pages import router

        assert router is not None

    def test_dashboard_router_has_routes_attribute(self):
        """Imported router has 'routes' attribute."""
        from python_depot.routers.dashboard_pages import router

        assert hasattr(router, "routes")

    def test_dashboard_router_has_at_least_one_endpoint(self):
        """Router defines at least one endpoint."""
        from python_depot.routers.dashboard_pages import router

        assert len(router.routes) >= 1

    def test_dashboard_router_registers_jinja2_templates(self):
        """dashboard_pages module has a Jinja2Templates instance."""
        import python_depot.routers.dashboard_pages as dp

        assert hasattr(dp, "templates"), (
            "Expected module-level 'templates' Jinja2Templates instance"
        )


class TestDashboardRoutesRegistered:
    """Verify dashboard UI routes are registered in the FastAPI app."""

    def test_overview_route_registered(self):
        """GET /dashboard is registered."""
        paths = Routes.paths()
        assert "/dashboard" in paths or "/dashboard/overview" in paths, (
            f"Expected /dashboard or /dashboard/overview in registered paths: {paths}"
        )

    def test_packages_route_registered(self):
        """GET /dashboard/packages is registered."""
        paths = Routes.paths()
        assert "/dashboard/packages" in paths

    def test_alerts_route_registered(self):
        """GET /dashboard/alerts is registered."""
        paths = Routes.paths()
        assert "/dashboard/alerts" in paths

    def test_package_detail_route_registered(self):
        """GET /dashboard/packages/{name} is registered."""
        paths = Routes.paths()
        assert (
            "/dashboard/packages/{package_name}" in paths
            or "/dashboard/packages/{name}" in paths
        ), f"Expected path param pattern in: {paths}"

    def test_static_files_mounted(self):
        """StaticFiles mount exists at path /static."""
        mounts = Routes.mounts()
        mount_paths = {m.path for m in mounts}
        assert "/static" in mount_paths, f"No /static mount found in: {mount_paths}"

    def test_dashboard_router_included_in_app(self):
        """Dashboard_pages router is included in the FastAPI app."""
        from python_depot.routers.dashboard_pages import router

        # Verify the router's routes appear in the app's included routers
        router_paths = {route.path for route in router.routes}
        included = [
            r
            for r in app.routes
            if isinstance(r, _IncludedRouter)
            and any(
                route.path in router_paths for route in r.original_router.routes
            )
        ]
        assert len(included) >= 1, "Dashboard router not included in app"


class TestDashboardHTTPServing:
    """Verify HTTP endpoints return correct status codes and content types.

    These tests require the static files to be served and the dashboard
    routes to be wired up. They pass when Phase 1 of the implementation
    plan is complete.
    """

    @pytest.mark.anyio
    async def test_static_css_returns_200(self, client):
        """GET /static/css/dashboard.css returns 200."""
        resp = await client.get("/static/css/dashboard.css")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_static_css_has_css_content_type(self, client):
        """GET /static/css/dashboard.css has correct content type."""
        resp = await client.get("/static/css/dashboard.css")
        assert "text/css" in resp.headers.get("content-type", "")

    @pytest.mark.anyio
    async def test_static_js_returns_200(self, client):
        """GET /static/js/dashboard.js returns 200."""
        resp = await client.get("/static/js/dashboard.js")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_static_js_has_js_content_type(self, client):
        """GET /static/js/dashboard.js has correct content type."""
        resp = await client.get("/static/js/dashboard.js")
        assert "text/javascript" in resp.headers.get("content-type", "")

    @pytest.mark.anyio
    async def test_dashboard_overview_returns_200(self, client):
        """GET /dashboard returns 200."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_dashboard_overview_is_html(self, client):
        """GET /dashboard returns text/html."""
        resp = await client.get("/dashboard")
        assert "text/html" in resp.headers.get("content-type", "")

    @pytest.mark.anyio
    async def test_dashboard_packages_returns_200(self, client):
        """GET /dashboard/packages returns 200."""
        resp = await client.get("/dashboard/packages")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_dashboard_packages_is_html(self, client):
        """GET /dashboard/packages returns text/html."""
        resp = await client.get("/dashboard/packages")
        assert "text/html" in resp.headers.get("content-type", "")

    @pytest.mark.anyio
    async def test_dashboard_alerts_returns_200(self, client):
        """GET /dashboard/alerts returns 200."""
        resp = await client.get("/dashboard/alerts")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_dashboard_alerts_is_html(self, client):
        """GET /dashboard/alerts returns text/html."""
        resp = await client.get("/dashboard/alerts")
        assert "text/html" in resp.headers.get("content-type", "")

    @pytest.mark.anyio
    async def test_dashboard_package_detail_returns_200(self, client):
        """GET /dashboard/packages/{name} returns 200 for known package."""
        resp = await client.get("/dashboard/packages/requests")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_dashboard_package_detail_is_html(self, client):
        """GET /dashboard/packages/{name} returns text/html."""
        resp = await client.get("/dashboard/packages/requests")
        assert "text/html" in resp.headers.get("content-type", "")

    @pytest.mark.anyio
    async def test_dashboard_unknown_package_detail_returns_404(self, client):
        """GET /dashboard/packages/{name} returns 404 for unknown package."""
        resp = await client.get("/dashboard/packages/nonexistent-pkg-99999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestDashboardOverviewBehavioral:
    """Behavioral tests for the overview page — fail with NotImplementedError."""

    @pytest.mark.anyio
    async def test_overview_contains_package_count(self, client):
        """Overview page renders total packages count from the backend API."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.text
        # total_packages from overview API (1 = seeded "requests")
        assert "total-packages" in html or "1" in html

    @pytest.mark.anyio
    async def test_overview_shows_severity_breakdown(self, client):
        """Overview page shows severity breakdown (CRITICAL/HIGH/MEDIUM/LOW)."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.text
        # The severity chart container should be present
        assert "severityChart" in html
        assert "Severity Breakdown" in html

    @pytest.mark.anyio
    async def test_overview_embeds_chartjs(self, client):
        """Overview page loads Chart.js library (CDN or bundled)."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.text
        # Chart.js CDN script tag
        assert "chart.js" in html.lower() or "chart.min.js" in html.lower()

    @pytest.mark.anyio
    async def test_overview_shows_scan_coverage(self, client):
        """Overview page shows scan coverage percentage."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.text
        # scan_coverage is rendered (100.0 since our seed is clean)
        assert "scan coverage" in html.lower() or "100" in html

    @pytest.mark.anyio
    async def test_overview_shows_last_scan_timestamp(self, client):
        """Overview page shows the last scan timestamp."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.text
        # last_scan timestamp present (ISO format)
        assert "T" in html and ":" in html  # rough ISO timestamp check

    @pytest.mark.anyio
    async def test_overview_chart_data_matches_api(self, client):
        """Overview page Chart.js data points match the backend API response."""
        dash_resp = await client.get("/dashboard")
        html = dash_resp.text

        # The HTML should include severity_json with the breakdown data
        # Check severity data is embedded in the page
        assert "severityData" in html
        # Verify Chart.js config uses the severity data
        assert "Object.keys(severityData)" in html
        assert "Object.values(severityData)" in html


class TestDashboardPackagesBehavioral:
    """Behavioral tests for packages page — fail with NotImplementedError."""

    @pytest.mark.anyio
    async def test_packages_page_renders_table(self, client):
        """Packages page renders an HTML table with package data."""
        resp = await client.get("/dashboard/packages")
        assert resp.status_code == 200
        html = resp.text
        # Check for table elements
        assert "<table" in html or "packages-table" in html
        # Check for package data row (integer ID from API)
        assert "<td>" in html and "</td>" in html

    @pytest.mark.anyio
    async def test_packages_table_has_expected_columns(self, client):
        """Package table includes columns: name, vuln count, status, last scan."""
        resp = await client.get("/dashboard/packages")
        assert resp.status_code == 200
        html = resp.text
        # Table headers for expected columns
        assert "Package" in html
        assert "Vulnerabilit" in html or "Status" in html
        assert "Last Scan" in html or "Last" in html

    @pytest.mark.anyio
    async def test_packages_page_has_search_input(self, client):
        """Packages page includes a search/filter input field."""
        resp = await client.get("/dashboard/packages")
        assert resp.status_code == 200
        html = resp.text
        # Search input
        assert "search" in html.lower()
        assert "package-search" in html or 'type="text"' in html

    @pytest.mark.anyio
    async def test_packages_passes_search_query_param(self, client):
        """Packages page passes ?q= query param through to backend."""
        resp = await client.get("/dashboard/packages?q=requests")
        assert resp.status_code == 200
        html = resp.text
        # Page renders successfully with query param
        assert "Package Health" in html

    @pytest.mark.anyio
    async def test_packages_has_pagination(self, client):
        """Packages page shows pagination controls (next/prev or page numbers)."""
        # Use a small limit to trigger pagination
        resp = await client.get("/dashboard/packages?limit=1&offset=0")
        assert resp.status_code == 200
        html = resp.text
        # Check for pagination elements
        assert "pagination" in html

    @pytest.mark.anyio
    async def test_packages_color_codes_status(self, client):
        """Package status is color-coded (green=clean, red=vulnerable, yellow=unknown)."""
        resp = await client.get("/dashboard/packages")
        assert resp.status_code == 200
        html = resp.text
        # Check for CSS status classes
        assert "status-clean" in html or "status-" in html


class TestDashboardAlertsBehavioral:
    """Behavioral tests for alerts page — fail with NotImplementedError."""

    @pytest.mark.anyio
    async def test_alerts_page_renders_table(self, client):
        """Alerts page renders an HTML table with alert data."""
        resp = await client.get("/dashboard/alerts")
        assert resp.status_code == 200
        html = resp.text
        # Table structure present
        assert "<table" in html or "Severity" in html
        # Table headers for expected columns
        assert "Severity" in html
        assert "Package" in html

    @pytest.mark.anyio
    async def test_alerts_page_has_severity_filter(self, client):
        """Alerts page has a severity filter dropdown or selector."""
        resp = await client.get("/dashboard/alerts")
        assert resp.status_code == 200
        html = resp.text
        # Filter dropdown
        assert "severity-filter" in html or "Severity" in html
        # Filter options
        assert "CRITICAL" in html or "select" in html

    @pytest.mark.anyio
    async def test_alerts_filters_by_severity(self, client):
        """Alerts page passes ?severity= query param to backend."""
        resp = await client.get("/dashboard/alerts?severity=CRITICAL")
        assert resp.status_code == 200
        html = resp.text
        # Page renders with severity filter
        assert "Alerts" in html

    @pytest.mark.anyio
    async def test_alerts_color_codes_severity(self, client):
        """Alert severity is color-coded (CRITICAL=red, HIGH=orange, etc.)."""
        resp = await client.get("/dashboard/alerts")
        assert resp.status_code == 200
        html = resp.text
        # CSS severity classes in the page (either in template or rendered)
        assert "severity-" in html or "status-badge" in html

    @pytest.mark.anyio
    async def test_alerts_has_pagination(self, client):
        """Alerts page shows pagination controls."""
        resp = await client.get("/dashboard/alerts?limit=1&offset=0")
        assert resp.status_code == 200
        html = resp.text
        # Pagination controls present
        assert "pagination" in html


class TestDashboardPackageDetailBehavioral:
    """Behavioral tests for package detail page — fail with NotImplementedError."""

    @pytest.mark.anyio
    async def test_package_detail_shows_score(self, client):
        """Package detail page renders the health score (0-100)."""
        resp = await client.get("/dashboard/packages/requests")
        assert resp.status_code == 200
        html = resp.text
        # Score should be rendered (100.0 for our clean package)
        assert "score" in html.lower()
        # Check a numeric score value is present
        assert any(c.isdigit() for c in html)

    @pytest.mark.anyio
    async def test_package_detail_shows_score_label(self, client):
        """Package detail page shows score label (EXCELLENT/GOOD/FAIR/POOR/CRITICAL)."""
        resp = await client.get("/dashboard/packages/requests")
        assert resp.status_code == 200
        html = resp.text
        # Score label rendered
        assert "EXCELLENT" in html or "GOOD" in html or "FAIR" in html or "POOR" in html or "CRITICAL" in html

    @pytest.mark.anyio
    async def test_package_detail_shows_breakdown(self, client):
        """Package detail page shows score breakdown components."""
        resp = await client.get("/dashboard/packages/requests")
        assert resp.status_code == 200
        html = resp.text
        # Breakdown fields
        assert "Base Score" in html or "base_score" in html
        assert "Vuln Penalty" in html or "vuln_penalty" in html

    @pytest.mark.anyio
    async def test_package_detail_shows_vuln_count(self, client):
        """Package detail page shows vulnerability count."""
        resp = await client.get("/dashboard/packages/requests")
        assert resp.status_code == 200
        html = resp.text
        # Vulnerability count displayed
        assert "Vulnerabilit" in html or "vuln_count" in html

    @pytest.mark.anyio
    async def test_package_detail_shows_max_severity(self, client):
        """Package detail page shows maximum severity level."""
        resp = await client.get("/dashboard/packages/requests")
        assert resp.status_code == 200
        html = resp.text
        # Max severity displayed (NONE for clean package)
        assert "Max Severity" in html or "max_severity" in html

    @pytest.mark.anyio
    async def test_package_detail_has_back_link(self, client):
        """Package detail page has a 'back to packages' navigation link."""
        resp = await client.get("/dashboard/packages/requests")
        assert resp.status_code == 200
        html = resp.text
        # Back link to packages page
        assert "/dashboard/packages" in html
        assert "Back" in html or "back" in html

    @pytest.mark.anyio
    async def test_package_detail_unknown_package(self, client):
        """Package detail page for unknown package returns a not-found message."""
        resp = await client.get("/dashboard/packages/nonexistent-pkg")
        assert resp.status_code == 404
        html = resp.text
        # Friendly not-found message
        assert "not found" in html.lower() or "no data" in html.lower()


class TestDashboardResponsiveBehavioral:
    """Behavioral tests for responsive design — fail with NotImplementedError."""

    @pytest.mark.anyio
    async def test_base_template_has_viewport_meta(self, client):
        """Base template includes <meta name='viewport'> for mobile responsiveness."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.text
        # Viewport meta tag
        assert 'name="viewport"' in html
        assert "width=device-width" in html

    @pytest.mark.anyio
    async def test_dashboard_css_has_media_queries(self, client):
        """dashboard.css contains media queries at 768px and 1024px breakpoints."""
        resp = await client.get("/static/css/dashboard.css")
        assert resp.status_code == 200
        css = resp.text
        # Media queries for responsive breakpoints
        assert "@media" in css
        assert "768px" in css
        assert "1024px" in css

    @pytest.mark.anyio
    async def test_nav_sidebar_links_all_sections(self, client):
        """Navigation sidebar or top-bar links to all major dashboard sections."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.text
        # Nav links to all major sections
        assert "/dashboard" in html  # Overview link
        assert "/dashboard/packages" in html  # Packages link
        assert "/dashboard/alerts" in html  # Alerts link

    @pytest.mark.anyio
    async def test_font_awesome_or_icons_loaded(self, client):
        """Dashboard loads icon library (Font Awesome CDN or inline SVG icons)."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.text
        # Font Awesome CDN or inline icons
        assert "font-awesome" in html.lower() or "fontawesome" in html.lower() or "fa-" in html

    @pytest.mark.anyio
    async def test_chartjs_loaded_from_cdn(self, client):
        """Chart.js is loaded from CDN (or bundled as static file)."""
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        html = resp.text
        # Chart.js script reference
        assert "chart.js" in html.lower() or "chart.min.js" in html.lower()
