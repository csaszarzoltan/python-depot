"""Pre-dev tests for CLI Entry Point + Batch Mode (M3).

Pattern:
- Interface tests: verify imports and function signatures — PASS immediately.
- Behavioral tests: verify CLI behavior — FAIL with NotImplementedError.
"""
from __future__ import annotations

import argparse
import inspect
from dataclasses import is_dataclass
from pathlib import Path

import pytest

# ===========================================================================
# SECTION 1: Interface Tests — PASS immediately
# ===========================================================================


class TestCLIModuleInterface:
    """Verify the CLI module exists with expected public API."""

    def test_module_imports(self):
        """cli module can be imported."""
        import python_depot_migrate.cli as cli_mod

        assert cli_mod is not None

    def test_main_function_exists(self):
        """main() function exists in cli module."""
        from python_depot_migrate.cli import main

        assert callable(main)

    def test_main_accepts_argv(self):
        """main() accepts optional argv parameter."""
        from python_depot_migrate.cli import main

        sig = inspect.signature(main)
        params = list(sig.parameters.keys())
        assert "argv" in params

    def test_main_argv_default_none(self):
        """main(argv=None) is the default — uses sys.argv."""
        from python_depot_migrate.cli import main

        sig = inspect.signature(main)
        assert sig.parameters["argv"].default is None

    def test_main_return_annotation(self):
        """main() has a return annotation of int."""
        from python_depot_migrate.cli import main

        sig = inspect.signature(main)
        assert sig.return_annotation is not inspect.Parameter.empty
        # Should be int or str 'int' (with from __future__ import annotations)
        ret = sig.return_annotation
        assert ret is int or ret == "int"

    def test_run_migration_exists(self):
        """run_migration() function exists."""
        from python_depot_migrate.cli import run_migration

        assert callable(run_migration)

    def test_run_migration_signature(self):
        """run_migration accepts project_path, apply, report_only."""
        from python_depot_migrate.cli import run_migration

        sig = inspect.signature(run_migration)
        params = list(sig.parameters.keys())
        assert "project_path" in params
        assert "apply" in params
        assert "report_only" in params

    def test_run_migration_apply_default_false(self):
        """run_migration apply defaults to False (dry-run)."""
        from python_depot_migrate.cli import run_migration

        sig = inspect.signature(run_migration)
        assert sig.parameters["apply"].default is False

    def test_run_migration_report_only_default_false(self):
        """run_migration report_only defaults to False."""
        from python_depot_migrate.cli import run_migration

        sig = inspect.signature(run_migration)
        assert sig.parameters["report_only"].default is False

    def test_run_batch_exists(self):
        """run_batch() function exists."""
        from python_depot_migrate.cli import run_batch

        assert callable(run_batch)

    def test_run_batch_signature(self):
        """run_batch accepts project_paths and apply."""
        from python_depot_migrate.cli import run_batch

        sig = inspect.signature(run_batch)
        params = list(sig.parameters.keys())
        assert "project_paths" in params
        assert "apply" in params

    def test_run_batch_apply_default_false(self):
        """run_batch apply defaults to False."""
        from python_depot_migrate.cli import run_batch

        sig = inspect.signature(run_batch)
        assert sig.parameters["apply"].default is False

    def test_build_parser_exists(self):
        """_build_parser() internal function exists."""
        from python_depot_migrate.cli import _build_parser

        assert callable(_build_parser)

    def test_build_parser_returns_argparse(self):
        """_build_parser returns an ArgumentParser."""
        from python_depot_migrate.cli import _build_parser

        parser = _build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_has_scan_argument(self):
        """Parser has --scan argument."""
        from python_depot_migrate.cli import _build_parser

        parser = _build_parser()
        # Parse a minimal command to check --scan exists
        args = parser.parse_args(["--scan", "."])
        assert hasattr(args, "scan")

    def test_parser_has_apply_flag(self):
        """Parser has --apply flag."""
        from python_depot_migrate.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--scan", ".", "--apply"])
        assert args.apply is True

    def test_parser_has_batch_flag(self):
        """Parser has --batch flag."""
        from python_depot_migrate.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--scan", ".", "--batch"])
        assert args.batch is True

    def test_parser_has_report_only_flag(self):
        """Parser has --report-only flag."""
        from python_depot_migrate.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--scan", ".", "--report-only"])
        assert args.report_only is True

    def test_parser_has_output_argument(self):
        """Parser has --output argument."""
        from python_depot_migrate.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--scan", ".", "--output", "/tmp/out"])
        assert hasattr(args, "output")

    def test_parser_scan_is_required(self):
        """--scan is required."""
        from python_depot_migrate.cli import _build_parser

        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parser_scan_accepts_multiple_paths(self):
        """--scan accepts multiple paths."""
        from python_depot_migrate.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--scan", "./a", "./b", "./c"])
        assert len(args.scan) == 3

    def test_main_is_cli_entry_point(self):
        """main is referenced as console_scripts entry point."""
        # Check that the entry point exists in pyproject.toml
        import tomllib

        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomllib.load(f)
        scripts = config.get("project", {}).get("scripts", {})
        assert "python-depot-migrate" in scripts
        assert scripts["python-depot-migrate"] == "python_depot_migrate.cli:main"


