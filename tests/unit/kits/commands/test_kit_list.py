"""Tests for kit list command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.kit.list import list_installed_kits
from erk.kits.io.state import save_project_config
from erk.kits.models.config import InstalledKit, ProjectConfig


def test_list_installed_kits_with_data() -> None:
    """Test list command displays installed kits properly."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        config = ProjectConfig(
            version="1",
            kits={
                "devrun": InstalledKit(
                    kit_id="devrun",
                    source_type="bundled",
                    version="0.1.0",
                    artifacts=["skills/devrun-make/SKILL.md"],
                ),
                "gh": InstalledKit(
                    kit_id="gh",
                    source_type="package",
                    version="1.2.3",
                    artifacts=["skills/gh/SKILL.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(list_installed_kits)

        assert result.exit_code == 0
        assert "Installed Kits (2):" in result.output
        # Check devrun line
        assert "devrun" in result.output
        assert "0.1.0" in result.output
        assert "bundled" in result.output
        # Check gh line
        assert "gh" in result.output
        assert "1.2.3" in result.output
        assert "package" in result.output


def test_list_no_kits_installed() -> None:
    """Test list command when no kits are installed."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        config = ProjectConfig(version="1", kits={})
        save_project_config(project_dir, config)

        result = runner.invoke(list_installed_kits)

        assert result.exit_code == 0
        assert "No kits installed" in result.output


def test_list_not_in_project_directory() -> None:
    """Test list command when not in a project directory."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Don't create config - simulate being outside project
        result = runner.invoke(list_installed_kits)

        assert result.exit_code == 1
        # Config is now expected at .erk/kits.toml
        assert "Error: No .erk/kits.toml found" in result.output


def test_list_single_kit() -> None:
    """Test list command with a single installed kit."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        config = ProjectConfig(
            version="1",
            kits={
                "example-kit": InstalledKit(
                    kit_id="example-kit",
                    source_type="package",
                    version="2.0.0",
                    artifacts=["skills/example-kit/SKILL.md", "commands/example-kit.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(list_installed_kits)

        assert result.exit_code == 0
        assert "Installed Kits (1):" in result.output
        assert "example-kit" in result.output
        assert "2.0.0" in result.output
        assert "package" in result.output
