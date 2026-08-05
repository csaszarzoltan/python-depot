"""Pre-dev TDD tests for the PEP 503 caching proxy router.

Pattern (repo convention, mirrors test_supply_chain_api.py):
- Interface tests: verify the router module, route registration, HTTP
  methods, handler signatures and type hints — PASS immediately.
- Behavioral tests: hit the endpoints through a minimal FastAPI app that
  includes the stub router. Because httpx ASGITransport is created with
  ``raise_app_exceptions=True``, the handler's NotImplementedError
  propagates out of the request — FAIL with NotImplementedError until the
  developer implements ``python_depot/routers/pep503.py``.

Endpoints under test:
- GET  /simple/{package}/        — PEP 503 simple index (cache hit /
                                    upstream proxy / offline 503)
- GET  /api/v1/cache/analytics   — hit rate, bytes served vs proxied,
                                    per-package stats
- POST /api/v1/cache/warmup      — prefetch top-N packages
"""

from __future__ import annotations

import inspect

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from python_depot.database import SessionLocal
from python_depot.models.pep503_cache import CachedPackage
from python_depot.pep503_cache import CacheConfig, PyPICacheService
from python_depot.routers.pep503 import (
    WarmupRequest,
    _get_cache_service,
    cache_analytics,
    cache_warmup,
    router,
    serve_simple_index,
)


def _ret_annotation(func) -> str:
    """Return annotation as string (works with ``from __future__ import annotations``)."""
    return inspect.signature(func).return_annotation


