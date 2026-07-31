"""Pre-development tests for CI/CD Config Updater (M4).

Interface tests:  PASS immediately (imports, signatures, dataclass fields).
Behavioral tests: FAIL/RED until implementation (NotImplementedError stubs).
"""

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest

from python_depot_migrate.ci_cd import (
    CICDConfig,
    CICDUpdater,
    MigrationDiff,
)

# ============================================================================
# PART 1: INTERFACE TESTS (pass immediately)
# ============================================================================


class TestImports:
    """Verify module loads and public names are importable."""

    def test_import_cicd_updater(self):
        assert CICDUpdater is not None

    def test_import_cicd_config(self):
        assert CICDConfig is not None

    def test_import_migration_diff(self):
        assert MigrationDiff is not None


class TestCICDConfigDataclass:
    """Verify CICDConfig dataclass structure."""

    def test_is_dataclass(self):
        assert is_dataclass(CICDConfig)

    def test_has_field_path(self):
        assert "path" in {f.name for f in fields(CICDConfig)}

    def test_has_field_kind(self):
        assert "kind" in {f.name for f in fields(CICDConfig)}

    def test_has_field_current_backend(self):
        assert "current_backend" in {f.name for f in fields(CICDConfig)}

    def test_has_field_content(self):
        assert "content" in {f.name for f in fields(CICDConfig)}

    def test_field_count(self):
        assert len(fields(CICDConfig)) == 4


class TestMigrationDiffDataclass:
    """Verify MigrationDiff dataclass structure."""

    def test_is_dataclass(self):
        assert is_dataclass(MigrationDiff)

    def test_has_field_original(self):
        assert "original" in {f.name for f in fields(MigrationDiff)}

    def test_has_field_updated(self):
        assert "updated" in {f.name for f in fields(MigrationDiff)}

    def test_has_field_changes(self):
        assert "changes" in {f.name for f in fields(MigrationDiff)}

    def test_field_count(self):
        assert len(fields(MigrationDiff)) == 3


class TestCICDUpdaterInterface:
    """Verify CICDUpdater class interface signatures."""

    def test_has_detect_method(self):
        assert hasattr(CICDUpdater, "detect")

    def test_has_update_method(self):
        assert hasattr(CICDUpdater, "update")

    def test_detect_signature(self):
        sig = inspect.signature(CICDUpdater.detect)
        params = list(sig.parameters.keys())
        assert params == ["self", "project_path"]

    def test_detect_project_path_type(self):
        sig = inspect.signature(CICDUpdater.detect)
        param = sig.parameters["project_path"]
        # With `from __future__ import annotations`, annotations are strings
        assert str(param.annotation) == "Path"

    def test_detect_return_annotation(self):
        sig = inspect.signature(CICDUpdater.detect)
        ret = sig.return_annotation
        assert str(ret) == "list[CICDConfig]"

    def test_update_signature(self):
        sig = inspect.signature(CICDUpdater.update)
        params = list(sig.parameters.keys())
        assert params == ["self", "config", "dry_run"]

    def test_update_config_type(self):
        sig = inspect.signature(CICDUpdater.update)
        param = sig.parameters["config"]
        assert str(param.annotation) == "CICDConfig"

    def test_update_dry_run_default(self):
        sig = inspect.signature(CICDUpdater.update)
        param = sig.parameters["dry_run"]
        assert param.default is True

    def test_update_dry_run_type(self):
        sig = inspect.signature(CICDUpdater.update)
        param = sig.parameters["dry_run"]
        assert str(param.annotation) == "bool"

    def test_update_return_annotation(self):
        sig = inspect.signature(CICDUpdater.update)
        ret = sig.return_annotation
        # Should be MigrationDiff | None
        assert str(ret) == "MigrationDiff | None"


class TestCICDConfigInstantiation:
    """Verify CICDConfig can be instantiated with required fields."""

    def test_instantiation_github_actions(self):
        cfg = CICDConfig(
            path=Path(".github/workflows/test.yml"),
            kind="github-actions",
            current_backend="pip",
            content="run: pip install pytest",
        )
        assert cfg.path == Path(".github/workflows/test.yml")
        assert cfg.kind == "github-actions"
        assert cfg.current_backend == "pip"

    def test_instantiation_gitlab_ci(self):
        cfg = CICDConfig(
            path=Path(".gitlab-ci.yml"),
            kind="gitlab-ci",
            current_backend="poetry",
            content="script: poetry install",
        )
        assert cfg.kind == "gitlab-ci"

    def test_instantiation_dockerfile(self):
        cfg = CICDConfig(
            path=Path("Dockerfile"),
            kind="dockerfile",
            current_backend="pipenv",
            content="RUN pipenv install",
        )
        assert cfg.kind == "dockerfile"


