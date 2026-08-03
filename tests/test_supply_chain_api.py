"""Pre-dev TDD tests for the supply-chain REST API router.

Pattern (repo convention):
- Interface tests: verify the router module, route registration, HTTP
  methods, handler signatures and type hints — PASS immediately.
- Behavioral tests: hit the endpoints through a minimal FastAPI app that
  includes the stub router. Because httpx ASGITransport is created with
  ``raise_app_exceptions=True``, the handler's NotImplementedError
  propagates out of the request — FAIL with NotImplementedError until the
  developer implements ``python_depot/routers/supply_chain.py``.

Endpoints under test:
- GET /api/v1/supply-chain/check?package=NAME -> {package, score, reasons}
- GET /api/v1/supply-chain/scan            -> {verdicts, scanned_at}
"""

from __future__ import annotations

import inspect
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from python_depot.routers.supply_chain import (
    check_supply_chain,
    router,
    scan_supply_chain,
)


def _ret_annotation(func) -> str:
    """Return annotation as string (works with ``from __future__ import annotations``)."""
    return inspect.signature(func).return_annotation


@pytest.fixture
def sc_app() -> FastAPI:
    """Minimal FastAPI app wiring the supply-chain router (prefix "")."""
    application = FastAPI()
    application.include_router(router, prefix="")
    return application


