"""Pre-dev TDD tests for the supply-chain typosquatting scanner.

Pattern (repo convention):
- Interface tests: verify imports, class/function signatures, type hints,
  dataclass fields and the ORM schema — PASS immediately.
- Behavioral tests: verify the expected detection behavior by calling the
  stub methods directly — FAIL with NotImplementedError until the
  developer implements ``python_depot/supply_chain.py`` and
  ``python_depot/models/supply_chain_verdict.py``.
"""

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

# Module-level import registers the table on Base.metadata before the
# autouse reset_db() fixture runs, so the schema exists for every test.
from python_depot.database import Base, SessionLocal
from python_depot.models.supply_chain_verdict import SupplyChainVerdict
from python_depot.supply_chain import (
    MaliciousFeed,
    PackageInfo,
    SimilarityEngine,
    SupplyChainAlerter,
    SupplyChainScanner,
    list_verdicts,
    store_verdict,
)


def _ret_annotation(func) -> str:
    """Return annotation as string (works with ``from __future__ import annotations``)."""
    return inspect.signature(func).return_annotation


def _assert_annotation(func, expected: str) -> None:
    """Assert a return annotation, accepting both string and class form."""
    ret = _ret_annotation(func)
    assert ret == expected or ret is expected, f"annotation {ret!r} != {expected!r}"


