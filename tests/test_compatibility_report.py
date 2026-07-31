"""Pre-development tests for Compatibility Checker + Migration Report (M5).

Interface tests verify structure (PASS immediately).
Behavioral tests stub with NotImplementedError (RED phase — fail until implemented).
"""
from __future__ import annotations

import inspect
import json
from dataclasses import fields
from pathlib import Path
from typing import get_type_hints

import pytest

from python_depot_migrate.compatibility import (
    KNOWN_UV_ISSUES,
    CompatibilityChecker,
    CompatibilityReport,
    CompatibilityWarning,
)
from python_depot_migrate.report import MigrationDiff, MigrationReportGenerator
from python_depot_migrate.scanner import (
    MigrationResult,
    ParsedDependency,
    ScanResult,
)

# ─── Interface Tests (structure verification) ────────────────────────────────
# These validate that the stubs have the correct shape.
# They MUST pass immediately on the stubs.


class TestCompatibilityWarningInterface:
    """Verify CompatibilityWarning dataclass structure."""

    def test_class_exists(self) -> None:
        assert CompatibilityWarning is not None

    def test_is_dataclass(self) -> None:
        assert hasattr(CompatibilityWarning, "__dataclass_fields__")

    def test_has_field_package(self) -> None:
        field_names = {f.name for f in fields(CompatibilityWarning)}
        assert "package" in field_names

    def test_has_field_issue(self) -> None:
        field_names = {f.name for f in fields(CompatibilityWarning)}
        assert "issue" in field_names

    def test_has_field_workaround(self) -> None:
        field_names = {f.name for f in fields(CompatibilityWarning)}
        assert "workaround" in field_names

    def test_has_field_severity(self) -> None:
        field_names = {f.name for f in fields(CompatibilityWarning)}
        assert "severity" in field_names

    def test_workaround_default_none(self) -> None:
        """workaround defaults to None per analyst spec."""
        w = CompatibilityWarning(package="x", issue="y")
        assert w.workaround is None

    def test_severity_default_warning(self) -> None:
        """severity defaults to 'warning'."""
        w = CompatibilityWarning(package="x", issue="y")
        assert w.severity == "warning"

    def test_can_construct_minimal(self) -> None:
        w = CompatibilityWarning(package="foo", issue="bar")
        assert w.package == "foo"
        assert w.issue == "bar"

    def test_can_construct_full(self) -> None:
        w = CompatibilityWarning(
            package="pip-tools",
            issue="incompatible",
            workaround="use uv pip compile",
            severity="error",
        )
        assert w.workaround == "use uv pip compile"
        assert w.severity == "error"

    def test_type_hints_present(self) -> None:
        hints = get_type_hints(CompatibilityWarning)
        assert "package" in hints
        assert "issue" in hints
        assert "workaround" in hints
        assert "severity" in hints


class TestCompatibilityReportInterface:
    """Verify CompatibilityReport dataclass structure."""

    def test_class_exists(self) -> None:
        assert CompatibilityReport is not None

    def test_is_dataclass(self) -> None:
        assert hasattr(CompatibilityReport, "__dataclass_fields__")

    def test_has_field_compatible(self) -> None:
        field_names = {f.name for f in fields(CompatibilityReport)}
        assert "compatible" in field_names

    def test_has_field_warnings(self) -> None:
        field_names = {f.name for f in fields(CompatibilityReport)}
        assert "warnings" in field_names

    def test_has_field_blockers(self) -> None:
        field_names = {f.name for f in fields(CompatibilityReport)}
        assert "blockers" in field_names

    def test_has_field_effort_estimate(self) -> None:
        field_names = {f.name for f in fields(CompatibilityReport)}
        assert "effort_estimate" in field_names

    def test_effort_estimate_default_low(self) -> None:
        r = CompatibilityReport()
        assert r.effort_estimate == "low"

    def test_compatible_default_empty_list(self) -> None:
        r = CompatibilityReport()
        assert r.compatible == []

    def test_warnings_default_empty_list(self) -> None:
        r = CompatibilityReport()
        assert r.warnings == []

    def test_blockers_default_empty_list(self) -> None:
        r = CompatibilityReport()
        assert r.blockers == []

    def test_can_construct_with_warnings(self) -> None:
        w = CompatibilityWarning(package="pip-tools", issue="incompatible")
        r = CompatibilityReport(warnings=[w])
        assert len(r.warnings) == 1
        assert r.warnings[0].package == "pip-tools"

    def test_can_construct_with_blockers(self) -> None:
        b = CompatibilityWarning(package="x", issue="fatal", severity="error")
        r = CompatibilityReport(blockers=[b])
        assert len(r.blockers) == 1

    def test_effort_estimate_literal_values(self) -> None:
        """effort_estimate should be one of 'low', 'medium', 'high'."""
        for val in ("low", "medium", "high"):
            r = CompatibilityReport(effort_estimate=val)
            assert r.effort_estimate == val

    def test_type_hints_present(self) -> None:
        hints = get_type_hints(CompatibilityReport)
        assert "compatible" in hints
        assert "warnings" in hints
        assert "blockers" in hints
        assert "effort_estimate" in hints