@pytest.fixture
def db_session():
    """Real SQLAlchemy session bound to the test SQLite database."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def pep503_app() -> FastAPI:
    """Minimal FastAPI app wiring the pep503 router (prefix '')."""
    application = FastAPI()
    application.include_router(router, prefix="")
    return application


@pytest.fixture
async def pep503_client(pep503_app):
    """Async HTTP client against the pep503 app.

    raise_app_exceptions=True propagates the stub handler's
    NotImplementedError out of the request so behavioral tests fail
    red with NotImplementedError until the handler is implemented.
    """
    transport = ASGITransport(app=pep503_app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _client_for(app: FastAPI):
    """Build an ASGI client for a given app (used after monkeypatching deps)."""
    transport = ASGITransport(app=app, raise_app_exceptions=True)
    return AsyncClient(transport=transport, base_url="http://test")


def _bind_service(app: FastAPI, service: PyPICacheService) -> None:
    """Point the router's dependency at a pre-built service.

    Uses ``app.dependency_overrides`` keyed on the dependency callable.
    NOTE: module-attribute monkeypatching (setattr on
    ``python_depot.routers.pep503._get_cache_service``) does NOT work —
    FastAPI captures the Depends() callable at decoration time, so the
    override dict keyed on that same callable is the only reliable hook.
    """
    app.dependency_overrides[_get_cache_service] = lambda: service


# ---------------------------------------------------------------------------
# Interface tests — pass immediately
# ---------------------------------------------------------------------------


class TestPep503RouterInterface:
    """Router module contract."""

    def test_router_import(self):
        """Router module imports and exposes an APIRouter instance."""
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_three_endpoints(self):
        """Router defines simple-index, analytics and warmup endpoints."""
        assert len(router.routes) == 3

    def test_simple_index_route_registered(self):
        """GET /simple/{package}/ is registered."""
        paths = {r.path for r in router.routes}
        assert "/simple/{package}/" in paths

    def test_analytics_route_registered(self):
        """GET /api/v1/cache/analytics is registered."""
        paths = {r.path for r in router.routes}
        assert "/api/v1/cache/analytics" in paths

    def test_warmup_route_registered(self):
        """POST /api/v1/cache/warmup is registered."""
        paths = {r.path for r in router.routes}
        assert "/api/v1/cache/warmup" in paths

    def test_route_methods(self):
        """Simple index + analytics are GET; warmup is POST."""
        methods = {r.path: r.methods for r in router.routes}
        assert "GET" in methods["/simple/{package}/"]
        assert "GET" in methods["/api/v1/cache/analytics"]
        assert "POST" in methods["/api/v1/cache/warmup"]

    def test_handlers_are_async(self):
        """All three handlers are coroutine functions."""
        assert inspect.iscoroutinefunction(serve_simple_index)
        assert inspect.iscoroutinefunction(cache_analytics)
        assert inspect.iscoroutinefunction(cache_warmup)

    def test_simple_index_handler_signature(self):
        """serve_simple_index accepts package (path) and service (dependency)."""
        sig = inspect.signature(serve_simple_index)
        params = sig.parameters
        assert "package" in params
        assert "service" in params
        _ret_annotation(serve_simple_index)

    def test_analytics_handler_signature(self):
        """cache_analytics accepts service (dependency)."""
        sig = inspect.signature(cache_analytics)
        assert "service" in sig.parameters

    def test_warmup_handler_signature(self):
        """cache_warmup accepts body (WarmupRequest) and service."""
        sig = inspect.signature(cache_warmup)
        params = sig.parameters
        assert "body" in params
        assert "service" in params

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
        assert "/simple/{package}/" in paths
        assert "/api/v1/cache/analytics" in paths
        assert "/api/v1/cache/warmup" in paths


class TestWarmupRequestInterface:
    """WarmupRequest pydantic model."""

    def test_fields(self):
        """top_n (default 10) and packages (optional list) are fields."""
        assert "top_n" in WarmupRequest.model_fields
        assert "packages" in WarmupRequest.model_fields

    def test_default_top_n(self):
        assert WarmupRequest().top_n == 10

    def test_constructible(self):
        req = WarmupRequest(top_n=5, packages=["requests"])
        assert req.top_n == 5
        assert req.packages == ["requests"]

    def test_validation_rejects_zero_top_n(self):
        """top_n must be >= 1 (validation runs before the stub body)."""
        with pytest.raises(Exception):
            WarmupRequest(top_n=0)


class TestPep503ApiValidationInterface:
    """Request validation that runs before any handler logic."""

    @pytest.mark.anyio
    async def test_warmup_rejects_zero_top_n(self, pep503_client):
        """top_n=0 is rejected with 422 by FastAPI validation."""
        resp = await pep503_client.post("/api/v1/cache/warmup", json={"top_n": 0})
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_warmup_rejects_missing_body(self, pep503_client):
        """A warmup request without a body is rejected with 422."""
        resp = await pep503_client.post("/api/v1/cache/warmup")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestSimpleIndexApiBehavioral:
    """GET /simple/{package}/ serving behavior."""

    @pytest.mark.anyio
    async def test_serves_cached_version_list(self, pep503_app, db_session, monkeypatch):
        """Cache hit: 200 with the cached versions and artifact links."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.31.0", "2.32.0"]',
            )
        )
        db_session.commit()
        _bind_service(pep503_app, PyPICacheService(config=CacheConfig(), db=db_session))
        async with _client_for(pep503_app) as ac:
            resp = await ac.get("/simple/requests/")
        assert resp.status_code == 200
        assert "2.32.0" in resp.text
        assert "2.31.0" in resp.text

    @pytest.mark.anyio
    async def test_index_html_contains_artifact_links(self, pep503_app, db_session, monkeypatch):
        """PEP 503 page exposes <a href> artifact links for pip resolution."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.32.0"]',
            )
        )
        db_session.commit()
        _bind_service(pep503_app, PyPICacheService(config=CacheConfig(), db=db_session))
        async with _client_for(pep503_app) as ac:
            resp = await ac.get("/simple/requests/")
        assert resp.status_code == 200
        assert "<a href" in resp.text.lower()

    @pytest.mark.anyio
    async def test_proxies_upstream_on_cache_miss(self, pep503_app, db_session, monkeypatch):
        """Cache miss: proxy upstream, serve the proxied versions, cache them."""
        service = PyPICacheService(config=CacheConfig(), db=db_session)

        async def fake_fetch(package: str) -> str:
            return (
                '<html><body>'
                '<a href="/simple/requests/requests-2.32.0-py3-none-any.whl">'
                "requests-2.32.0-py3-none-any.whl</a></body></html>"
            )

        monkeypatch.setattr(service, "fetch_upstream_index", fake_fetch)
        _bind_service(pep503_app, service)
        async with _client_for(pep503_app) as ac:
            resp = await ac.get("/simple/requests/")
        assert resp.status_code == 200
        assert "2.32.0" in resp.text
        row = db_session.query(CachedPackage).filter_by(normalized_name="requests").first()
        assert row is not None
        assert "2.32.0" in row.versions_json

    @pytest.mark.anyio
    async def test_offline_serves_cached_package(self, pep503_app, db_session, monkeypatch):
        """Offline mode still serves cached packages with 200."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.32.0"]',
            )
        )
        db_session.commit()
        service = PyPICacheService(
            config=CacheConfig(offline_mode=True), db=db_session
        )
        _bind_service(pep503_app, service)
        async with _client_for(pep503_app) as ac:
            resp = await ac.get("/simple/requests/")
        assert resp.status_code == 200
        assert "2.32.0" in resp.text

    @pytest.mark.anyio
    async def test_offline_missing_returns_503(self, pep503_app, db_session, monkeypatch):
        """Offline + not cached → clear 503 (cache-only fallback warning)."""
        service = PyPICacheService(
            config=CacheConfig(offline_mode=True), db=db_session
        )
        _bind_service(pep503_app, service)
        async with _client_for(pep503_app) as ac:
            resp = await ac.get("/simple/never-cached-package/")
        assert resp.status_code == 503

    @pytest.mark.anyio
    async def test_normalizes_requested_package_name(self, pep503_app, db_session, monkeypatch):
        """Request names are PEP 503-normalized before lookup."""
        db_session.add(
            CachedPackage(
                package="My.Package_Name",
                normalized_name="my-package-name",
                versions_json='["1.0.0"]',
            )
        )
        db_session.commit()
        _bind_service(pep503_app, PyPICacheService(config=CacheConfig(), db=db_session))
        async with _client_for(pep503_app) as ac:
            resp = await ac.get("/simple/My.Package_Name/")
        assert resp.status_code == 200
        assert "1.0.0" in resp.text


