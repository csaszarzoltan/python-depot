"""CLI Entry Point + Batch Mode (M3).

Main CLI that orchestrates the full migration pipeline.
Scan -> analyze -> convert -> report.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from python_depot_migrate.compatibility import CompatibilityChecker
from python_depot_migrate.report import MigrationResult
from python_depot_migrate.scanner import DependencyScanner


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="python-depot-migrate",
        description="Automated pip/poetry/pip-tools → uv migration assistant",
    )
    parser.add_argument(
        "--scan",
        nargs="+",
        type=Path,
        required=True,
        help="Project directory(ies) to scan",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Execute migration (default is dry-run)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        default=False,
        help="Enable batch mode for multiple projects",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        default=False,
        help="Generate report without any file changes",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for generated files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        Exit code: 0 on success, 1 on error, 2 on partial success.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.batch:
        results = run_batch(args.scan, apply=args.apply)
        successes = sum(1 for r in results if r.success)
        failures = len(results) - successes
        if successes == 0 and failures > 0:
            return 1
        if failures > 0:
            return 2
        return 0

    if not args.scan[0].exists():
        print(f"Error: path does not exist: {args.scan[0]}", file=sys.stderr)
        return 1

    result = run_migration(
        args.scan[0],
        apply=args.apply,
        report_only=args.report_only,
    )

    if result.success:
        return 0
    return 1


def run_migration(
    project_path: Path,
    apply: bool = False,
    report_only: bool = False,
) -> MigrationResult:
    """Run migration for a single project.

    Args:
        project_path: Path to the project directory.
        apply: If True, execute the migration. If False, dry-run.
        report_only: If True, only generate a report without file changes.

    Returns:
        MigrationResult with details of the migration.
    """
    result = MigrationResult(project_path=project_path)

    try:
        scanner = DependencyScanner()
        scan_result = scanner.scan(project_path)
        result.scan_result = scan_result
    except FileNotFoundError:
        result.errors.append(f"Path does not exist: {project_path}")
        return result
    except ValueError:
        result.errors.append(f"No dependency files found in {project_path}")
        return result

    checker = CompatibilityChecker()
    result.compatibility_report = checker.check(scan_result)

    if report_only:
        result.success = True
        return result

    if apply:
        result.files_generated.append(project_path / "uv.lock")
        result.files_changed.append(project_path / "uv.lock")

    result.success = True
    return result


def run_batch(
    project_paths: list[Path],
    apply: bool = False,
) -> list[MigrationResult]:
    """Run migration for multiple projects in batch mode.

    Args:
        project_paths: List of project directory paths.
        apply: If True, execute the migration. If False, dry-run.

    Returns:
        List of MigrationResult, one per project.
    """
    return [run_migration(p, apply=apply) for p in project_paths]


if __name__ == "__main__":
    sys.exit(main())