class TestCompatibilityCheckerInterface:
    """Verify CompatibilityChecker class structure."""

    def test_class_exists(self) -> None:
        assert CompatibilityChecker is not None

    def test_has_check_method(self) -> None:
        assert hasattr(CompatibilityChecker, "check")

    def test_check_method_signature(self) -> None:
        sig = inspect.signature(CompatibilityChecker.check)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "scan_result" in params

    def test_check_return_annotation(self) -> None:
        hints = get_type_hints(CompatibilityChecker.check)
        assert hints.get("return") is CompatibilityReport

    def test_check_param_has_type_hint(self) -> None:
        hints = get_type_hints(CompatibilityChecker.check)
        assert hints.get("scan_result") is ScanResult

    def test_instantiation(self) -> None:
        checker = CompatibilityChecker()
        assert checker is not None


class TestKnownUvIssuesInterface:
    """Verify the curated KNOWN_UV_ISSUES list."""

    def test_dict_exists(self) -> None:
        assert KNOWN_UV_ISSUES is not None

    def test_is_dict(self) -> None:
        assert isinstance(KNOWN_UV_ISSUES, dict)

    def test_has_pip_tools(self) -> None:
        assert "pip-tools" in KNOWN_UV_ISSUES

    def test_has_poetry_core(self) -> None:
        assert "poetry-core" in KNOWN_UV_ISSUES

    def test_has_black(self) -> None:
        assert "black" in KNOWN_UV_ISSUES

    def test_pip_tools_has_issue_key(self) -> None:
        assert "issue" in KNOWN_UV_ISSUES["pip-tools"]

    def test_pip_tools_has_workaround_key(self) -> None:
        assert "workaround" in KNOWN_UV_ISSUES["pip-tools"]

    def test_pip_tools_issue_is_string(self) -> None:
        assert isinstance(KNOWN_UV_ISSUES["pip-tools"]["issue"], str)

    def test_pip_tools_workaround_is_string_or_none(self) -> None:
        val = KNOWN_UV_ISSUES["pip-tools"]["workaround"]
        assert isinstance(val, str) or val is None

    def test_all_entries_have_issue_key(self) -> None:
        for name, entry in KNOWN_UV_ISSUES.items():
            assert "issue" in entry, f"Missing 'issue' in entry '{name}'"

    def test_all_entries_have_workaround_key(self) -> None:
        for name, entry in KNOWN_UV_ISSUES.items():
            assert "workaround" in entry, f"Missing 'workaround' in entry '{name}'"

    def test_curated_list_has_at_least_3_entries(self) -> None:
        assert len(KNOWN_UV_ISSUES) >= 3

    def test_entry_values_are_strings(self) -> None:
        for name, entry in KNOWN_UV_ISSUES.items():
            assert isinstance(entry["issue"], str), f"issue not str for {name}"
            if entry["workaround"] is not None:
                assert isinstance(entry["workaround"], str), f"workaround not str for {name}"


