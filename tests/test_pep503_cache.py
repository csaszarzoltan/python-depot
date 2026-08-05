"""Pre-dev TDD tests for the PEP 503 caching proxy service.

Pattern (repo convention):
- Interface tests: verify imports, class/function signatures, type hints,
  dataclass fields and the ORM schema — PASS immediately.
- Behavioral tests: verify the expected caching/proxying behavior by
  calling the stub methods directly — FAIL with NotImplementedError until
  the developer implements ``python_depot/pep503_cache.py`` and
  ``python_depot/models/pep503_cache.py``.
"""

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

# Module-level import registers the tables on Base.metadata before the
# autouse reset_db() fixture runs, so the schema exists for every test.
from python_depot.database import Base, SessionLocal
from python_depot.models.pep503_cache import CachedArtifact, CachedPackage
from python_depot.pep503_cache import (
    ALLOWED_HOSTS,
    PYPI_FILES_HOST,
    PYPI_SIMPLE_URL,
    CacheConfig,
    CacheMissError,
    PyPICacheService,
    SimpleIndexResult,
    normalize_package_name,
    validate_upstream_url,
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
def service(db_session):
    """PyPICacheService bound to the test session (plumbing only)."""
    return PyPICacheService(config=CacheConfig(), db=db_session)


# ---------------------------------------------------------------------------
# Interface tests — pass immediately
# ---------------------------------------------------------------------------


class TestPep503ConstantsInterface:
    """Module constants for the caching proxy."""

    def test_upstream_simple_url_template(self):
        """Upstream PyPI simple-index URL template is defined."""
        assert PYPI_SIMPLE_URL == "https://pypi.org/simple/{package}/"

    def test_artifact_host_defined(self):
        """Upstream artifact host is defined and allowlisted."""
        assert PYPI_FILES_HOST == "files.pythonhosted.org"
        assert PYPI_FILES_HOST in ALLOWED_HOSTS

    def test_allowed_hosts_is_tuple_of_hosts(self):
        """ALLOWED_HOSTS is a tuple of non-empty strings."""
        assert isinstance(ALLOWED_HOSTS, tuple)
        assert len(ALLOWED_HOSTS) > 0
        for host in ALLOWED_HOSTS:
            assert isinstance(host, str)
            assert len(host) > 0


class TestNormalizePackageNameInterface:
    """PEP 503 normalization function contract."""

    def test_importable(self):
        """normalize_package_name is importable and callable."""
        assert callable(normalize_package_name)

    def test_signature(self):
        """Signature: normalize_package_name(name: str) -> str."""
        sig = inspect.signature(normalize_package_name)
        assert "name" in sig.parameters
        ret = _ret_annotation(normalize_package_name)
        assert ret == "str" or ret is str


class TestValidateUpstreamUrlInterface:
    """SSRF URL validation contract."""

    def test_importable(self):
        """validate_upstream_url is importable and callable."""
        assert callable(validate_upstream_url)

    def test_signature(self):
        """Signature accepts url and allowed_hosts (default ALLOWED_HOSTS)."""
        sig = inspect.signature(validate_upstream_url)
        params = sig.parameters
        assert "url" in params
        assert "allowed_hosts" in params
        assert params["allowed_hosts"].default == ALLOWED_HOSTS
        ret = _ret_annotation(validate_upstream_url)
        assert ret == "bool" or ret is bool


class TestCacheConfigInterface:
    """CacheConfig dataclass fields and defaults."""

    def test_is_dataclass(self):
        assert is_dataclass(CacheConfig)

    def test_has_all_fields(self):
        """Config exposes the documented knobs."""
        names = {f.name for f in fields(CacheConfig)}
        assert {
            "cache_dir",
            "ttl_seconds",
            "max_size_bytes",
            "offline_mode",
            "upstream_timeout",
        } <= names

    def test_defaults(self):
        """Defaults: ttl 300s, 5 GiB cap, no offline, 10s timeout."""
        cfg = CacheConfig()
        assert cfg.ttl_seconds == 300
        assert cfg.max_size_bytes == 5 * 1024 * 1024 * 1024
        assert cfg.offline_mode is False
        assert cfg.upstream_timeout == 10.0


class TestSimpleIndexResultInterface:
    """SimpleIndexResult dataclass."""

    def test_is_dataclass(self):
        assert is_dataclass(SimpleIndexResult)

    def test_has_all_fields(self):
        names = {f.name for f in fields(SimpleIndexResult)}
        assert {"package", "versions", "served_from_cache"} <= names

    def test_constructible(self):
        result = SimpleIndexResult(package="requests", versions=["2.32.0"], served_from_cache=True)
        assert result.package == "requests"
        assert result.versions == ["2.32.0"]
        assert result.served_from_cache is True


class TestCacheMissErrorInterface:
    """CacheMissError exception exists."""

    def test_is_exception(self):
        assert issubclass(CacheMissError, Exception)


class TestPyPICacheServiceInterface:
    """PyPICacheService class contract."""

    def test_importable(self):
        assert isinstance(PyPICacheService, type)

    def test_init_signature(self):
        """__init__ accepts config and db, both optional."""
        sig = inspect.signature(PyPICacheService.__init__)
        params = sig.parameters
        assert "config" in params
        assert "db" in params
        assert params["config"].default is None
        assert params["db"].default is None

    def test_constructible_with_config(self, db_session):
        """Service constructs with an explicit config + db (plumbing)."""
        svc = PyPICacheService(config=CacheConfig(), db=db_session)
        assert svc.config is not None
        assert svc.db is db_session

    def test_default_config_reads_env(self, monkeypatch):
        """Env overrides flow into the default config (PYTHONDEPOT_*)."""
        monkeypatch.setenv("PYTHONDEPOT_CACHE_TTL", "42")
        monkeypatch.setenv("PYTHONDEPOT_OFFLINE_MODE", "1")
        svc = PyPICacheService()
        assert svc.config.ttl_seconds == 42
        assert svc.config.offline_mode is True
        assert svc._offline_mode is True

    def test_has_core_methods(self):
        """Every documented service method exists."""
        for name in (
            "get_simple_index",
            "fetch_upstream_index",
            "get_cached_versions",
            "is_cached",
            "set_offline_mode",
            "is_offline_mode",
            "get_artifact",
            "hit_rate",
            "bytes_served",
            "bytes_proxied",
            "package_stats",
            "overall_stats",
        ):
            assert callable(getattr(PyPICacheService, name)), name

    def test_async_methods_are_coroutines(self):
        """Network-touching methods are async."""
        for name in ("get_simple_index", "fetch_upstream_index", "get_artifact"):
            assert inspect.iscoroutinefunction(getattr(PyPICacheService, name)), name

    def test_get_simple_index_signature(self):
        """get_simple_index(package: str) -> SimpleIndexResult."""
        sig = inspect.signature(PyPICacheService.get_simple_index)
        assert "package" in sig.parameters
        assert "self" in sig.parameters
        ret = _ret_annotation(PyPICacheService.get_simple_index)
        assert ret == "SimpleIndexResult" or ret is SimpleIndexResult

    def test_analytics_method_return_annotations(self):
        """Analytics methods annotated with float/int/dict."""
        assert _ret_annotation(PyPICacheService.hit_rate) in ("float", float)
        assert _ret_annotation(PyPICacheService.bytes_served) in ("int", int)
        assert _ret_annotation(PyPICacheService.bytes_proxied) in ("int", int)
        ret = _ret_annotation(PyPICacheService.package_stats)
        assert "dict" in str(ret)
        ret = _ret_annotation(PyPICacheService.overall_stats)
        assert "dict" in str(ret)


class TestCachedPackageModelInterface:
    """CachedPackage ORM schema."""

    def test_table_registered(self):
        """pep503_cached_packages table is registered on Base.metadata."""
        assert "pep503_cached_packages" in Base.metadata.tables

    def test_tablename(self):
        assert CachedPackage.__tablename__ == "pep503_cached_packages"

    def test_columns_present(self):
        """All documented columns exist."""
        cols = {c.name for c in CachedPackage.__table__.c}
        assert {
            "id",
            "package",
            "normalized_name",
            "versions_json",
            "fetched_at",
            "last_access_at",
            "hit_count",
            "miss_count",
            "bytes_served",
            "bytes_proxied",
        } <= cols

    def test_normalized_name_indexed_and_unique(self):
        """normalized_name is the unique lookup key."""
        col = CachedPackage.__table__.c["normalized_name"]
        assert col.index or col.unique
        assert col.unique

    def test_constructible_and_persists(self, db_session):
        """A row can be created and read back."""
        pkg = CachedPackage(
            package="Requests",
            normalized_name="requests",
            versions_json='["2.32.0"]',
        )
        db_session.add(pkg)
        db_session.commit()
        loaded = db_session.query(CachedPackage).filter_by(normalized_name="requests").one()
        assert loaded.package == "Requests"
        assert loaded.versions_json == '["2.32.0"]'


class TestCachedArtifactModelInterface:
    """CachedArtifact ORM schema."""

    def test_table_registered(self):
        """pep503_cached_artifacts table is registered on Base.metadata."""
        assert "pep503_cached_artifacts" in Base.metadata.tables

    def test_tablename(self):
        assert CachedArtifact.__tablename__ == "pep503_cached_artifacts"

    def test_columns_present(self):
        cols = {c.name for c in CachedArtifact.__table__.c}
        assert {
            "id",
            "package_name",
            "filename",
            "url",
            "size_bytes",
            "stored_at",
            "last_access_at",
        } <= cols

    def test_filename_indexed(self):
        assert CachedArtifact.__table__.c["filename"].index


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestNormalizePackageNameBehavioral:
    """PEP 503 normalization rules."""

    def test_lowercases(self):
        assert normalize_package_name("Requests") == "requests"

    def test_collapses_underscores_to_dash(self):
        assert normalize_package_name("django_rest_framework") == "django-rest-framework"

    def test_collapses_dots_to_dash(self):
        assert normalize_package_name("Zope.Interface") == "zope-interface"

    def test_collapses_runs_of_separators(self):
        assert normalize_package_name("My.-_Package") == "my-package"

    def test_mixed_case_and_separators(self):
        assert normalize_package_name("NuMPy._-core") == "numpy-core"


class TestValidateUpstreamUrlBehavioral:
    """SSRF guard: schemes and host allowlist."""

    def test_accepts_https_allowlisted(self):
        assert validate_upstream_url("https://pypi.org/simple/requests/") is True

    def test_accepts_http_allowlisted(self):
        assert validate_upstream_url("http://pypi.org/simple/requests/") is True

    def test_accepts_artifact_host(self):
        url = "https://files.pythonhosted.org/packages/xx/yy/requests-2.32.0-py3-none-any.whl"
        assert validate_upstream_url(url) is True

    def test_rejects_ftp_scheme(self):
        assert validate_upstream_url("ftp://pypi.org/simple/requests/") is False

    def test_rejects_file_scheme(self):
        assert validate_upstream_url("file:///etc/passwd") is False

    def test_rejects_unknown_scheme(self):
        assert validate_upstream_url("gopher://pypi.org/x") is False

    def test_rejects_non_allowlisted_host(self):
        assert validate_upstream_url("https://evil.example.com/simple/requests/") is False

    def test_rejects_private_ip_host(self):
        assert validate_upstream_url("https://127.0.0.1/simple/requests/") is False

    def test_rejects_localhost_lookalike(self):
        assert validate_upstream_url("https://pypi.org.evil.com/x") is False


class TestCacheHitBehavioral:
    """Serving the cached version list on a cache hit."""

    @pytest.mark.anyio
    async def test_get_simple_index_serves_cached_versions(self, service, db_session):
        """A cached package is served from cache with its stored versions."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.31.0", "2.32.0"]',
            )
        )
        db_session.commit()
        result = await service.get_simple_index("requests")
        assert result.served_from_cache is True
        assert "2.31.0" in result.versions
        assert "2.32.0" in result.versions

    @pytest.mark.anyio
    async def test_hit_matches_normalized_name(self, service, db_session):
        """Lookup is by PEP 503-normalized name (case/separator agnostic)."""
        db_session.add(
            CachedPackage(
                package="My.Package_Name",
                normalized_name="my-package-name",
                versions_json='["1.0.0"]',
            )
        )
        db_session.commit()
        result = await service.get_simple_index("my.package_name")
        assert result.served_from_cache is True
        assert result.versions == ["1.0.0"]

    def test_get_cached_versions_returns_list(self, service, db_session):
        """get_cached_versions returns the stored version list."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.32.0"]',
            )
        )
        db_session.commit()
        assert service.get_cached_versions("requests") == ["2.32.0"]

    def test_get_cached_versions_missing_returns_empty(self, service):
        """Unknown package yields an empty list, not an error."""
        assert service.get_cached_versions("does-not-exist") == []

    def test_is_cached_true(self, service, db_session):
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.32.0"]',
            )
        )
        db_session.commit()
        assert service.is_cached("requests") is True

    def test_is_cached_false(self, service):
        assert service.is_cached("does-not-exist") is False


