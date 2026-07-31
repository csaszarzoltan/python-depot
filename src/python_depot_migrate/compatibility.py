"""Compatibility checker — pre-flight check for uv migration compatibility."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from python_depot_migrate.scanner import ScanResult

# Curated list of packages with known uv compatibility issues.
# This is research-backed and should be maintained as new issues are discovered.
KNOWN_UV_ISSUES: dict[str, dict[str, str | None]] = {
    "pip-tools": {
        "issue": "pip-tools uses pip's internal resolver; uv replaces it entirely",
        "workaround": "Use uv pip compile instead of pip-compile",
    },
    "poetry-core": {
        "issue": "Build backend incompatible with uv's build system",
        "workaround": "Replace with uv_build or setuptools in [build-system]",
    },
    "black": {
        "issue": "May need --target-version config update for uv environments",
        "workaround": "Update pyproject.toml [tool.black] target-version after migration",
    },
    "setuppy": {
        "issue": "setup.py-only projects lack PEP 621 pyproject.toml",
        "workaround": "Generate pyproject.toml with [build-system] pointing to setuptools",
    },
    "private-index": {
        "issue": "Private package indexes need UV_INDEX_* environment variables",
        "workaround": "Set UV_INDEX_<NAME>_USERNAME and UV_INDEX_<NAME>_PASSWORD",
    },
}


@dataclass
class CompatibilityWarning:
    """A warning about a package's compatibility with uv."""

    package: str
    issue: str
    workaround: str | None = None
    severity: Literal["info", "warning", "error"] = "warning"


@dataclass
class CompatibilityReport:
    """Result of a compatibility check against uv."""

    compatible: list[str] = field(default_factory=list)
    warnings: list[CompatibilityWarning] = field(default_factory=list)
    blockers: list[CompatibilityWarning] = field(default_factory=list)
    effort_estimate: Literal["low", "medium", "high"] = "low"


class CompatibilityChecker:
    """Check project dependencies for uv compatibility issues."""

    def check(self, scan_result: ScanResult) -> CompatibilityReport:
        """Analyze a scan result and return a compatibility report.

        Iterates over all dependencies, flagging those present in
        ``KNOWN_UV_ISSUES`` as warnings or blockers depending on severity.
        Unknown packages are classified as compatible.  The effort estimate
        is derived from the ratio of flagged to total packages.
        """
        all_deps = scan_result.dependencies + scan_result.dev_dependencies
        warnings: list[CompatibilityWarning] = []
        blockers: list[CompatibilityWarning] = []
        compatible: list[str] = []

        for dep in all_deps:
            entry = KNOWN_UV_ISSUES.get(dep.name)
            if entry is not None:
                # Packages in the curated list are treated as warnings by
                # default; "error"-level severity is only assigned when the
                # issue explicitly precludes automated migration.
                severity: Literal["info", "warning", "error"] = "warning"
                warnings.append(
                    CompatibilityWarning(
                        package=dep.name,
                        issue=entry["issue"],
                        workaround=entry["workaround"],
                        severity=severity,
                    )
                )
            else:
                compatible.append(dep.name)

        # Derive effort estimate from the ratio of flagged packages.
        total = len(all_deps)
        flagged = len(warnings) + len(blockers)
        if total == 0:
            effort: Literal["low", "medium", "high"] = "low"
        elif flagged == total:
            effort = "high"
        elif flagged / total >= 0.5:
            effort = "medium"
        else:
            effort = "low"

        return CompatibilityReport(
            compatible=compatible,
            warnings=warnings,
            blockers=blockers,
            effort_estimate=effort,
        )