@pytest.fixture
def db_session():
    """Real SQLAlchemy session bound to the test SQLite database."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Interface tests — pass immediately
# ---------------------------------------------------------------------------


class TestSimilarityEngineInterface:
    """Verify SimilarityEngine exists with the expected interface."""

    def test_module_import(self):
        """python_depot.supply_chain imports without error."""
        import python_depot.supply_chain  # noqa: F401

    def test_similarity_engine_import(self):
        """SimilarityEngine can be imported."""
        from python_depot.supply_chain import SimilarityEngine

        assert isinstance(SimilarityEngine, type)

    def test_init_signature(self):
        """__init__ accepts a configurable threshold defaulting to 0.8."""
        sig = inspect.signature(SimilarityEngine.__init__)
        params = sig.parameters
        assert "threshold" in params
        assert params["threshold"].default == 0.8

    def test_default_threshold_stored(self):
        """Default threshold is stored on the instance."""
        engine = SimilarityEngine()
        assert engine.threshold == 0.8

    def test_custom_threshold_stored(self):
        """Custom threshold is accepted and stored."""
        engine = SimilarityEngine(threshold=0.9)
        assert engine.threshold == 0.9

    def test_has_levenshtein_distance(self):
        """levenshtein_distance method exists."""
        assert hasattr(SimilarityEngine, "levenshtein_distance")
        assert callable(SimilarityEngine.levenshtein_distance)

    def test_has_damerau_levenshtein_distance(self):
        """damerau_levenshtein_distance method exists."""
        assert hasattr(SimilarityEngine, "damerau_levenshtein_distance")
        assert callable(SimilarityEngine.damerau_levenshtein_distance)

    def test_has_prefix_similarity(self):
        """prefix_similarity method exists."""
        assert hasattr(SimilarityEngine, "prefix_similarity")
        assert callable(SimilarityEngine.prefix_similarity)

    def test_has_suffix_similarity(self):
        """suffix_similarity method exists."""
        assert hasattr(SimilarityEngine, "suffix_similarity")
        assert callable(SimilarityEngine.suffix_similarity)

    def test_has_similarity(self):
        """similarity method exists."""
        assert hasattr(SimilarityEngine, "similarity")
        assert callable(SimilarityEngine.similarity)

    def test_has_is_similar(self):
        """is_similar method exists."""
        assert hasattr(SimilarityEngine, "is_similar")
        assert callable(SimilarityEngine.is_similar)

    def test_levenshtein_signature(self):
        """levenshtein_distance(a, b) -> int."""
        sig = inspect.signature(SimilarityEngine.levenshtein_distance)
        params = list(sig.parameters)
        assert params == ["self", "a", "b"]
        _assert_annotation(SimilarityEngine.levenshtein_distance, "int")

    def test_damerau_signature(self):
        """damerau_levenshtein_distance(a, b) -> int."""
        sig = inspect.signature(SimilarityEngine.damerau_levenshtein_distance)
        params = list(sig.parameters)
        assert params == ["self", "a", "b"]
        _assert_annotation(SimilarityEngine.damerau_levenshtein_distance, "int")

    def test_prefix_signature(self):
        """prefix_similarity(a, b) -> float."""
        sig = inspect.signature(SimilarityEngine.prefix_similarity)
        params = list(sig.parameters)
        assert params == ["self", "a", "b"]
        _assert_annotation(SimilarityEngine.prefix_similarity, "float")

    def test_suffix_signature(self):
        """suffix_similarity(a, b) -> float."""
        sig = inspect.signature(SimilarityEngine.suffix_similarity)
        params = list(sig.parameters)
        assert params == ["self", "a", "b"]
        _assert_annotation(SimilarityEngine.suffix_similarity, "float")

    def test_similarity_signature(self):
        """similarity(a, b) -> float."""
        sig = inspect.signature(SimilarityEngine.similarity)
        params = list(sig.parameters)
        assert params == ["self", "a", "b"]
        _assert_annotation(SimilarityEngine.similarity, "float")

    def test_is_similar_signature(self):
        """is_similar(candidate, known) -> bool."""
        sig = inspect.signature(SimilarityEngine.is_similar)
        params = list(sig.parameters)
        assert params == ["self", "candidate", "known"]
        _assert_annotation(SimilarityEngine.is_similar, "bool")


class TestPackageInfoInterface:
    """Verify PackageInfo dataclass contract."""

    def test_is_dataclass(self):
        """PackageInfo is a dataclass."""
        assert is_dataclass(PackageInfo)

    def test_fields(self):
        """PackageInfo has name, downloads, released_at fields."""
        names = {f.name for f in fields(PackageInfo)}
        assert names == {"name", "downloads", "released_at"}

    def test_defaults(self):
        """downloads defaults to 0 and released_at to None."""
        info = PackageInfo(name="requests")
        assert info.downloads == 0
        assert info.released_at is None

    def test_name_required(self):
        """PackageInfo requires a name."""
        with pytest.raises(TypeError):
            PackageInfo()  # type: ignore[call-arg]


class TestMaliciousFeedInterface:
    """Verify MaliciousFeed exists with the expected interface."""

    def test_import(self):
        """MaliciousFeed can be imported."""
        assert isinstance(MaliciousFeed, type)

    def test_init_signature(self):
        """__init__ accepts osv_entries and blocklist (both optional)."""
        sig = inspect.signature(MaliciousFeed.__init__)
        params = sig.parameters
        assert "osv_entries" in params
        assert "blocklist" in params
        assert params["osv_entries"].default is None
        assert params["blocklist"].default is None

    def test_defaults_stored(self):
        """Empty feed stores empty lists."""
        feed = MaliciousFeed()
        assert feed.osv_entries == []
        assert feed.blocklist == []

    def test_seeded_stored(self):
        """Provided entries are stored."""
        feed = MaliciousFeed(osv_entries=[{"package": "requets"}], blocklist=["evil"])
        assert feed.osv_entries == [{"package": "requets"}]
        assert feed.blocklist == ["evil"]

    def test_has_load(self):
        """load method exists."""
        assert hasattr(MaliciousFeed, "load")
        assert callable(MaliciousFeed.load)

    def test_has_refresh(self):
        """refresh method exists."""
        assert hasattr(MaliciousFeed, "refresh")
        assert callable(MaliciousFeed.refresh)

    def test_has_is_known_malicious(self):
        """is_known_malicious method exists."""
        assert hasattr(MaliciousFeed, "is_known_malicious")
        assert callable(MaliciousFeed.is_known_malicious)

    def test_has_known_packages(self):
        """known_packages method exists."""
        assert hasattr(MaliciousFeed, "known_packages")
        assert callable(MaliciousFeed.known_packages)

    def test_method_signatures(self):
        """load/refresh/is_known_malicious/known_packages signatures."""
        assert list(inspect.signature(MaliciousFeed.load).parameters) == ["self"]
        assert list(inspect.signature(MaliciousFeed.refresh).parameters) == ["self"]
        assert list(inspect.signature(MaliciousFeed.is_known_malicious).parameters) == [
            "self",
            "name",
        ]
        assert list(inspect.signature(MaliciousFeed.known_packages).parameters) == ["self"]

    def test_return_annotations(self):
        """Return type hints for feed methods."""
        _assert_annotation(MaliciousFeed.load, "None")
        _assert_annotation(MaliciousFeed.refresh, "None")
        _assert_annotation(MaliciousFeed.is_known_malicious, "bool")
        _assert_annotation(MaliciousFeed.known_packages, "list[str]")


class TestSupplyChainScannerInterface:
    """Verify SupplyChainScanner exists with the expected interface."""

    def test_import(self):
        """SupplyChainScanner can be imported."""
        assert isinstance(SupplyChainScanner, type)

    def test_init_signature(self):
        """__init__ accepts engine, feed, threshold, min_downloads, max_release_age_days."""
        sig = inspect.signature(SupplyChainScanner.__init__)
        params = sig.parameters
        for name in (
            "engine",
            "feed",
            "threshold",
            "min_downloads",
            "max_release_age_days",
        ):
            assert name in params, f"missing param {name}"
        assert params["threshold"].default == 0.8
        assert params["min_downloads"].default == 1000
        assert params["max_release_age_days"].default == 30

    def test_defaults_created(self):
        """Default engine and feed are created when omitted."""
        scanner = SupplyChainScanner()
        assert isinstance(scanner.engine, SimilarityEngine)
        assert isinstance(scanner.feed, MaliciousFeed)

    def test_has_download_risk(self):
        """download_risk method exists."""
        assert hasattr(SupplyChainScanner, "download_risk")
        assert callable(SupplyChainScanner.download_risk)

    def test_has_freshness_risk(self):
        """freshness_risk method exists."""
        assert hasattr(SupplyChainScanner, "freshness_risk")
        assert callable(SupplyChainScanner.freshness_risk)

    def test_has_scan(self):
        """scan method exists."""
        assert hasattr(SupplyChainScanner, "scan")
        assert callable(SupplyChainScanner.scan)

    def test_has_scan_many(self):
        """scan_many method exists."""
        assert hasattr(SupplyChainScanner, "scan_many")
        assert callable(SupplyChainScanner.scan_many)

    def test_download_risk_signature(self):
        """download_risk(downloads) -> float."""
        sig = inspect.signature(SupplyChainScanner.download_risk)
        assert list(sig.parameters) == ["self", "downloads"]
        _assert_annotation(SupplyChainScanner.download_risk, "float")

    def test_freshness_risk_signature(self):
        """freshness_risk(released_at) -> float."""
        sig = inspect.signature(SupplyChainScanner.freshness_risk)
        assert list(sig.parameters) == ["self", "released_at"]
        _assert_annotation(SupplyChainScanner.freshness_risk, "float")

    def test_scan_signature(self):
        """scan(package, info) -> SupplyChainVerdict."""
        sig = inspect.signature(SupplyChainScanner.scan)
        assert list(sig.parameters) == ["self", "package", "info"]
        _assert_annotation(SupplyChainScanner.scan, "SupplyChainVerdict")

    def test_scan_many_signature(self):
        """scan_many(packages) -> list[SupplyChainVerdict]."""
        sig = inspect.signature(SupplyChainScanner.scan_many)
        assert list(sig.parameters) == ["self", "packages"]
        _assert_annotation(SupplyChainScanner.scan_many, "list[SupplyChainVerdict]")


class TestSupplyChainAlerterInterface:
    """Verify SupplyChainAlerter exists with the expected interface."""

    def test_import(self):
        """SupplyChainAlerter can be imported."""
        assert isinstance(SupplyChainAlerter, type)

    def test_init_signature(self):
        """__init__ accepts db and webhook_url (webhook_url defaults to None)."""
        sig = inspect.signature(SupplyChainAlerter.__init__)
        params = sig.parameters
        assert "db" in params
        assert "webhook_url" in params
        assert params["webhook_url"].default is None

    def test_attrs_stored(self):
        """db and webhook_url are stored on the instance."""
        alerter = SupplyChainAlerter(
            db="fake_session",  # type: ignore[arg-type]
            webhook_url="https://hooks.example.com/supply-chain",
        )
        assert alerter.db == "fake_session"
        assert alerter.webhook_url == "https://hooks.example.com/supply-chain"

    def test_has_notify_method(self):
        """notify_new_suspicious is an async method."""
        assert hasattr(SupplyChainAlerter, "notify_new_suspicious")
        assert inspect.iscoroutinefunction(SupplyChainAlerter.notify_new_suspicious)

    def test_notify_signature(self):
        """notify_new_suspicious(verdict) -> bool."""
        sig = inspect.signature(SupplyChainAlerter.notify_new_suspicious)
        assert list(sig.parameters) == ["self", "verdict"]
        _assert_annotation(SupplyChainAlerter.notify_new_suspicious, "bool")


class TestPersistenceInterface:
    """Verify store_verdict / list_verdicts module functions."""

    def test_store_verdict_callable(self):
        """store_verdict is a callable module function."""
        assert callable(store_verdict)

    def test_list_verdicts_callable(self):
        """list_verdicts is a callable module function."""
        assert callable(list_verdicts)

    def test_store_verdict_signature(self):
        """store_verdict(db, verdict) -> None."""
        sig = inspect.signature(store_verdict)
        assert list(sig.parameters) == ["db", "verdict"]
        _assert_annotation(store_verdict, "None")

    def test_list_verdicts_signature(self):
        """list_verdicts(db) -> list[SupplyChainVerdict]."""
        sig = inspect.signature(list_verdicts)
        assert list(sig.parameters) == ["db"]
        _assert_annotation(list_verdicts, "list[SupplyChainVerdict]")


class TestVerdictModelInterface:
    """Verify the SupplyChainVerdict ORM schema (real in the stub)."""

    def test_model_import(self):
        """SupplyChainVerdict can be imported."""
        assert isinstance(SupplyChainVerdict, type)

    def test_tablename(self):
        """Table name is supply_chain_verdicts."""
        assert SupplyChainVerdict.__tablename__ == "supply_chain_verdicts"

    def test_table_registered(self):
        """Table is registered on Base.metadata."""
        assert "supply_chain_verdicts" in Base.metadata.tables

    def test_columns(self):
        """Table has id, package, score, reasons, detected_at columns."""
        cols = {c.name for c in SupplyChainVerdict.__table__.columns}
        assert {"id", "package", "score", "reasons", "detected_at"} <= cols

    def test_annotations(self):
        """Model declares the expected fields."""
        for field_name in ("package", "score", "reasons", "detected_at"):
            assert field_name in SupplyChainVerdict.__annotations__


# ---------------------------------------------------------------------------
# Behavioral tests — fail with NotImplementedError until implemented
# ---------------------------------------------------------------------------


class TestSimilarityEngineBehavioral:
    """Similarity engine: distances, heuristics, configurable threshold."""

    def test_levenshtein_typosquat_distance(self):
        """Levenshtein distance between typosquat pairs is small."""
        engine = SimilarityEngine()
        assert engine.levenshtein_distance("requests", "requets") == 1
        assert engine.levenshtein_distance("numpy", "numpy1") == 1

    def test_levenshtein_unrelated_distance(self):
        """Levenshtein distance between unrelated names is large."""
        engine = SimilarityEngine()
        assert engine.levenshtein_distance("requests", "flask") > 3
        assert engine.levenshtein_distance("numpy", "pandas") > 3

    def test_damerau_transposition(self):
        """Damerau-Levenshtein counts transpositions as a single edit."""
        engine = SimilarityEngine()
        assert engine.damerau_levenshtein_distance("abc", "acb") == 1
        assert engine.damerau_levenshtein_distance("requests", "requets") == 1

    def test_prefix_similarity_ordering(self):
        """Shared prefix raises prefix_similarity."""
        engine = SimilarityEngine()
        assert engine.prefix_similarity("requests", "requets") > engine.prefix_similarity(
            "requests", "flask"
        )

    def test_suffix_similarity_ordering(self):
        """Shared suffix raises suffix_similarity."""
        engine = SimilarityEngine()
        assert engine.suffix_similarity("requests", "requets") > engine.suffix_similarity(
            "requests", "flask"
        )

    def test_similarity_scores_in_range(self):
        """similarity returns values in [0.0, 1.0]."""
        engine = SimilarityEngine()
        for a, b in (("requests", "requets"), ("requests", "flask"), ("numpy", "numpy1")):
            score = engine.similarity(a, b)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_similarity_typosquat_outranks_unrelated(self):
        """Typosquat pairs score higher than unrelated pairs."""
        engine = SimilarityEngine()
        assert engine.similarity("requests", "requets") > engine.similarity(
            "requests", "flask"
        )

    @pytest.mark.parametrize(
        "candidate, known, expected",
        [
            ("requests", "requets", True),
            ("numpy", "numpy1", True),
            ("django", "djang0", True),
            ("flask", "flask", True),
            ("requests", "flask", False),
            ("numpy", "pandas", False),
            ("requests", "tornado", False),
        ],
    )
    def test_is_similar_default_threshold(self, candidate, known, expected):
        """is_similar flags typosquats and ignores unrelated names."""
        engine = SimilarityEngine()
        assert engine.is_similar(candidate, known) is expected

    def test_threshold_is_configurable(self):
        """A stricter threshold rejects borderline typosquats."""
        lenient = SimilarityEngine(threshold=0.4)
        strict = SimilarityEngine(threshold=0.99)
        assert lenient.is_similar("requests", "requets") is True
        assert strict.is_similar("requests", "requets") is False


class TestMaliciousFeedBehavioral:
    """Feed integration: OSV entries + blocklist loaded, refreshed, used."""

    def test_load_populates_blocklist(self):
        """load() makes blocklisted names known-malicious."""
        feed = MaliciousFeed(blocklist=["evil-tool"])
        feed.load()
        assert feed.is_known_malicious("evil-tool") is True
        assert feed.is_known_malicious("requests") is False

    def test_load_populates_osv_entries(self):
        """load() makes OSV entry packages known-malicious."""
        feed = MaliciousFeed(osv_entries=[{"package": "requets"}, {"package": "numpy1"}])
        feed.load()
        assert feed.is_known_malicious("requets") is True
        assert feed.is_known_malicious("numpy1") is True

    def test_known_packages_lists_all(self):
        """known_packages() returns blocklist + OSV package names."""
        feed = MaliciousFeed(
            osv_entries=[{"package": "requets"}], blocklist=["evil-tool"]
        )
        feed.load()
        known = feed.known_packages()
        assert "evil-tool" in known
        assert "requets" in known

    def test_refresh_updates_feed_data(self):
        """refresh() picks up new entries so a fresh scan sees them."""
        feed = MaliciousFeed(osv_entries=[], blocklist=["evil-tool"])
        feed.load()
        feed.osv_entries.append({"package": "requets"})
        feed.refresh()
        assert feed.is_known_malicious("requets") is True

    def test_feed_used_during_scan(self):
        """Scanner uses feed data: similar-to-known names score higher."""
        feed = MaliciousFeed(osv_entries=[{"package": "requests"}, {"package": "numpy"}])
        scanner = SupplyChainScanner(feed=feed)
        suspicious = scanner.scan(
            "requets",
            PackageInfo(name="requets", downloads=5, released_at=datetime.now(UTC)),
        )
        benign = scanner.scan(
            "flask",
            PackageInfo(
                name="flask",
                downloads=10**7,
                released_at=datetime.now(UTC) - timedelta(days=3650),
            ),
        )
        assert suspicious.score > benign.score

    def test_scan_known_malicious_scores_higher(self):
        """Blocklisted packages score higher than unrelated packages."""
        feed = MaliciousFeed(blocklist=["evil-tool"])
        scanner = SupplyChainScanner(feed=feed)
        evil = scanner.scan("evil-tool", PackageInfo(name="evil-tool"))
        safe = scanner.scan(
            "flask",
            PackageInfo(name="flask", downloads=10**7),
        )
        assert evil.score > safe.score


class TestSupplyChainScannerBehavioral:
    """Download-count and release-freshness heuristics."""

    def test_download_risk_low_downloads_high(self):
        """Low download counts produce higher risk."""
        scanner = SupplyChainScanner()
        low = scanner.download_risk(0)
        high = scanner.download_risk(10**6)
        assert isinstance(low, float)
        assert 0.0 <= low <= 1.0
        assert low > high

    def test_freshness_risk_recent_publish_high(self):
        """Recently published packages produce higher risk."""
        scanner = SupplyChainScanner()
        recent = scanner.freshness_risk(datetime.now(UTC))
        old = scanner.freshness_risk(datetime.now(UTC) - timedelta(days=3650))
        assert isinstance(recent, float)
        assert 0.0 <= recent <= 1.0
        assert recent > old

    def test_scan_returns_verdict(self):
        """scan() returns a SupplyChainVerdict with score and reasons."""
        scanner = SupplyChainScanner()
        verdict = scanner.scan("requests", PackageInfo(name="requests"))
        assert isinstance(verdict, SupplyChainVerdict)
        assert verdict.package == "requests"
        assert isinstance(verdict.score, int)
        assert 0 <= verdict.score <= 100
        assert isinstance(verdict.reasons, list)

    def test_scan_suspicious_scores_higher_than_benign(self):
        """Low-download + recent + similar scores higher than the reverse."""
        scanner = SupplyChainScanner(
            feed=MaliciousFeed(osv_entries=[{"package": "requests"}])
        )
        suspicious = scanner.scan(
            "requets",
            PackageInfo(name="requets", downloads=3, released_at=datetime.now(UTC)),
        )
        benign = scanner.scan(
            "flask",
            PackageInfo(
                name="flask",
                downloads=10**7,
                released_at=datetime.now(UTC) - timedelta(days=3650),
            ),
        )
        assert suspicious.score > benign.score

    def test_scan_many_returns_per_package_verdicts(self):
        """scan_many() returns one verdict per package."""
        scanner = SupplyChainScanner()
        verdicts = scanner.scan_many(["requests", "numpy"])
        assert isinstance(verdicts, list)
        assert len(verdicts) == 2
        for verdict in verdicts:
            assert isinstance(verdict, SupplyChainVerdict)
            assert verdict.package in ("requests", "numpy")
            assert 0 <= verdict.score <= 100


class TestSupplyChainAlerterBehavioral:
    """Alerts fire exactly once for newly detected suspicious packages."""

    @pytest.mark.anyio
    async def test_notify_fires_exactly_once(self):
        """A second notification for the same package is suppressed.

        With the webhook mocked to succeed, exactly one POST must be made
        for two notifications of the same suspicious package.
        """
        from unittest.mock import AsyncMock, patch

        import httpx

        request = httpx.Request("POST", "https://hooks.example.com/supply-chain")
        mock_response = httpx.Response(200, json={"status": "ok"}, request=request)
        mock_post = AsyncMock(return_value=mock_response)
        verdict = SupplyChainVerdict(
            package="requets",
            score=85,
            reasons='["name-similar to requests"]',
        )
        with patch("httpx.AsyncClient.post", new=mock_post):
            alerter = SupplyChainAlerter(
                db=None, webhook_url="https://hooks.example.com/supply-chain"
            )
            first = await alerter.notify_new_suspicious(verdict)
            second = await alerter.notify_new_suspicious(verdict)
        assert first is True
        assert second is False
        assert mock_post.await_count == 1

    @pytest.mark.anyio
    async def test_notify_posts_webhook_payload(self):
        """Notification POSTs the package in the webhook payload."""
        from unittest.mock import AsyncMock, patch

        import httpx

        request = httpx.Request("POST", "https://hooks.example.com/supply-chain")
        mock_response = httpx.Response(200, json={"status": "ok"}, request=request)
        mock_post = AsyncMock(return_value=mock_response)
        verdict = SupplyChainVerdict(
            package="numpy1",
            score=70,
            reasons='["name-similar to numpy"]',
        )
        with patch("httpx.AsyncClient.post", new=mock_post):
            alerter = SupplyChainAlerter(
                db=None, webhook_url="https://hooks.example.com/supply-chain"
            )
            result = await alerter.notify_new_suspicious(verdict)
            assert result is True
            mock_post.assert_awaited_once()
        payload = mock_post.call_args.kwargs.get("json")
        assert payload is not None
        assert payload.get("package") == "numpy1"


class TestPersistenceBehavioral:
    """Verdicts are stored in SQLite and can be read back."""

    def test_store_and_read_back_verdict(self, db_session):
        """A stored verdict is readable with all fields intact."""
        verdict = SupplyChainVerdict(
            package="requets",
            score=85,
            reasons='["name-similar to requests"]',
        )
        store_verdict(db_session, verdict)
        stored = list_verdicts(db_session)
        assert isinstance(stored, list)
        found = [v for v in stored if v.package == "requets"]
        assert len(found) == 1
        row = found[0]
        assert row.score == 85
        assert row.reasons is not None
        assert row.detected_at is not None

    def test_store_multiple_verdicts(self, db_session):
        """Multiple verdicts are stored and listed together."""
        store_verdict(
            db_session,
            SupplyChainVerdict(package="requets", score=85, reasons="[]"),
        )
        store_verdict(
            db_session,
            SupplyChainVerdict(package="numpy1", score=60, reasons="[]"),
        )
        stored = list_verdicts(db_session)
        packages = {v.package for v in stored}
        assert "requets" in packages
        assert "numpy1" in packages