class TestCacheAnalyticsApiBehavioral:
    """GET /api/v1/cache/analytics."""

    @pytest.mark.anyio
    async def test_analytics_shape(self, pep503_app, db_session, monkeypatch):
        """Analytics expose hit rate, bytes served/proxied and per-package stats."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json="[]",
                hit_count=3,
                miss_count=1,
                bytes_served=1024,
                bytes_proxied=512,
            )
        )
        db_session.commit()
        _bind_service(pep503_app, PyPICacheService(config=CacheConfig(), db=db_session))
        async with _client_for(pep503_app) as ac:
            resp = await ac.get("/api/v1/cache/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["hit_rate"], float)
        assert 0.0 <= data["hit_rate"] <= 1.0
        assert isinstance(data["bytes_served"], int)
        assert isinstance(data["bytes_proxied"], int)
        assert isinstance(data["per_package"], dict)
        assert "requests" in data["per_package"]

    @pytest.mark.anyio
    async def test_analytics_empty_cache(self, pep503_app, db_session, monkeypatch):
        """An empty cache still yields a valid analytics document."""
        _bind_service(pep503_app, PyPICacheService(config=CacheConfig(), db=db_session))
        async with _client_for(pep503_app) as ac:
            resp = await ac.get("/api/v1/cache/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["hit_rate"] == 0.0
        assert data["bytes_served"] == 0
        assert data["bytes_proxied"] == 0


class TestWarmupApiBehavioral:
    """POST /api/v1/cache/warmup."""

    @pytest.mark.anyio
    async def test_warmup_top_n(self, pep503_app, db_session, monkeypatch):
        """Warmup with top_n prefetches through the cache service."""
        service = PyPICacheService(config=CacheConfig(), db=db_session)
        _bind_service(pep503_app, service)
        async with _client_for(pep503_app) as ac:
            resp = await ac.post("/api/v1/cache/warmup", json={"top_n": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["requested"] == 3
        assert 0 <= data["cached"] <= 3
        assert isinstance(data["failed"], list)

    @pytest.mark.anyio
    async def test_warmup_explicit_packages(self, pep503_app, db_session, monkeypatch):
        """Warmup with an explicit package list prefetches exactly those."""
        service = PyPICacheService(config=CacheConfig(), db=db_session)
        _bind_service(pep503_app, service)
        async with _client_for(pep503_app) as ac:
            resp = await ac.post(
                "/api/v1/cache/warmup", json={"packages": ["requests", "numpy"]}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requested"] == 2