@pytest.fixture
async def sc_client(sc_app):
    """Async HTTP client against the supply-chain app.

    raise_app_exceptions=True propagates the stub handler's
    NotImplementedError out of the request so behavioral tests fail
    red with NotImplementedError until the handler is implemented.
    """
    transport = ASGITransport(app=sc_app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def _no_pypi_network(monkeypatch):
    """Never hit the real PyPI network from API tests.

    The router feeds real package metadata via ``fetch_package_info``;
    in tests that would be slow and non-deterministic, so it is
    replaced with an 'unknown data' stub. Tests that exercise the
    real-metadata path override the stub themselves.
    """

    async def _unknown(_name):
        return None

    monkeypatch.setattr(
        "python_depot.routers.supply_chain.fetch_package_info", _unknown
    )


# ---------------------------------------------------------------------------
# Interface tests — pass immediately
# ---------------------------------------------------------------------------


class TestSupplyChainRouterInterface:
    """Verify the supply-chain router module contract."""

    def test_router_import(self):
        """Router module imports and exposes an APIRouter instance."""
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_two_endpoints(self):
        """Router defines check and scan endpoints."""
        assert len(router.routes) == 2

    def test_check_route_registered(self):
        """GET /api/v1/supply-chain/check is registered."""
        paths = {r.path for r in router.routes}
        assert "/api/v1/supply-chain/check" in paths

    def test_scan_route_registered(self):
        """GET /api/v1/supply-chain/scan is registered."""
        paths = {r.path for r in router.routes}
        assert "/api/v1/supply-chain/scan" in paths

    def test_check_route_is_get(self):
        """Check route uses the GET method."""
        route = next(r for r in router.routes if r.path == "/api/v1/supply-chain/check")
        assert "GET" in route.methods

    def test_scan_route_is_get(self):
        """Scan route uses the GET method."""
        route = next(r for r in router.routes if r.path == "/api/v1/supply-chain/scan")
        assert "GET" in route.methods

    def test_handlers_are_async(self):
        """Both handlers are coroutine functions."""
        assert inspect.iscoroutinefunction(check_supply_chain)
        assert inspect.iscoroutinefunction(scan_supply_chain)

    def test_check_handler_signature(self):
        """check handler accepts package (query) and db (dependency)."""
        sig = inspect.signature(check_supply_chain)
        params = sig.parameters
        assert "package" in params
        assert "db" in params
        _ret_annotation(check_supply_chain)

    def test_scan_handler_signature(self):
        """scan handler accepts db (dependency)."""
        sig = inspect.signature(scan_supply_chain)
        assert "db" in sig.parameters

    def test_handler_return_annotations(self):
        """Handlers are annotated to return dict[str, Any]."""
        ret_check = _ret_annotation(check_supply_chain)
        ret_scan = _ret_annotation(scan_supply_chain)
        assert ret_check == "dict[str, Any]" or ret_check is dict
        assert ret_scan == "dict[str, Any]" or ret_scan is dict

    def test_router_wires_into_app(self):
        """Router can be included into a FastAPI app with prefix ''."""
        from fastapi.routing import APIRoute, _IncludedRouter

        application = FastAPI()
        application.include_router(router, prefix="")
        paths: set[str] = set()
        for r in application.routes:
            if isinstance(r, _IncludedRouter):
                for route in r.original_router.routes:
                    paths.add(r.include_context.prefix + route.path)
            elif isinstance(r, APIRoute):
                paths.add(r.path)
        assert "/api/v1/supply-chain/check" in paths
        assert "/api/v1/supply-chain/scan" in paths

    @pytest.mark.anyio
    async def test_check_missing_package_returns_422(self, sc_client):
        """Missing package query param is rejected with 422 by FastAPI.

        Validation runs before the handler body, so this passes even
        while the handler is still a NotImplementedError stub.
        """
        resp = await sc_client.get("/api/v1/supply-chain/check")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestSupplyChainApiBehavioral:
    """REST API behavior for the supply-chain endpoints."""

    @pytest.mark.anyio
    async def test_check_returns_verdict_json(self, sc_client):
        """GET check?package=NAME returns JSON with integer score 0-100 and reasons."""
        resp = await sc_client.get("/api/v1/supply-chain/check?package=requests")
        assert resp.status_code == 200
        data = resp.json()
        assert data["package"] == "requests"
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 100
        assert isinstance(data["reasons"], list)

    @pytest.mark.anyio
    async def test_check_suspicious_package_has_reasons(self, sc_client):
        """A non-trivial score comes with at least one detection reason."""
        resp = await sc_client.get("/api/v1/supply-chain/check?package=requets")
        assert resp.status_code == 200
        data = resp.json()
        if data["score"] > 0:
            assert len(data["reasons"]) > 0

    @pytest.mark.anyio
    async def test_check_response_shape(self, sc_client):
        """Check response contains exactly the expected keys."""
        resp = await sc_client.get("/api/v1/supply-chain/check?package=numpy")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"package", "score", "reasons"}

    @pytest.mark.anyio
    async def test_scan_returns_per_package_verdicts(self, sc_client):
        """GET scan returns per-package verdicts with the same shape."""
        resp = await sc_client.get("/api/v1/supply-chain/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert "verdicts" in data
        assert isinstance(data["verdicts"], list)
        for verdict in data["verdicts"]:
            assert "package" in verdict
            assert isinstance(verdict["score"], int)
            assert 0 <= verdict["score"] <= 100
            assert "reasons" in verdict
            assert isinstance(verdict["reasons"], list)

    @pytest.mark.anyio
    async def test_scan_returns_timestamp(self, sc_client):
        """Scan response includes a scanned_at timestamp."""
        resp = await sc_client.get("/api/v1/supply-chain/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert "scanned_at" in data
        assert isinstance(data["scanned_at"], str)
        assert len(data["scanned_at"]) > 0


# ---------------------------------------------------------------------------
# Regression tests for review findings F1-F6 (t_36a69304)
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Query-param validation on the check endpoint (F1)."""

    @pytest.mark.anyio
    async def test_empty_package_returns_422(self, sc_client):
        """Empty package name is rejected (min_length=1)."""
        resp = await sc_client.get("/api/v1/supply-chain/check?package=")
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_oversized_package_returns_422(self, sc_client):
        """Names longer than 200 chars are rejected before the engine runs."""
        resp = await sc_client.get(
            "/api/v1/supply-chain/check?package=" + "a" * 201
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "bad_name",
        ["requests requests", "a/b", "😀", "pkg;v1", "pkg,v2", "pkg\\evil"],
    )
    @pytest.mark.anyio
    async def test_illegal_characters_return_422(self, sc_client, bad_name):
        """Names outside [A-Za-z0-9._-] are rejected."""
        resp = await sc_client.get(
            "/api/v1/supply-chain/check?package=" + quote(bad_name)
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "good_name", ["requests", "scikit-learn", "pillow", "Django"]
    )
    @pytest.mark.anyio
    async def test_valid_names_return_200(self, sc_client, good_name):
        """Well-formed package names still scan successfully."""
        resp = await sc_client.get(
            "/api/v1/supply-chain/check?package=" + quote(good_name)
        )
        assert resp.status_code == 200


class TestRealMetadataFeeding:
    """Download heuristics run on real metadata, never dummy data (F2)."""

    @pytest.mark.anyio
    async def test_popular_package_gets_no_bogus_low_download_reason(
        self, sc_client, monkeypatch
    ):
        """A known-popular package is not flagged for low downloads."""
        from datetime import UTC, datetime, timedelta

        from python_depot.supply_chain import PackageInfo

        async def _popular(_name):
            return PackageInfo(
                name="requests",
                downloads=10**9,
                released_at=datetime.now(UTC) - timedelta(days=3650),
            )

        monkeypatch.setattr(
            "python_depot.routers.supply_chain.fetch_package_info", _popular
        )
        resp = await sc_client.get("/api/v1/supply-chain/check?package=requests")
        assert resp.status_code == 200
        reasons = resp.json()["reasons"]
        assert not any("low download count" in r for r in reasons)

    @pytest.mark.anyio
    async def test_unknown_metadata_emits_no_low_download_reason(self, sc_client):
        """Unknown download data must not produce the bogus reason either."""
        resp = await sc_client.get("/api/v1/supply-chain/check?package=requests")
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 0
        assert not any("low download count" in r for r in data["reasons"])


class TestAlertValueChain:
    """Webhook alerts fire when a package hits the threshold (F3, F4)."""

    @staticmethod
    def _seed_suspicious_scanner(monkeypatch) -> None:
        """Make one scanned package known-malicious and wire the webhook."""
        from python_depot.supply_chain import MaliciousFeed, SupplyChainScanner

        scanner = SupplyChainScanner(feed=MaliciousFeed(blocklist=["requests"]))
        monkeypatch.setattr(
            "python_depot.routers.supply_chain._scanner", lambda: scanner
        )
        monkeypatch.setenv(
            "PYTHONDEPOT_SUPPLY_CHAIN_WEBHOOK_URL",
            "https://hooks.example.com/supply-chain",
        )

    @pytest.mark.anyio
    async def test_scan_fires_webhook_for_suspicious_package(
        self, sc_client, monkeypatch
    ):
        """A score >= threshold triggers exactly one webhook POST (F3)."""
        import httpx

        self._seed_suspicious_scanner(monkeypatch)
        posts: list[tuple[str, dict]] = []

        async def _fake_post(self_, url, json=None, **kwargs):
            posts.append((str(url), json))
            return httpx.Response(200, json={}, request=httpx.Request("POST", url))

        monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)

        resp = await sc_client.get("/api/v1/supply-chain/scan")
        assert resp.status_code == 200
        assert len(posts) == 1
        url, payload = posts[0]
        assert url == "https://hooks.example.com/supply-chain"
        assert payload["package"] == "requests"
        assert payload["score"] >= 60

    @pytest.mark.anyio
    async def test_scan_does_not_refire_webhook_across_requests(
        self, sc_client, monkeypatch
    ):
        """Exactly-once: a second /scan must not re-fire the webhook (F4)."""
        import httpx

        self._seed_suspicious_scanner(monkeypatch)
        posts: list[str] = []

        async def _fake_post(self_, url, json=None, **kwargs):
            posts.append(str(url))
            return httpx.Response(200, json={}, request=httpx.Request("POST", url))

        monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)

        first = await sc_client.get("/api/v1/supply-chain/scan")
        second = await sc_client.get("/api/v1/supply-chain/scan")
        assert first.status_code == 200
        assert second.status_code == 200
        assert len(posts) == 1
