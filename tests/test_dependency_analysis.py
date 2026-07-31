"""Pre-dev tests for Dependency Analysis Engine (M1).

Interface tests — verify imports, signatures, types. Must pass immediately.
Behavioral tests — verify scanning and parsing. Must raise NotImplementedError.
"""

from __future__ import annotations

import enum
import inspect
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import get_type_hints

import pytest

# ──────────────────────────────────────────────────────────────────────
# Imports under test
# ──────────────────────────────────────────────────────────────────────
from python_depot_migrate.scanner import (
    DependencyFormat,
    DependencyScanner,
    ParsedDependency,
    ScanResult,
)

# =====================================================================
# SECTION 1 — INTERFACE TESTS (must pass immediately)
# =====================================================================


# --- 1A: Module & class existence ---


class TestModuleImports:
    """Verify the module loads and all public names are importable."""

    def test_import_dependency_format(self):
        assert DependencyFormat is not None

    def test_import_parsed_dependency(self):
        assert ParsedDependency is not None

    def test_import_scan_result(self):
        assert ScanResult is not None

    def test_import_dependency_scanner(self):
        assert DependencyScanner is not None


class TestDependencyFormatEnum:
    """DependencyFormat must be a proper Enum with expected members."""

    def test_is_enum_subclass(self):
        assert issubclass(DependencyFormat, enum.Enum)

    def test_has_requirements_txt(self):
        assert hasattr(DependencyFormat, "REQUIREMENTS_TXT")
        assert DependencyFormat.REQUIREMENTS_TXT.value == "requirements.txt"

    def test_has_requirements_in(self):
        assert hasattr(DependencyFormat, "REQUIREMENTS_IN")
        assert DependencyFormat.REQUIREMENTS_IN.value == "requirements.in"

    def test_has_pyproject_toml(self):
        assert hasattr(DependencyFormat, "PYPROJECT_TOML")
        assert DependencyFormat.PYPROJECT_TOML.value == "pyproject.toml"

    def test_has_pipfile(self):
        assert hasattr(DependencyFormat, "PIPFILE")
        assert DependencyFormat.PIPFILE.value == "Pipfile"

    def test_has_setup_py(self):
        assert hasattr(DependencyFormat, "SETUP_PY")
        assert DependencyFormat.SETUP_PY.value == "setup.py"

    def test_has_setup_cfg(self):
        assert hasattr(DependencyFormat, "SETUP_CFG")
        assert DependencyFormat.SETUP_CFG.value == "setup.cfg"

    def test_enum_member_count(self):
        assert len(DependencyFormat) == 6


# --- 1B: Dataclass existence & fields ---


class TestParsedDependencyDataclass:
    """ParsedDependency must be a dataclass with expected fields."""

    def test_is_dataclass(self):
        assert is_dataclass(ParsedDependency)

    def test_has_name_field(self):
        assert "name" in {f.name for f in fields(ParsedDependency)}

    def test_has_version_constraint_field(self):
        assert "version_constraint" in {f.name for f in fields(ParsedDependency)}

    def test_has_source_type_field(self):
        assert "source_type" in {f.name for f in fields(ParsedDependency)}

    def test_has_extras_field(self):
        assert "extras" in {f.name for f in fields(ParsedDependency)}

    def test_has_markers_field(self):
        assert "markers" in {f.name for f in fields(ParsedDependency)}

    def test_has_is_dev_field(self):
        assert "is_dev" in {f.name for f in fields(ParsedDependency)}

    def test_field_count(self):
        assert len(fields(ParsedDependency)) == 6

    def test_default_source_type(self):
        dep = ParsedDependency(name="test")
        assert dep.source_type == "pypi"

    def test_default_extras_is_empty_list(self):
        dep = ParsedDependency(name="test")
        assert dep.extras == []

    def test_default_version_constraint_is_none(self):
        dep = ParsedDependency(name="test")
        assert dep.version_constraint is None

    def test_default_markers_is_none(self):
        dep = ParsedDependency(name="test")
        assert dep.markers is None

    def test_default_is_dev_is_false(self):
        dep = ParsedDependency(name="test")
        assert dep.is_dev is False

    def test_construction_with_all_fields(self):
        dep = ParsedDependency(
            name="requests",
            version_constraint=">=2.28",
            source_type="pypi",
            extras=["security"],
            markers='sys_platform == "win32"',
            is_dev=True,
        )
        assert dep.name == "requests"
        assert dep.version_constraint == ">=2.28"
        assert dep.extras == ["security"]
        assert dep.is_dev is True

    def test_construction_with_no_optional_fields(self):
        dep = ParsedDependency(name="click")
        assert dep.name == "click"
        assert dep.version_constraint is None
        assert dep.source_type == "pypi"
        assert dep.extras == []
        assert dep.markers is None
        assert dep.is_dev is False


