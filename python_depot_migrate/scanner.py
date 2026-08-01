"""Dependency analysis engine — scan project for dependency files and parse them."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


class DependencyFormat(enum.Enum):
    """Enum for dependency file formats."""

    REQUIREMENTS_TXT = "requirements.txt"
    REQUIREMENTS_IN = "requirements.in"
    PYPROJECT_TOML = "pyproject.toml"
    PIPFILE = "Pipfile"
    SETUP_PY = "setup.py"
    SETUP_CFG = "setup.cfg"


@dataclass
class ParsedDependency:
    """A single parsed dependency with normalized fields."""

    name: str
    version_constraint: str | None = None
    source_type: Literal["pypi", "git", "path", "url"] = "pypi"
    extras: list[str] = field(default_factory=list)
    markers: str | None = None
    is_dev: bool = False


@dataclass
class ScanResult:
    """Result of scanning a project directory for dependencies."""

    source_format: DependencyFormat = DependencyFormat.REQUIREMENTS_TXT
    dependencies: list[ParsedDependency] = field(default_factory=list)
    dev_dependencies: list[ParsedDependency] = field(default_factory=list)
    extras: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationResult:
    """Result of running a migration on a project."""

    project_path: Path = field(default_factory=lambda: Path("."))
    scan_result: ScanResult = field(default_factory=ScanResult)
    files_changed: list[Path] = field(default_factory=list)
    files_generated: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dry_run: bool = True
    success: bool = False
    before_summary: str = ""
    after_summary: str = ""
    compatibility_report: Any = None

    # Alias for backward compatibility
    @property
    def migrated_files(self) -> list[Path]:
        """Alias for files_generated for backward compatibility."""
        return self.files_generated


class DependencyScanner:
    """Scan a project directory for dependency files and parse them."""

    def scan(self, project_path: Path) -> ScanResult:
        raise NotImplementedError

    def detect_formats(self, project_path: Path) -> list[DependencyFormat]:
        raise NotImplementedError
