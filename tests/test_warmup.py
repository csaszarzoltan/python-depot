"""Pre-dev TDD tests for the cache warm-up service and CLI.

Pattern (repo convention):
- Interface tests: verify imports, signatures, dataclass fields and
  constructor plumbing — PASS immediately.
- Behavioral tests: verify top-N prefetch behavior by calling the stub
  methods directly — FAIL with NotImplementedError until the developer
  implements ``python_depot/warmup.py``.
"""

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass

import pytest

from python_depot.database import SessionLocal
from python_depot.pep503_cache import (
    CacheConfig,
    CacheMissError,
    PyPICacheService,
    SimpleIndexResult,
)
from python_depot.warmup import TOP_PACKAGES, WarmupResult, WarmupService, main


def _ret_annotation(func) -> str:
    """Return annotation as string (works with ``from __future__ import annotations``)."""
    return inspect.signature(func).return_annotation


# Seed corpus used by the warm-up fixtures (longer than TOP_PACKAGES so
# ``prefetch_top()`` can exercise top_n=10 without repeating packages).
TOP_TEST_PACKAGES: list[str] = [
    "requests",
    "numpy",
    "pandas",
    "flask",
    "django",
    "scipy",
    "matplotlib",
    "pytest",
    "aiohttp",
    "fastapi",
    "httpx",
    "rich",
]