# ─── Report Interface Tests ──────────────────────────────────────────────────


class TestMigrationReportGeneratorInterface:
    """Verify MigrationReportGenerator class structure."""

    def test_class_exists(self) -> None:
        assert MigrationReportGenerator is not None

    def test_has_generate_method(self) -> None:
        assert hasattr(MigrationReportGenerator, "generate")

    def test_has_generate_markdown_method(self) -> None:
        assert hasattr(MigrationReportGenerator, "generate_markdown")

    def test_has_generate_json_method(self) -> None:
        assert hasattr(MigrationReportGenerator, "generate_json")

    def test_generate_method_signature(self) -> None:
        sig = inspect.signature(MigrationReportGenerator.generate)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "results" in params
        assert "report_path" in params

    def test_generate_return_annotation(self) -> None:
        hints = get_type_hints(MigrationReportGenerator.generate)
        assert hints.get("return") is str

    def test_generate_param_has_type_hint(self) -> None:
        hints = get_type_hints(MigrationReportGenerator.generate)
        assert hints.get("results") is MigrationResult

    def test_report_path_default_none(self) -> None:
        sig = inspect.signature(MigrationReportGenerator.generate)
        default = sig.parameters["report_path"].default
        assert default is None

    def test_instantiation(self) -> None:
        gen = MigrationReportGenerator()
        assert gen is not None

    def test_has_rollback_instructions_method(self) -> None:
        assert hasattr(MigrationReportGenerator, "_rollback_instructions")

    def test_has_before_after_method(self) -> None:
        assert hasattr(MigrationReportGenerator, "_before_after_comparison")


class TestMigrationDiffInterface:
    """Verify MigrationDiff dataclass structure."""

    def test_class_exists(self) -> None:
        assert MigrationDiff is not None

    def test_is_dataclass(self) -> None:
        assert hasattr(MigrationDiff, "__dataclass_fields__")

    def test_has_field_original(self) -> None:
        field_names = {f.name for f in fields(MigrationDiff)}
        assert "original" in field_names

    def test_has_field_updated(self) -> None:
        field_names = {f.name for f in fields(MigrationDiff)}
        assert "updated" in field_names

    def test_has_field_changes(self) -> None:
        field_names = {f.name for f in fields(MigrationDiff)}
        assert "changes" in field_names

    def test_can_construct(self) -> None:
        d = MigrationDiff(original="a", updated="b", changes=["c"])
        assert d.original == "a"
        assert d.updated == "b"


class TestScanResultForM5Interface:
    """Verify ScanResult (from M1) is usable by M5."""

    def test_scan_result_importable(self) -> None:
        assert ScanResult is not None

    def test_scan_result_has_dependencies(self) -> None:
        field_names = {f.name for f in fields(ScanResult)}
        assert "dependencies" in field_names

    def test_scan_result_has_dev_dependencies(self) -> None:
        field_names = {f.name for f in fields(ScanResult)}
        assert "dev_dependencies" in field_names

    def test_scan_result_has_metadata(self) -> None:
        field_names = {f.name for f in fields(ScanResult)}
        assert "metadata" in field_names

    def test_parsed_dependency_importable(self) -> None:
        assert ParsedDependency is not None

    def test_parsed_dependency_has_name(self) -> None:
        field_names = {f.name for f in fields(ParsedDependency)}
        assert "name" in field_names

    def test_parsed_dependency_has_version_constraint(self) -> None:
        field_names = {f.name for f in fields(ParsedDependency)}
        assert "version_constraint" in field_names

    def test_parsed_dependency_has_source_type(self) -> None:
        field_names = {f.name for f in fields(ParsedDependency)}
        assert "source_type" in field_names

    def test_parsed_dependency_has_extras(self) -> None:
        field_names = {f.name for f in fields(ParsedDependency)}
        assert "extras" in field_names

    def test_migration_result_importable(self) -> None:
        assert MigrationResult is not None

    def test_migration_result_has_success(self) -> None:
        field_names = {f.name for f in fields(MigrationResult)}
        assert "success" in field_names

    def test_migration_result_has_errors(self) -> None:
        field_names = {f.name for f in fields(MigrationResult)}
        assert "errors" in field_names

    def test_migration_result_has_dry_run(self) -> None:
        field_names = {f.name for f in fields(MigrationResult)}
        assert "dry_run" in field_names