class TestCacheMissProxyBehavioral:
    """Proxying upstream PyPI on a cache miss."""

    @pytest.mark.anyio
    async def test_miss_proxies_and_returns_upstream_versions(self, service, monkeypatch):
        """On miss the service fetches upstream, caches, and reports the proxy."""
        async def fake_fetch(package: str) -> str:
            assert package == "requests"
            return (
                '<html><body>'
                '<a href="/simple/requests/requests-2.32.0-py3-none-any.whl">'
                "requests-2.32.0-py3-none-any.whl</a>"
                '<a href="/simple/requests/requests-2.31.0.tar.gz">'
                "requests-2.31.0.tar.gz</a>"
                "</body></html>"
            )

        monkeypatch.setattr(service, "fetch_upstream_index", fake_fetch)
        result = await service.get_simple_index("requests")
        assert result.served_from_cache is False
        assert "2.32.0" in result.versions
        assert "2.31.0" in result.versions

    @pytest.mark.anyio
    async def test_miss_persists_fetched_versions(self, service, db_session, monkeypatch):
        """After a miss the version list is persisted for the next hit."""
        async def fake_fetch(package: str) -> str:
            return '<html><body><a href="/simple/x/x-1.0.0-py3-none-any.whl">x-1.0.0-py3-none-any.whl</a></body></html>'

        monkeypatch.setattr(service, "fetch_upstream_index", fake_fetch)
        await service.get_simple_index("requests")
        row = db_session.query(CachedPackage).filter_by(normalized_name="requests").first()
        assert row is not None
        assert "1.0.0" in row.versions_json

    @pytest.mark.anyio
    async def test_fetch_upstream_index_returns_html(self, service, monkeypatch):
        """fetch_upstream_index returns raw upstream HTML for the package."""
        html = await service.fetch_upstream_index("requests")
        assert isinstance(html, str)
        assert "requests" in html.lower()

    @pytest.mark.anyio
    async def test_miss_increments_miss_count(self, service, db_session, monkeypatch):
        """Misses are counted per package for analytics."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json="[]",
                miss_count=0,
            )
        )
        db_session.commit()

        async def fake_fetch(package: str) -> str:
            return '<html><body><a href="/simple/x/x-1.0.0.whl">x-1.0.0.whl</a></body></html>'

        monkeypatch.setattr(service, "fetch_upstream_index", fake_fetch)
        await service.get_simple_index("requests")
        db_session.expire_all()
        row = db_session.query(CachedPackage).filter_by(normalized_name="requests").one()
        assert row.miss_count >= 1


class TestOfflineFallbackBehavioral:
    """Cache-only fallback when the upstream is unreachable."""

    @pytest.mark.anyio
    async def test_offline_serves_cached_package(self, service, db_session):
        """Offline mode still serves packages that are cached."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.32.0"]',
            )
        )
        db_session.commit()
        service.set_offline_mode(True)
        assert service.is_offline_mode() is True
        result = await service.get_simple_index("requests")
        assert result.served_from_cache is True
        assert "2.32.0" in result.versions

    @pytest.mark.anyio
    async def test_offline_missing_raises_cache_miss(self, service):
        """Offline + not cached raises CacheMissError (endpoint maps to 503)."""
        service.set_offline_mode(True)
        with pytest.raises(CacheMissError):
            await service.get_simple_index("never-cached-package")

    @pytest.mark.anyio
    async def test_offline_never_fetches_upstream(self, service, monkeypatch):
        """Offline mode must not touch the upstream fetcher."""
        db_session = service.db
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.32.0"]',
            )
        )
        db_session.commit()

        async def boom(package: str) -> str:
            raise AssertionError("upstream fetched in offline mode")

        monkeypatch.setattr(service, "fetch_upstream_index", boom)
        service.set_offline_mode(True)
        result = await service.get_simple_index("requests")
        assert result.served_from_cache is True

    def test_offline_mode_toggle(self, service):
        """set_offline_mode flips the flag on/off."""
        service.set_offline_mode(True)
        assert service.is_offline_mode() is True
        service.set_offline_mode(False)
        assert service.is_offline_mode() is False

    def test_defaults_to_config_offline_mode(self, db_session):
        """A service built with offline CacheConfig starts offline."""
        svc = PyPICacheService(config=CacheConfig(offline_mode=True), db=db_session)
        assert svc.is_offline_mode() is True