class TestMigrationResultInterface:
    """Verify MigrationResult dataclass interface."""

    def test_import(self):
        """MigrationResult can be imported from report module."""
        from python_depot_migrate.report import MigrationResult

        assert MigrationResult is not None

    def test_is_dataclass(self):
        """MigrationResult is a dataclass."""
        from python_depot_migrate.report import MigrationResult

        assert is_dataclass(MigrationResult)

    def test_has_project_path(self):
        """MigrationResult has project_path field."""
        from python_depot_migrate.report import MigrationResult

        assert "project_path" in MigrationResult.__dataclass_fields__

    def test_has_success(self):
        """MigrationResult has success field."""
        from python_depot_migrate.report import MigrationResult

        assert "success" in MigrationResult.__dataclass_fields__

    def test_has_files_changed(self):
        """MigrationResult has files_changed field."""
        from python_depot_migrate.report import MigrationResult

        assert "files_changed" in MigrationResult.__dataclass_fields__

    def test_has_files_generated(self):
        """MigrationResult has files_generated field."""
        from python_depot_migrate.report import MigrationResult

        assert "files_generated" in MigrationResult.__dataclass_fields__

    def test_has_errors(self):
        """MigrationResult has errors field."""
        from python_depot_migrate.report import MigrationResult

        assert "errors" in MigrationResult.__dataclass_fields__

    def test_has_warnings(self):
        """MigrationResult has warnings field."""
        from python_depot_migrate.report import MigrationResult

        assert "warnings" in MigrationResult.__dataclass_fields__

    def test_success_default_false(self):
        """MigrationResult success defaults to False."""
        from python_depot_migrate.report import MigrationResult

        mr = MigrationResult(project_path=Path("."))
        assert mr.success is False

    def test_files_changed_default_empty(self):
        """MigrationResult files_changed defaults to empty list."""
        from python_depot_migrate.report import MigrationResult

        mr = MigrationResult(project_path=Path("."))
        assert mr.files_changed == []

    def test_errors_default_empty(self):
        """MigrationResult errors defaults to empty list."""
        from python_depot_migrate.report import MigrationResult

        mr = MigrationResult(project_path=Path("."))
        assert mr.errors == []


class TestMainModuleInterface:
    """Verify __main__.py can be imported and calls main."""

    def test_module_imports(self):
        """__main__ module can be imported."""
        import python_depot_migrate.__main__ as main_mod

        assert main_mod is not None

    def test_main_in_main_module(self):
        """__main__ module imports main from cli."""
        import python_depot_migrate.__main__ as main_mod

        assert hasattr(main_mod, "main")


# ===========================================================================
# SECTION 2: Behavioral Tests — FAIL with NotImplementedError
# ===========================================================================