class TestScanResultDataclass:
    """ScanResult must be a dataclass with expected fields."""

    def test_is_dataclass(self):
        assert is_dataclass(ScanResult)

    def test_has_source_format_field(self):
        assert "source_format" in {f.name for f in fields(ScanResult)}

    def test_has_dependencies_field(self):
        assert "dependencies" in {f.name for f in fields(ScanResult)}

    def test_has_dev_dependencies_field(self):
        assert "dev_dependencies" in {f.name for f in fields(ScanResult)}

    def test_has_extras_field(self):
        assert "extras" in {f.name for f in fields(ScanResult)}

    def test_has_metadata_field(self):
        assert "metadata" in {f.name for f in fields(ScanResult)}

    def test_field_count(self):
        assert len(fields(ScanResult)) == 5

    def test_default_dependencies_is_empty_list(self):
        result = ScanResult(source_format=DependencyFormat.REQUIREMENTS_TXT)
        assert result.dependencies == []

    def test_default_dev_dependencies_is_empty_list(self):
        result = ScanResult(source_format=DependencyFormat.REQUIREMENTS_TXT)
        assert result.dev_dependencies == []

    def test_default_extras_is_empty_dict(self):
        result = ScanResult(source_format=DependencyFormat.REQUIREMENTS_TXT)
        assert result.extras == {}

    def test_default_metadata_is_empty_dict(self):
        result = ScanResult(source_format=DependencyFormat.REQUIREMENTS_TXT)
        assert result.metadata == {}

    def test_construction_with_all_fields(self):
        dep = ParsedDependency(name="flask")
        result = ScanResult(
            source_format=DependencyFormat.PYPROJECT_TOML,
            dependencies=[dep],
            dev_dependencies=[],
            extras={"dev": ["pytest"]},
            metadata={"python_requires": ">=3.10"},
        )
        assert result.source_format == DependencyFormat.PYPROJECT_TOML
        assert len(result.dependencies) == 1
        assert result.metadata["python_requires"] == ">=3.10"


# --- 1C: DependencyScanner class & method signatures ---


class TestDependencyScannerClass:
    """DependencyScanner must exist as a class with scan() and detect_formats()."""

    def test_is_class(self):
        assert inspect.isclass(DependencyScanner)

    def test_has_scan_method(self):
        assert hasattr(DependencyScanner, "scan")
        assert callable(DependencyScanner.scan)

    def test_has_detect_formats_method(self):
        assert hasattr(DependencyScanner, "detect_formats")
        assert callable(DependencyScanner.detect_formats)

    def test_can_instantiate(self):
        scanner = DependencyScanner()
        assert scanner is not None

    def test_scan_signature_has_project_path(self):
        sig = inspect.signature(DependencyScanner.scan)
        assert "project_path" in sig.parameters

    def test_scan_project_path_type_hint(self):
        hints = get_type_hints(DependencyScanner.scan)
        assert hints.get("project_path") == Path

    def test_scan_return_type_hint(self):
        hints = get_type_hints(DependencyScanner.scan)
        assert hints.get("return") == ScanResult

    def test_detect_formats_signature_has_project_path(self):
        sig = inspect.signature(DependencyScanner.detect_formats)
        assert "project_path" in sig.parameters

    def test_detect_formats_project_path_type_hint(self):
        hints = get_type_hints(DependencyScanner.detect_formats)
        assert hints.get("project_path") == Path

    def test_detect_formats_return_type_hint(self):
        hints = get_type_hints(DependencyScanner.detect_formats)
        assert hints.get("return") == list[DependencyFormat]