class TestCacheTtlBehavioral:
    """Cached version lists expire after the configured TTL."""

    @pytest.mark.anyio
    async def test_stale_cache_refetches_upstream(self, service, db_session, monkeypatch):
        """A cache row older than ttl_seconds is refetched (served_from_cache=False)."""
        # SQLite stores naive datetimes (no tz) — seed naive UTC so the value
        # round-trips exactly and TTL arithmetic is deterministic.
        stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            seconds=service.config.ttl_seconds + 60
        )
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.31.0"]',
                fetched_at=stale,
            )
        )
        db_session.commit()

        async def fake_fetch(package: str) -> str:
            return '<html><body><a href="/simple/x/x-2.32.0.whl">x-2.32.0.whl</a></body></html>'

        monkeypatch.setattr(service, "fetch_upstream_index", fake_fetch)
        result = await service.get_simple_index("requests")
        assert result.served_from_cache is False
        assert "2.32.0" in result.versions

    @pytest.mark.anyio
    async def test_fresh_cache_is_served(self, service, db_session, monkeypatch):
        """A fresh cache row (within TTL) is served without upstream calls."""
        # Naive UTC — see test_stale_cache_refetches_upstream for why.
        fresh = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=10)
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.32.0"]',
                fetched_at=fresh,
            )
        )
        db_session.commit()

        async def boom(package: str) -> str:
            raise AssertionError("upstream fetched for fresh cache")

        monkeypatch.setattr(service, "fetch_upstream_index", boom)
        result = await service.get_simple_index("requests")
        assert result.served_from_cache is True
        assert "2.32.0" in result.versions