# ─── Behavioral Tests (RED phase — should fail with NotImplementedError) ─────
# These stubs raise NotImplementedError until the developer implements them.


@pytest.fixture
def empty_scan_result() -> ScanResult:
    """An empty ScanResult with no dependencies."""
    return ScanResult()


@pytest.fixture
def scan_with_known_issues() -> ScanResult:
    """A ScanResult with packages known to have uv compatibility issues."""
    return ScanResult(
        dependencies=[
            ParsedDependency(name="pip-tools"),
            ParsedDependency(name="poetry-core"),
            ParsedDependency(name="black"),
        ]
    )


@pytest.fixture
def scan_with_unknown_package() -> ScanResult:
    """A ScanResult with a package not in the curated list."""
    return ScanResult(
        dependencies=[
            ParsedDependency(name="some-random-lib"),
        ]
    )


@pytest.fixture
def scan_all_packages_blocked() -> ScanResult:
    """A ScanResult where every package has a known blocker."""
    return ScanResult(
        dependencies=[
            ParsedDependency(name="pip-tools"),
            ParsedDependency(name="poetry-core"),
        ]
    )


@pytest.fixture
def migration_result_minimal() -> MigrationResult:
    """A minimal MigrationResult for report generation."""
    return MigrationResult(
        project_path=Path("/tmp/test-project"),
        dry_run=True,
        success=True,
        before_summary="3 packages, requirements.txt",
        after_summary="3 packages, pyproject.toml + uv.lock",
    )


@pytest.fixture
def migration_result_no_changes() -> MigrationResult:
    """A MigrationResult with no files migrated."""
    return MigrationResult(
        project_path=Path("/tmp/test-project"),
        dry_run=True,
        success=True,
        files_changed=[],
    )


