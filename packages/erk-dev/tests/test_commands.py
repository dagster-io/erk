"""Integration tests for dev CLI commands."""

from pathlib import Path

from click.testing import CliRunner

from erk_dev.cli import cli


def test_clean_cache_help() -> None:
    """Test clean-cache help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["clean-cache", "--help"])
    assert result.exit_code == 0
    assert "Clean all cache directories" in result.output


def test_publish_to_pypi_help() -> None:
    """Test publish-to-pypi help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["publish-to-pypi", "--help"])
    assert result.exit_code == 0
    assert "Publish packages to PyPI." in result.output


def test_reserve_pypi_name_help() -> None:
    """Test reserve-pypi-name help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reserve-pypi-name", "--help"])
    assert result.exit_code == 0
    assert "Reserve a package name on PyPI" in result.output


def test_create_agents_symlinks_help() -> None:
    """Test create-agents-symlinks help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["create-agents-symlinks", "--help"])
    assert result.exit_code == 0
    assert "Create CLAUDE.md reference" in result.output


def test_bump_version_help() -> None:
    """Test bump-version help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["bump-version", "--help"])
    assert result.exit_code == 0
    assert "Bump all package and kit versions" in result.output


def test_cli_help_shows_commands() -> None:
    """Test that CLI help shows available commands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "bump-version" in result.output
    assert "clean-cache" in result.output
    assert "completion" in result.output
    assert "publish-to-pypi" in result.output
    assert "create-agents-symlinks" in result.output
    assert "reserve-pypi-name" in result.output


def test_all_command_directories_are_registered() -> None:
    """Ensure all command directories have corresponding CLI commands.

    This test prevents forgetting to register new commands when using
    static imports instead of dynamic loading.
    """
    import erk_dev

    # Find all command directories
    commands_dir = Path(erk_dev.__file__).parent / "commands"
    command_dirs = [
        d.name.replace("_", "-")
        for d in commands_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "command.py").exists()
    ]

    # Get registered commands
    registered_commands = list(cli.commands.keys())

    # Check all directories have registered commands
    missing_commands = set(command_dirs) - set(registered_commands)
    extra_commands = set(registered_commands) - set(command_dirs)

    assert not missing_commands, f"Commands not registered in CLI: {missing_commands}"
    assert not extra_commands, f"Commands registered but no directory: {extra_commands}"

    # Verify counts match
    assert len(command_dirs) == len(registered_commands), (
        f"Command directory count ({len(command_dirs)}) != "
        f"registered command count ({len(registered_commands)})"
    )
