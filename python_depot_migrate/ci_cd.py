"""CI/CD Configuration Updater (M4) — detect and migrate to uv."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class CICDConfig:
    """A detected CI/CD configuration file.

    Attributes:
        path: Absolute or relative path to the config file.
        kind: Type of CI/CD system detected.
        current_backend: Package manager currently in use (pip, poetry, pipenv).
        content: Full file contents.
    """

    path: Path
    kind: Literal["github-actions", "gitlab-ci", "dockerfile"]
    current_backend: str  # "pip", "poetry", "pipenv"
    content: str


@dataclass
class MigrationDiff:
    """Result of a CI/CD configuration migration.

    Attributes:
        original: Original file content before migration.
        updated: Updated file content after migration.
        changes: Human-readable list of changes made.
    """

    original: str
    updated: str
    changes: list[str]  # human-readable change list


class CICDUpdater:
    """Detect and update CI/CD configuration files for uv usage.

    Scans project directories for GitHub Actions workflows, GitLab CI configs,
    and Dockerfiles, then provides migration from pip/poetry/pipenv to uv.
    """

    def detect(self, project_path: Path) -> list[CICDConfig]:
        """Scan project directory for CI/CD config files.

        Detects:
        - .github/workflows/*.yml (GitHub Actions)
        - .gitlab-ci.yml (GitLab CI)
        - Dockerfiles with pip/poetry/pipenv install commands

        Args:
            project_path: Root directory of the project to scan.

        Returns:
            List of detected CICDConfig objects.
        """
        configs: list[CICDConfig] = []

        # Detect GitHub Actions workflows
        workflows_dir = project_path / ".github" / "workflows"
        if workflows_dir.is_dir():
            for yml_file in sorted(workflows_dir.rglob("*.yml")):
                content = yml_file.read_text(encoding="utf-8")
                backend = _detect_backend_from_content(content)
                configs.append(
                    CICDConfig(
                        path=yml_file,
                        kind="github-actions",
                        current_backend=backend,
                        content=content,
                    )
                )

        # Detect GitLab CI
        gitlab_ci = project_path / ".gitlab-ci.yml"
        if gitlab_ci.is_file():
            content = gitlab_ci.read_text(encoding="utf-8")
            backend = _detect_backend_from_content(content)
            configs.append(
                CICDConfig(
                    path=gitlab_ci,
                    kind="gitlab-ci",
                    current_backend=backend,
                    content=content,
                )
            )

        # Detect Dockerfiles
        for dockerfile in _find_dockerfiles(project_path):
            content = dockerfile.read_text(encoding="utf-8")
            backend = _detect_backend_from_content(content)
            # Only include if it actually uses a detectable backend
            if backend in ("pip", "poetry", "pipenv"):
                configs.append(
                    CICDConfig(
                        path=dockerfile,
                        kind="dockerfile",
                        current_backend=backend,
                        content=content,
                    )
                )

        return configs

    def update(
        self, config: CICDConfig, dry_run: bool = True
    ) -> MigrationDiff | None:
        """Update a CI/CD config for uv usage.

        Replaces pip/poetry/pipenv install commands with their uv equivalents:
        - pip install → uv pip install
        - poetry install → uv sync --locked
        - pipenv install → uv sync

        For Dockerfiles, also adds uv installation instructions.

        Args:
            config: The CI/CD config to update.
            dry_run: If True, return diff without modifying files.

        Returns:
            MigrationDiff if changes were made, None if no changes needed.
        """
        updated_content, changes = _apply_migrations(config.content, config.kind)

        if updated_content == config.content:
            return None

        if not dry_run and config.path.exists():
            config.path.write_text(updated_content, encoding="utf-8")

        return MigrationDiff(
            original=config.content,
            updated=updated_content,
            changes=changes,
        )


def _find_dockerfiles(project_path: Path) -> list[Path]:
    """Find all Dockerfiles in a project directory.

    Args:
        project_path: Root directory to search.

    Returns:
        List of paths to Dockerfiles found.
    """
    candidates = []
    # Standard Dockerfile
    dockerfile = project_path / "Dockerfile"
    if dockerfile.is_file():
        candidates.append(dockerfile)
    # Dockerfile variants
    for suffix in (".docker", ".dockerfile"):
        p = project_path / f"Dockerfile{suffix}"
        if p.is_file():
            candidates.append(p)
    return candidates


def _detect_backend_from_content(content: str) -> str:
    """Detect which package manager a CI/CD config uses.

    Checks for poetry/pipenv first (more specific), then falls back to pip.

    Args:
        content: File content to analyze.

    Returns:
        Detected backend name: "pip", "poetry", "pipenv", or "pip" as default.
    """
    # Check for poetry patterns
    if re.search(r"poetry\s+install", content):
        return "poetry"
    # Check for pipenv patterns
    if re.search(r"pipenv\s+install", content):
        return "pipenv"
    # Check for pip patterns (but not uv pip)
    if re.search(r"(?<!\buv\s)pip\s+install", content):
        return "pip"
    # If content is empty or has no detectable backend, default to pip
    return "pip"


def _apply_migrations(
    content: str, kind: str
) -> tuple[str, list[str]]:
    """Apply package manager migrations to content.

    Replaces pip/poetry/pipenv commands with uv equivalents.

    Args:
        content: Original file content.
        kind: CI/CD config type (github-actions, gitlab-ci, dockerfile).

    Returns:
        Tuple of (updated_content, list_of_changes).
    """
    updated = content
    changes: list[str] = []

    # Dockerfile-specific: add uv installation if not present
    if kind == "dockerfile" and "uv" not in updated:
        updated, docker_changes = _update_dockerfile(updated)
        changes.extend(docker_changes)

    # Replace pip install → uv pip install
    updated, pip_changes = _replace_pip_install(updated)
    changes.extend(pip_changes)

    # Replace poetry install → uv sync --locked
    updated, poetry_changes = _replace_poetry_install(updated)
    changes.extend(poetry_changes)

    # Replace pipenv install → uv sync
    updated, pipenv_changes = _replace_pipenv_install(updated)
    changes.extend(pipenv_changes)

    return updated, changes


def _update_dockerfile(content: str) -> tuple[str, list[str]]:
    """Update Dockerfile to include uv installation.

    Adds a RUN command to install uv before the first pip/poetry/pipenv
    install command, using the official uv installer.

    Args:
        content: Original Dockerfile content.

    Returns:
        Tuple of (updated_content, list_of_changes).
    """
    changes: list[str] = []

    # Check if uv is already installed (uv pip install already present)
    if re.search(r"uv\s+(pip|sync)", content):
        return content, changes

    # Find the first install command line and add uv before it
    lines = content.split("\n")
    new_lines: list[str] = []
    uv_added = False

    for line in lines:
        if (
            not uv_added
            and re.search(r"(RUN\s+)(pip|poetry|pipenv)\s+install", line)
        ):
            # Add uv installation before the first install command
            # Determine indentation from the current line
            indent = len(line) - len(line.lstrip())
            prefix = line[:indent]
            new_lines.append(
                f"{prefix}COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv"
            )
            uv_added = True
            changes.append("Added uv binary installation to Dockerfile")
        new_lines.append(line)

    return "\n".join(new_lines), changes


def _replace_pip_install(content: str) -> tuple[str, list[str]]:
    """Replace pip install commands with uv pip install.

    Handles various pip install patterns:
    - pip install -r requirements.txt
    - pip install package
    - pip install 'package[extras]'
    - pip install 'package>=version'

    Does NOT re-replace lines that already use uv pip install.

    Args:
        content: Original content.

    Returns:
        Tuple of (updated_content, list_of_changes).
    """
    changes: list[str] = []

    # Pattern: match pip install but NOT uv pip install
    # Negative lookbehind for "uv " to avoid double-replacing
    pattern = re.compile(r"(?<!\buv\s)(pip\s+install\b)")

    def _replace_pip(match: re.Match[str]) -> str:
        return "uv " + match.group(1)

    new_content, count = pattern.subn(_replace_pip, content)
    if count > 0:
        changes.append(
            f"Replaced {count} pip install command(s) with uv pip install"
        )

    return new_content, changes


def _replace_poetry_install(content: str) -> tuple[str, list[str]]:
    """Replace poetry install commands with uv sync --locked.

    Args:
        content: Original content.

    Returns:
        Tuple of (updated_content, list_of_changes).
    """
    changes: list[str] = []

    # Match poetry install with optional flags
    pattern = re.compile(r"poetry\s+install\b[^\n]*")

    def _replace_poetry(match: re.Match[str]) -> str:
        return "uv sync --locked"

    new_content, count = pattern.subn(_replace_poetry, content)
    if count > 0:
        changes.append(
            f"Replaced {count} poetry install command(s) with uv sync --locked"
        )

    return new_content, changes


def _replace_pipenv_install(content: str) -> tuple[str, list[str]]:
    """Replace pipenv install commands with uv sync.

    Args:
        content: Original content.

    Returns:
        Tuple of (updated_content, list_of_changes).
    """
    changes: list[str] = []

    # Match pipenv install with optional flags
    pattern = re.compile(r"pipenv\s+install\b[^\n]*")

    def _replace_pipenv(match: re.Match[str]) -> str:
        return "uv sync"

    new_content, count = pattern.subn(_replace_pipenv, content)
    if count > 0:
        changes.append(
            f"Replaced {count} pipenv install command(s) with uv sync"
        )

    return new_content, changes
