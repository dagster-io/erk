"""Tests for erk codespace init command."""

import json

from click.testing import CliRunner

from erk.cli.commands.codespace.init_cmd import init_codespace


def test_init_creates_devcontainer_json() -> None:
    """Test that init creates .devcontainer/devcontainer.json with correct content."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Act
        result = runner.invoke(init_codespace, [])

        # Assert
        assert result.exit_code == 0
        assert "Created" in result.output
        assert "devcontainer.json" in result.output

        # Verify file was created with correct content
        from pathlib import Path

        devcontainer_file = Path(".devcontainer/devcontainer.json")
        assert devcontainer_file.exists()

        content = json.loads(devcontainer_file.read_text(encoding="utf-8"))
        assert content["name"] == "erk-planning"
        assert content["image"] == "mcr.microsoft.com/devcontainers/python:3.13"
        assert "ANTHROPIC_API_KEY" in content["secrets"]


def test_init_fails_if_devcontainer_exists() -> None:
    """Test that init fails if devcontainer.json already exists."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Arrange - create existing file
        from pathlib import Path

        devcontainer_dir = Path(".devcontainer")
        devcontainer_dir.mkdir()
        (devcontainer_dir / "devcontainer.json").write_text("{}", encoding="utf-8")

        # Act
        result = runner.invoke(init_codespace, [])

        # Assert
        assert result.exit_code == 1
        assert "already exists" in result.output
        assert "--force" in result.output


def test_init_with_force_overwrites_existing() -> None:
    """Test that --force overwrites existing devcontainer.json."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Arrange - create existing file with different content
        from pathlib import Path

        devcontainer_dir = Path(".devcontainer")
        devcontainer_dir.mkdir()
        devcontainer_file = devcontainer_dir / "devcontainer.json"
        devcontainer_file.write_text('{"name": "old"}', encoding="utf-8")

        # Act
        result = runner.invoke(init_codespace, ["--force"])

        # Assert
        assert result.exit_code == 0
        assert "Created" in result.output

        # Verify content was overwritten
        content = json.loads(devcontainer_file.read_text(encoding="utf-8"))
        assert content["name"] == "erk-planning"


def test_init_creates_devcontainer_directory() -> None:
    """Test that init creates .devcontainer directory if it doesn't exist."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        from pathlib import Path

        # Verify directory doesn't exist
        assert not Path(".devcontainer").exists()

        # Act
        result = runner.invoke(init_codespace, [])

        # Assert
        assert result.exit_code == 0
        assert Path(".devcontainer").exists()
        assert Path(".devcontainer/devcontainer.json").exists()


def test_init_shows_next_steps() -> None:
    """Test that init shows helpful next steps after creation."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Act
        result = runner.invoke(init_codespace, [])

        # Assert
        assert result.exit_code == 0
        assert "Next steps" in result.output
        assert "ANTHROPIC_API_KEY" in result.output
        assert "gh secret set" in result.output
