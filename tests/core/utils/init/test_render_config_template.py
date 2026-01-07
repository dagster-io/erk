"""Tests for render_config_template function."""

from pathlib import Path

import pytest

from erk.core.init_utils import render_config_template


def test_renders_specified_preset(tmp_path: Path) -> None:
    """Test renders content from specified preset file."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    dagster_preset = presets_dir / "dagster.toml"
    dagster_preset.write_text("trunk_branch = 'master'", encoding="utf-8")

    result = render_config_template(presets_dir, "dagster")

    assert result == "trunk_branch = 'master'"


def test_renders_generic_when_none_specified(tmp_path: Path) -> None:
    """Test renders generic preset when None specified."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    generic_preset = presets_dir / "generic.toml"
    generic_preset.write_text("trunk_branch = 'main'", encoding="utf-8")

    result = render_config_template(presets_dir, None)

    assert result == "trunk_branch = 'main'"


def test_raises_error_for_missing_preset(tmp_path: Path) -> None:
    """Test raises ValueError for non-existent preset."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    with pytest.raises(ValueError, match="Preset 'nonexistent' not found"):
        render_config_template(presets_dir, "nonexistent")


def test_preserves_multiline_content(tmp_path: Path) -> None:
    """Test preserves multiline content from preset file."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    preset = presets_dir / "python.toml"
    preset.write_text(
        """trunk_branch = 'main'
worktree_prefix = 'wt-'""",
        encoding="utf-8",
    )

    result = render_config_template(presets_dir, "python")

    assert "trunk_branch = 'main'" in result
    assert "worktree_prefix = 'wt-'" in result