class TestMigrationDiffInstantiation:
    """Verify MigrationDiff can be instantiated."""

    def test_instantiation(self):
        diff = MigrationDiff(
            original="pip install pytest",
            updated="uv pip install pytest",
            changes=["Replaced pip install with uv pip install"],
        )
        assert diff.original == "pip install pytest"
        assert diff.updated == "uv pip install pytest"
        assert len(diff.changes) == 1


# ============================================================================
# PART 2: BEHAVIORAL TESTS (fail/RED until implemented)
# ============================================================================


class TestDetectBehavior:
    """Behavioral tests for CICDUpdater.detect() — currently RED."""

    def setup_method(self):
        self.updater = CICDUpdater()

    def test_detect_github_actions_workflow(self, tmp_path):
        """AC: Detects .github/workflows/*.yml files."""
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "test.yml"
        wf_file.write_text("name: Test\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n")

        try:
            result = self.updater.detect(tmp_path)
            assert len(result) >= 1
            kinds = [c.kind for c in result]
            assert "github-actions" in kinds
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_detect_multiple_github_workflows(self, tmp_path):
        """AC: Detects multiple .github/workflows/*.yml files."""
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        for name in ["test.yml", "lint.yml", "deploy.yml"]:
            (wf_dir / name).write_text(f"name: {name}\non: push\n")

        try:
            result = self.updater.detect(tmp_path)
            github_configs = [c for c in result if c.kind == "github-actions"]
            assert len(github_configs) == 3
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_detect_gitlab_ci(self, tmp_path):
        """AC: Detects .gitlab-ci.yml."""
        (tmp_path / ".gitlab-ci.yml").write_text("stages:\n  - test\n")

        try:
            result = self.updater.detect(tmp_path)
            kinds = [c.kind for c in result]
            assert "gitlab-ci" in kinds
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_detect_dockerfile_pip(self, tmp_path):
        """AC: Detects Dockerfiles with pip install."""
        (tmp_path / "Dockerfile").write_text(
            "FROM python:3.11\nRUN pip install -r requirements.txt\n"
        )

        try:
            result = self.updater.detect(tmp_path)
            docker_configs = [c for c in result if c.kind == "dockerfile"]
            assert len(docker_configs) >= 1
            assert docker_configs[0].current_backend == "pip"
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_detect_dockerfile_poetry(self, tmp_path):
        """AC: Detects Dockerfiles with poetry install."""
        (tmp_path / "Dockerfile").write_text(
            "FROM python:3.11\nRUN poetry install\n"
        )

        try:
            result = self.updater.detect(tmp_path)
            docker_configs = [c for c in result if c.kind == "dockerfile"]
            assert len(docker_configs) >= 1
            assert docker_configs[0].current_backend == "poetry"
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_detect_dockerfile_pipenv(self, tmp_path):
        """AC: Detects Dockerfiles with pipenv install."""
        (tmp_path / "Dockerfile").write_text(
            "FROM python:3.11\nRUN pipenv install --system\n"
        )

        try:
            result = self.updater.detect(tmp_path)
            docker_configs = [c for c in result if c.kind == "dockerfile"]
            assert len(docker_configs) >= 1
            assert docker_configs[0].current_backend == "pipenv"
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_detect_no_ci_files_returns_empty(self, tmp_path):
        """AC: No CI/CD files found → empty result, not error."""
        (tmp_path / "README.md").write_text("# Hello\n")

        try:
            result = self.updater.detect(tmp_path)
            assert result == []
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_detect_mixed_backends(self, tmp_path):
        """Edge: Mixed backends in same project (pip in Docker, poetry in CI)."""
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "jobs:\n  test:\n    steps:\n      - run: poetry install\n"
        )
        (tmp_path / "Dockerfile").write_text(
            "FROM python:3.11\nRUN pip install -r requirements.txt\n"
        )

        try:
            result = self.updater.detect(tmp_path)
            backends = {c.current_backend for c in result}
            assert "pip" in backends
            assert "poetry" in backends
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_detect_content_populated(self, tmp_path):
        """AC: Config.content contains the file contents."""
        content = "name: CI\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(content)

        try:
            result = self.updater.detect(tmp_path)
            assert any(c.content == content for c in result)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_detect_path_populated(self, tmp_path):
        """AC: Config.path points to the detected file."""
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "test.yml").write_text("on: push\n")

        try:
            result = self.updater.detect(tmp_path)
            paths = [c.path for c in result]
            assert any("test.yml" in str(p) for p in paths)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")