class TestAnalyticsBehavioral:
    """Hit rate, bytes served vs proxied, and per-package stats."""

    def test_hit_rate_zero_when_no_traffic(self, service):
        """No traffic → 0.0 hit rate."""
        assert service.hit_rate() == 0.0

    def test_hit_rate_reflects_hits_and_misses(self, service, db_session):
        """Seeded counters produce hits/(hits+misses)."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json="[]",
                hit_count=3,
                miss_count=1,
            )
        )
        db_session.commit()
        assert service.hit_rate() == pytest.approx(0.75)

    def test_bytes_served_counts_cached_bytes(self, service, db_session):
        """bytes_served sums the per-package served bytes."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json="[]",
                bytes_served=1024,
            )
        )
        db_session.add(
            CachedPackage(
                package="numpy",
                normalized_name="numpy",
                versions_json="[]",
                bytes_served=2048,
            )
        )
        db_session.commit()
        assert service.bytes_served() == 3072

    def test_bytes_proxied_counts_upstream_bytes(self, service, db_session):
        """bytes_proxied sums the per-package proxied bytes."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json="[]",
                bytes_proxied=4096,
            )
        )
        db_session.commit()
        assert service.bytes_proxied() == 4096

    def test_package_stats_shape(self, service, db_session):
        """package_stats exposes hits/misses/bytes for one package."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json='["2.32.0"]',
                hit_count=2,
                miss_count=1,
                bytes_served=512,
                bytes_proxied=256,
            )
        )
        db_session.commit()
        stats = service.package_stats("requests")
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["bytes_served"] == 512
        assert stats["bytes_proxied"] == 256
        assert isinstance(stats["versions"], list)
        assert "2.32.0" in stats["versions"]

    def test_overall_stats_shape(self, service, db_session):
        """overall_stats aggregates hit_rate/bytes plus per-package stats."""
        db_session.add(
            CachedPackage(
                package="requests",
                normalized_name="requests",
                versions_json="[]",
                hit_count=1,
                miss_count=1,
                bytes_served=100,
                bytes_proxied=200,
            )
        )
        db_session.commit()
        stats = service.overall_stats()
        assert "hit_rate" in stats
        assert "bytes_served" in stats
        assert "bytes_proxied" in stats
        assert "per_package" in stats
        assert "requests" in stats["per_package"]
        assert stats["per_package"]["requests"]["bytes_served"] == 100
