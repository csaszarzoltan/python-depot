"""Tests for PackageManagerDetector, EcosystemScanner, EcosystemStatsService."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """Load a test fixture file as string."""
    path = FIXTURES_DIR / name
    with open(path) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Interface tests
# ---------------------------------------------------------------------------


class TestPackageManagerDetectorInterface:
    """Verify PackageManagerDetector class exists with expected interface."""

    def test_detector_import(self):
        """PackageManagerDetector can be imported."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        assert PackageManagerDetector is not None
        assert isinstance(PackageManagerDetector, type)

    def test_detector_has_static_methods(self):
        """PackageManagerDetector has expected static detection methods."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        assert hasattr(PackageManagerDetector, "detect_from_pypi_json")
        assert hasattr(PackageManagerDetector, "detect_from_pyproject_toml")
        assert hasattr(PackageManagerDetector, "_extract_requires_dist_signals")
        assert hasattr(PackageManagerDetector, "_extract_project_urls_signals")
        assert hasattr(PackageManagerDetector, "_extract_classifier_signals")
        assert hasattr(PackageManagerDetector, "_parse_build_backend")
        assert hasattr(PackageManagerDetector, "_parse_tool_sections")
        assert hasattr(PackageManagerDetector, "_check_dynamic_deps")

    def test_detector_constants_defined(self):
        """PackageManagerDetector has expected manager constants."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        assert PackageManagerDetector.MANAGER_PIP == "pip"
        assert PackageManagerDetector.MANAGER_UV == "uv"
        assert PackageManagerDetector.MANAGER_POETRY == "poetry"
        assert PackageManagerDetector.MANAGER_PIP_TOOLS == "pip-tools"
        assert PackageManagerDetector.BUILDBACKEND_POETRY == "poetry.core.masonry.api"
        assert PackageManagerDetector.BUILDBACKEND_SETUPTOOLS == "setuptools.build_meta"

    def test_ecosystem_scanner_import(self):
        """EcosystemScanner can be imported."""
        from python_depot.ecosystem.scanner import EcosystemScanner

        assert EcosystemScanner is not None
        assert isinstance(EcosystemScanner, type)


# ---------------------------------------------------------------------------
# Behavioral tests — Tier 1 detection (PyPI JSON analysis)
# ---------------------------------------------------------------------------


class TestTier1Detection:
    """PackageManagerDetector Tier 1 — PyPI JSON signal extraction."""

    @pytest.mark.anyio
    async def test_detect_pip_only_from_pypi_json(self):
        """Pip-only package (setuptools backend) returns including ['pip']."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        pypi_data = json.loads(load_fixture("pypi_json_pip_only.json"))
        result = PackageManagerDetector.detect_from_pypi_json(pypi_data)
        assert isinstance(result, dict)
        assert "managers_supported" in result
        assert isinstance(result["managers_supported"], list)
        assert result["detection_tier"] == 1
        assert "pip" in result["managers_supported"]

    @pytest.mark.anyio
    async def test_detect_poetry_from_pypi_json(self):
        """Poetry-related package returns including ['poetry']."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        pypi_data = json.loads(load_fixture("pypi_json_poetry.json"))
        result = PackageManagerDetector.detect_from_pypi_json(pypi_data)
        assert isinstance(result, dict)
        assert "managers_supported" in result
        assert "poetry" in result["managers_supported"]

    @pytest.mark.anyio
    async def test_detect_uv_from_project_urls(self):
        """Package with uv references in project_urls returns ['uv']."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        pypi_data = json.loads(load_fixture("pypi_json_pip_only.json"))
        # Add uv signal to project_urls
        pypi_data["info"]["project_urls"]["uv"] = "https://github.com/astral-sh/uv"
        result = PackageManagerDetector.detect_from_pypi_json(pypi_data)
        assert isinstance(result, dict)
        assert "uv" in result["managers_supported"]

    @pytest.mark.anyio
    async def test_detect_no_signals_falls_back_to_pip(self):
        """Package with no PM signals defaults to ['pip']."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        minimal_json = {
            "info": {
                "name": "minimal",
                "version": "0.0.1",
                "requires_dist": None,
                "project_urls": None,
                "classifiers": None,
            }
        }
        result = PackageManagerDetector.detect_from_pypi_json(minimal_json)
        assert isinstance(result, dict)
        assert result["managers_supported"] == ["pip"]
        assert result["detection_tier"] == 1

    @pytest.mark.anyio
    async def test_detect_requires_dist_analysis(self):
        """_extract_requires_dist_signals detects build tools from requires_dist."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        requires = ["poetry-core>=1.5.0", "requests>=2.0.0"]
        result = PackageManagerDetector._extract_requires_dist_signals(requires)
        assert isinstance(result, list)
        assert any("poetry-core" in s.lower() for s in result)

    @pytest.mark.anyio
    async def test_detect_requires_dist_none(self):
        """_extract_requires_dist_signals returns empty list for None input."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        result = PackageManagerDetector._extract_requires_dist_signals(None)
        assert result == []


# ---------------------------------------------------------------------------
# Behavioral tests — Tier 2 detection (pyproject.toml parsing)
# ---------------------------------------------------------------------------