# --- 1D: ParsedDependency type hints ---


class TestParsedDependencyTypeHints:
    """Verify type hints on ParsedDependency fields."""

    def test_name_is_str(self):
        hints = get_type_hints(ParsedDependency)
        assert hints["name"] is str

    def test_version_constraint_is_optional_str(self):
        hints = get_type_hints(ParsedDependency)
        assert hints["version_constraint"] == str | None

    def test_extras_is_list_of_str(self):
        hints = get_type_hints(ParsedDependency)
        assert hints["extras"] == list[str]

    def test_markers_is_optional_str(self):
        hints = get_type_hints(ParsedDependency)
        assert hints["markers"] == str | None

    def test_is_dev_is_bool(self):
        hints = get_type_hints(ParsedDependency)
        assert hints["is_dev"] is bool


# =====================================================================
# SECTION 2 — BEHAVIORAL TESTS (must raise NotImplementedError)
# =====================================================================


@pytest.fixture
def scanner():
    """Create a fresh DependencyScanner instance."""
    return DependencyScanner()


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project directory."""
    return tmp_path


@pytest.fixture
def requirements_txt_project(tmp_path: Path) -> Path:
    """Project with a requirements.txt."""
    req = tmp_path / "requirements.txt"
    req.write_text(
        "flask>=2.3\n"
        "requests==2.31.0\n"
        "pyyaml\n"
        "click[extra]\n"
    )
    return tmp_path


@pytest.fixture
def pyproject_toml_project(tmp_path: Path) -> Path:
    """Project with a pyproject.toml."""
    toml = tmp_path / "pyproject.toml"
    toml.write_text(
        '[project]\n'
        'name = "myapp"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = [\n'
        '    "flask>=2.3",\n'
        '    "requests==2.31.0",\n'
        ']\n'
        '\n'
        '[project.optional-dependencies]\n'
        'dev = ["pytest", "ruff"]\n'
    )
    return tmp_path


@pytest.fixture
def pipfile_project(tmp_path: Path) -> Path:
    """Project with a Pipfile."""
    pipfile = tmp_path / "Pipfile"
    pipfile.write_text(
        '[[source]]\n'
        'url = "https://pypi.org/simple"\n'
        'verify_ssl = true\n'
        'name = "pypi"\n'
        '\n'
        '[packages]\n'
        'flask = ">=2.3"\n'
        'requests = "==2.31.0"\n'
        '\n'
        '[dev-packages]\n'
        'pytest = "*"\n'
        'ruff = "*"\n'
    )
    return tmp_path


@pytest.fixture
def setup_py_project(tmp_path: Path) -> Path:
    """Project with a setup.py."""
    setup = tmp_path / "setup.py"
    setup.write_text(
        "from setuptools import setup\n"
        "\n"
        "setup(\n"
        '    name="myapp",\n'
        '    version="0.1.0",\n'
        '    install_requires=[\n'
        '        "flask>=2.3",\n'
        '        "requests==2.31.0",\n'
        '    ],\n'
        '    extras_require={\n'
        '        "dev": ["pytest", "ruff"],\n'
        '    },\n'
        ")\n"
    )
    return tmp_path


@pytest.fixture
def empty_requirements_project(tmp_path: Path) -> Path:
    """Project with an empty requirements.txt."""
    req = tmp_path / "requirements.txt"
    req.write_text("")
    return tmp_path


@pytest.fixture
def vcs_requirements_project(tmp_path: Path) -> Path:
    """Project with VCS dependencies in requirements.txt."""
    req = tmp_path / "requirements.txt"
    req.write_text(
        "git+https://github.com/pallets/flask.git@2.3.3\n"
        "git+ssh://git@github.com/myorg/private-lib.git\n"
        "flask>=2.3\n"
    )
    return tmp_path


@pytest.fixture
def editable_requirements_project(tmp_path: Path) -> Path:
    """Project with editable installs."""
    req = tmp_path / "requirements.txt"
    req.write_text(
        "-e .\n"
        "-e ./local-lib\n"
        "flask>=2.3\n"
    )
    return tmp_path


@pytest.fixture
def extras_markers_project(tmp_path: Path) -> Path:
    """Project with extras and platform markers."""
    req = tmp_path / "requirements.txt"
    req.write_text(
        'requests[security,socks]>=2.28\n'
        'pywin32>=227; sys_platform == "win32"\n'
        'uvloop>=0.17; sys_platform != "win32"\n'
    )
    return tmp_path


@pytest.fixture
def malformed_toml_project(tmp_path: Path) -> Path:
    """Project with malformed TOML."""
    toml = tmp_path / "pyproject.toml"
    toml.write_text("[project\nname = broken")
    return tmp_path


@pytest.fixture
def private_index_project(tmp_path: Path) -> Path:
    """Project with private index reference."""
    pipfile = tmp_path / "Pipfile"
    pipfile.write_text(
        '[[source]]\n'
        'url = "https://pypi.org/simple"\n'
        'verify_ssl = true\n'
        'name = "pypi"\n'
        '\n'
        '[[source]]\n'
        'url = "https://private.pypi.example.com/simple"\n'
        'verify_ssl = true\n'
        'name = "private"\n'
        '\n'
        '[packages]\n'
        'flask = {version = ">=2.3", index = "pypi"}\n'
        'internal-lib = {version = "*", index = "private"}\n'
    )
    return tmp_path


# --- 2A: detect_formats behavioral ---


class TestDetectFormatsBehavior:
    """detect_formats must detect which dependency files exist."""

    def test_raises_not_implemented(self, scanner, tmp_project):
        with pytest.raises(NotImplementedError):
            scanner.detect_formats(tmp_project)

    def test_requirements_txt_detected(self, scanner, requirements_txt_project):
        try:
            result = scanner.detect_formats(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert DependencyFormat.REQUIREMENTS_TXT in result

    def test_pyproject_toml_detected(self, scanner, pyproject_toml_project):
        try:
            result = scanner.detect_formats(pyproject_toml_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert DependencyFormat.PYPROJECT_TOML in result

    def test_pipfile_detected(self, scanner, pipfile_project):
        try:
            result = scanner.detect_formats(pipfile_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert DependencyFormat.PIPFILE in result

    def test_setup_py_detected(self, scanner, setup_py_project):
        try:
            result = scanner.detect_formats(setup_py_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert DependencyFormat.SETUP_PY in result

    def test_empty_dir_returns_empty(self, scanner, tmp_project):
        try:
            result = scanner.detect_formats(tmp_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == []

    def test_multiple_formats(self, scanner, requirements_txt_project):
        """When multiple formats exist, all should be detected."""
        (requirements_txt_project / "pyproject.toml").write_text(
            '[project]\nname = "test"\n'
        )
        try:
            result = scanner.detect_formats(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert DependencyFormat.REQUIREMENTS_TXT in result
        assert DependencyFormat.PYPROJECT_TOML in result


# --- 2B: scan behavioral — requirements.txt ---


class TestScanRequirementsTxt:
    """scan must parse requirements.txt into normalized ScanResult."""

    def test_raises_not_implemented(self, scanner, tmp_project):
        with pytest.raises(NotImplementedError):
            scanner.scan(tmp_project)

    def test_returns_scan_result(self, scanner, requirements_txt_project):
        try:
            result = scanner.scan(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, ScanResult)

    def test_source_format_is_requirements_txt(self, scanner, requirements_txt_project):
        try:
            result = scanner.scan(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.source_format == DependencyFormat.REQUIREMENTS_TXT

    def test_correct_dependency_count(self, scanner, requirements_txt_project):
        try:
            result = scanner.scan(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.dependencies) == 4

    def test_flask_parsed(self, scanner, requirements_txt_project):
        try:
            result = scanner.scan(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        flask = next(d for d in result.dependencies if d.name == "flask")
        assert flask.version_constraint == ">=2.3"

    def test_requests_parsed(self, scanner, requirements_txt_project):
        try:
            result = scanner.scan(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        req = next(d for d in result.dependencies if d.name == "requests")
        assert req.version_constraint == "==2.31.0"

    def test_pyyaml_no_version(self, scanner, requirements_txt_project):
        try:
            result = scanner.scan(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        yaml_dep = next(d for d in result.dependencies if d.name == "pyyaml")
        assert yaml_dep.version_constraint is None

    def test_click_has_extras(self, scanner, requirements_txt_project):
        try:
            result = scanner.scan(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        click = next(d for d in result.dependencies if d.name == "click")
        assert "extra" in click.extras

    def test_all_pypi_source_type(self, scanner, requirements_txt_project):
        try:
            result = scanner.scan(requirements_txt_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        for dep in result.dependencies:
            assert dep.source_type == "pypi"


# --- 2C: scan behavioral — pyproject.toml ---


class TestScanPyprojectToml:
    """scan must parse pyproject.toml dependencies."""

    def test_returns_scan_result(self, scanner, pyproject_toml_project):
        try:
            result = scanner.scan(pyproject_toml_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, ScanResult)
        assert result.source_format == DependencyFormat.PYPROJECT_TOML

    def test_dependency_count(self, scanner, pyproject_toml_project):
        try:
            result = scanner.scan(pyproject_toml_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.dependencies) == 2

    def test_dev_dependencies_extracted(self, scanner, pyproject_toml_project):
        try:
            result = scanner.scan(pyproject_toml_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.dev_dependencies) == 2
        dev_names = {d.name for d in result.dev_dependencies}
        assert "pytest" in dev_names
        assert "ruff" in dev_names

    def test_extras_extracted(self, scanner, pyproject_toml_project):
        try:
            result = scanner.scan(pyproject_toml_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "dev" in result.extras

    def test_python_requires_in_metadata(self, scanner, pyproject_toml_project):
        try:
            result = scanner.scan(pyproject_toml_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.metadata.get("python_requires") == ">=3.10"


# --- 2D: scan behavioral — Pipfile ---


class TestScanPipfile:
    """scan must parse Pipfile packages and dev-packages."""

    def test_returns_scan_result(self, scanner, pipfile_project):
        try:
            result = scanner.scan(pipfile_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, ScanResult)
        assert result.source_format == DependencyFormat.PIPFILE

    def test_packages_count(self, scanner, pipfile_project):
        try:
            result = scanner.scan(pipfile_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.dependencies) == 2

    def test_dev_packages_count(self, scanner, pipfile_project):
        try:
            result = scanner.scan(pipfile_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.dev_dependencies) == 2

    def test_source_index_in_metadata(self, scanner, private_index_project):
        try:
            result = scanner.scan(private_index_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "sources" in result.metadata


# --- 2E: scan behavioral — setup.py ---


class TestScanSetupPy:
    """scan must parse setup.py install_requires and extras_require."""

    def test_returns_scan_result(self, scanner, setup_py_project):
        try:
            result = scanner.scan(setup_py_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, ScanResult)
        assert result.source_format == DependencyFormat.SETUP_PY

    def test_install_requires_count(self, scanner, setup_py_project):
        try:
            result = scanner.scan(setup_py_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.dependencies) == 2

    def test_extras_require_extracted(self, scanner, setup_py_project):
        try:
            result = scanner.scan(setup_py_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "dev" in result.extras


# --- 2F: Edge cases ---


class TestEmptyRequirements:
    """Empty requirements file should return ScanResult with no deps."""

    def test_empty_file_returns_empty_deps(self, scanner, empty_requirements_project):
        try:
            result = scanner.scan(empty_requirements_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, ScanResult)
        assert result.dependencies == []
        assert result.dev_dependencies == []


class TestVCSDependencies:
    """VCS deps (git+https, git+ssh) must be detected as git source_type."""

    def test_git_https_parsed(self, scanner, vcs_requirements_project):
        try:
            result = scanner.scan(vcs_requirements_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        git_deps = [d for d in result.dependencies if d.source_type == "git"]
        assert len(git_deps) >= 2

    def test_git_url_preserved(self, scanner, vcs_requirements_project):
        try:
            result = scanner.scan(vcs_requirements_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        git_dep = next(d for d in result.dependencies if d.source_type == "git")
        assert "github.com" in git_dep.name or "github.com" in (git_dep.version_constraint or "")

    def test_regular_dep_also_parsed(self, scanner, vcs_requirements_project):
        try:
            result = scanner.scan(vcs_requirements_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        flask = next(d for d in result.dependencies if d.name == "flask")
        assert flask.source_type == "pypi"


class TestEditableInstalls:
    """Editable installs (-e .) should not crash the scanner."""

    def test_editable_does_not_crash(self, scanner, editable_requirements_project):
        try:
            result = scanner.scan(editable_requirements_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, ScanResult)

    def test_editable_dep_present(self, scanner, editable_requirements_project):
        try:
            result = scanner.scan(editable_requirements_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        path_deps = [d for d in result.dependencies if d.source_type == "path"]
        assert len(path_deps) >= 1

    def test_regular_dep_also_present(self, scanner, editable_requirements_project):
        try:
            result = scanner.scan(editable_requirements_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        flask = next(d for d in result.dependencies if d.name == "flask")
        assert flask.source_type == "pypi"


class TestExtrasAndMarkers:
    """Extras [security,socks] and platform markers must be parsed."""

    def test_extras_parsed(self, scanner, extras_markers_project):
        try:
            result = scanner.scan(extras_markers_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        req = next(d for d in result.dependencies if d.name == "requests")
        assert "security" in req.extras
        assert "socks" in req.extras

    def test_markers_parsed(self, scanner, extras_markers_project):
        try:
            result = scanner.scan(extras_markers_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        pywin32 = next(d for d in result.dependencies if d.name == "pywin32")
        assert pywin32.markers is not None
        assert "win32" in pywin32.markers

    def test_platform_specific_dep_count(self, scanner, extras_markers_project):
        try:
            result = scanner.scan(extras_markers_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.dependencies) == 3


class TestMalformedTOML:
    """Malformed TOML should not crash — return empty or raise descriptive error."""

    def test_does_not_crash(self, scanner, malformed_toml_project):
        try:
            result = scanner.scan(malformed_toml_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except Exception as e:
            # Acceptable: descriptive parse error
            assert "toml" in str(e).lower() or "parse" in str(e).lower()
            return
        assert isinstance(result, ScanResult)

    def test_malformed_returns_empty_or_partial(self, scanner, malformed_toml_project):
        try:
            result = scanner.scan(malformed_toml_project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except Exception:
            pytest.skip("Scanner raises on malformed input — acceptable")
        assert len(result.dependencies) == 0


# --- 2G: Parametrized tests across all formats ---


@pytest.mark.parametrize(
    "fixture_name",
    [
        "requirements_txt_project",
        "pyproject_toml_project",
        "pipfile_project",
        "setup_py_project",
    ],
)
class TestScanAllFormats:
    """Shared behavioral checks across all supported formats."""

    def test_returns_scan_result(self, scanner, fixture_name, request):
        project = request.getfixturevalue(fixture_name)
        try:
            result = scanner.scan(project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, ScanResult)
        assert isinstance(result.source_format, DependencyFormat)
        assert isinstance(result.dependencies, list)
        assert isinstance(result.dev_dependencies, list)
        assert isinstance(result.extras, dict)
        assert isinstance(result.metadata, dict)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "requirements_txt_project",
        "pyproject_toml_project",
        "pipfile_project",
        "setup_py_project",
    ],
)
class TestDetectFormatsAllFormats:
    """detect_formats returns a list for all supported formats."""

    def test_returns_list(self, scanner, fixture_name, request):
        project = request.getfixturevalue(fixture_name)
        try:
            result = scanner.detect_formats(project)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, list)
        assert all(isinstance(f, DependencyFormat) for f in result)


# =====================================================================
# SECTION 3: Test counts (self-documenting)
# =====================================================================
# Total tests: ~80+ (interface ~45, behavioral ~35)
# Interface tests: pass immediately
# Behavioral tests: raise NotImplementedError (RED phase)
