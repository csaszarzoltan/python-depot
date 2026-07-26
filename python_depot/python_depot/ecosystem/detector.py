"""Package manager detection from PyPI JSON metadata and pyproject.toml content.

Provides the `PackageManagerDetector` class with static methods for
identifying which package manager(s) a Python package supports.
"""
from __future__ import annotations

import re
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


class PackageManagerDetector:
    """Static methods to detect package manager compatibility.

    Detection is done in two tiers:
        Tier 1 — PyPI JSON metadata analysis (fast, no downloads)
        Tier 2 — pyproject.toml analysis (requires file content)
    """

    # Package manager identifiers
    MANAGER_PIP = "pip"
    MANAGER_UV = "uv"
    MANAGER_POETRY = "poetry"
    MANAGER_PIP_TOOLS = "pip-tools"

    # Known build-backend identifiers
    BUILDBACKEND_SETUPTOOLS = "setuptools.build_meta"
    BUILDBACKEND_POETRY = "poetry.core.masonry.api"
    BUILDBACKEND_FLIT = "flit_core.buildapi"
    BUILDBACKEND_PDM = "pdm.backend"
    BUILDBACKEND_HATCH = "hatchling.build"
    BUILDBACKEND_MESON = "mesonpy"

    # Signals in project_urls that indicate package manager usage
    _UV_URL_SIGNALS = re.compile(r"uv|astral", re.IGNORECASE)
    _POETRY_URL_SIGNALS = re.compile(r"poetry", re.IGNORECASE)
    _PIP_TOOLS_URL_SIGNALS = re.compile(r"pip.tools|pip-tools|requirements", re.IGNORECASE)

    # Build-backend → manager mapping
    _BUILDBACKEND_MAP: dict[str, str] = {
        BUILDBACKEND_SETUPTOOLS: MANAGER_PIP,
        BUILDBACKEND_POETRY: MANAGER_POETRY,
        BUILDBACKEND_FLIT: MANAGER_PIP,
        BUILDBACKEND_PDM: MANAGER_PIP,
        BUILDBACKEND_HATCH: MANAGER_PIP,
        BUILDBACKEND_MESON: MANAGER_PIP,
    }

    @classmethod
    def detect_from_pypi_json(cls, pypi_data: dict[str, Any]) -> dict[str, Any]:
        """Detect package manager(s) from a PyPI JSON API response (Tier 1).

        Args:
            pypi_data: The JSON-decoded response from ``https://pypi.org/pypi/<name>/json``.

        Returns:
            Dict with keys:
                - managers_supported: list[str] — detected managers
                - detection_tier: int (always 1)
                - signals: dict with per-signal breakdown
        """
        requires_dist = cls._extract_requires_dist_signals(pypi_data.get("info", {}).get("requires_dist"))
        url_signals = cls._extract_project_urls_signals(pypi_data.get("info", {}).get("project_urls"))
        classifier_signals = cls._extract_classifier_signals(pypi_data.get("info", {}).get("classifiers"))

        managers: set[str] = set()

        # Check requires_dist for poetry-core → poetry
        for item in requires_dist:
            if "poetry-core" in item.lower():
                managers.add(cls.MANAGER_POETRY)
            if "pdm" in item.lower() and "pdm.backend" in item.lower():
                managers.add(cls.MANAGER_PIP)

        # Check project_urls for tool references
        for signal in url_signals:
            if signal == "uv":
                managers.add(cls.MANAGER_UV)
            if signal == "poetry":
                managers.add(cls.MANAGER_POETRY)
            if signal == "pip-tools":
                managers.add(cls.MANAGER_PIP_TOOLS)

        # Check classifiers for build system hints
        for signal in classifier_signals:
            if signal == "poetry":
                managers.add(cls.MANAGER_POETRY)
            if signal == "uv":
                managers.add(cls.MANAGER_UV)

        # Always include pip as the universal fallback
        managers.add(cls.MANAGER_PIP)

        return {
            "managers_supported": sorted(managers),
            "detection_tier": 1,
            "signals": {
                "requires_dist_signals": requires_dist,
                "url_signals": url_signals,
                "classifier_signals": classifier_signals,
            },
        }

    @classmethod
    def detect_from_pyproject_toml(cls, toml_content: str) -> dict[str, Any]:
        """Detect package manager(s) from a pyproject.toml string (Tier 2).

        Args:
            toml_content: The raw content of a pyproject.toml file.

        Returns:
            Dict with keys:
                - managers_supported: list[str]
                - build_backend: str | None
                - has_pyproject_toml: bool (True)
                - has_tool_uv: bool
                - has_tool_poetry: bool
                - has_tool_pip_tools: bool
                - detection_tier: int (always 2)
        """
        data = tomllib.loads(toml_content)
        backend = cls._parse_build_backend(data)
        tool_sections = cls._parse_tool_sections(data)

        managers: set[str] = set()
        managers.add(cls.MANAGER_PIP)

        if tool_sections.get("has_tool_poetry"):
            managers.add(cls.MANAGER_POETRY)
        if tool_sections.get("has_tool_uv"):
            managers.add(cls.MANAGER_UV)
        if tool_sections.get("has_tool_pip_tools"):
            managers.add(cls.MANAGER_PIP_TOOLS)

        return {
            "managers_supported": sorted(managers),
            "build_backend": backend,
            "has_pyproject_toml": True,
            "has_tool_uv": tool_sections.get("has_tool_uv", False),
            "has_tool_poetry": tool_sections.get("has_tool_poetry", False),
            "has_tool_pip_tools": tool_sections.get("has_tool_pip_tools", False),
            "detection_tier": 2,
        }

    # ------------------------------------------------------------------
    # Internal helpers — kept as static methods for testability
    # ------------------------------------------------------------------

    @classmethod
    def _extract_requires_dist_signals(
        cls, requires_dist: list[str] | None
    ) -> list[str]:
        """Extract package manager signals from requires_dist.

        Returns a list of signal strings (e.g. ``["poetry-core>=1.5.0"]``).
        """
        if not requires_dist:
            return []
        signals: list[str] = []
        for dep in requires_dist:
            lower = dep.lower()
            if "poetry-core" in lower:
                signals.append(dep)
            if "pdm.backend" in lower:
                signals.append(dep)
        return signals

    @classmethod
    def _extract_project_urls_signals(
        cls, project_urls: dict[str, str] | None
    ) -> list[str]:
        """Extract package manager signals from project_urls.

        Returns a list of manager names detected (e.g. ``["uv"]``).
        """
        if not project_urls:
            return []
        signals: list[str] = []
        for key, value in project_urls.items():
            combined = f"{key} {value}"
            if cls._UV_URL_SIGNALS.search(combined):
                signals.append("uv")
            if cls._POETRY_URL_SIGNALS.search(combined):
                signals.append("poetry")
            if cls._PIP_TOOLS_URL_SIGNALS.search(combined):
                signals.append("pip-tools")
        return list(set(signals))

    @classmethod
    def _extract_classifier_signals(
        cls, classifiers: list[str] | None
    ) -> list[str]:
        """Extract package manager signals from Trove classifiers.

        Returns a list of manager names detected.
        """
        if not classifiers:
            return []
        signals: list[str] = []
        for cls_str in classifiers:
            lower = cls_str.lower()
            if "poetry" in lower and "build" in lower:
                signals.append("poetry")
            if "uv" in lower and "tool" in lower:
                signals.append("uv")
        return list(set(signals))

    @classmethod
    def _parse_build_backend(cls, toml_data: dict[str, Any]) -> str | None:
        """Extract the build-backend from parsed pyproject.toml data."""
        build_system = toml_data.get("build-system")
        if isinstance(build_system, dict):
            backend = build_system.get("build-backend")
            if isinstance(backend, str) and backend:
                return backend
        return None

    @classmethod
    def _parse_tool_sections(cls, toml_data: dict[str, Any]) -> dict[str, bool]:
        """Detect which tool sections are present in parsed TOML data."""
        tool = toml_data.get("tool")
        if not isinstance(tool, dict):
            return {
                "has_tool_uv": False,
                "has_tool_poetry": False,
                "has_tool_pip_tools": False,
            }
        return {
            "has_tool_uv": "uv" in tool,
            "has_tool_poetry": "poetry" in tool,
            "has_tool_pip_tools": "pip-tools" in tool,
        }

    @classmethod
    def _check_dynamic_deps(cls, toml_data: dict[str, Any]) -> list[str]:
        """Extract dynamic dependency list from pyproject.toml."""
        project = toml_data.get("project")
        if isinstance(project, dict):
            dynamic = project.get("dynamic")
            if isinstance(dynamic, list):
                return [str(d) for d in dynamic]
        return []