class TestTier2Detection:
    """PackageManagerDetector Tier 2 — pyproject.toml signal extraction."""

    @pytest.mark.anyio
    async def test_parse_setuptools_pyproject(self):
        """Setuptools pyproject.toml returns setuptools build-backend and pip."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        toml_content = load_fixture("pyproject_toml_setuptools.toml")
        result = PackageManagerDetector.detect_from_pyproject_toml(toml_content)
        assert isinstance(result, dict)
        assert "managers_supported" in result
        assert "pip" in result["managers_supported"]
        assert result["build_backend"] == "setuptools.build_meta"

    @pytest.mark.anyio
    async def test_parse_poetry_pyproject(self):
        """Poetry pyproject.toml returns poetry-core build-backend and poetry."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        toml_content = load_fixture("pyproject_toml_poetry.toml")
        result = PackageManagerDetector.detect_from_pyproject_toml(toml_content)
        assert isinstance(result, dict)
        assert "poetry" in result["managers_supported"]
        assert result["build_backend"] == "poetry.core.masonry.api"

    @pytest.mark.anyio
    async def test_parse_uv_pyproject(self):
        """UV pyproject.toml returns setuptools build-backend and uv."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        toml_content = load_fixture("pyproject_toml_uv.toml")
        result = PackageManagerDetector.detect_from_pyproject_toml(toml_content)
        assert isinstance(result, dict)
        assert "uv" in result["managers_supported"]
        assert result["has_pyproject_toml"] is True

    @pytest.mark.anyio
    async def test_parse_pip_tools_pyproject(self):
        """Pip-tools pyproject.toml returns pip and pip-tools."""
        from python_depot.ecosystem.detector import PackageManagerDetector

        toml_content = load_fixture("pyproject_toml_pip_tools.toml")
        result = PackageManagerDetector.detect_from_pyproject_toml(toml_content)
        assert isinstance(result, dict)
        assert "pip-tools" in result["managers_supported"]

    @pytest.mark.anyio
    async def test_parse_build_backend(self):
        """_parse_build_backend extracts correct backend from parsed TOML."""
        import tomllib

        from python_depot.ecosystem.detector import PackageManagerDetector

        toml_data = tomllib.loads(load_fixture("pyproject_toml_setuptools.toml"))
        backend = PackageManagerDetector._parse_build_backend(toml_data)
        assert backend == "setuptools.build_meta"


# ---------------------------------------------------------------------------
# Behavioral tests — EcosystemScanner
# ---------------------------------------------------------------------------


class TestEcosystemScanner:
    """EcosystemScanner.scan_package behavior."""

    @pytest.mark.anyio
    async def test_scan_nonexistent_package_handles_gracefully(self):
        """scan_package with nonexistent package returns error state."""
        from python_depot.ecosystem.scanner import EcosystemScanner

        scanner = EcosystemScanner(db=None)
        result = await scanner.scan_package("nonexistent-pkg-xyz-12345")
        assert isinstance(result, dict)
        assert "package" in result
        assert result["package"] == "nonexistent-pkg-xyz-12345"
        assert result["detection_tier"] == 0  # not found

    @pytest.mark.anyio
    async def test_scan_batch_returns_list(self):
        """scan_batch returns a list of scan results."""
        from python_depot.ecosystem.scanner import EcosystemScanner

        scanner = EcosystemScanner(db=None)
        packages = ["nonexistent-aaa", "nonexistent-bbb", "nonexistent-ccc"]
        results = await scanner.scan_batch(packages, tier_1_only=True)
        assert isinstance(results, list)
        assert len(results) == 3
        for r in results:
            assert "package" in r
            assert "managers_supported" in r


# ---------------------------------------------------------------------------
# Behavioral tests — EcosystemStatsService
# ---------------------------------------------------------------------------


class TestEcosystemStatsService:
    """EcosystemStatsService aggregation queries."""

    @pytest.mark.anyio
    async def test_compute_stats_returns_empty_when_no_db(self):
        """compute_stats returns empty stats when no DB."""
        from python_depot.ecosystem.stats import EcosystemStatsService

        service = EcosystemStatsService(db=None)
        result = service.compute_stats()
        assert isinstance(result, dict)
        assert "total_packages_scanned" in result
        assert result["total_packages_scanned"] == 0
        assert "adoption_rates" in result
        rates = result["adoption_rates"]
        for key in ("pip_only", "uv_ready", "poetry_compatible", "pip_tools_compatible"):
            assert key in rates
            assert "count" in rates[key]
            assert "pct" in rates[key]

    @pytest.mark.anyio
    async def test_compute_stats_trending_migrations(self):
        """compute_stats includes trending_migrations list."""
        from python_depot.ecosystem.stats import EcosystemStatsService

        service = EcosystemStatsService(db=None)
        result = service.compute_stats()
        assert "trending_migrations" in result
        assert isinstance(result["trending_migrations"], list)
        if result["trending_migrations"]:
            entry = result["trending_migrations"][0]
            assert "from" in entry
            assert "to" in entry
            assert "estimated_packages" in entry

    @pytest.mark.anyio
    async def test_get_compatibility_matrix_returns_correct_structure(self):
        """get_compatibility_matrix returns paginated results."""
        from python_depot.ecosystem.stats import EcosystemStatsService

        service = EcosystemStatsService(db=None)
        result = service.get_compatibility_matrix(limit=50, offset=0)
        assert isinstance(result, dict)
        assert "packages" in result
        assert isinstance(result["packages"], list)
        assert "total" in result
        assert result["limit"] == 50
        assert result["offset"] == 0