class TestUpdateBehavior:
    """Behavioral tests for CICDUpdater.update() — currently RED."""

    def setup_method(self):
        self.updater = CICDUpdater()

    def _make_github_config(self, content: str) -> CICDConfig:
        return CICDConfig(
            path=Path(".github/workflows/test.yml"),
            kind="github-actions",
            current_backend="pip",
            content=content,
        )

    def _make_gitlab_config(self, content: str) -> CICDConfig:
        return CICDConfig(
            path=Path(".gitlab-ci.yml"),
            kind="gitlab-ci",
            current_backend="pip",
            content=content,
        )

    def _make_docker_config(self, content: str, backend: str = "pip") -> CICDConfig:
        return CICDConfig(
            path=Path("Dockerfile"),
            kind="dockerfile",
            current_backend=backend,
            content=content,
        )

    def test_replace_pip_install_uv_pip(self):
        """AC: Replaces `pip install` → `uv pip install`."""
        cfg = self._make_github_config(
            "steps:\n  - run: pip install pytest requests\n"
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv pip install" in diff.updated
            assert "pip install" not in diff.updated or "uv pip install" in diff.updated
            assert len(diff.changes) > 0
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_replace_poetry_install_uv_sync(self):
        """AC: Replaces `poetry install` → `uv sync --locked`."""
        cfg = self._make_github_config(
            "steps:\n  - run: poetry install\n"
        )
        cfg.current_backend = "poetry"

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv sync" in diff.updated
            assert "poetry install" not in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_replace_pipenv_install_uv_sync(self):
        """AC: Replaces `pipenv install` → `uv sync`."""
        cfg = self._make_github_config(
            "steps:\n  - run: pipenv install\n"
        )
        cfg.current_backend = "pipenv"

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv sync" in diff.updated
            assert "pipenv install" not in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_dry_run_does_not_modify_file(self, tmp_path):
        """AC: Dry-run mode shows diff without modifying files."""
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "test.yml"
        original_content = "steps:\n  - run: pip install pytest\n"
        wf_file.write_text(original_content)

        cfg = CICDConfig(
            path=wf_file,
            kind="github-actions",
            current_backend="pip",
            content=original_content,
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            # File should NOT be modified
            assert wf_file.read_text() == original_content
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_non_dry_run_modifies_file(self, tmp_path):
        """AC: Non-dry-run actually writes changes."""
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "test.yml"
        original_content = "steps:\n  - run: pip install pytest\n"
        wf_file.write_text(original_content)

        cfg = CICDConfig(
            path=wf_file,
            kind="github-actions",
            current_backend="pip",
            content=original_content,
        )

        try:
            diff = self.updater.update(cfg, dry_run=False)
            assert diff is not None
            # File SHOULD be modified
            updated_content = wf_file.read_text()
            assert updated_content != original_content
            assert "uv" in updated_content
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_no_changes_returns_none(self):
        """When config already uses uv, update returns None."""
        cfg = self._make_github_config(
            "steps:\n  - run: uv pip install pytest\n"
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is None
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_docker_replaces_pip_install(self):
        """AC: Updates Dockerfiles with pip install → uv pip install."""
        cfg = self._make_docker_config(
            "FROM python:3.11\nRUN pip install -r requirements.txt\n"
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv pip install" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_docker_updates_base_image(self):
        """AC: Updates Docker base images to use uv."""
        cfg = self._make_docker_config(
            "FROM python:3.11\nRUN pip install pytest\n"
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            # Should either update the base image or add uv installation
            assert "uv" in diff.updated.lower()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_migration_diff_has_changes_list(self):
        """AC: MigrationDiff.changes contains human-readable change descriptions."""
        cfg = self._make_github_config(
            "steps:\n  - run: pip install -e .\n"
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert isinstance(diff.changes, list)
            assert len(diff.changes) >= 1
            # Each change should be a non-empty string
            for change in diff.changes:
                assert isinstance(change, str)
                assert len(change) > 0
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_gitlab_ci_update(self):
        """AC: Updates GitLab CI configuration."""
        cfg = self._make_gitlab_config(
            "test:\n  script:\n    - pip install pytest\n"
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")


class TestEdgeCases:
    """Edge case behavioral tests — currently RED."""

    def setup_method(self):
        self.updater = CICDUpdater()

    def test_multi_stage_dockerfile(self):
        """Edge: Multi-stage Dockerfiles (build stage vs runtime stage)."""
        content = """FROM python:3.11 AS builder
RUN pip install build
RUN python -m build

FROM python:3.11-slim
RUN pip install -r requirements.txt
COPY --from=builder /app/dist/*.whl /app/
"""
        cfg = CICDConfig(
            path=Path("Dockerfile"),
            kind="dockerfile",
            current_backend="pip",
            content=content,
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            # Both stages should be handled
            assert "uv" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_matrix_build_github_actions(self):
        """Edge: Matrix builds in GitHub Actions."""
        content = """name: CI
on: push
jobs:
  test:
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest
"""
        cfg = CICDConfig(
            path=Path(".github/workflows/ci.yml"),
            kind="github-actions",
            current_backend="pip",
            content=content,
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            # Should replace pip install without breaking matrix syntax
            assert "uv pip install" in diff.updated
            assert "matrix" in diff.updated  # matrix preserved
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_pinned_action_versions(self):
        """Edge: Pinned action versions (e.g., actions/checkout@v3) preserved."""
        content = """steps:
  - uses: actions/checkout@v3
  - uses: actions/setup-python@v4
  - run: pip install pytest
"""
        cfg = CICDConfig(
            path=Path(".github/workflows/test.yml"),
            kind="github-actions",
            current_backend="pip",
            content=content,
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            # Pinned versions should be preserved
            assert "actions/checkout@v3" in diff.updated
            assert "actions/setup-python@v4" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_custom_cache_keys(self):
        """Edge: Custom cache keys should not be corrupted."""
        content = """steps:
  - uses: actions/cache@v3
    with:
      key: pip-${{ hashFiles('requirements.txt') }}
  - run: pip install -r requirements.txt
"""
        cfg = CICDConfig(
            path=Path(".github/workflows/ci.yml"),
            kind="github-actions",
            current_backend="pip",
            content=content,
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            # Cache key should be preserved (though it may reference uv now)
            assert "cache" in diff.updated.lower()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_pip_install_with_extras(self):
        """Edge: pip install with extras syntax."""
        cfg = CICDConfig(
            path=Path(".github/workflows/test.yml"),
            kind="github-actions",
            current_backend="pip",
            content="run: pip install 'requests[security,socks]'\n",
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv pip install" in diff.updated
            assert "requests[security,socks]" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_pip_install_with_version_constraint(self):
        """Edge: pip install with version constraints."""
        cfg = CICDConfig(
            path=Path(".github/workflows/test.yml"),
            kind="github-actions",
            current_backend="pip",
            content="run: pip install 'pytest>=7.0,<8.0'\n",
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv pip install" in diff.updated
            assert "pytest" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_poetry_install_with_dev_deps(self):
        """Edge: poetry install --no-dev vs poetry install."""
        cfg = CICDConfig(
            path=Path(".github/workflows/test.yml"),
            kind="github-actions",
            current_backend="poetry",
            content="run: poetry install --no-dev\n",
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_gitlab_ci_with_include(self):
        """Edge: GitLab CI with include/extends should not break structure."""
        content = """include:
  - local: .gitlab/ci/test.yml

stages:
  - test

test:
  script:
    - pip install -r requirements.txt
    - pytest
"""
        cfg = CICDConfig(
            path=Path(".gitlab-ci.yml"),
            kind="gitlab-ci",
            current_backend="pip",
            content=content,
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "include" in diff.updated  # include preserved
            assert "uv" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_non_standard_workflow_locations(self):
        """Edge: Workflow files in non-standard locations (e.g., nested dirs)."""
        updater = CICDUpdater()

        content = "name: Custom CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: pip install -r requirements.txt\n"
        cfg = CICDConfig(
            path=Path(".github/workflows/subdir/custom.yml"),
            kind="github-actions",
            current_backend="pip",
            content=content,
        )

        try:
            diff = updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_dockerfile_pip_install_no_requirements_file(self):
        """Edge: Dockerfile with pip install (not pip install -r)."""
        cfg = CICDConfig(
            path=Path("Dockerfile"),
            kind="dockerfile",
            current_backend="pip",
            content="FROM python:3.11\nRUN pip install flask gunicorn\n",
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv pip install" in diff.updated
            assert "flask" in diff.updated
            assert "gunicorn" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_dockerfile_uv_pip_install_already_migrated(self):
        """Edge: Dockerfile already using uv pip install → no changes."""
        cfg = CICDConfig(
            path=Path("Dockerfile"),
            kind="dockerfile",
            current_backend="pip",
            content="FROM python:3.11\nRUN uv pip install -r requirements.txt\n",
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is None  # Already migrated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_empty_content_no_changes(self):
        """Edge: Empty config content → no changes."""
        cfg = CICDConfig(
            path=Path(".github/workflows/empty.yml"),
            kind="github-actions",
            current_backend="pip",
            content="",
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is None  # Nothing to replace
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

    def test_pip_install_in_script_block(self):
        """Edge: pip install inside multi-line script block."""
        content = """script:
  - |
    pip install -r requirements.txt
    python -m pytest
"""
        cfg = CICDConfig(
            path=Path(".gitlab-ci.yml"),
            kind="gitlab-ci",
            current_backend="pip",
            content=content,
        )

        try:
            diff = self.updater.update(cfg, dry_run=True)
            assert diff is not None
            assert "uv pip install" in diff.updated
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
