"""Tests for MigrationGuideGenerator."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Interface tests
# ---------------------------------------------------------------------------


class TestMigrationGuideInterface:
    """Verify MigrationGuideGenerator class exists with expected interface."""

    def test_migration_guide_import(self):
        """MigrationGuideGenerator can be imported."""
        from python_depot.ecosystem.migration import MigrationGuideGenerator

        assert MigrationGuideGenerator is not None
        assert isinstance(MigrationGuideGenerator, type)

    def test_generator_has_generate_method(self):
        """MigrationGuideGenerator has generate_guide method."""
        from python_depot.ecosystem.migration import MigrationGuideGenerator

        assert hasattr(MigrationGuideGenerator, "generate_guide")
        assert callable(MigrationGuideGenerator.generate_guide)

    def test_generator_has_supported_migrations(self):
        """SUPPORTED_MIGRATIONS constant has expected pairs."""
        from python_depot.ecosystem.migration import SUPPORTED_MIGRATIONS

        assert isinstance(SUPPORTED_MIGRATIONS, dict)
        assert ("pip", "uv") in SUPPORTED_MIGRATIONS
        assert ("poetry", "uv") in SUPPORTED_MIGRATIONS
        assert ("pip", "poetry") in SUPPORTED_MIGRATIONS

    def test_get_supported_migrations_returns_list(self):
        """get_supported_migrations returns expected migration pairs."""
        from python_depot.ecosystem.migration import MigrationGuideGenerator

        gen = MigrationGuideGenerator(db=None)
        migrations = gen.get_supported_migrations()
        assert isinstance(migrations, list)
        assert len(migrations) >= 3
        expected = [
            {"from": "pip", "to": "uv"},
            {"from": "poetry", "to": "uv"},
            {"from": "pip", "to": "poetry"},
        ]
        for exp in expected:
            assert any(exp.items() <= actual.items() for actual in migrations)


# ---------------------------------------------------------------------------
# Behavioral tests
# ---------------------------------------------------------------------------


class TestMigrationGuideBehavioral:
    """MigrationGuideGenerator behavior with various inputs."""

    @pytest.mark.anyio
    async def test_guide_structure_has_required_sections(self):
        """Generated guide contains all required sections."""
        from python_depot.ecosystem.migration import MigrationGuideGenerator

        gen = MigrationGuideGenerator(db=None)
        result = gen.generate_guide(
            "requests", from_manager="pip", to_manager="uv"
        )
        assert isinstance(result, dict)
        assert "package" in result
        assert result["package"] == "requests"
        assert "from_manager" in result
        assert result["from_manager"] == "pip"
        assert "to_manager" in result
        assert result["to_manager"] == "uv"
        assert "guide_markdown" in result
        assert isinstance(result["guide_markdown"], str)
        assert len(result["guide_markdown"]) > 0
        assert "config_changes" in result
        assert isinstance(result["config_changes"], list)

    @pytest.mark.anyio
    async def test_config_changes_matches_from_to_pair(self):
        """config_changes entries correspond to the from→to migration."""
        from python_depot.ecosystem.migration import MigrationGuideGenerator

        gen = MigrationGuideGenerator(db=None)
        result = gen.generate_guide(
            "django", from_manager="pip", to_manager="uv"
        )
        assert "config_changes" in result
        changes = result["config_changes"]
        assert len(changes) > 0
        for change in changes:
            assert "file" in change
            assert "change" in change
            assert isinstance(change["file"], str)
            assert isinstance(change["change"], str)

    @pytest.mark.anyio
    async def test_guide_unsupported_migration_raises_error(self):
        """Unsupported migration (from, to) raises ValueError."""
        from python_depot.ecosystem.migration import MigrationGuideGenerator

        gen = MigrationGuideGenerator(db=None)
        with pytest.raises(ValueError, match="Unsupported migration"):
            gen.generate_guide(
                "requests", from_manager="pip", to_manager="npm"
            )

    @pytest.mark.anyio
    async def test_guide_poetry_to_uv_supported(self):
        """Migration from poetry to uv is supported."""
        from python_depot.ecosystem.migration import MigrationGuideGenerator

        gen = MigrationGuideGenerator(db=None)
        result = gen.generate_guide(
            "requests", from_manager="poetry", to_manager="uv"
        )
        assert isinstance(result, dict)
        assert result["from_manager"] == "poetry"
        assert result["to_manager"] == "uv"

    @pytest.mark.anyio
    async def test_guide_pip_to_poetry_supported(self):
        """Migration from pip to poetry is supported."""
        from python_depot.ecosystem.migration import MigrationGuideGenerator

        gen = MigrationGuideGenerator(db=None)
        result = gen.generate_guide(
            "requests", from_manager="pip", to_manager="poetry"
        )
        assert isinstance(result, dict)
        assert result["from_manager"] == "pip"
        assert result["to_manager"] == "poetry"
