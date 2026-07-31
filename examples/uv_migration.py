#!/usr/bin/env python3
"""UV Migration Assistant — programmatic usage examples.

Demonstrates the four migration stages without requiring a running server.
Run from the project root:

    python examples/uv_migration.py
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from python_depot_migrate.ci_cd import CICDUpdater
from python_depot_migrate.compatibility import CompatibilityChecker
from python_depot_migrate.lock_converter import LockConverter
from python_depot_migrate.report import MigrationReportGenerator
from python_depot_migrate.scanner import (
    DependencyFormat,
    MigrationResult,
    ParsedDependency,
    ScanResult,
)


def example_compatibility_check() -> None:
    """Stage 1-2: Create a scan result and check compatibility."""
    print("=" * 60)
    print("EXAMPLE 1: Compatibility Check")
    print("=" * 60)

    scan_result = ScanResult(
        source_format=DependencyFormat.REQUIREMENTS_TXT,
        dependencies=[
            ParsedDependency(name="fastapi", version_constraint=">=0.100.0"),
            ParsedDependency(name="pip-tools", version_constraint=">=7.0.0"),
            ParsedDependency(name="uvicorn", version_constraint=">=0.20.0"),
            ParsedDependency(name="black", version_constraint=">=23.0.0"),
        ],
        dev_dependencies=[
            ParsedDependency(name="pytest", version_constraint=">=8.0.0"),
        ],
    )

    checker = CompatibilityChecker()
    report = checker.check(scan_result)

    print(f"Compatible packages: {report.compatible}")
    print(f"Warnings: {len(report.warnings)}")
    for w in report.warnings:
        print(f"  - {w.package}: {w.issue}")
        if w.workaround:
            print(f"    Workaround: {w.workaround}")
    print(f"Effort estimate: {report.effort_estimate}")
    print()


def example_lock_conversion() -> None:
    """Stage 3: Read a lock file and build constraints."""
    print("=" * 60)
    print("EXAMPLE 2: Lock File Conversion")
    print("=" * 60)

    # Create a temporary pinned requirements.txt
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="requirements_"
    ) as f:
        f.write("# Pinned dependencies\n")
        f.write("fastapi==0.110.0\n")
        f.write("uvicorn[standard]==0.27.0\n")
        f.write("sqlalchemy==2.0.25\n")
        f.write("httpx==0.27.0\n")
        f.write("pydantic==2.5.3 --hash=sha256:abc123\n")
        f.write("\n")
        f.write("-e ./local-package\n")
        req_path = Path(f.name)

    try:
        converter = LockConverter()

        # Read the lock file
        snapshot = converter.read_lock(req_path)
        print(f"Source type: {snapshot.source_type}")
        print(f"Locked packages: {len(snapshot.packages)}")
        for pkg in snapshot.packages:
            print(f"  - {pkg.name}=={pkg.version}")

        # Build constraints for uv
        constraints = converter.build_constraints(snapshot)
        print(f"\nGenerated {len(constraints)} constraints for uv:")
        for c in constraints:
            print(f"  {c}")
    finally:
        req_path.unlink(missing_ok=True)

    print()


def example_cicd_detection() -> None:
    """Stage 4: Detect and preview CI/CD migrations."""
    print("=" * 60)
    print("EXAMPLE 3: CI/CD Config Detection & Migration")
    print("=" * 60)

    # Create a temporary project with a GitHub Actions workflow
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        workflows_dir = project / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        workflow_file = workflows_dir / "ci.yml"
        workflow_file.write_text(
            """name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pip install -e ".[dev]"
      - run: pytest
"""
        )

        # Also create a Dockerfile
        dockerfile = project / "Dockerfile"
        dockerfile.write_text(
            """FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN pip install -e .
CMD ["uvicorn", "app:main"]
"""
        )

        updater = CICDUpdater()
        configs = updater.detect(project)

        print(f"Detected {len(configs)} CI/CD config(s):")
        for cfg in configs:
            print(f"  - {cfg.kind}: {cfg.path.name} (backend: {cfg.current_backend})")

        # Preview changes (dry-run)
        for cfg in configs:
            diff = updater.update(cfg, dry_run=True)
            if diff:
                print(f"\nProposed changes for {cfg.path.name}:")
                for change in diff.changes:
                    print(f"  - {change}")

    print()


def example_migration_report() -> None:
    """Generate a migration report."""
    print("=" * 60)
    print("EXAMPLE 4: Migration Report")
    print("=" * 60)

    result = MigrationResult(
        project_path=Path("./my-web-app"),
        dry_run=True,
        success=True,
        before_summary="pip (requirements.txt, 24 packages)",
        after_summary="uv (pyproject.toml + uv.lock, 24 packages)",
        warnings=["pip-tools found — use uv pip compile instead"],
    )

    generator = MigrationReportGenerator()

    # Markdown report
    markdown = generator.generate_markdown(result)
    print("Markdown report:")
    print("-" * 40)
    print(markdown)

    # JSON report
    json_report = generator.generate_json(result)
    data = json.loads(json_report)
    print("JSON report keys:", list(data.keys()))
    print()


def example_scan_result_data_model() -> None:
    """Demonstrate the ScanResult data model."""
    print("=" * 60)
    print("EXAMPLE 5: ScanResult Data Model")
    print("=" * 60)

    result = ScanResult(
        source_format=DependencyFormat.PYPROJECT_TOML,
        dependencies=[
            ParsedDependency(
                name="requests",
                version_constraint=">=2.31.0",
                extras=["security"],
            ),
            ParsedDependency(
                name="my-private-lib",
                source_type="git",
            ),
        ],
        dev_dependencies=[
            ParsedDependency(name="ruff", is_dev=True),
        ],
        extras={"all": ["requests[security]", "click"]},
        metadata={"python_requires": ">=3.12"},
    )

    print(f"Format: {result.source_format.value}")
    print(f"Dependencies: {len(result.dependencies)}")
    for dep in result.dependencies:
        extras_str = f"[{','.join(dep.extras)}]" if dep.extras else ""
        print(f"  - {dep.name}{extras_str} ({dep.source_type})")
    print(f"Dev dependencies: {len(result.dev_dependencies)}")
    print(f"Extras groups: {list(result.extras.keys())}")
    print()


if __name__ == "__main__":
    example_compatibility_check()
    example_lock_conversion()
    example_cicd_detection()
    example_migration_report()
    example_scan_result_data_model()
    print("All examples completed successfully.")
