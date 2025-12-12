"""Tests for init command."""

import os
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.commands.init import init
from dot_agent_kit.io.state import load_project_config


def test_init_creates_config(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init creates .erk/installed.toml with correct structure."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})

        assert result.exit_code == 0
        assert "Created" in result.output

        # Config is now created in .erk/ directory
        config_path = tmp_project / ".erk" / "installed.toml"
        assert config_path.exists()

        config = load_project_config(tmp_project)
        assert config is not None
        assert config.version == "1"
        assert len(config.kits) == 0
    finally:
        os.chdir(original_cwd)


def test_init_creates_erk_directory(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init creates .erk/ directory if missing."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})

        assert result.exit_code == 0

        erk_dir = tmp_project / ".erk"
        assert erk_dir.exists()
        assert erk_dir.is_dir()
    finally:
        os.chdir(original_cwd)


def test_init_respects_force_flag(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init respects --force flag to overwrite existing config."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        # Create initial config
        result1 = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result1.exit_code == 0

        # Try to init again without force - should fail
        result2 = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result2.exit_code == 1
        assert "already exists" in result2.output

        # Try with force - should succeed
        result3 = cli_runner.invoke(init, ["--force"], catch_exceptions=False, obj={})
        assert result3.exit_code == 0
        assert "Created" in result3.output
    finally:
        os.chdir(original_cwd)


def test_init_errors_when_config_exists(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init errors appropriately when config exists (without --force)."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        # Create initial config
        result1 = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result1.exit_code == 0

        # Try to init again - should fail with helpful message
        result2 = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result2.exit_code == 1
        # Config is now at .erk/installed.toml
        assert "already exists" in result2.output
        assert "Use --force to overwrite" in result2.output
    finally:
        os.chdir(original_cwd)


def test_init_preserves_existing_erk_directory(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init doesn't fail if .erk/ directory already exists."""
    # Create .erk directory with content
    erk_dir = tmp_project / ".erk"
    erk_dir.mkdir()
    test_file = erk_dir / "test.txt"
    test_file.write_text("test content", encoding="utf-8")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        # Run init
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result.exit_code == 0

        # Verify directory and file still exist
        assert erk_dir.exists()
        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == "test content"
    finally:
        os.chdir(original_cwd)