@pytest.fixture
def db_session():
    """Real SQLAlchemy session bound to the test SQLite database."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def warmup_service(db_session):
    """WarmupService bound to a cache service over the test DB."""
    cache = PyPICacheService(config=CacheConfig(), db=db_session)
    return WarmupService(cache=cache, top_packages=TOP_TEST_PACKAGES)


# ---------------------------------------------------------------------------
# Interface tests — pass immediately
# ---------------------------------------------------------------------------


class TestWarmupResultInterface:
    """WarmupResult dataclass."""

    def test_is_dataclass(self):
        assert is_dataclass(WarmupResult)

    def test_has_all_fields(self):
        names = {f.name for f in fields(WarmupResult)}
        assert {"requested", "cached", "failed"} <= names

    def test_defaults(self):
        result = WarmupResult()
        assert result.requested == 0
        assert result.cached == 0
        assert result.failed == []

    def test_constructible(self):
        result = WarmupResult(requested=2, cached=1, failed=["numpy"])
        assert result.requested == 2
        assert result.cached == 1
        assert result.failed == ["numpy"]


class TestTopPackagesInterface:
    """Seed corpus for top-N prefetch."""

    def test_top_packages_is_nonempty_list(self):
        assert isinstance(TOP_PACKAGES, list)
        assert len(TOP_PACKAGES) > 0
        assert all(isinstance(name, str) for name in TOP_PACKAGES)


class TestWarmupServiceInterface:
    """WarmupService class contract."""

    def test_importable(self):
        assert isinstance(WarmupService, type)

    def test_init_signature(self):
        """__init__ accepts cache and top_packages, both optional."""
        sig = inspect.signature(WarmupService.__init__)
        params = sig.parameters
        assert "cache" in params
        assert "top_packages" in params
        assert params["cache"].default is None
        assert params["top_packages"].default is None

    def test_constructible(self, db_session):
        """Constructor plumbing: cache and top_packages stored."""
        cache = PyPICacheService(config=CacheConfig(), db=db_session)
        svc = WarmupService(cache=cache, top_packages=["requests"])
        assert svc.cache is cache
        assert svc.top_packages == ["requests"]

    def test_default_constructor_uses_top_packages(self):
        """Default constructor seeds top_packages from TOP_PACKAGES."""
        svc = WarmupService()
        assert svc.top_packages == TOP_PACKAGES

    def test_has_methods(self):
        """Both prefetch methods exist."""
        assert callable(WarmupService.prefetch_top)
        assert callable(WarmupService.prefetch)

    def test_prefetch_top_signature(self):
        """prefetch_top(top_n: int = 10) -> WarmupResult."""
        sig = inspect.signature(WarmupService.prefetch_top)
        params = sig.parameters
        assert "top_n" in params
        assert params["top_n"].default == 10
        ret = _ret_annotation(WarmupService.prefetch_top)
        assert ret == "WarmupResult" or ret is WarmupResult

    def test_prefetch_signature(self):
        """prefetch(packages: list[str]) -> WarmupResult."""
        sig = inspect.signature(WarmupService.prefetch)
        assert "packages" in sig.parameters
        ret = _ret_annotation(WarmupService.prefetch)
        assert ret == "WarmupResult" or ret is WarmupResult

    def test_prefetch_methods_are_coroutines(self):
        """Prefetch does async network work."""
        assert inspect.iscoroutinefunction(WarmupService.prefetch_top)
        assert inspect.iscoroutinefunction(WarmupService.prefetch)


class TestWarmupCliInterface:
    """CLI entry point contract."""

    def test_main_importable(self):
        assert callable(main)

    def test_main_signature(self):
        """main(argv: list[str] | None = None) -> int."""
        sig = inspect.signature(main)
        assert "argv" in sig.parameters
        assert sig.parameters["argv"].default is None
        ret = _ret_annotation(main)
        assert ret == "int" or ret is int


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestWarmupServiceBehavioral:
    """Top-N prefetch fetches packages through the cache service."""

    @pytest.mark.anyio
    async def test_prefetch_top_returns_counts(self, warmup_service, monkeypatch):
        """prefetch_top reports requested and cached counts."""
        async def fake_get(package: str) -> SimpleIndexResult:
            return SimpleIndexResult(package=package, versions=["1.0.0"], served_from_cache=False)

        monkeypatch.setattr(warmup_service.cache, "get_simple_index", fake_get)
        result = await warmup_service.prefetch_top(top_n=3)
        assert result.requested == 3
        assert 0 <= result.cached <= 3
        assert isinstance(result.failed, list)

    @pytest.mark.anyio
    async def test_prefetch_top_defaults_to_ten(self, warmup_service, monkeypatch):
        """prefetch_top without args requests 10 packages."""
        async def fake_get(package: str) -> SimpleIndexResult:
            return SimpleIndexResult(package=package, versions=["1.0.0"], served_from_cache=False)

        monkeypatch.setattr(warmup_service.cache, "get_simple_index", fake_get)
        result = await warmup_service.prefetch_top()
        assert result.requested == 10

    @pytest.mark.anyio
    async def test_prefetch_calls_cache_for_each_package(self, warmup_service, monkeypatch):
        """prefetch fetches every requested package through the cache."""
        fetched: list[str] = []

        async def fake_get(package: str) -> SimpleIndexResult:
            fetched.append(package)
            return SimpleIndexResult(package=package, versions=["1.0.0"], served_from_cache=False)

        monkeypatch.setattr(warmup_service.cache, "get_simple_index", fake_get)
        result = await warmup_service.prefetch(["requests", "numpy"])
        assert result.requested == 2
        assert result.cached == 2
        assert set(fetched) == {"requests", "numpy"}

    @pytest.mark.anyio
    async def test_prefetch_records_failures(self, warmup_service, monkeypatch):
        """A failing package is recorded in failed; the rest still prefetch."""
        async def fake_get(package: str) -> SimpleIndexResult:
            if package == "broken":
                raise CacheMissError("not cached")
            return SimpleIndexResult(package=package, versions=["1.0.0"], served_from_cache=False)

        monkeypatch.setattr(warmup_service.cache, "get_simple_index", fake_get)
        result = await warmup_service.prefetch(["ok", "broken"])
        assert result.requested == 2
        assert result.cached == 1
        assert "broken" in result.failed

    @pytest.mark.anyio
    async def test_prefetch_top_uses_seed_corpus(self, warmup_service, monkeypatch):
        """prefetch_top pulls from the configured top_packages seed list."""
        fetched: list[str] = []

        async def fake_get(package: str) -> SimpleIndexResult:
            fetched.append(package)
            return SimpleIndexResult(package=package, versions=["1.0.0"], served_from_cache=False)

        monkeypatch.setattr(warmup_service.cache, "get_simple_index", fake_get)
        await warmup_service.prefetch_top(top_n=2)
        assert set(fetched) == set(warmup_service.top_packages[:2])


class TestWarmupCliBehavioral:
    """CLI behavior."""

    def test_cli_main_returns_zero_on_success(self):
        """main() exits 0 after a successful warm-up run."""
        assert main(["--top", "2"]) == 0

    def test_cli_main_defaults_to_top_ten(self):
        """main() with no args runs the default top-10 prefetch."""
        assert main([]) == 0


class TestWarmupCliExitCodeBehavioral:
    """M3: CLI exit code reflects whether anything was cached."""

    def test_cli_main_exits_nonzero_when_nothing_cached(self, monkeypatch):
        """main() returns 1 when the warm-up cached nothing (automation detect)."""

        class _FailingWarmup:
            async def prefetch_top(self, top_n: int) -> WarmupResult:
                return WarmupResult(requested=top_n, cached=0, failed=["requests", "numpy"])

        monkeypatch.setattr("python_depot.warmup.WarmupService", _FailingWarmup)
        assert main(["--top", "2"]) == 1

    def test_cli_main_exits_zero_when_something_cached(self, monkeypatch):
        """main() returns 0 when at least one package was cached."""

        class _HappyWarmup:
            async def prefetch_top(self, top_n: int) -> WarmupResult:
                return WarmupResult(requested=top_n, cached=1, failed=["numpy"])

        monkeypatch.setattr("python_depot.warmup.WarmupService", _HappyWarmup)
        assert main(["--top", "2"]) == 0


class TestWarmupCliSelfContained:
    """Follow-up t_3092d37e: standalone CLI contract.

    The CLI must be self-contained — it initializes the cache tables
    itself (no ``OperationalError: no such table`` on a fresh DB) and
    runs when invoked as ``python -m python_depot.warmup``.
    """

    def test_main_initializes_db_before_running(self, monkeypatch):
        """main() calls init_db() so standalone runs never hit missing tables."""
        import python_depot.warmup as warmup_module

        initialized: list[bool] = []
        monkeypatch.setattr(warmup_module, "init_db", lambda: initialized.append(True))

        class _NoopWarmup:
            async def prefetch_top(self, top_n: int) -> WarmupResult:
                return WarmupResult(requested=top_n, cached=1, failed=[])

        monkeypatch.setattr(warmup_module, "WarmupService", _NoopWarmup)
        assert main(["--top", "1"]) == 0
        assert initialized == [True]

    def test_module_runs_as_main_with_help(self):
        """`python -m python_depot.warmup --help` prints usage (__main__ guard wired)."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "python_depot.warmup", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        assert "python-depot-cache-warmup" in result.stdout
        assert "usage:" in result.stdout.lower()