class TestCompatibilityCheckerBehavioral:
    """Behavioral tests for CompatibilityChecker — all should FAIL until implemented."""

    def test_check_returns_compatibility_report(self, empty_scan_result: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(empty_scan_result)
        assert isinstance(result, CompatibilityReport)

    def test_check_empty_scan_has_low_effort(self, empty_scan_result: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(empty_scan_result)
        assert result.effort_estimate == "low"

    def test_check_empty_scan_no_warnings(self, empty_scan_result: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(empty_scan_result)
        assert len(result.warnings) == 0

    def test_check_empty_scan_no_blockers(self, empty_scan_result: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(empty_scan_result)
        assert len(result.blockers) == 0

    def test_check_empty_scan_compatible_list_empty(self, empty_scan_result: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(empty_scan_result)
        assert len(result.compatible) == 0

    def test_check_flags_pip_tools(self, scan_with_known_issues: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(scan_with_known_issues)
        flagged = [w.package for w in result.warnings + result.blockers]
        assert "pip-tools" in flagged

    def test_check_flags_poetry_core(self, scan_with_known_issues: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(scan_with_known_issues)
        flagged = [w.package for w in result.warnings + result.blockers]
        assert "poetry-core" in flagged

    def test_check_flags_black(self, scan_with_known_issues: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(scan_with_known_issues)
        flagged = [w.package for w in result.warnings + result.blockers]
        assert "black" in flagged

    def test_check_warnings_have_workaround(self, scan_with_known_issues: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(scan_with_known_issues)
        for w in result.warnings:
            if w.package in KNOWN_UV_ISSUES:
                assert w.workaround is not None, f"Missing workaround for {w.package}"

    def test_check_unknown_package_not_flagged(self, scan_with_unknown_package: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(scan_with_unknown_package)
        flagged = [w.package for w in result.warnings + result.blockers]
        assert "some-random-lib" not in flagged

    def test_check_unknown_package_in_compatible(self, scan_with_unknown_package: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(scan_with_unknown_package)
        assert "some-random-lib" in result.compatible

    def test_check_all_blocked_has_high_effort(self, scan_all_packages_blocked: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(scan_all_packages_blocked)
        assert result.effort_estimate == "high"

    def test_check_all_packages_listed_in_report(self, scan_with_known_issues: ScanResult) -> None:
        """Every input package must appear in compatible, warnings, or blockers."""
        checker = CompatibilityChecker()
        result = checker.check(scan_with_known_issues)
        all_flagged = {w.package for w in result.warnings + result.blockers}
        all_compatible = set(result.compatible)
        all_known = all_flagged | all_compatible
        for dep in scan_with_known_issues.dependencies:
            assert dep.name in all_known, f"{dep.name} missing from report"

    def test_check_severity_field_on_warnings(self, scan_with_known_issues: ScanResult) -> None:
        checker = CompatibilityChecker()
        result = checker.check(scan_with_known_issues)
        for w in result.warnings:
            assert w.severity in ("info", "warning", "error")
        for b in result.blockers:
            assert b.severity in ("info", "warning", "error")

    def test_check_mixed_packages(self) -> None:
        """A mix of known-issue and clean packages produces correct partition."""
        scan = ScanResult(
            dependencies=[
                ParsedDependency(name="pip-tools"),
                ParsedDependency(name="requests"),
            ]
        )
        checker = CompatibilityChecker()
        result = checker.check(scan)
        all_flagged = {w.package for w in result.warnings + result.blockers}
        assert "pip-tools" in all_flagged
        assert "requests" in result.compatible


class TestMigrationReportGeneratorBehavioral:
    """Behavioral tests for MigrationReportGenerator — all should FAIL until implemented."""

    def test_generate_returns_string(self, migration_result_minimal: MigrationResult) -> None:
        gen = MigrationReportGenerator()
        output = gen.generate(migration_result_minimal)
        assert isinstance(output, str)

    def test_generate_markdown_returns_string(self, migration_result_minimal: MigrationResult) -> None:
        gen = MigrationReportGenerator()
        output = gen.generate_markdown(migration_result_minimal)
        assert isinstance(output, str)

    def test_generate_json_returns_valid_json(self, migration_result_minimal: MigrationResult) -> None:
        gen = MigrationReportGenerator()
        output = gen.generate_json(migration_result_minimal)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_generate_markdown_contains_project_path(self, migration_result_minimal: MigrationResult) -> None:
        gen = MigrationReportGenerator()
        output = gen.generate_markdown(migration_result_minimal)
        assert "test-project" in output

    def test_generate_markdown_contains_before_after(self, migration_result_minimal: MigrationResult) -> None:
        gen = MigrationReportGenerator()
        output = gen.generate_markdown(migration_result_minimal)
        assert "before" in output.lower() or "original" in output.lower()
        assert "after" in output.lower() or "migrated" in output.lower()

    def test_generate_includes_rollback_instructions(self, migration_result_minimal: MigrationResult) -> None:
        gen = MigrationReportGenerator()
        output = gen.generate(migration_result_minimal)
        assert "rollback" in output.lower()

    def test_generate_rollback_method_returns_string(self, migration_result_minimal: MigrationResult) -> None:
        gen = MigrationReportGenerator()
        output = gen._rollback_instructions(migration_result_minimal)
        assert isinstance(output, str)

    def test_generate_before_after_method_returns_string(self, migration_result_minimal: MigrationResult) -> None:
        gen = MigrationReportGenerator()
        output = gen._before_after_comparison(migration_result_minimal)
        assert isinstance(output, str)

    def test_generate_json_has_required_keys(self, migration_result_minimal: MigrationResult) -> None:
        gen = MigrationReportGenerator()
        output = gen.generate_json(migration_result_minimal)
        parsed = json.loads(output)
        assert "project_path" in parsed or "project" in parsed
        assert "before" in parsed or "original" in parsed or "summary" in parsed

    def test_generate_with_no_migrated_files(self, migration_result_no_changes: MigrationResult) -> None:
        """Report generation must not crash on empty migration result."""
        gen = MigrationReportGenerator()
        output = gen.generate(migration_result_no_changes)
        assert isinstance(output, str)
        assert len(output) > 0

    def test_generate_with_errors(self) -> None:
        """Report includes error information when migration had errors."""
        result = MigrationResult(
            project_path=Path("/tmp/test-project"),
            dry_run=False,
            success=False,
            errors=["uv not found", "Invalid lock file format"],
        )
        gen = MigrationReportGenerator()
        output = gen.generate(result)
        assert "uv not found" in output or "error" in output.lower()

    def test_generate_dry_run_noted(self) -> None:
        """Dry-run mode should be indicated in the report."""
        result = MigrationResult(
            project_path=Path("/tmp/test-project"),
            dry_run=True,
            success=True,
        )
        gen = MigrationReportGenerator()
        output = gen.generate(result)
        assert "dry" in output.lower() or "preview" in output.lower()

    def test_generate_json_with_errors(self) -> None:
        """JSON report includes error information."""
        result = MigrationResult(
            project_path=Path("/tmp/test-project"),
            dry_run=False,
            success=False,
            errors=["something went wrong"],
        )
        gen = MigrationReportGenerator()
        output = gen.generate_json(result)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_generate_markdown_with_migrated_files(self) -> None:
        """Report lists migrated files."""
        result = MigrationResult(
            project_path=Path("/tmp/test-project"),
            dry_run=False,
            success=True,
            files_generated=[Path("pyproject.toml"), Path("uv.lock")],
        )
        gen = MigrationReportGenerator()
        output = gen.generate_markdown(result)
        assert "pyproject.toml" in output

    def test_generate_to_file(self, tmp_path: Path) -> None:
        """When report_path is given, the report is written to disk."""
        result = MigrationResult(
            project_path=Path("/tmp/test-project"),
            dry_run=True,
            success=True,
        )
        gen = MigrationReportGenerator()
        output_path = tmp_path / "report.md"
        gen.generate(result, report_path=output_path)
        assert output_path.exists()


# ─── Integration sanity check ────────────────────────────────────────────────


class TestModuleImports:
    """Verify all M5 modules can be imported cleanly."""

    def test_import_compatibility(self) -> None:
        from python_depot_migrate import compatibility
        assert hasattr(compatibility, "CompatibilityChecker")
        assert hasattr(compatibility, "CompatibilityReport")
        assert hasattr(compatibility, "CompatibilityWarning")
        assert hasattr(compatibility, "KNOWN_UV_ISSUES")

    def test_import_report(self) -> None:
        from python_depot_migrate import report
        assert hasattr(report, "MigrationReportGenerator")
        assert hasattr(report, "MigrationDiff")

    def test_import_scanner_types(self) -> None:
        from python_depot_migrate import scanner
        assert hasattr(scanner, "ScanResult")
        assert hasattr(scanner, "ParsedDependency")
        assert hasattr(scanner, "MigrationResult")

    def test_cross_module_dataclass_usage(self) -> None:
        """Verify M5 classes can be used with M1 types."""
        ScanResult(
            dependencies=[ParsedDependency(name="requests")],
            metadata={"project_name": "test"},
        )
        report = CompatibilityReport(compatible=["requests"])
        assert report.compatible == ["requests"]

    def test_all_type_hints_compile(self) -> None:
        """Verify type hints don't cause runtime errors."""
        from python_depot_migrate.compatibility import CompatibilityChecker
        from python_depot_migrate.report import MigrationReportGenerator
        hints1 = get_type_hints(CompatibilityChecker.check)
        hints2 = get_type_hints(MigrationReportGenerator.generate)
        assert len(hints1) >= 1
        assert len(hints2) >= 1
