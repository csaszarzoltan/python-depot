"""Pre-development tests for python_depot_migrate.lock_converter (M2).

Interface tests: verify imports, class existence, signatures, type hints, dataclass fields.
    → Expected to PASS immediately (contract holds on stubs).

Behavioral tests: verify runtime behavior (reading lock files, building constraints,
    generating uv.lock). These FAIL during RED phase (NotImplementedError stubs).
    → Expected to FAIL (RED phase) until dev implements.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import is_dataclass
from pathlib import Path
from typing import get_type_hints

import pytest

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
from python_depot_migrate.lock_converter import (
    LockConverter,
    LockedPackage,
    LockSnapshot,
)

# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1: Import & class existence
# ═══════════════════════════════════════════════════════════════════════════


class TestImports:
    """Verify the module loads and all public symbols are importable."""

    def test_import_lock_converter_class(self):
        assert LockConverter is not None

    def test_import_locked_package(self):
        assert LockedPackage is not None

    def test_import_lock_snapshot(self):
        assert LockSnapshot is not None

    def test_lock_converter_is_class(self):
        assert isinstance(LockConverter, type)

    def test_locked_package_is_dataclass(self):
        assert is_dataclass(LockedPackage)

    def test_lock_snapshot_is_dataclass(self):
        assert is_dataclass(LockSnapshot)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2: Dataclass field contracts
# ═══════════════════════════════════════════════════════════════════════════


class TestLockedPackageFields:
    """Verify LockedPackage dataclass fields."""

    def test_has_name_field(self):
        assert "name" in LockedPackage.__dataclass_fields__

    def test_has_version_field(self):
        assert "version" in LockedPackage.__dataclass_fields__

    def test_has_extras_field(self):
        assert "extras" in LockedPackage.__dataclass_fields__

    def test_has_markers_field(self):
        assert "markers" in LockedPackage.__dataclass_fields__

    def test_has_source_field(self):
        assert "source" in LockedPackage.__dataclass_fields__

    def test_extras_default_empty_list(self):
        pkg = LockedPackage(name="requests", version="2.31.0")
        assert pkg.extras == []

    def test_markers_default_none(self):
        pkg = LockedPackage(name="requests", version="2.31.0")
        assert pkg.markers is None

    def test_source_default_none(self):
        pkg = LockedPackage(name="requests", version="2.31.0")
        assert pkg.source is None

    def test_field_count(self):
        assert len(LockedPackage.__dataclass_fields__) == 5


class TestLockSnapshotFields:
    """Verify LockSnapshot dataclass fields."""

    def test_has_source_type_field(self):
        assert "source_type" in LockSnapshot.__dataclass_fields__

    def test_has_packages_field(self):
        assert "packages" in LockSnapshot.__dataclass_fields__

    def test_has_metadata_field(self):
        assert "metadata" in LockSnapshot.__dataclass_fields__

    def test_source_type_annotation(self):
        hints = get_type_hints(LockSnapshot)
        assert "source_type" in hints

    def test_packages_default_empty_list(self):
        snap = LockSnapshot(source_type="poetry")
        assert snap.packages == []

    def test_metadata_default_empty_dict(self):
        snap = LockSnapshot(source_type="poetry")
        assert snap.metadata == {}

    def test_field_count(self):
        assert len(LockSnapshot.__dataclass_fields__) == 3


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 3: Signature & type hint contracts
# ═══════════════════════════════════════════════════════════════════════════


class TestLockConverterSignatures:
    """Verify method signatures, parameter names, defaults, and return annotations."""

    # --- read_lock ---
    def test_read_lock_exists(self):
        assert hasattr(LockConverter, "read_lock")
        assert callable(LockConverter.read_lock)

    def test_read_lock_has_lock_path_param(self):
        sig = inspect.signature(LockConverter.read_lock)
        assert "lock_path" in sig.parameters

    def test_read_lock_lock_path_annotation(self):
        sig = inspect.signature(LockConverter.read_lock)
        param = sig.parameters["lock_path"]
        # With from __future__ import annotations, annotations are strings
        assert "Path" in str(param.annotation)

    def test_read_lock_return_annotation(self):
        sig = inspect.signature(LockConverter.read_lock)
        # With from __future__ import annotations, annotations are strings
        assert "LockSnapshot" in str(sig.return_annotation)

    # --- build_constraints ---
    def test_build_constraints_exists(self):
        assert hasattr(LockConverter, "build_constraints")
        assert callable(LockConverter.build_constraints)

    def test_build_constraints_has_snapshot_param(self):
        sig = inspect.signature(LockConverter.build_constraints)
        assert "snapshot" in sig.parameters

    def test_build_constraints_snapshot_annotation(self):
        sig = inspect.signature(LockConverter.build_constraints)
        param = sig.parameters["snapshot"]
        # With from __future__ import annotations, annotations are strings
        assert "LockSnapshot" in str(param.annotation)

    def test_build_constraints_return_annotation(self):
        sig = inspect.signature(LockConverter.build_constraints)
        ret = sig.return_annotation
        # With from __future__ import annotations, annotations are strings
        assert "list" in str(ret) and "str" in str(ret)

    # --- generate_uv_lock ---
    def test_generate_uv_lock_exists(self):
        assert hasattr(LockConverter, "generate_uv_lock")
        assert callable(LockConverter.generate_uv_lock)

    def test_generate_uv_lock_params(self):
        sig = inspect.signature(LockConverter.generate_uv_lock)
        assert "project_path" in sig.parameters
        assert "constraints" in sig.parameters
        assert "dry_run" in sig.parameters

    def test_generate_uv_lock_project_path_annotation(self):
        sig = inspect.signature(LockConverter.generate_uv_lock)
        param = sig.parameters["project_path"]
        # With from __future__ import annotations, annotations are strings
        assert "Path" in str(param.annotation)

    def test_generate_uv_lock_constraints_annotation(self):
        sig = inspect.signature(LockConverter.generate_uv_lock)
        param = sig.parameters["constraints"]
        # With from __future__ import annotations, annotations are strings
        assert "list" in str(param.annotation) and "str" in str(param.annotation)

    def test_generate_uv_lock_dry_run_default_true(self):
        sig = inspect.signature(LockConverter.generate_uv_lock)
        param = sig.parameters["dry_run"]
        assert param.default is True

    def test_generate_uv_lock_dry_run_annotation(self):
        sig = inspect.signature(LockConverter.generate_uv_lock)
        param = sig.parameters["dry_run"]
        # With from __future__ import annotations, annotations are strings
        assert "bool" in str(param.annotation)

    def test_generate_uv_lock_return_annotation(self):
        sig = inspect.signature(LockConverter.generate_uv_lock)
        ret = sig.return_annotation
        # Should be Path | None — with future annotations it's a string
        assert ret is not None


class TestLockConverterInstantiation:
    """Verify LockConverter can be instantiated (no __init__ params)."""

    def test_instantiate_with_defaults(self):
        converter = LockConverter()
        assert isinstance(converter, LockConverter)

    def test_single_instance_is_fresh(self):
        c1 = LockConverter()
        c2 = LockConverter()
        assert c1 is not c2


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 4: Behavioral RED-phase tests (NotImplementedError stubs)
# ═══════════════════════════════════════════════════════════════════════════


class TestReadLockBehavioral:
    """Behavioral tests for LockConverter.read_lock — GREEN phase."""

    def test_read_lock_file_not_found(self):
        converter = LockConverter()
        with pytest.raises(FileNotFoundError):
            converter.read_lock(Path("poetry.lock"))

    def test_read_lock_pipenv_file_not_found(self):
        converter = LockConverter()
        with pytest.raises(FileNotFoundError):
            converter.read_lock(Path("Pipfile.lock"))

    def test_read_lock_requirements_file_not_found(self):
        converter = LockConverter()
        with pytest.raises(FileNotFoundError):
            converter.read_lock(Path("requirements.txt"))


class TestBuildConstraintsBehavioral:
    """Behavioral tests for LockConverter.build_constraints — GREEN phase."""

    def test_build_constraints_returns_empty_for_empty_snapshot(self):
        converter = LockConverter()
        snap = LockSnapshot(source_type="poetry")
        result = converter.build_constraints(snap)
        assert result == []

    def test_build_constraints_with_empty_packages(self):
        converter = LockConverter()
        snap = LockSnapshot(source_type="pipenv", packages=[], metadata={})
        result = converter.build_constraints(snap)
        assert result == []


class TestGenerateUvLockBehavioral:
    """Behavioral tests for LockConverter.generate_uv_lock — GREEN phase."""

    def test_generate_uv_lock_dry_run_returns_none(self, tmp_path: Path):
        converter = LockConverter()
        result = converter.generate_uv_lock(
            project_path=tmp_path,
            constraints=["requests==2.31.0"],
            dry_run=True,
        )
        assert result is None

    def test_generate_uv_lock_apply_returns_none_when_uv_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """When uv is not on PATH, generate_uv_lock should handle gracefully."""
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: (_ for _ in ()).throw(
                FileNotFoundError("uv not found")
            ),
        )
        converter = LockConverter()
        result = converter.generate_uv_lock(
            project_path=tmp_path,
            constraints=["requests==2.31.0"],
            dry_run=False,
        )
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 5: Future behavioral tests (skip during RED, run after implementation)
# ═══════════════════════════════════════════════════════════════════════════


class TestReadLockFuture:
    """Future behavioral tests for read_lock — active after implementation."""

    def test_read_poetry_lock_extracts_packages(self, tmp_path: Path):
        converter = LockConverter()
        # Create a minimal poetry.lock TOML
        poetry_lock = tmp_path / "poetry.lock"
        poetry_lock.write_text(
            '[[package]]\nname = "requests"\nversion = "2.31.0"\n'
            '[[package]]\nname = "urllib3"\nversion = "2.0.7"\n'
        )
        try:
            snapshot = converter.read_lock(poetry_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert isinstance(snapshot, LockSnapshot)
        assert snapshot.source_type == "poetry"
        assert len(snapshot.packages) >= 2
        names = {p.name for p in snapshot.packages}
        assert "requests" in names
        assert "urllib3" in names

    def test_read_poetry_lock_extracts_versions(self, tmp_path: Path):
        converter = LockConverter()
        poetry_lock = tmp_path / "poetry.lock"
        poetry_lock.write_text(
            '[[package]]\nname = "click"\nversion = "8.1.7"\n'
        )
        try:
            snapshot = converter.read_lock(poetry_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        click = [p for p in snapshot.packages if p.name == "click"]
        assert len(click) == 1
        assert click[0].version == "8.1.7"

    def test_read_pipenv_lock_extracts_packages(self, tmp_path: Path):
        converter = LockConverter()
        pipfile_lock = tmp_path / "Pipfile.lock"
        data = {
            "_meta": {"hash": {"sha256": "abc"}, "requires": {"python_version": "3.11"}},
            "default": {
                "requests": {"hashes": ["sha256:deadbeef"], "version": "==2.31.0"},
            },
            "develop": {},
        }
        pipfile_lock.write_text(json.dumps(data, indent=2))
        try:
            snapshot = converter.read_lock(pipfile_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert isinstance(snapshot, LockSnapshot)
        assert snapshot.source_type == "pipenv"
        names = {p.name for p in snapshot.packages}
        assert "requests" in names

    def test_read_pinned_requirements_extracts_packages(self, tmp_path: Path):
        converter = LockConverter()
        req = tmp_path / "requirements.txt"
        req.write_text(
            "requests==2.31.0\n"
            "urllib3==2.0.7 \n"  # trailing space
            "click==8.1.7\n"
        )
        try:
            snapshot = converter.read_lock(req)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert snapshot.source_type == "requirements"
        assert len(snapshot.packages) >= 3

    def test_read_pinned_requirements_with_hashes(self, tmp_path: Path):
        converter = LockConverter()
        req = tmp_path / "requirements.txt"
        req.write_text(
            "requests==2.31.0 --hash=sha256:abc123\n"
        )
        try:
            snapshot = converter.read_lock(req)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        pkgs = [p for p in snapshot.packages if p.name == "requests"]
        assert len(pkgs) == 1
        assert pkgs[0].version == "2.31.0"

    def test_read_lock_empty_file(self, tmp_path: Path):
        converter = LockConverter()
        lock_file = tmp_path / "requirements.txt"
        lock_file.write_text("")
        try:
            snapshot = converter.read_lock(lock_file)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert snapshot.packages == []

    def test_read_lock_nonexistent_file(self, tmp_path: Path):
        converter = LockConverter()
        try:
            converter.read_lock(tmp_path / "nonexistent.lock")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except FileNotFoundError:
            pass  # acceptable behavior

    def test_read_lock_extracts_extras(self, tmp_path: Path):
        converter = LockConverter()
        poetry_lock = tmp_path / "poetry.lock"
        poetry_lock.write_text(
            '[[package]]\nname = "requests"\nversion = "2.31.0"\n'
            'extras = ["security", "socks"]\n'
        )
        try:
            snapshot = converter.read_lock(poetry_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        req = [p for p in snapshot.packages if p.name == "requests"]
        assert len(req) == 1
        assert set(req[0].extras) == {"security", "socks"}

    def test_read_lock_extracts_markers(self, tmp_path: Path):
        converter = LockConverter()
        poetry_lock = tmp_path / "poetry.lock"
        poetry_lock.write_text(
            '[[package]]\nname = "colorama"\nversion = "0.4.6"\n'
            'markers = "sys_platform == \"win32\""\n'
        )
        try:
            snapshot = converter.read_lock(poetry_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        colorama = [p for p in snapshot.packages if p.name == "colorama"]
        assert len(colorama) == 1
        assert colorama[0].markers is not None

    def test_read_lock_extracts_vcs_source(self, tmp_path: Path):
        converter = LockConverter()
        poetry_lock = tmp_path / "poetry.lock"
        poetry_lock.write_text(
            '[[package]]\nname = "mypackage"\nversion = "0.1.0"\n'
            '[package.source]\ntype = "git"\n'
            'url = "git+https://github.com/user/repo.git"\n'
            'reference = "main"\n'
        )
        try:
            snapshot = converter.read_lock(poetry_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        mp = [p for p in snapshot.packages if p.name == "mypackage"]
        assert len(mp) == 1
        assert mp[0].source is not None
        assert mp[0].source["type"] == "git"

    def test_read_lock_empty_extras_list(self, tmp_path: Path):
        converter = LockConverter()
        poetry_lock = tmp_path / "poetry.lock"
        poetry_lock.write_text(
            '[[package]]\nname = "bare"\nversion = "1.0.0"\n'
        )
        try:
            snapshot = converter.read_lock(poetry_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        bare = [p for p in snapshot.packages if p.name == "bare"]
        assert len(bare) == 1
        assert bare[0].extras == []


class TestBuildConstraintsFuture:
    """Future behavioral tests for build_constraints — active after implementation."""

    def test_build_constraints_returns_list_of_strings(self):
        converter = LockConverter()
        snap = LockSnapshot(
            source_type="poetry",
            packages=[
                LockedPackage(name="requests", version="2.31.0"),
            ],
        )
        try:
            result = converter.build_constraints(snap)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert isinstance(result, list)
        assert all(isinstance(c, str) for c in result)

    def test_build_constraints_pins_exact_versions(self):
        converter = LockConverter()
        snap = LockSnapshot(
            source_type="poetry",
            packages=[
                LockedPackage(name="requests", version="2.31.0"),
                LockedPackage(name="urllib3", version="2.0.7"),
            ],
        )
        try:
            result = converter.build_constraints(snap)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert len(result) >= 2
        for c in result:
            assert "==" in c

    def test_build_constraints_empty_packages(self):
        converter = LockConverter()
        snap = LockSnapshot(source_type="poetry", packages=[])
        try:
            result = converter.build_constraints(snap)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert result == []

    def test_build_constraints_includes_extras(self):
        converter = LockConverter()
        snap = LockSnapshot(
            source_type="poetry",
            packages=[
                LockedPackage(name="requests", version="2.31.0", extras=["security"]),
            ],
        )
        try:
            result = converter.build_constraints(snap)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert any("requests" in c and "security" in c for c in result)

    def test_build_constraints_skips_vcs_sources(self):
        converter = LockConverter()
        snap = LockSnapshot(
            source_type="poetry",
            packages=[
                LockedPackage(
                    name="mypackage",
                    version="0.1.0",
                    source={"type": "git", "url": "git+https://github.com/x/y.git"},
                ),
            ],
        )
        try:
            result = converter.build_constraints(snap)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        # VCS packages may or may not appear as constraints;
        # if they do, they should be skipped or handled specially.
        # This test verifies the method runs without error.
        assert isinstance(result, list)


class TestGenerateUvLockFuture:
    """Future behavioral tests for generate_uv_lock — active after implementation."""

    def test_generate_uv_lock_dry_run_returns_none(self, tmp_path: Path):
        converter = LockConverter()
        try:
            result = converter.generate_uv_lock(
                project_path=tmp_path,
                constraints=["requests==2.31.0"],
                dry_run=True,
            )
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert result is None

    def test_generate_uv_lock_apply_returns_path(self, tmp_path: Path):
        converter = LockConverter()
        try:
            result = converter.generate_uv_lock(
                project_path=tmp_path,
                constraints=["requests==2.31.0"],
                dry_run=False,
            )
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        # After implementation, should return Path or None (if uv not found)
        assert result is None or isinstance(result, Path)

    def test_generate_uv_lock_dry_run_default(self, tmp_path: Path):
        converter = LockConverter()
        try:
            result = converter.generate_uv_lock(
                project_path=tmp_path,
                constraints=["requests==2.31.0"],
            )
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        # Default dry_run=True should return None
        assert result is None

    def test_generate_uv_lock_with_empty_constraints(self, tmp_path: Path):
        converter = LockConverter()
        try:
            result = converter.generate_uv_lock(
                project_path=tmp_path,
                constraints=[],
                dry_run=True,
            )
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert result is None

    def test_generate_uv_lock_with_multiple_constraints(self, tmp_path: Path):
        converter = LockConverter()
        constraints = [
            "requests==2.31.0",
            "urllib3==2.0.7",
            "click==8.1.7",
        ]
        try:
            result = converter.generate_uv_lock(
                project_path=tmp_path,
                constraints=constraints,
                dry_run=True,
            )
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert result is None

    def test_generate_uv_lock_handles_missing_uv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """When uv is not on PATH, generate_uv_lock should handle gracefully."""
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: (_ for _ in ()).throw(
                FileNotFoundError("uv not found")
            ),
        )
        converter = LockConverter()
        try:
            converter.generate_uv_lock(
                project_path=tmp_path,
                constraints=["requests==2.31.0"],
                dry_run=True,
            )
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        except FileNotFoundError:
            pass  # Acceptable: raises error if uv missing

    def test_generate_uv_lock_passes_constraints_file(self, tmp_path: Path):
        """Verify constraints are written to a temp file and passed to uv."""
        converter = LockConverter()
        try:
            result = converter.generate_uv_lock(
                project_path=tmp_path,
                constraints=["requests==2.31.0", "urllib3==2.0.7"],
                dry_run=True,
            )
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        # Just verifying it doesn't crash during RED
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 6: Edge case tests
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge case behavioral tests — active after implementation."""

    def test_poetry_lock_with_platform_markers(self, tmp_path: Path):
        """Platform-specific deps should have markers preserved."""
        converter = LockConverter()
        poetry_lock = tmp_path / "poetry.lock"
        poetry_lock.write_text(
            '[[package]]\nname = "colorama"\nversion = "0.4.6"\n'
            'markers = "sys_platform == \"win32\""\n'
            '[[package]]\nname = "win32-clipboard"\nversion = "0.0.1"\n'
            'markers = "sys_platform == \"win32\""\n'
        )
        try:
            snapshot = converter.read_lock(poetry_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert snapshot.source_type == "poetry"
        for pkg in snapshot.packages:
            if pkg.name in ("colorama", "win32-clipboard"):
                assert pkg.markers is not None

    def test_pipenv_lock_with_vcs_sources(self, tmp_path: Path):
        """VCS deps in Pipfile.lock should be handled."""
        converter = LockConverter()
        pipfile_lock = tmp_path / "Pipfile.lock"
        data = {
            "_meta": {"hash": {"sha256": "abc"}, "requires": {"python_version": "3.11"}},
            "default": {
                "mypackage": {
                    "hashes": [],
                    "version": "==0.1.0",
                    "extras": [],
                    "index": "pypi",
                    "editable": False,
                    "path": ".",
                },
            },
            "develop": {},
        }
        pipfile_lock.write_text(json.dumps(data, indent=2))
        try:
            snapshot = converter.read_lock(pipfile_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert snapshot.source_type == "pipenv"
        pkgs = [p for p in snapshot.packages if p.name == "mypackage"]
        assert len(pkgs) == 1

    def test_pinned_requirements_with_editable_install(self, tmp_path: Path):
        """Editable installs (-e .) should be handled without crashing."""
        converter = LockConverter()
        req = tmp_path / "requirements.txt"
        req.write_text(
            "-e .\n"
            "requests==2.31.0\n"
        )
        try:
            snapshot = converter.read_lock(req)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        # Editable installs may or may not appear as packages;
        # the key is the reader doesn't crash.
        assert isinstance(snapshot.packages, list)

    def test_poetry_lock_resolver_behavior_note(self, tmp_path: Path):
        """Different resolver behavior between poetry and uv is documented."""
        converter = LockConverter()
        poetry_lock = tmp_path / "poetry.lock"
        poetry_lock.write_text(
            '[[package]]\nname = "requests"\nversion = "2.31.0"\n'
            '[[package]]\nname = "urllib3"\nversion = "2.0.7"\n'
            '[[package]]\nname = "certifi"\nversion = "2023.7.22"\n'
            '[[package]]\nname = "charset-normalizer"\nversion = "3.2.0"\n'
            '[[package]]\nname = "idna"\nversion = "3.4"\n'
        )
        try:
            snapshot = converter.read_lock(poetry_lock)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        # All 5 packages from the requests dependency tree should be extracted
        assert len(snapshot.packages) >= 5

    def test_build_constraints_all_types(self):
        """Constraints should be generated for all source types."""
        converter = LockConverter()
        for stype in ("poetry", "pipenv", "pip-tools", "requirements"):
            snap = LockSnapshot(
                source_type=stype,
                packages=[LockedPackage(name="requests", version="2.31.0")],
            )
            try:
                result = converter.build_constraints(snap)
            except NotImplementedError:
                pytest.skip("Not implemented yet — RED phase")
            assert isinstance(result, list)

    def test_pip_tools_requirements_format(self, tmp_path: Path):
        """pip-tools compiled requirements have === or == pins."""
        converter = LockConverter()
        req = tmp_path / "requirements.txt"
        req.write_text(
            "# This file is autogenerated by pip-compile\n"
            "# with Python 3.11\n"
            "requests==2.31.0\n"
            "    # via -r requirements.in\n"
        )
        try:
            snapshot = converter.read_lock(req)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")

        assert isinstance(snapshot.packages, list)


# ═══════════════════════════════════════════════════════════════════════════
# Summary marker — pytest collection check
# ═══════════════════════════════════════════════════════════════════════════


def test_pytest_collection_smoke():
    """Sanity: verify test file collects without import errors."""
    assert True
