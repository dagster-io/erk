"""Tests for hook scoping utilities."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import click
from click.testing import CliRunner

from dot_agent_kit.hooks.decorators import project_scoped
from dot_agent_kit.hooks.scope import is_in_managed_project


class TestIsInManagedProject:
    """Tests for is_in_managed_project function."""

    def test_returns_true_when_config_exists(self, tmp_path: Path) -> None:
        """Test returns True when .erk/dot-agent.toml exists at repo root."""
        # Setup: Create .erk/dot-agent.toml
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir()
        (erk_dir / "dot-agent.toml").write_text("version = 1", encoding="utf-8")

        # Mock git rev-parse to return our temp path as repo root
        with patch("dot_agent_kit.hooks.scope.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "rev-parse", "--show-toplevel"],
                returncode=0,
                stdout=str(tmp_path) + "\n",
                stderr="",
            )
            result = is_in_managed_project()

        assert result is True

    def test_returns_false_when_config_missing(self, tmp_path: Path) -> None:
        """Test returns False when .erk/dot-agent.toml is missing."""
        # No .erk directory created

        # Mock git rev-parse to return our temp path as repo root
        with patch("dot_agent_kit.hooks.scope.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "rev-parse", "--show-toplevel"],
                returncode=0,
                stdout=str(tmp_path) + "\n",
                stderr="",
            )
            result = is_in_managed_project()

        assert result is False

    def test_returns_false_when_erk_dir_exists_but_no_toml(self, tmp_path: Path) -> None:
        """Test returns False when .erk/ exists but dot-agent.toml is missing."""
        # Create .erk/ directory but not the toml file
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir()

        with patch("dot_agent_kit.hooks.scope.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "rev-parse", "--show-toplevel"],
                returncode=0,
                stdout=str(tmp_path) + "\n",
                stderr="",
            )
            result = is_in_managed_project()

        assert result is False

    def test_returns_false_when_not_in_git_repo(self) -> None:
        """Test returns False when not in a git repository."""
        with patch("dot_agent_kit.hooks.scope.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", "rev-parse", "--show-toplevel"],
                stderr="fatal: not a git repository",
            )
            result = is_in_managed_project()

        assert result is False


class TestProjectScopedDecorator:
    """Tests for the project_scoped decorator."""

    def test_decorator_executes_when_in_managed_project(self, cli_runner: CliRunner) -> None:
        """Test decorator allows hook to execute when in managed project."""

        @click.command()
        @project_scoped
        def test_hook() -> None:
            click.echo("Hook executed")

        with patch("dot_agent_kit.hooks.decorators.is_in_managed_project", return_value=True):
            result = cli_runner.invoke(test_hook)

        assert result.exit_code == 0
        assert "Hook executed" in result.output

    def test_decorator_skips_when_not_in_managed_project(self, cli_runner: CliRunner) -> None:
        """Test decorator skips hook silently when not in managed project."""

        @click.command()
        @project_scoped
        def test_hook() -> None:
            click.echo("Hook executed")

        with patch("dot_agent_kit.hooks.decorators.is_in_managed_project", return_value=False):
            result = cli_runner.invoke(test_hook)

        assert result.exit_code == 0
        assert result.output == ""

    def test_decorator_preserves_function_metadata(self) -> None:
        """Test decorator preserves the original function's metadata."""

        @click.command()
        @project_scoped
        def my_test_hook() -> None:
            """This is my test hook docstring."""
            pass

        # functools.wraps should preserve __name__ and __doc__
        # The wrapper function inside project_scoped should have these
        # Note: Click wraps the function in a Command, so we check the callback
        callback = my_test_hook.callback
        assert callback is not None
        assert callback.__name__ == "my_test_hook"
        assert "test hook docstring" in (callback.__doc__ or "")

    def test_decorator_passes_arguments_through(self, cli_runner: CliRunner) -> None:
        """Test decorator passes arguments to the wrapped function."""

        @click.command()
        @click.option("--name", default="World")
        @project_scoped
        def test_hook(name: str) -> None:
            click.echo(f"Hello, {name}!")

        with patch("dot_agent_kit.hooks.decorators.is_in_managed_project", return_value=True):
            result = cli_runner.invoke(test_hook, ["--name", "Test"])

        assert result.exit_code == 0
        assert "Hello, Test!" in result.output


class TestProjectScopedIntegration:
    """Integration tests for project_scoped with actual filesystem."""

    def test_hook_fires_in_managed_project(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test hook fires when .erk/dot-agent.toml exists."""
        # Setup managed project
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir()
        (erk_dir / "dot-agent.toml").write_text("version = 1", encoding="utf-8")

        @click.command()
        @project_scoped
        def test_hook() -> None:
            click.echo("Hook fired")

        # Mock git to return our temp path
        with patch("dot_agent_kit.hooks.scope.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "rev-parse", "--show-toplevel"],
                returncode=0,
                stdout=str(tmp_path) + "\n",
                stderr="",
            )
            result = cli_runner.invoke(test_hook)

        assert result.exit_code == 0
        assert "Hook fired" in result.output

    def test_hook_silent_in_unmanaged_project(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test hook is silent when .erk/dot-agent.toml is missing."""

        @click.command()
        @project_scoped
        def test_hook() -> None:
            click.echo("Hook fired")

        # Mock git to return our temp path (no .erk/dot-agent.toml)
        with patch("dot_agent_kit.hooks.scope.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "rev-parse", "--show-toplevel"],
                returncode=0,
                stdout=str(tmp_path) + "\n",
                stderr="",
            )
            result = cli_runner.invoke(test_hook)

        assert result.exit_code == 0
        assert result.output == ""

    def test_hook_silent_outside_git_repo(self, cli_runner: CliRunner) -> None:
        """Test hook is silent when not in a git repository."""

        @click.command()
        @project_scoped
        def test_hook() -> None:
            click.echo("Hook fired")

        # Mock git to fail (not in repo)
        with patch("dot_agent_kit.hooks.scope.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", "rev-parse", "--show-toplevel"],
                stderr="fatal: not a git repository",
            )
            result = cli_runner.invoke(test_hook)

        assert result.exit_code == 0
        assert result.output == ""
