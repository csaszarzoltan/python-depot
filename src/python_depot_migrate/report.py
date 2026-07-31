"""Migration report generator — produce human-readable and JSON reports."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from python_depot_migrate.scanner import MigrationResult


@dataclass
class MigrationDiff:
    """Before/after diff for a single file migration."""

    original: str
    updated: str
    changes: list[str]


class MigrationReportGenerator:
    """Generate migration reports in markdown and JSON formats."""

    def generate(self, results: MigrationResult, report_path: Path | None = None) -> str:
        """Produce a markdown report and optionally write it to *report_path*.

        The report includes before/after comparison, rollback instructions,
        migrated file listing, and any errors encountered during migration.
        """
        content = self.generate_markdown(results)
        if report_path is not None:
            report_path.write_text(content, encoding="utf-8")
        return content

    def generate_markdown(self, results: MigrationResult) -> str:
        """Return a human-readable markdown migration report."""
        sections: list[str] = []

        # Header
        sections.append(f"# Migration Report: {results.project_path}")
        sections.append("")

        # Status
        status = "Dry Run" if results.dry_run else "Applied"
        success_text = "Success" if results.success else "Failed"
        sections.append(f"**Status:** {success_text} ({status})")
        sections.append("")

        # Before / After comparison
        sections.append("## Before / After Comparison")
        sections.append("")
        sections.append(self._before_after_comparison(results))
        sections.append("")

        # Migrated files
        if results.files_generated:
            sections.append("## Migrated Files")
            sections.append("")
            for f in results.files_generated:
                sections.append(f"- `{f}`")
            sections.append("")

        # Errors
        if results.errors:
            sections.append("## Errors")
            sections.append("")
            for err in results.errors:
                sections.append(f"- {err}")
            sections.append("")

        # Warnings
        if results.warnings:
            sections.append("## Warnings")
            sections.append("")
            for warn in results.warnings:
                sections.append(f"- {warn}")
            sections.append("")

        # Rollback instructions
        sections.append("## Rollback Instructions")
        sections.append("")
        sections.append(self._rollback_instructions(results))
        sections.append("")

        return "\n".join(sections)

    def generate_json(self, results: MigrationResult) -> str:
        """Return a JSON migration report."""
        data: dict[str, object] = {
            "project_path": str(results.project_path),
            "success": results.success,
            "dry_run": results.dry_run,
            "summary": f"{results.before_summary} -> {results.after_summary}",
            "before_summary": results.before_summary,
            "after_summary": results.after_summary,
            "files_changed": [str(f) for f in results.files_changed],
            "files_generated": [str(f) for f in results.files_generated],
            "warnings": results.warnings,
            "errors": results.errors,
            "rollback": self._rollback_instructions(results),
            "before_after": self._before_after_comparison(results),
        }
        return json.dumps(data, indent=2)

    def _rollback_instructions(self, results: MigrationResult) -> str:
        """Return markdown rollback instructions for the migration."""
        if results.dry_run:
            return (
                "This was a dry run — no changes were applied. "
                "No rollback is necessary."
            )
        if not results.migrated_files:
            return (
                "No files were migrated. "
                "No rollback is necessary."
            )
        lines = [
            "To revert this migration:",
            "",
        ]
        for f in results.migrated_files:
            lines.append(f"- Restore `{f}` from version control or backup")
        lines.append("")
        lines.append(
            "If you ran `uv lock`, delete the generated `uv.lock` file."
        )
        return "\n".join(lines)

    def _before_after_comparison(self, results: MigrationResult) -> str:
        """Return a before/after comparison section."""
        before = results.before_summary or "(no before summary available)"
        after = results.after_summary or "(no after summary available)"
        lines = [
            "| Aspect | Before | After |",
            "|--------|--------|-------|",
            f"| Summary | {before} | {after} |",
            f"| Path | {results.project_path} | {results.project_path} |",
        ]
        return "\n".join(lines)
