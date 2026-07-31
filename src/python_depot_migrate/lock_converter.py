"""Lock file conversion module.

Reads existing lock files (poetry.lock, Pipfile.lock, pip-tools compiled requirements),
extracts locked versions, and produces uv.lock via uv lock with version constraints pinned.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class LockedPackage:
    """A single locked package extracted from a lock file."""

    name: str
    version: str
    extras: list[str] = field(default_factory=list)
    markers: str | None = None
    source: dict[str, Any] | None = None


@dataclass
class LockSnapshot:
    """Snapshot of all locked packages from a source lock file."""

    source_type: Literal["poetry", "pipenv", "pip-tools", "requirements"]
    packages: list[LockedPackage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lock file readers
# ---------------------------------------------------------------------------

def _parse_poetry_toml(data: dict) -> LockSnapshot:
    """Parse a parsed TOML dict from poetry.lock into a LockSnapshot."""
    packages: list[LockedPackage] = []
    for pkg in data.get("package", []):
        extras = pkg.get("extras", [])
        markers = pkg.get("markers", None)
        source = pkg.get("source", None)
        packages.append(LockedPackage(
            name=pkg["name"],
            version=pkg["version"],
            extras=extras,
            markers=markers,
            source=source,
        ))

    metadata = {}
    if "metadata" in data:
        metadata = {
            "lock_version": data["metadata"].get("lock-version"),
            "content_hash": data["metadata"].get("content-hash"),
        }

    return LockSnapshot(source_type="poetry", packages=packages, metadata=metadata)


def _read_poetry_lock_regex(lock_path: Path) -> LockSnapshot:
    """Fallback regex parser for poetry.lock when TOML parsing fails.

    Handles malformed TOML by extracting [[package]] blocks with regex.
    """
    content = lock_path.read_text()
    packages: list[LockedPackage] = []

    # Split on [[package]] headers
    blocks = re.split(r'\[\[package\]\]', content)
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        name_match = re.search(r'^name\s*=\s*"([^"]+)"', block, re.MULTILINE)
        version_match = re.search(r'^version\s*=\s*"([^"]+)"', block, re.MULTILINE)

        if not name_match or not version_match:
            continue

        name = name_match.group(1)
        version = version_match.group(1)

        extras: list[str] = []
        extras_match = re.search(r'^extras\s*=\s*\[(.*?)\]', block, re.MULTILINE)
        if extras_match:
            extras = [
                e.strip().strip('"')
                for e in extras_match.group(1).split(",")
                if e.strip().strip('"')
            ]

        markers: str | None = None
        markers_match = re.search(
            r'^markers\s*=\s*"((?:[^"\\]|\\.)*)"', block, re.MULTILINE
        )
        if markers_match:
            markers = markers_match.group(1).replace('\\"', '"')

        source: dict[str, Any] | None = None
        source_match = re.search(
            r'^\[package\.source\]\s*\n((?:.*\n)*?)(?=\n\[|\Z)',
            block,
            re.MULTILINE,
        )
        if source_match:
            source_text = source_match.group(1)
            source = {}
            for sline in source_text.strip().splitlines():
                kv = sline.strip().split(" = ", 1)
                if len(kv) == 2:
                    key = kv[0].strip()
                    val = kv[1].strip().strip('"')
                    source[key] = val

        packages.append(LockedPackage(
            name=name,
            version=version,
            extras=extras,
            markers=markers,
            source=source,
        ))

    return LockSnapshot(source_type="poetry", packages=packages)


def _read_poetry_lock(lock_path: Path) -> LockSnapshot:
    """Read a poetry.lock (TOML) file."""
    try:
        with open(lock_path, "rb") as f:
            data = tomllib.load(f)
        return _parse_poetry_toml(data)
    except (tomllib.TOMLDecodeError, OSError):
        # Fallback to regex parser for malformed TOML
        return _read_poetry_lock_regex(lock_path)


def _read_pipenv_lock(lock_path: Path) -> LockSnapshot:
    """Read a Pipfile.lock (JSON) file."""
    with open(lock_path) as f:
        data = json.load(f)

    packages: list[LockedPackage] = []
    for section in ("default", "develop"):
        for name, info in data.get(section, {}).items():
            version_str = info.get("version", "")
            # Strip leading == if present
            version = version_str.lstrip("=") if version_str else ""
            extras = info.get("extras", [])
            markers = info.get("markers", None)
            source = None
            if info.get("editable"):
                source = {"type": "editable", "path": info.get("path", ".")}
            packages.append(LockedPackage(
                name=name,
                version=version,
                extras=extras if isinstance(extras, list) else [],
                markers=markers,
                source=source,
            ))

    return LockSnapshot(source_type="pipenv", packages=packages)


def _read_requirements(lock_path: Path) -> LockSnapshot:
    """Read a pinned requirements.txt file (pip-tools compiled or plain pinned)."""
    packages: list[LockedPackage] = []
    content = lock_path.read_text()

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Skip editable installs
        if line.startswith(("-e ", "--editable")):
            continue
        # Skip flags/options
        if line.startswith("-"):
            continue

        # Extract name==version, stripping --hash=... suffixes
        # Handle: name==1.2.3 --hash=sha256:xxx
        base = line.split("--hash=")[0].strip()
        # Handle indented lines (pip-tools format)
        base = base.lstrip()

        match = re.match(r"^([A-Za-z0-9_.-]+)==(.+)$", base)
        if match:
            name = match.group(1)
            version = match.group(2)
            packages.append(LockedPackage(name=name, version=version))

    return LockSnapshot(source_type="requirements", packages=packages)


# ---------------------------------------------------------------------------
# LockConverter
# ---------------------------------------------------------------------------

class LockConverter:
    """Converts existing lock files to uv-compatible format.

    Pipeline:
        1. read_lock()       → LockSnapshot
        2. build_constraints() → list[str]
        3. generate_uv_lock() → Path | None
    """

    def read_lock(self, lock_path: Path) -> LockSnapshot:
        """Read a lock file and return a LockSnapshot with all locked packages.

        Supports poetry.lock (TOML), Pipfile.lock (JSON),
        pip-tools compiled requirements.txt (==pinned), and
        plain requirements.txt with pinned versions.

        Args:
            lock_path: Path to the lock file.

        Returns:
            LockSnapshot containing source type, packages, and metadata.

        Raises:
            FileNotFoundError: If the lock file does not exist.
        """
        if not lock_path.exists():
            raise FileNotFoundError(f"Lock file not found: {lock_path}")

        name = lock_path.name.lower()
        if name == "poetry.lock":
            return _read_poetry_lock(lock_path)
        elif name == "pipfile.lock":
            return _read_pipenv_lock(lock_path)
        else:
            return _read_requirements(lock_path)

    def build_constraints(self, snapshot: LockSnapshot) -> list[str]:
        """Build a list of pinned version constraints from a LockSnapshot.

        Produces lines like ``package==1.2.3`` suitable for feeding into
        ``uv lock --constraint-file``.

        Args:
            snapshot: A LockSnapshot from read_lock().

        Returns:
            List of constraint strings (one per package).
        """
        if not snapshot.packages:
            return []

        constraints: list[str] = []
        for pkg in snapshot.packages:
            # Skip VCS sources — they can't be pinned as constraints
            if pkg.source and pkg.source.get("type") in ("git", "hg", "svn", "bzr"):
                continue

            if pkg.extras:
                extras_str = ",".join(sorted(pkg.extras))
                constraints.append(f"{pkg.name}[{extras_str}]=={pkg.version}")
            else:
                constraints.append(f"{pkg.name}=={pkg.version}")

        return constraints

    def generate_uv_lock(
        self,
        project_path: Path,
        constraints: list[str],
        dry_run: bool = True,
    ) -> Path | None:
        """Generate a uv.lock file using the uv CLI.

        When dry_run=True, runs ``uv lock --dry-run`` to validate without
        modifying the project. When dry_run=False, runs ``uv lock`` to
        produce the actual lock file.

        Args:
            project_path: Root directory of the target project.
            constraints: List of pinned version constraints (from build_constraints).
            dry_run: If True, validate only; if False, produce uv.lock.

        Returns:
            Path to the generated uv.lock when dry_run=False, or None for
            dry runs and failures.
        """
        if not constraints:
            return None

        # Write constraints to a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="constraints_"
        ) as f:
            f.write("\n".join(constraints))
            constraint_file = f.name

        try:
            cmd = ["uv", "lock", f"--constraint-file={constraint_file}"]
            if dry_run:
                cmd.append("--dry-run")

            result = subprocess.run(  # noqa: PLW1510
                cmd,
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return None

            if dry_run:
                return None

            uv_lock = project_path / "uv.lock"
            return uv_lock if uv_lock.exists() else None

        except FileNotFoundError:
            # uv not installed
            return None
        except subprocess.TimeoutExpired:
            return None
        finally:
            Path(constraint_file).unlink(missing_ok=True)