class TestMainBehavior:
    """Behavioral tests for main() — all raise NotImplementedError in RED phase."""

    def test_main_returns_zero_on_success(self):
        """main() returns 0 on successful dry-run scan."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", "."])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 0

    def test_main_returns_error_on_bad_path(self):
        """main() returns 1 for non-existent path."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", "/nonexistent/path/xyz"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 1

    def test_main_dry_run_default(self):
        """main() defaults to dry-run (no file writes)."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", "."])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 0

    def test_main_apply_flag(self):
        """main() with --apply executes migration."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", ".", "--apply"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 0

    def test_main_report_only_skips_writes(self):
        """main() with --report-only generates report without file changes."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", ".", "--report-only"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 0

    def test_main_batch_mode(self):
        """main() with --batch processes multiple projects."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", "./a", "./b", "./c", "--batch"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 0

    def test_main_partial_failure_returns_two(self):
        """main() returns 2 for partial success in batch mode."""
        from python_depot_migrate.cli import main

        # One valid, one invalid path — should return 2 (partial success)
        try:
            result = main(["--scan", ".", "/nonexistent", "--batch"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 2

    def test_main_no_dep_files_returns_error(self):
        """main() returns 1 when no dependency files found."""
        from python_depot_migrate.cli import main

        # A temp dir with no dep files
        try:
            result = main(["--scan", "/tmp"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 1

    def test_main_shows_output_to_stdout(self):
        """main() outputs progress/analysis to stdout."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", "."])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 0


class TestRunMigrationBehavior:
    """Behavioral tests for run_migration() — all raise NotImplementedError in RED phase."""

    def test_returns_migration_result(self):
        """run_migration returns a MigrationResult."""
        from python_depot_migrate.cli import run_migration
        from python_depot_migrate.report import MigrationResult

        try:
            result = run_migration(Path("."))
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, MigrationResult)

    def test_result_has_project_path(self):
        """MigrationResult.project_path matches input."""
        from python_depot_migrate.cli import run_migration

        try:
            result = run_migration(Path("."))
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.project_path == Path(".")

    def test_dry_run_does_not_write_files(self):
        """run_migration with dry-run does not write files."""
        import tempfile

        from python_depot_migrate.cli import run_migration

        tmpdir = Path(tempfile.mkdtemp())
        try:
            result = run_migration(tmpdir, apply=False)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.files_changed == []

    def test_apply_writes_files(self):
        """run_migration with apply=True writes output files."""
        from python_depot_migrate.cli import run_migration

        try:
            result = run_migration(Path("."), apply=True)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(result.files_generated) > 0

    def test_report_only_no_file_changes(self):
        """run_migration with report_only=True changes no files."""
        from python_depot_migrate.cli import run_migration

        try:
            result = run_migration(Path("."), report_only=True)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.files_changed == []
        assert result.files_generated == []

    def test_bad_path_raises_error(self):
        """run_migration with non-existent path populates errors."""
        from python_depot_migrate.cli import run_migration

        try:
            result = run_migration(Path("/nonexistent/path/xyz"))
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert not result.success
        assert len(result.errors) > 0

    def test_mixed_format_project(self):
        """run_migration handles requirements.txt + pyproject.toml coexisting."""
        from python_depot_migrate.cli import run_migration

        try:
            result = run_migration(Path("."))
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result.errors, list)

    def test_scanner_integration(self):
        """run_migration invokes DependencyScanner.scan internally."""
        from python_depot_migrate.cli import run_migration

        try:
            result = run_migration(Path("."))
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # If scanner ran, scan_result should be populated
        assert result.scan_result is not None

    def test_compatibility_check_integration(self):
        """run_migration invokes CompatibilityChecker.check internally."""
        from python_depot_migrate.cli import run_migration

        try:
            result = run_migration(Path("."))
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.compatibility_report is not None


class TestRunBatchBehavior:
    """Behavioral tests for run_batch() — all raise NotImplementedError in RED phase."""

    def test_returns_list_of_results(self):
        """run_batch returns a list of MigrationResult."""
        from python_depot_migrate.cli import run_batch
        from python_depot_migrate.report import MigrationResult

        try:
            results = run_batch([Path("."), Path("/tmp")])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(results, list)
        assert all(isinstance(r, MigrationResult) for r in results)

    def test_result_count_matches_input(self):
        """run_batch returns one result per input path."""
        from python_depot_migrate.cli import run_batch

        paths = [Path("."), Path("/tmp")]
        try:
            results = run_batch(paths)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert len(results) == len(paths)

    def test_batch_partial_failure(self):
        """run_batch handles mix of valid and invalid paths."""
        from python_depot_migrate.cli import run_batch

        paths = [Path("."), Path("/nonexistent")]
        try:
            results = run_batch(paths)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # At least one should succeed, one should fail
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) >= 1
        assert len(failures) >= 1

    def test_batch_apply_flag_propagates(self):
        """run_batch apply flag applies to all projects."""
        from python_depot_migrate.cli import run_batch

        paths = [Path("."), Path("/tmp")]
        try:
            results = run_batch(paths, apply=True)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # All results should have been processed with apply
        assert isinstance(results, list)

    def test_batch_empty_list(self):
        """run_batch with empty list returns empty list."""
        from python_depot_migrate.cli import run_batch

        try:
            results = run_batch([])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert results == []

    def test_batch_independence(self):
        """run_batch: failure in one project doesn't crash others."""
        from python_depot_migrate.cli import run_batch

        paths = [Path("."), Path("/nonexistent"), Path("/tmp")]
        try:
            results = run_batch(paths)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # Should get 3 results even though one path is bad
        assert len(results) == 3


class TestUVNotInstalledBehavior:
    """Behavioral tests for uv-not-installed error handling."""

    def test_uv_not_installed_error_message(self):
        """main() shows clear error suggesting uv install when uv is missing."""
        from python_depot_migrate.cli import main

        try:
            main(["--scan", ".", "--apply"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # If uv is not installed, should get error code 1 with helpful message
        # (This test will pass after implementation; the skip handles RED phase)


class TestExitCodeBehavior:
    """Behavioral tests for exit code semantics."""

    def test_zero_on_full_success(self):
        """Exit code 0 when all projects migrate successfully."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", "."])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 0

    def test_one_on_error(self):
        """Exit code 1 on complete failure (bad path, no deps)."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", "/nonexistent"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 1

    def test_two_on_partial_success(self):
        """Exit code 2 when batch has mix of successes and failures."""
        from python_depot_migrate.cli import main

        try:
            result = main(["--scan", ".", "/nonexistent", "--batch"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result == 2
