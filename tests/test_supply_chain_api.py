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
